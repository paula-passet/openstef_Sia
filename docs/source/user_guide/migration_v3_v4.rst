Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant architectural redesign of the library. It introduces a modular
package structure, replaces the ``PredictionJobDataClass`` configuration model with typed
dataclasses, and swaps raw ``pandas.DataFrame`` inputs for dedicated dataset types. This page
walks through every breaking change and provides side-by-side before/after code examples so
you can migrate incrementally.

.. note::

   If you rely on ``openstef-dbc`` for database integration, see :doc:`data_integration` for
   V4-compatible patterns. For production deployment considerations after migrating, refer to
   :doc:`deployment`.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 was a single-package library tightly coupled to ``openstef-dbc`` for data access. V4
separates concerns into focused packages, removes the database coupling entirely, and aligns
the API more closely with the scikit-learn ecosystem. The headline changes are:

- **Modular packages** replace the monolithic ``openstef`` package.
- **``PredictionJobDataClass`` is removed** — configuration is now expressed through typed
  ``ModelConfig`` and related dataclasses.
- **``pandas.DataFrame`` inputs are replaced** by ``TimeSeriesDataset`` and
  ``VersionedTimeSeriesDataset``.
- **Pipeline entry points are reorganised** — the top-level ``train_model_pipeline`` and
  ``create_forecast_pipeline`` functions are superseded by a ``ForecastingModel`` /
  ``CustomForecastingWorkflow`` pattern.
- **``openstef-dbc`` is no longer a dependency** — data fetching is your responsibility,
  giving you full control over data sources.

----

Package Structure Changes
--------------------------

In V3 everything lived in a single ``openstef`` package. V4 splits the library into
composable packages that you install only as needed.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Concern
     - V3 location
     - V4 package
   * - Core utilities, base types
     - ``openstef.*``
     - ``openstef-core``
   * - ML models, feature engineering
     - ``openstef.model.*``, ``openstef.feature_engineering.*``
     - ``openstef-models``
   * - Backtesting, evaluation, metrics
     - ``openstef.pipeline.train_model_and_forecast_back_test``
     - ``openstef-beam``
   * - Database tasks
     - ``openstef-dbc`` (separate, required)
     - Not included — bring your own data layer

**Before (V3) — installation:**

.. code-block:: bash

   pip install openstef openstef-dbc

**After (V4) — installation:**

.. code-block:: bash

   # Core forecasting only
   pip install openstef

   # Core + backtesting / evaluation tools
   pip install "openstef[beam]"

   # Everything available
   pip install "openstef[all]"

----

Configuration: PredictionJobDataClass → ModelConfig
-----------------------------------------------------

The ``PredictionJobDataClass`` (often called ``pj``) was the central configuration object in
V3. It was a dictionary-like dataclass that bundled model type, horizon, resolution, and
hyperparameters together. V4 removes this class entirely.

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

   from openstef_models.config import ModelConfig

   config = ModelConfig(
       model_type="xgb",
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       horizon=48,           # hours, not minutes
       resolution_minutes=15,
   )

Key differences to note:

- ``horizon_minutes`` becomes ``horizon`` expressed in **hours**.
- ``id``, ``lat``, ``lon``, ``name``, and ``forecast_type`` are no longer part of the model
  configuration — they belong to your own application metadata.
- ``hyper_params`` and ``feature_names`` are configured through the pipeline and feature
  engineering components rather than the top-level config object.
- ``ModelSpecificationDataClass`` has no V4 equivalent; model specifications are inferred
  during training.

----

Data Input: DataFrame → TimeSeriesDataset
------------------------------------------

