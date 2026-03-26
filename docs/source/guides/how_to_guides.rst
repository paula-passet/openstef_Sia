How-To Guides
=============

This section provides practical, task-specific guides for implementing OpenSTEF in production environments. Unlike tutorials that teach concepts, these guides focus on solving specific deployment and integration challenges.

Setting Up Production Deployment
---------------------------------

OpenSTEF provides flexible deployment options ranging from simple cron-based scheduling to sophisticated orchestration platforms.

Simple Cron-Based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, OpenSTEF's task modules can be executed directly via cron jobs. This approach works well for smaller installations or proof-of-concept deployments.

.. code-block:: python

   from openstef.tasks.create_forecast import main as create_forecast_main
   from openstef.tasks.train_model import main as train_model_main
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Basic forecast creation task
   def run_forecast_task():
       config = load_config()  # Your configuration loading logic
       database = get_database_connection()  # Your database setup
       
       with TaskContext("forecast_task", config, database) as context:
           create_forecast_main(config=config, database=database)

The OpenSTEF task modules are designed to be called directly from cron jobs. Each task handles database connections, error handling, and logging automatically through the ``TaskContext`` manager.

Example cron configuration:

.. code-block:: bash

   # Train models daily at 2 AM
   0 2 * * * /usr/bin/python3 /path/to/your/train_models.py
   
   # Create forecasts every 15 minutes
   */15 * * * * /usr/bin/python3 /path/to/your/create_forecast.py

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more complex workflows requiring dependency management, monitoring, and failure handling, Dagster provides excellent integration with OpenSTEF pipelines.

.. code-block:: python

   from dagster import asset, Config, OpExecutionContext
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   class OpenSTEFConfig(Config):
       prediction_job_id: int
       model_type: str = "xgb"
   
   @asset
   def trained_model(context: OpExecutionContext, config: OpenSTEFConfig):
       """Train an OpenSTEF model for the specified prediction job."""
       # Load prediction job configuration
       pj = load_prediction_job(config.prediction_job_id)
       
       # Prepare training data
       training_data = get_training_data(pj)
       
       # Train model using OpenSTEF pipeline
       model = train_model_pipeline(
           pj=pj,
           input_data=training_data,
           model_type=config.model_type
       )
       
       context.log.info(f"Model trained for PJ {config.prediction_job_id}")
       return model
   
   @asset(deps=[trained_model])
   def forecast(context: OpExecutionContext, config: OpenSTEFConfig):
       """Create forecast using trained model."""
       pj = load_prediction_job(config.prediction_job_id)
       input_data = get_forecast_input_data(pj)
       
       forecast_result = create_forecast_pipeline(
           pj=pj,
           input_data=input_data
       )
       
       # Store forecast results
       save_forecast(forecast_result)
       context.log.info(f"Forecast created for PJ {config.prediction_job_id}")
       return forecast_result

This approach provides dependency tracking, automatic retries, and comprehensive monitoring through Dagster's UI.

Data Integration Patterns
-------------------------

OpenSTEF supports various data sources and storage backends through flexible adapter patterns.

S3 Integration
^^^^^^^^^^^^^^

For cloud-based deployments, S3 provides scalable storage for both input data and model artifacts.

.. code-block:: python

   import boto3
   import pandas as pd
   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   
   class S3DataProvider:
       def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str):
           self.s3_client = boto3.client(
               's3',
               aws_access_key_id=aws_access_key,
               aws_secret_access_key=aws_secret_key
           )
           self.bucket_name = bucket_name
       
       def load_training_data(self, prediction_job_id: int) -> pd.DataFrame:
           """Load training data from S3."""
           key = f"training_data/pj_{prediction_job_id}.parquet"
           
           response = self.s3_client.get_object(
               Bucket=self.bucket_name, 
               Key=key
           )
           
           return pd.read_parquet(response['Body'])
       
       def save_forecast(self, forecast_data: pd.DataFrame, prediction_job_id: int):
           """Save forecast results to S3."""
           key = f"forecasts/pj_{prediction_job_id}_{pd.Timestamp.now().date()}.parquet"
           
           # Convert to parquet bytes
           parquet_buffer = forecast_data.to_parquet()
           
           self.s3_client.put_object(
               Bucket=self.bucket_name,
               Key=key,
               Body=parquet_buffer
           )

