Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant redesign of the library. While V3 was built around a monolithic ``openstef`` package tightly coupled to the ``openstef-dbc`` database connector, V4 adopts a modular, multi-package architecture that makes the library easier to embed in your own pipelines without any database dependency. This page covers every breaking change you need to know, with concrete before/after code examples for each one.

.. note::

   If you are deploying OpenSTEF in production, see :doc:`deployment` for patterns
   that work with the V4 architecture. For data integration specifics (S3, InfluxDB,
   Databricks), see :doc:`data_integration`.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 grew organically around a single ``openstef`` package that assumed you were running
a full application: tasks fetched data from a database, pipelines wrote results back,
and the ``PredictionJobDataClass`` acted as a global configuration object threaded
through every call. This design made it hard to use OpenSTEF as a pure library — you
either took the whole stack or wrote significant glue code to work around it.

V4 breaks that coupling. The library is now split into focused packages
(``openstef-core``, ``openstef-models``, ``openstef-beam``), the database layer is
entirely optional, and the central configuration object has been replaced with typed
dataclasses and a composable pipeline model. The result is a library you can drop into
any Python project without pulling in database infrastructure.

----

Package Structure Changes
--------------------------

The single ``openstef`` package is replaced by a set of smaller, independently
installable packages. Install only what you need.

**Before (V3) — one package:**

.. code-block:: bash

   pip install openstef
   # Optional database connector
   pip install openstef-dbc

**After (V4) — modular packages:**

.. code-block:: bash

   # Core abstractions: datasets, base model interfaces, exceptions
   pip install openstef-core

   # Forecasting models, feature pipelines, workflows
   pip install openstef-models

   # Apache Beam-based distributed runners (optional)
   pip install openstef-beam

The top-level import paths change accordingly:

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

**After (V4):**

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )

----

Breaking Change 1: PredictionJobDataClass Removed
--------------------------------------------------

In V3, ``PredictionJobDataClass`` was the central configuration object. It was a
dictionary-like dataclass passed into every pipeline call to carry model type,
horizons, quantiles, feature names, and location metadata.

V4 removes this concept entirely. Configuration is now expressed through typed
dataclasses that are specific to each component — ``ForecastingWorkflowConfig`` for
workflow-level settings, ``ModelConfig`` for model hyperparameters, and
``LocationConfig`` for geographic metadata. This makes configuration more explicit and
eliminates the large, catch-all parameter bag.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   import pandas as pd

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

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )

   from openstef.pipeline.train_model import train_model_pipeline
   train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_models.integrations.joblib import JoblibModelSerializer
   from openstef_core.datasets import VersionedTimeSeriesDataset
   import pandas as pd

   # Location metadata is now a dedicated typed config
   location = LocationConfig(id=287, name="TestPrediction", lat=52.0, lon=5.0)

   # Workflow-level configuration replaces PredictionJobDataClass
   config = ForecastingWorkflowConfig(
       location=location,
       horizon=48,           # hours, not minutes
       resolution=15,        # minutes
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
   )

   workflow = create_forecasting_workflow(config)

   # Data is wrapped in a typed dataset, not passed as a raw DataFrame
   raw = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   dataset = VersionedTimeSeriesDataset(raw)

   # Train using the workflow object
   model_storage = JoblibModelSerializer()
   workflow.train(dataset, model_storage, model_id="TestPrediction")

Key differences to note:

- ``horizon_minutes`` is replaced by ``horizon`` expressed in **hours**.
- ``hyper_params`` and ``feature_names`` are no longer top-level fields; configure
  them through the model's own ``ModelConfig``.
- The workflow object owns the train/predict lifecycle instead of standalone pipeline
  functions.

----

Breaking Change 2: Pipeline Functions Replaced by Workflow Objects
-------------------------------------------------------------------

V3 exposed top-level pipeline functions (``train_model_pipeline``,
``create_forecast_pipeline``) that you called with a prediction job and a DataFrame.
V4 replaces these with a ``CustomForecastingWorkflow`` object that encapsulates the
full train-predict lifecycle, including feature engineering and model storage.

