Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant redesign of the library. It moves away from the database-coupled,
task-oriented architecture of V3 toward a modular, composable pipeline model that works
standalone — no ``openstef-dbc`` required. This page documents every breaking change you are
likely to encounter and shows you exactly how to update your code.

.. note::

   This guide focuses purely on the migration mechanics. For practical end-to-end examples
   using the new V4 API, see :doc:`use_cases`. For deploying V4 in production, see
   :doc:`deployment`.

----

What Changed and Why
--------------------

V3 was designed around a central database connector (``openstef-dbc``) that fetched data,
ran pipelines, and wrote results back automatically through *tasks*. This made the library
difficult to use outside that specific infrastructure. V4 removes that coupling entirely:

- **No more ``openstef-dbc`` dependency.** You own your data I/O.
- **No more ``PredictionJobDataClass``.** Configuration is expressed through typed model
  and pipeline objects.
- **Pandas DataFrames are no longer the primary data contract.** V4 introduces
  ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` as first-class data structures.
- **Pipelines are composable objects**, not module-level functions you call with a dict.
- **Package namespace is split** across ``openstef_core``, ``openstef_models``, and
  optional integration packages.

----

Package Structure Changes
--------------------------

The single ``openstef`` package of V3 has been replaced by a set of focused packages.

**Before (V3):**

.. code-block:: python

   # Everything lived in the openstef namespace
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from openstef.pipeline.train_create_forecast_backtest import (
       train_model_and_forecast_back_test,
   )

**After (V4):**

.. code-block:: python

   # Core data structures and abstractions
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Models, forecasters, and pipeline components
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )

   # High-level workflow orchestration
   from openstef_core.workflows import CustomForecastingWorkflow

   # Model persistence
   from openstef_models.integrations.joblib import JoblibModelSerializer

The key rule of thumb: **data structures and interfaces live in** ``openstef_core``;
**concrete model implementations live in** ``openstef_models``.

----

Breaking Change: PredictionJobDataClass Removed
------------------------------------------------

``PredictionJobDataClass`` (and its companion ``ModelSpecificationDataClass``) no longer
exist. In V3 they acted as a configuration dictionary passed into every pipeline function.
In V4, configuration is distributed across the objects that need it — the forecaster
receives its horizons and quantiles directly, and the pipeline is assembled from typed
components.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       lat=52.0,
       lon=5.0,
       forecast_type="demand",
       name="ExampleForecast",
       hyper_params={},
       feature_names=None,
   )
   modelspecs = ModelSpecificationDataClass(id=pj["id"])

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting_model import ForecastingModel

   # Horizons and quantiles are passed directly to the forecaster
   horizons = [LeadTime.from_string("PT24H"), LeadTime.from_string("PT47H")]
   quantiles = [Q(0.10), Q(0.30), Q(0.50), Q(0.70), Q(0.90)]

   forecaster = ConstantMedianForecaster(horizons=horizons, quantiles=quantiles)
   model = ForecastingModel(forecaster=forecaster)

There is no global configuration object. Each component declares what it needs.

----

Breaking Change: Data Input Format
------------------------------------

V3 pipelines accepted a plain ``pd.DataFrame`` with a ``load`` column and a
``DatetimeIndex``. V4 wraps time series data in a dedicated class that carries
metadata (sample interval, availability timestamps) needed for realistic backtesting
and multi-version datasets.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   # input_data is a plain DataFrame with a DatetimeIndex and a 'load' column

**After (V4):**

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   raw = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )

   dataset = TimeSeriesDataset(
       data=raw,
       sample_interval=timedelta(minutes=15),
   )

For backtesting scenarios where data arrives with delays or revisions, use
``VersionedTimeSeriesDataset`` instead — it solves the O(n²) memory problem that arose
when concatenating DataFrames with misaligned ``(timestamp, available_at)`` pairs.

----

Breaking Change: Training and Forecasting Pipelines
-----------------------------------------------------

V3 exposed ``train_model_pipeline()`` and ``create_forecast_pipeline()`` as module-level
functions. You called them with a prediction job dict and a DataFrame. V4 replaces these
with a ``CustomForecastingWorkflow`` object whose ``fit()`` and ``predict()`` methods
accept a ``TimeSeriesDataset``.

**Before (V3) — Training:**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   trained_model, report, modelspecs, train_data = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

**After (V4) — Training:**

.. code-block:: python

   from openstef_core.workflows import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(model=model, model_id="my_forecast_model")
   training_result = workflow.fit(dataset)

**Before (V3) — Forecasting:**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4) — Forecasting:**

.. code-block:: python

   forecasts = workflow.predict(dataset)

The workflow object holds the trained model in memory. If you need to persist and reload
it between runs, see the :ref:`model-storage` section below.

----

Breaking Change: Model Storage
--------------------------------

.. _model-storage:

V3 used MLflow as its model registry, configured via a URI string passed to each pipeline
call. V4 decouples storage from the pipeline: you choose a serializer and pass it to the
workflow as a callback, or use it directly.

**Before (V3):**

.. code-block:: python

   # MLflow URI was threaded through every pipeline call
   train_model_pipeline(
       pj, data, mlflow_tracking_uri="./mlflow_trained_models", ...
   )
   create_forecast_pipeline(
       pj, data, mlflow_tracking_uri="./mlflow_trained_models"
   )

**After (V4) — local file storage with Joblib:**

.. code-block:: python

   from pathlib import Path
   from openstef_models.integrations.joblib import JoblibModelSerializer
   from openstef_core.storage import LocalModelStorage

   storage = LocalModelStorage(
       path=Path("./trained_models"),
       serializer=JoblibModelSerializer(),
   )

   # Save a trained model
   storage.save_model("my_forecast_model", workflow.model)

   # Load it back later
   loaded_model = storage.load_model("my_forecast_model")

Storage is now a first-class concern that you configure once and pass around explicitly,
rather than an implicit side-effect of calling a pipeline function.

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate an existing V3 integration.

**Step 1 — Update your dependencies**

Remove ``openstef`` and ``openstef-dbc`` from your requirements. Add the V4 packages:

.. code-block:: text

   openstef-core>=4.0
   openstef-models>=4.0

**Step 2 — Replace all V3 imports**

Search your codebase for any import from the ``openstef`` namespace and update it using
the package structure table above. Pay particular attention to:

- ``openstef.data_classes.*`` → remove entirely; configuration moves to component constructors
- ``openstef.pipeline.*`` → replace with ``CustomForecastingWorkflow``
- ``openstef.model.*`` → replace with ``openstef_models.models.*``

**Step 3 — Replace PredictionJobDataClass construction**

Every place you build a ``PredictionJobDataClass`` dict, replace it with direct
instantiation of the forecaster and model objects, passing horizons and quantiles
as typed values.

**Step 4 — Wrap DataFrames in TimeSeriesDataset**

Anywhere you pass a raw DataFrame to a pipeline, wrap it in ``TimeSeriesDataset``
and supply the ``sample_interval``. For backtesting with point-in-time correctness,
migrate to ``VersionedTimeSeriesDataset``.

**Step 5 — Replace pipeline function calls with workflow methods**

Replace ``train_model_pipeline(pj, data, ...)`` with ``workflow.fit(dataset)`` and
``create_forecast_pipeline(pj, data, ...)`` with ``workflow.predict(dataset)``.

**Step 6 — Migrate model storage**

Replace MLflow URI arguments with an explicit ``LocalModelStorage`` (or your preferred
storage backend) and call ``storage.save_model()`` / ``storage.load_model()`` where
needed.

**Step 7 — Remove openstef-dbc task wrappers**

If you were using ``openstef-dbc`` tasks (``train_model_task``, ``create_forecast_task``,
etc.), these no longer exist. You are now responsible for fetching input data and writing
forecast output yourself. See :doc:`data_integration` for patterns covering S3,
Databricks, and InfluxDB sources.

----

Complete Before/After Example
-------------------------------

The following shows a minimal but complete train-then-forecast flow in both versions.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.10, 0.50, 0.90],
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       lat=52.0,
       lon=5.0,
       forecast_type="demand",
       name="MyForecast",
       hyper_params={},
       feature_names=None,
   )

   input_data = pd.read_csv("data/load_data.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200]
   forecast_data = input_data.copy()
   forecast_data.iloc[-200:, forecast_data.columns.get_loc("load")] = float("nan")

   train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_models",
       artifact_folder="./mlflow_models",
   )

   forecast = create_forecast_pipeline(
       pj,
       forecast_data,
       mlflow_tracking_uri="./mlflow_models",
   )
   print(forecast.head())

**After (V4):**

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_core.workflows import CustomForecastingWorkflow
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting_model import ForecastingModel

   # 1. Load data and wrap in the V4 data structure
   raw = pd.read_csv("data/load_data.csv", index_col="index", parse_dates=True)
   dataset = TimeSeriesDataset(data=raw, sample_interval=timedelta(minutes=15))

   # 2. Build the model — configuration lives on the components, not a dict
   horizons = [LeadTime.from_string("PT47H")]
   quantiles = [Q(0.10), Q(0.50), Q(0.90)]
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(horizons=horizons, quantiles=quantiles)
   )

   # 3. Create a workflow and train
   workflow = CustomForecastingWorkflow(model=model, model_id="my_forecast_model")
   workflow.fit(dataset)

   # 4. Generate forecasts
   forecasts = workflow.predict(dataset)
   print(forecasts.data.head())

----

.. note::

   If you use custom feature engineering, preprocessing transforms, or postprocessing
   steps (e.g. confidence interval applicators), these are now expressed as
   ``FeaturePipeline`` and ``TransformPipeline`` objects passed to ``ForecastingModel``.
   Refer to the API reference for ``openstef_models.models.forecasting_model`` for the
   full constructor signature.

.. note::

   Logging configuration has not changed structurally, but V4 uses structured log fields
   that align with the new component model. See :doc:`logging` for recommended log-level
   setup and custom handler patterns.