The ``openstef_models`` Package
================================

The ``openstef_models`` package is the primary modelling layer of OpenSTEF. It provides
everything needed to go from raw time series data to a trained, explainable, and
persistable probabilistic forecast: feature engineering transforms, gradient-boosted
forecasting models, component-splitting models, calibration utilities, workflow presets,
and integrations with external tracking systems such as MLflow.

This page focuses on the internal design of ``openstef_models`` — how its sub-packages
relate to each other and how you compose them in practice. For the validated dataset
types that flow through these components, see :doc:`core`. For the large-scale batch
pipelines that orchestrate training and backtesting, see :doc:`beam`. For ensemble
models that combine multiple ``openstef_models`` forecasters, see :doc:`meta`.

.. note::

   [DIAGRAM: Module map showing openstef_models architecture. Top level: Presets/Workflows (ForecastingWorkflowConfig, create_forecasting_workflow, CustomForecastingWorkflow). Middle level: ForecastingModel composed of Transforms (energy_domain, time_domain, general) feeding into Forecasting Models (XGBoost, LightGBM, LGBMLinear, GBLinear, Flatliner) and Component Splitting (ComponentSplitter). Bottom level: Integrations (MLFlowStorage, MLFlowStorageCallback) and Mixins (ModelSerializer, ModelIdentifier, PredictorCallback) providing persistence and lifecycle management. Arrows show: Presets configure ForecastingModel; Transforms feed features into Forecasters; Mixins compose into Forecasters; Integrations receive trained models from Workflows.]

---

Transforms
----------

All feature engineering in ``openstef_models`` is expressed as stateless or stateful
``Transform`` objects that implement the ``TimeSeriesTransform`` protocol from
``openstef_core``. Transforms are grouped into three domain namespaces under
``openstef_models.transforms``.

**Energy domain** (``openstef_models.transforms.energy_domain``)
   Transforms that encode physical knowledge about the power grid. The most commonly
   used are:

   - ``WindPowerFeatureAdder`` — derives wind power estimates from wind speed columns
     using a configurable power curve.
   - Solar irradiance and temperature-based features for photovoltaic generation.

**Time domain** (``openstef_models.transforms.time_domain``)
   Transforms that capture temporal structure:

   - ``LagsAdder`` — the workhorse of time-series feature engineering. It generates
     lagged copies of the target variable at configurable offsets. Three strategies are
     available: *trivial* (fixed minute/day lags), *custom* (explicit ``timedelta``
     list), and *autocorrelation-based* (peaks in the ACF determine which lags are
     informative). The transform is horizon-aware: it only adds lags that are causally
     valid for each forecast horizon in the dataset.
   - ``RollingAggregatesAdder`` — appends rolling-window statistics (mean, median, max,
     min) over configurable windows.

**General** (``openstef_models.transforms.general``)
   Model-agnostic utilities such as ``DimensionalityReducer``, which wraps a
   dimensionality-reduction step (e.g. PCA) as a fitted transform that can be
   serialised alongside the model.

Transforms are composed into a ``TransformPipeline`` (from ``openstef_core``) and
attached to a ``ForecastingModel`` as either a *preprocessing* or *postprocessing*
stage:

.. code-block:: python

   from datetime import timedelta

   from openstef_core.mixins.transform import TransformPipeline
   from openstef_core.types import LeadTime, Q

   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.time_domain.rolling_aggregates_adder import (
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.energy_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )

   horizons = [LeadTime(timedelta(hours=h)) for h in [1, 4, 24]]

   preprocessing = TransformPipeline(
       transforms=[
           WindPowerFeatureAdder(wind_speed_column="wind_speed_80m"),
           LagsAdder(horizons=horizons),
           RollingAggregatesAdder(
               aggregates=["mean", "median", "max", "min"],
               horizons=horizons,
           ),
       ]
   )

---

Forecasting Models
------------------

``openstef_models.models.forecasting`` contains the gradient-boosted tree forecasters
that power the majority of OpenSTEF deployments. All forecasters produce *probabilistic*
outputs: rather than a single point estimate, each model predicts a configurable set of
quantiles simultaneously.

The available forecasters fall into two families:

**Gradient boosting trees (non-linear)**

