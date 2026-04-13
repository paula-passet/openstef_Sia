Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant rewrite of the library. The core forecasting concepts remain the same — you still define a job, supply time series data, train a model, and produce a forecast — but almost every API surface has changed. This page documents the breaking changes, explains what replaced what, and provides side-by-side before/after code examples to help you migrate an existing V3 codebase.

.. note::

   V3 and V4 are **not** import-compatible. You cannot mix V3 and V4 calls in the same
   codebase. Plan for a full cut-over rather than an incremental migration.

.. contents:: On this page
   :local:
   :depth: 2

----

Overview of What Changed
------------------------

V4 was redesigned around three goals: making OpenSTEF a cleaner standalone library
(removing the hard dependency on ``openstef-dbc``), replacing ad-hoc dict-like data
structures with typed, composable objects, and aligning the pipeline API with
scikit-learn conventions. The table below summarises the highest-impact changes.

.. list-table::
   :header-rows: 1
   :widths: 35 35 30

   * - V3 concept
     - V4 replacement
     - Notes
   * - ``PredictionJobDataClass``
     - ``ForecastingModel`` + config objects
     - Job config is now split across typed dataclasses
   * - ``ModelSpecificationDataClass``
     - ``ModelConfig`` / ``ForecastingWorkflowConfig``
     - Merged into workflow configuration
   * - ``train_model_pipeline()``
     - ``CustomForecastingWorkflow.train()``
     - Workflow object owns the full lifecycle
   * - ``create_forecast_pipeline()``
     - ``CustomForecastingWorkflow.predict()``
     - Same workflow object used for inference
   * - ``pandas.DataFrame`` (raw input)
     - ``VersionedTimeSeriesDataset``
     - Typed dataset with interval metadata
   * - ``openstef-dbc`` tasks
     - Standalone pipelines only
     - Database layer is your responsibility in V4
   * - MLflow via ``mlflow_tracking_uri`` kwarg
     - ``MLFlowStorageCallback``
     - Persistence is opt-in via callbacks
   * - Feature engineering helpers (individual imports)
     - ``FeaturePipeline`` / ``LagsAdder`` / ``HolidayFeatureAdder``
     - Composable transform objects

----

Package Structure Changes
--------------------------

V3 shipped as a single ``openstef`` package. V4 splits the library into focused
sub-packages, each installable independently.

**Before (V3) — single package:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.feature_engineering.lag_features import generate_lag_feature_functions
   from openstef.feature_engineering.holiday_features import (
       generate_holiday_feature_functions,
   )

**After (V4) — modular sub-packages:**

.. code-block:: python

   # Core abstractions
   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset

   # Model building blocks
   from openstef_models.model import ForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.transforms import FeaturePipeline
   from openstef_models.transforms.lags import LagsAdder
   from openstef_models.transforms.holidays import HolidayFeatureAdder
   from openstef_models.storage import LocalModelStorage

The key sub-packages and their responsibilities are:

- ``openstef-core`` — base classes, dataset types, interfaces
- ``openstef-models`` — forecasting models, pipelines, workflows, transforms
- ``openstef-beam`` — Apache Beam runners for large-scale batch processing (optional)

.. note::

   Install only what you need. A standalone training/inference script requires
   ``openstef-core`` and ``openstef-models``. The ``openstef-beam`` package is only
   needed for distributed execution.

----

.. _breaking-change-1:

Breaking Change 1: Prediction Job Configuration
-------------------------------------------------

In V3, a *prediction job* was a ``PredictionJobDataClass`` instance (essentially a
validated dict) that was threaded through every pipeline call. In V4, configuration is
expressed through typed dataclasses and is embedded inside the ``ForecastingModel``
and ``CustomForecastingWorkflow`` objects at construction time.

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
       train_components=False,
       name="TestPrediction",
       model_type_group=None,
       hyper_params={},
       feature_names=None,
       forecast_type="demand",
   )
   modelspecs = ModelSpecificationDataClass(id=pj["id"])

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_models.workflows.config import ForecastingWorkflowConfig

   # Configuration is a typed dataclass — no more dict-like access
   config = ForecastingWorkflowConfig(
       model_id="prediction-287",
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       horizons=[timedelta(hours=h) for h in range(1, 48)],
       target_column="load",
   )

Key differences to note:

- ``horizon_minutes`` (a single integer) becomes ``horizons`` (a list of
  ``timedelta`` objects), allowing multi-horizon training in a single pass.
- ``resolution_minutes`` is no longer specified in the job — it is inferred from the
  ``VersionedTimeSeriesDataset`` you supply.
