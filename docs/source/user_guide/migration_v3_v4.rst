Migrating from V3 to V4
=======================

OpenSTEF V4 represents a major architectural shift from V3, introducing breaking changes that require code updates. This guide walks you through the key changes and provides practical migration steps with before/after examples.

Overview of breaking changes
-----------------------------

V4 removes several core concepts from V3 and introduces new data structures:

**Removed in V4:**

- ``PredictionJobDataClass`` - Configuration is now passed as individual parameters
- ``openstef-dbc`` integration - V4 is a standalone library without database coupling
- Direct pandas DataFrame usage in pipelines - Replaced with ``TimeSeriesDataset``

**New in V4:**

- ``TimeSeriesDataset`` - Structured container for time series data with metadata
- Simplified pipeline APIs with explicit parameters
- Decoupled data access - You manage your own data sources

Key architectural changes
--------------------------

Package structure
^^^^^^^^^^^^^^^^^

V3 organized functionality around database tasks and tightly coupled pipelines. V4 reorganizes around core machine learning workflows:

**V3 structure:**

.. code-block:: text

   openstef/
   ├── tasks/          # Database-coupled operations
   ├── pipeline/       # Pipelines expecting PredictionJobDataClass
   └── feature_engineering/

**V4 structure:**

.. code-block:: text

   openstef/
   ├── pipeline/       # Standalone pipelines
   ├── data/           # TimeSeriesDataset and validation
   ├── model/          # Model implementations
   └── feature_engineering/

Import paths remain similar, but function signatures have changed significantly.

Data handling
^^^^^^^^^^^^^

V3 accepted pandas DataFrames directly and used ``PredictionJobDataClass`` for configuration. V4 requires wrapping your data in ``TimeSeriesDataset`` and passing configuration as function parameters.

**V3 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Define prediction job with all configuration
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=47*60,
       resolution_minutes=15,
       lat=52.0,
       lon=5.0,
   )
   
   # Load data as DataFrame
   train_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   
   # Train model
   model = train_model_pipeline(
       pj,
       train_data,
       mlflow_tracking_uri="./mlruns"
   )

**V4 approach:**

.. code-block:: python

   import pandas as pd
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train import train_pipeline
   
   # Load data as DataFrame
   df = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',
       feature_columns=[col for col in df.columns if col != 'load']
   )
   
   # Train model with explicit parameters
   model, report = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizons=[0.25, 47.0],  # In hours
       resolution_minutes=15
   )

Pipeline API changes
^^^^^^^^^^^^^^^^^^^^

V4 pipeline functions have simplified signatures without ``PredictionJobDataClass``:

**Training:**

.. code-block:: python

   # V3
   from openstef.pipeline.train_model import train_model_pipeline
   model = train_model_pipeline(prediction_job, train_data)
   
   # V4
   from openstef.pipeline.train import train_pipeline
   model, report = train_pipeline(
       dataset=dataset,
       model_type='xgb',
       horizons=[0.25, 47.0]
   )

**Prediction:**

.. code-block:: python

   # V3
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   forecast = create_forecast_pipeline(prediction_job, input_data, model)
   
   # V4
   from openstef.pipeline.predict import predict_pipeline
   forecast = predict_pipeline(
       dataset=dataset,
       model=model,
       horizons=[0.25, 47.0]
   )

Step-by-step migration workflow
--------------------------------

1. Update dependencies
^^^^^^^^^^^^^^^^^^^^^^

Update your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # Remove
   openstef==3.x.x
   openstef-dbc==x.x.x
   
   # Add
   openstef>=4.0.0

Note that V4 may have different Python version requirements. Check the release notes for compatibility.

2. Replace PredictionJobDataClass usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Identify all places where you create ``PredictionJobDataClass`` instances and extract the relevant parameters:

.. code-block:: python

   # V3: Extract configuration from PredictionJobDataClass
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',
       quantiles=[0.05, 0.5, 0.95],
       horizon_minutes=47*60,
       resolution_minutes=15,
       lat=52.0,
       lon=5.0,
       feature_names=['temperature', 'humidity']
   )
   
   # V4: Store as regular variables or configuration dict
   config = {
       'model_type': 'xgb',
       'quantiles': [0.05, 0.5, 0.95],
       'horizons': [0.25, 47.0],  # Convert minutes to hours
       'resolution_minutes': 15,
       'feature_names': ['temperature', 'humidity']
   }

3. Wrap data in TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Convert DataFrame handling to use ``TimeSeriesDataset``:

.. code-block:: python

   # V3: Direct DataFrame usage
   train_data = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   
   # V4: Wrap in TimeSeriesDataset
   from openstef.data.dataset import TimeSeriesDataset
   
   df = pd.read_csv('data.csv', index_col='index', parse_dates=True)
   dataset = TimeSeriesDataset(
       data=df,
       target_column='load',
       feature_columns=[col for col in df.columns if col != 'load']
   )

