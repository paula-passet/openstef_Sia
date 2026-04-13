Migration Guide: V3 to V4
=========================

OpenSTEF V4 is a significant architectural redesign of the library. It moves away from a
monolithic package with tight database coupling toward a modular, multi-package structure
that can be embedded cleanly into any Python project. This guide covers every breaking
change you are likely to encounter and provides concrete before/after code examples to
help you migrate existing V3 code.

.. note::

   If you are starting a new project, use V4 directly and skip this guide. The
   :doc:`use_cases` page shows idiomatic V4 patterns for common forecasting scenarios.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 was built around a single ``openstef`` package whose high-level *tasks* assumed a
database connection (provided by the companion ``openstef-dbc`` package) and whose
pipelines returned raw ``pandas.DataFrame`` objects. This design made the library
difficult to use outside of the original operational context.

V4 replaces this with a family of focused packages:

- **openstef-core** — base abstractions: datasets, model interfaces, configuration types
- **openstef-models** — concrete forecasting models, feature pipelines, and workflows
- **openstef-beam** — Apache Beam runners for large-scale distributed forecasting

The key conceptual shifts are:

- ``PredictionJobDataClass`` / ``ModelSpecificationDataClass`` → replaced by typed
  ``BaseConfig`` subclasses (``ForecastingWorkflowConfig``, ``LocationConfig``, etc.)
- ``pd.DataFrame`` as the universal data container → replaced by
  ``VersionedTimeSeriesDataset``
- MLflow-coupled model storage → replaced by a pluggable ``ModelStorage`` interface
  (``LocalModelStorage``, ``JoblibModelSerializer``, …)
- Database-aware *tasks* → removed; data access is your responsibility (see
  :doc:`data_integration`)
- High-level ``train_model_pipeline`` / ``create_forecast_pipeline`` functions →
  replaced by ``CustomForecastingWorkflow``

----

Package Installation
--------------------

**Before (V3):**

.. code-block:: bash

   pip install openstef

**After (V4):**

.. code-block:: bash

   # Core abstractions + the models package covers most use cases
   pip install openstef-core openstef-models

   # Add the Beam runner only if you need distributed execution
   pip install openstef-beam

----

Import Paths
------------

Almost every import path changes in V4. The table below shows the most common V3
imports and their V4 equivalents.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - V3 import
     - V4 import
   * - ``from openstef.data_classes.prediction_job import PredictionJobDataClass``
     - ``from openstef_models.presets.forecasting_workflow import ForecastingWorkflowConfig``
   * - ``from openstef.data_classes.model_specifications import ModelSpecificationDataClass``
     - ``from openstef_models.models.forecasting_model import ForecastingModel``
   * - ``from openstef.pipeline.train_model import train_model_pipeline``
     - ``from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow``
   * - ``from openstef.pipeline.create_forecast import create_forecast_pipeline``
     - ``from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow``
   * - ``from openstef.pipeline.train_create_forecast_backtest import train_model_and_forecast_back_test``
     - Use ``CustomForecastingWorkflow`` with a held-out split
   * - ``from openstef.metrics.figure import plot_feature_importance``
     - ``from openstef_beam.analysis.plots import ...`` (or use workflow callbacks)

----

Defining a Prediction Job
--------------------------

In V3, a *prediction job* was a dictionary-like dataclass that bundled every
configuration option — model type, horizon, quantiles, location — into one object.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   import pandas as pd

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.05, 0.10, 0.30, 0.50, 0.70, 0.90, 0.95],
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       lat=52.0,
       lon=5.0,
       name="TestPrediction",
       forecast_type="demand",
       hyper_params={},
       feature_names=None,
       train_components=False,
       model_type_group=None,
       description="description",
   )

   modelspecs = ModelSpecificationDataClass(id=pj["id"])

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )

**After (V4):**

.. code-block:: python

   import numpy as np
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )

   config = ForecastingWorkflowConfig(
       location=LocationConfig(lat=52.0, lon=5.0, name="TestPrediction"),
       model="xgb",
       quantiles=[0.05, 0.10, 0.30, 0.50, 0.70, 0.90, 0.95],
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       forecast_type="demand",
   )

   # Data is now wrapped in a typed dataset rather than a bare DataFrame
   raw = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   dataset = VersionedTimeSeriesDataset(data=raw)

The ``ForecastingWorkflowConfig`` is a ``BaseConfig`` subclass, so it is fully typed and
validated at construction time. Fields that were silently ignored in V3 (e.g. passing an
unknown key to the dict) now raise a validation error immediately.

----

Training a Model
----------------

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   # Returns (model, report, modelspecs, train/val/test DataFrames)
   model, report, modelspecs, data_splits = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from pathlib import Path
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.integrations.joblib import JoblibModelSerializer
   from openstef_core.model_storage import LocalModelStorage
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # Build the workflow from config (creates model + feature pipeline internally)
   workflow = create_forecasting_workflow(config)

   # Attach persistent storage (optional but recommended)
   storage = LocalModelStorage(
       Path("./trained_models"),
       serializer=JoblibModelSerializer(),
   )
   workflow = CustomForecastingWorkflow(workflow.model, storage=storage)

   # Train — dataset replaces the bare DataFrame
   workflow.fit(dataset)

The V4 workflow handles feature engineering, validation splits, and model persistence
internally. You no longer need to manage ``mlflow_tracking_uri`` or ``artifact_folder``
arguments; storage is configured once on the workflow object.

----

