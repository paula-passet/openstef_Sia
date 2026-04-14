Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant architectural redesign of the library. It moves away from a monolithic package tightly coupled to a database connector (``openstef-dbc``) toward a modular, standalone library that you can integrate into any Python project or data platform. This page covers every breaking change you need to know, with concrete before-and-after code examples and a step-by-step workflow for completing the migration.

.. note::

   If you are deploying OpenSTEF in production or integrating it with external data sources, see the sibling pages
   :doc:`deployment` and :doc:`data_integration` after completing this migration.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 was built around a single ``openstef`` package that assumed a specific database back-end (``openstef-dbc``) and a fixed pipeline structure driven by ``PredictionJobDataClass``. This made it difficult to use OpenSTEF as a pure library — you had to adopt the entire operational stack to get any value from it.

V4 replaces that design with a **modular package family**. The core abstractions (datasets, models, pipelines, storage) are now independent components that compose cleanly. The ``PredictionJobDataClass`` is gone; configuration is expressed through typed dataclasses and composable pipeline objects instead.

The headline changes are:

- **Package structure** — one monolithic package becomes several focused packages (``openstef-core``, ``openstef-models``, ``openstef-beam``).
- **Data model** — ``pandas.DataFrame`` inputs are replaced by ``VersionedTimeSeriesDataset``.
- **Job configuration** — ``PredictionJobDataClass`` / ``ModelSpecificationDataClass`` are replaced by composable ``ForecastingModel`` configuration.
- **Pipelines** — ``train_model_pipeline`` / ``create_forecast_pipeline`` are replaced by ``CustomForecastingWorkflow``.
- **Model storage** — MLflow-only storage is replaced by a pluggable ``ModelStorage`` interface (``LocalModelStorage``, ``JoblibModelSerializer``, and others).
- **No mandatory database dependency** — ``openstef-dbc`` is no longer required.

----

Package Structure Changes
--------------------------

V3 shipped as a single installable package. V4 splits functionality across a small family of packages that you can install selectively.

**Before (V3):**

.. code-block:: bash

   pip install openstef
   # Also required for most real-world use:
   pip install openstef-dbc

**After (V4):**

.. code-block:: bash

   # Meta-package — installs openstef-core + openstef-models (recommended starting point)
   pip install openstef

   # Full installation including backtesting and evaluation tools
   pip install "openstef[all]"

   # Fine-grained control
   pip install openstef-core      # Datasets, base types, shared utilities
   pip install openstef-models    # ML models, feature engineering, pipelines
   pip install openstef-beam      # Backtesting, evaluation, analysis, metrics

The ``openstef-dbc`` dependency is **no longer required**. V4 is a standalone library; you bring your own data loading logic. See :doc:`data_integration` for patterns covering S3, Databricks, InfluxDB, and other sources.

.. list-table:: Package Mapping V3 → V4
   :header-rows: 1
   :widths: 40 60

   * - V3 module
     - V4 equivalent
   * - ``openstef.data_classes.prediction_job``
     - ``openstef_core.base_model`` + ``openstef_models`` pipeline config
   * - ``openstef.pipeline.train_model``
     - ``openstef_models`` ``CustomForecastingWorkflow``
   * - ``openstef.pipeline.create_forecast``
     - ``openstef_models`` ``CustomForecastingWorkflow``
   * - ``openstef.model.serializer``
     - ``openstef_models.integrations.joblib`` / ``LocalModelStorage``
   * - ``openstef-dbc`` (external)
     - Bring your own data loader (see :doc:`data_integration`)

----

Breaking Change 1: PredictionJobDataClass Removed
--------------------------------------------------

In V3, every pipeline call started by constructing a ``PredictionJobDataClass`` dict-like object that bundled together model type, horizon, resolution, quantiles, and metadata. V4 removes this concept entirely. Configuration is now expressed directly when you build a ``ForecastingModel``.

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
   from openstef_models.model.forecasting_model import ForecastingModel
   from openstef_models.forecasters.xgb import XGBForecaster  # example forecaster
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Horizon and quantiles are expressed directly on the forecaster
   forecaster = XGBForecaster(
       horizons=["PT48H"],
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
   )

   model = ForecastingModel(
       forecaster=forecaster,
       target_column="load",
   )

