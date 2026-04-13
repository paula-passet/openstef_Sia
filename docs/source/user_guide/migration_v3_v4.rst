Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant redesign of the library that introduces a modular,
multi-package architecture, replaces the ``PredictionJobDataClass`` configuration
model with composable Python objects, and swaps the monolithic pipeline API for
an explicit workflow pattern. This page covers every breaking change you are
likely to encounter, explains the reasoning behind each one, and provides
concrete before/after code examples to guide your migration.

.. note::

   V3 and V4 are **not** backwards-compatible. A codebase written against the
   V3 API will not run against V4 without changes. Work through this guide
   top-to-bottom before attempting to run your existing code against the new
   library.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 shipped as a single ``openstef`` package that bundled data access
(``openstef-dbc``), model logic, pipelines, and feature engineering together.
This made the library hard to extend and tightly coupled it to a specific
database back-end.

V4 splits the library into focused, independently installable packages:

- **openstef-core** — base interfaces, dataset types, and abstract model
  contracts.
- **openstef-models** — concrete model implementations (XGBoost, etc.),
  feature transforms, and workflow helpers.
- **openstef-beam** — optional Apache Beam integration for large-scale
  distributed forecasting.

The practical consequence is that your imports change, the configuration object
changes, and the high-level pipeline functions are replaced by an explicit
workflow class. Each of these is covered in its own section below.

.. note:: [DIAGRAM: V3 single-package layout vs V4 multi-package layout showing openstef-core / openstef-models / openstef-beam as separate boxes with dependency arrows]

----

Package Structure and Imports
------------------------------

In V3, everything lived under the ``openstef`` namespace:

.. code-block:: python

   # Before (V3)
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

In V4, imports are distributed across the new packages:

.. code-block:: python

   # After (V4)
   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.integrations.joblib import JoblibModelSerializer

Install the packages you need:

.. code-block:: bash

   pip install openstef-core openstef-models
   # Optional: distributed execution
   pip install openstef-beam

----

Configuration: PredictionJobDataClass → Composable Objects
-----------------------------------------------------------

V3 used a single flat ``PredictionJobDataClass`` dictionary-like object to
carry every piece of configuration — model type, horizon, resolution, quantiles,
feature flags, and location metadata — in one place.

.. code-block:: python

   # Before (V3)
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       horizon_minutes=48 * 60,
       resolution_minutes=15,
       lat=52.0,
       lon=5.0,
       train_components=False,
       name="TestPrediction",
       model_type_group=None,
       hyper_params={},
       feature_names=None,
       forecast_type="demand",
   )
   modelspecs = ModelSpecificationDataClass(id=pj["id"])

V4 removes ``PredictionJobDataClass`` entirely. Configuration is now expressed
through typed, composable objects that are passed directly to the components
that need them. A ``LocationConfig`` captures site metadata, hyperparameters
are typed dataclasses on the model class itself, and the ``ForecastingModel``
assembles everything:

.. code-block:: python

   # After (V4)
   from openstef_models.presets.forecasting_workflow import LocationConfig
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_models.models import ForecastingModel
   from openstef_models.transforms.time_domain import (
       HolidayFeatureAdder,
       LagsAdder,
   )
   from openstef_models.transforms.general import Scaler

   location = LocationConfig(
       id=287,
       name="TestPrediction",
       lat=52.0,
       lon=5.0,
   )

   hyperparams = XGBoostHyperParams()          # typed, with sensible defaults

   forecaster = XGBoostForecaster(hyperparams=hyperparams)

   model = ForecastingModel(
       predictor=forecaster,
       feature_pipeline=...,                   # see Feature Engineering section
       postprocessor=...,
   )

The key benefit is that each concern — location, hyperparameters, features,
post-processing — is now a separate, independently testable object rather than
a field in a single flat dictionary.

----

Data Structures: DataFrames → TimeSeriesDataset
------------------------------------------------

