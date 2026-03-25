How-to Guides
=============


How-to Guides
=============


These how-to guides provide step-by-step instructions for specific implementation tasks when working with the OpenSTEF library. Each guide focuses on practical scenarios you may encounter when integrating OpenSTEF's forecasting capabilities into your energy forecasting workflows, from data preparation and feature engineering to model training and prediction generation. The guides complement the API reference by showing real-world usage patterns and best practices for leveraging OpenSTEF's machine learning functionality in your applications.


While tutorials are designed to help you learn OpenSTEF concepts through guided examples, how-to guides focus on solving specific problems you encounter when working with the OpenSTEF library. Tutorials take a learning-oriented approach, walking you through complete workflows to build understanding, whereas how-to guides are task-oriented, providing direct solutions to particular challenges like configuring prediction jobs, implementing custom feature engineering, or integrating OpenSTEF into your existing forecasting pipeline. Think of tutorials as classroom lessons and how-to guides as reference recipes for accomplishing specific goals with the library.


.. note::

   OpenSTEF is a Python library, not a standalone application. To use OpenSTEF in production, you need to integrate it into your own system architecture. This typically involves creating additional components such as data fetchers to collect input data, APIs to serve data, and schedulers to run forecasting tasks. The how-to guides in this section focus on using OpenSTEF's library functions within your own implementation.


Deployment
----------


When deploying the OpenSTEF library in production environments, it's important to understand that OpenSTEF is a Python software package that provides machine learning capabilities for energy forecasting, not a standalone application. To create a complete forecasting solution, you'll need to integrate OpenSTEF with additional components that handle data ingestion, API services, and scheduling. The library's modular and containerized design makes it platform-agnostic and suitable for various deployment architectures, from cloud-based Kubernetes clusters to on-premises systems. Key deployment considerations include ensuring data availability through robust data fetchers, implementing proper scheduling mechanisms for training and prediction tasks, and establishing reliable fallback strategies to maintain forecast availability - a critical requirement in energy sector applications.


Simple Cron-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Cron-based deployment is the simplest approach for running OpenSTEF in production environments where you need basic scheduling capabilities without complex orchestration requirements. This method is ideal for small to medium-scale deployments, development environments, or situations where you want to minimize infrastructure complexity. However, cron-based deployment has several limitations: it lacks sophisticated error handling and retry mechanisms, provides limited monitoring and alerting capabilities, offers no built-in dependency management between different forecasting jobs, and has minimal scalability options. Additionally, cron jobs run independently without coordination, making it difficult to manage complex workflows or handle failures gracefully. For production environments requiring high availability, detailed monitoring, or complex job dependencies, consider using more robust orchestration platforms like Kubernetes or Apache Airflow.


.. code-block:: python

   ```python
   #!/usr/bin/env python3
   """
   Simple OpenSTEF forecasting script for cron scheduling.
   This script trains models and generates forecasts for configured prediction jobs.
   """

   import logging
   from datetime import datetime, timedelta
   from openstef.tasks import create_forecast_task, create_train_task
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.database import DataBase

   # Configure logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('/var/log/openstef_cron.log'),
           logging.StreamHandler()
       ]
   )

   def main():
       """Main function to run OpenSTEF tasks."""
       try:
           # Initialize database connection
           db = DataBase()

           # Get active prediction jobs from database
           prediction_jobs = db.get_prediction_jobs(active_only=True)

           current_time = datetime.utcnow()

           for job in prediction_jobs:
               logging.info(f"Processing prediction job: {job.name}")

               # Train model weekly (check if it's Monday and early morning)
               if current_time.weekday() == 0 and current_time.hour < 6:
                   logging.info(f"Training model for job: {job.name}")
                   train_task = create_train_task(job)
                   train_task.run()

               # Generate forecast
               logging.info(f"Creating forecast for job: {job.name}")
               forecast_task = create_forecast_task(job)
               forecast_task.run()

           logging.info("All prediction jobs processed successfully")

       except Exception as e:
           logging.error(f"Error in OpenSTEF cron job: {str(e)}")
           raise

   if __name__ == "__main__":
       main()
   ```


.. code-block:: bash

   #!/bin/bash
   # OpenSTEF forecast update script
   # This script runs OpenSTEF forecasting tasks

   # Set environment variables
   export PYTHONPATH=/path/to/openstef
   export DATABASE_URI="postgresql://user:password@localhost:5432/openstef_db"

   # Activate virtual environment
   source /path/to/openstef-env/bin/activate

   # Run forecasting pipeline
   python -c "
   from openstef.tasks import create_forecast_task
   from openstef.model.prediction_job import PredictionJobDataClass

   # Configure prediction job
   prediction_job = PredictionJobDataClass(
       id=1,
       name='solar_forecast_job',
       model='xgb',
       horizon_minutes=2880,  # 48 hours
       resolution_minutes=15,
       feature_names=['load', 'weather_temp', 'weather_radiation']
   )

   # Create and execute forecast task
   task = create_forecast_task(prediction_job)
   task.run()
   "

   # Cron configuration examples:
   # Run forecasts every 15 minutes:
   # */15 * * * * /path/to/forecast_script.sh >> /var/log/openstef_forecast.log 2>&1

   # Run model training daily at 2 AM:
   # 0 2 * * * /path/to/train_script.sh >> /var/log/openstef_train.log 2>&1

   # Run forecasts every hour during business hours:
   # 0 8-18 * * 1-5 /path/to/forecast_script.sh >> /var/log/openstef_forecast.log 2>&1


