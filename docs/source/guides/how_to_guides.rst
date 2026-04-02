How-To Guides
=============

This page provides practical, task-specific guides for implementing OpenSTEF in your environment. Unlike the tutorials which walk you through learning the library, these guides focus on solving specific integration and deployment challenges you'll face when putting OpenSTEF into production.

Each guide addresses a common implementation task with working examples you can adapt to your needs.


Setting Up Deployment
---------------------

OpenSTEF is a Python library, not a standalone application. You need to integrate it into your own scheduling and orchestration infrastructure. Here are common approaches.

Simple Cron-Based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, a cron job can trigger your forecasting script at regular intervals.

Create a Python script that runs your forecast pipeline:

.. code-block:: python

   # forecast_job.py
   import logging
   from datetime import datetime, timedelta
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   def run_forecast():
       """Run forecast for all prediction jobs."""
       try:
           # Load your prediction jobs from database or config
           prediction_jobs = load_prediction_jobs()
           
           for pj in prediction_jobs:
               logger.info(f"Creating forecast for {pj['name']}")
               
               # Load input data for this prediction job
               input_data = load_input_data(pj['id'])
               
               # Create forecast
               forecast = create_forecast_pipeline(
                   pj=pj,
                   input_data=input_data
               )
               
               # Save forecast to your database
               save_forecast(pj['id'], forecast)
               
           logger.info("All forecasts completed successfully")
           
       except Exception as e:
           logger.error(f"Forecast job failed: {e}")
           raise
   
   if __name__ == "__main__":
       run_forecast()

Add to your crontab to run every 15 minutes:

.. code-block:: bash

   # Run forecast every 15 minutes
   */15 * * * * /path/to/venv/bin/python /path/to/forecast_job.py >> /var/log/openstef/forecast.log 2>&1

For model training, run less frequently (e.g., daily):

.. code-block:: bash

   # Retrain models daily at 2 AM
   0 2 * * * /path/to/venv/bin/python /path/to/train_job.py >> /var/log/openstef/training.log 2>&1

.. note::
   Ensure your script handles errors gracefully and logs appropriately. Consider adding alerting for failed runs.


Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more complex workflows with dependencies, monitoring, and retries, use an orchestration tool like Dagster.

.. code-block:: python

   # dagster_forecast.py
   from dagster import asset, AssetExecutionContext, Definitions, ScheduleDefinition
   from datetime import datetime
   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   @asset
   def prediction_jobs(context: AssetExecutionContext) -> list:
       """Load prediction job configurations."""
       context.log.info("Loading prediction jobs")
       # Load from your configuration source
       return load_prediction_jobs_from_db()
   
   @asset
   def input_data(context: AssetExecutionContext, prediction_jobs: list) -> dict:
       """Load input data for all prediction jobs."""
       context.log.info("Loading input data")
       data = {}
       for pj in prediction_jobs:
           data[pj['id']] = load_input_data(pj['id'])
       return data
   
   @asset
   def forecasts(
       context: AssetExecutionContext,
       prediction_jobs: list,
       input_data: dict
   ) -> dict:
       """Generate forecasts for all prediction jobs."""
       results = {}
       for pj in prediction_jobs:
           context.log.info(f"Creating forecast for {pj['name']}")
           forecast = create_forecast_pipeline(
               pj=pj,
               input_data=input_data[pj['id']]
           )
           results[pj['id']] = forecast
       return results
   
   @asset
   def saved_forecasts(context: AssetExecutionContext, forecasts: dict) -> None:
       """Save forecasts to database."""
       for pj_id, forecast in forecasts.items():
           context.log.info(f"Saving forecast for job {pj_id}")
           save_forecast_to_db(pj_id, forecast)
   
   # Schedule to run every 15 minutes
   forecast_schedule = ScheduleDefinition(
       name="forecast_schedule",
       target=saved_forecasts,
       cron_schedule="*/15 * * * *"
   )
   
   defs = Definitions(
       assets=[prediction_jobs, input_data, forecasts, saved_forecasts],
       schedules=[forecast_schedule]
   )

This approach provides:

- Dependency management between tasks
- Automatic retries on failure
- Web UI for monitoring
- Asset versioning and lineage

See the `Dagster documentation <https://docs.dagster.io/>`_ for deployment options.


Integrating Data Sources
-------------------------

OpenSTEF requires input data (load measurements, weather forecasts) and produces output forecasts. You need to integrate these with your data infrastructure.

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

Store input data and forecasts in S3 buckets.

.. code-block:: python

   import boto3
   import pandas as pd
   from io import StringIO
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Initialize S3 client
   s3_client = boto3.client('s3')
   
   def load_input_data_from_s3(bucket: str, key: str) -> pd.DataFrame:
       """Load input data from S3."""
       obj = s3_client.get_object(Bucket=bucket, Key=key)
       return pd.read_csv(obj['Body'])
   
   def save_forecast_to_s3(
       forecast: pd.DataFrame,
       bucket: str,
       key: str
   ) -> None:
       """Save forecast to S3."""
       csv_buffer = StringIO()
       forecast.to_csv(csv_buffer, index=True)
       s3_client.put_object(
           Bucket=bucket,
           Key=key,
           Body=csv_buffer.getvalue()
       )
   
   # Example usage
   def run_forecast_with_s3():
       # Load prediction job config
       pj = load_prediction_job()
       
       # Load input data from S3
       input_data = load_input_data_from_s3(
           bucket='my-openstef-data',
           key=f'input/{pj["id"]}/latest.csv'
       )
       
       # Create forecast
       forecast = create_forecast_pipeline(pj=pj, input_data=input_data)
       
       # Save to S3
       timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
       save_forecast_to_s3(
           forecast=forecast,
           bucket='my-openstef-forecasts',
           key=f'forecasts/{pj["id"]}/{timestamp}.csv'
       )

.. note::
   Consider using partitioned storage (by date, prediction job) for efficient querying and lifecycle management.


Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

Use Databricks for data processing and model training at scale.

.. code-block:: python

   from pyspark.sql import SparkSession
   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Initialize Spark session
   spark = SparkSession.builder.getOrCreate()
   
   def load_training_data_from_delta(table_name: str, pj_id: int) -> pd.DataFrame:
       """Load training data from Delta table."""
       df_spark = spark.table(table_name).filter(f"prediction_job_id = {pj_id}")
       return df_spark.toPandas()
   
   def save_model_to_delta(pj_id: int, model_specs: dict) -> None:
       """Save trained model metadata to Delta table."""
       model_df = spark.createDataFrame([{
           'prediction_job_id': pj_id,
           'trained_at': pd.Timestamp.now(),
           'model_type': model_specs['model'],
           'feature_names': str(model_specs['feature_names'])
       }])
       model_df.write.mode('append').saveAsTable('openstef_models')
   
   # Example training job
   def train_on_databricks(pj_id: int):
       # Load prediction job config
       pj = load_prediction_job(pj_id)
       
       # Load training data from Delta Lake
       training_data = load_training_data_from_delta('openstef_input_data', pj_id)
       
       # Train model
       model_specs = train_model_pipeline(
           pj=pj,
           input_data=training_data
       )
       
       # Save model metadata
       save_model_to_delta(pj_id, model_specs)
       
       return model_specs

You can run this as a Databricks job scheduled through the Databricks UI or API.


InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