The ``TimeSeriesDataset`` provides validation and ensures your data meets OpenSTEF requirements.

4. Update pipeline calls
^^^^^^^^^^^^^^^^^^^^^^^^^

Replace V3 pipeline calls with V4 equivalents:

.. code-block:: python

   # V3: Training
   from openstef.pipeline.train_model import train_model_pipeline
   model = train_model_pipeline(
       pj,
       train_data,
       check_old_model_age=False,
       mlflow_tracking_uri="./mlruns"
   )
   
   # V4: Training
   from openstef.pipeline.train import train_pipeline
   model, report = train_pipeline(
       dataset=dataset,
       model_type=config['model_type'],
       quantiles=config['quantiles'],
       horizons=config['horizons'],
       mlflow_tracking_uri="./mlruns"
   )

5. Handle database operations separately
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V3's ``openstef-dbc`` package provided database tasks. In V4, you manage data access yourself:

.. code-block:: python

   # V3: Database task handled data loading
   from openstef.tasks.train import train_model_task
   train_model_task(prediction_job_id=287)  # Loads from database internally
   
   # V4: You load data explicitly
   from openstef.pipeline.train import train_pipeline
   
   # Load from your data source (SQL, S3, etc.)
   df = load_data_from_source(location_id=287)
   dataset = TimeSeriesDataset(data=df, target_column='load')
   model, report = train_pipeline(dataset=dataset, model_type='xgb')

See the :doc:`data_integration` guide for patterns on loading data from various sources.

Common migration patterns
--------------------------

Forecasting workflow
^^^^^^^^^^^^^^^^^^^^

Complete example of migrating a forecast workflow:

.. code-block:: python

   # V3 workflow
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   pj = PredictionJobDataClass(id=287, model='xgb', horizon_minutes=2880)
   train_data = pd.read_csv('train.csv', index_col=0, parse_dates=True)
   forecast_data = pd.read_csv('forecast.csv', index_col=0, parse_dates=True)
   
   model = train_model_pipeline(pj, train_data)
   forecast = create_forecast_pipeline(pj, forecast_data, model)

.. code-block:: python

   # V4 workflow
   from openstef.data.dataset import TimeSeriesDataset
   from openstef.pipeline.train import train_pipeline
   from openstef.pipeline.predict import predict_pipeline
   
   # Prepare training data
   train_df = pd.read_csv('train.csv', index_col=0, parse_dates=True)
   train_dataset = TimeSeriesDataset(
       data=train_df,
       target_column='load',
       feature_columns=[c for c in train_df.columns if c != 'load']
   )
   
   # Train model
   model, report = train_pipeline(
       dataset=train_dataset,
       model_type='xgb',
       horizons=[0.25, 48.0]
   )
   
   # Prepare forecast data
   forecast_df = pd.read_csv('forecast.csv', index_col=0, parse_dates=True)
   forecast_dataset = TimeSeriesDataset(
       data=forecast_df,
       feature_columns=[c for c in forecast_df.columns]
   )
   
   # Generate forecast
   forecast = predict_pipeline(
       dataset=forecast_dataset,
       model=model,
       horizons=[0.25, 48.0]
   )

Hyperparameter optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # V3
   from openstef.pipeline.optimize_hyperparameters import optimize_hyperparameters_pipeline
   
   optimized_model, modelspecs, report, _ = optimize_hyperparameters_pipeline(
       pj, input_data, n_trials=50
   )
   
   # V4
   from openstef.pipeline.optimize import optimize_hyperparameters_pipeline
   
   optimized_model, best_params = optimize_hyperparameters_pipeline(
       dataset=dataset,
       model_type='xgb',
       n_trials=50,
       horizons=[0.25, 47.0]
   )

Testing considerations
----------------------

Update your tests to use V4 APIs:

.. code-block:: python

   # V3 test
   def test_training():
       pj = PredictionJobDataClass(id=1, model='xgb')
       data = create_test_dataframe()
       model = train_model_pipeline(pj, data)
       assert model is not None
   
   # V4 test
   def test_training():
       data = create_test_dataframe()
       dataset = TimeSeriesDataset(data=data, target_column='load')
       model, report = train_pipeline(dataset=dataset, model_type='xgb')
       assert model is not None
       assert report is not None

Next steps
----------

After migrating your code:

- Review the :doc:`deployment` guide for production deployment patterns
- Configure logging following the :doc:`logging` guide
- Explore :doc:`use_cases` for V4-specific examples

.. note::

   If you encounter migration issues not covered here, check the GitHub issues or open a new one with your specific use case.