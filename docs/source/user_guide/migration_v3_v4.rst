Migration Guide: V3 to V4
==========================

OpenSTEF V4 is a significant redesign of the library. The monolithic ``openstef`` package
has been split into focused sub-packages, the pipeline API has moved from standalone
functions to composable classes, and the data model has shifted from plain DataFrames
to typed dataset objects. This page walks through every breaking change and shows
exactly what to update in your code.

.. note::

   This guide covers the ``openstef`` → ``openstef-core`` / ``openstef-models``
   transition. For deployment patterns using the new API, see :doc:`deployment`.
   For connecting data sources to the new dataset types, see :doc:`data_integration`.

----

Package Structure
-----------------

The single ``openstef`` package has been decomposed into two independently installable
packages. Update your ``requirements.txt`` or ``pyproject.toml`` accordingly.

**Before (V3):**

.. code-block:: bash

   pip install openstef

**After (V4):**

.. code-block:: bash

   # Core abstractions, base classes, and dataset types
   pip install openstef-core

   # Forecasting models, pipelines, and evaluation
   pip install openstef-models

Most application code will depend on both. The split allows downstream projects to
depend only on ``openstef-core`` when implementing custom models without pulling in
the full model zoo.

----

Import Paths
------------

Every import path has changed. The table below covers the most commonly used symbols.

+----------------------------------------------+--------------------------------------------------+
| V3 import                                    | V4 import                                        |
+==============================================+==================================================+
| ``openstef.data_classes.prediction_job``     | ``openstef_core.prediction_job``                 |
|   ``PredictionJobDataClass``                 |   *(see PredictionJob section below)*            |
+----------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.train_model``            | ``openstef_models.models.forecasting``           |
|   ``train_model_pipeline``                   |   ``ForecastingModel``                           |
+----------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.create_forecast``        | ``openstef_models.models.forecasting``           |
|   ``create_forecast_pipeline``               |   ``ForecastingModel.predict``                   |
+----------------------------------------------+--------------------------------------------------+
| ``openstef.pipeline.create_forecast``        | ``openstef_models.models.forecasting``           |
|   ``create_basecase_forecast_pipeline``      |   ``BaseForecastingModel``                       |
+----------------------------------------------+--------------------------------------------------+
| ``openstef_models.models.forecasting``       | ``openstef_models.models.forecasting``           |
|   ``OpenstfRegressor``                       |   ``BaseForecastingModel``                       |
+----------------------------------------------+--------------------------------------------------+

----

PredictionJob and Configuration
--------------------------------

V3 used ``PredictionJobDataClass`` — a plain Pydantic dataclass constructed from a
dictionary — to carry all job configuration. V4 replaces this with structured
configuration objects that separate concerns (model identity, quantiles, horizons,
evaluation windows) and are passed directly to the relevant pipeline components.

**Before (V3):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

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

**After (V4):**

.. code-block:: python

   from openstef_models.models.forecasting import ForecastingModel
   from openstef_core.mixins.predictor import Predictor

   # Configuration is now passed directly to the model and pipeline objects.
   # Quantiles, lead times, and evaluation windows are first-class types.
   from openstef_models.evaluation.config import EvaluationConfig, AvailableAt, LeadTime, Window
   from datetime import timedelta

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

.. note::

   The flat ``PredictionJobDataClass`` dictionary is gone. If you stored prediction
   job configs in a database or config file as dictionaries, you will need a one-time
   migration step to map the old keys to the new typed objects.

----

Training Pipeline
-----------------

V3 exposed training as a module-level function. V4 uses a ``ForecastingModel`` class
whose ``fit`` method accepts typed ``TimeSeriesDataset`` objects instead of raw
DataFrames.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline

   pj = PredictionJobDataClass(**{...})  # as above

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )

   # Split manually before passing to the pipeline
   train_data = input_data.iloc[:-200, :]

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets.time_series import TimeSeriesDataset
   from openstef_models.models.forecasting import ForecastingModel

   raw = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )

   # Wrap DataFrames in typed dataset objects
   train_ds = TimeSeriesDataset(data=raw.iloc[:-200, :])
   val_ds   = TimeSeriesDataset(data=raw.iloc[-200:-48, :])
   test_ds  = TimeSeriesDataset(data=raw.iloc[-48:, :])

   # Instantiate and train the model
   model = ForecastingModel(...)   # pass preprocessor, forecaster, postprocessor
   result = model.fit(
       data=train_ds,
       data_val=val_ds,
       data_test=test_ds,
   )

Key differences:

- ``train_model_pipeline()`` → ``ForecastingModel.fit()``
- Raw ``pd.DataFrame`` → ``TimeSeriesDataset``
- MLflow tracking URI is now configured on the workflow/storage layer, not passed
  directly to the pipeline function (see :doc:`deployment`)
- Train/val/test splitting is the caller's responsibility, making the boundary explicit

----

Forecasting Pipeline
--------------------

V3's ``create_forecast_pipeline`` loaded a model from MLflow by prediction job ID and
returned a DataFrame. V4 separates model storage from prediction: you load the model
yourself and call ``predict``.

**Before (V3):**

.. code-block:: python

   import numpy as np
   import pandas as pd
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(**{...})

   to_forecast_data = input_data.copy()
   to_forecast_data.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_core.datasets.time_series import TimeSeriesDataset
   from openstef_models.models.forecasting import ForecastingModel

   # Load a previously fitted model (storage integration is separate)
   model: ForecastingModel = ...   # loaded via your storage backend

   forecast_ds = TimeSeriesDataset(data=to_forecast_data)
   predictions = model.predict(data=forecast_ds)