- ``ModelSpecificationDataClass`` is gone entirely; its role is absorbed into the
  workflow configuration and the ``ForecastingModel`` constructor.
- Fields are accessed as attributes (``config.model``), not dict keys
  (``pj["model"]``).

----

.. _breaking-change-2:

Breaking Change 2: Input Data Format
--------------------------------------

In V3 pipelines accepted a plain ``pandas.DataFrame`` with a ``DatetimeIndex`` and a
``load`` column. V4 wraps the same data in a ``VersionedTimeSeriesDataset``, which
carries the sample interval as metadata and supports multi-version datasets for
backtesting.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   # DataFrame passed directly to pipeline
   train_model_pipeline(pj, input_data, ...)

**After (V4):**

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   raw = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="timestamp",
       parse_dates=True,
   )

   # Wrap in a typed dataset — sample_interval is required
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw,
       sample_interval=timedelta(minutes=15),
   )

   # Dataset is passed to the workflow, not the pipeline function
   workflow.train(dataset)

The ``from_dataframe`` constructor validates that the index is a ``DatetimeIndex``
and that the data is consistent with the declared ``sample_interval``. This catches
common data quality issues — missing timestamps, irregular spacing — that previously
surfaced as silent errors deep inside the V3 pipeline.

----

Breaking Change 3: Training and Forecasting Pipelines
-------------------------------------------------------

V3 exposed ``train_model_pipeline()`` and ``create_forecast_pipeline()`` as top-level
functions. In V4, these are methods on a ``CustomForecastingWorkflow`` object that you
construct once and reuse for both training and inference.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import numpy as np

   # Train
   train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

   # Forecast — NaN out the future load values to signal "to be predicted"
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan
   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path
   from openstef_models.model import ForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage import LocalModelStorage
   from openstef_models.transforms import FeaturePipeline
   from openstef_models.transforms.lags import LagsAdder
   from openstef_models.transforms.holidays import HolidayFeatureAdder
   from openstef_models.forecasters.xgb import XGBQuantileForecaster

   # Build the model once — preprocessing and postprocessing are explicit
   model = ForecastingModel(
       preprocessing=FeaturePipeline(
           transforms=[
               HolidayFeatureAdder(country="NL"),
               LagsAdder(
                   history_available=timedelta(days=14),
                   horizons=[timedelta(hours=h) for h in range(1, 48)],
               ),
           ]
       ),
       forecaster=XGBQuantileForecaster(
           quantiles=[0.10, 0.30, 0.50, 0.70, 0.90]
       ),
       target_column="load",
   )

   storage = LocalModelStorage(Path("./trained_models"))
   workflow = CustomForecastingWorkflow(model=model, model_id="prediction-287")

   # Train
   workflow.train(dataset)
   storage.save_model("prediction-287", model)

   # Predict — no NaN sentinel values needed
   loaded_model = storage.load_model("prediction-287")
   predict_workflow = CustomForecastingWorkflow(
       model=loaded_model, model_id="prediction-287"
   )
   forecast = predict_workflow.predict(predict_dataset)

Notable changes:

- Feature engineering is no longer implicit. In V3, the pipeline silently applied lag
  features and weather-derived features based on the prediction job config. In V4, you
  declare every transform explicitly in the ``FeaturePipeline``. This is more verbose
  but makes the data flow transparent and testable.
- The NaN-sentinel pattern (setting future load to ``NaN`` to mark it as the forecast
  target) is gone. V4 uses the dataset's ``available_at`` metadata to determine what
  is observable at prediction time.
- MLflow integration is opt-in via ``MLFlowStorageCallback`` rather than a kwarg on
  the pipeline function. See :doc:`deployment` for details on configuring callbacks
  in production.

----

Breaking Change 4: ``openstef-dbc`` Dependency
------------------------------------------------

V3 provided a ``tasks`` module (``openstef.tasks.train_model``,
``openstef.tasks.create_forecast``, etc.) that coupled the library to ``openstef-dbc``
for database I/O. This pattern looked like:

**Before (V3):**

.. code-block:: python

   from openstef.tasks import train_model as task
   from openstef_dbc.database import DataBase
   from openstef_dbc.log import logging

   def main():
       logging.configure_logging(loglevel=config.loglevel, runtime_env=config.env)
       database = DataBase(config)
       task.main(config=config, database=database)

   if __name__ == "__main__":
       main()

**After (V4):**