- Simple and widely available - cron is installed on most Unix-like systems by default

- No additional infrastructure required - works with basic server setups

- Easy to understand and debug - straightforward scheduling syntax

- Lightweight resource usage - minimal overhead compared to complex orchestration tools

- Good for basic periodic training and forecasting tasks

- Limited error handling and retry mechanisms compared to dedicated workflow tools

- No built-in dependency management between different OpenSTEF tasks

- Difficult to scale across multiple servers without additional coordination

- Basic logging capabilities - may require custom solutions for comprehensive monitoring

- No automatic failover or high availability features

- Manual management required for complex scheduling scenarios


Dagster Integration
^^^^^^^^^^^^^^^^^^^


Dagster provides significant advantages for orchestrating OpenSTEF workflows, particularly when managing complex forecasting pipelines at scale. As a modern data orchestrator, Dagster offers built-in data lineage tracking, which is invaluable when working with OpenSTEF's multi-stage pipelines that involve data validation, feature engineering, and machine learning components. The asset-based approach of Dagster aligns well with OpenSTEF's pipeline architecture, allowing you to define clear dependencies between training models, creating forecasts, and evaluating performance. Dagster's robust scheduling capabilities enable automated execution of OpenSTEF's various pipelines (train_model, create_forecast, optimize_hyperparameters) while providing comprehensive monitoring and alerting when workflows fail. Additionally, Dagster's built-in data quality checks complement OpenSTEF's data validation features, ensuring that prediction jobs receive clean, validated input data before processing begins.


.. code-block:: python

   ```python
   from dagster import asset, Config, AssetExecutionContext
   from openstef.pipeline import train_model, create_forecast
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   import pandas as pd

   class OpenSTEFConfig(Config):
       prediction_job_id: int
       horizon_minutes: int = 2880  # 48 hours
       model_type: str = "xgb"

   @asset
   def training_data(context: AssetExecutionContext, config: OpenSTEFConfig) -> pd.DataFrame:
       """Load and prepare training data for OpenSTEF model."""
       # In practice, this would connect to your data source
       # Here we show the expected data structure
       context.log.info(f"Loading training data for prediction job {config.prediction_job_id}")

       # Your data loading logic here
       # training_data = load_data_from_database(config.prediction_job_id)
       training_data = pd.DataFrame()  # Placeholder

       return training_data

   @asset
   def prediction_job_config(config: OpenSTEFConfig) -> PredictionJobDataClass:
       """Create prediction job configuration for OpenSTEF."""
       return PredictionJobDataClass(
           id=config.prediction_job_id,
           model=config.model_type,
           horizon_minutes=config.horizon_minutes,
           resolution_minutes=15,
           train_components=True,
           feature_names=["load", "weather_temp", "weather_radiation"]
       )

   @asset
   def trained_model(
       context: AssetExecutionContext,
       training_data: pd.DataFrame,
       prediction_job_config: PredictionJobDataClass
   ):
       """Train OpenSTEF model using the training pipeline."""
       context.log.info("Training OpenSTEF model")

       # Use OpenSTEF training pipeline
       model_specs = train_model.train_model_pipeline(
           pj=prediction_job_config,
           input_data=training_data
       )

       context.log.info(f"Model training completed. Model type: {model_specs.model_type_name}")
       return model_specs

   @asset
   def forecast_input_data(context: AssetExecutionContext, config: OpenSTEFConfig) -> pd.DataFrame:
       """Load recent data for forecasting."""
       context.log.info("Loading forecast input data")

       # Your data loading logic for recent data
       # forecast_data = load_recent_data(config.prediction_job_id)
       forecast_data = pd.DataFrame()  # Placeholder

       return forecast_data

   @asset
   def energy_forecast(
       context: AssetExecutionContext,
       trained_model,
       forecast_input_data: pd.DataFrame,
       prediction_job_config: PredictionJobDataClass
   ) -> pd.DataFrame:
       """Generate energy load forecast using OpenSTEF."""
       context.log.info("Generating forecast")

       # Use OpenSTEF forecasting pipeline
       forecast = create_forecast.create_forecast_pipeline(
           pj=prediction_job_config,
           input_data=forecast_input_data,
           model_specs=trained_model
       )

       context.log.info(f"Forecast generated with {len(forecast)} data points")
       return forecast
   ```


.. [DIAGRAM: Dagster pipeline visualization showing OpenSTEF workflow steps]


