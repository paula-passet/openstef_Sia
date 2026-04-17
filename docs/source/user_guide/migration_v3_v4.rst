Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant redesign of the library. The monolithic ``openstef``
package has been replaced by a modular, multi-package architecture, and several
core abstractions — most notably ``PredictionJobDataClass`` and the flat pipeline
functions — have been replaced with composable, typed building blocks. This page
documents every breaking change and provides concrete before/after examples to
help you migrate existing V3 code.

.. note::

   If you are starting a new project, go directly to the
   :doc:`use_cases` page for idiomatic V4 patterns. This page is for
   teams with existing V3 code that needs to be updated.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 shipped as a single ``openstef`` package with a flat pipeline API driven by a
dictionary-like ``PredictionJobDataClass``. While convenient for small scripts,
this design made it difficult to swap components, test in isolation, or integrate
with modern data platforms.

V4 addresses these limitations by:

- **Splitting the library into focused packages** — ``openstef-core``,
  ``openstef-models``, and ``openstef-beam`` — each with a clear responsibility.
- **Replacing ``PredictionJobDataClass`` with typed, composable objects** — a
  ``ForecastingModel``, a ``FeaturePipeline``, and a ``CustomForecastingWorkflow``
  that you assemble yourself.
- **Replacing pandas DataFrames as the primary data contract** with
  ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``, which carry metadata
  about sample intervals and data availability.
- **Making model storage explicit** via ``LocalModelStorage`` or
  ``MLFlowStorageCallback`` rather than implicit side-effects inside pipeline
  functions.

----

Package Structure Changes
--------------------------

V3 used a single installable package. V4 distributes functionality across three
packages that you install according to what you need.

**Before (V3) — single package:**

.. code-block:: python

   # Everything lives under openstef.*
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

**After (V4) — modular packages:**

.. code-block:: python

   # Core data structures and abstractions
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.datasets import ForecastDataset

   # Model building blocks and workflow orchestration
   from openstef_models.workflows import CustomForecastingWorkflow

   # Visualisation and beam-based pipelines
   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

Install only what you need:

.. code-block:: bash

   # Minimal — data structures and model interfaces
   pip install openstef-core

   # Add model implementations and workflow orchestration
   pip install openstef-models

   # Add visualisation and large-scale pipeline utilities
   pip install openstef-beam

.. mermaid:: /diagrams/user_guide/migration_v3_v4_diagram_1.mmd

----

Breaking Change: PredictionJobDataClass Removed
------------------------------------------------

``PredictionJobDataClass`` was the central configuration object in V3. It no
longer exists in V4. Configuration is now expressed through the objects you
compose — the forecaster, the feature pipeline, and the workflow — rather than
through a single dictionary-like dataclass.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47 * 60,
       resolution_minutes=15,
       name="Example",
       hyper_params={},
       feature_names=None,
   )

**After (V4):**

There is no direct replacement object. Instead, you express the same intent
through the components themselves:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.models.forecasting_model import ForecastingModel

   # Model identity and horizon are properties of the workflow and model,
   # not a separate configuration bag.
   workflow = CustomForecastingWorkflow(
       model_id="demand_xgb_v1",
       model=ForecastingModel(
           # ... see full example below
           target_column="load",
           tags={"model": "xgb", "location": "Example"},
       ),
   )

See the :ref:`full-workflow-example` section below for a complete working
example.

----

Breaking Change: Flat Pipeline Functions Replaced
--------------------------------------------------

V3 exposed ``train_model_pipeline()`` and ``create_forecast_pipeline()`` as
top-level functions that accepted a ``PredictionJobDataClass`` and a
``pd.DataFrame``. V4 replaces these with methods on ``CustomForecastingWorkflow``.

**Before (V3) — training:**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(**pj_dict)
   input_data = pd.read_csv("data/load.csv", index_col="index", parse_dates=True)

   model, report, train_data, val_data, test_data, scores = train_model_pipeline(
       pj, input_data
   )

**After (V4) — training:**

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.workflows import CustomForecastingWorkflow

   dataset = VersionedTimeSeriesDataset.read_parquet("data/load.parquet")

   workflow = CustomForecastingWorkflow(
       model_id="demand_xgb_v1",
       model=model,  # ForecastingModel instance — see full example
   )
   result = workflow.fit(dataset)

**Before (V3) — forecasting:**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   forecast_df = create_forecast_pipeline(pj, input_data, model, modelspecs)

**After (V4) — forecasting:**

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   forecast: ForecastDataset = workflow.predict(dataset)
   print(forecast.data.tail())

----

Breaking Change: DataFrame → TimeSeriesDataset
----------------------------------------------

