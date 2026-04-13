Migration Guide: V3 to V4
==========================

OpenSTEF 4.0 is a significant architectural redesign of the library. This guide covers everything you need to know to migrate existing V3 code to V4: the new package structure, the replacement of ``PredictionJobDataClass`` with a typed configuration model, the shift from pandas DataFrames to ``TimeSeriesDataset``, and the new workflow API. Work through each section in order, then follow the step-by-step migration workflow at the end.

.. note::

   V3 and V4 are **not API-compatible**. You cannot mix V3 and V4 calls in the same pipeline. Treat this as a full rewrite of your integration layer, not a patch upgrade.

----

Package Structure Changes
--------------------------

V3 was distributed as a single ``openstef`` package. V4 adopts a modular, multi-package layout. Each package has a focused responsibility, and you install only what you need.

.. list-table:: V4 Package Layout
   :header-rows: 1
   :widths: 30 70

   * - Package
     - Purpose
   * - ``openstef``
     - Meta-package; installs core components (start here)
   * - ``openstef-core``
     - Dataset types, shared types, base models, utilities
   * - ``openstef-models``
     - ML models, feature engineering, forecasting pipelines
   * - ``openstef-beam``
     - Backtesting, evaluation, analysis, and metrics (BEAM)
   * - ``openstef-compatibility``
     - Compatibility shim for V3 patterns (coming soon)
   * - ``openstef-foundational-models``
     - Deep learning and foundational models (coming soon)

**Before (V3) — single package install:**

.. code-block:: bash

   pip install openstef

**After (V4) — meta-package or selective install:**

.. code-block:: bash

   # Recommended: install everything
   pip install "openstef[all]"

   # Or install only what you need
   pip install openstef-core openstef-models

The import paths change accordingly. V3 imports from a flat ``openstef.*`` namespace; V4 imports are distributed across ``openstef_core.*`` and ``openstef_models.*``.

----

PredictionJobDataClass → Typed Configuration
---------------------------------------------

The most impactful breaking change is the removal of ``PredictionJobDataClass`` and ``ModelSpecificationDataClass``. In V3 these were loosely typed dict-like objects that bundled job metadata, model hyperparameters, and runtime settings together. V4 replaces them with explicit, typed configuration objects and separates concerns cleanly.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model import ModelSpecificationDataClass

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
   import numpy as np
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting.xgb_quantile_forecaster import (
       XGBQuantileForecaster,
   )
   from openstef_models.models.forecasting_model import ForecastingModel

   horizons = [LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")]
   quantiles = [Q(0.10), Q(0.30), Q(0.50), Q(0.70), Q(0.90)]

   model = ForecastingModel(
       forecaster=XGBQuantileForecaster(
           horizons=horizons,
           quantiles=quantiles,
       )
   )

What changed and why: the prediction job concept conflated data routing (database IDs, lat/lon) with modelling concerns (quantiles, horizons, model type). V4 separates these: ``ForecastingModel`` owns the modelling configuration, while data routing is handled by your application layer or a workflow object. This makes the library easier to use standalone without any database dependency.

----

Data Representation: DataFrames → TimeSeriesDataset
-----------------------------------------------------

V3 pipelines accepted and returned plain ``pandas.DataFrame`` objects. V4 introduces ``TimeSeriesDataset`` and its subclasses (``VersionedTimeSeriesDataset``, ``ForecastInputDataset``, ``ForecastDataset``) as the canonical data container. These types carry metadata — sample interval, column semantics, forecast start — that V3 pipelines had to infer or receive via the prediction job.

**Before (V3) — loading data as a raw DataFrame:**

.. code-block:: python

   import pandas as pd

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   # Pipeline received a bare DataFrame; column names were convention-based

**After (V4) — wrapping data in a TimeSeriesDataset:**

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   raw = pd.read_csv(
       "data/my_timeseries.csv",
       index_col="datetime",
       parse_dates=True,
   )

   dataset = VersionedTimeSeriesDataset(
       data=raw,                          # DataFrame with a DatetimeIndex
       sample_interval=timedelta(minutes=15),
   )

The ``sample_interval`` parameter makes the temporal resolution explicit rather than inferred. Downstream pipeline components use this to construct lag features, validate data completeness, and align forecast horizons correctly.

----

Pipeline API: Functions → Workflow Objects
-------------------------------------------

V3 exposed pipelines as module-level functions (``train_model_pipeline``, ``create_forecast_pipeline``). You called them directly, passing the prediction job and a DataFrame. V4 organises the same logic into ``CustomForecastingWorkflow``, a stateful object that owns the model and exposes ``fit`` / ``predict`` methods consistent with the scikit-learn convention.

**Before (V3) — calling pipeline functions directly:**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   train_data, validation_data, test_data = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4) — using the workflow object:**

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # 1. Build the model
   horizons = [LeadTime.from_string("PT24H")]
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.5)],
       )
   )

   # 2. Create the workflow
   workflow = CustomForecastingWorkflow(model=model, model_id="my_model")

   # 3. Train
   workflow.fit(dataset)

   # 4. Predict
   forecasts = workflow.predict(dataset)

