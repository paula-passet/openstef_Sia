How-To Guides
=============

This section provides task-specific implementation guides for common OpenSTEF deployment scenarios. These guides assume you're familiar with the basic concepts covered in our tutorials and focus on specific integration challenges.

Simple Deployment Setup
-----------------------

Setting up basic forecasting workflows using cron jobs or orchestration tools like Dagster.

Cron-Based Scheduling
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides built-in task modules designed for scheduled execution. The simplest deployment approach uses cron jobs to run forecasting tasks at regular intervals.

.. code-block:: python

   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.tasks.train_model import train_model_task
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Define prediction job configuration
   prediction_job = PredictionJobDataClass(
       id=1,
       name="substation_forecast",
       model="xgb",
       lat=52.0,
       lon=4.0,
       resolution_minutes=15
   )
   
   # Create task context with database connections
   context = TaskContext(
       database=your_database_connection,
       model_store=your_model_storage
   )
   
   # Run forecast task (typically called from cron)
   create_forecast_task(prediction_job, context)

Create a cron job to run forecasts every 15 minutes:

.. code-block:: bash

   # Add to crontab (crontab -e)
   */15 * * * * /usr/bin/python /path/to/your/forecast_script.py

For model training, schedule less frequently:

.. code-block:: bash

   # Train models daily at 2 AM
   0 2 * * * /usr/bin/python /path/to/your/training_script.py

.. note::
   The task modules expect trained models to be available in persistent storage. Run training tasks before attempting forecasts.

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more sophisticated workflows, integrate OpenSTEF with Dagster for better monitoring, dependency management, and error handling.

.. code-block:: python

   from dagster import asset, job, schedule, DefaultScheduleStatus
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.tasks.train_model import train_model_task
   
   @asset
   def weather_data():
       """Fetch latest weather data."""
       # Your weather data fetching logic
       return fetch_weather_data()
   
   @asset
   def load_data():
       """Fetch latest load measurements."""
       # Your load data fetching logic
       return fetch_load_data()
   
   @asset(deps=[weather_data, load_data])
   def energy_forecast(context):
       """Generate energy forecast using OpenSTEF."""
       prediction_job = PredictionJobDataClass(
           id=1,
           name="dagster_forecast",
           model="xgb"
       )
       
       task_context = TaskContext(
           database=context.resources.database,
           model_store=context.resources.model_store
       )
       
       return create_forecast_task(prediction_job, task_context)
   
   @job
   def forecast_pipeline():
       energy_forecast()
   
   # Schedule to run every 15 minutes
   forecast_schedule = ScheduleDefinition(
       job=forecast_pipeline,
       cron_schedule="*/15 * * * *",
       default_status=DefaultScheduleStatus.RUNNING
   )

This approach provides better observability and makes it easier to handle data dependencies between tasks.

Data Integration
----------------

Connecting OpenSTEF with various data sources and storage systems.

S3 Integration
^^^^^^^^^^^^^^

For cloud-based deployments, integrate with AWS S3 for data storage and model persistence.

.. code-block:: python

   import boto3
   import pandas as pd
   from openstef_beam.benchmarking import S3BenchmarkStorage
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   
   # Configure S3 client
   s3_client = boto3.client('s3')
   
   # Set up S3 storage for benchmarking results
   local_storage = LocalBenchmarkStorage('/tmp/benchmarks')
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name='your-openstef-bucket',
       s3_prefix='benchmarks/',
       s3fs_kwargs={'key': 'your-access-key', 'secret': 'your-secret-key'}
   )
   
   # Load training data from S3
   def load_training_data_from_s3(bucket, key):
       obj = s3_client.get_object(Bucket=bucket, Key=key)
       return pd.read_parquet(obj['Body'])
   
   # Save forecast results to S3
   def save_forecast_to_s3(forecast_df, bucket, key):
       forecast_df.to_parquet(f's3://{bucket}/{key}')
   
   # Example usage in forecast task
   training_data = load_training_data_from_s3('data-bucket', 'training/load_data.parquet')
   # ... run forecasting ...
   save_forecast_to_s3(forecast_results, 'results-bucket', 'forecasts/latest.parquet')

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

OpenSTEF's openstef-dbc package provides native InfluxDB support for time series data storage.

.. code-block:: python

   from openstef_dbc.influxdb import InfluxDBConnector
   from datetime import datetime, timedelta
   
   # Configure InfluxDB connection
   influx_client = InfluxDBConnector(
       host='your-influxdb-host',
       port=8086,
       database='energy_data',
       username='your-username',
       password='your-password'
   )
   
   # Query historical load data
   def get_load_data(start_time, end_time):
       query = f"""
       SELECT mean("value") as load
       FROM "load_measurements"
       WHERE time >= '{start_time}' AND time <= '{end_time}'
       GROUP BY time(15m) fill(linear)
       """
       return influx_client.exec_influx_query(query)
   
   # Write forecast results
   def write_forecast_to_influx(forecast_df, measurement_name):
       points = []
       for idx, row in forecast_df.iterrows():
           point = {
               "measurement": measurement_name,
               "time": idx,
               "fields": {
                   "forecast": row['forecast'],
                   "quantile_10": row['quantile_10'],
                   "quantile_90": row['quantile_90']
               }
           }
           points.append(point)
       
       influx_client.write_points(points)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For large-scale data processing, integrate OpenSTEF with Databricks for distributed training and forecasting.