V3 used plain ``pd.DataFrame`` objects as the data contract throughout the
library. V4 introduces ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``
as first-class data structures. These carry the sample interval and, for
versioned datasets, an ``available_at`` column that records when each
observation became available — enabling realistic backtesting without data
leakage.

**Before (V3):**

.. code-block:: python

   import pandas as pd

   input_data = pd.read_csv(
       "data/load.csv", index_col="index", parse_dates=True
   )
   # Pass raw DataFrame directly to pipeline functions
   forecast_df = create_forecast_pipeline(pj, input_data, model, modelspecs)

**After (V4):**

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Option A: load from parquet (recommended for production)
   dataset = VersionedTimeSeriesDataset.read_parquet("data/load.parquet")

   # Option B: wrap an existing DataFrame
   raw_df = pd.read_csv("data/load.csv", index_col="timestamp", parse_dates=True)
   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw_df, sample_interval=timedelta(minutes=15)
   )

   # Combine multiple sources with a left join, then materialise
   combined = VersionedTimeSeriesDataset.concat(
       [load_dataset, weather_dataset, epex_dataset],
       mode="left",
   ).select_version()

.. note::

   ``select_version()`` materialises the lazy versioned dataset into a concrete
   ``TimeSeriesDataset``. Call it only when you need a snapshot — for example,
   just before passing data to a model. Keeping data in ``VersionedTimeSeriesDataset``
   form for as long as possible avoids the O(n²) memory cost of eagerly joining
   misaligned time series.

----

Breaking Change: Model Storage is Now Explicit
----------------------------------------------

In V3, trained models were stored as a side-effect of calling
``train_model_pipeline()``, controlled by fields on the prediction job. In V4,
storage is an explicit ``callback`` attached to the workflow.

**Before (V3):**

.. code-block:: python

   # Storage happened implicitly — controlled by prediction job fields
   pj = PredictionJobDataClass(
       id=287,
       # MLflow URI was set via environment variable or openstef-dbc config
       ...
   )
   model, report, *_ = train_model_pipeline(pj, input_data)

**After (V4) — local storage:**

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.model_storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("models/"))
   workflow = CustomForecastingWorkflow(
       model_id="demand_xgb_v1",
       model=model,
       callbacks=[storage],
   )
   workflow.fit(dataset)

**After (V4) — MLflow storage:**

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.callbacks import MLFlowStorageCallback
   from openstef_models.model_storage import MLFlowStorage
   from pathlib import Path

   mlflow_callback = MLFlowStorageCallback(
       storage=MLFlowStorage(
           tracking_uri="http://mlflow.example.com",
           local_artifacts_path=Path("mlflow_artifacts/"),
       ),
       model_reuse_enable=True,
       model_selection_enable=True,
   )
   workflow = CustomForecastingWorkflow(
       model_id="demand_xgb_v1",
       model=model,
       callbacks=[mlflow_callback],
   )

----

.. _full-workflow-example:

Full Before/After Workflow Example
------------------------------------

The following pair of examples shows a complete train-then-forecast workflow in
both versions. Use this as a reference when porting an existing script.

**Before (V3) — complete script:**

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # 1. Configure via prediction job
   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=2880,
       resolution_minutes=15,
       name="Substation_A",
       hyper_params={},
       feature_names=None,
       save_train_forecasts=True,
   )

   # 2. Load data as a plain DataFrame
   input_data = pd.read_csv(
       "data/load.csv", index_col="index", parse_dates=True
   )
   train_data = input_data.iloc[:-192]   # all but last 48 h
   forecast_data = input_data.iloc[-192:]

   # 3. Train — model is stored as a side-effect
   model, report, train_df, val_df, test_df, scores = train_model_pipeline(
       pj, train_data
   )

   # 4. Forecast
   forecast_df = create_forecast_pipeline(pj, forecast_data, model, None)
   print(forecast_df.head())

