How-to Guides
=============


Overview
--------


These guides provide practical implementation instructions for integrating the OpenSTEF library into production environments. Each guide addresses specific technical tasks such as configuring data connectors, setting up forecasting pipelines, and deploying containerized solutions. The focus is on real-world integration scenarios where OpenSTEF functions as a core component within larger energy forecasting systems.


- Getting started with OpenSTEF library integration

- Setting up data connectors and preprocessing pipelines

- Training and validating forecasting models

- Generating single-shot multi-horizon predictions

- Implementing probabilistic forecasting with confidence intervals

- Deploying OpenSTEF in containerized environments

- Creating custom fallback strategies for resilient forecasting

- Splitting forecasts into renewable energy components


Setting Up Production Deployments
---------------------------------


When deploying OpenSTEF in production environments, consider that it's a Python library requiring additional components for full application functionality. Deploy containerized instances with data fetchers, APIs, and orchestration services. Implement fallback strategies for forecast resilience, as availability is critical in energy sector applications. Configure probabilistic forecasting capabilities and component splitting features based on your grid balancing requirements.


.. code-block:: python

   # Run forecasting pipeline every hour
   0 * * * * /usr/bin/python3 -c "
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd

   # Load prediction job configuration
   pj = {'id': 307, 'model': 'xgb', 'horizon_minutes': 2880, 'resolution_minutes': 15}

   # Execute forecast pipeline
   forecast = create_forecast_pipeline(pj, datetime_start=pd.Timestamp.now())
   "

   # Train models daily at 2 AM
   0 2 * * * /usr/bin/python3 -c "
   from openstef.pipeline.train_model import train_model_pipeline

   pj = {'id': 307, 'model': 'xgb', 'horizon_minutes': 2880}
   train_model_pipeline(pj)
   "

   # Optimize hyperparameters weekly on Sundays
   0 3 * * 0 /usr/bin/python3 -c "
   from openstef.pipeline.optimize_hyperparameters import optimize_hyperparameters_pipeline

   pj = {'id': 307, 'model': 'xgb', 'horizon_minutes': 2880}
   optimize_hyperparameters_pipeline(pj)
   "


Data Integration Patterns
-------------------------


OpenSTEF library integrates with various data sources through custom data connectors and APIs. Common scenarios include fetching weather data via scheduled jobs, connecting to time-series databases for load data, and implementing REST APIs for real-time data access. The library requires external data fetcher components to retrieve input data and write it to databases. Integration patterns typically involve combining multiple data sources like weather forecasts, historical load data, and grid topology information to prepare features for forecasting models.


.. code-block:: python

   import pandas as pd
   from influxdb_client import InfluxDBClient
   import boto3
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline

   # Connect to InfluxDB for time series data
   client = InfluxDBClient(url="http://localhost:8086", token="your-token", org="your-org")
   query_api = client.query_api()

   # Fetch load data from InfluxDB
   flux_query = '''
   from(bucket: "energy_data")
     |> range(start: -30d)
     |> filter(fn: (r) => r["_measurement"] == "load")
     |> filter(fn: (r) => r["location"] == "substation_1")
   '''
   load_data = query_api.query_data_frame(flux_query)

   # Connect to S3 for weather data
   s3_client = boto3.client('s3',
                           aws_access_key_id='your-key',
                           aws_secret_access_key='your-secret')

   # Download weather data from S3
   weather_obj = s3_client.get_object(Bucket='weather-bucket', Key='forecast_data.csv')
   weather_data = pd.read_csv(weather_obj['Body'])

   # Prepare data for OpenSTEF
   input_data = pd.merge(load_data, weather_data, on='datetime', how='inner')
   input_data.set_index('datetime', inplace=True)

   # Create prediction job and train model
   pj = PredictionJob(
       id=123,
       name="substation_1_forecast",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15
   )

   model = train_model_pipeline(pj, input_data)


Orchestration with Workflow Tools
---------------------------------


Workflow orchestration tools enhance OpenSTEF library deployment by automating complex forecasting pipelines across distributed systems. These tools manage data fetching, model training, and prediction scheduling while handling dependencies between OpenSTEF's modular components. Integration enables reliable production forecasting with monitoring, error handling, and scalable execution of OpenSTEF's train and predict methodologies.


.. code-block:: python

   from dagster import asset, job, op, Config
   from openstef.pipeline import train_model, create_forecast
   import pandas as pd

   class OpenSTEFConfig(Config):
       model_type: str = "xgb"
       horizon_hours: int = 48
       train_data_days: int = 90

   @op
   def fetch_training_data(context) -> pd.DataFrame:
       # Fetch historical load and weather data
       return pd.read_csv("training_data.csv", parse_dates=['datetime'])

   @op
   def train_forecasting_model(context, config: OpenSTEFConfig, data: pd.DataFrame):
       model = train_model(
           data=data,
           model_type=config.model_type,
           horizon=config.horizon_hours
       )
       return model

   @op
   def generate_forecast(context, config: OpenSTEFConfig, model, input_data: pd.DataFrame):
       forecast = create_forecast(
           model=model,
           input_data=input_data,
           horizon=config.horizon_hours
       )
       return forecast

   @job(config=OpenSTEFConfig)
   def openstef_forecasting_pipeline():
       training_data = fetch_training_data()
       model = train_forecasting_model(training_data)
       forecast = generate_forecast(model, training_data)
       return forecast


Migrating from OpenSTEF v3
--------------------------


OpenSTEF 4.0 introduces significant architectural changes from version 3, focusing on modularity, type safety, and broader domain applicability. Key changes include decoupled external dependencies like MLFlow and openstef-dbc, centralized data preprocessing logic, and flexible configuration mechanisms replacing hard-coded assumptions.

The library now supports diverse forecasting use cases beyond Netherlands-specific applications, with customizable holiday calendars and relaxed input data constraints. Migration requires updating code to use the new modular component system and revised APIs for model integration and data handling.


- Update your imports to use the new modular structure: from openstef.model import XGBQuantileOpenstfRegressor instead of legacy imports

- Replace hard-coded configuration with flexible config objects: config = ForecastConfig(horizon_minutes=2880, quantiles=[0.1, 0.5, 0.9]) instead of fixed parameters

- Migrate data preprocessing to centralized functions: preprocessed_data = preprocess_forecast_data(raw_data, config) instead of inline preprocessing

- Update model initialization with new constructor patterns: model = XGBQuantileOpenstfRegressor(quantiles=[0.1, 0.5, 0.9], n_estimators=100)

- Replace MLFlow dependencies with native OpenSTEF model persistence: model.save('model.pkl') and loaded_model = XGBQuantileOpenstfRegressor.load('model.pkl')

- Update validation workflows to use new validation modules: from openstef.validation import validate_forecast_input, validate_model_output

- Migrate custom holiday calendars using new configuration system: config.holiday_calendar = CustomHolidayCalendar(country='NL', custom_holidays=['2024-04-27'])

- Update pipeline callbacks to new interface: pipeline.add_callback('post_prediction', custom_callback_function)

- Replace deprecated utility functions with v4 equivalents - check migration guide for function mapping

- Test your migration with provided compatibility checker: python -m openstef.migration.check_compatibility your_code.py


