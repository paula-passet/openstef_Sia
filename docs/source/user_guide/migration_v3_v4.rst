Migrating from V3 to V4
=======================

OpenSTEF V4 represents a major architectural redesign focused on making the library more modular, flexible, and easier to integrate into diverse production environments. This guide walks through the key breaking changes and provides step-by-step migration instructions with before/after code examples.

Overview of Changes
-------------------

V4 introduces several fundamental changes that affect how you use OpenSTEF:

**Data handling**: V3 used pandas DataFrames directly throughout the API. V4 introduces ``TimeSeriesDataset``, a structured container that encapsulates time series data with metadata and validation.

**Configuration**: V3 relied on ``PredictionJobDataClass`` to configure forecasting tasks. V4 removes this concept entirely, replacing it with more focused configuration objects like ``ModelSpecification``.

**Database integration**: V3 included tight coupling with openstef-dbc for database operations. V4 is a standalone library with no database dependencies, giving you complete control over data persistence.

**Package structure**: V4 reorganizes modules for better separation of concerns, moving away from task-oriented pipelines toward composable components.

Breaking Changes
----------------

Data Input: DataFrame to TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most pervasive change is the shift from pandas DataFrames to ``TimeSeriesDataset``.

**V3 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Load data as DataFrame
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   
   # Pass DataFrame directly to pipeline
   model = train_model_pipeline(pj, input_data)

**V4 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train import train_pipeline
   
   # Load data as DataFrame
   df = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset.from_dataframe(
       df,
       target_column='load',
       datetime_column=df.index
   )
   
   # Pass dataset to pipeline
   model = train_pipeline(model_spec, dataset)

The ``TimeSeriesDataset`` provides validation, metadata tracking, and a consistent interface across all OpenSTEF functions. It ensures your data has the required structure before training or prediction begins.

Configuration: PredictionJobDataClass Removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3's ``PredictionJobDataClass`` mixed concerns—it contained model configuration, location metadata, database identifiers, and forecast parameters. V4 separates these into focused objects.

**V3 approach:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       hyper_params={},
       feature_names=None
   )
   
   model = train_model_pipeline(pj, input_data)

**V4 approach:**

.. code-block:: python

   from openstef.model.specification import ModelSpecification
   
   model_spec = ModelSpecification(
       model_type='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       horizon_minutes=47*60,
       resolution_minutes=15,
       hyperparameters={}
   )
   
   model = train_pipeline(model_spec, dataset)

Location metadata (``lat``, ``lon``) and forecast type are no longer part of the model configuration—they're application-level concerns you manage separately. This makes OpenSTEF more flexible for different deployment scenarios.

Pipeline Functions: Simplified Signatures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 pipeline functions have cleaner signatures with fewer parameters. Database and MLflow integration is now optional and handled separately.

**V3 training pipeline:**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   
   model = train_model_pipeline(
       pj,
       input_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlflow_models",
       artifact_folder="./artifacts"
   )

**V4 training pipeline:**

.. code-block:: python

   from openstef.pipeline.train import train_pipeline
   from openstef.model.serializer import MLflowSerializer
   
   # Train the model
   model, report = train_pipeline(model_spec, dataset)
   
   # Optionally persist with MLflow
   serializer = MLflowSerializer(tracking_uri="./mlflow_models")
   serializer.save_model(model, model_spec)

Persistence is now explicit and decoupled from training. You can train models without any storage dependencies, making testing and experimentation simpler.

**V3 prediction pipeline:**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./mlflow_models"
   )

**V4 prediction pipeline:**

.. code-block:: python

   from openstef.pipeline.predict import predict_pipeline
   from openstef.model.serializer import MLflowSerializer
   
   # Load the model
   serializer = MLflowSerializer(tracking_uri="./mlflow_models")
   model = serializer.load_model(model_id)
   
   # Generate predictions
   forecast = predict_pipeline(model, dataset)

Import Path Changes
^^^^^^^^^^^^^^^^^^^

Several modules have been reorganized:

- ``openstef.data_classes`` → ``openstef.model.specification`` (for model config)
- ``openstef.pipeline.train_model`` → ``openstef.pipeline.train``
- ``openstef.pipeline.create_forecast`` → ``openstef.pipeline.predict``
- Database-related modules removed entirely

Step-by-Step Migration Workflow
--------------------------------

1. Update Dependencies
^^^^^^^^^^^^^^^^^^^^^^

Update your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # Old
   openstef==3.4.72
   openstef-dbc==3.x.x
   
   # New
   openstef>=4.0.0

Remove ``openstef-dbc`` if present—V4 has no database dependencies.