.. code-block:: python

   ```python
   from dagster import asset, job, schedule, DefaultScheduleStatus
   from openstef.pipeline import train_model, create_forecast
   from openstef.model.prediction_job import PredictionJobDataClass
   import pandas as pd

   # Define prediction job configuration
   prediction_job = PredictionJobDataClass(
       id=123,
       name="solar_forecast_job",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,  # 48 hours
       train_components=True,
       feature_names=["load", "weather", "radiation"]
   )

   @asset
   def training_data():
       """Load and prepare training data for the model"""
       # Your data loading logic here
       return pd.read_csv("training_data.csv")

   @asset
   def trained_model(training_data):
       """Train OpenSTEF model using the pipeline"""
       model_specs = train_model.train_model_pipeline(
           pj=prediction_job,
           input_data=training_data
       )
       return model_specs

   @asset
   def forecast_data():
       """Load recent data for forecasting"""
       # Your forecast data loading logic here
       return pd.read_csv("recent_data.csv")

   @asset(deps=[trained_model])
   def energy_forecast(forecast_data):
       """Generate forecast using OpenSTEF pipeline"""
       forecast = create_forecast.create_forecast_pipeline(
           pj=prediction_job,
           input_data=forecast_data
       )
       return forecast

   @job
   def openstef_forecast_job():
       """Complete OpenSTEF forecasting workflow"""
       energy_forecast()

   # Schedule to run every hour
   @schedule(
       job=openstef_forecast_job,
       cron_schedule="0 * * * *",
       default_status=DefaultScheduleStatus.RUNNING
   )
   def hourly_forecast_schedule():
       return {}

   # Daily training schedule
   @job
   def openstef_training_job():
       """Daily model training workflow"""
       trained_model()

   @schedule(
       job=openstef_training_job,
       cron_schedule="0 2 * * *",  # Run at 2 AM daily
       default_status=DefaultScheduleStatus.RUNNING
   )
   def daily_training_schedule():
       return {}
   ```


Data Integration
----------------


OpenSTEF as a Python library requires integration with various data sources and sinks to function effectively in production environments. The library follows a modular architecture where data integration occurs through well-defined interfaces between tasks, pipelines, and external systems. Tasks handle data fetching from databases and writing results back, while pipelines can work directly with provided data for more flexible integration patterns. Key integration requirements include access to historical energy load data, weather forecasts, and other relevant time series data that feed into the feature engineering process. The library expects data to be available in specific formats and time intervals to support its single-shot, multi-horizon forecasting methodology. When deploying OpenSTEF in production, you'll typically need to implement custom data fetchers to pull information from your existing data infrastructure, configure appropriate data APIs for serving results, and ensure proper data validation flows to maintain forecast quality.


AWS S3 Integration
^^^^^^^^^^^^^^^^^^


OpenSTEF library can integrate with AWS S3 to handle input data storage and forecast output persistence in cloud environments. This integration is particularly valuable when deploying OpenSTEF as part of a larger forecasting application where data needs to be shared across distributed components. Common use cases include storing historical energy consumption data, weather forecasts, and grid topology information in S3 buckets for training models, as well as writing forecast results back to S3 for consumption by downstream applications or visualization tools. To set up S3 integration, you'll need AWS credentials configured (via AWS CLI, environment variables, or IAM roles), the boto3 Python package installed, and appropriate S3 bucket permissions for read/write operations. The integration works seamlessly with OpenSTEF's data loading pipeline, allowing you to replace local file storage with scalable cloud storage while maintaining the same forecasting workflow.


.. code-block:: python

   ```python
   import boto3
   import pandas as pd
   from io import StringIO
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline

   # Initialize S3 client
   s3_client = boto3.client('s3',
                           aws_access_key_id='your_access_key',
                           aws_secret_access_key='your_secret_key',
                           region_name='us-east-1')

   # Load training data from S3
   bucket_name = 'your-openstef-data-bucket'
   training_data_key = 'training_data/load_forecast_data.csv'

   # Download CSV data from S3
   response = s3_client.get_object(Bucket=bucket_name, Key=training_data_key)
   csv_content = response['Body'].read().decode('utf-8')

   # Convert to pandas DataFrame
   training_data = pd.read_csv(StringIO(csv_content))
   training_data['datetime'] = pd.to_datetime(training_data['datetime'])
   training_data.set_index('datetime', inplace=True)

   # Load prediction job configuration
   config_key = 'configs/prediction_job_config.json'
   config_response = s3_client.get_object(Bucket=bucket_name, Key=config_key)
   config_data = json.loads(config_response['Body'].read().decode('utf-8'))

   # Create prediction job from config
   prediction_job = PredictionJob(**config_data)

   # Train model using the loaded data
   trained_model = train_model_pipeline(
       prediction_job=prediction_job,
       input_data=training_data
   )

   print(f"Model trained successfully with {len(training_data)} data points")
   ```


.. code-block:: python

   ```python
   import boto3
   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Initialize S3 client
   s3_client = boto3.client('s3')
   bucket_name = 'your-forecast-bucket'

   # Assume you have forecast data from OpenSTEF pipeline
   # This could be the result from create_forecast_pipeline
   forecast_data = create_forecast_pipeline(
       pj=your_prediction_job,
       input_data=input_data,
       model=trained_model
   )

   # Convert forecast results to CSV format
   forecast_df = pd.DataFrame(forecast_data)
   csv_buffer = forecast_df.to_csv(index=False)

   # Save forecast results to S3
   forecast_key = f'forecasts/{prediction_job_id}/forecast_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
   s3_client.put_object(
       Bucket=bucket_name,
       Key=forecast_key,
       Body=csv_buffer,
       ContentType='text/csv'
   )

   # Optionally save confidence intervals if available
   if 'quantiles' in forecast_data:
       confidence_df = pd.DataFrame(forecast_data['quantiles'])
       confidence_csv = confidence_df.to_csv(index=False)

       confidence_key = f'forecasts/{prediction_job_id}/confidence_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
       s3_client.put_object(
           Bucket=bucket_name,
           Key=confidence_key,
           Body=confidence_csv,
           ContentType='text/csv'
       )

   print(f"Forecast results saved to s3://{bucket_name}/{forecast_key}")
   ```


