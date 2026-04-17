The Model Layer (``openstef_models``)
======================================

The ``openstef_models`` package is the algorithmic core of OpenSTEF. It provides the
feature engineering transforms, forecasting models, component splitters, and workflow
presets that you compose to build short-term energy forecasting pipelines. Everything
in this package depends on the validated dataset types and base abstractions defined in
``openstef_core`` (see :doc:`core`), and its workflows are executed at scale by the
pipelines in ``openstef_beam`` (see :doc:`beam`).

This page covers the internal structure of ``openstef_models``: how transforms are
organised by domain, which forecasting and component-splitting models are available,
how presets and workflows tie everything together, and how integrations (MLflow),
mixins, and explainability utilities extend the core functionality.

.. note::

   [DIAGRAM: Module map showing transforms (grouped by domain: time_domain, weather_domain, energy_domain, general, postprocessing) feeding into ForecastingModel and ComponentSplittingModel, with CustomForecastingWorkflow / ForecastingWorkflowConfig as top-level orchestration, and MLFlowStorage / MLFlowStorageCallback as persistence integrations hanging off the workflow layer]

----

Transforms: Feature Engineering by Domain
------------------------------------------

All transforms in ``openstef_models.transforms`` implement the ``TimeSeriesTransform``
interface from ``openstef_core``: they accept a ``TimeSeriesDataset`` and return an
enriched ``TimeSeriesDataset``. Each transform also exposes a ``features_added()``
method so that downstream selectors can reason about what columns were introduced.

Transforms are grouped into four sub-packages that reflect the origin of the features
they produce.

**Time domain** (``openstef_models.transforms.time_domain``)
   Derives features purely from the timestamp index. This group is the most broadly
   applicable and is included in virtually every workflow preset:

   - ``DatetimeFeaturesAdder`` — hour-of-day, day-of-week, month, and similar calendar
     features encoded as numerics.
   - ``CyclicFeaturesAdder`` — sine/cosine encoding of periodic calendar features to
     avoid discontinuities at period boundaries.
   - ``HolidayFeatureAdder`` — binary flags for public holidays, configurable per
     country/region.
   - ``RollingAggregatesAdder`` — rolling window statistics (mean, median, min, max)
     over the target or any other column.
   - ``LagsAdder`` — lagged copies of the target column at configurable offsets.
   - ``Shifter`` — shifts a column by a fixed number of steps, useful for aligning
     external signals with the forecast horizon.

**Weather domain** (``openstef_models.transforms.weather_domain``)
   Derives higher-level meteorological features from raw weather inputs:

   - ``AtmosphereDerivedFeaturesAdder`` — computes derived atmospheric variables (e.g.
     dew point, absolute humidity) from basic measurements such as temperature and
     relative humidity.
   - ``DaylightFeatureAdder`` — adds solar elevation angle and daylight duration, which
     are strong drivers of both solar generation and load.
   - ``RadiationDerivedFeaturesAdder`` — derives additional irradiance features from
     raw shortwave radiation measurements.

**Energy domain** (``openstef_models.transforms.energy_domain``)
   Encodes physical knowledge specific to the power system:

   - ``WindPowerFeatureAdder`` — converts wind speed to an estimated wind power output
     using a configurable power curve, providing a physics-informed feature for wind
     park forecasting.

**General utilities** (``openstef_models.transforms.general``)
   Data-quality and dimensionality transforms that are model-agnostic:

   - ``Imputer`` / ``NaNDropper`` — handle missing values before model training.
   - ``OutlierHandler`` — clips or removes statistical outliers.
   - ``Scaler`` — standardises or normalises feature columns.
   - ``Selector`` / ``EmptyFeatureRemover`` — prune uninformative or zero-variance
     columns.
   - ``DimensionalityReducer`` — wraps a fitted dimensionality reduction step (e.g.
     PCA) as a stateful transform.
   - ``SampleWeighter`` / ``SampleWeightConfig`` — assigns per-sample training weights,
     for example to down-weight older observations.

**Postprocessing** (``openstef_models.transforms.postprocessing``)
   Applied after the model produces raw quantile predictions:

   - ``ConfidenceIntervalApplicator`` — maps raw quantile outputs to a calibrated
     confidence interval representation.
   - ``QuantileSorter`` — enforces quantile monotonicity (i.e. that Q10 ≤ Q50 ≤ Q90)
     after any postprocessing step that could violate it.

----

Forecasting Models
------------------

``openstef_models.models.forecasting`` contains the gradient-boosting forecasters that
power the majority of OpenSTEF deployments. All of them implement the
``openstef_core`` ``Predictor`` protocol and produce probabilistic (multi-quantile)
outputs.

