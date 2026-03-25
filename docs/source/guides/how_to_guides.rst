How-To Guides
=============

This section provides task-specific implementation guides for common OpenSTEF deployment and integration scenarios. These guides focus on practical implementation details for specific technical challenges you might encounter when deploying OpenSTEF in production environments.

Setting Up Deployment Orchestration
------------------------------------

OpenSTEF is a Python library that requires orchestration to run forecasting tasks in production. Here are two common approaches for scheduling and running OpenSTEF tasks.

Simple Cron Job Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, you can run OpenSTEF tasks directly using cron jobs. This approach works well for small to medium-scale deployments with predictable scheduling needs.

Create a Python script that wraps OpenSTEF tasks::

   # train_model_job.py
   from openstef.tasks.train_model import main as train_model_main
   from openstef.tasks.utils.taskcontext import TaskContext
   from your_config import get_config, get_database

   def run_training():
       config = get_config()
       database = get_database()
       
       with TaskContext("model_training", config, database) as context:
           train_model_main(config=config, database=database)

   if __name__ == "__main__":
       run_training()

Set up your crontab to run training and forecasting tasks::

   # Train models daily at 2 AM
   0 2 * * * /usr/bin/python /path/to/train_model_job.py
   
   # Create forecasts every hour
   0 * * * * /usr/bin/python /path/to/create_forecast_job.py
   
   # Optimize hyperparameters weekly
   0 3 * * 0 /usr/bin/python /path/to/optimize_hyperparameters_job.py

.. note::
   The TaskContext manager handles error reporting and database connections. Set ``suppress_exceptions=False`` to ensure cron jobs fail visibly when issues occur.

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more complex workflows with dependencies, monitoring, and retry logic, Dagster provides a robust orchestration platform::

   from dagster import asset, job, schedule, DefaultSensorContext
   from openstef.tasks.train_model import train_model_task
   from openstef.tasks.create_basecase_forecast import create_basecase_forecast_task
   from your_openstef_setup import get_prediction_jobs, get_context

   @asset
   def trained_models():
       """Train OpenSTEF models for all prediction jobs."""
       context = get_context()
       prediction_jobs = get_prediction_jobs()
       
       for pj in prediction_jobs:
           train_model_task(pj, context, check_old_model_age=True)
       
       return len(prediction_jobs)

   @asset(deps=[trained_models])
   def basecase_forecasts():
       """Generate basecase forecasts using trained models."""
       context = get_context()
       prediction_jobs = get_prediction_jobs()
       
       for pj in prediction_jobs:
           create_basecase_forecast_task(pj, context)
       
       return len(prediction_jobs)

   @job
   def openstef_pipeline():
       basecase_forecasts()

   @schedule(cron_schedule="0 2 * * *", job=openstef_pipeline)
   def daily_forecast_schedule():
       return {}

This approach provides better visibility into task execution, automatic retries, and dependency management between training and forecasting steps.

Data Integration Patterns
--------------------------

OpenSTEF requires input data (load measurements, weather forecasts) and produces forecast outputs that need integration with external systems. Here are common integration patterns.

S3 Integration
^^^^^^^^^^^^^^

