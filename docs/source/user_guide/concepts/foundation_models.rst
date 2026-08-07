Foundation Models
=================

This page explains how OpenSTEF supports foundation models: pre-trained forecasting models that can generate predictions for new targets without per-target training. Foundation models use the ONNX runtime for efficient inference, enabling zero-shot forecasting across thousands of grid locations with minimal setup.

What is a Foundation Model?
---------------------------

In the OpenSTEF context, a foundation model is a forecasting model that has been pre-trained on a large, diverse corpus of energy time series data. Unlike the standard workflow where each target (substation, feeder, solar park) requires its own training cycle with historical data, a foundation model arrives ready to predict.

The key distinction:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Aspect
     - Trained Model
     - Foundation Model
   * - Setup time
     - Requires weeks of historical data collection and training
     - Immediate; no per-target training needed
   * - Adaptation
     - Fully adapted to local patterns and characteristics
     - Generalizes across targets; less local adaptation
   * - Deployment
     - One model artifact per target
     - Single model artifact serves many targets
   * - Data requirements
     - Historical load, weather, and calendar features per target
     - Only current input features at inference time
   * - Best suited for
     - High-value targets with stable data pipelines
     - Rapid onboarding, cold-start scenarios, large-scale rollouts

Foundation models are provided by the ``openstef-foundation`` package, which is currently under active development. They complement (rather than replace) per-target trained models in the OpenSTEF ecosystem.

.. note::

   Foundation models trade local adaptation for deployment speed. For targets where you have sufficient historical data and the time to train, a per-target model (see :ref:`concept_models`) will typically capture local patterns more precisely.

ONNX Runtime for Inference
--------------------------

OpenSTEF foundation models are distributed as ONNX (Open Neural Network Exchange) files. ONNX is a vendor-neutral format that decouples model training from inference, allowing models trained in any framework (PyTorch, TensorFlow, JAX) to run through a single, optimized runtime.

Using ONNX provides several advantages for energy forecasting deployments:

- **Portability**: the same model file runs on Linux servers, edge devices, and cloud instances without framework-specific dependencies.
- **Performance**: the ONNX Runtime applies graph optimizations (operator fusion, memory planning) that reduce latency compared to running the original training framework.
- **Minimal dependencies**: inference requires only ``onnxruntime`` (or a hardware-specific variant), not the full training stack.

Execution Providers
^^^^^^^^^^^^^^^^^^^

The ONNX Runtime supports multiple hardware backends through *execution providers*. OpenSTEF allows you to configure which provider to use based on your deployment hardware:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Provider
     - Use case
   * - ``CPUExecutionProvider``
     - Default; works everywhere. Suitable for moderate batch sizes and standard server deployments.
   * - ``CUDAExecutionProvider``
     - NVIDIA GPU acceleration. Beneficial when processing large batches across many targets simultaneously.
   * - ``CoreMLExecutionProvider``
     - Apple Silicon (M1/M2/M3). Useful for local development or edge deployments on macOS hardware.

The execution provider is selected at model initialization. If a requested provider is unavailable (for example, requesting CUDA on a machine without a GPU), the runtime falls back to CPU automatically.

.. warning::

   GPU-accelerated providers (CUDA, CoreML) require installing the corresponding ``onnxruntime`` variant (e.g., ``onnxruntime-gpu``). The base ``onnxruntime`` package only includes the CPU provider.

Batched Inference Across Targets
--------------------------------

A key architectural advantage of foundation models is their ability to process multiple targets in a single forward pass. Rather than invoking the model once per target, OpenSTEF batches prediction requests together, which is significantly more efficient on both CPU and GPU hardware.

The batching mechanism builds on the :class:`~openstef_core.mixins.predictor.BatchPredictor` interface. This interface defines a ``predict_batch`` method that accepts a list of input datasets and returns predictions for all of them in one call. The foundation model's ONNX session processes the entire batch as a single tensor operation.

How batching works in practice:

1. Multiple targets are collected into a batch (up to a configurable ``batch_size``).
2. Each target's input features are preprocessed independently into a standardized format.
3. The preprocessed inputs are stacked into a single tensor and passed to the ONNX session.
4. The runtime returns predictions for all targets simultaneously.
5. Results are unpacked and postprocessed per target.

This approach scales well: forecasting 10,000 grid locations becomes a matter of processing a manageable number of batches rather than 10,000 sequential model invocations.

When to Use Foundation Models
-----------------------------

Foundation models are most valuable in scenarios where per-target training is impractical or unnecessary:

- **Cold start**: a new grid location has been instrumented but lacks the weeks of historical data needed to train a dedicated model.
- **Large-scale rollout**: onboarding hundreds or thousands of targets simultaneously, where training individual models would take days.
- **Rapid prototyping**: evaluating whether forecasting adds value for a new use case before investing in a full training pipeline.
- **Fallback**: providing predictions when a trained model fails or becomes stale (see :doc:`/user_guide/guides/reliability_fallback`).

For production targets with stable data pipelines and sufficient history, per-target trained models (XGBoost, LightGBM, or ensembles) will generally outperform a foundation model on local patterns such as site-specific load shapes, unusual weather sensitivities, or atypical calendar effects. The recommended approach is to start with a foundation model for immediate coverage, then transition high-value targets to trained models as data accumulates.

Relationship to Other Concepts
------------------------------

Foundation models integrate with the broader OpenSTEF architecture:

- **Model selection** (:ref:`concept_models`): the workflow configuration determines whether a target uses a trained model or a foundation model. Both produce the same output format (quantile forecasts over specified horizons).
- **Probabilistic forecasting** (:doc:`/user_guide/guides/probabilistic_forecasting`): foundation models produce quantile predictions, enabling the same uncertainty estimation workflows as trained models.
- **Backtesting** (:doc:`/user_guide/guides/backtesting`): foundation models can be evaluated using the same backtesting infrastructure, allowing direct comparison against trained alternatives.
- **Meta-learning** (:ref:`concept_metalearning`): while meta-learning selects the best *trained* model type per target, foundation models offer an alternative path that bypasses model selection entirely.