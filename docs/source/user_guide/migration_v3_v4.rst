Migration Guide: V3 to V4
==========================

OpenSTEF V4 represents a major architectural shift from V3, introducing breaking changes that require code modifications. This guide walks you through the key changes and provides practical migration steps with before/after examples.

Overview of Changes
-------------------

V4 fundamentally restructures how you work with OpenSTEF as a library:

- **Data handling**: V3's pandas DataFrame approach is replaced by the ``TimeSeriesDataset`` abstraction
- **Configuration**: The ``PredictionJobDataClass`` concept is removed in favor of direct pipeline configuration
- **Database integration**: V3's ``openstef-dbc`` integration is removed - V4 is a standalone library
- **Package structure**: Core functionality moves from tasks to pipelines, emphasizing library usage over application patterns

These changes make OpenSTEF more flexible and easier to integrate into diverse production environments, but require updating existing code.

Key Breaking Changes
--------------------

Data Input: DataFrame to TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 accepted raw pandas DataFrames throughout the API. V4 introduces ``TimeSeriesDataset``, a structured container that explicitly defines target variables, features, and metadata.

**V3 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Load raw DataFrame
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_data = input_data.iloc[:-200, :]
   
   # Pass DataFrame directly to pipeline
   models = train_model_pipeline(pj, train_data)

**V4 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train_model import train_model_pipeline_core
   
   # Load raw DataFrame
   df = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_df = df.iloc[:-200, :]
   
   # Create TimeSeriesDataset with explicit structure
   dataset = TimeSeriesDataset(
       data=train_df,
       target_column='load',
       feature_columns=['temperature', 'humidity', 'wind_speed']
   )
   
   # Pass dataset to pipeline
   model, metrics = train_model_pipeline_core(dataset, config)

The ``TimeSeriesDataset`` makes data structure explicit and enables better validation. You must identify which columns are targets versus features when creating the dataset.

Configuration: PredictionJobDataClass Removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 used ``PredictionJobDataClass`` to bundle all configuration. V4 removes this abstraction - you configure pipelines directly with dictionaries or configuration objects.

**V3 approach:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       name="backtest",
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       hyper_params={},
       feature_names=None
   )
   
   models = train_model_pipeline(pj, train_data)

**V4 approach:**

.. code-block:: python

   # Configuration as dictionary
   config = {
       'model_type': 'xgb',
       'quantiles': [0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       'forecast_type': 'demand',
       'horizon_minutes': 47*60,
       'resolution_minutes': 15,
       'hyper_params': {}
   }
   
   model, metrics = train_model_pipeline_core(dataset, config)

Configuration is now passed directly to pipeline functions. Location metadata (``lat``, ``lon``) and identifiers (``id``, ``name``) are handled separately from model configuration.

Pipeline Functions: Renamed and Restructured
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 renames pipeline functions to emphasize the "core" library pattern and removes task-oriented wrappers.

**V3 pipeline functions:**

- ``train_model_pipeline()`` - high-level training with database integration
- ``create_forecast_pipeline()`` - high-level forecasting with database integration

**V4 pipeline functions:**

- ``train_model_pipeline_core()`` - core training logic, no database dependencies
- ``predict_pipeline_core()`` - core prediction logic, no database dependencies

The ``_core`` suffix indicates these are pure library functions. You handle data loading and persistence yourself. See :doc:`data_integration` for patterns on integrating with databases, S3, or other data sources.

Database Integration Removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3 included ``openstef-dbc`` for database integration. V4 removes this entirely - OpenSTEF is now a pure machine learning library.

**V3 approach with database:**

.. code-block:: python

   from openstef.tasks.train_model import train_model_task
   
   # Task fetches data from database, trains, stores results
   train_model_task(
       pj,
       database_connection,
       mlflow_tracking_uri="./mlflow"
   )

**V4 approach:**

.. code-block:: python

   # You handle data loading
   df = load_data_from_database(connection, location_id)
   dataset = TimeSeriesDataset(data=df, target_column='load', feature_columns=features)
   
   # Train model
   model, metrics = train_model_pipeline_core(dataset, config)
   
   # You handle model persistence
   save_model_to_storage(model, storage_path)

This separation gives you complete control over data sources and storage backends. See :doc:`deployment` for production deployment patterns.

Step-by-Step Migration Workflow
--------------------------------

Follow these steps to migrate existing V3 code to V4:

1. Update Dependencies
^^^^^^^^^^^^^^^^^^^^^^

Update your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # Remove V3
   # openstef==3.4.72
   # openstef-dbc==3.x.x
   
   # Add V4
   openstef>=4.0.0

Remove ``openstef-dbc`` entirely - it's not compatible with V4.

2. Refactor Data Loading
^^^^^^^^^^^^^^^^^^^^^^^^^

Replace DataFrame-based data loading with ``TimeSeriesDataset`` creation:

.. code-block:: python

   # V3 code
   input_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_data = input_data.iloc[:-200, :]
   
   # V4 equivalent
   from openstef.data.dataset import TimeSeriesDataset
   
   df = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   train_df = df.iloc[:-200, :]
   
   # Define structure explicitly
   dataset = TimeSeriesDataset(
       data=train_df,
       target_column='load',  # Your target variable
       feature_columns=['temp', 'humidity', 'wind']  # Your features
   )

Identify your target column and feature columns explicitly. This replaces V3's implicit assumptions.

3. Convert Configuration
^^^^^^^^^^^^^^^^^^^^^^^^

Replace ``PredictionJobDataClass`` with configuration dictionaries:

.. code-block:: python

   # V3 code
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2820,
       resolution_minutes=15
   )
   
   # V4 equivalent
   config = {
       'model_type': 'xgb',
       'quantiles': [0.1, 0.5, 0.9],
       'horizon_minutes': 2820,
       'resolution_minutes': 15
   }
   
   # Store metadata separately if needed
   metadata = {
       'location_id': 287,
       'location_name': 'Substation A'
   }