For benchmark storage, OpenSTEF provides built-in S3 integration:

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   
   # Set up hybrid local/S3 storage
   local_storage = LocalBenchmarkStorage(base_path="/tmp/benchmarks")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="my-openstef-benchmarks",
       s3_prefix="production/",
       s3fs_kwargs={
           'key': 'your-access-key',
           'secret': 'your-secret-key'
       }
   )

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time-series focused deployments, InfluxDB provides efficient storage and querying capabilities.

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd
   
   class InfluxDBProvider:
       def __init__(self, url: str, token: str, org: str, bucket: str):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.bucket = bucket
           self.org = org
       
       def load_measurement_data(self, prediction_job_id: int, 
                               start_time: str, end_time: str) -> pd.DataFrame:
           """Load measurement data from InfluxDB."""
           query = f'''
           from(bucket: "{self.bucket}")
             |> range(start: {start_time}, stop: {end_time})
             |> filter(fn: (r) => r["_measurement"] == "load")
             |> filter(fn: (r) => r["prediction_job_id"] == "{prediction_job_id}")
             |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
           '''
           
           query_api = self.client.query_api()
           result = query_api.query_data_frame(query=query, org=self.org)
           
           # Convert to OpenSTEF expected format
           result.set_index('_time', inplace=True)
           return result[['load']]
       
       def write_forecast(self, forecast_data: pd.DataFrame, prediction_job_id: int):
           """Write forecast results to InfluxDB."""
           write_api = self.client.write_api(write_options=SYNCHRONOUS)
           
           points = []
           for timestamp, row in forecast_data.iterrows():
               point = Point("forecast") \
                   .tag("prediction_job_id", str(prediction_job_id)) \
                   .field("forecast", float(row['forecast'])) \
                   .field("quantile_10", float(row.get('quantile_0.1', 0))) \
                   .field("quantile_90", float(row.get('quantile_0.9', 0))) \
                   .time(timestamp)
               points.append(point)
           
           write_api.write(bucket=self.bucket, org=self.org, record=points)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For large-scale data processing, Databricks provides powerful distributed computing capabilities.

.. code-block:: python

   from databricks.sql import connect
   import pandas as pd
   
   class DatabricksProvider:
       def __init__(self, server_hostname: str, http_path: str, access_token: str):
           self.connection = connect(
               server_hostname=server_hostname,
               http_path=http_path,
               access_token=access_token
           )
       
       def load_aggregated_data(self, prediction_job_ids: list, 
                              start_date: str, end_date: str) -> pd.DataFrame:
           """Load aggregated training data from Databricks."""
           pj_list = ','.join(map(str, prediction_job_ids))
           
           query = f"""
           SELECT 
               prediction_job_id,
               datetime,
               load,
               temperature,
               wind_speed,
               solar_irradiance
           FROM energy_measurements 
           WHERE prediction_job_id IN ({pj_list})
             AND datetime BETWEEN '{start_date}' AND '{end_date}'
           ORDER BY prediction_job_id, datetime
           """
           
           return pd.read_sql(query, self.connection)
       
       def batch_train_models(self, prediction_jobs: list):
           """Train multiple models in parallel using Databricks."""
           # This would typically use Databricks Jobs API or MLflow
           # for distributed model training
           pass

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 introduces significant architectural changes that improve modularity and flexibility. This guide helps you migrate existing V3 implementations.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant change is the modular architecture. OpenSTEF V4 splits functionality into focused packages:

- ``openstef-core``: Data types, interfaces, and shared utilities
- ``openstef-models``: Forecasting models and preprocessing
- ``openstef-meta``: Advanced ensemble models  
- ``openstef-beam``: Backtesting, evaluation, and analysis

Package Import Changes
^^^^^^^^^^^^^^^^^^^^^^

Update your imports to reflect the new package structure:

.. code-block:: python

   # V3 imports
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.model.regressors.xgb import XGBOpenstef
   from openstef.validation.validation import validate_data
   
   # V4 imports
   from openstef_models.workflows.train_model import train_model_pipeline
   from openstef_models.model.regressors.xgb import XGBOpenstef  
   from openstef_models.validation.validation import validate_data

Configuration Updates
^^^^^^^^^^^^^^^^^^^^^

V4 introduces more flexible configuration patterns. Update your prediction job configurations:

.. code-block:: python

   # V3 style - rigid structure
   prediction_job = {
       'id': 123,
       'model': 'xgb',
       'quantiles': [0.1, 0.5, 0.9],
       'feature_names': ['load_7d', 'temp', 'wind']
   }
   
   # V4 style - more flexible with presets
   from openstef_models.model.presets import get_preset_config
   
   # Use preset for quick setup
   prediction_job = get_preset_config(
       use_case='congestion_management',
       prediction_job_id=123,
       quantiles=[0.1, 0.5, 0.9]
   )
   
   # Or customize fully
   from openstef_core.data_classes import PredictionJobDataClass
   
   prediction_job = PredictionJobDataClass(
       id=123,
       model_type='xgb_quantile',
       quantiles=[0.1, 0.5, 0.9],
       feature_engineering_config={
           'lag_features': True,
           'weather_features': True,
           'calendar_features': True
       }
   )

Pipeline API Changes
^^^^^^^^^^^^^^^^^^^^

The pipeline APIs are more consistent in V4:

.. code-block:: python

   # V3 - mixed parameter patterns
   model = train_model_pipeline(
       pj, 
       input_data, 
       check_old_model_age=True,
       datetime_start=start_date
   )
   
   # V4 - consistent configuration objects
   from openstef_models.workflows import TrainingConfig
   
   config = TrainingConfig(
       check_old_model_age=True,
       datetime_start=start_date,
       datetime_end=end_date
   )
   
   model = train_model_pipeline(
       prediction_job=pj,
       input_data=input_data,
       config=config
   )

Evaluation and Benchmarking
^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 introduces the powerful ``openstef-beam`` package for evaluation:

.. code-block:: python

   # V3 - basic evaluation
   from openstef.metrics import calc_metrics
   
   metrics = calc_metrics(y_true, y_pred, quantiles)
   
   # V4 - comprehensive benchmarking
   from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkConfig
   from openstef_beam.evaluation import EvaluationConfig
   
   benchmark_config = BenchmarkConfig(
       targets=target_list,
       evaluation_config=EvaluationConfig(
           metrics=['mae', 'mape', 'crps'],
           quantile_metrics=True
       )
   )
   
   pipeline = BenchmarkPipeline(benchmark_config)
   results = pipeline.run_backtest()

Migration Checklist
^^^^^^^^^^^^^^^^^^^^

1. **Update dependencies**: Replace ``openstef`` with the new V4 packages
2. **Refactor imports**: Update all import statements to new package structure  
3. **Update configurations**: Migrate to new configuration classes or use presets
4. **Test pipelines**: Verify that your training and forecasting pipelines work
5. **Migrate evaluation**: Take advantage of new benchmarking capabilities
6. **Update deployment**: Ensure your orchestration handles new package structure

.. note::
   V4 is designed to be more modular, so you only need to install the packages you actually use. For basic forecasting, ``openstef-core`` and ``openstef-models`` are sufficient.

For detailed migration support, see the changelog or reach out to the OpenSTEF community through our `Slack channel <https://slack.lfenergy.org/>`_.