.. note::

   When integrating OpenSTEF with AWS S3, proper credential management is critical for security. Never hardcode AWS credentials directly in your code or configuration files. Instead, use AWS IAM roles, environment variables, or AWS credential files. Ensure your S3 buckets have appropriate access policies and consider using temporary credentials through AWS STS when possible. For production deployments, implement least-privilege access principles and regularly rotate credentials.


InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^


InfluxDB is particularly well-suited for storing and managing OpenSTEF's time-series data due to its optimized design for temporal datasets with regular sampling intervals. OpenSTEF's TimeSeriesDataset implementation relies on consistent datetime indexing and structured time-based queries, which align perfectly with InfluxDB's time-series database architecture. The database's efficient storage of timestamped data points, combined with its powerful querying capabilities for time-based filtering and aggregation, makes it an ideal backend for OpenSTEF's forecasting workflows. Additionally, InfluxDB's ability to handle high-frequency data ingestion and its built-in retention policies complement OpenSTEF's need to process large volumes of energy sector data while maintaining historical datasets for model training and validation.


.. code-block:: python

   ```python
   from influxdb_client import InfluxDBClient
   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Initialize InfluxDB client
   client = InfluxDBClient(
       url="http://localhost:8086",
       token="your-influxdb-token",
       org="your-organization"
   )

   # Define query parameters
   bucket = "energy_data"
   start_time = datetime.now() - timedelta(days=30)
   end_time = datetime.now()

   # Query historical load and weather data for training
   query = f'''
   from(bucket: "{bucket}")
     |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
     |> filter(fn: (r) => r["_measurement"] == "energy_load" or r["_measurement"] == "weather")
     |> filter(fn: (r) => r["location"] == "substation_001")
     |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
     |> sort(columns: ["_time"])
   '''

   # Execute query and convert to DataFrame
   query_api = client.query_api()
   result = query_api.query_data_frame(query)

   # Prepare data for OpenSTEF
   df = result.set_index('_time')
   df.index = pd.to_datetime(df.index)
   df = df.sort_index()

   # Select relevant features for training
   feature_columns = ['load_mw', 'temperature', 'humidity', 'wind_speed', 'solar_radiation']
   training_data = df[feature_columns].dropna()

   # Create OpenSTEF TimeSeriesDataset
   dataset = TimeSeriesDataset.from_pandas(training_data)

   # Filter dataset for specific time range if needed
   filtered_dataset = dataset.filter_by_range(
       start=start_time,
       end=end_time - timedelta(hours=24)  # Reserve last 24h for validation
   )

   print(f"Retrieved {len(filtered_dataset.to_pandas())} records for training")
   print(f"Features: {filtered_dataset.feature_names}")
   print(f"Time range: {filtered_dataset.index[0]} to {filtered_dataset.index[-1]}")

   client.close()
   ```


.. code-block:: python

   ```python
   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd
   from datetime import datetime
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Initialize InfluxDB client
   client = InfluxDBClient(
       url="http://localhost:8086",
       token="your-token",
       org="your-org"
   )
   write_api = client.write_api(write_option=SYNCHRONOUS)

   # Create forecast using OpenSTEF
   model = ARIMAOpenstfRegressor()
   forecast_data = create_forecast_pipeline(
       pj={"id": 307, "name": "wind_farm_1"},
       model=model,
       horizon_minutes=2880  # 48 hours
   )

   # Convert forecast results to InfluxDB points
   points = []
   for index, row in forecast_data.iterrows():
       point = Point("energy_forecast") \
           .tag("location", "wind_farm_1") \
           .tag("model_type", "ARIMA") \
           .field("forecast_mw", float(row['forecast'])) \
           .field("quantile_10", float(row.get('quantile_10', 0))) \
           .field("quantile_90", float(row.get('quantile_90', 0))) \
           .time(index)
       points.append(point)

   # Write forecast data to InfluxDB
   write_api.write(bucket="energy_forecasts", record=points)

   # Query and verify data was written
   query_api = client.query_api()
   query = '''
   from(bucket: "energy_forecasts")
     |> range(start: -24h)
     |> filter(fn: (r) => r._measurement == "energy_forecast")
     |> filter(fn: (r) => r.location == "wind_farm_1")
   '''

   result = query_api.query(query=query)
   print(f"Successfully wrote {len(points)} forecast points to InfluxDB")

   client.close()
   ```


- Use consistent measurement names that align with OpenSTEF's TimeSeriesDataset structure, such as 'load', 'solar', 'wind' for energy forecasting data

- Design tags to include essential metadata like prediction_job_id, horizon, and location to enable efficient filtering by OpenSTEF's lead time and availability filtering methods

- Store timestamps in UTC with consistent precision (typically 15-minute intervals) to match OpenSTEF's regular sampling interval requirements

