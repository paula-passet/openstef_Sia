How-to Guides
=============


Setting Up Production Deployments
---------------------------------


OpenSTEF is a Python library that requires additional components for production deployment. You must build your own data fetcher, data API, and forecaster components around the core OpenSTEF library. The library integrates with orchestration tools like Kubernetes CronJobs or Dagster for scheduling training and prediction tasks. Consider implementing separate services for data ingestion, model training, and forecast generation to ensure scalable production operations.


.. code-block:: python

   #!/bin/bash
   # crontab entry: 0 */6 * * * /path/to/forecast_job.sh

   import os
   import sys
   from openstef.tasks.create_forecast import main as create_forecast
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from openstef.database.connector import DatabaseConnector

   # Configure database connection
   config = {
       'database': {
           'host': 'localhost',
           'port': 5432,
           'database': 'openstef',
           'username': 'forecast_user',
           'password': os.environ.get('DB_PASSWORD')
       }
   }

   # Initialize database connector
   database = DatabaseConnector(config['database'])

   # Run forecasting task
   try:
       create_forecast(config=config, database=database)
       print("Forecast completed successfully")
   except Exception as e:
       print(f"Forecast failed: {e}")
       sys.exit(1)


Data Integration Patterns
-------------------------


OpenSTEF library integrates with various data sources and storage systems through flexible patterns. Input data retrieval typically involves database connectors, APIs, or direct file access for weather data, load measurements, and grid information. The library supports both batch and streaming data ingestion workflows.

Forecast results can be stored in multiple formats and systems including databases, cloud storage like S3, time-series databases such as InfluxDB, or flat files. Storage patterns accommodate both real-time prediction outputs and historical backtest results with configurable retention policies.

Integration patterns separate data access logic from forecasting logic, enabling the library to work with existing infrastructure. Custom database connectors like OpenSTEF-dbc provide organization-specific data access while maintaining standardized interfaces for the core forecasting functionality.


.. code-block:: python

   import boto3
   import pandas as pd
   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # S3 data retrieval
   s3_client = boto3.client('s3')
   response = s3_client.get_object(Bucket='energy-data', Key='load_data.csv')
   input_data = pd.read_csv(response['Body'])
   input_data['datetime'] = pd.to_datetime(input_data['datetime'])
   input_data.set_index('datetime', inplace=True)

   # Train model with retrieved data
   model = train_model_pipeline(
       pj={'id': 307, 'name': 'wind_farm_1', 'type': 'wind'},
       input_data=input_data,
       model_type=ARIMAOpenstfRegressor
   )

   # Generate forecast
   forecast = create_forecast_pipeline(
       pj={'id': 307, 'name': 'wind_farm_1'},
       model=model,
       input_data=input_data
   )

   # Store forecast in InfluxDB
   client = InfluxDBClient(url="http://localhost:8086", token="your-token", org="energy-org")
   write_api = client.write_api(write_options=SYNCHRONOUS)

   for index, row in forecast.iterrows():
       point = Point("energy_forecast") \
           .tag("project_id", "307") \
           .tag("project_name", "wind_farm_1") \
           .field("forecast", row['forecast']) \
           .field("quantile_P10", row.get('quantile_P10', 0)) \
           .field("quantile_P90", row.get('quantile_P90', 0)) \
           .time(index)
       write_api.write(bucket="forecasts", record=point)

   client.close()


Advanced Orchestration with Dagster
-----------------------------------


Dagster provides robust orchestration capabilities for OpenSTEF library pipelines, enabling dependency management, data lineage tracking, and failure recovery across complex forecasting workflows. The integration allows seamless scheduling of train_model, create_forecast, and optimize_hyperparameters pipelines while maintaining data provenance and monitoring execution health across distributed systems.


