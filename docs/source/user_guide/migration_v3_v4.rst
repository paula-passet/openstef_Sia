Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant architectural redesign of the library. It moves away from a
database-coupled, monolithic pipeline model toward a modular, standalone package ecosystem.
This guide covers every category of breaking change, explains the reasoning behind each
decision, and provides concrete before/after code examples so you can migrate incrementally.

.. note::

   V3 and V4 are **not** API-compatible. Running V3 code against the V4 packages will raise
   ``ImportError`` or ``AttributeError`` at runtime. Work through this guide section by
   section rather than attempting a bulk find-and-replace.

.. contents:: On this page
   :local:
   :depth: 2

----

Overview of What Changed
-------------------------

V4 reorganises OpenSTEF from a single ``openstef`` wheel into a family of focused packages.
The table below summarises the high-level shifts:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Concern
     - V3
     - V4
   * - Package layout
     - Single ``openstef`` package
     - ``openstef-core``, ``openstef-models``, ``openstef-beam``, …
   * - Job configuration
     - ``PredictionJobDataClass`` + ``ModelSpecificationDataClass``
     - ``BaseConfig`` / plain dataclasses per component
   * - Data representation
     - ``pandas.DataFrame`` throughout
     - ``VersionedTimeSeriesDataset``
   * - Pipeline entry point
     - ``train_model_pipeline(pj, df, ...)``
     - ``ForecastingModel`` + ``ForecastingWorkflow``
   * - Model storage
     - MLflow (mandatory)
     - Pluggable ``ModelStorage`` (``LocalModelStorage``, custom)
   * - Database integration
     - ``openstef-dbc`` tightly coupled
     - Fully decoupled; bring your own data layer
   * - Feature engineering
     - Implicit, inside pipeline
     - Explicit ``FeaturePipeline`` composed by the caller

----

Package Structure Changes
--------------------------

In V3 everything lived under the ``openstef`` namespace::

   openstef.pipeline.train_model
   openstef.pipeline.create_forecast
   openstef.model.regressors.xgb
   openstef.data_classes.prediction_job

V4 distributes responsibilities across separate installable packages:

- **openstef-core** — abstract base classes, dataset types, exceptions, and the
  ``Predictor`` / ``Stateful`` interfaces.
- **openstef-models** — concrete ``ForecastingModel``, built-in forecasters (XGBoost,
  LightGBM, …), feature pipelines, and model storage integrations.
- **openstef-beam** — Apache Beam runners for large-scale distributed forecasting,
  including analysis and plotting utilities.

Install only what you need:

.. code-block:: bash

   # Minimal: core abstractions + models
   pip install openstef-core openstef-models

   # Add distributed execution support
   pip install openstef-beam

.. warning::

   The old ``openstef`` package on PyPI is the V3 release. Installing it alongside
   V4 packages in the same environment will cause import conflicts. Use a fresh
   virtual environment when migrating.

----

.. _breaking-change-1:

Breaking Change 1 — PredictionJob Removed
------------------------------------------

V3 centred every operation on ``PredictionJobDataClass``, a large dict-like object that
bundled model hyperparameters, horizon settings, and metadata into one structure.
V4 removes this concept entirely. Configuration is now expressed through typed,
component-specific dataclasses and constructor arguments.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       horizon_minutes=48 * 60,
       resolution_minutes=15,
       lat=52.0,
       lon=4.0,
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
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.forecasters.xgb import XGBQuantileForecaster
   from openstef_core.datasets.time_series import LeadTime, Q

   horizons = [LeadTime.from_string("PT48H")]
   quantiles = [Q(0.10), Q(0.30), Q(0.50), Q(0.70), Q(0.90)]

   model = ForecastingModel(
       forecaster=XGBQuantileForecaster(
           horizons=horizons,
           quantiles=quantiles,
       )
   )

The key difference: in V4 each concern (forecaster type, quantiles, horizons) is a
constructor argument on the relevant component rather than a field on a shared job object.
There is no global ``id`` or ``name`` field on the model itself — those belong to the
storage layer (see :ref:`breaking-change-3` below).

----