For cloud-native deployments, S3 provides scalable storage for both input data and forecast results::

   import boto3
   import pandas as pd
   from openstef.tasks.create_basecase_forecast import create_basecase_forecast_task
   from your_openstef_setup import get_context, get_prediction_job

   def load_data_from_s3(bucket: str, key: str) -> pd.DataFrame:
       """Load input data from S3."""
       s3 = boto3.client('s3')
       obj = s3.get_object(Bucket=bucket, Key=key)
       return pd.read_parquet(obj['Body'])

   def save_forecast_to_s3(forecast: pd.DataFrame, bucket: str, key: str):
       """Save forecast results to S3."""
       s3 = boto3.client('s3')
       parquet_buffer = forecast.to_parquet()
       s3.put_object(Bucket=bucket, Key=key, Body=parquet_buffer)

   def run_forecast_with_s3_integration():
       # Load input data
       load_data = load_data_from_s3('input-bucket', 'load_data/latest.parquet')
       weather_data = load_data_from_s3('input-bucket', 'weather/latest.parquet')
       
       # Run OpenSTEF forecast
       context = get_context()
       pj = get_prediction_job(pid=123)
       
       # Customize prediction job with S3 data
       # (Implementation depends on your data adapter)
       forecast_result = create_basecase_forecast_task(pj, context)
       
       # Save results back to S3
       save_forecast_to_s3(forecast_result, 'output-bucket', 'forecasts/latest.parquet')

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time-series focused deployments, InfluxDB provides efficient storage and querying::

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd

   def read_from_influxdb(client: InfluxDBClient, query: str) -> pd.DataFrame:
       """Read time series data from InfluxDB."""
       query_api = client.query_api()
       result = query_api.query_data_frame(query)
       return result

   def write_forecast_to_influxdb(client: InfluxDBClient, forecast: pd.DataFrame, measurement: str):
       """Write forecast results to InfluxDB."""
       write_api = client.write_api(write_options=SYNCHRONOUS)
       
       points = []
       for index, row in forecast.iterrows():
           point = Point(measurement) \
               .tag("prediction_job", row['pid']) \
               .field("forecast", row['forecast']) \
               .field("quantile_10", row['quantile_10']) \
               .field("quantile_90", row['quantile_90']) \
               .time(index)
           points.append(point)
       
       write_api.write_points(points)

   def influxdb_forecast_pipeline():
       client = InfluxDBClient(url="http://localhost:8086", token="your-token", org="your-org")
       
       # Query input data
       load_query = 'from(bucket:"load_data") |> range(start: -30d)'
       load_data = read_from_influxdb(client, load_query)
       
       # Run OpenSTEF forecast (adapt to your setup)
       # forecast_result = run_openstef_forecast(load_data)
       
       # Write results back
       # write_forecast_to_influxdb(client, forecast_result, "energy_forecast")

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For environments using Databricks for data processing, integrate OpenSTEF within Spark workflows::

   from pyspark.sql import SparkSession
   from pyspark.sql.functions import pandas_udf, col
   from pyspark.sql.types import StructType, StructField, DoubleType, TimestampType
   import pandas as pd

   # Define forecast schema
   forecast_schema = StructType([
       StructField("timestamp", TimestampType(), True),
       StructField("forecast", DoubleType(), True),
       StructField("quantile_10", DoubleType(), True),
       StructField("quantile_90", DoubleType(), True)
   ])

   @pandas_udf(returnType=forecast_schema)
   def openstef_forecast_udf(data: pd.DataFrame) -> pd.DataFrame:
       """Pandas UDF to run OpenSTEF forecasting on Spark DataFrame."""
       # Initialize OpenSTEF components
       # (Implementation depends on your OpenSTEF setup)
       
       # Process data and create forecast
       # forecast_result = create_forecast(data)
       
       # Return results in expected schema
       return forecast_result[['timestamp', 'forecast', 'quantile_10', 'quantile_90']]

   def run_databricks_forecast():
       spark = SparkSession.builder.appName("OpenSTEF_Forecast").getOrCreate()
       
       # Load input data from Delta tables
       load_data = spark.table("energy_data.load_measurements")
       weather_data = spark.table("weather_data.forecasts")
       
       # Join and prepare data for forecasting
       input_data = load_data.join(weather_data, on="timestamp")
       
       # Apply OpenSTEF forecasting
       forecasts = input_data.groupBy("prediction_job_id").apply(openstef_forecast_udf)
       
       # Save results to Delta table
       forecasts.write.mode("overwrite").saveAsTable("forecasts.energy_predictions")

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural refactor focused on modularity and flexibility. This section guides you through the key changes and migration steps.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The V4 release introduces several breaking changes:

- **Modular architecture**: OpenSTEF is now split into separate packages (openstef-core, openstef-models, openstef-meta, openstef-beam)
- **Decoupled dependencies**: External dependencies like MLFlow and openstef-dbc are no longer required
- **Flexible configuration**: Hard-coded assumptions replaced with configurable options
- **Type safety**: Full type annotations throughout the codebase
- **Improved extensibility**: Clear interfaces for custom models and transforms

Migration Strategy
^^^^^^^^^^^^^^^^^^

Start by updating your imports to use the new modular structure::

   # V3 imports
   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.tasks.train_model import train_model_task

   # V4 imports
   from openstef_models.regressors import ARIMAOpenstfRegressor
   from openstef_models.preprocessing import apply_features
   from openstef_models.workflows import train_model_task

Update configuration patterns to use the new flexible configuration system::

   # V3: Hard-coded configuration
   def create_model():
       return ARIMAOpenstfRegressor(
           # Fixed parameters
       )

   # V4: Configurable presets
   from openstef_models.presets import get_model_preset
   
   def create_model(config):
       return get_model_preset(
           model_type=config.model_type,
           use_case=config.use_case,
           **config.model_params
       )

Replace TaskContext usage with the new modular approach::

   # V3: TaskContext with database dependency
   from openstef.tasks.utils.taskcontext import TaskContext
   
   with TaskContext("task_name", config, database) as context:
       train_model_task(pj, context)

   # V4: Flexible context management
   from openstef_core.context import create_context
   
   context = create_context(
       config=config,
       data_provider=your_data_provider,  # No longer requires openstef-dbc
       model_store=your_model_store
   )
   train_model_task(pj, context)

.. warning::
   V4 is not backward compatible with V3. Plan for a complete migration rather than incremental updates. Test thoroughly with your specific use cases before deploying to production.

Testing Your Migration
^^^^^^^^^^^^^^^^^^^^^^^

Use OpenSTEF Beam to validate that your V4 migration produces equivalent results::

   from openstef_beam.benchmarking import compare_model_versions
   
   # Compare V3 vs V4 results
   comparison_results = compare_model_versions(
       v3_predictions=v3_forecast_results,
       v4_predictions=v4_forecast_results,
       evaluation_metrics=['mae', 'rmse', 'mape']
   )
   
   # Ensure performance is maintained or improved
   assert comparison_results.mae_difference < 0.05  # Less than 5% difference

For detailed migration assistance, consult the changelog for breaking changes and the tutorials section for V4-specific implementation patterns.