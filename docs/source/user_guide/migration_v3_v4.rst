Migrating from V3 to V4
========================

OpenSTEF V4 introduces significant breaking changes to improve the library's architecture, make it fully standalone, and modernize its data handling. This guide walks you through every change you need to make when upgrading from V3 to V4.

.. warning::

   V3 and V4 APIs are **not compatible**. Code written for V3 will not work with V4 without modification. Plan dedicated time for migration and testing.

Overview of Breaking Changes
----------------------------

The V4 release restructures OpenSTEF around three core principles: standalone operation (no required database connector), explicit data contracts, and modern Python patterns. The major changes are:

- **Data representation**: V3 uses raw ``pandas.DataFrame`` objects throughout; V4 introduces ``TimeSeriesDataset`` as the primary data container
- **Configuration**: V3's ``PredictionJobDataClass`` is replaced with a cleaner configuration approach
- **Database decoupling**: V3 tightly integrates with ``openstef-dbc``; V4 operates as a standalone library where you provide your own data
- **Pipeline signatures**: All pipeline functions have updated signatures and return types
- **Package structure**: Several modules have been reorganized

.. note::

   If you are starting fresh with OpenSTEF (not migrating from V3), you can skip this page entirely and go straight to the :doc:`use_cases` guide.

Step 1: Update Your Installation
---------------------------------

Remove V3 and install V4:

.. code-block:: bash

   pip uninstall openstef openstef-dbc
   pip install openstef>=4.0

If you relied on ``openstef-dbc`` for database connectivity, you will need to replace those calls with your own data loading logic. See :doc:`data_integration` for patterns using S3, Databricks, InfluxDB, and other sources.

Step 2: Replace PredictionJobDataClass
---------------------------------------

In V3, ``PredictionJobDataClass`` bundled model configuration, location metadata, and forecasting parameters into a single object that was tightly coupled to the database layer.

**V3 (before):**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=2880,
       resolution_minutes=15,
       name="my_forecast",
       save_train_forecasts=True,
   )

**V4 (after):**

In V4, ``PredictionJobDataClass`` still exists but is used differently. The library is now standalone---you no longer need ``openstef-dbc`` to resolve database dependencies. Configuration is passed directly, and model specifications are handled through ``ModelSpecificationDataClass``:

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

   # Prediction job defines WHAT to forecast
   pj = PredictionJobDataClass(
       id=287,
       model="xgb",
       quantiles=[10, 30, 50, 70, 90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=2880,
       resolution_minutes=15,
       name="my_forecast",
       hyper_params={},
       feature_names=None,
       default_modelspecs=None,
       save_train_forecasts=True,
   )

   # Model specifications define HOW to train
   model_specs = ModelSpecificationDataClass(
       id=287,
       hyper_params={"n_estimators": 100, "max_depth": 6},
       feature_names=["load", "temperature", "windspeed"],
   )

The key difference: V4 requires you to be explicit about ``hyper_params``, ``feature_names``, and ``default_modelspecs`` fields. These were previously resolved implicitly through the database connector.

Step 3: Update Pipeline Calls
------------------------------

Pipeline functions in V4 have updated signatures. The most important change is that you must supply data directly---there is no implicit database fetch.

Training Pipeline
^^^^^^^^^^^^^^^^^

**V3 (before):**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline

   # V3: pipeline fetched data via openstef-dbc context
   train_model_pipeline(pj, context)

**V4 (after):**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # You load data yourself
   input_data = pd.read_csv(
       "data/model_input.csv",
       index_col="index",
       parse_dates=True,
   )

   # V4: pass data explicitly
   model, report, model_specs, _ = train_model_pipeline(
       pj=pj,
       input_data=input_data,
   )

Forecast Pipeline
^^^^^^^^^^^^^^^^^

**V3 (before):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # V3: database-coupled
   forecast = create_forecast_pipeline(pj, context)

**V4 (after):**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # You provide input data and the trained model
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=input_data,
       model=model,
       model_specs=model_specs,
   )

.. note::

   All pipeline functions in V4 (``train_model_pipeline``, ``create_forecast_pipeline``, ``create_basecase_forecast_pipeline``, ``create_components_forecast_pipeline``, ``optimize_hyperparameters_pipeline``) follow this same pattern: you provide data and configuration explicitly.