The ``openstef.tasks`` module and the ``openstef-dbc`` dependency are **removed** from
the V4 library. Data loading and writing is now entirely your responsibility. OpenSTEF
provides the forecasting logic; you provide the I/O layer. A minimal replacement
pattern is:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   def load_from_your_database(prediction_id: str) -> pd.DataFrame:
       # Replace with your actual data source
       ...

   raw = load_from_your_database("prediction-287")
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw, sample_interval=timedelta(minutes=15)
   )

   workflow = CustomForecastingWorkflow(model=model, model_id="prediction-287")
   workflow.train(dataset)

For patterns covering S3, Databricks, and InfluxDB data sources, see
:doc:`data_integration`.

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate a V3 project to V4.

**Step 1 — Update your dependencies**

Remove ``openstef`` and ``openstef-dbc`` from your ``requirements.txt`` or
``pyproject.toml`` and replace them with the V4 sub-packages:

.. code-block:: text

   # Remove:
   openstef>=3.x
   openstef-dbc>=3.x

   # Add:
   openstef-core>=4.0
   openstef-models>=4.0

**Step 2 — Replace ``PredictionJobDataClass`` with workflow configuration**

Search your codebase for ``PredictionJobDataClass`` and ``ModelSpecificationDataClass``
instantiations. Replace each one with a ``ForecastingWorkflowConfig`` as described in
the *Prediction Job Configuration* section above. Pay particular attention to
``horizon_minutes`` → ``horizons`` (list of ``timedelta``) and ``resolution_minutes``
(now inferred from the dataset).

**Step 3 — Wrap your DataFrames in ``VersionedTimeSeriesDataset``**

Anywhere you pass a ``pd.DataFrame`` to a V3 pipeline, wrap it first:

.. code-block:: python

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       df, sample_interval=timedelta(minutes=resolution_minutes)
   )

**Step 4 — Replace pipeline function calls with workflow methods**

Replace ``train_model_pipeline(pj, data, ...)`` with ``workflow.train(dataset)`` and
``create_forecast_pipeline(pj, data, ...)`` with ``workflow.predict(dataset)``. Build
the ``CustomForecastingWorkflow`` once and reuse it.

**Step 5 — Make feature engineering explicit**

If your V3 code relied on the pipeline's implicit feature engineering, you must now
declare those transforms in a ``FeaturePipeline``. Audit which features your trained
model actually used (check MLflow artifacts or model feature importance) and add the
corresponding ``LagsAdder``, ``HolidayFeatureAdder``, or weather feature transforms
to your pipeline.

**Step 6 — Replace task-based I/O**

Remove all ``openstef.tasks.*`` imports and ``openstef-dbc`` calls. Implement your own
data loading functions and call the V4 workflow methods directly. See
:doc:`data_integration` for practical patterns.

**Step 7 — Update model persistence**

Replace ``mlflow_tracking_uri`` kwargs with a ``LocalModelStorage`` or
``MLFlowStorageCallback``. Saved V3 models are not compatible with V4 — you will need
to retrain from scratch.

.. warning::

   Models serialised by V3 (via MLflow + joblib) cannot be loaded by V4's
   ``LocalModelStorage`` or ``JoblibModelSerializer``. Plan a retraining run as part
   of your migration. If you need to serve V3 models during a transition period, keep
   a separate V3 environment running in parallel.

----

Common Migration Errors
------------------------

The following errors appear frequently when migrating V3 code.

``ImportError: cannot import name 'PredictionJobDataClass'``
   This class no longer exists. Replace it with ``ForecastingWorkflowConfig`` as
   described in the *Prediction Job Configuration* section above.

``TypeError: train_model_pipeline() got an unexpected keyword argument``
   The V3 pipeline functions are removed. Replace the call with
   ``CustomForecastingWorkflow.train()``.

``AttributeError: 'DataFrame' object has no attribute 'sample_interval'``
   You are passing a raw ``pd.DataFrame`` where a ``VersionedTimeSeriesDataset`` is
   expected. Wrap your data as described in the *Input Data Format* section above.

``ModuleNotFoundError: No module named 'openstef_dbc'``
   Remove the ``openstef-dbc`` dependency and replace task-based I/O with your own
   data loading code.

----

Related Pages
-------------

- :doc:`use_cases` — practical end-to-end examples using the V4 API
- :doc:`data_integration` — connecting V4 pipelines to S3, Databricks, and InfluxDB
- :doc:`deployment` — production deployment patterns including callback configuration
- :doc:`logging` — configuring logging in V4 (the ``openstef_dbc`` logging helper is gone)