Separate model configuration from metadata. Configuration goes to pipelines; metadata is for your application logic.

4. Update Pipeline Calls
^^^^^^^^^^^^^^^^^^^^^^^^^

Replace V3 pipeline functions with V4 ``_core`` equivalents:

.. code-block:: python

   # V3 training
   from openstef.pipeline.train_model import train_model_pipeline
   models = train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlflow"
   )
   
   # V4 training
   from openstef.pipeline.train_model import train_model_pipeline_core
   model, metrics = train_model_pipeline_core(
       dataset,
       config,
       mlflow_tracking_uri="./mlflow"
   )

Note the return value changes: V4 returns ``(model, metrics)`` tuple instead of a models dictionary.

For prediction:

.. code-block:: python

   # V3 prediction
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   forecast = create_forecast_pipeline(pj, forecast_input_data, model)
   
   # V4 prediction
   from openstef.pipeline.predict import predict_pipeline_core
   
   forecast_dataset = TimeSeriesDataset(
       data=forecast_df,
       target_column='load',
       feature_columns=features
   )
   
   predictions = predict_pipeline_core(forecast_dataset, model, config)

5. Handle Model Persistence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 still supports MLflow for model storage, but you control the lifecycle:

.. code-block:: python

   import mlflow
   from openstef.pipeline.train_model import train_model_pipeline_core
   
   # Train model
   model, metrics = train_model_pipeline_core(
       dataset,
       config,
       mlflow_tracking_uri="./mlflow"
   )
   
   # Optionally save to custom location
   with open('model.pkl', 'wb') as f:
       pickle.dump(model, f)
   
   # Or use MLflow explicitly
   mlflow.sklearn.log_model(model, "model")

V4 gives you flexibility to use MLflow, pickle, joblib, or any other persistence mechanism.

6. Replace Task Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you used V3 tasks (from ``openstef.tasks``), replace them with pipeline functions plus your own data integration:

.. code-block:: python

   # V3 task-based approach
   from openstef.tasks.train_model import train_model_task
   train_model_task(pj, database_connection)
   
   # V4 library approach
   from openstef.pipeline.train_model import train_model_pipeline_core
   
   # Your data integration
   df = fetch_training_data(location_id, start_date, end_date)
   dataset = TimeSeriesDataset(data=df, target_column='load', feature_columns=features)
   
   # Core library function
   model, metrics = train_model_pipeline_core(dataset, config)
   
   # Your persistence
   save_model(model, location_id)

This pattern gives you full control over data sources and storage. See :doc:`data_integration` for integration examples with S3, Databricks, and InfluxDB.

Common Migration Patterns
--------------------------

Batch Training Jobs
^^^^^^^^^^^^^^^^^^^

V3 batch training using tasks:

.. code-block:: python

   # V3
   for pj in prediction_jobs:
       train_model_task(pj, db_connection)

V4 equivalent with explicit data handling:

.. code-block:: python

   # V4
   for location_config in locations:
       # Load data
       df = load_training_data(location_config['id'])
       dataset = TimeSeriesDataset(
           data=df,
           target_column='load',
           feature_columns=location_config['features']
       )
       
       # Train
       model, metrics = train_model_pipeline_core(dataset, location_config)
       
       # Save
       save_model(model, location_config['id'])
       log_metrics(metrics, location_config['id'])

Real-Time Forecasting
^^^^^^^^^^^^^^^^^^^^^

V3 forecasting with database:

.. code-block:: python

   # V3
   from openstef.tasks.create_forecast import create_forecast_task
   create_forecast_task(pj, db_connection)

V4 equivalent:

.. code-block:: python

   # V4
   # Load model and recent data
   model = load_model(location_id)
   df = fetch_recent_data(location_id, hours=48)
   
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',
       feature_columns=features
   )
   
   # Generate forecast
   predictions = predict_pipeline_core(dataset, model, config)
   
   # Store results
   save_predictions(predictions, location_id)

Feature Engineering
^^^^^^^^^^^^^^^^^^^

Feature engineering APIs remain largely compatible, but work with ``TimeSeriesDataset``:

.. code-block:: python

   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   
   # Apply features to dataset
   applicator = TrainFeatureApplicator(
       horizons=[0.25, 24.0, 47.0],
       feature_names=['load_lag_1', 'temp', 'humidity']
   )
   
   enriched_dataset = applicator.apply(dataset)

The feature engineering module continues to work similarly, but operates on ``TimeSeriesDataset`` objects instead of raw DataFrames.

Next Steps
----------

After migrating your code:

- Review :doc:`data_integration` for patterns on connecting to your data sources
- See :doc:`deployment` for production deployment strategies
- Check :doc:`logging` for configuring logging in V4
- Explore :doc:`use_cases` for complete examples of common workflows

The V4 architecture gives you more flexibility to integrate OpenSTEF into your specific environment while maintaining the powerful forecasting capabilities of the library.