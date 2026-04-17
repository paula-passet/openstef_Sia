Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural redesign of the library. This guide covers
every breaking change you are likely to encounter, explains the reasoning behind each
one, and provides concrete before/after code examples so you can migrate an existing
V3 codebase systematically.

.. note::

   V4 requires **Python ≥ 3.12**. If your environment runs an older interpreter,
   upgrade Python before attempting any other migration step.

.. contents:: On this page
   :local:
   :depth: 2

----

What Changed and Why
--------------------

V3 shipped as a single ``openstef`` package that bundled pipelines, data classes,
models, and evaluation utilities together. As the library grew, this monolithic layout
made it difficult to depend on only the parts you needed and slowed down the release
cycle for individual components.

V4 splits the library into focused sub-packages that can be installed independently:

- **openstef-core** — dataset abstractions, base model interfaces, preprocessing
  transforms, and the ``ForecastingModel`` / ``ForecastingWorkflow`` orchestration layer.
- **openstef-models** — concrete forecaster implementations (XGBoost, LightGBM, etc.).
- **openstef-beam** — Backtesting, Evaluation, Analysis and Metrics (BEAM) pipelines.
- **openstef-meta** — shared metadata and type definitions used across packages.
- **openstef** — convenience meta-package that installs all of the above.

If you previously ran ``pip install openstef`` you can keep doing so and everything
will be available. If you only need a subset of functionality, install the relevant
sub-package directly.

----

Package Installation
--------------------

Before (V3):

.. code-block:: python

   # pip install openstef
   import openstef

After (V4):

.. code-block:: python

   # Full install (recommended for most users)
   # pip install openstef

   # Or install only what you need:
   # pip install openstef-core          # datasets, base models, pipelines
   # pip install openstef-models        # concrete forecasters
   # pip install openstef-beam          # backtesting & evaluation
   # pip install openstef-beam[baselines]  # includes openstef-meta + openstef-models

----

Breaking Change 1 — PredictionJob Replaced by Dataset Abstractions
-------------------------------------------------------------------

The most impactful change is the removal of ``PredictionJobDataClass`` as the central
configuration object. In V3, a ``PredictionJobDataClass`` dictionary-like object
carried both model configuration *and* data routing information through every pipeline
call. In V4 these concerns are separated:

- **Model configuration** lives inside the forecaster object itself (quantiles,
  hyperparameters, horizon).
- **Data** is wrapped in ``TimeSeriesDataset`` or ``VersionedTimeSeriesDataset``
  objects from ``openstef_core.datasets``.

Before (V3):

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline

   pj = PredictionJobDataClass(**dict(
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
       default_modelspecs=None,
       save_train_forecasts=True,
   ))

   input_data = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   train_data = input_data.iloc[:-200, :]

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

After (V4):

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_core.models.forecasting import ForecastingModel

   # Wrap raw data in a typed dataset
   raw = pd.read_csv("data/input.csv", index_col="index", parse_dates=True)
   dataset = TimeSeriesDataset(data=raw)

   train_dataset = TimeSeriesDataset(data=raw.iloc[:-200, :])
   val_dataset   = TimeSeriesDataset(data=raw.iloc[-200:-100, :])
   test_dataset  = TimeSeriesDataset(data=raw.iloc[-100:, :])

   # Build and train the model — configuration lives on the forecaster
   model = ForecastingModel(forecaster=ConstantMedianForecaster())
   result = model.fit(
       data=train_dataset,
       data_val=val_dataset,
       data_test=test_dataset,
   )

Key differences:

- ``PredictionJobDataClass`` is gone. There is no direct replacement; its fields are
  now distributed between the forecaster constructor and the dataset object.
- ``train_model_pipeline()`` is replaced by ``ForecastingModel.fit()``.
- MLflow tracking is no longer a positional argument; it is handled through the
  ``ForecastingWorkflow`` callback system (see :ref:`workflow-callbacks` below).

----

Breaking Change 2 — Forecast Pipeline Replaced by ``ForecastingModel.predict()``
----------------------------------------------------------------------------------

