Migrating from V3 to V4
=======================

OpenSTEF V4 is a significant architectural evolution of the library. Where V3 centred on a single ``openstef`` package with pipeline functions and a ``PredictionJobDataClass`` configuration object, V4 introduces a modular multi-package design built around typed datasets, composable workflow objects, and a clean separation between core abstractions, model implementations, and infrastructure integrations. This page covers every breaking change you are likely to encounter and provides step-by-step guidance for updating your code.

.. note::

   This guide focuses on the migration mechanics. For practical end-to-end examples of the new V4 API in action, see :doc:`use_cases`. For production deployment patterns, see :doc:`deployment`.

----

Package Structure
-----------------

The most fundamental change in V4 is the split of the monolithic ``openstef`` package into three focused packages. You will need to update your ``pip install`` commands and all import statements.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Concern
     - V3 package
     - V4 package
   * - Core abstractions, datasets, types
     - ``openstef``
     - ``openstef-core``
   * - Model implementations, workflows
     - ``openstef``
     - ``openstef-models``
   * - Distributed / Beam pipelines
     - *(not available)*
     - ``openstef-beam``

Install the packages you need:

.. code-block:: python

   # Before (V3)
   pip install openstef

   # After (V4) — install only what you need
   pip install openstef-core openstef-models

The top-level import namespaces change accordingly:

.. code-block:: python

   # Before (V3)
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # After (V4)
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

----

Configuration: PredictionJob → ForecastingWorkflowConfig
---------------------------------------------------------

In V3, a prediction job was a plain dictionary promoted to a dataclass. It bundled model type, geographic coordinates, horizon, quantiles, and hyperparameters into a single flat object that was passed to every pipeline function.