- Use separate measurements for forecasts and actuals rather than mixing them in fields, enabling clear distinction between predicted and observed values

- Include version tags when storing forecast data to support OpenSTEF's versioning capabilities for model comparison and backtesting

- Structure field names to match OpenSTEF's feature naming conventions, using descriptive names like 'temperature_2m', 'wind_speed_10m' for weather features

- Implement retention policies that align with your forecasting horizons - keep detailed data for recent periods and aggregated data for historical analysis

- Use batch writes when ingesting large datasets to optimize performance, especially when working with OpenSTEF's bulk data processing workflows

- Design your schema to support range queries efficiently, as OpenSTEF frequently filters data by time ranges using filter_by_range() methods

- Consider using continuous queries for pre-aggregating data at different time resolutions to support various OpenSTEF analysis requirements


Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^


Databricks is particularly valuable when working with OpenSTEF at enterprise scale, where large volumes of historical energy data need to be processed for model training or when running forecasts across hundreds or thousands of grid points simultaneously. Since OpenSTEF is a Python library that can run in any containerized environment, it integrates seamlessly with Databricks' distributed computing capabilities. Consider using Databricks with OpenSTEF when you need to handle massive datasets for feature engineering, when training models on years of historical data across multiple locations, or when your forecasting workload requires parallel processing of numerous prediction tasks. The cloud-based and platform-agnostic nature of OpenSTEF makes it well-suited for Databricks environments, especially when your organization already uses Databricks for other data science workflows or when you need the scalability to support grid-wide forecasting operations that exceed the capacity of single-machine deployments.


.. code-block:: python

   # Install OpenSTEF in Databricks cluster
   %pip install openstef

   # Import necessary modules
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd
   from datetime import datetime, timedelta

   # Configure Spark for distributed processing
   spark.conf.set("spark.sql.adaptive.enabled", "true")
   spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")

   # Load data from Delta Lake or other Databricks data source
   input_data = spark.table("energy_data.load_measurements").toPandas()

   # Create prediction job configuration
   prediction_job = PredictionJob(
       id=1,
       name="databricks_load_forecast",
       model="xgb",
       resolution_minutes=15,
       forecast_type="demand",
       horizon_minutes=2880,  # 48 hours ahead
       train_components=["load"]
   )

   # Prepare training data with distributed processing capabilities
   train_data = input_data[
       (input_data['datetime'] >= datetime.now() - timedelta(days=365)) &
       (input_data['datetime'] <= datetime.now() - timedelta(days=1))
   ].copy()

   # Train model using OpenSTEF pipeline optimized for large datasets
   trained_model = train_model_pipeline(
       pj=prediction_job,
       input_data=train_data,
       mlflow_tracking_uri="databricks"  # Use Databricks MLflow
   )

   # Create forecast for next 48 hours
   forecast_input = input_data[
       input_data['datetime'] >= datetime.now() - timedelta(hours=48)
   ].copy()

   forecast = create_forecast_pipeline(
       pj=prediction_job,
       input_data=forecast_input,
       model=trained_model
   )

   # Save results back to Delta Lake for downstream applications
   forecast_df = spark.createDataFrame(forecast)
   forecast_df.write.mode("overwrite").saveAsTable("energy_forecasts.load_predictions")

   print(f"Forecast generated for {len(forecast)} time periods")
   print(f"Results saved to Delta Lake table: energy_forecasts.load_predictions")


.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from pyspark.sql import SparkSession
   from concurrent.futures import ThreadPoolExecutor
   import pandas as pd

   # Initialize Spark session for Databricks
   spark = SparkSession.builder \
       .appName("OpenSTEF_Parallel_Forecasting") \
       .config("spark.sql.adaptive.enabled", "true") \
       .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
       .getOrCreate()

   # Define prediction jobs for multiple locations/assets
   prediction_jobs = [
       {"pid": 307, "location": "Amsterdam_North", "model_type": "xgb"},
       {"pid": 308, "location": "Rotterdam_Harbor", "model_type": "lgb"},
       {"pid": 309, "location": "Utrecht_Central", "model_type": "xgb"},
       {"pid": 310, "location": "Eindhoven_Industrial", "model_type": "linear"},
       {"pid": 311, "location": "Groningen_Residential", "model_type": "xgb"}
   ]

   def run_forecast_job(job_config):
       """Execute a single forecasting job"""
       try:
           # Load input data from Databricks tables
           input_data = spark.sql(f"""
               SELECT * FROM energy_data.load_measurements
               WHERE pid = {job_config['pid']}
               AND datetime >= current_date() - interval 90 days
           """).toPandas()

           # Create forecast using OpenSTEF
           forecast = create_forecast_pipeline(
               pj=job_config,
               input_data=input_data,
               horizon_minutes=2880,  # 48 hours ahead
               resolution_minutes=15
           )

           # Store results back to Databricks
           forecast_df = spark.createDataFrame(forecast)
           forecast_df.write \
               .mode("overwrite") \
               .option("mergeSchema", "true") \
               .saveAsTable(f"forecasts.predictions_{job_config['pid']}")

           return {"pid": job_config['pid'], "status": "success", "points": len(forecast)}

       except Exception as e:
           return {"pid": job_config['pid'], "status": "error", "error": str(e)}

   # Execute jobs in parallel using ThreadPoolExecutor
   with ThreadPoolExecutor(max_workers=4) as executor:
       # Submit all jobs
       future_to_job = {
           executor.submit(run_forecast_job, job): job
           for job in prediction_jobs
       }

       # Collect results as they complete
       results = []
       for future in future_to_job:
           job = future_to_job[future]
           try:
               result = future.result(timeout=300)  # 5 minute timeout per job
               results.append(result)
               print(f"Job {result['pid']}: {result['status']}")
           except Exception as e:
               print(f"Job {job['pid']} failed: {e}")

   # Summary of parallel execution
   successful_jobs = [r for r in results if r['status'] == 'success']
   print(f"Completed {len(successful_jobs)}/{len(prediction_jobs)} forecasting jobs successfully")


