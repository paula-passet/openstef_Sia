The openstef_models Package
===========================

This page covers the ``openstef_models`` package — the model layer of OpenSTEF. It describes how feature transforms are organised by domain, which forecasting and component-splitting models are available, how presets and workflows tie everything together, and how integrations, mixins, and explainability tools extend the core modelling loop.

For the validated dataset types that flow through these models see :doc:`core`, and for the Beam-based batch pipelines that run them at scale see :doc:`beam`.

.. note:: [DIAGRAM: Module map showing transforms (energy_domain, time_domain, and other domain sub-packages) feeding into models (forecasting models and component-splitting models). Presets/workflows sit as a top-level orchestration layer above both. Integrations (MLflow storage, callbacks) attach to the workflow layer for persistence. Mixins and explainability modules attach to individual model classes.]

----

Package layout
--------------

``openstef_models`` is structured around four concerns:

- **Transforms** — stateless or stateful feature-engineering steps, grouped by domain.
- **Models** — forecasting estimators and component-splitting estimators.
- **Presets & workflows** — high-level configuration objects that wire transforms and models into a ready-to-run pipeline.
- **Cross-cutting utilities** — integrations (MLflow), mixins (serialisation, callbacks), and explainability tools.

Transforms
----------

All feature-engineering logic lives under ``openstef_models.transforms``. Transforms are grouped into domain sub-packages so that related steps can be imported and composed independently.

Energy-domain transforms
^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.energy_domain`` contains steps that are specific to power-grid data: solar irradiance corrections, wind-speed scaling, electricity-price lags, and similar energy-system features. These transforms expect the column-naming conventions defined by ``openstef_core`` datasets (see :doc:`core`).

Time-domain transforms
^^^^^^^^^^^^^^^^^^^^^^

Calendar and temporal features — hour-of-day, day-of-week, holiday flags, and rolling-window aggregates — live in a separate sub-package. Keeping them separate means they can be reused for any time-series problem without pulling in energy-specific dependencies.

Rolling aggregate features (mean, median, max, min over configurable windows) are a first-class concept here and are exposed directly through ``ForecastingWorkflowConfig``:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="my_load_model",
       rolling_aggregate_features=["mean", "median", "max", "min"],
       horizons=[1, 24, 48],
       quantiles=[0.1, 0.5, 0.9],
   )

Forecasting models
------------------

Forecasting estimators live under ``openstef_models.models.forecasting``. All of them target **probabilistic, multi-quantile** output — each model produces a separate prediction for every requested quantile rather than a single point estimate.

The available models are:

- **XGBoostForecaster** — gradient-boosted trees via XGBoost; handles complex nonlinear patterns well and is the default choice for most load-forecasting tasks.
- **LGBMForecaster** — gradient-boosted trees via LightGBM; faster training on large datasets.
- **LGBMLinearForecaster** — LightGBM with linear leaves (``linear_tree=True``); combines tree structure with linear extrapolation, which can improve behaviour at the edges of the training distribution.

All three share the same ``Forecaster`` base class and accept ``ForecastInputDataset`` / ``ForecastDataset`` types from ``openstef_core``. Hyperparameters are declared as ``HyperParams`` subclasses (also from ``openstef_core``), which means they are validated by Pydantic and can be serialised to JSON.

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_core.datasets import ForecastInputDataset

   model = XGBoostForecaster()
   model.fit(train_dataset)

   forecast = model.predict(ForecastInputDataset(...))

For ensemble forecasting across multiple model types, see :doc:`meta`.

Component splitting
-------------------

Component-splitting models decompose a total load signal into interpretable sub-components (for example, base load, solar contribution, and wind contribution) before or after forecasting. They live under ``openstef_models.models.component_splitting`` and follow the same ``Forecaster`` interface, so they can be slotted into any workflow that accepts a standard estimator.

Component splitting is particularly useful when downstream consumers need to reason about individual generation or consumption sources rather than the aggregate net load.

Presets and workflows
---------------------

The ``openstef_models.presets`` package is the recommended entry point for most users. Rather than assembling transforms and models by hand, you declare intent through ``ForecastingWorkflowConfig`` and let ``create_forecasting_workflow`` build the pipeline:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   config = ForecastingWorkflowConfig(
       model_id="wind_park_alpha",
       model="lgbm",
       horizons=[1, 4, 24],
       quantiles=[0.05, 0.25, 0.5, 0.75, 0.95],
       # Weather column mappings
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       temperature_column="temperature_2m",
       relative_humidity_column="relative_humidity_2m",
       # Rolling features
       rolling_aggregate_features=["mean", "median", "max", "min"],
       # MLflow persistence
       mlflow_storage=None,   # set to an MLFlowStorage instance to enable
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)
   forecast = workflow.predict(input_dataset)

