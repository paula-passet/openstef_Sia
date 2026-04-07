Migration Guide: OpenSTEF V3 to V4
===================================

This guide helps you migrate existing OpenSTEF V3 code to the V4 API. OpenSTEF V4 introduces significant architectural changes that improve the library's modularity and make it easier to integrate into different environments. This page covers the key breaking changes, updated APIs, and provides step-by-step migration examples.

Overview of Changes
-------------------

OpenSTEF V4 represents a major refactoring focused on making the library truly standalone and framework-agnostic. The most significant changes include:

- **Removal of PredictionJobDataClass**: V4 eliminates the monolithic prediction job concept in favor of explicit configuration parameters
- **Introduction of TimeSeriesDataset**: Replaces raw pandas DataFrames with a structured data container
- **Standalone library**: V4 removes the tight coupling with openstef-dbc, making it easier to integrate with any data source
- **Simplified pipeline APIs**: Pipelines now accept explicit parameters instead of extracting them from prediction jobs
- **Package structure reorganization**: Clearer separation between pipelines, tasks, and core functionality

Breaking Changes
----------------

PredictionJobDataClass Removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``PredictionJobDataClass`` was the central configuration object in V3, containing all parameters for training and forecasting. In V4, this has been removed entirely. Instead, pipeline functions accept explicit parameters.

**V3 Code:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd
   
   # Define prediction job with all configuration
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       name="my_forecast",
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       horizon_minutes=47*60,
       resolution_minutes=15,
       hyper_params={},
       feature_names=None,
   )
   
   # Load data as DataFrame
   train_data = pd.read_csv('data/train.csv', index_col='index', parse_dates=True)
   
   # Train model
   model = train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlflow_models"
   )

**V4 Code:**

.. code-block:: python

   from openstef.pipeline.train_pipeline import train_pipeline
   from openstef.data.dataset import TimeSeriesDataset
   import pandas as pd
   
   # Load data as DataFrame
   df = pd.read_csv('data/train.csv', index_col='index', parse_dates=True)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',
       feature_columns=[col for col in df.columns if col != 'load']
   )
   
   # Train model with explicit parameters
   model = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       quantiles=[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95],
       horizon_minutes=47*60,
       resolution_minutes=15,
       mlflow_tracking_uri="./mlflow_models"
   )

TimeSeriesDataset Replaces DataFrames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 introduces the ``TimeSeriesDataset`` class as the primary data container. While pipelines may still work with DataFrames internally, the public API expects TimeSeriesDataset objects. This provides better validation, clearer semantics, and easier feature management.

**Key benefits:**

- Explicit separation of target and feature columns
- Built-in validation for time series requirements
- Metadata storage (resolution, horizon, etc.)
- Consistent interface across all pipelines

**Migration pattern:**

.. code-block:: python

   # V3: Direct DataFrame usage
   train_data = pd.read_csv('data.csv', parse_dates=True, index_col=0)
   
   # V4: Wrap in TimeSeriesDataset
   from openstef.data.dataset import TimeSeriesDataset
   
   df = pd.read_csv('data.csv', parse_dates=True, index_col=0)
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',  # Explicitly specify target
       feature_columns=['temperature', 'humidity', 'wind_speed']  # Explicitly specify features
   )

Pipeline Function Signatures Changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All pipeline functions have new signatures that accept explicit parameters instead of a prediction job object.

**V3 train_model_pipeline:**

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   
   model = train_model_pipeline(
       pj,  # PredictionJobDataClass
       train_data,  # DataFrame
       check_old_model_age=False,
       mlflow_tracking_uri="./models"
   )

**V4 train_pipeline:**

.. code-block:: python

   from openstef.pipeline.train_pipeline import train_pipeline
   
   model = train_pipeline(
       dataset=dataset,  # TimeSeriesDataset
       model_type='xgb',
       quantiles=[0.5],
       horizon_minutes=1440,
       resolution_minutes=15,
       mlflow_tracking_uri="./models",
       # Additional explicit parameters as needed
   )