2. Refactor Data Loading
^^^^^^^^^^^^^^^^^^^^^^^^^

Wrap your DataFrame loading code with ``TimeSeriesDataset``:

.. code-block:: python

   # Add this import
   from openstef.data.dataset import TimeSeriesDataset
   
   # After loading your DataFrame
   df = load_your_data()  # Your existing data loading logic
   
   # Wrap it
   dataset = TimeSeriesDataset.from_dataframe(
       df,
       target_column='load',  # Your target variable name
       datetime_column=df.index
   )

3. Replace PredictionJobDataClass
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract model-specific configuration into ``ModelSpecification``:

.. code-block:: python

   # Old V3 code
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
       hyper_params={'max_depth': 5}
   )
   
   # New V4 code
   from openstef.model.specification import ModelSpecification
   
   model_spec = ModelSpecification(
       model_type='xgb',
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,
       resolution_minutes=15,
       hyperparameters={'max_depth': 5}
   )
   
   # Store id, location, etc. separately in your application
   forecast_id = 287

4. Update Training Code
^^^^^^^^^^^^^^^^^^^^^^^^

Replace ``train_model_pipeline`` with ``train_pipeline``:

.. code-block:: python

   # Old V3
   from openstef.pipeline.train_model import train_model_pipeline
   
   model = train_model_pipeline(
       pj, 
       train_data,
       mlflow_tracking_uri="./mlflow"
   )
   
   # New V4
   from openstef.pipeline.train import train_pipeline
   from openstef.model.serializer import MLflowSerializer
   
   model, report = train_pipeline(model_spec, dataset)
   
   # Separate persistence step
   if save_model:
       serializer = MLflowSerializer(tracking_uri="./mlflow")
       serializer.save_model(model, model_spec, metadata={'id': forecast_id})

5. Update Prediction Code
^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace ``create_forecast_pipeline`` with ``predict_pipeline``:

.. code-block:: python

   # Old V3
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./mlflow"
   )
   
   # New V4
   from openstef.pipeline.predict import predict_pipeline
   from openstef.model.serializer import MLflowSerializer
   
   # Load model separately
   serializer = MLflowSerializer(tracking_uri="./mlflow")
   model = serializer.load_model(model_id)
   
   # Generate forecast
   forecast = predict_pipeline(model, dataset)

6. Handle Database Operations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you used openstef-dbc in V3, you'll need to implement data loading and persistence yourself. V4 is storage-agnostic.

See :doc:`data_integration` for patterns on reading from various data sources (S3, Databricks, InfluxDB, etc.).

Common Migration Patterns
--------------------------

Batch Processing
^^^^^^^^^^^^^^^^

If you process multiple forecasts in V3:

.. code-block:: python

   # V3 pattern
   for pj in prediction_jobs:
       input_data = load_data_from_db(pj.id)
       forecast = create_forecast_pipeline(pj, input_data)
       save_forecast_to_db(pj.id, forecast)

Migrate to V4:

.. code-block:: python

   # V4 pattern
   for forecast_config in forecast_configs:
       df = load_data(forecast_config['id'])  # Your data loading
       dataset = TimeSeriesDataset.from_dataframe(df, target_column='load')
       
       model = load_model(forecast_config['model_id'])  # Your model loading
       forecast = predict_pipeline(model, dataset)
       
       save_forecast(forecast_config['id'], forecast)  # Your persistence

Feature Engineering
^^^^^^^^^^^^^^^^^^^

V3 and V4 both support feature engineering, but the API differs slightly:

.. code-block:: python

   # V3
   from openstef.feature_engineering.apply_features import apply_features
   
   data_with_features = apply_features(input_data, pj)
   
   # V4
   from openstef.feature_engineering.feature_applicator import FeatureApplicator
   
   applicator = FeatureApplicator(model_spec)
   dataset_with_features = applicator.apply_features(dataset)

Testing Your Migration
-----------------------

After migrating, verify your code works correctly:

1. **Compare predictions**: Run both V3 and V4 on the same data and compare outputs. Small numerical differences are expected due to dependency updates, but overall patterns should match.

2. **Check model performance**: Retrain models with V4 and compare metrics from the training report.

3. **Validate data flow**: Ensure ``TimeSeriesDataset`` correctly captures your data structure—check column names, datetime index, and missing value handling.

4. **Test edge cases**: Verify behavior with missing data, short time series, and unusual input patterns.

Getting Help
------------

If you encounter issues during migration:

- Check the V4 API reference for detailed function signatures
- Review the example notebooks for V4 usage patterns
- Open an issue on GitHub with V3/V4 code comparison

For production deployment considerations, see :doc:`deployment`. For logging configuration changes, see :doc:`logging`.