``ForecastingWorkflowConfig`` also accepts a ``LocationConfig`` for tagging experiments with geographic metadata, which flows through to MLflow run tags automatically.

.. note::

   ``model_reuse_enable=True`` tells the workflow to skip retraining when a
   previously fitted model for the same ``model_id`` is already available. This
   is especially useful during backtesting runs where the same model is evaluated
   across many time windows.

The returned ``CustomForecastingWorkflow`` object is a self-contained, serialisable unit: it holds the fitted transforms, the fitted estimator, and the configuration that produced them.

MLflow integration
------------------

``openstef_models.integrations.mlflow`` provides two classes:

- **MLFlowStorage** — reads and writes fitted workflows to an MLflow model registry. Pass an instance to ``ForecastingWorkflowConfig.mlflow_storage`` to enable automatic versioning.
- **MLFlowStorageCallback** — a callback that logs metrics, parameters, and artefacts to an MLflow experiment run during ``fit``.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   storage = MLFlowStorage(tracking_uri="http://mlflow.example.com")

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model="lgbm",
       horizons=[1, 24],
       quantiles=[0.1, 0.5, 0.9],
       mlflow_storage=storage,
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)
   # The fitted workflow is now versioned in the MLflow registry.
   # Reload it later:
   loaded = storage.load("substation_42")

.. note::

   MLflow is an optional dependency. Install it with ``pip install openstef-models[mlflow]``.

Mixins
------

``openstef_models.mixins`` provides building blocks for model management:

- **ModelSerializer / ModelIdentifier** — handle serialisation of fitted estimators to and from persistent storage, with a stable identity scheme based on ``model_id``.
- **PredictorCallback** — a hook interface that workflow steps call at defined points in the training and prediction lifecycle. Implement this interface to add custom logging, alerting, or side-effects without modifying the core workflow.

These mixins are used internally by ``MLFlowStorageCallback`` and are available for custom integrations.

Explainability
--------------

``openstef_models.explainability`` gives models the ability to report *why* they produced a particular forecast.

Two mixins define the contract:

- **ExplainableForecaster** — any model implementing this mixin exposes a ``feature_importances`` property (returns a ``pd.DataFrame``) and a ``plot_feature_importances`` method (returns an interactive Plotly treemap).
- **ContributionsMixin** — extends explainability to the sample level: ``predict_contributions(data)`` returns a ``TimeSeriesDataset`` where each column is the additive contribution of one feature to the prediction.

``LGBMForecaster`` and ``LGBMLinearForecaster`` implement both mixins. ``XGBoostForecaster`` implements ``ExplainableForecaster``.

.. code-block:: python

   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

   model = LGBMForecaster()
   model.fit(train_dataset)

   # Global feature importance
   importances = model.feature_importances          # pd.DataFrame
   fig = model.plot_feature_importances()           # Plotly Figure
   fig.show()

.. note:: [VISUALIZATION: Interactive treemap showing feature importance scores grouped by feature category (weather, calendar, rolling aggregates), with tile size proportional to importance.]

.. code-block:: python

   # Per-sample contributions
   contributions = model.predict_contributions(input_dataset)
   # contributions is a TimeSeriesDataset with one column per input feature

.. note::

   ``FeatureImportancePlotter`` from ``openstef_models.explainability`` can be
   used standalone to render importance data that was computed elsewhere or
   loaded from storage.

Putting it together
-------------------

The typical development loop with ``openstef_models`` is:

1. Choose or customise transforms from ``openstef_models.transforms``.
2. Select a forecasting model or component-splitting model.
3. Wrap both in a ``ForecastingWorkflowConfig`` and call ``create_forecasting_workflow``.
4. Attach an ``MLFlowStorage`` for persistence and a ``PredictorCallback`` for observability.
5. Inspect results with ``plot_feature_importances`` or ``predict_contributions``.

Steps 1–4 are handled automatically when you use the preset; you only need to drop down to the lower layers when you need behaviour the preset does not expose.

For running this workflow at scale across many substations or time windows, see :doc:`beam`, which wraps ``CustomForecastingWorkflow`` in Apache Beam pipelines. For ensemble strategies that combine multiple ``openstef_models`` estimators, see :doc:`meta`.