V3 pipelines accepted plain ``pandas.DataFrame`` objects with a ``DatetimeIndex``. V4
introduces ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` to make temporal
structure and data-availability semantics explicit.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   # V3: pass a raw DataFrame directly to the pipeline
   input_data = pd.read_csv(
       "data/load_data.csv",
       index_col="index",
       parse_dates=True,
   )

   train_data, validation_data, test_data = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   raw_df = pd.read_csv(
       "data/load_data.csv",
       index_col="timestamp",
       parse_dates=True,
   )

   # Wrap the DataFrame in a VersionedTimeSeriesDataset.
   # sample_interval describes the temporal resolution of your data.
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw_df,
       sample_interval=timedelta(minutes=15),
   )

``VersionedTimeSeriesDataset`` tracks *when* each observation became available, which is
essential for realistic backtesting. For simple single-source data without availability
metadata, ``TimeSeriesDataset`` is the lighter-weight alternative:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   dataset = TimeSeriesDataset(
       data=raw_df,
       sample_interval=timedelta(minutes=15),
   )

----

Training Pipeline
-----------------

V3 exposed a ``train_model_pipeline`` function at the top level. V4 replaces this with a
``ForecastingModel`` class that composes preprocessing, a model, and postprocessing, and a
``CustomForecastingWorkflow`` (or ``TaskRunner``) that orchestrates training and inference.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   train_data, validation_data, test_data = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.config import ModelConfig
   from openstef_models.forecasting_model import ForecastingModel
   from openstef_models.feature_pipeline import FeaturePipeline
   from openstef_models.storage import LocalModelStorage
   from openstef_models.workflow import CustomForecastingWorkflow

   # 1. Prepare data
   raw_df = pd.read_csv("data/load_data.csv", index_col="timestamp", parse_dates=True)
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw_df, sample_interval=timedelta(minutes=15)
   )

   # 2. Configure the model
   config = ModelConfig(model_type="xgb", horizon=47, resolution_minutes=15)

   # 3. Build the forecasting model (preprocessing + model + postprocessing)
   feature_pipeline = FeaturePipeline.with_defaults(config)
   model = ForecastingModel(config=config, feature_pipeline=feature_pipeline)

   # 4. Set up storage
   storage = LocalModelStorage(Path("./trained_models"))

   # 5. Train via the workflow
   workflow = CustomForecastingWorkflow(model=model, storage=storage)
   workflow.train(dataset)

.. note::

   MLflow tracking is no longer configured through pipeline arguments. In V4, model
   persistence is handled by the ``ModelStorage`` abstraction — use ``LocalModelStorage``
   for filesystem storage or implement the ``ModelStorage`` interface for custom backends
   (S3, MLflow, etc.). See :doc:`data_integration` for examples.

----

Forecasting Pipeline
---------------------

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   # Load the previously trained model from storage
   loaded_model = storage.load_model("my_forecast_model")

   # Run inference on new data
   forecast = workflow.predict(dataset)

   # forecast is a pandas DataFrame with quantile columns
   print(forecast.head())

----

Backtesting
-----------

V3 provided ``train_model_and_forecast_back_test`` as a single function. In V4, backtesting
is part of the ``openstef-beam`` package (Backtesting, Evaluation, Analysis, and Metrics).

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_and_forecast_back_test

   forecast, model, train_data, validation_data, test_data, scores = (
       train_model_and_forecast_back_test(
           pj,
           ModelSpecificationDataClass(id=pj["id"]),
           input_data,
           training_horizons=[0.25, 47.0],
       )
   )

**After (V4):**

.. code-block:: bash

   pip install "openstef[beam]"

.. code-block:: python

   from openstef_beam.backtest import BacktestRunner

   runner = BacktestRunner(model=model, storage=storage)
   backtest_results = runner.run(dataset, horizons=[0.25, 47.0])

   # Access metrics and forecasts
   print(backtest_results.metrics)

----

Import Path Changes
--------------------

Many internal modules have moved or been renamed. The table below covers the most commonly
used imports.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - V3 import
     - V4 import
   * - ``from openstef.data_classes.prediction_job import PredictionJobDataClass``
     - ``from openstef_models.config import ModelConfig``
   * - ``from openstef.data_classes.model_specifications import ModelSpecificationDataClass``
     - *(removed — no direct equivalent)*
   * - ``from openstef.pipeline.train_model import train_model_pipeline``
     - ``from openstef_models.workflow import CustomForecastingWorkflow``
   * - ``from openstef.pipeline.create_forecast import create_forecast_pipeline``
     - ``from openstef_models.workflow import CustomForecastingWorkflow``
   * - ``from openstef.pipeline.train_model import train_model_and_forecast_back_test``
     - ``from openstef_beam.backtest import BacktestRunner``
   * - ``from openstef.feature_engineering.feature_applicator import ...``
     - ``from openstef_models.feature_pipeline import FeaturePipeline``
   * - ``from openstef.model.serializer import MLflowSerializer``
     - ``from openstef_models.storage import LocalModelStorage``

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate a working V3 integration to V4.

**Step 1 — Update your dependencies**

.. code-block:: bash

   # Remove V3 packages
   pip uninstall openstef openstef-dbc

   # Install V4 (add [beam] if you use backtesting)
   pip install "openstef[all]"

**Step 2 — Replace PredictionJobDataClass**

Search your codebase for ``PredictionJobDataClass`` and ``ModelSpecificationDataClass``.
Replace each instantiation with a ``ModelConfig``. Move any application-level metadata
(``id``, ``name``, ``lat``, ``lon``) into your own data structures — OpenSTEF V4 does not
require them.

**Step 3 — Wrap DataFrames in dataset types**

Find every place you pass a ``pd.DataFrame`` to a pipeline function and wrap it with
``VersionedTimeSeriesDataset.from_dataframe(df, sample_interval=timedelta(minutes=15))``.
Ensure your DataFrame's index is a ``DatetimeIndex`` named ``"timestamp"``.

**Step 4 — Replace pipeline calls**

Replace calls to ``train_model_pipeline`` and ``create_forecast_pipeline`` with a
``ForecastingModel`` + ``CustomForecastingWorkflow`` setup (see the examples above).

**Step 5 — Replace MLflow storage configuration**

Remove ``mlflow_tracking_uri`` and ``artifact_folder`` arguments. Instantiate a
``LocalModelStorage`` pointing at your desired directory, or implement a custom
``ModelStorage`` backend.

**Step 6 — Migrate backtesting (if used)**

Install ``openstef-beam`` and replace ``train_model_and_forecast_back_test`` calls with
``BacktestRunner``.

**Step 7 — Remove openstef-dbc**

V4 has no built-in database connector. Move data-fetching logic to your application layer.
See :doc:`data_integration` for patterns that work with InfluxDB, S3, and Databricks.

.. warning::

   ``openstef-compatibility`` (a shim layer that accepts V3-style ``PredictionJobDataClass``
   objects and translates them to V4 internals) is listed as *coming soon*. Until it is
   released, the manual migration steps above are required.

----

Deprecation Warnings
---------------------

During the transition period, some V3-style keyword arguments emit ``DeprecationWarning``
rather than raising immediately. Enable all warnings during your migration to surface these
early:

.. code-block:: bash

   python -W all my_script.py

Or in code:

.. code-block:: python

   import warnings
   warnings.filterwarnings("error", category=DeprecationWarning, module="openstef")

This converts deprecation warnings into errors so your test suite will fail loudly on any
remaining V3 usage.

----

Getting Help
------------

- **Use cases and worked examples** — :doc:`use_cases`
- **Production deployment after migration** — :doc:`deployment`
- **Connecting V4 to your data sources** — :doc:`data_integration`
- **Logging configuration** — :doc:`logging`
- **GitHub issue tracker** — `github.com/OpenSTEF/openstef/issues <https://github.com/OpenSTEF/openstef/issues>`_