V4 replaces this with ``ForecastingWorkflowConfig``, a Pydantic-validated configuration class that lives in ``openstef_models.presets``. The workflow object it produces encapsulates the full train/predict lifecycle rather than being a passive data bag.

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

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   config = ForecastingWorkflowConfig(
       model_id="demand_forecast_v1",
       model="xgboost",                          # "xgboost", "gblinear", "lgbm", etc.
       horizons=[LeadTime.from_string("PT47H")], # ISO 8601 duration strings
       quantiles=[Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_10m",
   )

   workflow = create_forecasting_workflow(config)

Key differences to note:

- Quantiles are now typed ``Q`` objects (floats in ``[0, 1]``) rather than integer percentages.
- Horizons use ISO 8601 duration strings via ``LeadTime.from_string()``, not raw minutes.
- The ``id`` field is replaced by a string ``model_id`` used for MLflow tracking.
- Geographic coordinates are optional and grouped under a ``LocationConfig`` sub-object.
- ``create_forecasting_workflow()`` returns a stateful workflow object — not just a config.

----

Training: Pipeline Functions → Workflow Objects
-----------------------------------------------

V3 exposed training as a standalone function call. You passed the prediction job and a ``pandas.DataFrame`` directly to ``train_model_pipeline()``, and MLflow paths were threaded through as string arguments.

V4 wraps the entire lifecycle — preprocessing, fitting, postprocessing, and optional MLflow storage — inside the workflow object returned by ``create_forecasting_workflow()``. You call ``.fit()`` on it with a ``TimeSeriesDataset``.

**Before (V3):**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline

   input_data = pd.read_csv(
       "data/get_model_input_pid_287.csv",
       index_col="index",
       parse_dates=True,
   )
   train_data = input_data.iloc[:-200, :]  # reserve last ~48 h for evaluation

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
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Wrap your DataFrame in a typed dataset
   raw = pd.read_parquet("data/load_and_features.parquet")
   dataset = VersionedTimeSeriesDataset.from_dataframe(raw, sample_interval=pd.Timedelta("15min"))

   workflow = create_forecasting_workflow(
       ForecastingWorkflowConfig(
           model_id="demand_forecast_v1",
           model="xgboost",
           horizons=[LeadTime.from_string("PT47H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           target_column="load",
       )
   )

   result = workflow.fit(dataset)

The ``fit()`` call returns a ``ModelFitResult`` that carries training metrics and model metadata. MLflow integration is now configured declaratively inside ``ForecastingWorkflowConfig`` via the ``mlflow_storage`` field rather than as ad-hoc string arguments.

----

Forecasting: create_forecast_pipeline → workflow.predict
---------------------------------------------------------

V3 forecasting required reloading the model from MLflow by passing the same ``mlflow_tracking_uri`` used during training. V4 keeps the fitted model inside the workflow object, so prediction is a direct method call.

**Before (V3):**

.. code-block:: python

   import numpy as np
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Mask the target column to simulate a live forecast
   to_forecast_data = input_data.copy()
   to_forecast_data.loc[test_indices, "load"] = np.nan

   forecast = create_forecast_pipeline(
       pj,
       to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   # Build a dataset covering the forecast window
   forecast_raw = pd.read_parquet("data/forecast_features.parquet")
   forecast_dataset = TimeSeriesDataset(
       data=forecast_raw,
       sample_interval=pd.Timedelta("15min"),
   )

   forecast = workflow.predict(forecast_dataset)
   # Returns a ForecastDataset with quantile columns

The returned ``ForecastDataset`` is a validated subclass of ``TimeSeriesDataset``. It carries the forecast values alongside their quantile columns and can be serialised directly with ``.to_parquet()``.

----

Data Handling: DataFrames → TimeSeriesDataset
---------------------------------------------

V3 used plain ``pandas.DataFrame`` objects throughout. V4 introduces ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` from ``openstef_core.datasets`` as the primary data containers. These classes enforce a ``DatetimeIndex``, a consistent ``sample_interval``, and optional ``available_at`` versioning for realistic backtesting.

.. note::

   ``VersionedTimeSeriesDataset`` is particularly important when your feature data (e.g. weather forecasts) arrives at different times than your load measurements. It tracks *when* each data point became available, enabling leak-free backtesting.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Load multiple versioned sources and join them
   load_ds = VersionedTimeSeriesDataset.read_parquet("data/load.parquet")
   weather_ds = VersionedTimeSeriesDataset.read_parquet("data/weather_forecasts.parquet")
   epex_ds = VersionedTimeSeriesDataset.read_parquet("data/epex.parquet")

   # Left join: keep all load timestamps, attach features where available
   combined = VersionedTimeSeriesDataset.concat(
       [load_ds, weather_ds, epex_ds],
       mode="left",
   ).select_version()

   print(combined.data.shape)
   print(combined.feature_names)

----

MLflow Integration
------------------

In V3, MLflow paths were passed as plain strings to each pipeline function call. In V4, MLflow is an optional callback configured once inside ``ForecastingWorkflowConfig``.

**Before (V3):**

.. code-block:: python

   train_model_pipeline(
       pj, train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_trained_models",
       artifact_folder="./mlflow_artifacts",
   )

   create_forecast_pipeline(
       pj, to_forecast_data,
       mlflow_tracking_uri="./mlflow_trained_models",
   )

**After (V4):**

.. code-block:: python

   from pathlib import Path
   from openstef_models.integrations.mlflow import MLFlowStorage
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_core.types import LeadTime, Q

   workflow = create_forecasting_workflow(
       ForecastingWorkflowConfig(
           model_id="demand_forecast_v1",
           model="xgboost",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           target_column="load",
           mlflow_storage=MLFlowStorage(
               tracking_uri="./mlflow_tracking",
               local_artifacts_path=Path("./mlflow_tracking_artifacts"),
           ),
       )
   )

   # Both fit() and predict() now automatically log to MLflow
   workflow.fit(dataset)

Set ``mlflow_storage=None`` to disable MLflow entirely during development.

----

Step-by-Step Migration Workflow
--------------------------------

Follow these steps in order to migrate an existing V3 codebase:

1. **Update dependencies.** Replace ``openstef`` in your ``requirements.txt`` or ``pyproject.toml`` with ``openstef-core`` and ``openstef-models``. Add ``openstef-beam`` only if you use distributed pipelines.

2. **Update all imports.** Replace every ``from openstef.*`` import. Use the mapping in the `Package Structure`_ section above as a reference. Your IDE's "find and replace" across the project is the fastest approach.

3. **Replace PredictionJobDataClass.** Identify every place you construct a ``PredictionJobDataClass`` dict and replace it with a ``ForecastingWorkflowConfig``. Pay attention to quantile units (percentages → fractions) and horizon units (minutes → ``LeadTime`` ISO strings).

4. **Wrap DataFrames in datasets.** Find every ``pd.read_csv`` or ``pd.read_parquet`` call that feeds into a pipeline and wrap the result in ``TimeSeriesDataset`` or ``VersionedTimeSeriesDataset``. Ensure the ``sample_interval`` matches your data resolution.

5. **Replace train_model_pipeline calls.** Swap each ``train_model_pipeline(pj, df, ...)`` call for ``workflow.fit(dataset)``. Move MLflow configuration into ``ForecastingWorkflowConfig``.

6. **Replace create_forecast_pipeline calls.** Swap each ``create_forecast_pipeline(pj, df, ...)`` call for ``workflow.predict(dataset)``.

7. **Update result handling.** V3 returned plain DataFrames; V4 returns typed dataset objects (``ModelFitResult``, ``ForecastDataset``). Access the underlying DataFrame via ``.data`` where needed.

8. **Run your test suite.** Focus first on shape and dtype assertions — the column naming conventions for quantile outputs have changed to reflect fractional quantile values (e.g. ``quantile_0.5`` instead of ``forecast_50``).

.. warning::

   Quantile column names in forecast outputs changed from integer percentages (``forecast_10``, ``forecast_50``) in V3 to fractional notation (``quantile_0.1``, ``quantile_0.5``) in V4. Any downstream code that reads these column names by string must be updated.

----

Quick Reference: Changed Import Paths
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - V3 import
     - V4 import
   * - ``openstef.data_classes.prediction_job.PredictionJobDataClass``
     - ``openstef_models.presets.ForecastingWorkflowConfig``
   * - ``openstef.pipeline.train_model.train_model_pipeline``
     - ``openstef_models.presets.create_forecasting_workflow`` → ``workflow.fit()``
   * - ``openstef.pipeline.create_forecast.create_forecast_pipeline``
     - ``openstef_models.presets.create_forecasting_workflow`` → ``workflow.predict()``
   * - *(plain DataFrame)*
     - ``openstef_core.datasets.TimeSeriesDataset``
   * - *(plain DataFrame with timestamps)*
     - ``openstef_core.datasets.VersionedTimeSeriesDataset``
   * - ``openstef.model.regressors.*``
     - ``openstef_models.models.*``

----

Further Reading
---------------

- :doc:`use_cases` — End-to-end V4 examples for congestion forecasting and other common scenarios.
- :doc:`deployment` — Production deployment patterns using the V4 workflow API.
- :doc:`data_integration` — Reading versioned data from S3, Databricks, and InfluxDB into ``VersionedTimeSeriesDataset``.