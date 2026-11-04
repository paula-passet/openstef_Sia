Foundation Models
=================

Foundation models in OpenSTEF are pretrained forecasting models distributed as ONNX artifacts. They produce forecasts without requiring per-target training, making them suitable for rapid deployment across many grid locations. This page explains what foundation models are, how they fit into the OpenSTEF forecasting architecture, and when to choose them over trained models.

.. note::

   The ``openstef-foundation`` package is under active development. The concepts and interfaces described here reflect the current design direction. Some details may evolve before the stable release.

What Is a Foundation Model?
---------------------------

In the energy forecasting context, a *foundation model* is a neural network pretrained on a large, diverse corpus of energy time series data. Because it has already learned general patterns (diurnal cycles, weather-load relationships, seasonal trends), it can produce reasonable forecasts for a new target without any local training data. This is sometimes called *zero-shot forecasting*.

Traditional forecasting in OpenSTEF follows a train-then-predict cycle: you collect historical data for a specific grid location, train a model (such as XGBoost or LightGBM), and then use that model for predictions. Foundation models skip the training step entirely. You provide input features and the pretrained model returns a forecast immediately.

This distinction matters operationally. When a distribution system operator adds a new measurement point, there may be no historical data available yet. A foundation model can begin producing forecasts on day one, while a trained model must wait until enough data has accumulated.

ONNX as the Runtime Format
--------------------------

OpenSTEF uses the `ONNX Runtime <https://onnxruntime.ai/>`_ to execute foundation models. ONNX (Open Neural Network Exchange) is a vendor-neutral format for representing trained neural networks. By distributing foundation models as ``.onnx`` files, OpenSTEF decouples the training framework (PyTorch, TensorFlow, or others) from the inference environment.

This design has several practical benefits:

- **No training framework dependency.** Production systems do not need PyTorch or TensorFlow installed; only ``onnxruntime`` is required.
- **Hardware acceleration.** ONNX Runtime supports multiple execution providers, allowing the same model file to run on different hardware without code changes.
- **Deterministic inference.** The serialized graph produces identical outputs for identical inputs, simplifying debugging and reproducibility.

Execution Providers
^^^^^^^^^^^^^^^^^^^

An *execution provider* tells ONNX Runtime which hardware backend to use for inference. The choice affects throughput and latency but does not change the model's outputs.

.. list-table:: Supported Execution Providers
   :header-rows: 1
   :widths: 20 40 40

   * - Provider
     - Use Case
     - Notes
   * - ``CPUExecutionProvider``
     - Default; works everywhere
     - No additional dependencies required
   * - ``CUDAExecutionProvider``
     - GPU-accelerated inference on NVIDIA hardware
     - Requires ``onnxruntime-gpu`` and a compatible CUDA toolkit
   * - ``CoreMLExecutionProvider``
     - Apple Silicon (M-series) acceleration
     - Available on macOS with ``onnxruntime`` built with CoreML support

The execution provider is specified as a configuration field. ONNX Runtime attempts providers in the order given and falls back to CPU if the preferred provider is unavailable.

.. code-block:: python

   # Conceptual configuration for execution provider selection
   execution_providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

Integration with the Forecaster Interface
-----------------------------------------

Foundation models in OpenSTEF implement the same :class:`openstef_models.models.forecasting.forecaster.Forecaster` interface used by trained models like XGBoost and LightGBM. This means they participate in the standard prediction pipeline: preprocessing transforms are applied to input data, the forecaster produces raw predictions, and postprocessing transforms format the output.

The key difference is the ``fit`` step. A foundation model's ``is_fitted`` property returns ``True`` immediately because its weights are loaded from the ONNX file at initialization. Calling ``fit`` is either a no-op or performs optional fine-tuning, depending on the implementation.

Because foundation models conform to the ``Forecaster`` interface, they can be used anywhere a trained forecaster is expected: in :doc:`/user_guide/guides/forecasting` workflows, in :doc:`/user_guide/guides/backtesting` evaluations via BEAM, and in ensemble configurations alongside trained models.

