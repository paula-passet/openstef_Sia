How-to Guides
=============

This section provides practical, task-specific guides for implementing OpenSTEF in production environments. These guides focus on specific integration challenges and deployment patterns commonly encountered when using OpenSTEF as a forecasting library in operational systems.

Setting up Production Deployment
---------------------------------

OpenSTEF is a Python library designed to be integrated into your existing infrastructure. Here are common deployment patterns for operational forecasting systems.

Simple Cron-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For basic deployments, you can schedule OpenSTEF forecasting tasks using cron jobs. This approach works well for smaller systems or when integrating with existing cron-based workflows.

.. code-block:: python

   # forecast_job.py
   import logging
   from datetime import datetime, timedelta
   from openstef_models.model.regressors import XGBRegressorModel
   from openstef_models.pipelines.train import train_model_pipeline
   from openstef_models.pipelines.predict import predict_pipeline
   from openstef_core.datasets import TabularDataset

   def run_forecast_job():
       """Main forecasting job to be called by cron."""
       try:
           # Load your data (implement based on your data source)
           data = load_training_data()
           
           # Train model if needed (daily/weekly schedule)
           if should_retrain_model():
               model = train_model_pipeline(
                   data=data,
                   model_type=XGBRegressorModel,
                   horizons=[0.25, 24.0, 47.0]
               )
               save_model(model)
           
           # Create forecast
           model = load_model()
           forecast_data = load_forecast_data()
           
           forecast = predict_pipeline(
               model=model,
               data=forecast_data,
               horizons=[0.25, 24.0, 47.0]
           )
           
           # Store results (implement based on your storage)
           store_forecast(forecast)
           
           logging.info(f"Forecast completed at {datetime.now()}")
           
       except Exception as e:
           logging.error(f"Forecast job failed: {e}")
           send_alert(f"OpenSTEF forecast failed: {e}")

   if __name__ == "__main__":
       run_forecast_job()

Add this to your crontab for hourly forecasts:

.. code-block:: bash

   # Run forecast every hour at minute 15
   15 * * * * /path/to/venv/bin/python /path/to/forecast_job.py

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more sophisticated orchestration with dependency management, monitoring, and retry logic, Dagster provides an excellent framework for OpenSTEF deployments.

.. code-block:: python

   # dagster_forecast.py
   from dagster import asset, job, op, Config, OpExecutionContext
   from openstef_models.pipelines.train import train_model_pipeline
   from openstef_models.pipelines.predict import predict_pipeline
   from openstef_models.model.regressors import XGBRegressorModel
   import pandas as pd

   class ForecastConfig(Config):
       prediction_job_id: int
       horizons: list[float] = [0.25, 24.0, 47.0]
       retrain_threshold_days: int = 7

   @asset
   def training_data(context: OpExecutionContext) -> pd.DataFrame:
       """Load and prepare training data."""
       # Implement your data loading logic
       data = load_data_from_source()
       context.log.info(f"Loaded {len(data)} training records")
       return data

   @asset(deps=[training_data])
   def trained_model(context: OpExecutionContext, config: ForecastConfig):
       """Train model if needed."""
       if model_needs_retraining(config.retrain_threshold_days):
           data = training_data
           model = train_model_pipeline(
               data=data,
               model_type=XGBRegressorModel,
               horizons=config.horizons
           )
           context.log.info("Model retrained successfully")
           return model
       else:
           return load_existing_model()

   @asset(deps=[trained_model])
   def forecast_results(context: OpExecutionContext, config: ForecastConfig):
       """Generate forecast using trained model."""
       model = trained_model
       forecast_data = load_forecast_input_data()
       
       forecast = predict_pipeline(
           model=model,
           data=forecast_data,
           horizons=config.horizons
       )
       
       context.log.info(f"Generated forecast with {len(forecast)} predictions")
       return forecast

   @job
   def forecast_job():
       forecast_results()

Data Integration Patterns
--------------------------

OpenSTEF integrates with various data sources and storage systems. Here are common integration patterns for different platforms.

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

For cloud-based deployments, S3 provides scalable storage for both input data and forecast results.

.. code-block:: python

   # s3_integration.py
   import boto3
   import pandas as pd
   from io import StringIO
   from openstef_core.datasets import TabularDataset

   class S3DataProvider:
       def __init__(self, bucket_name: str, aws_profile: str = None):
           self.bucket_name = bucket_name
           self.s3_client = boto3.client('s3', profile_name=aws_profile)
       
       def load_training_data(self, prediction_job_id: int) -> TabularDataset:
           """Load training data from S3."""
           key = f"training_data/pj_{prediction_job_id}/data.parquet"
           
           response = self.s3_client.get_object(
               Bucket=self.bucket_name, 
               Key=key
           )
           
           df = pd.read_parquet(response['Body'])
           return TabularDataset(df)
       
       def save_forecast(self, forecast: pd.DataFrame, prediction_job_id: int):
           """Save forecast results to S3."""
           key = f"forecasts/pj_{prediction_job_id}/{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.parquet"
           
           parquet_buffer = StringIO()
           forecast.to_parquet(parquet_buffer)
           
           self.s3_client.put_object(
               Bucket=self.bucket_name,
               Key=key,
               Body=parquet_buffer.getvalue()
           )

   # Usage example
   data_provider = S3DataProvider("my-openstef-bucket")
   training_data = data_provider.load_training_data(prediction_job_id=123)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For organizations using Databricks, OpenSTEF can be integrated into existing data pipelines and notebooks.

