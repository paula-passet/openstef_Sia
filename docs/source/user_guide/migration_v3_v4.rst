Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant architectural overhaul of the library. It moves away from the
database-coupled, task-oriented design of V3 toward a fully standalone, composable pipeline
architecture. This guide covers every breaking change you are likely to encounter and walks
you through updating your code step by step.

.. note::

   V3 and V4 are **not** API-compatible. You cannot mix V3 and V4 imports in the same
   project. Plan a clean cutover rather than an incremental migration.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 was designed around a central database connector (``openstef-dbc``) that fetched and
wrote data on your behalf. Pipelines were tightly coupled to that connector, which made
the library difficult to use outside of the specific infrastructure it was built for.

V4 removes this coupling entirely. The library is now a pure Python toolkit: you bring
your own data, you own the storage layer, and you compose pipelines from explicit building
blocks. The key architectural shifts are:

- **No more ``openstef-dbc`` dependency** — data I/O is your responsibility.
- **``PredictionJobDataClass`` is gone** — configuration is now expressed through typed
  model and workflow objects.
- **pandas DataFrames replaced by ``TimeSeriesDataset``** — a purpose-built data structure
  that carries temporal metadata alongside the values.
- **Tasks are gone** — the task layer (which called ``openstef-dbc`` under the hood) has
  been removed. Use pipelines and workflows directly.
- **Composable pipelines** — preprocessing, forecasting, and postprocessing are separate
  objects you assemble into a ``ForecastingModel``.

----

Package Structure Changes
--------------------------

V3 shipped a single ``openstef`` package. V4 splits functionality across focused packages:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Concern
     - V3 location
     - V4 location
   * - Core data types & pipelines
     - ``openstef``
     - ``openstef_core``
   * - Model training & forecasting
     - ``openstef.pipeline``
     - ``openstef_core``
   * - Visualisation / analysis
     - ``openstef.plotting``
     - ``openstef_beam.analysis.plots``
   * - Database tasks
     - ``openstef_dbc`` (separate package)
     - **Removed** — bring your own I/O

Update your ``requirements.txt`` or ``pyproject.toml`` accordingly:

**Before (V3):**

.. code-block:: python

   # requirements.txt
   openstef>=3.0,<4.0
   openstef-dbc>=3.0,<4.0

**After (V4):**

.. code-block:: python

   # requirements.txt
   openstef-core>=4.0
   openstef-beam>=4.0   # optional — only needed for visualisation / Beam runners

----

.. _breaking-change-1:

Breaking Change 1: PredictionJobDataClass Removed
--------------------------------------------------

In V3, every pipeline call started with constructing a ``PredictionJobDataClass`` — a
dict-like object that bundled model type, horizon, resolution, quantiles, and location
metadata into a single configuration blob.

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

V4 has no equivalent single configuration class. Instead, you configure each component
of the pipeline explicitly when constructing a ``ForecastingModel`` and a workflow. See
:ref:`breaking-change-3` for a full end-to-end example.

----

.. _breaking-change-2:

Breaking Change 2: Input Data Format
--------------------------------------

V3 pipelines accepted a plain ``pandas.DataFrame`` with a ``DatetimeIndex`` and a
``load`` column. V4 introduces ``TimeSeriesDataset`` (and its versioned subclass
``VersionedTimeSeriesDataset``), which wraps the DataFrame and carries temporal metadata
that the pipeline uses for feature engineering and train/test splitting.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   # A plain DataFrame — index must be a DatetimeIndex
   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   # Pass directly to the pipeline
   # train_model_pipeline(pj, input_data, ...)

**After (V4):**

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   raw = pd.read_csv(
       "data/load_data.csv",
       index_col="datetime",
       parse_dates=True,
   )
   # Wrap in a TimeSeriesDataset before passing to any pipeline
   dataset = TimeSeriesDataset(data=raw, target_column="load")

For testing and prototyping, V4 ships a helper that generates synthetic data so you can
explore the API without real data:

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset

   dataset = create_synthetic_forecasting_dataset()

----

.. _breaking-change-3:

Breaking Change 3: Pipeline API
---------------------------------

The V3 ``train_model_pipeline`` and ``create_forecast_pipeline`` functions are replaced
by a composable object graph: a ``ForecastingModel`` (which holds preprocessing,
forecaster, and postprocessing stages) wrapped in a ``CustomForecastingWorkflow``.

**Before (V3):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import numpy as np

   # Train
   models = train_model_pipeline(
       pj,
       train_data,                          # plain DataFrame
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_trained_models",
   )

   # Forecast — set future load values to NaN to signal the horizon
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   import numpy as np
   import pandas as pd
   from openstef_core.datasets import ForecastDataset, TimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.workflows import CustomForecastingWorkflow
   from openstef_core.models import ForecastingModel
   from openstef_core.pipelines import FeaturePipeline, TransformPipeline
   from openstef_core.storage import LocalModelStorage

   # 1. Prepare data
   dataset = create_synthetic_forecasting_dataset()

   # 2. Build the preprocessing pipeline
   preprocessing = FeaturePipeline(
       transforms=[
           # Add holiday features, lag transforms, scaling, etc.
           # See the feature engineering docs for available transforms.
       ]
   )

   # 3. Assemble the forecasting model
   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=preprocessing),
       forecaster=...,          # e.g. ConstantMedianForecaster or XGBForecaster
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
   )

   # 4. Set up model storage
   storage = LocalModelStorage(path=Path("./models"))

   # 5. Create and run the workflow
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_forecast_model",
       run_name="training_run_001",
   )

   workflow.train(dataset)
   forecast: ForecastDataset = workflow.predict(dataset)