Before (V3):

.. code-block:: python

   import numpy as np
   import pandas as pd
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Mask the load column to signal "forecast these rows"
   to_forecast = input_data.copy()
   to_forecast.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

After (V4):

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   # Pass the dataset directly — no NaN masking required
   forecast_dataset = model.predict(data=test_dataset)

   # Access the underlying DataFrame
   forecast_df = forecast_dataset.data

The V4 ``predict()`` method returns a ``ForecastDataset`` rather than a plain
``pd.DataFrame``. Use ``.data`` to retrieve the underlying DataFrame when you need
to pass results to downstream code that expects a DataFrame.

----

Breaking Change 3 — Model Persistence and Workflow Callbacks
-------------------------------------------------------------

.. _workflow-callbacks:

V3 used MLflow tracking URIs passed directly to pipeline functions. V4 introduces
``ForecastingWorkflow``, which wraps a ``ForecastingModel`` and manages persistence,
experiment tracking, and custom callbacks through a unified interface.

Before (V3):

.. code-block:: python

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

After (V4):

.. code-block:: python

   from openstef_core.models.forecasting import ForecastingModel
   from openstef_core.workflows.forecasting import ForecastingWorkflow
   from openstef_core.workflows.model_identifier import ModelIdentifier

   workflow = ForecastingWorkflow(
       model=model,
       model_id=ModelIdentifier(name="demand-forecast-287"),
       run_name="training-run-001",
       experiment_tags={"asset": "287", "type": "demand"},
   )

   result = workflow.fit(
       data=train_dataset,
       data_val=val_dataset,
       data_test=test_dataset,
   )

Callbacks registered on the workflow fire at ``pre-fit`` and ``post-fit`` lifecycle
events, giving you a clean extension point for logging, alerting, or custom artifact
storage without modifying pipeline code.

----

Breaking Change 4 — Backtesting and Evaluation (BEAM)
------------------------------------------------------

V3 did not ship a dedicated backtesting framework. Ad-hoc evaluation was typically
done by manually splitting data and calling ``create_forecast_pipeline`` in a loop.
V4 provides ``openstef-beam`` for this purpose.

Before (V3) — manual backtesting loop:

.. code-block:: python

   results = []
   for window_start in backtest_windows:
       train_slice = input_data.loc[:window_start]
       test_slice  = input_data.loc[window_start:]
       fc = create_forecast_pipeline(pj, test_slice,
                                     mlflow_tracking_uri="./mlflow_trained_models")
       results.append(fc)

After (V4) — using ``openstef-beam``:

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   from openstef_beam.backtesting import BacktestConfig
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage

   storage = LocalBenchmarkStorage(base_path=Path("./results"))

   backtest_config = BacktestConfig(
       horizon=timedelta(hours=24),
       window_step=timedelta(days=1),
   )
   evaluation_config = EvaluationConfig()
   analysis_config = AnalysisConfig(
       visualization_providers=[SummaryTableVisualization(name="summary")],
   )

   pipeline = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       storage=storage,
   )

BEAM enforces proper temporal constraints automatically — it will never allow the
model to see future data during a backtest window, which was easy to violate
accidentally in the V3 manual approach.

----

Breaking Change 5 — Import Paths
---------------------------------

Many import paths have changed. The table below lists the most commonly used V3
imports and their V4 equivalents.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - V3 import
     - V4 import
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - Removed — use ``ForecastingModel`` + ``TimeSeriesDataset``
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``openstef_core.models.forecasting.ForecastingModel.fit``
   * - ``openstef.pipeline.create_forecast.create_forecast_pipeline``
     - ``openstef_core.models.forecasting.ForecastingModel.predict``
   * - ``openstef.pipeline.create_forecast.create_basecase_forecast_pipeline``
     - ``openstef_core.models.forecasting.ForecastingModel.predict`` (basecase forecaster)
   * - ``openstef.model.regressors.*``
     - ``openstef_models.models.*``
   * - *(no equivalent)*
     - ``openstef_beam.backtesting.BacktestPipeline``
   * - *(no equivalent)*
     - ``openstef_beam.evaluation.EvaluationPipeline``
   * - *(no equivalent)*
     - ``openstef_beam.benchmarking.BenchmarkPipeline``