.. warning::

   When running OpenSTEF on Databricks for large-scale data processing, carefully monitor cluster resource allocation and costs. OpenSTEF's machine learning pipelines can be computationally intensive, especially during model training phases. Consider using auto-scaling clusters to handle variable workloads efficiently, but be aware that frequent scaling can impact performance. Set appropriate timeouts for long-running forecasting jobs and implement proper error handling to prevent resource waste from failed tasks. Since OpenSTEF is a Python library that processes energy data continuously, ensure your Databricks workspace has sufficient storage for intermediate results and model artifacts.


Migration from OpenSTEF v3
--------------------------


OpenSTEF v4.0 represents a significant evolution from version 3, introducing substantial improvements in code quality, architectural design, and domain applicability. The migration from v3 to v4 involves adapting to a more modular architecture with decoupled external dependencies, updated configuration mechanisms that replace hard-coded assumptions, and generalized domain logic that extends beyond Netherlands-specific implementations. Key changes include centralized data preprocessing logic, enhanced test coverage, standardized coding practices, and improved support for diverse data formats and availability scenarios. While these changes provide greater flexibility and robustness, they require careful consideration of your existing v3 implementation and may involve updating configuration files, adapting custom integrations, and reviewing data input formats to align with the new architectural patterns.


Key Changes and Breaking Changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Complete architectural redesign with modular, composable components replacing monolithic structure

- Full type safety implementation throughout the codebase to catch bugs early and improve maintainability

- Decoupled external dependencies (MLFlow, openstef-dbc, xgboost/gblinear) for enhanced modularity and portability

- Flexible configuration mechanisms replacing hard-coded assumptions and improving adaptability

- Clear interfaces for adding custom models, transforms, and metrics without modifying core code

- Generalized domain-specific logic to support use cases beyond Netherlands-specific implementations

- Relaxed rigid input data constraints allowing more flexible data formats and structures

- Improved support for diverse data availability scenarios enabling more resilient forecasting pipelines

- Pipeline APIs designed for enterprise integration with existing systems

- Flexible callback mechanisms for custom component development

- Performance optimizations for production use cases handling 10,000+ daily forecasts


- MLFlow integration has been decoupled and is no longer a hard dependency

- openstef-dbc database connector has been removed as a core dependency

- XGBoost gblinear model support has been deprecated in favor of more flexible model interfaces

- Hard-coded Dutch holiday calendars and energy pricing assumptions have been removed

- Rigid input data format constraints have been relaxed, breaking compatibility with some v3 data structures

- Direct database connection methods from v3 are no longer available in the core library

- Legacy configuration files and hard-coded parameters have been replaced with flexible configuration mechanisms

- Some v3-specific preprocessing pipelines have been consolidated and may require code updates


.. warning::

   OpenSTEF v4 represents a major architectural redesign that introduces significant breaking changes from v3. Key areas requiring code updates include: modular component interfaces replacing monolithic structures, decoupled external dependencies (MLFlow, openstef-dbc, xgboost), centralized data preprocessing logic, flexible configuration mechanisms replacing hard-coded assumptions, and generalized domain logic removing Netherlands-specific constraints. Existing v3 pipelines and integrations will require substantial refactoring to work with v4's new modular architecture and type-safe interfaces.


Step-by-Step Migration Process
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


- Review your current v3 configuration files and identify all prediction jobs, model settings, and data connections

- Install the latest OpenSTEF v4 package using pip install openstef

- Create new configuration files following the v4 schema format, mapping your v3 settings to the corresponding v4 structure

- Update your data connector implementation to use the new v4 database interface if you're using OpenSTEF-dbc

- Modify your forecasting pipeline code to use the updated v4 API methods and class structures

- Test the migration with a subset of your prediction jobs to validate functionality and performance

- Update any custom feature engineering or model training code to align with v4 methodology changes

- Deploy the migrated configuration to your production environment with appropriate monitoring

- Verify all prediction jobs are running correctly and producing expected forecast outputs

- Document any custom modifications or workarounds needed for your specific use case