Step 4: Remove openstef-dbc Dependencies
-----------------------------------------

In V3, the ``context`` object from ``openstef-dbc`` handled all data I/O:

.. code-block:: python

   # V3: openstef-dbc provided the context manager
   from openstef_dbc.services.prediction_job import PredictionJobService
   from openstef_dbc.services.model_input import ModelInputService

   pj_service = PredictionJobService(context)
   prediction_jobs = pj_service.get_prediction_jobs()

   input_service = ModelInputService(context)
   input_data = input_service.get_model_input(pj)

In V4, replace these with your own data loading functions:

.. code-block:: python

   # V4: you handle data I/O
   import pandas as pd

   def load_prediction_config():
       """Load prediction job configuration from your own storage."""
       # From a YAML file, database, API, etc.
       return PredictionJobDataClass(**config)

   def load_input_data(pj):
       """Load input data from your own storage."""
       # From S3, InfluxDB, Databricks, CSV, etc.
       return pd.read_parquet(f"s3://bucket/input/{pj.id}.parquet")

For detailed data integration patterns, see :doc:`data_integration`.

Step 5: Update Data Handling
-----------------------------

V4 expects input DataFrames to follow a strict column ordering convention:

- The ``load`` column must be **first**
- The ``horizon`` column must be **last**

Violating this raises ``InputDataWrongColumnOrderError``.

.. code-block:: python

   import pandas as pd

   # Ensure correct column order
   required_first = "load"
   required_last = "horizon"

   cols = input_data.columns.tolist()
   cols.remove(required_first)
   cols.remove(required_last)
   input_data = input_data[[required_first] + cols + [required_last]]

Step 6: Update Model Storage and Loading
------------------------------------------

V3 relied on ``openstef-dbc`` to store and retrieve trained models (typically via MLflow with a database backend). In V4, model persistence is your responsibility:

.. code-block:: python

   import pickle
   from pathlib import Path

   # Save after training
   model_path = Path("models") / f"model_{pj.id}.pkl"
   model_path.parent.mkdir(exist_ok=True)
   with open(model_path, "wb") as f:
       pickle.dump(model, f)

   # Load for forecasting
   with open(model_path, "rb") as f:
       model = pickle.load(f)

You can also continue using MLflow or any other model registry---V4 simply does not mandate one. For production deployment patterns, see :doc:`deployment`.

Migration Checklist
-------------------

Use this checklist to track your migration progress:

- [ ] Update ``openstef`` to V4 and remove ``openstef-dbc``
- [ ] Update all ``PredictionJobDataClass`` instantiations with new required fields (``hyper_params``, ``feature_names``, ``default_modelspecs``)
- [ ] Replace all ``context``-based pipeline calls with explicit data passing
- [ ] Implement your own data loading functions (replacing ``openstef-dbc`` services)
- [ ] Ensure input DataFrame column ordering (``load`` first, ``horizon`` last)
- [ ] Implement your own model storage/loading logic
- [ ] Update any task-level code (``openstef.tasks.*``) that assumed database connectivity
- [ ] Run your test suite and validate forecast outputs match expected ranges

Common Migration Errors
-----------------------

``InputDataWrongColumnOrderError``
   Your input DataFrame columns are not in the expected order. Ensure ``load`` is the first column and ``horizon`` is the last.

``TypeError: missing required argument 'input_data'``
   You are calling a V4 pipeline with V3-style arguments. V4 pipelines require explicit ``input_data`` and often ``model`` and ``model_specs`` parameters.

``ImportError: No module named 'openstef_dbc'``
   You still have code that imports from ``openstef-dbc``. Replace these imports with your own data access layer.

``ValidationError`` on ``PredictionJobDataClass``
   V4 uses Pydantic for validation. Fields that were optional in V3 may now be required, or their types may have changed. Check the field definitions in the API reference.

Getting Help
------------

If you encounter issues during migration:

- Check the `OpenSTEF GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_ for known migration problems
- Review the `example notebooks <https://github.com/OpenSTEF/openstef-offline-example>`_ for working V4 code patterns
- For logging and debugging during migration, see :doc:`logging`