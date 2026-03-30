How-To Guides
=============

This section provides practical guides for specific implementation tasks when working with the OpenSTEF library. These guides focus on concrete solutions to common deployment and integration challenges that go beyond the basic tutorials.

Setting Up Production Deployment
---------------------------------

OpenSTEF is designed to integrate into existing systems rather than run as a standalone application. Here are common deployment patterns for production environments.

Cron-based Scheduling
^^^^^^^^^^^^^^^^^^^^^

The simplest deployment approach uses cron jobs to execute forecasting tasks at regular intervals. OpenSTEF provides task modules specifically designed for this pattern:

.. code-block:: python

   from openstef.tasks.create_forecast import main as create_forecast
   from openstef.tasks.train_model import main as train_model
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Example cron job script
   def run_forecast_task():
       with TaskContext("forecast_task", config, database) as context:
           create_forecast(config=config, database=database)
   
   def run_training_task():
       with TaskContext("training_task", config, database) as context:
           train_model(config=config, database=database)

Configure your crontab to run these tasks:

.. code-block:: bash

   # Run forecasts every 15 minutes
   */15 * * * * /path/to/python /path/to/forecast_script.py
   
   # Retrain models daily at 2 AM
   0 2 * * * /path/to/python /path/to/training_script.py

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more complex workflows, Dagster provides better dependency management and monitoring:

.. code-block:: python

   from dagster import op, job, schedule
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.tasks.utils.taskcontext import TaskContext
   
   @op
   def forecast_op(context):
       with TaskContext("dagster_forecast", config, database) as task_context:
           # Your forecasting logic here
           create_forecast_task(prediction_job, task_context)
   
   @op
   def train_op(context):
       with TaskContext("dagster_training", config, database) as task_context:
           # Your training logic here
           pass
   
   @job
   def forecast_job():
       forecast_op()
   
   @schedule(cron_schedule="*/15 * * * *", job=forecast_job)
   def forecast_schedule(_context):
       return {}

Data Integration Patterns
--------------------------

OpenSTEF supports various data sources through flexible integration patterns. The library separates data retrieval from forecasting logic, allowing you to adapt to different storage systems.

S3 Integration
^^^^^^^^^^^^^^

For cloud-based deployments, S3 provides scalable storage for both input data and forecast results:

.. code-block:: python

   import boto3
   import pandas as pd
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Configure S3 client
   s3_client = boto3.client('s3')
   
   def load_data_from_s3(bucket, key):
       """Load training data from S3"""
       obj = s3_client.get_object(Bucket=bucket, Key=key)
       return pd.read_parquet(obj['Body'])
   
   def save_forecast_to_s3(forecast_df, bucket, key):
       """Save forecast results to S3"""
       parquet_buffer = forecast_df.to_parquet()
       s3_client.put_object(Bucket=bucket, Key=key, Body=parquet_buffer)
   
   # Example workflow
   input_data = load_data_from_s3('my-bucket', 'input/load_data.parquet')
   forecast = create_forecast_pipeline(input_data, model=ARIMAOpenstfRegressor())
   save_forecast_to_s3(forecast, 'my-bucket', 'forecasts/latest.parquet')

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

InfluxDB is commonly used for time series data storage in energy applications:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   
   def read_from_influxdb(client, query):
       """Read time series data from InfluxDB"""
       result = client.query_api().query_data_frame(query)
       return result
   
   def write_to_influxdb(client, forecast_df, measurement):
       """Write forecast results to InfluxDB"""
       write_api = client.write_api()
       
       # Convert DataFrame to InfluxDB format
       for index, row in forecast_df.iterrows():
           point = {
               "measurement": measurement,
               "time": index,
               "fields": {"forecast": row['forecast'], "quantile_10": row['quantile_10']}
           }
           write_api.write(bucket="forecasts", record=point)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For large-scale data processing with Databricks:

.. code-block:: python

   from pyspark.sql import SparkSession
   from openstef.model.regressors import XGBOpenstfRegressor
   
   # Initialize Spark session
   spark = SparkSession.builder.appName("OpenSTEF_Forecasting").getOrCreate()
   
   def process_with_databricks():
       # Read data using Spark
       df = spark.read.parquet("/mnt/datalake/energy_data/")
       
       # Convert to Pandas for OpenSTEF processing
       pandas_df = df.toPandas()
       
       # Create forecast
       model = XGBOpenstfRegressor()
       forecast = create_forecast_pipeline(pandas_df, model=model)
       
       # Convert back to Spark DataFrame and save
       spark_forecast = spark.createDataFrame(forecast)
       spark_forecast.write.mode("overwrite").parquet("/mnt/datalake/forecasts/")

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 introduces significant architectural changes that improve modularity and flexibility. This section guides you through the migration process.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant changes in V4 include:

- **Modular architecture**: Core functionality split into separate packages (openstef-core, openstef-models, openstef-beam)
- **Decoupled dependencies**: MLFlow, openstef-dbc, and model-specific dependencies are now optional
- **Flexible configuration**: Hard-coded assumptions replaced with configurable parameters
- **Improved type safety**: Full type annotations throughout the codebase

Migration Steps
^^^^^^^^^^^^^^^

1. **Update import statements**: Many modules have moved to new packages:

.. code-block:: python

   # V3 imports
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.validation.validation import ValidationRunner
   
   # V4 imports
   from openstef.models.regressors import ARIMAOpenstfRegressor
   from openstef.beam.validation import ValidationRunner

2. **Update configuration handling**: V4 uses more explicit configuration:

.. code-block:: python

   # V3 approach (implicit configuration)
   model = XGBOpenstfRegressor()
   
   # V4 approach (explicit configuration)
   from openstef.models.config import ModelConfig
   
   config = ModelConfig(
       horizon_minutes=2880,  # 48 hours
       resolution_minutes=15,
       quantiles=[0.1, 0.5, 0.9]
   )
   model = XGBOpenstfRegressor(config=config)

3. **Handle breaking API changes**: Some method signatures have changed:

.. code-block:: python

   # V3 method call
   forecast = model.predict(input_data, horizon=48)
   
   # V4 method call
   forecast = model.predict(
       input_data, 
       horizon_minutes=2880,  # More explicit time specification
       quantiles=[0.1, 0.5, 0.9]
   )

Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

**Database dependency**: If you're not using the full OpenSTEF reference implementation, you may need to handle database connections differently:

.. code-block:: python

   # V3 (required openstef-dbc)
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # V4 (database optional)
   from openstef.core.context import ForecastContext
   
   # Create context without database dependency
   context = ForecastContext(config=your_config)

**Model serialization**: V4 uses different serialization formats for better compatibility:

.. code-block:: python

   # V3 model loading
   model = joblib.load('model_v3.pkl')
   
   # V4 model loading (with migration helper)
   from openstef.models.serialization import load_legacy_model
   
   model = load_legacy_model('model_v3.pkl')  # Converts V3 format to V4

.. note::
   The migration process may require updating your data preprocessing pipelines. V4 centralizes preprocessing logic, which may affect custom feature engineering workflows. Consult the :doc:`../reference/architecture` page for details on the new modular structure.

For complex migration scenarios or enterprise deployments, consider running V3 and V4 in parallel during the transition period to validate forecast consistency before fully switching to V4.