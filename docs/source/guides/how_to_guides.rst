How-to Guides
=============


Overview
--------


These guides provide practical solutions for implementing the OpenSTEF library in production environments. They focus on specific integration tasks, deployment patterns, and configuration scenarios that teams encounter when building forecasting systems with OpenSTEF as their core machine learning component.


Deployment Setup
----------------


OpenSTEF library deployment requires careful orchestration of multiple components including data fetchers, APIs, and forecasting schedulers. The library is fully containerized and platform-agnostic, enabling deployment on any container orchestration system like Kubernetes. Resource management should account for machine learning workloads during training phases and ensure sufficient compute resources for real-time forecasting operations.

Scheduling considerations include coordinating data ingestion pipelines, model training cycles, and forecast generation intervals. The library's resilient architecture supports fallback strategies to ensure continuous forecast availability. Deploy multiple instances across availability zones to maintain service reliability, especially critical for energy sector applications where forecast interruptions can impact grid operations.


.. code-block:: python

   #!/bin/bash
   # Cron job deployment script for OpenSTEF forecasting
   # Add to crontab: 0 */6 * * * /path/to/openstef_forecast.sh

   import os
   from datetime import datetime
   from openstef.tasks import create_forecast_task
   from openstef.data_classes.prediction_job import PredictionJob

   # Basic cron job implementation
   def run_forecast():
       job = PredictionJob(
           id=123,
           name="solar_forecast",
           model="xgb",
           horizon_minutes=2880
       )

       task = create_forecast_task(job)
       forecast = task.run()
       return forecast

   if __name__ == "__main__":
       run_forecast()


   # Dagster integration pattern
   from dagster import op, job, schedule, DefaultScheduleStatus
   from openstef.tasks import create_train_model_task, create_forecast_task
   from openstef.data_classes.prediction_job import PredictionJob

   @op
   def train_model_op():
       job = PredictionJob(
           id=456,
           name="wind_model",
           model="lgb",
           train_horizons_minutes=[15, 60, 1440]
       )

       task = create_train_model_task(job)
       return task.run()

   @op
   def create_forecast_op():
       job = PredictionJob(
           id=456,
           name="wind_model",
           model="lgb",
           horizon_minutes=2880
       )

       task = create_forecast_task(job)
       return task.run()

   @job
   def openstef_pipeline():
       forecast = create_forecast_op()
       return forecast

   @schedule(
       job=openstef_pipeline,
       cron_schedule="0 */3 * * *",
       default_status=DefaultScheduleStatus.RUNNING
   )
   def openstef_schedule():
       return {}


Data Integration
----------------


OpenSTEF library integrates with various storage systems through custom data connectors and APIs. For cloud storage like S3, implement data fetchers that retrieve input data and write to your database layer. Time-series databases like InfluxDB work well for storing forecast results and historical data. For big data platforms like Databricks, create data APIs that provide seamless access to OpenSTEF's training and prediction pipelines. The library's modular architecture allows you to build custom connectors for any storage system by implementing the required data interface methods.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Custom data retrieval implementation
   class CustomDataConnector:
       def __init__(self, api_endpoint, database_config):
           self.api_endpoint = api_endpoint
           self.db_config = database_config

       def get_load_data(self, pid, start_date, end_date):
           # Fetch historical load data from your data source
           query = f"SELECT datetime, load FROM energy_data WHERE pid={pid} AND datetime BETWEEN '{start_date}' AND '{end_date}'"
           return pd.read_sql(query, self.connection)

       def get_weather_data(self, location, start_date, end_date):
           # Retrieve weather forecast data
           params = {
               'location': location,
               'start': start_date,
               'end': end_date,
               'variables': ['temperature', 'wind_speed', 'radiation']
           }
           response = requests.get(f"{self.api_endpoint}/weather", params=params)
           return pd.DataFrame(response.json())

   # Custom forecast posting implementation
   class ForecastPublisher:
       def __init__(self, output_database, api_client):
           self.db = output_database
           self.api = api_client

       def post_forecast(self, forecast_data, prediction_job):
           # Store forecast in database
           forecast_data.to_sql('forecasts', self.db, if_exists='append')

           # Send to external API
           payload = {
               'pid': prediction_job.id,
               'forecast': forecast_data.to_dict('records'),
               'model_type': prediction_job.model,
               'created_at': pd.Timestamp.now().isoformat()
           }
           self.api.post('/forecasts', json=payload)

   # Integration example
   connector = CustomDataConnector('https://api.weather.com', db_config)
   publisher = ForecastPublisher(database_conn, api_client)

   # Create prediction job
   job = PredictionJob(
       id=123,
       model='xgb',
       horizon_minutes=2880,
       train_components=['load', 'weather']
   )

   # Train model with custom data
   input_data = connector.get_load_data(job.id, '2023-01-01', '2023-12-31')
   weather_data = connector.get_weather_data('Amsterdam', '2023-01-01', '2024-01-31')
   model = train_model_pipeline(job, input_data, weather_data)

   # Generate and publish forecast
   forecast = create_forecast_pipeline(job, model, weather_data)
   publisher.post_forecast(forecast, job)


Migration from OpenSTEF v3
--------------------------


OpenSTEF v4 introduces significant architectural changes from v3, prioritizing modularity and type safety. Key breaking changes include decoupled external dependencies like MLFlow and openstef-dbc, centralized data preprocessing logic, and flexible configuration mechanisms replacing hard-coded assumptions. New features encompass broader domain applicability beyond Netherlands-specific use cases, support for diverse data formats, and improved extensibility through clear interfaces for custom models and transforms.


- Update import statements from openstef v3 to v4 module structure

- Replace MLFlow dependencies with new modular tracking system

- Migrate hard-coded configuration to flexible config files

- Update data preprocessing calls to use centralized preprocessing logic

- Replace xgboost/gblinear model calls with new modular model interface

- Update validation logic to use decoupled validation components

- Migrate custom holiday calendars to new configurable calendar system

- Replace rigid input data formats with flexible data structure handlers

- Update pipeline callbacks to use new callback mechanism

- Test migrated code with new type safety requirements


Advanced Configuration
----------------------


OpenSTEF library offers extensive configuration options for performance optimization through its modular architecture. Advanced users can customize feature engineering pipelines, model specifications, and prediction job parameters to optimize memory usage and computational efficiency. The library supports custom objective functions, metamodels, and confidence interval methods for specialized forecasting requirements.

Performance tuning involves configuring data preparation workflows, selecting appropriate lag and rolling features, and optimizing model hyperparameters. Users can implement custom missing value handlers, feature clippers, and grouped regressors to handle specific data characteristics. The single-shot, multi-horizon forecasting methodology allows efficient batch processing for large-scale deployments.


.. note::

   OpenSTEF is a Python library requiring additional components for production deployment. Common pitfalls include insufficient data validation, missing confidence interval configuration, and inadequate logging setup. Ensure proper database connections, weather data fetching schedules, and model retraining intervals before deployment.