Similarly, prediction pipelines have changed:

**V3 create_forecast_pipeline:**

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   forecast = create_forecast_pipeline(
       pj,
       input_data,
       mlflow_tracking_uri="./models"
   )

**V4 predict_pipeline:**

.. code-block:: python

   from openstef.pipeline.predict_pipeline import predict_pipeline
   
   forecast = predict_pipeline(
       dataset=dataset,
       model=trained_model,  # Or load from MLflow
       horizon_minutes=1440,
       mlflow_tracking_uri="./models"
   )

openstef-dbc Decoupling
^^^^^^^^^^^^^^^^^^^^^^^

V3 had tight integration with the ``openstef-dbc`` package for database operations. V4 is completely standalone - you manage data loading and persistence yourself.

**V3 with openstef-dbc:**

.. code-block:: python

   from openstef.tasks.train_model import train_model_task
   
   # Task automatically fetches data from database
   train_model_task(
       pj=pj,
       context=database_context
   )

**V4 approach:**

.. code-block:: python

   from openstef.pipeline.train_pipeline import train_pipeline
   from openstef.data.dataset import TimeSeriesDataset
   
   # You handle data loading
   df = load_data_from_your_database(location_id=287)
   
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',
       feature_columns=feature_cols
   )
   
   # You call the pipeline
   model = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       quantiles=[0.5],
       horizon_minutes=1440,
       resolution_minutes=15
   )
   
   # You handle model storage
   save_model_to_your_storage(model, location_id=287)

This change gives you complete control over data sources and storage backends. See the :doc:`data_integration` page for patterns on integrating with different data sources.

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
   # Remove openstef-dbc if you were using it

2. Replace PredictionJobDataClass
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Identify all places where you create ``PredictionJobDataClass`` instances and extract the relevant parameters:

.. code-block:: python

   # V3
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.5],
       horizon_minutes=1440,
       resolution_minutes=15,
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
   )

Extract the parameters you actually need for each pipeline call:

.. code-block:: python

   # V4 - store as simple dict or config object
   config = {
       'location_id': 287,
       'model_type': 'xgb',
       'quantiles': [0.5],
       'horizon_minutes': 1440,
       'resolution_minutes': 15,
       'forecast_type': 'demand',
       'lat': 52.0,
       'lon': 5.0,
   }

3. Wrap DataFrames in TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Find all pipeline calls and wrap DataFrames:

.. code-block:: python

   # V3
   train_data = pd.read_csv('data.csv', parse_dates=True, index_col=0)
   model = train_model_pipeline(pj, train_data, mlflow_tracking_uri="./models")
   
   # V4
   from openstef.data.dataset import TimeSeriesDataset
   
   df = pd.read_csv('data.csv', parse_dates=True, index_col=0)
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',
       feature_columns=[col for col in df.columns if col != 'load']
   )
   model = train_pipeline(
       dataset=dataset,
       model_type=config['model_type'],
       quantiles=config['quantiles'],
       horizon_minutes=config['horizon_minutes'],
       resolution_minutes=config['resolution_minutes'],
       mlflow_tracking_uri="./models"
   )

4. Update Pipeline Imports and Calls
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace old pipeline imports with new ones:

.. code-block:: python

   # V3 imports
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # V4 imports
   from openstef.pipeline.train_pipeline import train_pipeline
   from openstef.pipeline.predict_pipeline import predict_pipeline

Update all function calls to use explicit parameters instead of passing the prediction job.

5. Replace Task Calls with Pipeline Calls
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you were using tasks from ``openstef.tasks``, replace them with direct pipeline calls and handle data I/O yourself:

.. code-block:: python

   # V3 task-based approach
   from openstef.tasks.train_model import train_model_task
   
   train_model_task(pj=pj, context=db_context)
   
   # V4 pipeline-based approach
   from openstef.pipeline.train_pipeline import train_pipeline
   
   # Load data yourself
   df = your_data_loader.load_training_data(location_id=287)
   dataset = TimeSeriesDataset(data=df, target_column='load', feature_columns=features)
   
   # Call pipeline
   model = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       quantiles=[0.5],
       horizon_minutes=1440,
       resolution_minutes=15
   )
   
   # Save model yourself
   your_model_store.save(model, location_id=287)

Complete Example: Before and After
-----------------------------------

Here's a complete example showing a typical V3 workflow and its V4 equivalent.

**V3 Complete Example:**

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd
   import numpy as np
   
   # Define prediction job
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=2880,
       resolution_minutes=15,
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
   )
   
   # Load and prepare data
   data = pd.read_csv('data.csv', index_col=0, parse_dates=True)
   train_data = data.iloc[:-192]
   forecast_data = data.copy()
   forecast_data.iloc[-192:, forecast_data.columns.get_loc('load')] = np.nan
   
   # Train model
   model = train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./models"
   )
   
   # Make forecast
   forecast = create_forecast_pipeline(
       pj,
       forecast_data,
       mlflow_tracking_uri="./models"
   )

**V4 Complete Example:**

.. code-block:: python

   from openstef.pipeline.train_pipeline import train_pipeline
   from openstef.pipeline.predict_pipeline import predict_pipeline
   from openstef.data.dataset import TimeSeriesDataset
   import pandas as pd
   import numpy as np
   
   # Configuration (no more PredictionJobDataClass)
   config = {
       'location_id': 287,
       'model_type': 'xgb',
       'quantiles': [0.05, 0.5, 0.95],
       'horizon_minutes': 2880,
       'resolution_minutes': 15,
   }
   
   # Load and prepare data
   df = pd.read_csv('data.csv', index_col=0, parse_dates=True)
   train_df = df.iloc[:-192]
   
   # Create dataset for training
   train_dataset = TimeSeriesDataset(
       data=train_df,
       target_column='load',
       feature_columns=[col for col in train_df.columns if col != 'load']
   )
   
   # Train model
   model = train_pipeline(
       dataset=train_dataset,
       model_type=config['model_type'],
       quantiles=config['quantiles'],
       horizon_minutes=config['horizon_minutes'],
       resolution_minutes=config['resolution_minutes'],
       mlflow_tracking_uri="./models"
   )
   
   # Prepare forecast data
   forecast_df = df.copy()
   forecast_df.iloc[-192:, forecast_df.columns.get_loc('load')] = np.nan
   
   forecast_dataset = TimeSeriesDataset(
       data=forecast_df,
       target_column='load',
       feature_columns=[col for col in forecast_df.columns if col != 'load']
   )
   
   # Make forecast
   forecast = predict_pipeline(
       dataset=forecast_dataset,
       model=model,
       horizon_minutes=config['horizon_minutes'],
       mlflow_tracking_uri="./models"
   )

Common Migration Pitfalls
--------------------------

**Forgetting to specify target_column**: TimeSeriesDataset requires explicit target and feature columns. Don't assume the library will infer them.

**Passing DataFrames directly**: V4 pipelines expect TimeSeriesDataset objects. Passing DataFrames directly will raise errors.

**Looking for PredictionJobDataClass**: This class no longer exists. Use simple dictionaries or your own configuration objects.

**Expecting automatic data loading**: V4 doesn't include database integration. You must load and save data yourself.

**Using old import paths**: Pipeline modules have been reorganized. Update your imports to match the new structure.

Next Steps
----------

After migrating your code:

- Review :doc:`data_integration` for patterns on connecting to your data sources
- Check :doc:`deployment` for production deployment strategies with V4
- Explore :doc:`use_cases` for V4 examples of common forecasting scenarios

If you encounter issues during migration, consult the API reference or open an issue on GitHub.