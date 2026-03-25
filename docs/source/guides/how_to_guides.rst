How-to Guides
=============


Setting Up Simple Deployments
-----------------------------


OpenSTEF is a library designed for integration into production forecasting systems. Common deployment patterns include scheduled CRON jobs for automated model training and forecast generation, containerized workflows using Kubernetes CronJobs, and direct Python script execution. The library's pipeline-based architecture supports flexible deployment configurations, allowing organizations to implement training, forecasting, and optimization tasks according to their operational requirements and infrastructure constraints.


.. code-block:: python

   # Train models daily at 2 AM
   0 2 * * * cd /path/to/openstef && python -m openstef.tasks.train_model

   # Create forecasts every hour
   0 * * * * cd /path/to/openstef && python -m openstef.tasks.create_forecast

   # Optimize hyperparameters weekly on Sundays at 3 AM
   0 3 * * 0 cd /path/to/openstef && python -m openstef.tasks.optimize_hyperparameters

   # Create wind forecasts every 6 hours
   0 */6 * * * cd /path/to/openstef && python -m openstef.tasks.create_wind_forecast


Data Integration Patterns
-------------------------


OpenSTEF library integrates with various data sources through flexible patterns. The core library accepts pandas DataFrames, allowing integration with databases, APIs, and file formats. Custom database connectors can be implemented using the OpenSTEF-dbc pattern for company-specific data sources.

Data integration typically involves fetching input data, feature preparation, and feeding processed datasets to OpenSTEF's forecasting functions. The library supports time-series data formats commonly used in energy forecasting, including weather data, load measurements, and external features required for accurate predictions.


.. code-block:: python

   import pandas as pd
   from influxdb_client import InfluxDBClient
   import boto3
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Configure InfluxDB connection
   influx_client = InfluxDBClient(
       url="http://localhost:8086",
       token="your-token",
       org="your-org"
   )

   # Configure S3 connection
   s3_client = boto3.client(
       's3',
       aws_access_key_id='your-access-key',
       aws_secret_access_key='your-secret-key'
   )

   def fetch_training_data():
       query = '''
       from(bucket: "energy_data")
         |> range(start: -30d)
         |> filter(fn: (r) => r["_measurement"] == "load")
         |> filter(fn: (r) => r["_field"] == "value")
       '''

       tables = influx_client.query_api().query(query)
       data = []
       for table in tables:
           for record in table.records:
               data.append({
                   'datetime': record.get_time(),
                   'load': record.get_value()
               })

       return pd.DataFrame(data).set_index('datetime')

   def store_forecast_to_s3(forecast_df, prediction_job_id):
       csv_buffer = forecast_df.to_csv()
       s3_key = f"forecasts/{prediction_job_id}/forecast.csv"

       s3_client.put_object(
           Bucket='energy-forecasts',
           Key=s3_key,
           Body=csv_buffer
       )

   # Retrieve data and create forecast
   training_data = fetch_training_data()

   model = train_model_pipeline(
       pj={'id': 123, 'model': 'arima'},
       input_data=training_data
   )

   forecast = create_forecast_pipeline(
       pj={'id': 123},
       model=model,
       input_data=training_data
   )

   store_forecast_to_s3(forecast, prediction_job_id=123)


Orchestration with Dagster
--------------------------


Dagster provides robust orchestration capabilities for OpenSTEF's machine learning pipelines, enabling production-ready scheduling, monitoring, and dependency management. The integration leverages OpenSTEF's modular architecture to create scalable workflows that handle data availability constraints and maintain performance standards.

Setup requires installing both OpenSTEF and Dagster packages, then wrapping OpenSTEF pipelines as Dagster assets or ops. This approach supports complex enterprise environments with custom APIs while preserving OpenSTEF's unopinionated design principles for forecasting workflows.


.. code-block:: python

   from dagster import asset, job, Config, OpExecutionContext
   from openstef.pipeline import train_model, create_forecast
   import pandas as pd

   class ForecastConfig(Config):
       prediction_id: int
       horizon_hours: int = 47

   @asset
   def training_data(context: OpExecutionContext) -> pd.DataFrame:
       """Load and prepare training data for model training."""
       # Load your data source here
       data = pd.read_csv("energy_data.csv")
       data["datetime"] = pd.to_datetime(data["datetime"])
       return data

   @asset
   def trained_model(context: OpExecutionContext, training_data: pd.DataFrame):
       """Train OpenSTEF model using pipeline."""
       model_config = {
           "id": 307,
           "name": "wind_turbine_forecast",
           "type": "wind",
           "resolution_minutes": 15
       }

       trained_model = train_model(
           pj=model_config,
           input_data=training_data,
           datetime_start="2023-01-01",
           datetime_end="2023-12-31"
       )

       return trained_model

   @asset
   def forecast_output(context: OpExecutionContext, config: ForecastConfig, trained_model) -> pd.DataFrame:
       """Generate forecast using trained model."""
       forecast_data = create_forecast(
           pj={"id": config.prediction_id, "name": "production_forecast"},
           input_data=pd.DataFrame(),
           model=trained_model,
           horizon_hours=config.horizon_hours
       )

       return forecast_data

   @job(config=ForecastConfig)
   def openstef_forecasting_job():
       """Complete OpenSTEF forecasting workflow."""
       data = training_data()
       model = trained_model(data)
       forecast_output(model)


Migrating from OpenSTEF v3
--------------------------


- External dependencies like MLFlow, openstef-dbc, and xgboost/gblinear are now decoupled - update your integration code accordingly

- Data preprocessing logic has been centralized - migrate custom preprocessing to use new unified interfaces

- Hard-coded assumptions replaced with flexible configuration - review and update configuration files

- Input data constraints relaxed - validate your data formats against new flexible schemas

- Domain-specific logic generalized - update holiday calendars and regional settings for non-Dutch deployments

- Modular architecture introduced - refactor monolithic implementations to use new composable components

- Type safety enforced throughout - add type annotations to custom code and fix type-related errors

- Pipeline APIs redesigned - update integration points to use new callback mechanisms

- Test coverage requirements increased - ensure custom components meet new testing standards


.. code-block:: python

   OpenSTEF v3.x:


   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   from openstef.data_classes import PredictionJobDataClass

   # Old configuration approach
   config = {
       'model': 'xgb',
       'quantiles': [0.1, 0.5, 0.9],
       'horizon_minutes': 2880
   }

   # Pipeline creation with hard-coded dependencies
   pipeline = create_forecast_pipeline(config)
   model = XGBQuantileOpenstfRegressor()


   OpenSTEF v4.x:


   from openstef.models import QuantileRegressor
   from openstef.pipeline import ForecastPipeline
   from openstef.config import PipelineConfig

   # New modular configuration
   config = PipelineConfig(
       model_type='quantile_regressor',
       quantiles=[0.1, 0.5, 0.9],
       forecast_horizon_hours=48
   )

   # Decoupled pipeline with flexible model selection
   pipeline = ForecastPipeline(config)
   model = QuantileRegressor(backend='xgboost')