.. list-table::
   :header-rows: 1
   :widths: 25 55 20

   * - Class
     - Characteristics
     - Hyperparams class
   * - ``XGBoostForecaster``
     - Gradient-boosted trees via XGBoost; handles complex nonlinear patterns well;
       default choice for most load forecasting tasks.
     - ``XGBoostHyperParams``
   * - ``LGBMForecaster``
     - Gradient-boosted trees via LightGBM; faster training and lower memory than
       XGBoost on large datasets.
     - ``LGBMHyperParams``
   * - ``GBLinearForecaster``
     - Gradient-boosted linear model; better extrapolation outside the training range;
       useful when the relationship is approximately linear.
     - ``GBLinearHyperParams``
   * - ``LGBMLinearForecaster``
     - LightGBM with a linear booster; combines LightGBM's efficiency with linear
       extrapolation.
     - ``LGBMLinearHyperParams``
   * - ``MedianForecaster``
     - Returns the rolling historical median; a lightweight statistical baseline.
     - —
   * - ``FlatlinerForecaster``
     - Returns a constant value; used as a degenerate baseline and in testing.
     - —

Each gradient-boosting forecaster accepts a ``quantiles`` list and a ``horizons`` list
at construction time, so the same model object produces all requested quantiles for all
requested lead times in a single ``predict`` call.

The ``ForecastingModel`` class (``openstef_models.models``) wraps a forecaster together
with optional preprocessing and postprocessing ``TransformPipeline`` instances, forming
a self-contained, serialisable unit:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_core.types import LeadTime, Q
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_models.transforms.general import Imputer, OutlierHandler
   from openstef_models.transforms.postprocessing import QuantileSorter

   model = ForecastingModel(
       forecaster=XGBoostForecaster(
           horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT4H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=XGBoostHyperParams(),
       ),
       preprocessing=TransformPipeline(transforms=[Imputer(), OutlierHandler()]),
       postprocessing=TransformPipeline(transforms=[QuantileSorter()]),
       target_column="load",
   )

----

Component Splitting
-------------------

Alongside point and probabilistic forecasting, ``openstef_models`` provides a parallel
model family for *component splitting*: decomposing a measured total load signal into
its constituent energy-source components (solar, wind, residual load, etc.).

The base abstraction lives in
``openstef_models.models.component_splitting.component_splitter``:

- ``ComponentSplitterConfig`` — declares which source column to split and which
  ``EnergyComponentType`` values to produce.
- ``ComponentSplitter`` — abstract base that all splitters implement; its ``predict``
  method maps a ``TimeSeriesDataset`` to an ``EnergyComponentDataset``.

Two concrete implementations are provided:

- **``ConstantComponentSplitter``** — applies fixed ratios derived from known
  installed-capacity data. Factory methods ``known_solar_park()`` and
  ``known_wind_farm()`` provide sensible defaults for common asset types.
- **``LinearComponentSplitter``** — fits a linear model to learn component ratios from
  labelled training data.

The high-level ``ComponentSplittingModel`` (``openstef_models.models.component_splitting_model``)
wraps a ``ComponentSplitter`` with preprocessing and postprocessing pipelines, mirroring
the ``ForecastingModel`` pattern:

.. code-block:: python

   from openstef_models.models.component_splitting import (
       ComponentSplitter,
       ComponentSplitterConfig,
   )
   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
   )

   # Use a preset for a known solar park
   splitter = ConstantComponentSplitter.known_solar_park()
   components = splitter.predict(dataset)  # returns EnergyComponentDataset

----

Presets and Workflows
---------------------

Building a full forecasting pipeline by hand — assembling transforms, choosing a model,
wiring up serialisation — is repetitive. The ``openstef_models.presets`` package
captures this boilerplate in two classes:

- **``ForecastingWorkflowConfig``** — a Pydantic ``BaseConfig`` that declares every
  knob of a standard forecasting workflow: model type, forecast horizons, quantiles,
  weather column mappings, rolling aggregate statistics, MLflow storage settings, and
  more.
- **``create_forecasting_workflow(config)``** — factory function that instantiates a
  ``CustomForecastingWorkflow`` from a config object, wiring together the appropriate
  transforms and model automatically.

``LocationConfig`` is a companion config that carries grid-location metadata (name,
region, coordinates) and exposes a ``tags`` property that generates a dictionary
suitable for use as MLflow run tags.

A typical preset-based workflow looks like this:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow
   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model="xgboost",
       horizons=["PT1H", "PT4H", "PT24H"],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       # Weather column mappings (must match column names in your dataset)
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       relative_humidity_column="relative_humidity_2m",
       pressure_column="surface_pressure",
       # Rolling aggregate features to add
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   workflow = create_forecasting_workflow(config)

   # Train on historical data
   workflow.fit(train_dataset)

   # Generate probabilistic forecasts
   forecast = workflow.predict(forecast_dataset)