- ``XGBoostForecaster`` — XGBoost with multi-quantile regression. Handles complex
  non-linear patterns well and is the default choice for load forecasting.
- ``LGBMForecaster`` — LightGBM equivalent; typically faster to train on large datasets.
- ``LGBMLinearForecaster`` — LightGBM with linear leaf models. Combines the
  tree-structure feature selection of LightGBM with linear extrapolation at the leaves,
  which can improve performance on targets with strong linear trends.

**Linear gradient boosting**

- ``GBLinearForecaster`` — gradient-boosted linear model. Trades some non-linear
  modelling capacity for better extrapolation outside the training distribution and
  faster inference.

**Baseline**

- ``ConstantMedianForecaster`` (``FlatLiner``) — predicts historical quantile values
  as constants. Useful as a sanity-check baseline and for testing pipeline plumbing
  without a real model.

All forecasters share the same interface: they accept a ``ForecastInputDataset``,
return a ``ForecastDataset``, and expose a ``quantiles`` property listing the quantile
levels they were configured to predict. Hyperparameters are declared as typed Pydantic
models (e.g. ``LGBMLinearHyperParams``) so they can be validated, serialised, and
logged automatically.

---

Component Splitting
-------------------

``openstef_models.models.component_splitting`` addresses a different but related
problem: given a net load measurement on a grid connection, decompose it into
constituent generation and consumption components (solar, wind, base load, etc.).

The central class is ``ComponentSplitter``, configured via ``ComponentSplitterConfig``.
Rather than learning a full generative model, component splitters typically combine
known physical ratios (installed capacity, efficiency curves) with statistical
corrections learned from historical data. The output is a ``TimeSeriesDataset`` with
one column per identified component, which can then be fed into separate forecasters
for each component.

.. code-block:: python

   from openstef_models.models.component_splitting import (
       ComponentSplitter,
       ComponentSplitterConfig,
   )

   config = ComponentSplitterConfig(
       solar_capacity_mwp=12.5,
       wind_capacity_mw=0.0,
   )
   splitter = ComponentSplitter(config=config)
   splitter.fit(historical_dataset)
   components = splitter.transform(historical_dataset)
   # components now contains separate columns for each energy source

---

Presets and Workflows
---------------------

The ``openstef_models.presets`` sub-package provides a high-level entry point that
assembles transforms, a forecaster, and optional postprocessing into a single
``CustomForecastingWorkflow`` object. This is the recommended way to use the library
for standard energy forecasting tasks.

The key objects are:

- ``ForecastingWorkflowConfig`` — a Pydantic configuration model that captures every
  aspect of a workflow: model type, forecast horizons, quantiles, weather column
  mappings, rolling aggregate settings, MLflow connection details, and more.
- ``LocationConfig`` — optional sub-config that attaches geographic metadata (name,
  region, coordinates) to a workflow. Its ``tags`` property produces a dictionary
  suitable for MLflow run tagging.
- ``create_forecasting_workflow(config)`` — factory function that instantiates a
  ``CustomForecastingWorkflow`` from a ``ForecastingWorkflowConfig``.

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow
   from openstef_core.types import Q, LeadTime
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="substation_amsterdam_001",
       model="xgboost",
       horizons=[LeadTime(timedelta(hours=h)) for h in [1, 4, 24, 48]],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       # Weather feature column mappings
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       # Rolling aggregate features
       rolling_aggregate_features=["mean", "median", "max", "min"],
       # Disable MLflow for local experimentation
       mlflow_storage=None,
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(training_dataset)
   forecast = workflow.predict(inference_dataset)

.. note::

   ``ForecastingWorkflowConfig`` is intentionally declarative: the same configuration
   object can be serialised to JSON, stored alongside a trained model, and used to
   reconstruct an identical workflow later. This makes it the natural unit of
   configuration in production deployments.

**[VISUALIZATION: Example probabilistic forecast output — three quantile bands (P10, P50, P90) plotted against actual load measurements over a 48-hour horizon, produced by the workflow above]**

---

Integrations
------------

MLflow
^^^^^^

``openstef_models.integrations.mlflow`` provides a first-class MLflow integration for
model lifecycle management. It exposes two classes:

- ``MLFlowStorage`` — a storage backend that serialises trained models, logs
  hyperparameters and metrics to an MLflow tracking server, and manages the model
  registry. It uses ``JoblibModelSerializer`` (from
  ``openstef_models.integrations.joblib``) to serialise model artefacts before
  uploading them.
- ``MLFlowStorageCallback`` — a ``PredictorCallback`` that can be attached to a
  workflow so that every training run automatically logs to MLflow without any
  additional boilerplate.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback
   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow
   from openstef_core.types import Q, LeadTime
   from datetime import timedelta

   storage = MLFlowStorage(tracking_uri="http://mlflow.example.com:5000")

   config = ForecastingWorkflowConfig(
       model_id="substation_amsterdam_001",
       model="lgbm",
       horizons=[LeadTime(timedelta(hours=1))],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       mlflow_storage=storage,
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(training_dataset)
   # Model, hyperparameters, and metrics are now logged to MLflow automatically.

.. note::

   MLflow is an optional dependency. Install it with ``pip install openstef-models[mlflow]``.
   The rest of the library functions without it.

---

Mixins
------

``openstef_models.mixins`` provides composable building blocks for model management
that are used internally by forecasters and integrations:

- ``ModelSerializer`` — protocol and base implementation for serialising and
  deserialising trained model objects. Concrete implementations (e.g.
  ``JoblibModelSerializer``) plug in different serialisation backends.
- ``ModelIdentifier`` — attaches a stable string identity to a model instance, used
  as the key for storage and retrieval in registries.
- ``PredictorCallback`` — a hook interface invoked at defined points in the training
  and prediction lifecycle. ``MLFlowStorageCallback`` is the primary built-in
  implementation, but the interface is public so you can attach custom callbacks (e.g.
  for alerting or custom metrics logging).

These mixins follow the composition-over-inheritance pattern: rather than a deep class
hierarchy, forecasters gain capabilities by holding mixin instances as attributes.

---

Explainability
--------------

``openstef_models.explainability`` provides two mixins that forecasters can implement
to expose interpretability information:

- ``ExplainableForecaster`` — declares a ``feature_importances`` property returning a
  ``pd.DataFrame`` of importance scores, and a ``plot_feature_importances`` method
  that produces an interactive Plotly treemap grouped by feature category. All
  gradient-boosted forecasters in ``openstef_models`` implement this mixin.
- ``ContributionsMixin`` — extends explainability to the sample level via
  ``predict_contributions``, which returns a ``TimeSeriesDataset`` where each column
  represents the additive contribution of one feature to each prediction. This is
  particularly useful for debugging unexpected forecast behaviour on specific days.

.. code-block:: python

   # After fitting a workflow, inspect feature importances
   forecaster = workflow.model.forecaster

   # Tabular importances
   importances_df = forecaster.feature_importances
   print(importances_df.head(10))

   # Interactive treemap (returns a Plotly Figure)
   from openstef_core.types import Q
   fig = forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()

   # Per-sample contributions (if the forecaster implements ContributionsMixin)
   from openstef_models.explainability.mixins import ContributionsMixin
   if isinstance(forecaster, ContributionsMixin):
       contributions = forecaster.predict_contributions(inference_dataset)

**[VISUALIZATION: Feature importance treemap showing grouped contributions of lag features, weather features, and calendar features to the median (P50) forecast, as produced by plot_feature_importances()]**

---

Putting It Together
-------------------

The design of ``openstef_models`` follows a clear layering principle:

1. **Transforms** encode domain knowledge and temporal structure as reusable,
   composable steps.
2. **Forecasting models** and **component splitters** consume transformed features and
   produce probabilistic outputs.
3. **Mixins** compose orthogonal capabilities (serialisation, callbacks, explainability)
   into forecasters without coupling them to specific infrastructure.
4. **Presets** assemble all of the above into a single, configuration-driven workflow
   object that is the primary public API for most users.
5. **Integrations** connect workflows to external systems (MLflow) for production
   lifecycle management.

For running these workflows at scale across many grid connections, see :doc:`beam`,
which wraps ``openstef_models`` workflows in Apache Beam pipelines for distributed
backtesting and training. For combining multiple ``openstef_models`` forecasters into
an ensemble, see :doc:`meta`.