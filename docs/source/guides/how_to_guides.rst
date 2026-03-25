Now I have enough information to create a comprehensive how-to guides page. Let me write the complete RST documentation page.

How-to Guides
=============

This page provides task-specific practical guides for implementing OpenSTEF in production environments. These guides focus on specific implementation challenges not covered in the tutorials, including deployment orchestration, data integration with external systems, and migration from OpenSTEF V3 to V4.

Setting Up Production Deployment
---------------------------------

OpenSTEF is a Python machine learning library that requires orchestration for production forecasting workflows. Here are two common approaches for scheduling and running forecasting tasks.

Simple Cron-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, you can use cron jobs to schedule OpenSTEF tasks. This approach works well for smaller installations or when integrating with existing cron-based infrastructure.

.. code-block:: python

   # train_model_job.py
   from openstef.tasks.train_model import main as train_model_main
   from openstef.tasks.utils.taskcontext import TaskContext
   from your_config import get_config, get_database
   
   def run_model_training():
       config = get_config()
       database = get_database()
       
       with TaskContext("model_training", config, database) as context:
           train_model_main(config=config, database=database)
   
   if __name__ == "__main__":
       run_model_training()

Create a cron job to run this script:

.. code-block:: bash

   # Run model training daily at 2 AM
   0 2 * * * /path/to/python /path/to/train_model_job.py

   # Run forecast creation every 15 minutes
   */15 * * * * /path/to/python /path/to/create_forecast_job.py

.. note::
   The OpenSTEF repository includes example cron job configurations in the `/k8s/CronJobs` folder that you can adapt for your deployment.

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more complex workflows requiring dependency management, monitoring, and retry logic, Dagster provides a robust orchestration solution:

.. code-block:: python

   from dagster import job, op, schedule, DefaultScheduleStatus
   from openstef.tasks.train_model import train_model_task
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.tasks.utils.taskcontext import TaskContext
   from your_config import get_config, get_database, get_prediction_jobs
   
   @op
   def train_models_op():
       config = get_config()
       database = get_database()
       prediction_jobs = get_prediction_jobs()
       
       with TaskContext("train_models", config, database) as context:
           for pj in prediction_jobs:
               train_model_task(pj, context)
   
   @op
   def create_forecasts_op():
       config = get_config()
       database = get_database()
       prediction_jobs = get_prediction_jobs()
       
       with TaskContext("create_forecasts", config, database) as context:
           for pj in prediction_jobs:
               create_forecast_task(pj, context)
   
   @job
   def openstef_workflow():
       create_forecasts_op(train_models_op())
   
   @schedule(
       job=openstef_workflow,
       cron_schedule="0 */6 * * *",  # Every 6 hours
       default_status=DefaultScheduleStatus.RUNNING
   )
   def openstef_schedule(_context):
       return {}

This approach provides better observability, error handling, and dependency management for production deployments.

Data Integration with External Systems
--------------------------------------

OpenSTEF requires time series data for training and forecasting. Here's how to integrate with common data storage systems.

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

For cloud-based deployments, you can store and retrieve forecast data using S3:

.. code-block:: python

   import boto3
   import pandas as pd
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.tasks.utils.taskcontext import TaskContext
   
   class S3DataProvider:
       def __init__(self, bucket_name, aws_access_key_id, aws_secret_access_key):
           self.s3_client = boto3.client(
               's3',
               aws_access_key_id=aws_access_key_id,
               aws_secret_access_key=aws_secret_access_key
           )
           self.bucket_name = bucket_name
       
       def load_input_data(self, system_id, start_date, end_date):
           """Load historical data from S3 for forecasting"""
           key = f"timeseries/{system_id}/{start_date}_{end_date}.parquet"
           
           try:
               response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
               return pd.read_parquet(response['Body'])
           except Exception as e:
               print(f"Error loading data from S3: {e}")
               return None
       
       def save_forecast(self, system_id, forecast_data):
           """Save forecast results to S3"""
           key = f"forecasts/{system_id}/{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.parquet"
           
           forecast_data.to_parquet(f"s3://{self.bucket_name}/{key}")
   
   # Usage example
   s3_provider = S3DataProvider("your-bucket", "your-key", "your-secret")
   input_data = s3_provider.load_input_data("Location_A_System_1", "2024-01-01", "2024-01-31")
   
   if input_data is not None:
       forecast = create_forecast_pipeline(prediction_job, input_data)
       s3_provider.save_forecast("Location_A_System_1", forecast)

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time series databases like InfluxDB, you can create custom data providers:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from datetime import datetime, timedelta
   
   class InfluxDBProvider:
       def __init__(self, url, token, org, bucket):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.query_api = self.client.query_api()
           self.write_api = self.client.write_api()
           self.bucket = bucket
           self.org = org
       
       def get_measurement_data(self, system_id, start_time, end_time):
           """Retrieve measurement data from InfluxDB"""
           query = f'''
           from(bucket: "{self.bucket}")
               |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
               |> filter(fn: (r) => r["_measurement"] == "load")
               |> filter(fn: (r) => r["system_id"] == "{system_id}")
               |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
           '''
           
           result = self.query_api.query_data_frame(query)
           if not result.empty:
               result['datetime'] = pd.to_datetime(result['_time'])
               result = result.set_index('datetime')
               return result[['load']]
           return pd.DataFrame()
       
       def store_forecast(self, system_id, forecast_df):
           """Store forecast results in InfluxDB"""
           for index, row in forecast_df.iterrows():
               point = {
                   "measurement": "forecast",
                   "tags": {"system_id": system_id},
                   "fields": {"forecast": row['forecast'], "quantile_10": row.get('quantile_10', None)},
                   "time": index
               }
               self.write_api.write(bucket=self.bucket, org=self.org, record=point)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For Databricks environments, you can leverage Delta Lake for data storage and retrieval:

.. code-block:: python

   from pyspark.sql import SparkSession
   import pandas as pd
   from delta.tables import DeltaTable
   
   class DatabricksProvider:
       def __init__(self, spark_session=None):
           self.spark = spark_session or SparkSession.builder.appName("OpenSTEF").getOrCreate()
       
       def load_training_data(self, system_id, start_date, end_date):
           """Load training data from Delta Lake"""
           query = f"""
           SELECT datetime, load, temperature, irradiance, windspeed
           FROM energy_measurements
           WHERE system_id = '{system_id}'
           AND datetime BETWEEN '{start_date}' AND '{end_date}'
           ORDER BY datetime
           """
           
           spark_df = self.spark.sql(query)
           return spark_df.toPandas().set_index('datetime')
       
       def save_forecast_results(self, system_id, forecast_df):
           """Save forecast results to Delta Lake"""
           forecast_df_reset = forecast_df.reset_index()
           forecast_df_reset['system_id'] = system_id
           forecast_df_reset['created_at'] = pd.Timestamp.now()
           
           spark_df = self.spark.createDataFrame(forecast_df_reset)
           spark_df.write.format("delta").mode("append").saveAsTable("forecast_results")

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity and flexibility. This section guides you through the migration process based on feedback from production users.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

OpenSTEF V4 introduces several breaking changes that require code updates:

- **Modular architecture**: V4 splits functionality into separate packages (`openstef-core`, `openstef-models`, `openstef-meta`, `openstef-beam`)
- **Decoupled dependencies**: External dependencies like MLFlow and database connections are now optional
- **Type safety**: Full type annotations throughout the codebase
- **Flexible configuration**: Replaces hard-coded assumptions with configurable options

Migration Steps
^^^^^^^^^^^^^^^

1. **Update package imports**: The modular structure requires updated import statements:

.. code-block:: python

   # V3 imports
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import train_model_pipeline
   
   # V4 imports
   from openstef_models.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.workflows import train_model_pipeline

2. **Update configuration handling**: V4 introduces more flexible configuration management:

.. code-block:: python

   # V3 configuration (hard-coded)
   from openstef.data_classes import PredictionJobDataClass
   
   pj = PredictionJobDataClass(
       id=1,
       name="test_job",
       model="xgb",
       # Limited configuration options
   )
   
   # V4 configuration (flexible)
   from openstef_core.data_classes import PredictionJobDataClass
   from openstef_models.config import ModelConfig
   
   model_config = ModelConfig(
       model_type="xgb_quantile",
       hyperparameters={"n_estimators": 100, "max_depth": 6},
       feature_engineering={"lag_features": True, "weather_features": True}
   )
   
   pj = PredictionJobDataClass(
       id=1,
       name="test_job",
       model_config=model_config
   )

3. **Update pipeline calls**: Pipeline interfaces have been streamlined:

.. code-block:: python

   # V3 pipeline usage
   from openstef.pipeline.train_model import train_model_pipeline
   
   trained_model = train_model_pipeline(
       pj=prediction_job,
       input_data=training_data,
       check_old_model_age=True
   )
   
   # V4 pipeline usage
   from openstef_models.workflows import TrainingWorkflow
   
   workflow = TrainingWorkflow(prediction_job)
   trained_model = workflow.run(training_data)

Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

**Database dependency**: V4 makes database connections optional. If you're using custom database providers:

.. code-block:: python

   # V3 - database required
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # V4 - database optional, use custom providers
   from openstef_core.interfaces import DataProvider
   
   class CustomDataProvider(DataProvider):
       def get_load_data(self, system_id, start, end):
           # Your custom data retrieval logic
           pass

**Model serialization**: V4 changes how models are stored and loaded:

.. code-block:: python

   # V3 model storage
   import pickle
   with open('model.pkl', 'wb') as f:
       pickle.dump(trained_model, f)
   
   # V4 model storage (recommended)
   from openstef_models.integrations.joblib import JoblibModelStorage
   
   storage = JoblibModelStorage("models/")
   storage.save_model(trained_model, "my_model_v1")
   loaded_model = storage.load_model("my_model_v1")

.. warning::
   V4 is currently in alpha. Test thoroughly in a development environment before migrating production systems. The stable release will include additional migration tools and documentation.

For detailed migration assistance, consult the :doc:`../reference/changelog` for breaking changes in each version, or reach out to the OpenSTEF community for support with specific migration challenges.