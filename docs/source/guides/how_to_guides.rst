How-to Guides
=============


Deployment Setup
----------------


When deploying OpenSTEF as a library in production environments, consider integrating its pipelines into existing orchestration workflows. The library's modular design allows you to embed forecasting functionality into custom applications or scheduled batch processes. Production deployments typically require proper error handling, logging, and monitoring around pipeline execution. Consider data persistence strategies for model artifacts and forecast outputs, as OpenSTEF focuses on computation rather than storage management.


.. code-block:: python

   # Cron job example for daily forecast generation
   0 6 * * * /usr/bin/python3 -c "
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd

   # Load prediction job configuration
   pj = PredictionJob(id=123, model='xgb', horizon_minutes=2880)
   forecast = create_forecast_pipeline(pj, datetime_start=pd.Timestamp.now())
   "

   # Dagster orchestration example
   from dagster import op, job, schedule, DailyPartitionsDefinition
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJob

   @op
   def train_model_op():
       pj = PredictionJob(id=123, model='xgb', horizon_minutes=2880)
       return train_model_pipeline(pj)

   @op
   def create_forecast_op():
       pj = PredictionJob(id=123, model='xgb', horizon_minutes=2880)
       return create_forecast_pipeline(pj)

   @job(partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"))
   def openstef_forecast_job():
       create_forecast_op()

   @schedule(job=openstef_forecast_job, cron_schedule="0 6 * * *")
   def daily_forecast_schedule():
       return {}


Data Integration
----------------


OpenSTEF library supports integration with various data sources through flexible connector patterns. The OpenSTEF-dbc package provides database interfaces for SQL databases, InfluxDB, and S3 storage systems. As a Python library, OpenSTEF requires custom data fetchers and APIs to retrieve input data from external sources. Integration typically involves building data pipelines that fetch weather data, energy measurements, and other relevant inputs, then format them for OpenSTEF's forecasting algorithms.


.. code-block:: python

   # S3 Integration
   import boto3
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline

   # Configure S3 client
   s3_client = boto3.client('s3',
                           aws_access_key_id='your_access_key',
                           aws_secret_access_key='your_secret_key',
                           region_name='eu-west-1')

   # Load training data from S3
   bucket_name = 'energy-forecasting-data'
   data_key = 'historical/load_data_2023.parquet'
   s3_client.download_file(bucket_name, data_key, 'local_data.parquet')

   # Train model and upload results
   pj = PredictionJob(id=123, model='xgb', horizon_minutes=15)
   trained_model = train_model_pipeline(pj, input_data='local_data.parquet')

   # Upload trained model to S3
   model_key = f'models/model_{pj.id}_{pj.horizon_minutes}min.pkl'
   s3_client.upload_file('trained_model.pkl', bucket_name, model_key)

   # InfluxDB Integration
   from influxdb_client import InfluxDBClient, Point
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Configure InfluxDB client
   influx_client = InfluxDBClient(
       url="http://localhost:8086",
       token="your_influx_token",
       org="energy_forecasting"
   )

   # Query historical data for forecasting
   query = '''
   from(bucket: "energy_data")
     |> range(start: -7d)
     |> filter(fn: (r) => r["_measurement"] == "load")
     |> filter(fn: (r) => r["location"] == "substation_001")
   '''

   query_api = influx_client.query_api()
   historical_data = query_api.query_data_frame(query)

   # Create forecast
   forecast = create_forecast_pipeline(pj, input_data=historical_data)

   # Write forecast back to InfluxDB
   write_api = influx_client.write_api()
   for idx, row in forecast.iterrows():
       point = Point("forecast") \
           .tag("location", "substation_001") \
           .tag("horizon", f"{pj.horizon_minutes}min") \
           .field("predicted_load", row['forecast']) \
           .field("confidence_interval_lower", row['quantile_0.1']) \
           .field("confidence_interval_upper", row['quantile_0.9']) \
           .time(row['datetime'])
       write_api.write(bucket="forecasts", record=point)

   # Database Integration with OpenSTEF-dbc
   from openstef_dbc.database import DataBase
   from openstef.pipeline.optimize_hyperparameters import optimize_hyperparameters_pipeline

   # Initialize database connection
   db = DataBase(
       host="localhost",
       port=5432,
       database="energy_forecasting",
       username="openstef_user",
       password="secure_password"
   )

   # Retrieve prediction job configuration
   pj_config = db.get_prediction_job(job_id=456)
   pj = PredictionJob(**pj_config)

   # Get training data from database
   training_data = db.get_model_input(
       pid=pj.id,
       start_date="2023-01-01",
       end_date="2023-12-31"
   )

   # Optimize hyperparameters and train
   optimized_model = optimize_hyperparameters_pipeline(pj, training_data)

   # Store forecast results
   forecast_data = create_forecast_pipeline(pj, input_data=training_data)
   db.write_forecast(
       forecast=forecast_data,
       job_id=pj.id,
       forecast_type="demand"
   )


Custom Components
-----------------


OpenSTEF provides several extension points for custom implementations. The TargetProvider abstract interface allows custom data loading strategies by implementing get_targets(), get_measurements_for_target(), and get_predictors_for_target() methods. Custom target providers can extend SimpleTargetProvider for file-based loading or implement the full TargetProvider interface for advanced data sources.

The feature engineering system supports custom transformations through the feature_engineering module. Custom feature applicators can be integrated into the data preparation pipeline by extending existing feature classes or implementing new feature transformation logic. The modular design allows seamless integration of domain-specific features while maintaining compatibility with OpenSTEF's forecasting workflows.


.. code-block:: python

   from pathlib import Path
   from typing import List
   import pandas as pd
   from openstef_beam.benchmarking.target_provider import TargetProvider, TargetProviderConfig
   from openstef_beam.benchmarking.metrics import MetricProvider
   from openstef_beam.benchmarking.datasets import VersionedTimeSeriesDataset
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   class CustomTargetProviderConfig(TargetProviderConfig):
       data_path: Path
       target_pattern: str = "target_{id}.parquet"
       measurements_pattern: str = "measurements_{id}.parquet"

   class CustomTargetProvider(TargetProvider):
       def __init__(self, config: CustomTargetProviderConfig):
           self.config = config

       def get_targets(self, filter_args=None) -> List[str]:
           target_files = list(self.config.data_path.glob("target_*.parquet"))
           targets = [f.stem.replace("target_", "") for f in target_files]
           return targets if not filter_args else [t for t in targets if t in filter_args]

       def get_measurements_for_target(self, target: str) -> VersionedTimeSeriesDataset:
           file_path = self.config.data_path / self.config.measurements_pattern.format(id=target)
           data = pd.read_parquet(file_path)
           return VersionedTimeSeriesDataset(data=data, version="1.0")

       def get_predictors_for_target(self, target: str) -> VersionedTimeSeriesDataset:
           file_path = self.config.data_path / self.config.target_pattern.format(id=target)
           data = pd.read_parquet(file_path)
           return VersionedTimeSeriesDataset(data=data, version="1.0")

       def get_metrics_for_target(self, target: str) -> List[MetricProvider]:
           return [MetricProvider(name="mae"), MetricProvider(name="rmse")]

   class CustomWorkflowComponent:
       def __init__(self, prediction_job: PredictionJobDataClass):
           self.prediction_job = prediction_job

       def prepare_features(self, input_data: pd.DataFrame) -> pd.DataFrame:
           # Apply standard OpenSTEF feature engineering
           features_data = apply_features(
               df=input_data,
               pj=self.prediction_job,
               horizon_minutes=self.prediction_job.horizon_minutes
           )

           # Add custom domain-specific features
           features_data['custom_ratio'] = features_data['load'] / features_data['temperature']
           features_data['peak_indicator'] = (features_data.index.hour >= 17) & (features_data.index.hour <= 20)

           return features_data

       def validate_data(self, data: pd.DataFrame) -> bool:
           required_columns = ['load', 'temperature', 'windspeed']
           return all(col in data.columns for col in required_columns)


Migration from OpenSTEF v3
--------------------------


- External dependencies like MLFlow, openstef-dbc, and xgboost/gblinear are now decoupled - update your integration code accordingly

- Data preprocessing logic has been centralized - review custom preprocessing implementations for compatibility

- Configuration mechanisms have replaced hard-coded assumptions - migrate configuration files to new format

- Input data constraints have been relaxed - verify your data formats still work with the more flexible structure

- Module interfaces have changed for better composability - update import statements and component initialization

- Type safety has been implemented throughout - add type annotations to custom components

- Holiday calendars and domain-specific logic are now configurable - replace hardcoded Dutch/Alliander assumptions

- Performance optimizations may affect callback timing - test custom performance monitoring code


.. code-block:: python

   **OpenSTEF v3.x (Before):**

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.validation.validation import calc_forecast_quality

   # Hard-coded configuration
   model = XGBQuantileOpenstfRegressor()
   model.fit(train_data)

   # Tightly coupled preprocessing
   processed_data = apply_features(raw_data, pj=pj_dict)

   # MLFlow dependency required
   quality_metrics = calc_forecast_quality(predictions, actuals)

   **OpenSTEF v4.x (After):**

   from openstef.model import QuantileRegressor
   from openstef.preprocessing import FeatureEngineer
   from openstef.validation import ForecastValidator
   from openstef.config import ModelConfig

   # Configurable and modular design
   config = ModelConfig(model_type="xgboost", quantiles=[0.1, 0.5, 0.9])
   model = QuantileRegressor(config=config)
   model.fit(train_data)

   # Decoupled preprocessing pipeline
   feature_engineer = FeatureEngineer()
   processed_data = feature_engineer.transform(raw_data)

   # Optional MLFlow integration
   validator = ForecastValidator(use_mlflow=False)
   quality_metrics = validator.evaluate(predictions, actuals)


Configuration Management
------------------------


OpenSTEF library uses environment variables with the `openstef_` prefix for configuration management. Settings can be loaded from `.env` files or set directly in your environment. The library supports nested configuration structures and automatic type parsing for different data types including enums and boolean values.

For production deployments, configure environment-specific settings through your deployment system. Development environments can use local `.env` files while production systems should use secure environment variable injection. The configuration system validates settings on startup and provides clear error messages for missing or invalid values.


.. code-block:: yaml

   # Development environment configuration
   from openstef.settings import Settings

   # Basic development settings
   settings = Settings(
       database_uri="postgresql://user:pass@localhost:5432/openstef_dev",
       log_level="DEBUG",
       post_teams_messages=False
   )

   # Production environment configuration
   import os
   from openstef.settings import Settings

   # Production settings with environment variables
   settings = Settings(
       database_uri=os.getenv("OPENSTEF_DATABASE_URI"),
       log_level="INFO",
       post_teams_messages=True,
       model_storage_path="/opt/openstef/models",
       cache_enabled=True
   )

   # Docker environment configuration
   # .env file for container deployment
   OPENSTEF_DATABASE_URI=postgresql://openstef:password@db:5432/openstef_prod
   OPENSTEF_LOG_LEVEL=INFO
   OPENSTEF_POST_TEAMS_MESSAGES=true
   OPENSTEF_MODEL_STORAGE_PATH=/app/models
   OPENSTEF_CACHE_ENABLED=true

   # Kubernetes ConfigMap example
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: openstef-config
   data:
     OPENSTEF_DATABASE_URI: "postgresql://openstef:password@postgres-service:5432/openstef"
     OPENSTEF_LOG_LEVEL: "INFO"
     OPENSTEF_POST_TEAMS_MESSAGES: "true"