**After (V4) — complete script:**

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   import pandas as pd
   from openstef_core.datasets import ForecastDataset, VersionedTimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.callbacks import MLFlowStorageCallback
   from openstef_models.model_storage import MLFlowStorage
   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)

   # 1. Load data — combine load measurements with weather forecasts
   load_ds = VersionedTimeSeriesDataset.read_parquet("data/load.parquet")
   weather_ds = VersionedTimeSeriesDataset.read_parquet("data/weather.parquet")

   dataset = VersionedTimeSeriesDataset.concat(
       [load_ds, weather_ds], mode="left"
   ).select_version()

   # 2. Build the forecasting model with explicit pre/post-processing
   #    (see use_cases page for full FeaturePipeline configuration)
   model = ForecastingModel(
       target_column="load",
       tags={"model": "xgb", "location": "Substation_A"},
   )

   # 3. Attach storage as an explicit callback
   mlflow_cb = MLFlowStorageCallback(
       storage=MLFlowStorage(
           tracking_uri="http://mlflow.example.com",
           local_artifacts_path=Path("mlflow_artifacts/"),
       ),
       model_reuse_enable=True,
   )

   # 4. Assemble and run the workflow
   workflow = CustomForecastingWorkflow(
       model_id="demand_xgb_v1",
       model=model,
       callbacks=[mlflow_cb],
   )

   result = workflow.fit(dataset)
   if result is not None:
       logger.info("Metrics:\n%s", result.metrics_test.to_dataframe())

   # 5. Forecast
   forecast: ForecastDataset = workflow.predict(dataset)
   print(forecast.data.tail())

   # 6. Visualise using the built-in plotter
   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=dataset.data["load"])
       .add_model(
           model_name="xgb",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.write_html("forecast.html")

----

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order when porting a V3 codebase.

1. **Update dependencies.** Remove ``openstef`` from your requirements and add
   ``openstef-core``, ``openstef-models``, and (if needed) ``openstef-beam``.

2. **Replace all ``PredictionJobDataClass`` instantiations.** Identify every
   place a prediction job is constructed and note which fields are used. Map
   those fields to the appropriate V4 component (model type → forecaster class,
   quantiles → postprocessing step, horizon → dataset configuration).

3. **Wrap your DataFrames.** Replace ``pd.read_csv`` / ``pd.read_parquet`` calls
   that feed into pipelines with ``VersionedTimeSeriesDataset.read_parquet()``
   or ``VersionedTimeSeriesDataset.from_dataframe()``. Ensure your data has a
   ``DatetimeIndex`` named ``timestamp``.

4. **Replace ``train_model_pipeline()`` calls.** Construct a
   ``CustomForecastingWorkflow`` with a ``ForecastingModel`` and call
   ``workflow.fit(dataset)``.

5. **Replace ``create_forecast_pipeline()`` calls.** Call
   ``workflow.predict(dataset)`` on the same workflow instance. The return type
   is ``ForecastDataset``, not a ``pd.DataFrame`` — access ``.data`` for the
   underlying frame.

6. **Make storage explicit.** Remove any implicit storage configuration from
   prediction job fields and attach a ``LocalModelStorage`` or
   ``MLFlowStorageCallback`` to the workflow.

7. **Update visualisation code.** If you used ``plot_feature_importance()`` or
   similar V3 helpers, replace them with the ``ForecastTimeSeriesPlotter`` from
   ``openstef_beam.analysis.plots``.

8. **Run your test suite.** Pay particular attention to any code that inspects
   the raw return values of the old pipeline functions — the tuple
   ``(model, report, train_df, val_df, test_df, scores)`` no longer exists.
   Use ``result.metrics_test`` and ``result.metrics_full`` from the
   ``ModelFitResult`` returned by ``workflow.fit()`` instead.

----

Quick Reference: V3 → V4 Symbol Map
-------------------------------------

+-----------------------------------------------+--------------------------------------------------+
| V3 symbol                                     | V4 replacement                                   |
+===============================================+==================================================+
| ``openstef.data_classes.prediction_job``      | No direct replacement — see composable objects   |
|   ``PredictionJobDataClass``                  | below                                            |
+-----------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.train_model``             | ``openstef_models.workflows``                    |
|   ``train_model_pipeline()``                  |   ``CustomForecastingWorkflow.fit()``            |
+-----------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.create_forecast``         | ``openstef_models.workflows``                    |
|   ``create_forecast_pipeline()``              |   ``CustomForecastingWorkflow.predict()``        |
+-----------------------------------------------+--------------------------------------------------+
| ``pd.DataFrame`` (pipeline data contract)     | ``openstef_core.datasets``                       |
|                                               |   ``TimeSeriesDataset`` /                        |
|                                               |   ``VersionedTimeSeriesDataset``                 |
+-----------------------------------------------+--------------------------------------------------+
| Implicit MLflow storage via prediction job    | ``openstef_models.callbacks``                    |
|                                               |   ``MLFlowStorageCallback``                      |
+-----------------------------------------------+--------------------------------------------------+
| ``openstef.metrics.metrics``                  | ``result.metrics_test`` /                        |
|                                               |   ``result.metrics_full`` on ``ModelFitResult``  |
+-----------------------------------------------+--------------------------------------------------+

----

Related Pages
-------------

- :doc:`use_cases` — idiomatic V4 patterns for congestion forecasting and other
  common scenarios, written from scratch without V3 assumptions.
- :doc:`data_integration` — how to read data from S3, Databricks, and InfluxDB
  into ``VersionedTimeSeriesDataset`` for use with V4 workflows.
- :doc:`deployment` — production deployment patterns including containerisation
  and scheduling for V4-based forecasting services.