.. code-block:: python

   # databricks_integration.py
   from pyspark.sql import SparkSession
   from openstef_models.pipelines.train import train_model_pipeline
   from openstef_core.datasets import TabularDataset

   def run_openstef_on_databricks(table_name: str, prediction_job_id: int):
       """Run OpenSTEF training and prediction in Databricks environment."""
       spark = SparkSession.builder.getOrCreate()
       
       # Load data from Delta table
       spark_df = spark.table(table_name).filter(
           f"prediction_job_id = {prediction_job_id}"
       )
       
       # Convert to pandas for OpenSTEF
       pandas_df = spark_df.toPandas()
       dataset = TabularDataset(pandas_df)
       
       # Train model
       model = train_model_pipeline(
           data=dataset,
           horizons=[0.25, 24.0, 47.0]
       )
       
       # Save model to DBFS
       model_path = f"/dbfs/openstef/models/pj_{prediction_job_id}"
       save_model_to_path(model, model_path)
       
       return model

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time series databases like InfluxDB, OpenSTEF can read historical data and write forecast results efficiently.

.. code-block:: python

   # influxdb_integration.py
   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd
   from openstef_core.datasets import TabularDataset

   class InfluxDBProvider:
       def __init__(self, url: str, token: str, org: str):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.org = org
       
       def load_historical_data(self, bucket: str, measurement: str, 
                              start_time: str, prediction_job_id: int) -> TabularDataset:
           """Load historical data for training."""
           query = f'''
           from(bucket: "{bucket}")
             |> range(start: {start_time})
             |> filter(fn: (r) => r["_measurement"] == "{measurement}")
             |> filter(fn: (r) => r["prediction_job_id"] == "{prediction_job_id}")
             |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
           '''
           
           query_api = self.client.query_api()
           result = query_api.query_data_frame(query, org=self.org)
           
           return TabularDataset(result)
       
       def write_forecast(self, forecast: pd.DataFrame, bucket: str, 
                         measurement: str, prediction_job_id: int):
           """Write forecast results to InfluxDB."""
           write_api = self.client.write_api(write_options=SYNCHRONOUS)
           
           points = []
           for _, row in forecast.iterrows():
               point = Point(measurement) \
                   .tag("prediction_job_id", str(prediction_job_id)) \
                   .field("forecast", row['forecast']) \
                   .field("quantile_10", row.get('quantile_10', None)) \
                   .field("quantile_90", row.get('quantile_90', None)) \
                   .time(row['datetime'])
               points.append(point)
           
           write_api.write(bucket=bucket, org=self.org, record=points)

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity and flexibility. This section guides you through the migration process.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant changes in V4 include:

- **Modular architecture**: Core functionality split into separate packages (openstef-models, openstef-beam, openstef-core)
- **Type safety**: Full type annotations throughout the codebase
- **Flexible configuration**: Configuration-driven approach replacing hard-coded assumptions
- **Improved data handling**: New dataset abstractions with better validation
- **Pipeline-based workflows**: Clear separation between training and prediction pipelines

Migration Steps
^^^^^^^^^^^^^^^

1. **Update package imports**: V4 uses a new package structure.

.. code-block:: python

   # V3 imports
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline.train_model import train_model
   
   # V4 imports
   from openstef_models.model.regressors import XGBRegressorModel
   from openstef_models.pipelines.train import train_model_pipeline

2. **Adapt data loading**: V4 uses new dataset classes.

.. code-block:: python

   # V3 approach
   data = pd.read_csv("data.csv")
   model = train_model(data, model_type="xgb")
   
   # V4 approach
   from openstef_core.datasets import TabularDataset
   
   data = pd.read_csv("data.csv")
   dataset = TabularDataset(data)
   model = train_model_pipeline(
       data=dataset,
       model_type=XGBRegressorModel
   )

3. **Update prediction workflows**: V4 separates training and prediction pipelines.

.. code-block:: python

   # V4 prediction workflow
   from openstef_models.pipelines.predict import predict_pipeline
   
   forecast = predict_pipeline(
       model=trained_model,
       data=forecast_dataset,
       horizons=[0.25, 24.0, 47.0]
   )

4. **Configuration migration**: V4 uses structured configuration objects.

.. code-block:: python

   # V4 configuration approach
   from openstef_models.config import ModelConfig
   
   config = ModelConfig(
       model_type=XGBRegressorModel,
       horizons=[0.25, 24.0, 47.0],
       feature_engineering_params={
           'weather_features': True,
           'lag_features': [1, 24, 168]
       }
   )

.. note::
   For detailed migration assistance, consult the `V4 Migration Guide <https://github.com/OpenSTEF/openstef/discussions>`_ in our GitHub discussions or join our community Slack channel.

Common Integration Challenges
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Data format compatibility**: Ensure your data includes required columns (datetime, load, weather variables). V4 provides better validation to catch issues early.

**Model persistence**: V4 uses a new model serialization format. Retrain existing models or use the migration utilities provided in the openstef-models package.

**Custom features**: If you've implemented custom feature engineering in V3, review the new extensible feature engineering system in V4.

For additional support during migration, see our :doc:`../project/support` page or join our community discussions.