----

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order to migrate a V3 project to V4.

**Step 1 — Upgrade Python and install V4**

.. code-block:: bash

   # Ensure Python >= 3.12 is active, then:
   pip install --upgrade openstef

**Step 2 — Replace PredictionJob construction**

Search your codebase for ``PredictionJobDataClass`` and ``dict(id=..., model=...)``.
For each occurrence:

1. Identify which fields were used for model configuration (``model``, ``quantiles``,
   ``horizon_minutes``) and move them to the forecaster constructor.
2. Identify which fields were used for data routing (``lat``, ``lon``,
   ``resolution_minutes``) and encode them in your data loading layer instead.

**Step 3 — Replace pipeline function calls**

- ``train_model_pipeline(pj, data, ...)`` → ``ForecastingModel.fit(data, ...)``
- ``create_forecast_pipeline(pj, data, ...)`` → ``ForecastingModel.predict(data)``

Wrap your ``pd.DataFrame`` inputs in ``TimeSeriesDataset`` before passing them.

**Step 4 — Migrate model persistence**

Replace direct ``mlflow_tracking_uri`` arguments with a ``ForecastingWorkflow``
instance. Register any custom post-training logic as workflow callbacks rather than
code that runs after the pipeline call returns.

**Step 5 — Migrate backtesting**

Replace manual backtest loops with ``openstef_beam.backtesting.BacktestPipeline``.
Configure ``BacktestConfig`` with the same horizon and step sizes you used previously.
Use ``EvaluationPipeline`` to compute metrics — this ensures consistent metric
definitions across experiments.

**Step 6 — Update CI / integration tests**

Run your test suite. The most common remaining failures after the steps above are:

- Code that inspects the ``pj`` dict directly (e.g. ``pj["id"]``) — replace with
  model or dataset attributes.
- Code that expects ``create_forecast_pipeline`` to return a plain ``pd.DataFrame`` —
  call ``.data`` on the returned ``ForecastDataset``.
- MLflow artifact paths hard-coded as strings passed to pipeline functions — move
  these to workflow configuration.

----

[DIAGRAM: V3 vs V4 architecture comparison — left side shows single openstef package with PredictionJob flowing through train_model_pipeline and create_forecast_pipeline; right side shows split packages openstef-core / openstef-models / openstef-beam with TimeSeriesDataset flowing through ForecastingModel.fit and ForecastingModel.predict, with ForecastingWorkflow wrapping the model]

----

Summary of All Breaking Changes
---------------------------------

- ``PredictionJobDataClass`` removed; replaced by ``TimeSeriesDataset`` + forecaster
  configuration.
- ``train_model_pipeline()`` removed; replaced by ``ForecastingModel.fit()``.
- ``create_forecast_pipeline()`` removed; replaced by ``ForecastingModel.predict()``.
- Pipeline functions no longer accept ``mlflow_tracking_uri`` or ``artifact_folder``
  arguments; use ``ForecastingWorkflow`` callbacks instead.
- Forecast results are now ``ForecastDataset`` objects, not plain ``pd.DataFrame``;
  use ``.data`` to unwrap.
- All concrete model classes moved from ``openstef.model.regressors`` to
  ``openstef_models.models``.
- Python < 3.12 is no longer supported.
- Backtesting and evaluation utilities are now in the separate ``openstef-beam``
  package.

----

Related Pages
-------------

- :doc:`use_cases` — end-to-end examples using the V4 API for common forecasting
  scenarios such as congestion forecasting.
- :doc:`deployment` — production deployment patterns including workflow scheduling
  and model registry integration.
- :doc:`data_integration` — reading training data from S3, Databricks, and InfluxDB
  into ``TimeSeriesDataset`` objects.