.. code-block:: python

   from pyspark.sql import SparkSession
   from openstef_models.forecasting import make_forecast
   import pandas as pd
   
   # Initialize Spark session
   spark = SparkSession.builder.appName("OpenSTEF_Forecasting").getOrCreate()
   
   # Load data from Databricks tables
   def load_databricks_data(table_name, start_date, end_date):
       query = f"""
       SELECT * FROM {table_name}
       WHERE date >= '{start_date}' AND date <= '{end_date}'
       """
       return spark.sql(query)
   
   # Distributed forecasting across multiple prediction jobs
   def run_distributed_forecasting(prediction_jobs):
       def forecast_single_job(job_config):
           # Convert Spark DataFrame to Pandas for OpenSTEF
           training_data = load_databricks_data(
               job_config['data_table'],
               job_config['start_date'],
               job_config['end_date']
           ).toPandas()
           
           # Run OpenSTEF forecast
           forecast = make_forecast(
               model_type=job_config['model_type'],
               training_data=training_data,
               forecast_horizon_hours=job_config['horizon']
           )
           
           return forecast
       
       # Use Spark to parallelize across jobs
       job_rdd = spark.sparkContext.parallelize(prediction_jobs)
       results = job_rdd.map(forecast_single_job).collect()
       
       return results

Migration from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 introduces significant architectural changes that require code updates for existing V3 users.

Key Changes Overview
^^^^^^^^^^^^^^^^^^^^

The major differences between V3 and V4 include:

- **Modular architecture**: V4 splits functionality into separate packages (openstef-models, openstef-beam, openstef-core)
- **Decoupled dependencies**: External dependencies like MLFlow and openstef-dbc are now optional
- **Type safety**: Full type annotations throughout the codebase
- **Flexible configuration**: Replaces hard-coded assumptions with configurable parameters

Package Migration
^^^^^^^^^^^^^^^^^

Update your imports to use the new modular structure:

.. code-block:: python

   # OpenSTEF V3 imports
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.tasks.create_forecast import create_forecast_task
   
   # OpenSTEF V4 imports
   from openstef_models.regressors import ARIMAOpenstfRegressor
   from openstef_models.pipelines import train_model_pipeline
   from openstef_models.tasks import create_forecast_task

Configuration Changes
^^^^^^^^^^^^^^^^^^^^^

V4 introduces more flexible configuration mechanisms:

.. code-block:: python

   # V3: Hard-coded configuration
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Limited configuration options
   model = train_model_pipeline(
       pj=prediction_job,
       input_data=training_data
   )
   
   # V4: Flexible configuration
   from openstef_models.pipelines import train_model_pipeline
   from openstef_models.config import ModelConfig
   
   # Extensive configuration options
   config = ModelConfig(
       model_type="xgb",
       hyperparameter_optimization=True,
       feature_engineering_config={
           "lag_features": [1, 2, 24],
           "weather_features": ["temperature", "wind_speed"],
           "holiday_calendar": "netherlands"  # Now configurable!
       },
       validation_config={
           "cv_folds": 5,
           "test_fraction": 0.2
       }
   )
   
   model = train_model_pipeline(
       prediction_job=prediction_job,
       training_data=training_data,
       config=config
   )

Data Pipeline Updates
^^^^^^^^^^^^^^^^^^^^^

V4 centralizes data preprocessing logic:

.. code-block:: python

   # V3: Scattered preprocessing
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.validation.validation import validate_data
   
   # Preprocessing scattered across modules
   validated_data = validate_data(raw_data)
   featured_data = apply_features(validated_data, pj)
   
   # V4: Centralized preprocessing
   from openstef_models.preprocessing import DataPreprocessor
   from openstef_models.feature_engineering import FeatureEngineer
   
   # Unified preprocessing pipeline
   preprocessor = DataPreprocessor(
       validation_rules=your_validation_config,
       cleaning_rules=your_cleaning_config
   )
   
   feature_engineer = FeatureEngineer(
       lag_features=[1, 2, 24],
       weather_features=["temperature", "wind_speed"],
       calendar_features=True
   )
   
   # Chain preprocessing steps
   processed_data = preprocessor.fit_transform(raw_data)
   featured_data = feature_engineer.fit_transform(processed_data)

Error Handling Improvements
^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 provides more specific exception types:

.. code-block:: python

   # V3: Generic exceptions
   try:
       forecast = create_forecast_task(pj, context)
   except Exception as e:
       logger.error(f"Forecast failed: {e}")
   
   # V4: Specific exception handling
   from openstef_models.exceptions import (
       ModelNotFoundError,
       InsufficientDataError,
       ValidationError
   )
   
   try:
       forecast = create_forecast_task(pj, context)
   except ModelNotFoundError:
       logger.error("Model not found, triggering training")
       train_model_task(pj, context)
       forecast = create_forecast_task(pj, context)
   except InsufficientDataError as e:
       logger.warning(f"Insufficient data: {e}")
       # Implement fallback strategy
   except ValidationError as e:
       logger.error(f"Data validation failed: {e}")
       # Handle data quality issues

Migration Checklist
^^^^^^^^^^^^^^^^^^^^

Use this checklist to ensure complete migration:

1. **Update package installations**:
   
   .. code-block:: bash
   
      # Remove V3
      pip uninstall openstef
      
      # Install V4
      pip install "openstef[all]"  # or specific packages

2. **Update imports** throughout your codebase
3. **Review configuration** - replace hard-coded values with configurable parameters
4. **Update exception handling** to use specific exception types
5. **Test data pipelines** with the new preprocessing modules
6. **Validate forecast accuracy** using openstef-beam evaluation tools

.. warning::
   V4 is not backward compatible with V3. Plan for thorough testing before deploying to production.

For detailed migration assistance, consult the changelog or reach out to the community through our `GitHub Issues <https://github.com/OpenSTEF/openstef/issues>`_.