The workflow object also supports lifecycle callbacks, which replace the ad-hoc logging and MLflow calls that V3 users had to wire up manually:

.. code-block:: python

   from openstef_models.workflows.callbacks import ForecastingCallback

   class LoggingCallback(ForecastingCallback):
       def on_fit_end(self, context, result):
           print("Training complete")

       def on_predict_end(self, pipeline, dataset, forecasts):
           print(f"Generated {len(forecasts.data)} forecasts")

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_model",
       callbacks=[LoggingCallback()],
   )

----

Model Storage
--------------

V3 relied on MLflow as the only model storage backend, configured through ``mlflow_tracking_uri`` and ``artifact_folder`` arguments passed directly to pipeline functions. V4 abstracts storage behind a ``ModelStorage`` interface, with ``LocalModelStorage`` and ``JoblibModelSerializer`` as the default implementations. MLflow is still available as a callback (``MLFlowStorageCallback``), but it is no longer the only option.

**Before (V3):**

.. code-block:: python

   train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4) — local storage:**

.. code-block:: python

   from openstef_models.storage.local_model_storage import LocalModelStorage

   storage = LocalModelStorage(base_path="./models")
   storage.save_model("my_model", workflow.model)

   loaded_model = storage.load_model("my_model")

**After (V4) — MLflow via callback:**

.. code-block:: python

   from openstef_models.workflows.callbacks.mlflow_storage_callback import (
       MLFlowStorageCallback,
   )

   callback = MLFlowStorageCallback(
       storage=my_mlflow_storage,
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),
       model_selection_enable=True,
   )
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_model",
       callbacks=[callback],
   )

----

Deprecation Warnings
---------------------

Where V3 patterns have not yet been fully removed, V4 emits ``DeprecationWarning`` at runtime. Watch for these in your logs during the migration period:

.. code-block:: python

   import warnings
   warnings.filterwarnings("error", category=DeprecationWarning)
   # Run your pipeline — any deprecated call will raise immediately,
   # making it easy to locate remaining V3 patterns.

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate a V3 integration to V4.

1. **Update your installation.** Replace ``pip install openstef`` with ``pip install "openstef[all]"`` (or the specific packages you need). Remove ``openstef-dbc`` if you were using it for database integration — V4 is standalone by design.

2. **Audit your imports.** Search your codebase for ``from openstef.`` and ``import openstef.``. Every such import needs to be mapped to either ``openstef_core`` or ``openstef_models``. The old ``openstef.data_classes``, ``openstef.pipeline``, and ``openstef.tasks`` namespaces no longer exist.

3. **Replace PredictionJobDataClass.** Identify every place you construct a ``PredictionJobDataClass`` or ``ModelSpecificationDataClass``. Replace them with a ``ForecastingModel`` configured with the appropriate ``forecaster``, ``horizons``, and ``quantiles``.

4. **Wrap your DataFrames.** Find every DataFrame passed into a V3 pipeline function. Wrap it in ``VersionedTimeSeriesDataset``, supplying the correct ``sample_interval``. Ensure your DataFrame has a ``DatetimeIndex`` and a ``load`` column (or configure ``target_column`` on your ``ForecastingModel``).

5. **Replace pipeline function calls.** Swap ``train_model_pipeline(...)`` and ``create_forecast_pipeline(...)`` calls for ``CustomForecastingWorkflow.fit(dataset)`` and ``CustomForecastingWorkflow.predict(dataset)``.

6. **Migrate model storage.** Replace ``mlflow_tracking_uri`` / ``artifact_folder`` arguments with a ``LocalModelStorage`` instance or an ``MLFlowStorageCallback``.

7. **Re-enable deprecation warnings** (see above) and run your test suite. Resolve any remaining warnings before moving to production.

8. **Test forecasts end-to-end.** Compare forecast outputs against known-good V3 results for the same input data. Quantile outputs and feature engineering have changed; expect some numerical differences, particularly in edge cases.

.. note::

   The ``openstef-compatibility`` package (coming soon) will provide a thin shim that accepts V3-style ``PredictionJobDataClass`` objects and translates them to V4 calls. Watch the release notes if you need a lower-effort migration path for large codebases.

----

Related Pages
--------------

- :doc:`use_cases` — Worked examples of common forecasting scenarios using the V4 API.
- :doc:`data_integration` — Connecting V4 pipelines to S3, Databricks, InfluxDB, and other data sources.
- :doc:`deployment` — Production deployment patterns including containerisation and scheduling.
- :doc:`logging` — Configuring structured logging and integrating with your observability stack.