.. code-block:: python

   ```python
   # OpenSTEF v3 example - Legacy approach
   from openstef.model.regressors import ARimaRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJob
   import pandas as pd

   # Load prediction job configuration (v3 format)
   pj = PredictionJob(
       id=123,
       name="solar_farm_forecast",
       model="arima",
       resolution_minutes=15,
       forecast_type="demand",
       train_components=["load", "weather", "apx"]
   )

   # Load training data
   train_data = pd.read_csv("historical_data.csv", parse_dates=['datetime'])
   train_data.set_index('datetime', inplace=True)

   # Train model using v3 pipeline
   model_specs = train_model_pipeline(
       pj=pj,
       input_data=train_data,
       check_hyper_params=True
   )

   # Create forecast using v3 pipeline
   forecast_data = pd.read_csv("forecast_input.csv", parse_dates=['datetime'])
   forecast_data.set_index('datetime', inplace=True)

   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=forecast_data,
       model_specs=model_specs
   )

   print(f"Generated forecast with {len(forecast)} data points")
   ```


.. code-block:: python

   ```python
   # V3 (Legacy) - Deprecated approach
   from openstef.model.regressors import ARIMAOpenstef
   from openstef.pipeline import train_model, create_forecast

   # Old configuration format
   config = {
       'model': 'arima',
       'horizons': [0.25, 24.0, 47.0],
       'resolution_minutes': 15
   }

   # Legacy training approach
   model = train_model(train_data, config)
   forecast = create_forecast(model, predict_data, config)

   # Current Version (V4+) - Recommended approach
   from openstef.model.regressors.xgb import XGBOpenstef
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Modern configuration using ModelConfig
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass

   model_specs = ModelSpecificationDataClass(
       id=123,
       name="wind_farm_forecast",
       model="xgb",
       horizons=[0.25, 24.0, 47.0],
       resolution_minutes=15,
       feature_names=["weather_temp", "weather_windspeed", "load_entsoe"]
   )

   # Current training approach with pipeline
   trained_model = train_model_pipeline(
       pj=train_data,
       model_specs=model_specs,
       mlflow_tracking_uri=None
   )

   # Current forecasting approach
   forecast_data = create_forecast_pipeline(
       pj=predict_data,
       model_specs=model_specs,
       trained_model=trained_model
   )
   ```


.. note::

   We strongly recommend implementing a phased testing approach during your migration. Start by testing the migration on a small subset of your prediction jobs in a development environment before applying changes to your production systems. Use OpenSTEF's offline example notebooks to validate that your migrated configurations produce expected results. Consider running both v3 and v4 configurations in parallel for a period to compare outputs and ensure consistency. This approach helps identify configuration issues early and minimizes the risk of disrupting your forecasting operations.


Configuration Migration
^^^^^^^^^^^^^^^^^^^^^^^


OpenSTEF configuration management has evolved across versions to provide more flexibility and better integration capabilities. The library's configuration system centers around prediction jobs, which serve as input configuration containers that define tasks and pipelines for specific forecasting scenarios. When migrating between versions, users should pay particular attention to changes in prediction job parameters, feature engineering configurations, and machine learning model settings. The configuration structure supports both task-based workflows (where OpenSTEF handles data fetching and writing) and pipeline-based workflows (where users manage data operations directly), and migration may require adjusting which approach your implementation uses. Additionally, data validation parameters and feature engineering settings within prediction jobs may have new options or modified defaults that need to be reviewed during version updates.


.. code-block:: yaml

   ```python
   # Example v3 configuration format (deprecated)
   config = {
       "model": {
           "type": "xgb",
           "hyper_params": {
               "n_estimators": 100,
               "max_depth": 6,
               "learning_rate": 0.1
           }
       },
       "feature_engineering": {
           "lag_features": [1, 7, 14],
           "weather_features": ["temperature", "wind_speed", "radiation"],
           "calendar_features": ["hour", "day_of_week", "month"]
       },
       "data_source": {
           "database_uri": "postgresql://user:pass@localhost/openstef",
           "load_table": "energy_loads",
           "weather_table": "weather_data"
       },
       "prediction_job": {
           "id": 123,
           "name": "solar_farm_forecast",
           "horizon_minutes": [15, 60, 1440],
           "resolution_minutes": 15,
           "train_components": ["load", "weather"],
           "quantiles": [0.1, 0.5, 0.9]
       }
   }
   ```


.. code-block:: yaml

   ```python
   # New configuration format for OpenSTEF prediction jobs
   from openstef.model.prediction_job import PredictionJobDataClass

   # Example of updated configuration structure
   config = PredictionJobDataClass(
       id=123,
       name="solar_farm_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       feature_modules=[
           "openstef.feature_engineering.weather_features",
           "openstef.feature_engineering.lag_features"
       ],
       horizon_minutes=2880,  # 48 hours
       resolution_minutes=15,
       train_components=1,
       hyper_params={
           "n_estimators": 100,
           "max_depth": 6,
           "learning_rate": 0.1
       },
       feature_names=[
           "load_entsoe",
           "T_2m",
           "radiation_temp",
           "windspeed_100m"
       ]
   )

   # Pipeline configuration with new structure
   pipeline_config = {
       "data_validation": {
           "flatliner_threshold": 0.95,
           "missing_fraction_threshold": 0.3
       },
       "feature_engineering": {
           "lag_features": [96, 672, 8760],  # 1 day, 1 week, 1 year in 15-min intervals
           "weather_features": ["temperature", "radiation", "windspeed"]
       },
       "model_training": {
           "validation_fraction": 0.2,
           "test_fraction": 0.1
       }
   }
   ```


- Prediction job configuration parameters including model type and location settings