There is no global job ID or ``lat``/``lon`` baked into the model configuration. Metadata that was previously stored on the prediction job (location, tags) is attached at the workflow or storage layer instead, keeping the model object focused on ML concerns.

----

Breaking Change 2: DataFrame Inputs Replaced by TimeSeriesDataset
------------------------------------------------------------------

V3 pipelines accepted a plain ``pandas.DataFrame`` with a ``DatetimeIndex`` and a ``load`` column. V4 wraps time series data in ``VersionedTimeSeriesDataset``, which carries the sample interval alongside the data and enables the library to reason about temporal alignment, versioning, and lead times without relying on implicit conventions.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   # A plain DataFrame was passed directly to pipeline functions
   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )

   # Pipelines accepted the raw DataFrame
   train_model_pipeline(pj, input_data, mlflow_tracking_uri="./mlflow_trained_models")

**After (V4):**

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   raw = pd.read_csv(
       "data/load_data.csv",
       index_col="timestamp",
       parse_dates=True,
   )

   # Wrap the DataFrame, declaring the sample interval explicitly
   dataset = VersionedTimeSeriesDataset(
       data=raw,
       sample_interval=timedelta(minutes=15),
   )

   # The dataset is now passed to workflow methods
   workflow.fit(dataset)

The ``sample_interval`` parameter replaces the ``resolution_minutes`` field that previously lived on the prediction job. Making it part of the dataset object means the library can validate temporal consistency at construction time rather than discovering mismatches deep inside a pipeline.

----

Breaking Change 3: Pipeline Functions Replaced by Workflow Objects
------------------------------------------------------------------

V3 exposed two top-level pipeline functions — ``train_model_pipeline`` and ``create_forecast_pipeline`` — that were called with a prediction job dict and a DataFrame. V4 replaces these with a ``CustomForecastingWorkflow`` object whose ``fit`` and ``predict`` methods mirror the familiar scikit-learn interface.

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
       artifact_folder="./mlflow_artifacts",
   )

   # Forecast — NaN out the target column for the forecast horizon
   to_forecast_data = input_data.copy()
   to_forecast_data.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.workflow import CustomForecastingWorkflow
   from openstef_models.storage import LocalModelStorage

   storage = LocalModelStorage(path="./models")

   workflow = CustomForecastingWorkflow(
       model=model,           # ForecastingModel built above
       model_id="my_forecast",
       callbacks=[],          # optional: MLFlowStorageCallback, etc.
   )

   # Train
   result = workflow.fit(train_dataset)

   # Forecast — no need to manually NaN out the target column
   forecasts = workflow.predict(forecast_dataset)

   # Persist the trained model
   storage.save_model("my_forecast", workflow.model)

The workflow object is stateful: after ``fit`` it holds the trained model and can be serialised to storage. Loading a previously trained model for inference is equally straightforward:

.. code-block:: python

   from openstef_models.workflow import ForecastingWorkflow

   workflow = ForecastingWorkflow.from_storage(
       model_id="my_forecast",
       storage=storage,
   )
   forecasts = workflow.predict(forecast_dataset)

----

Breaking Change 4: Model Storage Interface
------------------------------------------

V3 used MLflow as the only supported model store, configured via a ``mlflow_tracking_uri`` string argument threaded through every pipeline call. V4 introduces a pluggable ``ModelStorage`` interface. ``LocalModelStorage`` (backed by ``JoblibModelSerializer``) is the default for development; MLflow is available as an optional callback.

**Before (V3):**

.. code-block:: python

   # mlflow_tracking_uri was a required argument on every pipeline call
   train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.storage import LocalModelStorage
   from openstef_models.integrations.joblib import JoblibModelSerializer

   # Local storage — suitable for development and single-machine deployments
   storage = LocalModelStorage(
       path="./models",
       serializer=JoblibModelSerializer(),
   )

   # Save and load are explicit operations, not side effects of pipeline calls
   storage.save_model("my_forecast", workflow.model)
   loaded_model = storage.load_model("my_forecast")