**Before (V3) — making a forecast:**

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Blank out the period you want to forecast
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4) — making a forecast:**

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Wrap your input in a typed dataset
   forecast_input = VersionedTimeSeriesDataset(to_forecast_df)

   # Load the previously trained model and predict
   loaded_model = model_storage.load_model("TestPrediction")
   forecast_dataset = loaded_model.predict(forecast_input)

   # forecast_dataset is a typed ForecastDataset, not a raw DataFrame
   forecast_df = forecast_dataset.to_dataframe()

.. note::

   ``ForecastDataset`` and ``ForecastInputDataset`` are validated dataset types
   defined in ``openstef_core.datasets``. They carry domain-specific constraints
   (e.g. required columns, horizon metadata) that were previously checked ad-hoc
   inside V3 pipeline functions.

----

Breaking Change 3: Data Structures — DataFrame to TimeSeriesDataset
--------------------------------------------------------------------

V3 passed raw ``pandas.DataFrame`` objects between every component. V3 pipelines
expected a specific column layout (a ``load`` column, datetime index, weather
features) but enforced this only at runtime with opaque errors.

V4 introduces ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` from
``openstef_core.datasets``. These are typed wrappers that validate structure on
construction and carry horizon metadata alongside the data.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   # Raw DataFrame — column names and index type are implicit contracts
   data = pd.read_csv("load_data.csv", index_col="index", parse_dates=True)
   # Passed directly to pipeline functions
   train_model_pipeline(pj, data, ...)

**After (V4):**

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset

   raw = pd.read_csv("load_data.csv", index_col="index", parse_dates=True)

   # Wrap in a validated dataset — structure is checked at construction time
   dataset = VersionedTimeSeriesDataset(raw)

   # Pass the dataset to the workflow
   workflow.train(dataset, model_storage, model_id="my_location")

``VersionedTimeSeriesDataset`` is the right choice for most use cases: it tracks
when each data point became available, which is important for backtesting and
avoiding look-ahead bias. Use the base ``TimeSeriesDataset`` when you only have a
single snapshot of data without availability timestamps.

----

Breaking Change 4: Model Storage — MLflow to Pluggable Serializers
-------------------------------------------------------------------

V3 used MLflow as its model storage backend. The ``mlflow_tracking_uri`` parameter
was required by every pipeline call, and the MLflow server had to be reachable at
training and inference time.

V4 replaces this with a pluggable serializer interface. The default implementation,
``JoblibModelSerializer``, stores models as local ``.joblib`` files. You can
implement the ``ModelSerializer`` interface to target any storage backend (S3, GCS,
a database) without changing your pipeline code.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",   # required
       artifact_folder="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.integrations.joblib import JoblibModelSerializer
   from pathlib import Path

   # Configure storage — no MLflow server required
   storage = JoblibModelSerializer(base_path=Path("./trained_models"))

   # Pass storage to the workflow; it handles save/load internally
   workflow.train(dataset, storage, model_id="my_location")

   # Load a model explicitly when needed
   model = storage.load_model("my_location")

.. note::

   If your organisation already depends on MLflow for experiment tracking, you can
   implement a custom ``ModelSerializer`` that writes to your MLflow server. See the
   ``openstef_core.mixins.stateful`` module for the interface to implement.

----

Breaking Change 5: openstef-dbc Is No Longer Required
------------------------------------------------------

In V3, the ``openstef-dbc`` package was a practical requirement for any non-trivial
use: it provided the database connectors that tasks used to fetch prediction jobs and
write forecasts. Without it, you had to bypass the task layer entirely and call
pipelines directly with manually constructed ``PredictionJobDataClass`` objects.

V4 has no dependency on ``openstef-dbc`` at all. The library is self-contained.
Data ingestion is your responsibility — bring data in as a ``VersionedTimeSeriesDataset``
from whatever source you use (CSV, S3, InfluxDB, a REST API). See :doc:`data_integration`
for patterns covering common sources.

----

Step-by-Step Migration Workflow
--------------------------------

Follow these steps to migrate an existing V3 codebase to V4.

**Step 1 — Update your dependencies**

Remove ``openstef`` and optionally ``openstef-dbc`` from your requirements. Add the
V4 packages you need:

.. code-block:: bash

   pip uninstall openstef openstef-dbc
   pip install openstef-core openstef-models

**Step 2 — Replace PredictionJobDataClass**

Find every instantiation of ``PredictionJobDataClass`` in your codebase. For each
one, create a ``ForecastingWorkflowConfig`` (and a ``LocationConfig`` for geographic
fields). Map the fields using this table:

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - V3 field
     - V4 equivalent
     - Notes
   * - ``id``
     - ``LocationConfig.id``
     -
   * - ``name``
     - ``LocationConfig.name``
     -
   * - ``lat``, ``lon``
     - ``LocationConfig.lat``, ``LocationConfig.lon``
     -
   * - ``horizon_minutes``
     - ``ForecastingWorkflowConfig.horizon``
     - Convert to hours: ``horizon_minutes / 60``
   * - ``resolution_minutes``
     - ``ForecastingWorkflowConfig.resolution``
     - Still in minutes
   * - ``quantiles``
     - ``ForecastingWorkflowConfig.quantiles``
     -
   * - ``model``
     - Configured on the ``ForecastingModel`` directly
     - e.g. ``XGBForecaster``
   * - ``hyper_params``
     - ``ModelConfig`` passed to the forecaster
     -
   * - ``feature_names``
     - ``FeaturePipeline`` configuration
     -
   * - ``forecast_type``
     - Expressed via dataset type (``EnergyComponentDataset``, etc.)
     -

**Step 3 — Wrap your DataFrames**

Replace every raw ``pd.DataFrame`` passed to a pipeline with a
``VersionedTimeSeriesDataset``:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   dataset = VersionedTimeSeriesDataset(your_existing_dataframe)

**Step 4 — Replace pipeline function calls**

Replace calls to ``train_model_pipeline`` and ``create_forecast_pipeline`` with
workflow methods:

.. code-block:: python

   # V3
   train_model_pipeline(pj, data, mlflow_tracking_uri="...")
   forecast = create_forecast_pipeline(pj, data, mlflow_tracking_uri="...")

   # V4
   workflow.train(dataset, storage, model_id="my_location")
   forecast_dataset = workflow.predict(forecast_input, storage, model_id="my_location")

**Step 5 — Replace MLflow storage**

Remove all ``mlflow_tracking_uri`` and ``artifact_folder`` arguments. Instantiate a
``JoblibModelSerializer`` pointing to an equivalent local path, or implement a custom
serializer for your storage backend.

**Step 6 — Run your test suite**

V4 raises typed exceptions from ``openstef_core.exceptions`` rather than generic
Python exceptions. If your error-handling code catches specific exception types,
update those imports.

----

Quick Reference: Import Changes
--------------------------------

The table below covers the most commonly used V3 imports and their V4 replacements.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - V3 import
     - V4 import
   * - ``from openstef.data_classes.prediction_job import PredictionJobDataClass``
     - ``from openstef_models.presets.forecasting_workflow import ForecastingWorkflowConfig``
   * - ``from openstef.data_classes.model_specifications import ModelSpecificationDataClass``
     - ``from openstef_core.base_model import BaseConfig``
   * - ``from openstef.pipeline.train_model import train_model_pipeline``
     - ``workflow.train(...)`` via ``create_forecasting_workflow``
   * - ``from openstef.pipeline.create_forecast import create_forecast_pipeline``
     - ``workflow.predict(...)`` via ``create_forecasting_workflow``
   * - ``pd.DataFrame`` (raw, passed to pipelines)
     - ``from openstef_core.datasets import VersionedTimeSeriesDataset``
   * - MLflow via ``mlflow_tracking_uri``
     - ``from openstef_models.integrations.joblib import JoblibModelSerializer``

----

.. note::

   For questions about deploying V4 in production environments, including Kubernetes
   and cloud-native patterns, see :doc:`deployment`. For configuring structured
   logging in V4, see :doc:`logging`.