.. code-block:: python

   from dagster import asset, job, op, Config, DagsterLogManager
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd
   from datetime import datetime, timedelta

   class ForecastConfig(Config):
       prediction_job_id: int
       forecast_horizon_hours: int = 48
       model_type: str = "xgb"

   @op
   def load_prediction_job(context: DagsterLogManager, config: ForecastConfig) -> PredictionJob:
       """Load prediction job configuration"""
       return PredictionJob(
           id=config.prediction_job_id,
           model="xgb",
           resolution_minutes=15,
           horizon_minutes=config.forecast_horizon_hours * 60,
           feature_names=["load", "weather_temp", "weather_radiation"]
       )

   @op
   def extract_training_data(context: DagsterLogManager, job: PredictionJob) -> pd.DataFrame:
       """Extract historical data for model training"""
       end_date = datetime.now()
       start_date = end_date - timedelta(days=365)

       # Simulate data extraction from your data source
       dates = pd.date_range(start_date, end_date, freq='15min')
       data = pd.DataFrame({
           'datetime': dates,
           'load': [100 + i % 50 for i in range(len(dates))],
           'weather_temp': [15 + (i % 20) for i in range(len(dates))],
           'weather_radiation': [500 + (i % 300) for i in range(len(dates))]
       })
       return data

   @op
   def train_forecast_model(context: DagsterLogManager, job: PredictionJob, data: pd.DataFrame) -> dict:
       """Train forecasting model using OpenSTEF"""
       model_specs = train_model_pipeline(
           pj=job,
           input_data=data,
           datetime_start=data['datetime'].min(),
           datetime_end=data['datetime'].max()
       )
       context.log.info(f"Model trained for job {job.id}")
       return model_specs

   @op
   def generate_forecast(context: DagsterLogManager, job: PredictionJob, model_specs: dict) -> pd.DataFrame:
       """Generate forecast using trained model"""
       forecast_data = create_forecast_pipeline(
           pj=job,
           model_specs=model_specs,
           datetime_start=datetime.now(),
           datetime_end=datetime.now() + timedelta(hours=48)
       )
       context.log.info(f"Forecast generated for {len(forecast_data)} periods")
       return forecast_data

   @op
   def validate_forecast(context: DagsterLogManager, forecast: pd.DataFrame) -> pd.DataFrame:
       """Validate forecast results"""
       if forecast.empty:
           raise ValueError("Empty forecast generated")

       if forecast['forecast'].isna().any():
           context.log.warning("Forecast contains NaN values")

       context.log.info(f"Forecast validation complete: {len(forecast)} predictions")
       return forecast

   @job(config=ForecastConfig)
   def openstef_forecast_pipeline():
       """Complete automated forecasting workflow using OpenSTEF library"""
       job_config = load_prediction_job()
       training_data = extract_training_data(job_config)
       model = train_forecast_model(job_config, training_data)
       forecast = generate_forecast(job_config, model)
       validate_forecast(forecast)


Migrating from OpenSTEF v3
--------------------------


OpenSTEF 4.0 introduces significant architectural improvements over v3, focusing on modularity and extensibility. The library now features decoupled external dependencies, eliminating tight coupling with MLFlow and openstef-dbc components. API changes include full type safety implementation throughout the codebase and standardized interfaces for custom model integration.

Key enhancements include centralized data preprocessing logic, flexible configuration mechanisms replacing hard-coded assumptions, and improved support for diverse data formats. The modular design enables easier integration of new forecasting models and custom transforms without modifying core library code.

New features expand domain applicability beyond Netherlands-specific use cases, supporting customizable holiday calendars and dynamic energy pricing scenarios. The library now accommodates more flexible input data structures and provides better resilience for varying data availability conditions across different deployment environments.


- Update import statements: Replace 'from openstef.model import OpenstfRegressor' with 'from openstef.models import XGBoostQuantileOpenstfRegressor'

- Modify model initialization: Change 'model = OpenstfRegressor()' to 'model = XGBoostQuantileOpenstfRegressor(quantiles=[0.1, 0.5, 0.9])'

- Update data preprocessing calls: Replace 'openstef.preprocessing.apply_features()' with 'openstef.feature_engineering.apply_feature_transformations()'

- Refactor configuration handling: Move from hard-coded parameters to 'config = OpenstfConfig.from_dict(config_dict)' pattern

- Update prediction methods: Change 'model.predict(data)' to 'predictions = model.predict(data, return_quantiles=True)'

- Migrate MLFlow integration: Replace direct MLFlow calls with 'openstef.metrics.ModelMetrics.log_to_mlflow()' wrapper