Generating a Forecast
---------------------

**Before (V3):**

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Mask the load column to signal "these are the timesteps to forecast"
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   # The same workflow object is used for both training and prediction
   # Pass a dataset whose target column contains NaN for future timesteps
   forecast_dataset = VersionedTimeSeriesDataset(data=to_forecast_df)

   forecasts = workflow.predict(forecast_dataset)
   # forecasts is a typed result object; access the DataFrame via forecasts.data

The workflow automatically loads the persisted model if ``storage`` is configured, so
you can call ``predict`` in a separate process without re-training.

----

Running a Backtest
------------------

V3 exposed a dedicated ``train_model_and_forecast_back_test`` pipeline. V4 does not
ship a separate backtest pipeline; instead you construct a held-out split manually and
call the workflow's ``fit`` / ``predict`` methods.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_create_forecast_backtest import (
       train_model_and_forecast_back_test,
   )

   forecast, model, train_data, validation_data, test_data = (
       train_model_and_forecast_back_test(
           pj,
           modelspecs,
           input_data,
           training_horizons=[0.25, 47.0],
       )
   )

**After (V4):**

.. code-block:: python

   from datetime import timedelta

   # Split manually — last 48 hours as test set
   cutoff = dataset.data.index[-200]
   train_dataset = VersionedTimeSeriesDataset(data=dataset.data.loc[:cutoff])
   test_df = dataset.data.loc[cutoff:].copy()
   test_df["load"] = np.nan
   test_dataset = VersionedTimeSeriesDataset(data=test_df)

   workflow.fit(train_dataset)
   backtest_forecasts = workflow.predict(test_dataset)

This approach gives you full control over the split strategy and is compatible with
cross-validation loops.

----

Model Storage
-------------

V3 used MLflow as the only storage backend, configured via URI strings passed directly
to pipeline functions. V4 introduces a ``ModelStorage`` interface with swappable
backends.

**Before (V3):**

.. code-block:: python

   # Storage was implicit — pipelines wrote to MLflow automatically
   train_model_pipeline(
       pj, data,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from openstef_core.model_storage import LocalModelStorage
   from openstef_models.integrations.joblib import JoblibModelSerializer

   # Local filesystem (development / single-machine)
   storage = LocalModelStorage(
       Path("./trained_models"),
       serializer=JoblibModelSerializer(),
   )

   workflow = CustomForecastingWorkflow(forecasting_model, storage=storage)
   workflow.fit(dataset)                      # saves automatically
   loaded_workflow = CustomForecastingWorkflow(forecasting_model, storage=storage)
   loaded_workflow.predict(forecast_dataset)  # loads automatically

For S3 or Databricks-backed storage, see :doc:`data_integration`.

----

Removed Features
----------------

The following V3 features have no direct V4 equivalent:

- **openstef-dbc integration** — The ``tasks`` layer (``openstef.tasks.*``) that
  fetched and wrote data via ``openstef-dbc`` is removed entirely. Data access is now
  your responsibility. See :doc:`data_integration` for patterns.
- **Component forecasting pipeline** — ``create_component_forecast_pipeline`` (solar /
  wind / usage decomposition) is not yet ported to V4.
- **Basecase forecast pipeline** — ``create_basecase_forecast_pipeline`` is not yet
  ported to V4.
- **Hyperparameter optimisation pipeline** — ``optimize_hyperparameters_pipeline`` is
  not yet ported to V4.

.. note::

   If your workflow depends on any of the removed pipelines, consider pinning to V3
   while the V4 equivalents are developed, or open an issue on the OpenSTEF GitHub
   repository.

----

Step-by-Step Migration Checklist
---------------------------------

Work through the following steps in order when migrating a V3 codebase:

1. **Update dependencies** — replace ``openstef`` with ``openstef-core`` and
   ``openstef-models`` in your ``requirements.txt`` or ``pyproject.toml``.

2. **Replace imports** — use the import mapping table above to update every
   ``from openstef.*`` import.

3. **Replace PredictionJobDataClass** — convert each prediction job dict to a
   ``ForecastingWorkflowConfig``. Pay attention to renamed fields (e.g.
   ``horizon_minutes`` is preserved, but ``model_type_group`` is removed).

4. **Wrap DataFrames in VersionedTimeSeriesDataset** — every place you passed a
   ``pd.DataFrame`` to a pipeline function, wrap it first:
   ``dataset = VersionedTimeSeriesDataset(data=df)``.

5. **Replace pipeline calls with workflow methods** — swap
   ``train_model_pipeline(pj, data, ...)`` for ``workflow.fit(dataset)`` and
   ``create_forecast_pipeline(pj, data, ...)`` for ``workflow.predict(dataset)``.

6. **Configure storage explicitly** — replace MLflow URI arguments with a
   ``LocalModelStorage`` (or other backend) attached to the workflow.

7. **Remove openstef-dbc task calls** — rewrite data fetching and writing using your
   own database clients. See :doc:`data_integration` for guidance.

8. **Run your test suite** — V4 raises validation errors eagerly on misconfigured
   objects, so many silent V3 bugs will surface as exceptions during construction.

----

Related Pages
-------------

- :doc:`use_cases` — idiomatic V4 patterns for demand forecasting and congestion
  management
- :doc:`data_integration` — connecting V4 to S3, Databricks, InfluxDB, and other
  data sources
- :doc:`deployment` — production deployment patterns for V4 workflows
- :doc:`logging` — configuring logging in V4 (the logging API also changed from V3)