.. note::

   The workflow pattern separates *what* the model does (``ForecastingModel``) from
   *how* it is stored and versioned (``LocalModelStorage``, ``MLFlowStorageCallback``).
   This makes it straightforward to swap storage backends without touching model logic.
   See :doc:`deployment` for production storage patterns.

----

.. _breaking-change-4:

Breaking Change 4: Model Storage
----------------------------------

V3 used MLflow as the only storage backend, configured via a URI string passed to each
pipeline call. V4 introduces a ``ModelStorage`` abstraction with pluggable backends.

**Before (V3):**

.. code-block:: python

   # URI passed ad-hoc to every pipeline call
   train_model_pipeline(pj, data, mlflow_tracking_uri="./mlflow_trained_models")
   create_forecast_pipeline(pj, data, mlflow_tracking_uri="./mlflow_trained_models")

**After (V4):**

.. code-block:: python

   from openstef_core.storage import LocalModelStorage, JoblibModelSerializer
   from pathlib import Path

   # Local filesystem storage (development / testing)
   storage = LocalModelStorage(path=Path("./models"))

   # Save and load explicitly
   storage.save_model("my_model", trained_model)
   loaded_model = storage.load_model("my_model")

For MLflow-backed storage in production, attach an ``MLFlowStorageCallback`` to your
workflow instead of passing a URI string. Refer to :doc:`deployment` for the full
production pattern.

----

.. _breaking-change-5:

Breaking Change 5: Visualisation
----------------------------------

V3 included plotting utilities directly in the ``openstef`` package. In V4, visualisation
lives in the optional ``openstef_beam`` package.

**Before (V3):**

.. code-block:: python

   from openstef.plotting import plot_feature_importance, plot_forecast

   plot_forecast(forecast_df)

**After (V4):**

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   plotter.plot(forecast_dataset)

Install the extra dependency if you need it:

.. code-block:: bash

   pip install openstef-beam

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate an existing V3 codebase.

**Step 1 — Update dependencies**

Remove ``openstef`` and ``openstef-dbc`` from your environment. Install ``openstef-core``
and, if you use visualisation, ``openstef-beam``.

.. code-block:: bash

   pip uninstall openstef openstef-dbc
   pip install openstef-core openstef-beam

**Step 2 — Remove all openstef-dbc calls**

Search your codebase for any import from ``openstef_dbc`` or any task-layer import such
as ``openstef.tasks``. These have no V4 equivalent. Replace data fetching with your own
I/O logic (see :doc:`data_integration` for patterns covering S3, Databricks, and
InfluxDB).

**Step 3 — Replace PredictionJobDataClass**

Find every instantiation of ``PredictionJobDataClass`` and ``ModelSpecificationDataClass``.
These classes do not exist in V4. Move the configuration values into the relevant
``ForecastingModel`` constructor arguments and workflow parameters.

**Step 4 — Wrap DataFrames in TimeSeriesDataset**

Find every place you pass a raw DataFrame to a pipeline. Wrap it:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   dataset = TimeSeriesDataset(data=your_dataframe, target_column="load")

**Step 5 — Replace pipeline function calls**

Replace calls to ``train_model_pipeline`` and ``create_forecast_pipeline`` with a
``ForecastingModel`` + ``CustomForecastingWorkflow`` construction. Use the full example
in :ref:`breaking-change-3` as your template.

**Step 6 — Update model storage**

Replace ``mlflow_tracking_uri`` keyword arguments with a ``LocalModelStorage`` or
``MLFlowStorageCallback`` as shown in :ref:`breaking-change-4`.

**Step 7 — Update visualisation imports**

Replace any ``openstef.plotting`` imports with ``openstef_beam.analysis.plots`` as shown
in :ref:`breaking-change-5`.

**Step 8 — Run your tests**

V4 ships ``openstef_core.testing`` utilities including
``create_synthetic_forecasting_dataset``. Use these in your unit tests to avoid needing
real data during CI.

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset

   def test_my_workflow():
       dataset = create_synthetic_forecasting_dataset()
       workflow = build_my_workflow()
       workflow.train(dataset)
       forecast = workflow.predict(dataset)
       assert forecast is not None

----

Quick Reference: V3 → V4 Symbol Map
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 45 10

   * - V3 symbol
     - V4 equivalent
     - Notes
   * - ``PredictionJobDataClass``
     - *(removed)*
     - Config is now per-component
   * - ``ModelSpecificationDataClass``
     - *(removed)*
     - Config is now per-component
   * - ``train_model_pipeline``
     - ``CustomForecastingWorkflow.train``
     - Composable
   * - ``create_forecast_pipeline``
     - ``CustomForecastingWorkflow.predict``
     - Returns ``ForecastDataset``
   * - ``train_model_and_forecast_back_test``
     - ``CustomForecastingWorkflow`` with backtest config
     - See examples
   * - ``pandas.DataFrame`` (pipeline input)
     - ``TimeSeriesDataset``
     - Carries temporal metadata
   * - ``openstef_dbc`` tasks
     - *(removed)*
     - Bring your own I/O
   * - ``openstef.plotting``
     - ``openstef_beam.analysis.plots``
     - Optional dependency
   * - ``mlflow_tracking_uri`` kwarg
     - ``LocalModelStorage`` / ``MLFlowStorageCallback``
     - Explicit storage objects

----

Related Pages
--------------

- :doc:`use_cases` — End-to-end examples using the V4 API for congestion forecasting
  and other common scenarios.
- :doc:`deployment` — Production deployment patterns including MLflow-backed storage
  and containerised workflows.
- :doc:`data_integration` — How to read data from S3, Databricks, and InfluxDB and
  feed it into V4 pipelines.