.. note::

   ``predictions`` is a ``ForecastDataset``, not a plain DataFrame. Access the
   underlying data via ``predictions.data`` when you need DataFrame-compatible output.

----

Model Serialisation and MLflow
-------------------------------

V3 passed ``mlflow_tracking_uri`` and ``artifact_folder`` directly to pipeline
functions. V4 introduces a dedicated storage and workflow layer that wraps the model.

**Before (V3):**

.. code-block:: python

   train, val, test = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

**After (V4):**

.. code-block:: python

   from openstef_models.workflows.forecasting import ForecastingWorkflow, ModelIdentifier

   workflow = ForecastingWorkflow(
       model=model,
       model_id=ModelIdentifier(id="287"),
       run_name="demand-forecast-example",
       experiment_tags={"forecast_type": "demand"},
   )

   result = workflow.fit(data=train_ds, data_val=val_ds, data_test=test_ds)

The ``ForecastingWorkflow`` handles callback execution (including MLflow logging)
around the ``fit`` and ``predict`` calls. Storage backends are configured once on the
workflow rather than threaded through every function call.

----

Feature Contributions (Explainability)
---------------------------------------

V3 generated feature-importance HTML reports as side effects of training. V4 exposes
contributions as a first-class method.

**Before (V3):** Reports were written to ``artifact_folder`` automatically during
``train_model_pipeline``. There was no programmatic API to retrieve contribution
values at prediction time.

**After (V4):**

.. code-block:: python

   contributions = model.predict_contributions(data=forecast_ds)
   # Returns a TimeSeriesDataset with per-sample feature contributions

.. note::

   Not all model types support ``predict_contributions``. Models that do not will
   raise ``NotImplementedError``. Check ``model.get_explainable_components()`` to
   inspect which sub-components expose explainability.

----

Backtesting
-----------

V3 had no built-in backtesting pipeline. V4 ships ``BacktestPipeline`` in
``openstef-models``.

**After (V4):**

.. code-block:: python

   from openstef_models.backtesting.pipeline import BacktestPipeline
   from openstef_core.datasets.versioned_time_series import VersionedTimeSeriesDataset

   backtest = BacktestPipeline(config=backtest_config, forecaster=model)
   results = backtest.run(dataset=versioned_dataset)

   # results is a TimeSeriesDataset indexed by available_at and lead_time
   print(results.data.head())

See :doc:`use_cases` for a worked backtesting example.

----

Step-by-Step Migration Workflow
---------------------------------

Follow these steps in order to migrate an existing V3 codebase.

1. **Update dependencies.** Replace ``openstef`` with ``openstef-core`` and
   ``openstef-models`` in your dependency file. Run ``pip install openstef-core openstef-models``
   and confirm the old ``openstef`` package is uninstalled.

2. **Fix import paths.** Use the table in the `Import Paths`_ section as a reference.
   A project-wide search for ``from openstef.`` and ``import openstef.`` will surface
   every location that needs updating.

3. **Replace PredictionJobDataClass construction.** Identify every place a
   ``PredictionJobDataClass`` dict is built and map the fields to the new typed
   configuration objects. Pay particular attention to ``quantiles``, ``horizon_minutes``,
   and ``resolution_minutes`` — these become ``Quantile``, ``LeadTime``, and
   ``timedelta`` types respectively.

4. **Wrap DataFrames in TimeSeriesDataset.** Find every call to a V3 pipeline function
   and wrap the DataFrame arguments in ``TimeSeriesDataset``. Ensure the DataFrame
   index is a ``DatetimeIndex`` before wrapping.

5. **Replace pipeline function calls.** Swap ``train_model_pipeline`` for
   ``ForecastingModel.fit`` and ``create_forecast_pipeline`` for
   ``ForecastingModel.predict``, following the examples in the `Training Pipeline`_
   and `Forecasting Pipeline`_ sections above.

6. **Migrate MLflow configuration.** Remove ``mlflow_tracking_uri`` and
   ``artifact_folder`` keyword arguments from pipeline calls. Configure a
   ``ForecastingWorkflow`` with the appropriate storage backend instead.

7. **Run your test suite.** The new API is stricter about types. Expect
   ``ValidationError`` from Pydantic if any configuration values are out of range,
   and ``TypeError`` if a raw DataFrame is passed where a ``TimeSeriesDataset`` is
   expected.

.. note:: [DIAGRAM: Step-by-step migration flow from V3 monolith to V4 split-package architecture, showing the mapping of V3 pipeline functions to V4 class methods and dataset types]

----

Quick Reference: Removed Symbols
----------------------------------

The following V3 symbols have no direct equivalent and require a design change rather
than a simple rename.

- ``openstef.pipeline.train_model.train_model_pipeline`` — use ``ForecastingModel.fit``
- ``openstef.pipeline.create_forecast.create_forecast_pipeline`` — use ``ForecastingModel.predict``
- ``openstef.pipeline.create_forecast.create_basecase_forecast_pipeline`` — use ``BaseForecastingModel``
- ``openstef.data_classes.prediction_job.PredictionJobDataClass`` — use typed config objects
- ``OpenstfRegressor`` — use ``BaseForecastingModel``

.. warning::

   The ``check_old_model_age`` parameter from ``train_model_pipeline`` has no V4
   equivalent. Model age checks should be implemented in a ``ForecastingCallback``
   registered on the ``ForecastingWorkflow``.

----

Related Pages
-------------

- :doc:`use_cases` — end-to-end examples using the V4 API, including backtesting and
  congestion forecasting
- :doc:`deployment` — configuring storage backends and MLflow tracking with
  ``ForecastingWorkflow``
- :doc:`data_integration` — reading from S3, Databricks, and InfluxDB into
  ``TimeSeriesDataset``