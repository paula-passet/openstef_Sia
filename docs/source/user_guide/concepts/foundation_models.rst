Foundation Models
=================

This page explains how OpenSTEF uses pretrained foundation models for zero-shot energy forecasting. Unlike traditional per-target models that require historical training data, foundation models produce forecasts immediately for any time series, making them ideal for new connections, rapid deployment, or situations where training data is unavailable.

For an overview of all model types (including trained models), see :doc:`/user_guide/concepts/models`.

What is a Foundation Model?
---------------------------

A foundation model in the OpenSTEF context is a large pretrained time-series forecaster (currently Chronos-2) that has learned temporal patterns from millions of diverse time series. Because it generalizes across domains, it can produce probabilistic forecasts for energy targets it has never seen before.

The key properties are:

- **Zero-shot inference**: no per-target training step; ``fit()`` is a no-op.
- **Probabilistic output**: native quantile predictions (e.g. Q10, Q50, Q90).
- **Covariate-aware**: non-target columns (weather forecasts) condition the prediction.
- **ONNX-based**: the model ships as an ONNX graph, executed through ONNX Runtime for portable, hardware-accelerated inference.

OpenSTEF publishes Chronos-2 checkpoints on the HuggingFace Hub in two sizes:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Size
     - Enum member
     - Use case
   * - Base
     - ``Chronos2.BASE``
     - Higher accuracy; recommended when GPU is available
   * - Small
     - ``Chronos2.SMALL``
     - Lower latency; suitable for CPU-only environments

ONNX Runtime Backend
--------------------

Foundation model inference is handled by :class:`~openstef_foundation_models.inference.onnx_backend.OnnxBackend`, which wraps an ONNX Runtime ``InferenceSession``. The session is built once from a resolved checkpoint and reused for every subsequent ``run()`` call, so a single backend instance can serve an entire backtest or production loop without reloading weights.

The backend is constructed through :meth:`~openstef_foundation_models.inference.onnx_backend.OnnxBackend.from_checkpoint`, which accepts:

- A resolved checkpoint (weights file plus metadata).
- An ordered list of execution providers.
- Optional session configuration (thread counts, graph optimization level).

Execution Provider Selection
----------------------------

Which hardware accelerator ONNX Runtime dispatches to depends on both the host platform and the checkpoint's properties (precision, static vs. dynamic shapes). OpenSTEF encapsulates this logic in a **provider policy** rather than scattering platform checks throughout application code.

The available providers are:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Provider
     - Class
     - Notes
   * - CPU
     - :class:`~openstef_foundation_models.inference.providers.CpuProvider`
     - Always available; the universal fallback.
   * - CUDA
     - :class:`~openstef_foundation_models.inference.providers.CudaProvider`
     - NVIDIA GPUs. Works with fp16, fp32, and int8 graphs.
   * - TensorRT
     - :class:`~openstef_foundation_models.inference.providers.TensorRTProvider`
     - Opt-in NVIDIA acceleration with engine caching. Not selected by default due to build cost.
   * - CoreML
     - :class:`~openstef_foundation_models.inference.providers.CoreMLProvider`
     - Apple GPU / Neural Engine. Requires static-shape checkpoints (``MLProgram`` format).

The :class:`~openstef_foundation_models.inference.provider_selection.DefaultProviderPolicy` applies these rules automatically:

- **int8 checkpoints**: CUDA + CPU (CoreML cannot accelerate quantized ops).
- **macOS with static shapes**: CoreML (``CPUAndGPU``) + CPU.
- **NVIDIA host**: CUDA + CPU.
- **Fallback**: CPU only.

To override the automatic selection, pass explicit providers in the backend configuration:

.. code-block:: python

   from openstef_foundation_models.inference.providers import CudaProvider, CpuProvider

   config = ForecastingWorkflowConfig(
       backend=OnnxBackendConfig(providers=[CudaProvider(), CpuProvider()]),
   )

Checkpoint Variants
-------------------

Each published checkpoint comes in two ONNX variants:

- **Dynamic** (default): variable-length input shapes; portable across platforms.
- **Static**: fixed tensor dimensions; required for CoreML acceleration on macOS.

The :meth:`~openstef_foundation_models.models.catalog.CheckpointVariant.recommended` class method selects the appropriate variant for the current host (static on macOS, dynamic elsewhere). You can also point to a local ONNX export via a ``LocalCheckpoint`` for air-gapped or custom-trained models.

Workflow Configuration
----------------------

The :class:`~openstef_foundation_models.presets.forecasting_workflow.ForecastingWorkflowConfig` is the single declarative object that controls a foundation-model forecast. Its key fields are:

- ``model``: the model family (currently ``"chronos2"``).
- ``checkpoint``: which weights to load (size, variant, or local path).
- ``quantiles``: the quantile levels to predict.
- ``horizons``: one or more forecast lead times.
- ``target_column``: the column to forecast.
- ``selected_features``: columns to retain; every non-target column becomes a known covariate.
- ``backend``: nested config for execution providers and session options.

The factory function :func:`~openstef_foundation_models.presets.forecasting_workflow.create_forecasting_workflow` resolves the checkpoint, builds the ONNX session once, and returns a ready-to-use :class:`~openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow`.

.. code-block:: python

   from openstef_foundation_models.models import Chronos2
   from openstef_foundation_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig, create_forecasting_workflow,
   )

   workflow = create_forecasting_workflow(ForecastingWorkflowConfig(
       checkpoint=Chronos2.SMALL.checkpoint(),
   ))

Batching Across Multiple Targets
---------------------------------

Foundation models benefit significantly from batching: stacking multiple forecast windows into a single ONNX Runtime call amortizes session overhead and enables GPU parallelism.

OpenSTEF supports batching at two levels:

- **Forecaster level**: :meth:`~openstef_foundation_models.models.forecasting.chronos2_forecaster.Chronos2Forecaster.predict_batch` accepts a list of input datasets and returns one forecast per input in a single backend call.
- **Workflow level**: :meth:`~openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow.predict_batch` orchestrates batched prediction with callback execution.

In a live setting you would typically batch forecasts for many different locations or targets at once. For backtesting, the pipeline groups consecutive forecast windows per target into batches of a configurable size.

.. note::

   Larger batch sizes reduce the number of ONNX calls but increase peak memory. For CPU-only inference, a batch size of 1 is often optimal. On GPU, batch sizes of 8-32 typically yield the best throughput.

Tradeoffs vs. Trained Models
-----------------------------

Choosing between a foundation model and a per-target trained model involves balancing deployment speed against local adaptation:

.. list-table::
   :header-rows: 1
   :widths: 25 40 40

   * - Dimension
     - Foundation model (zero-shot)
     - Trained model (per-target)
   * - Setup time
     - Immediate; no training data needed
     - Requires weeks/months of historical data
   * - Local adaptation
     - Limited; relies on covariates for context
     - Learns target-specific patterns and seasonality
   * - Maintenance
     - Single model serves all targets
     - One model per target to retrain and monitor
   * - Accuracy (mature targets)
     - Good baseline; may underperform on idiosyncratic loads
     - Typically higher after sufficient training
   * - New connections
     - Ideal; forecasts from day one
     - Cannot produce forecasts until data accumulates

A common deployment pattern is to use the foundation model as a starting point for new targets, then transition to a trained model once enough historical data has accumulated. The :doc:`/user_guide/guides/reliability_fallback` mechanisms can also use a foundation model as a fallback when a trained model fails validation.

.. warning::

   Because ``fit()`` is a no-op for foundation models, calling it does not raise an error but produces no trained state. The model is considered fitted from construction. Ensure your orchestration logic does not wait for a training step that will never produce new weights.

Evaluating Foundation Model Performance
---------------------------------------

Foundation models participate in the same evaluation framework as trained models. Use :doc:`/user_guide/concepts/beam` to run backtests that compare a foundation-model workflow against trained alternatives on the same historical windows. The backtest pipeline automatically uses ``predict_batch`` when a batch size is configured, making large-scale evaluation efficient.