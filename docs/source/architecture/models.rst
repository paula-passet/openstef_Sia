The openstef_models Package
===========================

The ``openstef_models`` package is the algorithmic core of OpenSTEF. It provides
the feature engineering transforms, forecasting models, component-splitting models,
and the preset/workflow layer that assembles them into end-to-end pipelines. This
page explains how those pieces relate to each other and how to use them directly.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

For the pipeline layer that schedules and executes these workflows at scale, see
:doc:`beam`. For ensemble composition across multiple models, see :doc:`meta`.


Transforms
----------

All feature engineering is expressed as stateless or stateful *transform* objects
that operate on ``TimeSeriesDataset`` instances (defined in ``openstef_core``; see
:doc:`core`). Transforms are grouped into four sub-packages by concern.

General transforms
^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.general`` contains the workhorse preprocessing steps
that apply regardless of domain:

- ``Imputer`` — fills missing values using a configurable strategy.
- ``NaNDropper`` — removes rows that still contain NaN after imputation.
- ``OutlierHandler`` — clips or removes statistical outliers.
- ``Scaler`` — standardises or normalises feature columns.
- ``Selector`` — drops low-importance or zero-variance features.
- ``Shifter`` — creates lag copies of target or feature columns.
- ``EmptyFeatureRemover`` — prunes columns that are entirely empty.
- ``SampleWeighter`` / ``SampleWeightConfig`` — assigns per-sample training weights,
  useful for down-weighting stale historical data.

Time-domain transforms
^^^^^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.time_domain`` derives features from the timestamp
index itself:

- ``DatetimeFeaturesAdder`` — extracts hour-of-day, day-of-week, month, etc.
- ``CyclicFeaturesAdder`` — encodes periodic features as sine/cosine pairs so
  that midnight and 23:00 are numerically adjacent.
- ``HolidayFeatureAdder`` — adds a binary holiday indicator using a configurable
  calendar.
- ``LagsAdder`` — appends lagged observations at specified offsets.
- ``RollingAggregatesAdder`` — computes rolling mean, median, max, and min over
  configurable windows.

Energy-domain transforms
^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.energy_domain`` contains physics-informed feature
engineering specific to power systems:

- ``WindPowerFeatureAdder`` — derives wind-power-relevant features (e.g. cubed
  wind speed, air density corrections) from raw meteorological inputs.

Additional energy-domain transforms follow the same pattern and can be composed
freely with the general and time-domain transforms.

Post-processing transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_models.transforms.postprocessing`` operates on model *outputs* rather
than inputs:

- ``QuantileSorter`` — enforces monotonicity across quantile predictions so that
  e.g. the 10th percentile never exceeds the 90th.
- ``ConfidenceIntervalApplicator`` — widens or clips confidence intervals to
  respect physical constraints such as non-negative power.


Forecasting Models
------------------

``openstef_models.models.forecasting`` provides probabilistic, multi-quantile
forecasters. Every forecaster produces a distribution over the forecast horizon
rather than a single point estimate.

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Class
     - Backend
     - Notes
   * - ``XGBoostForecaster``
     - XGBoost
     - Gradient-boosted trees; strong on non-linear patterns.
   * - ``GBLinearForecaster``
     - XGBoost (linear booster)
     - Better extrapolation outside training range; faster inference.
   * - ``LGBMForecaster``
     - LightGBM
     - Leaf-wise boosting; efficient on large datasets.
   * - ``LGBMLinearForecaster``
     - LightGBM (linear)
     - Linear variant of the LightGBM booster.
   * - ``MedianForecaster``
     - Statistical
     - Returns the historical median; useful as a baseline.
   * - ``FlatlinerForecaster``
     - Statistical
     - Returns a constant; used as a degenerate baseline or placeholder.

Each tree-based forecaster ships with a corresponding ``HyperParams`` dataclass
(e.g. ``XGBoostHyperParams``, ``LGBMHyperParams``) that documents and validates
its tunable parameters.

