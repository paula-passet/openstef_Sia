How-to Guides
================

This page provides task-specific operational guides for deploying and integrating OpenSTEF in production environments. Each guide focuses on practical implementation patterns and real-world scenarios.

.. note::
   OpenSTEF is a Python library that requires integration into your own application infrastructure. These guides show common deployment and integration patterns, not turnkey solutions.

Simple Deployment
=================

Setting up Scheduled Forecasting
---------------------------------

The most basic deployment pattern involves running forecasts on a regular schedule. Here's how to set up automated forecasting:

**Using Cron Jobs**

.. code-block:: python

   # forecast_job.py
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   def run_daily_forecast():
       # Load your data (implement based on your data source)
       input_data = load_forecast_data()
       
       # Configure prediction job
       pj = PredictionJob(
           id=1,
           model="xgb",
           horizon_minutes=2880,  # 48 hours
           resolution_minutes=15
       )
       
       # Train model
       model = train_model_pipeline(pj, input_data)
       
       # Create forecast
       forecast = create_forecast_pipeline(pj, input_data, model)
       
       # Save results (implement based on your storage)
       save_forecast_results(forecast)

   if __name__ == "__main__":
       run_daily_forecast()

Add to crontab for daily execution at 6 AM:

.. code-block:: bash

   0 6 * * * /usr/bin/python3 /path/to/forecast_job.py

**Using Dagster for Orchestration**

For more complex workflows, integrate OpenSTEF with Dagster:

.. code-block:: python

   from dagster import op, job, schedule
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   @op
   def load_data():
       return load_forecast_data()
   
   @op
   def train_forecast_model(input_data):
       pj = create_prediction_job()
       return train_model_pipeline(pj, input_data)
   
   @op
   def generate_forecast(input_data, model):
       pj = create_prediction_job()
       return create_forecast_pipeline(pj, input_data, model)
   
   @op
   def store_results(forecast):
       save_forecast_results(forecast)
   
   @job
   def daily_forecast_job():
       data = load_data()
       model = train_forecast_model(data)
       forecast = generate_forecast(data, model)
       store_results(forecast)
   
   @schedule(job=daily_forecast_job, cron_schedule="0 6 * * *")
   def daily_forecast_schedule():
       return {}

**Minimal Production Setup**

Key considerations for production deployment:

- **Error handling**: Wrap forecasting pipeline in try-catch blocks with proper logging
- **Monitoring**: Track forecast generation success/failure and model performance
- **Model persistence**: Store trained models to avoid retraining on every run
- **Data validation**: Validate input data quality before training/forecasting
- **Fallback strategies**: Implement backup forecasting methods when primary models fail

Data Integration
================

Connecting to S3
----------------

Amazon S3 is a common data source for energy forecasting workflows:

**Reading Input Data from S3**

.. code-block:: python

   import boto3
   import pandas as pd
   from io import StringIO
   
   def load_data_from_s3(bucket_name, object_key):
       s3_client = boto3.client('s3')
       
       # Download CSV data
       response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
       csv_content = response['Body'].read().decode('utf-8')
       
       # Convert to DataFrame
       df = pd.read_csv(StringIO(csv_content))
       df['datetime'] = pd.to_datetime(df['datetime'])
       df.set_index('datetime', inplace=True)
       
       return df
   
   # Usage in forecasting pipeline
   input_data = load_data_from_s3('energy-data-bucket', 'hourly_load_2024.csv')

**Writing Forecasts to S3**

.. code-block:: python

   def save_forecast_to_s3(forecast_df, bucket_name, object_key):
       s3_client = boto3.client('s3')
       
       # Convert DataFrame to CSV
       csv_buffer = StringIO()
       forecast_df.to_csv(csv_buffer, index=True)
       
       # Upload to S3
       s3_client.put_object(
           Bucket=bucket_name,
           Key=object_key,
           Body=csv_buffer.getvalue(),
           ContentType='text/csv'
       )
   
   # Usage after forecast generation
   save_forecast_to_s3(forecast_results, 'forecast-output-bucket', 
                       f'forecasts/forecast_{datetime.now().strftime("%Y%m%d")}.csv')

Databricks Integration
----------------------

For big data environments using Databricks:

.. code-block:: python

   # In Databricks notebook
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJob
   
   # Read data from Delta Lake
   input_data = spark.table("energy_database.hourly_measurements").toPandas()
   input_data['datetime'] = pd.to_datetime(input_data['datetime'])
   input_data.set_index('datetime', inplace=True)
   
   # Configure and run OpenSTEF pipeline
   pj = PredictionJob(
       id=1,
       model="xgb",
       horizon_minutes=1440,
       resolution_minutes=60
   )
   
   model = train_model_pipeline(pj, input_data)
   forecast = create_forecast_pipeline(pj, input_data, model)
   
   # Write results back to Delta Lake
   forecast_spark_df = spark.createDataFrame(forecast.reset_index())
   forecast_spark_df.write.mode("overwrite").saveAsTable("energy_database.forecasts")

InfluxDB Integration
--------------------

For time series databases like InfluxDB:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   
   def load_data_from_influxdb(url, token, org, bucket, measurement):
       client = InfluxDBClient(url=url, token=token, org=org)
       query_api = client.query_api()
       
       query = f'''
           from(bucket: "{bucket}")
               |> range(start: -30d)
               |> filter(fn: (r) => r["_measurement"] == "{measurement}")
               |> aggregateWindow(every: 15m, fn: mean, createEmpty: false)
               |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
       '''
       
       result = query_api.query_data_frame(query)
       result['_time'] = pd.to_datetime(result['_time'])
       result.set_index('_time', inplace=True)
       
       return result
   
   def write_forecast_to_influxdb(forecast_df, url, token, org, bucket):
       client = InfluxDBClient(url=url, token=token, org=org)
       write_api = client.write_api()
       
       # Convert forecast to InfluxDB format
       for timestamp, row in forecast_df.iterrows():
           point = Point("forecast") \
               .time(timestamp) \
               .field("p10", row['quantile_0.1']) \
               .field("p50", row['quantile_0.5']) \
               .field("p90", row['quantile_0.9'])
           
           write_api.write(bucket=bucket, org=org, record=point)

General Adapter Patterns
-------------------------

For custom data sources, implement adapter functions following these patterns:

.. code-block:: python

   def create_data_adapter(source_config):
       """Generic adapter factory for different data sources"""
       
       def load_data():
           # Implement source-specific data loading
           raw_data = fetch_from_source(source_config)
           
           # Standardize to OpenSTEF expected format
           standardized_data = standardize_columns(raw_data)
           standardized_data = validate_data_quality(standardized_data)
           
           return standardized_data
       
       def save_results(forecast_data):
           # Implement source-specific result storage
           formatted_data = format_for_destination(forecast_data)
           store_to_destination(formatted_data, source_config)
       
       return load_data, save_results

Migrating from OpenSTEF V3
===========================

Key Breaking Changes in V4
---------------------------

OpenSTEF V4 introduces several architectural changes that require code updates:

**Module Restructuring**

.. code-block:: python

   # V3 imports (deprecated)
   from openstef.model.regressors import OpenstfRegressor
   from openstef.tasks.create_forecast import create_forecast
   
   # V4 imports (current)
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.create_forecast import create_forecast_pipeline

**Configuration Changes**

PredictionJob configuration has been streamlined:

.. code-block:: python

   # V3 configuration
   pj = PredictionJob(
       id=1,
       model_type="xgb",
       forecast_type="demand",
       train_horizons_minutes=[15, 30, 45],
       # ... many other parameters
   )
   
   # V4 configuration (simplified)
   pj = PredictionJob(
       id=1,
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15
   )

Migration Steps
---------------

1. **Update imports**: Replace task-based imports with pipeline-based imports
2. **Simplify PredictionJob**: Remove deprecated configuration parameters
3. **Update function calls**: Replace task functions with pipeline functions
4. **Test data compatibility**: Ensure your data format matches V4 expectations

.. warning::
   V4 removes support for some V3 configuration options. Review your PredictionJob configurations carefully and consult the API reference for current parameter names.

Common Migration Issues
-----------------------

Based on community feedback, these are the most frequent migration challenges:

**Model Loading**

V3 model files may not be compatible with V4. Plan to retrain models during migration:

.. code-block:: python

   # Don't rely on loading V3 model files
   # Instead, retrain with V4 pipeline
   model = train_model_pipeline(pj, input_data)

**Data Schema Changes**

Some column names and data types have been standardized. Verify your data preprocessing:

.. code-block:: python

   # Ensure datetime column is properly formatted
   df['datetime'] = pd.to_datetime(df['datetime'])
   df.set_index('datetime', inplace=True)
   
   # Check for required columns
   required_columns = ['load', 'T-1h', 'humidity', 'radiation']  # example
   missing_columns = set(required_columns) - set(df.columns)
   if missing_columns:
       raise ValueError(f"Missing required columns: {missing_columns}")

For specific migration questions, consult the `GitHub Discussions <https://github.com/OpenSTEF/openstef/discussions>`_ or refer to the detailed API reference documentation.