.. _breaking-change-2:

Breaking Change 2 — DataFrame Replaced by VersionedTimeSeriesDataset
----------------------------------------------------------------------

V3 pipelines accepted and returned plain ``pandas.DataFrame`` objects. V4 introduces
``VersionedTimeSeriesDataset``, a typed wrapper that carries the data together with its
``sample_interval`` and version metadata. This makes temporal alignment errors detectable
at construction time rather than silently producing wrong forecasts.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   input_data = pd.read_csv(
       "data/load_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   # DataFrame passed directly to pipeline
   train_data, validation_data, test_data = train_model_pipeline(
       pj, input_data, check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.time_series import VersionedTimeSeriesDataset

   raw = pd.read_csv("data/load_pid_287.csv", index_col="index", parse_dates=True)

   dataset = VersionedTimeSeriesDataset(
       data=raw,
       sample_interval=timedelta(minutes=15),
   )

``VersionedTimeSeriesDataset`` is the currency of the entire V4 API: it is what you pass
to ``workflow.fit()``, what ``workflow.predict()`` accepts, and what feature pipelines
transform. Anywhere V3 expected a ``DataFrame``, V4 expects a dataset object.

----

.. _breaking-change-3:

Breaking Change 3 — Pipeline Functions Replaced by Workflow Objects
---------------------------------------------------------------------

V3 exposed top-level pipeline functions (``train_model_pipeline``,
``create_forecast_pipeline``, ``train_model_and_forecast_back_test``). V4 replaces these
with the ``ForecastingWorkflow`` / ``CustomForecastingWorkflow`` classes, which encapsulate
the same logic but support callbacks, pluggable storage, and reuse across train/predict
cycles.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Training
   train_data, validation_data, test_data = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

   # Forecasting
   forecast = create_forecast_pipeline(
       pj, input_data, mlflow_tracking_uri="./mlflow_trained_models"
   )

**After (V4):**

.. code-block:: python

   from openstef_models.workflows.forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingWorkflow,
       ForecastingCallback,
   )
   from openstef_models.storage.local import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(Path("./trained_models"))

   # Optional: attach callbacks for logging, monitoring, etc.
   class TrainingLogger(ForecastingCallback):
       def on_fit_end(self, context, result):
           print("Training complete")

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="load_forecast_287",
       storage=storage,
       callbacks=[TrainingLogger()],
   )

   # Training
   workflow.fit(dataset)

   # Forecasting
   forecasts = workflow.predict(dataset)

To reload a previously saved model from storage:

.. code-block:: python

   workflow = ForecastingWorkflow.from_storage(
       model_id="load_forecast_287",
       storage=storage,
   )
   forecasts = workflow.predict(dataset)

----

.. _breaking-change-4:

Breaking Change 4 — MLflow No Longer Mandatory
------------------------------------------------

V3 hard-wired MLflow as the model store; every pipeline call required
``mlflow_tracking_uri`` and ``artifact_folder`` arguments. V4 introduces a
``ModelStorage`` abstraction with pluggable backends.

**Before (V3):**

.. code-block:: python

   train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.storage.local import LocalModelStorage
   from openstef_models.integrations.joblib import JoblibModelSerializer
   from pathlib import Path

   # Local filesystem (development / single-machine)
   storage = LocalModelStorage(
       path=Path("./trained_models"),
       serializer=JoblibModelSerializer(),
   )

MLflow remains available as an optional integration, but it is no longer a required
dependency. For production storage patterns (S3, Databricks), see
:doc:`data_integration`.

----

.. _breaking-change-5:

Breaking Change 5 — Feature Engineering is Now Explicit
---------------------------------------------------------

V3 applied feature engineering (lag features, holiday flags, weather variables) silently
inside the pipeline based on ``PredictionJobDataClass`` fields. V4 makes this explicit
through a composable ``FeaturePipeline`` that you construct and attach to the
``ForecastingModel``.

**Before (V3):**