V3 pipelines accepted and returned plain ``pandas.DataFrame`` objects, with
the index expected to be a ``DatetimeIndex``.

.. code-block:: python

   # Before (V3)
   import pandas as pd

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   # Pass raw DataFrame directly to the pipeline
   train_model_pipeline(pj, input_data, ...)

V4 introduces ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` as
first-class data containers. ``VersionedTimeSeriesDataset`` is particularly
important for backtesting because it tracks *when* each observation became
available, preventing data leakage.

.. code-block:: python

   # After (V4)
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset

   raw = pd.read_csv(
       "data/load_data.csv",
       index_col="datetime",
       parse_dates=True,
   )

   # Wrap in a VersionedTimeSeriesDataset
   dataset = VersionedTimeSeriesDataset(raw)

   # Pass the dataset to the workflow — not a bare DataFrame
   workflow.train(dataset)

You can still work with the underlying DataFrame via the dataset's standard
pandas-compatible interface, so existing data-loading code needs only a thin
wrapping layer rather than a full rewrite.

----

Pipelines → Workflows
---------------------

V3 exposed two top-level pipeline functions — ``train_model_pipeline`` and
``create_forecast_pipeline`` — that handled everything internally, including
MLflow tracking URI management.

.. code-block:: python

   # Before (V3)
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Train
   train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

   # Forecast
   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

V4 replaces these functions with a ``CustomForecastingWorkflow`` class. Model
persistence is handled by an explicit ``LocalModelStorage`` (or any compatible
storage back-end), which you construct and inject yourself:

.. code-block:: python

   # After (V4)
   from pathlib import Path
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.integrations.joblib import JoblibModelSerializer
   from openstef_core.storage import LocalModelStorage

   storage = LocalModelStorage(
       Path("./trained_models"),
       serializer=JoblibModelSerializer(),
   )

   workflow = CustomForecastingWorkflow(
       model=model,           # ForecastingModel built above
       storage=storage,
   )

   # Train and persist
   workflow.train(train_dataset)

   # Load and forecast
   workflow.load("my_model")
   forecast = workflow.predict(forecast_dataset)

Separating storage from the pipeline logic means you can swap in an S3-backed
or database-backed storage implementation without touching your training code.
See :doc:`data_integration` for patterns covering S3, Databricks, and InfluxDB
storage back-ends.

----

Feature Engineering
-------------------

V3 applied feature engineering automatically inside the pipeline based on
flags set on the ``PredictionJobDataClass`` (e.g., ``train_components``,
``feature_names``).

V4 makes the feature pipeline explicit. You compose a ``FeaturePipeline`` from
individual transform classes and attach it to the ``ForecastingModel``:

.. code-block:: python

   # After (V4) — explicit feature pipeline
   from openstef_models.transforms.general import (
       Scaler,
       EmptyFeatureRemover,
       NaNDropper,
   )
   from openstef_models.transforms.time_domain import (
       HolidayFeatureAdder,
       DatetimeFeaturesAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   feature_pipeline = [
       HolidayFeatureAdder(country="NL"),
       DatetimeFeaturesAdder(),
       LagsAdder(lags=[1, 2, 4, 7 * 24 * 4]),   # 15-min resolution lags
       RollingAggregatesAdder(),
       EmptyFeatureRemover(),
       NaNDropper(),
       Scaler(),
   ]

   model = ForecastingModel(
       predictor=XGBoostForecaster(),
       feature_pipeline=feature_pipeline,
   )

This explicit composition replaces the implicit feature selection that V3
controlled via ``feature_names`` and ``hyper_params`` keys on the prediction
job.

----

Model Storage: MLflow → Pluggable Storage
-----------------------------------------

V3 was tightly coupled to MLflow for model tracking and artifact storage. The
``mlflow_tracking_uri`` parameter appeared on every pipeline call.

V4 introduces a storage abstraction. ``LocalModelStorage`` with
``JoblibModelSerializer`` is the default for local development; other
serializers and storage back-ends can be plugged in without changing pipeline
code.

.. code-block:: python

   # Before (V3) — MLflow URI threaded through every call
   train_model_pipeline(pj, data, mlflow_tracking_uri="./mlflow_trained_models", ...)
   create_forecast_pipeline(pj, data, mlflow_tracking_uri="./mlflow_trained_models")

.. code-block:: python

   # After (V4) — storage configured once, injected into workflow
   from openstef_models.integrations.joblib import JoblibModelSerializer
   from openstef_core.storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(
       Path("./trained_models"),
       serializer=JoblibModelSerializer(),
   )
   # storage is passed to the workflow once; pipeline calls are storage-agnostic

.. note::

   If you relied on MLflow's experiment tracking UI, you will need to add your
   own tracking layer in V4. The library no longer prescribes a tracking
   back-end.

----

Removed: openstef-dbc Integration
----------------------------------

V3 shipped a companion package ``openstef-dbc`` that provided database tasks
wrapping the pipelines (fetching input data, writing forecasts to InfluxDB,
etc.). These tasks are **not** part of V4.

If your V3 code used ``openstef-dbc`` tasks directly, you need to replace them
with explicit data-loading code. The :doc:`data_integration` page covers
recommended patterns for reading from InfluxDB, S3, and Databricks in V4.

----

Step-by-Step Migration Workflow
---------------------------------

Work through these steps in order to migrate an existing V3 codebase:

1. **Update dependencies.** Replace ``openstef`` in your ``requirements.txt``
   or ``pyproject.toml`` with ``openstef-core`` and ``openstef-models``. Remove
   ``openstef-dbc`` if present.

2. **Fix imports.** Search for ``from openstef.`` and update each import to the
   corresponding V4 path. The table below maps the most common V3 imports to
   their V4 equivalents.

3. **Replace PredictionJobDataClass.** Identify every place a
   ``PredictionJobDataClass`` is constructed and replace it with a
   ``LocationConfig`` plus typed model/hyperparameter objects.

4. **Wrap DataFrames.** Find every ``pd.read_csv`` or DataFrame passed to a
   pipeline and wrap it in ``VersionedTimeSeriesDataset``.

5. **Rebuild the feature pipeline.** Replace implicit feature flags on the
   prediction job with an explicit list of transform objects.

6. **Replace pipeline calls.** Swap ``train_model_pipeline`` and
   ``create_forecast_pipeline`` calls for a ``CustomForecastingWorkflow``
   instance with an injected storage back-end.

7. **Replace MLflow storage.** Construct a ``LocalModelStorage`` with
   ``JoblibModelSerializer`` (or a custom back-end) and pass it to the
   workflow.

8. **Run your tests.** V4 ships with typed interfaces; a mypy pass after
   migration will surface remaining incompatibilities quickly.

----

Common Import Mapping
---------------------

The table below lists the most frequently used V3 symbols and their V4
equivalents:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - V3 import
     - V4 equivalent
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - ``openstef_models.presets.forecasting_workflow.LocationConfig`` + model config objects
   * - ``openstef.data_classes.model_specifications.ModelSpecificationDataClass``
     - Removed — hyperparameters live on the model class (e.g., ``XGBoostHyperParams``)
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow.train``
   * - ``openstef.pipeline.create_forecast.create_forecast_pipeline``
     - ``openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow.predict``
   * - ``openstef.model.regressors.xgb.XGBOpenstfRegressor``
     - ``openstef_models.models.forecasting.xgboost_forecaster.XGBoostForecaster``
   * - ``pandas.DataFrame`` (raw, passed to pipeline)
     - ``openstef_core.datasets.VersionedTimeSeriesDataset``

----

.. note::

   **Deployment patterns** for running V4 in production — including
   containerisation and scheduling — are covered in :doc:`deployment`.
   For configuring structured logging in V4 (the logging API also changed
   slightly), see :doc:`logging`.