.. code-block:: python

   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   params = XGBoostHyperParams(n_estimators=500, learning_rate=0.05, max_depth=6)
   model = XGBoostForecaster(hyperparams=params)


Component Splitting
-------------------

Beyond whole-load forecasting, ``openstef_models`` supports *component splitting*:
decomposing a measured load signal into interpretable sub-components (e.g. base
load, solar generation, wind generation). Component-splitting models live under
``openstef_models.models`` alongside the forecasting models and share the same
transform infrastructure, but their outputs are multi-column datasets representing
each physical component rather than quantile bands.

This is particularly useful when downstream consumers need component-level
visibility — for example, a grid operator who needs to know how much of the
residual load is attributable to behind-the-meter solar.


Presets and Workflows
---------------------

Assembling transforms and models by hand is verbose. The ``openstef_models.presets``
package provides a higher-level configuration-driven API that wires everything
together into a ``CustomForecastingWorkflow``.

``ForecastingWorkflowConfig`` is a validated ``BaseConfig`` dataclass that
captures all choices in one place: which model to use, which weather columns are
available, which quantiles to predict, horizon settings, rolling-aggregate
statistics, and MLflow storage options.

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   config = ForecastingWorkflowConfig(
       model_id="my_substation_001",
       run_name="training_run_v1",
       model="xgboost",
       horizons=[1, 24, 48],          # hours ahead
       quantiles=[0.1, 0.5, 0.9],
       temperature_column="temperature_2m",
       wind_speed_column="wind_speed_80m",
       radiation_column="shortwave_radiation",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
       mlflow_storage=None,           # set to an MLFlowStorage instance in production
   )

   workflow = create_forecasting_workflow(config)

The returned ``CustomForecastingWorkflow`` exposes ``train`` and ``predict``
methods and can be handed directly to the ``openstef_beam`` pipeline layer (see
:doc:`beam`) for distributed execution.

``LocationConfig`` is a companion dataclass that attaches geographic metadata
(name, region, coordinates) to a workflow. Its ``tags`` property serialises the
location as a flat ``dict[str, str]``, which MLflow uses to tag experiment runs
for easy filtering.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import LocationConfig

   location = LocationConfig(
       name="Substation Noord",
       region="Amsterdam",
       latitude=52.38,
       longitude=4.90,
   )
   # location.tags() → {"name": "Substation Noord", "region": "Amsterdam", ...}


MLflow Integration
------------------

``openstef_models.integrations.mlflow`` provides two classes that connect
workflows to an MLflow tracking server:

- ``MLFlowStorage`` — handles serialising a trained model to the MLflow model
  registry and loading it back. It implements the ``ModelSerializer`` interface
  (see `Mixins`_ below) so it can be dropped into any workflow that expects a
  storage backend.
- ``MLFlowStorageCallback`` — a ``PredictorCallback`` that fires after each
  training run to persist the model and log metrics automatically.

.. code-block:: python

   from openstef_models.integrations.mlflow import MLFlowStorage, MLFlowStorageCallback

   storage = MLFlowStorage(
       tracking_uri="http://mlflow.internal:5000",
       experiment_name="load_forecasting",
   )
   callback = MLFlowStorageCallback(storage=storage)

   config = ForecastingWorkflowConfig(
       model_id="substation_001",
       model="lgbm",
       horizons=[1, 24],
       quantiles=[0.1, 0.5, 0.9],
       mlflow_storage=storage,
   )
   workflow = create_forecasting_workflow(config)

MLflow is an optional dependency. If it is not installed, importing from
``openstef_models.integrations.mlflow`` raises an ``ImportError`` with an
informative message.

.. note::

   ``MLFlowStorage`` stores models using MLflow's native ``pyfunc`` flavour, which
   means any MLflow-compatible serving infrastructure (e.g. Azure ML, Databricks,
   self-hosted REST server) can load and serve OpenSTEF models without additional
   glue code.


Mixins
------

``openstef_models.mixins`` provides reusable behaviours that can be composed into
custom model classes without inheriting from a concrete base:

- ``ModelSerializer`` / ``ModelIdentifier`` — abstract the persistence contract.
  ``ModelIdentifier`` uniquely names a model (combining ``model_id`` and version
  information); ``ModelSerializer`` defines ``save`` and ``load`` methods.
  ``MLFlowStorage`` is the production implementation; a filesystem-based
  implementation is straightforward to write for testing.
- ``PredictorCallback`` — a hook interface invoked at defined points in the
  training and prediction lifecycle. ``MLFlowStorageCallback`` is the built-in
  implementation, but custom callbacks (e.g. sending Slack alerts, writing to a
  database) follow the same interface.

.. code-block:: python

   from openstef_models.mixins import ModelIdentifier, ModelSerializer, PredictorCallback

   class LocalDiskStorage(ModelSerializer):
       def save(self, identifier: ModelIdentifier, model) -> None:
           import joblib, pathlib
           pathlib.Path("models").mkdir(exist_ok=True)
           joblib.dump(model, f"models/{identifier.model_id}.pkl")

       def load(self, identifier: ModelIdentifier):
           import joblib
           return joblib.load(f"models/{identifier.model_id}.pkl")


Explainability
--------------

``openstef_models.explainability`` provides two mixin classes and a plotter that
add interpretability to any forecaster:

- ``ExplainableForecaster`` — declares a ``feature_importances`` property
  returning a ``pd.DataFrame`` of importance scores, and a
  ``plot_feature_importances`` method that renders an interactive Plotly treemap
  grouped by feature category.
- ``ContributionsMixin`` — adds ``predict_contributions``, which returns a
  ``TimeSeriesDataset`` where each column is the additive contribution of one
  feature to the prediction. This is the SHAP-style decomposition used to explain
  individual forecasts.
- ``FeatureImportancePlotter`` — a standalone utility that takes a feature
  importance ``DataFrame`` and produces the treemap figure, usable independently
  of the mixin.

.. code-block:: python

   from openstef_models.explainability import ExplainableForecaster, ContributionsMixin
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   # XGBoostForecaster already implements both mixins
   workflow = create_forecasting_workflow(config)
   workflow.train(train_dataset)

   model: XGBoostForecaster = workflow.model

   # Global feature importance
   importances = model.feature_importances   # pd.DataFrame
   fig = model.plot_feature_importances()    # plotly Figure
   fig.show()

   # Per-sample contributions for a specific forecast window
   contributions = model.predict_contributions(forecast_input)

.. note:: [VISUALIZATION: Plotly treemap of feature importances grouped by category (time features, weather features, lag features), with colour intensity proportional to importance score.]

The ``predict_contributions`` output has the same index as the input dataset,
making it straightforward to plot contribution time series alongside the forecast
to understand *why* a particular spike or trough was predicted.


Putting It Together
-------------------

The following sketch shows a complete local training and inference loop using
only ``openstef_models``, without the Beam pipeline layer:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.integrations.mlflow import MLFlowStorage

   # 1. Configure
   storage = MLFlowStorage(
       tracking_uri="http://localhost:5000",
       experiment_name="demo",
   )
   config = ForecastingWorkflowConfig(
       model_id="demo_substation",
       model="lgbm",
       horizons=[1, 24, 48],
       quantiles=[0.05, 0.5, 0.95],
       temperature_column="temperature_2m",
       wind_speed_column="wind_speed_80m",
       radiation_column="shortwave_radiation",
       rolling_aggregate_features=["mean", "median"],
       mlflow_storage=storage,
   )

   # 2. Build workflow (assembles transforms + model + callbacks)
   workflow = create_forecasting_workflow(config)

   # 3. Train — persists to MLflow automatically via MLFlowStorageCallback
   workflow.train(train_dataset)

   # 4. Forecast
   forecast = workflow.predict(forecast_input_dataset)

   # 5. Explain
   fig = workflow.model.plot_feature_importances()
   fig.show()

For distributed backtesting across many substations, pass the workflow to the
``openstef_beam`` pipelines described in :doc:`beam`. For combining multiple
workflows into a single ensemble output, see :doc:`meta`.