- Update validation pipeline: Replace 'openstef.validation.validate()' with new modular validation components

- Refactor holiday calendar usage: Replace Netherlands-specific logic with 'HolidayCalendar.from_country_code(country)'

- Update data input validation: Adapt to relaxed input constraints using new 'DataValidator.validate_flexible()' methods

- Test migration: Run 'python -m openstef.migration.validate_v3_compatibility' to verify successful migration


Custom Data Source Integration
------------------------------


Custom data sources in OpenSTEF must implement specific interface patterns to integrate with the library's forecasting pipeline. Data connectors should provide standardized methods for fetching time-series data, handling data validation, and managing connection lifecycles. The OpenSTEF-dbc repository demonstrates company-specific database connector implementations that follow these interface requirements.

Implementation requires adherence to OpenSTEF's data preprocessing logic and feature preparation standards. Custom connectors must handle data retrieval, transformation, and error management while maintaining compatibility with the library's single-shot, multi-horizon forecasting methodology. The modular architecture in OpenSTEF 4.0 enables decoupled data source integration without hard-coded dependencies.


.. code-block:: python

   from abc import ABC, abstractmethod
   from typing import Dict, List, Optional, Tuple
   import pandas as pd
   from datetime import datetime

   class CustomDataConnector(ABC):
       """Base class for custom data connectors in OpenSTEF"""

       def __init__(self, connection_config: Dict):
           self.config = connection_config
           self.connection = None

       @abstractmethod
       def connect(self) -> None:
           """Establish connection to data source"""
           pass

       @abstractmethod
       def get_load_data(self, pid: int, start: datetime, end: datetime) -> pd.DataFrame:
           """Retrieve load data for prediction job"""
           pass

       @abstractmethod
       def get_weather_data(self, location: str, start: datetime, end: datetime) -> pd.DataFrame:
           """Retrieve weather forecast data"""
           pass

   class ProprietaryDBConnector(CustomDataConnector):
       """Custom connector for proprietary database system"""

       def connect(self) -> None:
           import proprietary_db_driver
           self.connection = proprietary_db_driver.connect(
               host=self.config['host'],
               database=self.config['database'],
               username=self.config['username'],
               password=self.config['password']
           )

       def get_load_data(self, pid: int, start: datetime, end: datetime) -> pd.DataFrame:
           query = """
           SELECT timestamp, load_mw
           FROM energy_loads
           WHERE prediction_job_id = %s
           AND timestamp BETWEEN %s AND %s
           ORDER BY timestamp
           """

           result = self.connection.execute(query, (pid, start, end))
           df = pd.DataFrame(result.fetchall(), columns=['datetime', 'load'])
           df['datetime'] = pd.to_datetime(df['datetime'])
           df.set_index('datetime', inplace=True)
           return df

       def get_weather_data(self, location: str, start: datetime, end: datetime) -> pd.DataFrame:
           query = """
           SELECT timestamp, temperature, wind_speed, radiation
           FROM weather_forecasts
           WHERE location_code = %s
           AND timestamp BETWEEN %s AND %s
           ORDER BY timestamp
           """

           result = self.connection.execute(query, (location, start, end))
           df = pd.DataFrame(result.fetchall(),
                            columns=['datetime', 'temp', 'windspeed_ms', 'radiation'])
           df['datetime'] = pd.to_datetime(df['datetime'])
           df.set_index('datetime', inplace=True)
           return df

   # Usage example
   connector_config = {
       'host': 'proprietary-db.company.com',
       'database': 'energy_data',
       'username': 'openstef_user',
       'password': 'secure_password'
   }

   custom_connector = ProprietaryDBConnector(connector_config)
   custom_connector.connect()

   # Integrate with OpenSTEF workflow
   from openstef.pipeline.train_model import train_model_pipeline

   load_data = custom_connector.get_load_data(
       pid=123,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 1, 31)
   )

   weather_data = custom_connector.get_weather_data(
       location='NL_GRID_001',
       start=datetime(2024, 1, 1),
       end=datetime(2024, 1, 31)
   )

   # Combine data for OpenSTEF training
   input_data = load_data.join(weather_data, how='inner')