InfluxDB is commonly used for time-series data storage in energy systems.

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Initialize InfluxDB client
   client = InfluxDBClient(
       url="http://localhost:8086",
       token="my-token",
       org="my-org"
   )
   
   def load_input_data_from_influx(
       bucket: str,
       measurement: str,
       start: str,
       stop: str
   ) -> pd.DataFrame:
       """Load input data from InfluxDB."""
       query_api = client.query_api()
       
       query = f'''
       from(bucket: "{bucket}")
           |> range(start: {start}, stop: {stop})
           |> filter(fn: (r) => r["_measurement"] == "{measurement}")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
       '''
       
       result = query_api.query_data_frame(query)
       result['_time'] = pd.to_datetime(result['_time'])
       return result.set_index('_time')
   
   def save_forecast_to_influx(
       forecast: pd.DataFrame,
       bucket: str,
       measurement: str,
       pj_id: int
   ) -> None:
       """Save forecast to InfluxDB."""
       write_api = client.write_api(write_options=SYNCHRONOUS)
       
       for timestamp, row in forecast.iterrows():
           point = Point(measurement) \
               .tag("prediction_job_id", str(pj_id)) \
               .time(timestamp)
           
           # Add forecast quantiles
           for col in forecast.columns:
               point = point.field(col, float(row[col]))
           
           write_api.write(bucket=bucket, record=point)
   
   # Example usage
   def run_forecast_with_influx(pj_id: int):
       pj = load_prediction_job(pj_id)
       
       # Load last 14 days of data
       input_data = load_input_data_from_influx(
           bucket='openstef-input',
           measurement='load',
           start='-14d',
           stop='now()'
       )
       
       # Create forecast
       forecast = create_forecast_pipeline(pj=pj, input_data=input_data)
       
       # Save to InfluxDB
       save_forecast_to_influx(
           forecast=forecast,
           bucket='openstef-forecasts',
           measurement='forecast',
           pj_id=pj_id
       )

.. note::
   InfluxDB 2.x uses a different API than 1.x. Ensure you're using the correct client library version.


Migrating from V3 to V4
------------------------

OpenSTEF V4 introduced significant changes to improve usability and maintainability. This guide helps you migrate existing V3 code.

Key Breaking Changes
^^^^^^^^^^^^^^^^^^^^

**Pipeline Functions**

V3 used class-based pipelines. V4 uses simple functions:

.. code-block:: python

   # V3 approach
   from openstef.pipeline import Pipeline
   pipeline = Pipeline()
   forecast = pipeline.create_forecast(pj, input_data)
   
   # V4 approach
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   forecast = create_forecast_pipeline(pj=pj, input_data=input_data)

**Prediction Job Structure**

V4 expects prediction jobs as dictionaries rather than custom objects:

.. code-block:: python

   # V4 prediction job format
   pj = {
       'id': 307,
       'name': 'Substation_A',
       'model': 'xgb',
       'quantiles': [0.1, 0.5, 0.9],
       'horizon_minutes': 2880,  # 48 hours
       'resolution_minutes': 15,
       'lat': 52.1326,
       'lon': 5.2913
   }

**Input Data Format**

Input data must be a pandas DataFrame with DatetimeIndex:

.. code-block:: python

   # Required columns depend on use case
   # For basic load forecasting:
   input_data = pd.DataFrame({
       'load': [...],  # Historical load measurements
       'radiation': [...],  # Solar radiation forecast
       'windspeed': [...],  # Wind speed forecast
       'temperature': [...]  # Temperature forecast
   }, index=pd.DatetimeIndex([...]))

Migration Steps
^^^^^^^^^^^^^^^

1. **Update imports**: Replace class-based pipeline imports with function imports
2. **Convert prediction jobs**: Transform custom objects to dictionaries
3. **Update pipeline calls**: Use new function-based API
4. **Test thoroughly**: Verify forecast outputs match expected behavior

Example V3 to V4 Migration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # V3 code
   from openstef.pipeline import Pipeline
   from openstef.model.prediction_job import PredictionJob
   
   pj = PredictionJob(id=307, name='Substation_A', model='xgb')
   pipeline = Pipeline()
   forecast = pipeline.create_forecast(pj, input_data)
   
   # V4 equivalent
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   pj = {
       'id': 307,
       'name': 'Substation_A',
       'model': 'xgb',
       'quantiles': [0.1, 0.5, 0.9],
       'horizon_minutes': 2880,
       'resolution_minutes': 15
   }
   forecast = create_forecast_pipeline(pj=pj, input_data=input_data)

.. note::
   If you encounter issues during migration, check the changelog for detailed breaking changes or ask in the OpenSTEF community channels.


Next Steps
----------

- See :doc:`../getting_started/tutorials` for comprehensive examples of OpenSTEF workflows
- Review :doc:`use_cases` to understand different forecasting scenarios
- Check :doc:`faq` for common questions about deployment and integration