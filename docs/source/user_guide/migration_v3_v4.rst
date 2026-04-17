Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant architectural evolution of the library. Rather than incremental API changes, V4 introduces a fully redesigned package structure built around composable, typed components. This guide covers every category of breaking change and provides concrete before/after code examples to help you migrate existing V3 workflows.

.. note::

   If you are starting a new project, go directly to the :doc:`use_cases` page for
   idiomatic V4 patterns. This guide is specifically for teams upgrading from V3.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 organised everything inside a single ``openstef`` package. Pipelines were
top-level functions, the ``PredictionJobDataClass`` was the central configuration
object, and model storage was handled implicitly through MLflow paths passed as
string arguments.

V4 splits the library into focused sub-packages and replaces the monolithic
pipeline functions with a composable object model:

- **openstef-core** — datasets, base interfaces, types, and utilities
- **openstef-models** — model implementations, feature pipelines, workflows, and presets
- **openstef-beam** — distributed execution, evaluation, and visualisation helpers

The ``PredictionJobDataClass`` is gone. Configuration is now expressed through
typed Pydantic ``BaseConfig`` objects that are specific to each component. Pipelines
are replaced by ``ForecastingModel`` + ``CustomForecastingWorkflow``, which give you
explicit control over every stage while still providing sensible defaults.

----

Package Structure Changes
--------------------------

The table below maps the most commonly used V3 import paths to their V4 equivalents.

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - V3 import
     - V4 import
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - ``openstef_core.base_model.BaseConfig`` (per-component configs)
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``openstef_models.workflows.custom_forecasting_workflow.CustomForecastingWorkflow``
   * - ``openstef.pipeline.create_forecast.create_forecast_pipeline``
     - ``CustomForecastingWorkflow.predict``
   * - ``openstef.models.*`` (regressors)
     - ``openstef_models.models.*``
   * - *(implicit MLflow path string)*
     - ``openstef_models.storage.LocalModelStorage`` / ``MLFlowStorage``

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

----

.. _breaking-change-1:

Breaking Change 1: PredictionJob Replaced by Typed Configs
-----------------------------------------------------------

In V3, a single ``PredictionJobDataClass`` dictionary-like object carried every
setting — model type, quantiles, horizon, location, and more. In V4 each component
declares its own typed configuration using Pydantic ``BaseConfig`` subclasses.
This makes configuration errors visible at construction time rather than at
runtime deep inside a pipeline.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       name="my_forecast",
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       hyper_params={},
       feature_names=None,
   )

**After (V4):**

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import LeadTime, Q

   location = LocationConfig(lat=52.0, lon=5.0, name="my_forecast")

   config = ForecastingWorkflowConfig(
       model_id="my_forecast_287",
       horizons=[LeadTime.from_string("PT47H")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       location=location,
   )

   workflow = create_forecasting_workflow(config)

Key differences:

- ``horizon_minutes`` becomes a typed ``LeadTime`` value (ISO 8601 duration string).
- ``quantiles`` are typed ``Q`` objects rather than bare floats.
- ``model`` type is now selected by choosing a concrete ``Forecaster`` subclass,
  not a string.
- ``id`` is replaced by a human-readable ``model_id`` string used for storage.

----

.. _breaking-change-2:

Breaking Change 2: Pipeline Functions Replaced by Workflow Objects
------------------------------------------------------------------

In V3 ``train_model_pipeline`` and ``create_forecast_pipeline`` were standalone
functions. You called them, passed a prediction job and a DataFrame, and received
results back. V4 replaces these with a stateful ``CustomForecastingWorkflow`` object
whose ``fit`` and ``predict`` methods carry the same responsibilities but with
explicit dataset types and lifecycle callbacks.

**Before (V3) — training:**

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline

   pj = PredictionJobDataClass(**pj_dict)
   input_data = pd.read_csv("data/load.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   model, report, modelspecs, datasets = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

**After (V4) — training:**

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # Wrap your DataFrame in a typed dataset
   df = pd.read_csv("data/load.csv", index_col="index", parse_dates=True)
   dataset = VersionedTimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
   )

   # Build the model and workflow explicitly
   horizons = [LeadTime.from_string("PT47H")]
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.5)],
       )
   )

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_forecast_287",
   )

   fit_result = workflow.fit(dataset)

**Before (V3) — forecasting:**

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   to_forecast_data = input_data.copy(deep=True)
   to_forecast_data.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4) — forecasting:**

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   # Provide data with NaN in the target column for the forecast horizon
   forecast_df = df.copy()
   forecast_df.loc[test_indices, "load"] = np.nan

   forecast_dataset = VersionedTimeSeriesDataset(
       data=forecast_df,
       sample_interval=timedelta(minutes=15),
   )

   forecasts: ForecastDataset = workflow.predict(forecast_dataset)

The workflow object retains the fitted model in memory and can be persisted to
storage independently of the predict call — a cleaner separation than V3's implicit
MLflow coupling.

----

.. _breaking-change-3:

Breaking Change 3: Dataset Types
---------------------------------

V3 accepted plain ``pandas.DataFrame`` objects everywhere. V4 introduces typed
dataset wrappers that carry metadata (sample interval, horizon availability) and
enforce schema validation before data reaches the model.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Purpose
     - V3
     - V4
   * - Training data
     - ``pd.DataFrame``
     - ``openstef_core.datasets.TimeSeriesDataset``
   * - Versioned / multi-horizon data
     - ``pd.DataFrame`` with manual slicing
     - ``openstef_core.datasets.VersionedTimeSeriesDataset``
   * - Forecast input
     - ``pd.DataFrame`` with NaN target
     - ``openstef_core.datasets.ForecastInputDataset``
   * - Forecast output
     - ``pd.DataFrame``
     - ``openstef_core.datasets.ForecastDataset``

Wrapping an existing DataFrame is straightforward:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   dataset = TimeSeriesDataset(
       data=my_dataframe,          # your existing pd.DataFrame
       sample_interval=timedelta(minutes=15),
   )

----

.. _breaking-change-4:

Breaking Change 4: Model Storage
----------------------------------

V3 passed MLflow tracking URIs as string arguments directly to pipeline functions.
V4 makes storage an explicit, injectable dependency through a ``ModelStorage``
interface. Two implementations ship out of the box:

- ``LocalModelStorage`` — stores serialised models on the local filesystem.
- ``MLFlowStorage`` — stores models and artefacts in an MLflow tracking server.

**Before (V3):**

.. code-block:: python

   train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.storage import LocalModelStorage
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   storage = LocalModelStorage(path="./trained_models")

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_forecast_287",
   )

   fit_result = workflow.fit(dataset)
   storage.save(workflow.model_id, workflow)

   # Later, restore from storage
   loaded_workflow = CustomForecastingWorkflow.from_storage(
       model_id="my_forecast_287",
       storage=storage,
   )

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate a V3 codebase to V4.

**Step 1 — Update dependencies**

Replace the single ``openstef`` package with the V4 sub-packages relevant to your
use case:

.. code-block:: bash

   pip uninstall openstef
   pip install openstef-core openstef-models

If you use distributed execution or the built-in evaluation and plotting utilities,
also install:

.. code-block:: bash

   pip install openstef-beam

**Step 2 — Replace PredictionJobDataClass**

Search your codebase for ``PredictionJobDataClass`` and replace each instantiation
with the appropriate V4 config object. Use ``ForecastingWorkflowConfig`` for
end-to-end workflows, or construct ``ForecastingModel`` directly if you only need
the model layer. See :ref:`breaking-change-1` above for the field mapping.

**Step 3 — Replace pipeline function calls**

Replace calls to ``train_model_pipeline`` and ``create_forecast_pipeline`` with a
``CustomForecastingWorkflow`` instance. The workflow's ``fit`` and ``predict``
methods accept ``TimeSeriesDataset`` / ``VersionedTimeSeriesDataset`` objects
instead of raw DataFrames. See :ref:`breaking-change-2` for full before/after
examples.

**Step 4 — Wrap DataFrames in dataset types**

Identify every ``pd.DataFrame`` that was passed to a V3 pipeline function and wrap
it in the appropriate V4 dataset class. The ``sample_interval`` parameter is
required and must match the actual data frequency. See :ref:`breaking-change-3` for
the full mapping.

**Step 5 — Externalise model storage**

Replace MLflow URI strings in pipeline calls with an explicit ``LocalModelStorage``
or ``MLFlowStorage`` instance. Attach it to the workflow or call ``storage.save``
and ``storage.load`` directly. See :ref:`breaking-change-4` for examples.

**Step 6 — Run your test suite**

V4 raises ``pydantic.ValidationError`` for misconfigured components at construction
time, so many configuration bugs that were previously silent runtime failures will
now surface immediately. Fix any validation errors before proceeding to integration
testing.

.. note::

   The V4 ``Predictor`` base class follows the scikit-learn ``fit`` / ``predict``
   pattern. If you have custom model subclasses from V3, re-implement them by
   subclassing ``openstef_core.mixins.predictor.Predictor`` and implementing
   ``is_fitted``, ``fit``, and ``predict``.

----

Quick Reference: Import Path Changes
--------------------------------------

.. code-block:: python

   # ── V3 ──────────────────────────────────────────────────────────────────
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # ── V4 equivalents ───────────────────────────────────────────────────────
   from openstef_core.datasets import (
       TimeSeriesDataset,
       VersionedTimeSeriesDataset,
       ForecastDataset,
   )
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from openstef_models.storage import LocalModelStorage

----

Related Pages
--------------

- :doc:`use_cases` — idiomatic V4 usage patterns for common forecasting scenarios
- :doc:`deployment` — production deployment patterns including MLflow storage
  configuration and scaling strategies
- :doc:`data_integration` — reading training data from S3, Databricks, and
  InfluxDB into ``TimeSeriesDataset`` objects