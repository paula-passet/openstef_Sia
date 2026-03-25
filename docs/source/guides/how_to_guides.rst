How-To Guides
=============


Deployment and Orchestration
----------------------------


OpenSTEF library deployment in production requires orchestrating training and forecasting tasks through schedulers like CRON jobs or workflow engines such as Dagster. The library provides standalone task modules that can be executed directly or integrated into existing pipeline infrastructure. Production deployments must handle database connections, MLflow model storage, and context management for reliable automated forecasting operations.


.. code-block:: python

   #!/usr/bin/env python3
   import sys
   import logging
   from openstef.tasks.train_model import main as train_model_main
   from openstef.tasks.create_basecase_forecast import main as forecast_main

   # Configure logging for cron job
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(levelname)s - %(message)s',
       handlers=[
           logging.FileHandler('/var/log/openstef/cron.log'),
           logging.StreamHandler()
       ]
   )

   def run_training_job():
       try:
           logging.info("Starting model training job")
           train_model_main()
           logging.info("Model training completed successfully")
           return 0
       except Exception as e:
           logging.error(f"Model training failed: {str(e)}")
           return 1

   def run_forecast_job():
       try:
           logging.info("Starting basecase forecast job")
           forecast_main(t_behind_days=15, t_ahead_days=14)
           logging.info("Basecase forecast completed successfully")
           return 0
       except Exception as e:
           logging.error(f"Basecase forecast failed: {str(e)}")
           return 1

   if __name__ == "__main__":
       job_type = sys.argv[1] if len(sys.argv) > 1 else "forecast"

       if job_type == "train":
           exit_code = run_training_job()
       elif job_type == "forecast":
           exit_code = run_forecast_job()
       else:
           logging.error(f"Unknown job type: {job_type}")
           exit_code = 1

       sys.exit(exit_code)


Orchestration with Dagster
^^^^^^^^^^^^^^^^^^^^^^^^^^


Dagster provides robust orchestration capabilities for OpenSTEF's complex forecasting workflows, enabling seamless coordination of training, prediction, and analysis pipelines. The framework's asset-based approach naturally maps to OpenSTEF's pipeline architecture, allowing you to define dependencies between model training, forecast generation, and evaluation steps. Dagster's built-in monitoring, lineage tracking, and failure recovery mechanisms ensure reliable execution of multi-step forecasting operations across different target groups and time horizons.


.. code-block:: python

   from dagster import asset, job, op, Config
   from openstef.pipeline.train_create_forecast_backtest import train_create_forecast_backtest_pipeline
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_meta.presets.forecasting_workflow import create_ensemble_forecasting_workflow, EnsembleForecastingWorkflowConfig
   import pandas as pd

   class ForecastConfig(Config):
       prediction_job: int = 307
       horizon_minutes: int = 2880
       train_horizons_minutes: list[int] = [15, 60, 1440]

   @asset
   def training_data() -> pd.DataFrame:
       return pd.read_csv("training_data.csv", index_col=0, parse_dates=True)

   @asset
   def forecast_model(training_data: pd.DataFrame, config: ForecastConfig) -> CustomForecastingWorkflow:
       workflow_config = EnsembleForecastingWorkflowConfig(
           prediction_job=config.prediction_job,
           horizon_minutes=config.horizon_minutes
       )
       return create_ensemble_forecasting_workflow(workflow_config)

   @asset
   def forecast_results(forecast_model: CustomForecastingWorkflow, training_data: pd.DataFrame) -> pd.DataFrame:
       forecast_dataset = forecast_model.predict(training_data)
       return forecast_dataset.to_dataframe()

   @op
   def run_backtest(context, prediction_job: int, horizon_minutes: int):
       result = train_create_forecast_backtest_pipeline(
           pj=prediction_job,
           horizon_minutes=horizon_minutes,
           datetime_start="2023-01-01",
           datetime_end="2023-12-31"
       )
       return result

   @job
   def forecasting_pipeline():
       run_backtest()


Data Integration Patterns
-------------------------


OpenSTEF library supports multiple data integration patterns to connect with external systems and data platforms. Direct database integration works best for real-time operational deployments where low latency is critical. Cloud storage patterns like S3 are ideal for batch processing, model benchmarking, and archival workflows. Time-series databases such as InfluxDB excel at handling high-frequency measurement data with efficient querying capabilities. API-based integration provides flexibility for connecting diverse systems while maintaining loose coupling between OpenSTEF and external data sources.


.. code-block:: python

   import boto3
   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd

   # S3 data retrieval with authentication
   s3_client = boto3.client(
       's3',
       aws_access_key_id='your_access_key',
       aws_secret_access_key='your_secret_key',
       region_name='eu-west-1'
   )

   # Download prediction data from S3
   response = s3_client.get_object(
       Bucket='openstef-data',
       Key='predictions/system_Location_A_System_1.csv'
   )
   df = pd.read_csv(response['Body'])

   # InfluxDB client with authentication
   influx_client = InfluxDBClient(
       url="http://localhost:8086",
       token="your_influx_token",
       org="openstef"
   )

   # Post predictions to InfluxDB
   write_api = influx_client.write_api(write_options=SYNCHRONOUS)

   for _, row in df.iterrows():
       point = Point("predictions") \
           .tag("system_id", "Location_A_System_1") \
           .tag("prediction_id", "313") \
           .field("forecast", float(row['forecast'])) \
           .time(row['datetime'])

       write_api.write(bucket="openstef", record=point)

   influx_client.close()


Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^


