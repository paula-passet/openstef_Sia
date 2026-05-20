Models
======

This page explains OpenSTEF's model architecture — the layered design that separates
forecasting logic from preprocessing, persistence, and orchestration. Understanding
these layers helps you choose the right level of abstraction for your use case:
production deployments vs. research experimentation.

For background on why energy forecasting requires specialized tooling, see
:doc:`intro_to_energy_forecasting`.

.. mermaid:: /diagrams/user_guide/concepts/models_diagram_1.mmd

Architecture Layers
-------------------

OpenSTEF is **not opinionated by default** — it exposes full configuration at every
layer. Opinions are added only at the Preset level. The architecture consists of five
layers, from lowest to highest abstraction:

.. list-table:: Architecture Layers
   :header-rows: 1
   :widths: 15 40 25 20

   * - Layer
     - Responsibility
     - Key Classes
     - When to Use
   * - **Forecaster**
     - Standalone model wrapper adding energy-domain awareness (quantile outputs, lead times). No preprocessing — pure predict/fit.
     - :class:`~openstef_core.forecasters.lgbm_forecaster.LGBMForecaster`, :class:`~openstef_core.forecasters.xgboost_forecaster.XGBoostForecaster`, :class:`~openstef_core.forecasters.gblinear_forecaster.GBLinearForecaster`
     - Custom pipelines, research
   * - **Transforms**
     - Standalone pre/postprocessing steps (feature engineering, scaling, outlier handling). Composable via :class:`~openstef_core.mixins.TransformPipeline`.
     - :class:`~openstef_core.mixins.transform.Transform`, :class:`~openstef_core.mixins.TransformPipeline`
     - Building custom pipelines
   * - **Model**
     - Binds a Forecaster + preprocessing Transforms + postprocessing Transforms into a single saveable, serializable unit.
     - :class:`~openstef_meta.models.ensemble_forecasting_model.EnsembleForecastingModel`
     - Packaging for deployment
   * - **Workflow**
     - Orchestrates the Model lifecycle with callbacks, experiment tracking, storage, and evaluation.
     - ``CustomForecastingWorkflow``
     - Full control over training/inference
   * - **Presets**
     - Opinionated constructor functions for Workflows with sensible defaults. Recommended for production.
     - :func:`~openstef_meta.presets.forecasting_workflow.create_ensemble_forecasting_workflow`
     - Production (covers 99% of use cases)

Presets vs. Raw Workflow API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**For production**, use Presets. They encode best practices — proper transform ordering
(validation → features → cleaning), appropriate evaluation metrics, and performance
callbacks:

.. code-block:: python

   from openstef_meta.presets.forecasting_workflow import (
       EnsembleForecastingWorkflowConfig,
       create_ensemble_forecasting_workflow,
   )

   workflow = create_ensemble_forecasting_workflow(config)

**For research/experimentation**, use the raw Workflow API. You get full
configurability over every transform, forecaster combination, and evaluation metric
without the preset's opinions constraining you.

.. note::

   The Preset layer is where OpenSTEF becomes opinionated. Everything below it is a
   toolkit — you compose the pieces however your use case demands.


Available Forecasters
---------------------

OpenSTEF provides several forecaster implementations, each wrapping a proven ML
library with energy-domain extensions (multi-quantile output, lead-time awareness,
proper handling of temporal features).

.. list-table:: Forecaster Comparison
   :header-rows: 1
   :widths: 18 30 25 12 15

   * - Forecaster
     - Strengths
     - Best For
     - Quantile Support
     - Runtime
   * - **LGBMForecaster**
     - Fast training, handles categorical features natively, low memory footprint
     - General-purpose load forecasting, high-frequency retraining
     - Yes (multi-quantile)
     - Fast
   * - **XGBoostForecaster**
     - Strong regularization, robust to outliers, GPU acceleration
     - Non-linear patterns, complex feature interactions
     - Yes (multi-quantile)
     - Medium
   * - **GBLinearForecaster**
     - Interpretable coefficients, single-horizon focus, fast inference
     - Congestion management, regulatory reporting requiring explainability
     - Yes (multi-quantile)
     - Very fast
   * - **Ensemble (via EnsembleForecastingModel)**
     - Combines multiple base forecasters with learned weighting, reduces variance
     - Production deployments where accuracy is paramount and runtime allows
     - Yes (multi-quantile)
     - Slow (trains multiple models)

.. note:: [VISUALIZATION: Bar chart comparing forecaster accuracy (RMSE) across different prediction horizons on a benchmark dataset]


Model Selection Guidance
------------------------

Choosing the right model depends on your operational constraints:

**When accuracy is paramount and runtime allows → Ensemble**

The ensemble model trains multiple base forecasters (LightGBM, XGBoost, etc.) and
learns optimal combination weights via a meta-learner. This reduces prediction variance
and is the recommended default for production. See :doc:`/tutorials/ensemble_forecasting`
for a worked example.

**When interpretability matters → GBLinear**

For congestion management and grid capacity planning, operators often need to explain
*why* a forecast predicts high load. GBLinearForecaster uses XGBoost's ``gblinear``
booster, producing linear coefficients that map directly to feature contributions.

.. warning::

   GBLinearForecaster is constrained to a **single horizon** per model instance.
   If you need multi-horizon forecasts, instantiate one per lead time.

**When speed is critical → LGBMForecaster**

LightGBM's histogram-based algorithm trains significantly faster than XGBoost on large
datasets. For high-frequency retraining (e.g., every 15 minutes), this is often the
only viable single-model option.

**For thermal load forecasting → Median-based approaches**

Thermal loads exhibit strong seasonal patterns with less stochastic variation. Simpler
statistical approaches or ensemble models configured with appropriate lag features
perform well here.


Transform Pipeline Composition
------------------------------

Transforms are the building blocks of preprocessing and postprocessing. They follow a
strict ordering convention:

1. **Validation** — data completeness checks
2. **Feature engineering** — cyclic features, holidays, lags, weather derivatives
3. **Cleaning** — outlier handling, scaling, empty feature removal

.. code-block:: python

   from openstef_core.mixins import TransformPipeline

   preprocessing = TransformPipeline(transforms=[
       CompletenessChecker(completeness_threshold=0.5),
       CyclicFeaturesAdder(),
       LagsAdder(history_available=timedelta(days=14), horizons=horizons),
       Scaler(selection=Exclude(target_column), method="standard"),
   ])

Each transform implements ``fit``, ``transform``, and ``fit_transform``, and tracks its
own fitted state via the ``is_fitted`` property. The pipeline applies transforms
sequentially, passing each output as input to the next.

.. mermaid:: /diagrams/user_guide/concepts/models_diagram_2.mmd

Hyperparameter Configuration
-----------------------------

Every forecaster exposes its hyperparameters through a typed Pydantic model:

- :class:`~openstef_core.forecasters.lgbm_forecaster.LGBMHyperParams` — learning rate, max depth, n_estimators, etc.
- :class:`~openstef_core.forecasters.xgboost_forecaster.XGBoostHyperParams` — same family with XGBoost-specific options
- :class:`~openstef_core.forecasters.gblinear_forecaster.GBLinearHyperParams` — regularization parameters for linear booster

Hyperparameters are set at forecaster construction time and validated by Pydantic.
The Preset layer provides sensible defaults; when using the raw API, you configure
them explicitly.


Next Steps
----------

- :doc:`/tutorials/ensemble_forecasting` — Build and evaluate an ensemble forecast end-to-end
- :ref:`guide_forecasting` — Operational guide for running forecasts in production
- :doc:`intro_to_energy_forecasting` — Background on energy forecasting challenges