To keep MLflow tracking, attach an ``MLFlowStorageCallback`` to the workflow instead of passing a URI string:

.. code-block:: python

   from openstef_models.callbacks import MLFlowStorageCallback

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_forecast",
       callbacks=[
           MLFlowStorageCallback(
               storage=mlflow_storage,
               model_reuse_enable=True,
               model_reuse_max_age=7,  # days
           )
       ],
   )

----

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order to migrate an existing V3 codebase.

**Step 1 — Update dependencies**

Remove ``openstef`` V3 and ``openstef-dbc`` from your requirements. Install the V4 meta-package:

.. code-block:: bash

   pip uninstall openstef openstef-dbc
   pip install "openstef[all]"

**Step 2 — Replace PredictionJobDataClass**

Search your codebase for ``PredictionJobDataClass`` and ``ModelSpecificationDataClass``. For each occurrence, extract the relevant fields and move them to the appropriate V4 object:

- ``model``, ``quantiles``, ``horizon_minutes`` → forecaster constructor arguments
- ``resolution_minutes`` → ``VersionedTimeSeriesDataset(sample_interval=...)``
- ``id``, ``name``, tags → ``CustomForecastingWorkflow(model_id=..., experiment_tags=...)``

**Step 3 — Wrap DataFrames in VersionedTimeSeriesDataset**

Find every location where a ``pd.DataFrame`` is passed to a pipeline function. Wrap it:

.. code-block:: python

   dataset = VersionedTimeSeriesDataset(
       data=your_dataframe,
       sample_interval=timedelta(minutes=resolution_minutes),
   )

**Step 4 — Replace pipeline function calls**

Replace ``train_model_pipeline(...)`` with ``workflow.fit(dataset)`` and ``create_forecast_pipeline(...)`` with ``workflow.predict(dataset)``. Build a ``CustomForecastingWorkflow`` once and reuse it for both operations.

**Step 5 — Update model storage**

Replace ``mlflow_tracking_uri`` arguments with a ``LocalModelStorage`` instance for development, or an ``MLFlowStorageCallback`` for production tracking. Explicit ``save_model`` / ``load_model`` calls replace the implicit side effects of the old pipeline functions.

**Step 6 — Update data loading**

Remove any ``openstef-dbc`` calls. Implement your own data loader that returns a ``pd.DataFrame`` and wrap it in ``VersionedTimeSeriesDataset``. See :doc:`data_integration` for ready-made patterns for common data sources.

**Step 7 — Run your test suite**

V4 ships with a stricter type system. Run your tests with ``mypy`` or ``pyright`` enabled to catch any remaining type mismatches early.

----

Quick Reference: Import Changes
--------------------------------

The table below lists the most commonly used V3 imports and their V4 equivalents.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - V3 import
     - V4 import
   * - ``from openstef.data_classes.prediction_job import PredictionJobDataClass``
     - *(removed — see ForecastingModel)*
   * - ``from openstef.pipeline.train_model import train_model_pipeline``
     - ``from openstef_models.workflow import CustomForecastingWorkflow``
   * - ``from openstef.pipeline.create_forecast import create_forecast_pipeline``
     - ``from openstef_models.workflow import CustomForecastingWorkflow``
   * - ``from openstef.model.serializer import MLflowSerializer``
     - ``from openstef_models.storage import LocalModelStorage``
   * - ``from openstef.pipeline.train_model import train_model_and_forecast_back_test``
     - ``from openstef_beam`` backtesting utilities

----

.. note::

   **Compatibility layer:** An ``openstef-compatibility`` package that provides a thin shim over the V4 API using V3-style function signatures is planned. Check the OpenSTEF release notes for availability before undertaking a large-scale migration.

.. note::

   .. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

----

Related Pages
--------------

- :doc:`use_cases` — End-to-end examples using the V4 API for congestion forecasting and other scenarios.
- :doc:`data_integration` — Patterns for loading data from S3, Databricks, InfluxDB, and other sources into ``VersionedTimeSeriesDataset``.
- :doc:`deployment` — Production deployment patterns for V4, including containerisation and batch inference.
- :doc:`logging` — Configuring logging in V4, which uses standard Python ``logging`` rather than V3's custom log handlers.