.. code-block:: python

   # Feature engineering happened automatically based on pj fields:
   # pj['feature_names'], pj['train_components'], etc.
   train_model_pipeline(pj, input_data, ...)

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   from openstef_models.features.pipeline import FeaturePipeline
   from openstef_models.features.transforms import (
       HolidayFeatures,
       LagTransform,
       StandardScaler,
   )

   feature_pipeline = FeaturePipeline(
       transforms=[
           HolidayFeatures(country="NL"),
           LagTransform(lags=[timedelta(hours=24), timedelta(hours=168)]),
           StandardScaler(),
       ]
   )

   model = ForecastingModel(
       forecaster=my_forecaster,
       feature_pipeline=feature_pipeline,
   )

This change makes it straightforward to add, remove, or reorder preprocessing steps
without subclassing anything.

----

Step-by-Step Migration Workflow
---------------------------------

Work through these steps in order. Each step is independently testable.

**Step 1 — Update your environment**

.. code-block:: bash

   pip uninstall openstef openstef-dbc
   pip install openstef-core openstef-models

**Step 2 — Replace PredictionJobDataClass**

Find every instantiation of ``PredictionJobDataClass`` and
``ModelSpecificationDataClass``. Replace them with direct constructor arguments on the
relevant V4 component (forecaster, feature pipeline, workflow). See
:ref:`breaking-change-1` above.

**Step 3 — Wrap your DataFrames**

Find every ``pd.read_csv`` / ``pd.DataFrame`` that feeds a pipeline. Wrap the result in
``VersionedTimeSeriesDataset``, supplying the correct ``sample_interval``. See
:ref:`breaking-change-2` above.

**Step 4 — Replace pipeline function calls**

Replace calls to ``train_model_pipeline`` and ``create_forecast_pipeline`` with a
``CustomForecastingWorkflow`` instance. See :ref:`breaking-change-3` above.

**Step 5 — Choose a storage backend**

Replace ``mlflow_tracking_uri`` / ``artifact_folder`` arguments with a ``ModelStorage``
instance. ``LocalModelStorage`` is the simplest starting point. See
:ref:`breaking-change-4` above.

**Step 6 — Make feature engineering explicit**

Review any ``feature_names`` or ``train_components`` fields on your old prediction jobs
and translate them into a ``FeaturePipeline``. See :ref:`breaking-change-5` above.

**Step 7 — Run your test suite**

V4 raises typed exceptions from ``openstef_core.exceptions``. Update any ``except``
clauses that caught V3-specific exception types.

.. note::

   [DIAGRAM: Side-by-side flowchart — V3 pipeline (PredictionJob → train_model_pipeline → MLflow)
   vs V4 pipeline (VersionedTimeSeriesDataset → ForecastingModel + FeaturePipeline →
   ForecastingWorkflow → ModelStorage)]

----

Quick Reference: Import Path Changes
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - V3 import
     - V4 replacement
   * - ``from openstef.data_classes.prediction_job import PredictionJobDataClass``
     - Removed — use component constructors directly
   * - ``from openstef.data_classes.model_specifications import ModelSpecificationDataClass``
     - Removed — use component constructors directly
   * - ``from openstef.pipeline.train_model import train_model_pipeline``
     - ``from openstef_models.workflows.forecasting_workflow import CustomForecastingWorkflow``
   * - ``from openstef.pipeline.create_forecast import create_forecast_pipeline``
     - ``from openstef_models.workflows.forecasting_workflow import ForecastingWorkflow``
   * - ``from openstef.model.regressors.xgb import XGBQuantileRegressor``
     - ``from openstef_models.forecasters.xgb import XGBQuantileForecaster``
   * - ``from openstef.model.serializer import MLflowSerializer``
     - ``from openstef_models.integrations.joblib import JoblibModelSerializer``

----

Related Pages
--------------

- :doc:`use_cases` — End-to-end examples (congestion forecasting, etc.) written against
  the V4 API.
- :doc:`data_integration` — How to read training data from S3, Databricks, and InfluxDB
  using the V4 data layer.
- :doc:`deployment` — Production deployment patterns (containerised workers, Beam
  pipelines) using V4 packages.
- :doc:`logging` — Configuring structured logging with V4's updated log levels and
  handlers.