The ``CustomForecastingWorkflow`` returned by the factory is the same object used
internally by the ``openstef_beam`` batch pipelines, so a workflow developed and tested
locally can be handed directly to a Beam pipeline without modification.

.. note::

   The ``openstef_meta`` package provides an ``EnsembleForecastingWorkflow`` preset
   that mirrors this API but combines multiple ``CustomForecastingWorkflow`` instances
   into an ensemble. See :doc:`meta` for details.

----

Integrations
------------

MLflow
^^^^^^

The ``openstef_models.integrations.mlflow`` sub-package provides two classes for
integrating model lifecycle management with an MLflow tracking server:

- **``MLFlowStorage``** — a storage backend that serialises trained models, logs
  metrics and hyperparameters, and manages the MLflow experiment/run hierarchy.
  It handles local artifact staging before upload and normalises tracking URIs
  (including local file paths) automatically.
- **``MLFlowStorageCallback``** — a ``PredictorCallback`` that triggers
  ``MLFlowStorage`` operations at the appropriate points in the training and prediction
  lifecycle, so you can attach MLflow tracking to any workflow without modifying the
  model code.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback
   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow

   storage = MLFlowStorage(tracking_uri="http://mlflow.example.com:5000")

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model="lgbm",
       horizons=["PT1H"],
       quantiles=["Q10", "Q50", "Q90"],
       mlflow_storage=storage,
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)
   # Model, metrics, and hyperparameters are automatically logged to MLflow

.. note::

   MLflow is an optional dependency. Install it with ``pip install openstef-models[mlflow]``
   before using this integration.

Joblib
^^^^^^

``openstef_models.integrations.joblib`` provides ``JoblibModelSerializer``, a
serialisation backend used by ``MLFlowStorage`` to persist trained model objects to
disk. It is used internally and rarely needs to be called directly.

----

Mixins
------

``openstef_models.mixins`` provides two reusable building blocks for model management:

- **``ModelSerializer``** — abstract interface for serialising and deserialising trained
  model objects. Concrete implementations (such as ``JoblibModelSerializer``) plug in
  via this interface, making it straightforward to swap serialisation backends.
- **``ModelIdentifier``** — a value object that uniquely identifies a model within a
  storage backend, combining a model ID with optional versioning metadata.
- **``PredictorCallback``** — base class for lifecycle hooks that fire at defined points
  during training and prediction. ``MLFlowStorageCallback`` is the primary built-in
  implementation, but you can subclass ``PredictorCallback`` to add custom behaviour
  (e.g. sending alerts, writing to a database) without touching workflow code.

----

Explainability
--------------

Understanding *why* a model produces a particular forecast is essential for operational
trust. ``openstef_models.explainability`` provides two mixin interfaces and a suite of
plotters:

- **``ExplainableForecaster``** — mixin for forecasters that expose feature importance
  scores. Implementing classes must provide a ``feature_importances`` property returning
  a ``pd.DataFrame``, and gain a ``plot_feature_importances(quantile)`` method that
  renders an interactive Plotly treemap grouped by feature domain.
- **``ContributionsMixin``** — mixin for forecasters that can attribute individual
  predictions to specific features. The ``predict_contributions(data)`` method returns
  a ``TimeSeriesDataset`` where each column represents the contribution of one feature
  to the forecast at each timestep.

The XGBoost and LightGBM forecasters implement both mixins out of the box, so feature
importances and per-sample SHAP-style contributions are available without any extra
configuration:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow
   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model="xgboost",
       horizons=["PT1H"],
       quantiles=[Q(0.5)],
   )
   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)

   forecaster = workflow.model.forecaster

   # Global feature importances as a DataFrame
   importances = forecaster.feature_importances

   # Interactive treemap (returns a Plotly Figure)
   fig = forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()

   # Per-sample contributions
   contributions = forecaster.predict_contributions(forecast_dataset)

[VISUALIZATION: Feature importance treemap showing top features grouped by domain (time, weather, energy) for a trained XGBoostForecaster]

----

Putting It All Together
-----------------------

The relationship between the layers described on this page can be summarised as:

1. **Transforms** enrich raw ``TimeSeriesDataset`` objects with domain-specific features.
2. **``ForecastingModel``** / **``ComponentSplittingModel``** wrap a core model with
   pre- and postprocessing transform pipelines.
3. **``CustomForecastingWorkflow``** (created via ``create_forecasting_workflow``)
   orchestrates training and prediction, optionally persisting results via an
   ``MLFlowStorageCallback``.
4. **Explainability mixins** expose feature importances and per-sample contributions
   from the trained forecaster without requiring any changes to the workflow.

For running these workflows at scale across many grid locations, see :doc:`beam`, which
describes how ``openstef_beam`` wraps ``CustomForecastingWorkflow`` in distributed
Apache Beam pipelines. For ensemble strategies that combine multiple
``CustomForecastingWorkflow`` instances, see :doc:`meta`.