OpenSTEF integrates with Databricks through Spark-based distributed computing capabilities. The library's forecasting pipelines work with Databricks DataFrames and can leverage MLflow for model tracking. Key requirements include configuring the MLflow tracking URI and ensuring weather data contains required columns like 'radiation' and 'windspeed_100m' for component forecasting workflows.


.. code-block:: python

   # Databricks notebook setup for OpenSTEF
   import os
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from pyspark.sql import SparkSession

   # Initialize Spark session with optimized settings
   spark = SparkSession.builder \
       .appName("OpenSTEF-Forecasting") \
       .config("spark.sql.adaptive.enabled", "true") \
       .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
       .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
       .getOrCreate()

   # Configure MLflow tracking
   mlflow_tracking_uri = "databricks"
   os.environ["MLFLOW_TRACKING_URI"] = mlflow_tracking_uri

   # Create prediction job
   pj = PredictionJobDataClass(
       id=123,
       name="solar_forecast",
       model_type="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880
   )

   # Load input data from Delta table
   input_data = spark.table("energy_data.load_measurements").toPandas()

   # Create forecast
   forecast_df = create_forecast_pipeline(
       pj=pj,
       input_data=input_data,
       mlflow_tracking_uri=mlflow_tracking_uri
   )

   # Save results to Delta table
   spark.createDataFrame(forecast_df).write \
       .mode("overwrite") \
       .option("overwriteSchema", "true") \
       .saveAsTable("energy_data.forecasts")


Migration from V3 to V4
-----------------------


OpenSTEF 4.0 introduces significant architectural changes focused on modularity, type safety, and broader domain applicability. The library decouples external dependencies like MLFlow and openstef-dbc, centralizes data preprocessing logic, and replaces hard-coded assumptions with flexible configuration mechanisms. These changes enable support for diverse use cases beyond the Netherlands energy grid while maintaining performance for production deployments.

Migration planning should account for breaking changes in data preprocessing workflows, configuration structures, and external dependency integrations. The modular architecture requires updating existing pipelines to use new component interfaces, while improved type safety may expose previously hidden compatibility issues. Plan for testing custom models and transforms against the new extensible framework before production deployment.


- Update import statements: Replace 'from openstef.model import OpenstfRegressor' with 'from openstef.models import XGBQuantileOpenstfRegressor' or appropriate model class

- Replace MLFlow dependencies: Remove mlflow tracking calls and replace with openstef.callbacks.MLFlowCallback if needed

- Update data preprocessing: Replace manual preprocessing with openstef.preprocessing.create_feature_pipeline() for standardized feature engineering

- Modify model initialization: Change OpenstfRegressor() to specific model classes like XGBQuantileOpenstfRegressor(quantiles=[0.1, 0.5, 0.9])

- Update prediction calls: Replace model.predict(data) with model.predict(data, quantiles=[0.5]) for quantile models

- Replace validation logic: Use openstef.validation.split_data_train_validation_test() instead of custom splitting

- Update configuration: Replace hard-coded parameters with openstef.config.Config() objects for flexible settings

- Modify pipeline creation: Use openstef.pipeline.create_forecast_pipeline() instead of manual pipeline assembly

- Update callback usage: Replace direct logging with openstef.callbacks system for model tracking and monitoring

- Test with new API: Run openstef.validation.backtest() to verify migration using the new validation framework


Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^


Common migration challenges include dependency conflicts when upgrading from V3 to V4, particularly with MLFlow and xgboost/gblinear integrations. Data format compatibility issues may arise due to relaxed input constraints in V4. Configuration migration requires updating hard-coded assumptions to use the new flexible configuration mechanisms. Test coverage gaps can surface during migration, requiring additional validation of custom components against V4's modular architecture.


.. code-block:: python

   OpenSTEF V3 (Legacy):


   from openstef.model.regressors import ARIMAOpenstfRegressor
   from openstef.pipeline import train_model
   from openstef.data_classes import ModelConfig

   # V3 approach with tightly coupled components
   config = ModelConfig(
       model="arima",
       horizons=[0.25, 24.0],
       feature_names=["load", "weather_temp"]
   )

   model = ARIMAOpenstfRegressor()
   trained_model = train_model(
       model=model,
       config=config,
       train_data=train_df
   )


   OpenSTEF V4 (Current):


   from openstef.models import ARIMAModel
   from openstef.pipeline import Pipeline
   from openstef.config import ForecastConfig

   # V4 approach with modular, configurable components
   config = ForecastConfig(
       model_type="arima",
       horizons=[0.25, 24.0],
       features=["load", "weather_temp"],
       preprocessing={"normalize": True}
   )

   pipeline = Pipeline(config=config)
   model = ARIMAModel(config.model_params)
   trained_model = pipeline.train(model, train_data=train_df)