Batching Across Multiple Targets
---------------------------------

When forecasting for many grid locations simultaneously, batching becomes important for throughput. The ``Forecaster`` base class provides a ``_predict_batch`` method that, by default, loops over inputs one at a time. Foundation models backed by ONNX Runtime can override this method to issue a single batched inference call, passing multiple targets through the neural network in one forward pass.

Batched inference is particularly effective for foundation models because:

- Neural networks on GPU hardware achieve higher utilization with larger batch sizes.
- The ONNX Runtime session can be reused across all targets in the batch, avoiding repeated session initialization.
- Preprocessing and postprocessing can be vectorized across the batch.

The batch prediction interface is exposed at the workflow level through ``predict_batch``, which accepts a list of datasets and a corresponding sequence of forecast start times. This is the same interface used by trained models, so switching between foundation and trained models requires no changes to the calling code.

Model Selection and Configuration
----------------------------------

Foundation model selection is controlled through configuration fields that specify:

- **Model path.** The filesystem or remote path to the ``.onnx`` file containing the pretrained weights.
- **Execution providers.** An ordered list of ONNX Runtime execution providers to attempt.
- **Quantiles.** The probability levels for probabilistic forecasts, matching the quantiles the foundation model was trained to predict.
- **Horizons.** The lead times the model supports, which must align with the horizons encoded during pretraining.

Because foundation models are pretrained, the quantiles and horizons are fixed at export time. You cannot request a quantile or horizon that the model was not trained to produce. This contrasts with some trained models where these can be configured before training.

Tradeoffs: Foundation Models vs. Trained Models
------------------------------------------------

Choosing between a foundation model and a per-target trained model involves balancing deployment speed against forecast accuracy for specific locations.

.. list-table:: Comparison of Forecasting Approaches
   :header-rows: 1
   :widths: 25 37 38

   * - Characteristic
     - Foundation Model
     - Trained Model (e.g., XGBoost)
   * - Training data required
     - None (zero-shot)
     - Weeks to months of historical data
   * - Time to first forecast
     - Immediate
     - After sufficient data collection and training
   * - Adaptation to local patterns
     - Limited; relies on general patterns
     - Strong; learns location-specific behavior
   * - Computational cost (inference)
     - Higher (neural network forward pass)
     - Lower (tree-based models are fast on CPU)
   * - Hardware acceleration
     - Benefits significantly from GPU
     - Typically CPU-bound
   * - Model size
     - Larger (tens to hundreds of MB)
     - Smaller (typically under 10 MB)
   * - Update cycle
     - New model version from upstream
     - Retrain locally with fresh data

A practical deployment pattern combines both approaches. Foundation models provide forecasts for new or data-sparse locations, while trained models take over once enough historical data is available. The shared ``Forecaster`` interface makes this transition seamless; you swap the forecaster in the workflow configuration without changing the rest of the pipeline.

When to Use Foundation Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Foundation models are a good fit when:

- You need forecasts for a new grid location with no historical measurement data.
- You are onboarding many targets at once and cannot train individual models for each.
- You want a baseline forecast to compare against trained models during evaluation.
- Your deployment environment has GPU resources that can accelerate neural network inference.

When to Prefer Trained Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Trained models are preferable when:

- Sufficient historical data is available for the target location.
- The target exhibits unusual local patterns (e.g., industrial load profiles, behind-the-meter solar) that a general model may not capture.
- Inference latency on CPU is a concern, as tree-based models are typically faster per prediction.
- You need fine-grained control over hyperparameters and feature engineering for a specific use case.

.. seealso::

   - :doc:`/user_guide/concepts/models` for an overview of all available model types and selection guidance.
   - :doc:`/user_guide/guides/forecasting` for the standard prediction workflow that applies to both foundation and trained models.
   - :doc:`/user_guide/concepts/beam` for evaluating and comparing foundation model performance against trained alternatives.