- Feature engineering configuration for input data preparation and feature selection

- Machine learning model parameters such as XGB quantile model settings

- Data validation rules and thresholds for detecting flatliners and data quality issues

- Multi-horizon forecast configuration including time horizons and prediction intervals

- Confidence estimation method selection between available approaches

- Database connection parameters if using tasks instead of pipelines directly

- Input data source configuration and data fetching parameters


Validation and Testing
^^^^^^^^^^^^^^^^^^^^^^


After migrating to OpenSTEF, it's crucial to validate that your models and workflows are functioning correctly in the new environment. The OpenSTEF library provides comprehensive validation tools through the `openstef.validation` module to help ensure data quality and model reliability. Proper validation involves checking data completeness using functions like `calc_completeness_dataframe()` and `is_data_sufficient()`, detecting anomalies such as flatliner patterns with `detect_ongoing_flatliner()`, and verifying that your prediction workflows produce expected results. This validation step is essential because differences in data preprocessing, feature engineering, or model configuration between your previous system and OpenSTEF could lead to unexpected behavior or degraded performance if not properly addressed.


.. code-block:: python

   ```python
   import pandas as pd
   import numpy as np
   from openstef.model.model_creator import ModelCreator
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.validation.validation import validate

   # Load your historical data and configuration
   data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)
   pj_config = {
       'id': 123,
       'model': 'xgb',
       'horizon_minutes': 2880,
       'resolution_minutes': 15
   }

   # Create forecasts with current version
   current_forecast = create_forecast_pipeline(
       pj=pj_config,
       input_data=data,
       datetime_start='2023-01-01',
       datetime_end='2023-01-31'
   )

   # Load v3 forecast results (assuming you saved them previously)
   v3_forecast = pd.read_csv('v3_forecast_results.csv', index_col=0, parse_dates=True)

   # Compare forecast accuracy metrics
   def compare_forecasts(actual, forecast1, forecast2, name1="Current", name2="v3"):
       """Compare two forecast versions against actual values"""

       # Calculate MAE for both versions
       mae1 = np.mean(np.abs(actual - forecast1))
       mae2 = np.mean(np.abs(actual - forecast2))

       # Calculate RMSE for both versions
       rmse1 = np.sqrt(np.mean((actual - forecast1) ** 2))
       rmse2 = np.sqrt(np.mean((actual - forecast2) ** 2))

       # Calculate bias
       bias1 = np.mean(forecast1 - actual)
       bias2 = np.mean(forecast2 - actual)

       print(f"Comparison Results:")
       print(f"{name1} - MAE: {mae1:.2f}, RMSE: {rmse1:.2f}, Bias: {bias1:.2f}")
       print(f"{name2} - MAE: {mae2:.2f}, RMSE: {rmse2:.2f}, Bias: {bias2:.2f}")
       print(f"MAE Improvement: {((mae2 - mae1) / mae2 * 100):.1f}%")
       print(f"RMSE Improvement: {((rmse2 - rmse1) / rmse2 * 100):.1f}%")

   # Perform comparison
   actual_values = data['load']  # Assuming 'load' is your target column
   compare_forecasts(actual_values, current_forecast['forecast'], v3_forecast['forecast'])

   # Validate data quality consistency
   validation_current = validate(
       pj_id=pj_config['id'],
       data=data,
       flatliner_threshold_minutes=180,
       resolution_minutes=15
   )

   print(f"Data validation passed: {validation_current}")

   # Check for significant differences in predictions
   forecast_diff = np.abs(current_forecast['forecast'] - v3_forecast['forecast'])
   large_differences = forecast_diff > (0.1 * np.mean(actual_values))

   if large_differences.any():
       print(f"Warning: {large_differences.sum()} timestamps show significant differences (>10% of mean load)")
       print("Consider investigating these periods:")
       print(current_forecast.index[large_differences][:5])  # Show first 5 problematic timestamps
   ```


- Verify that all prediction jobs are properly configured and accessible through the OpenSTEF library

- Test data validation functions using openstef.validation.validate() to ensure your data meets quality requirements

- Check data completeness using openstef.validation.calc_completeness_dataframe() and calc_completeness_features()

- Validate that flatliner detection works correctly with detect_ongoing_flatliner() function

- Ensure model training pipeline runs successfully using openstef.pipeline.train_model

- Test forecast creation with openstef.pipeline.create_forecast to verify end-to-end functionality

- Verify hyperparameter optimization works with openstef.pipeline.optimize_hyperparameters

- Check that all required regressors (XGB, LGBM, Linear, etc.) are available and functioning

- Test model serialization and deserialization using openstef.model.serializer

- Validate performance monitoring capabilities with openstef.monitoring.performance_meter

- Ensure data sufficiency checks pass using is_data_sufficient() with appropriate thresholds

- Test component forecasting functionality if using split forecasts

- Verify that all custom model configurations load and execute properly


.. note::

   We recommend running your migrated OpenSTEF implementation in parallel with your existing forecasting system for at least 2-4 weeks before fully switching over. This parallel period allows you to validate that the library produces consistent results and helps identify any data quality issues or configuration problems. Use the built-in validation functions like `validate()` and `is_data_sufficient()` to systematically compare outputs and ensure your migration maintains forecasting accuracy.


