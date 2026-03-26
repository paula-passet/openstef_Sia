How-To Guides
=============

This section provides practical, task-specific guides for common OpenSTEF implementation scenarios. These guides focus on specific deployment patterns, data integrations, and migration tasks that go beyond the basic tutorials.

.. note::
   These guides assume you've completed the :doc:`../getting_started/quickstart` and are familiar with OpenSTEF's core concepts. For comprehensive learning, see :doc:`../getting_started/tutorials`.

Setting Up Production Deployments
----------------------------------

Simple Cron-based Scheduling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most straightforward way to deploy OpenSTEF forecasting is using cron jobs for periodic execution. OpenSTEF provides task modules specifically designed for this approach.

.. code-block:: python

   # create_forecast_job.py
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef_models.workflows import ForecastingWorkflow
   from openstef_core.data import PredictionJobDataClass
   
   def main():
       # Load your prediction job configuration
       pj = PredictionJobDataClass.from_config("config/prediction_job.yaml")
       
       # Create context with your data connections
       context = TaskContext(
           database=your_database_connection,
           influxdb=your_influxdb_connection
       )
       
       # Run the forecast task
       create_forecast_task(pj, context, t_behind_days=14)
   
   if __name__ == "__main__":
       main()

Set up the cron job to run every 15 minutes:

.. code-block:: bash

   # Add to crontab with: crontab -e
   */15 * * * * /path/to/python /path/to/create_forecast_job.py >> /var/log/openstef.log 2>&1

For model training and hyperparameter optimization, create separate scripts:

.. code-block:: python

   # train_models_job.py
   from openstef.tasks.train_model import train_model_task
   
   def main():
       # Run daily at 2 AM
       train_model_task(pj, context)
   
   # optimize_hyperparams_job.py  
   from openstef.tasks.optimize_hyperparameters import optimize_hyperparameters_task
   
   def main():
       # Run weekly
       optimize_hyperparameters_task(pj, context, check_hyper_param_age=True)

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more sophisticated workflow management, integrate OpenSTEF with Dagster for dependency tracking, monitoring, and error handling.

.. code-block:: python

   # dagster_openstef.py
   from dagster import asset, AssetIn, Config, DagsterInstance
   from openstef_models.workflows import ForecastingWorkflow, TrainingWorkflow
   from openstef_core.data import PredictionJobDataClass
   import pandas as pd
   
   class OpenSTEFConfig(Config):
       prediction_job_id: int
       forecast_horizon_hours: int = 47
       
   @asset
   def raw_data(config: OpenSTEFConfig) -> pd.DataFrame:
       """Fetch raw input data from your data source."""
       # Your data retrieval logic here
       return fetch_training_data(config.prediction_job_id)
   
   @asset
   def trained_model(raw_data: pd.DataFrame, config: OpenSTEFConfig):
       """Train OpenSTEF model."""
       pj = PredictionJobDataClass.from_id(config.prediction_job_id)
       
       workflow = TrainingWorkflow()
       model = workflow.run(
           data=raw_data,
           prediction_job=pj
       )
       
       # Store model using your preferred method
       save_model(model, config.prediction_job_id)
       return model
   
   @asset(ins={"model": AssetIn("trained_model")})
   def forecast(model, config: OpenSTEFConfig) -> pd.DataFrame:
       """Create forecast using trained model."""
       pj = PredictionJobDataClass.from_id(config.prediction_job_id)
       
       workflow = ForecastingWorkflow()
       forecast_data = workflow.run(
           model=model,
           prediction_job=pj,
           horizon_hours=config.forecast_horizon_hours
       )
       
       return forecast_data

Deploy with Dagster's scheduling capabilities:

.. code-block:: python

   from dagster import ScheduleDefinition, DefaultScheduleStatus
   
   forecast_schedule = ScheduleDefinition(
       name="openstef_forecast_schedule",
       cron_schedule="*/15 * * * *",  # Every 15 minutes
       job_name="forecast_job",
       default_status=DefaultScheduleStatus.RUNNING
   )

Data Integration Patterns
-------------------------

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF supports S3 for storing benchmark results and model artifacts through the openstef-beam package.

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   import boto3
   
   # Configure S3 storage for benchmark results
   local_storage = LocalBenchmarkStorage(base_path="/tmp/openstef_benchmarks")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="your-openstef-bucket",
       s3_prefix="benchmarks/",
       s3fs_kwargs={
           "key": "your-aws-access-key",
           "secret": "your-aws-secret-key",
           "endpoint_url": "https://s3.amazonaws.com"
       }
   )
   
   # Use in benchmarking workflow
   from openstef_beam.benchmarking import BenchmarkTarget
   
   target = BenchmarkTarget(
       prediction_job_id=123,
       model_type="xgb_quantile",
       start_date="2024-01-01",
       end_date="2024-01-31"
   )
   
   # Results are automatically synced to S3
   s3_storage.save_backtest_output(target, backtest_results)

For custom S3 model storage:

.. code-block:: python

   import boto3
   import pickle
   from openstef_models.serialization import ModelSerializer
   
   def save_model_to_s3(model, bucket_name, key):
       """Save OpenSTEF model to S3."""
       s3_client = boto3.client('s3')
       
       # Serialize model
       serializer = ModelSerializer()
       model_bytes = serializer.serialize(model)
       
       # Upload to S3
       s3_client.put_object(
           Bucket=bucket_name,
           Key=key,
           Body=model_bytes
       )
   
   def load_model_from_s3(bucket_name, key):
       """Load OpenSTEF model from S3."""
       s3_client = boto3.client('s3')
       
       # Download from S3
       response = s3_client.get_object(Bucket=bucket_name, Key=key)
       model_bytes = response['Body'].read()
       
       # Deserialize model
       serializer = ModelSerializer()
       return serializer.deserialize(model_bytes)

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

OpenSTEF natively supports InfluxDB for time series data storage through the openstef-dbc package.

.. code-block:: python

   from openstef_dbc.database import InfluxDBConnector
   import pandas as pd
   
   # Configure InfluxDB connection
   influx_config = {
       'host': 'localhost',
       'port': 8086,
       'database': 'openstef',
       'username': 'your_username',
       'password': 'your_password'
   }
   
   influx_client = InfluxDBConnector(**influx_config)
   
   # Write forecast results to InfluxDB
   def write_forecast_to_influx(forecast_df, prediction_job_id):
       """Write forecast results to InfluxDB."""
       
       # Prepare data for InfluxDB
       points = []
       for timestamp, row in forecast_df.iterrows():
           point = {
               "measurement": "forecast",
               "tags": {
                   "prediction_job_id": prediction_job_id,
                   "model_type": row.get("model_type", "unknown")
               },
               "time": timestamp,
               "fields": {
                   "forecast": float(row["forecast"]),
                   "quantile_10": float(row.get("quantile_10", 0)),
                   "quantile_90": float(row.get("quantile_90", 0))
               }
           }
           points.append(point)
       
       influx_client.write_points(points)
   
   # Read historical data from InfluxDB
   def read_training_data(system_id, start_date, end_date):
       """Read training data from InfluxDB."""
       query = f"""
       SELECT mean("load") as load, mean("temperature") as temperature
       FROM "measurements"
       WHERE "system_id" = '{system_id}'
       AND time >= '{start_date}' AND time <= '{end_date}'
       GROUP BY time(15m) fill(linear)
       """
       
       result = influx_client.query(query)
       return pd.DataFrame(result.get_points())

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

Integrate OpenSTEF with Databricks for large-scale data processing and model training.

.. code-block:: python

   # databricks_openstef.py
   from pyspark.sql import SparkSession
   from openstef_models.workflows import TrainingWorkflow
   import pandas as pd
   
   # Initialize Spark session
   spark = SparkSession.builder.appName("OpenSTEF").getOrCreate()
   
   def train_models_on_databricks(prediction_jobs_df):
       """Train multiple OpenSTEF models in parallel on Databricks."""
       
       def train_single_model(prediction_job_data):
           """Train a single model - runs on Spark workers."""
           from openstef_models.workflows import TrainingWorkflow
           from openstef_core.data import PredictionJobDataClass
           
           # Convert Spark Row to PredictionJobDataClass
           pj = PredictionJobDataClass(**prediction_job_data.asDict())
           
           # Load training data (implement your data loading logic)
           training_data = load_training_data(pj.id)
           
           # Train model
           workflow = TrainingWorkflow()
           model = workflow.run(data=training_data, prediction_job=pj)
           
           # Save model to distributed storage
           save_model_to_dbfs(model, f"/mnt/models/pj_{pj.id}")
           
           return {"prediction_job_id": pj.id, "status": "completed"}
       
       # Use Spark to parallelize model training
       results = prediction_jobs_df.rdd.map(train_single_model).collect()
       return results
   
   # Example usage
   prediction_jobs_spark_df = spark.createDataFrame(prediction_jobs_pandas_df)
   results = train_models_on_databricks(prediction_jobs_spark_df)

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity and flexibility. This section guides you through the migration process.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant changes in V4 include:

- **Modular package structure**: Core functionality split into `openstef-core`, `openstef-models`, and `openstef-beam`
- **Type safety**: Full type annotations throughout the codebase
- **Workflow-based architecture**: Pipelines replaced with more flexible workflow classes
- **Decoupled dependencies**: MLflow, database connections, and model types are now optional

Package Migration
^^^^^^^^^^^^^^^^^

Update your imports to use the new package structure:

.. code-block:: python

   # V3 imports
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # V4 imports
   from openstef_models.workflows import TrainingWorkflow
   from openstef_models.regressors import XGBQuantileRegressor
   from openstef_core.data import PredictionJobDataClass

Configuration Migration
^^^^^^^^^^^^^^^^^^^^^^^

V4 uses a more flexible configuration system:

.. code-block:: python

   # V3 configuration (hardcoded in prediction job)
   pj = PredictionJobDataClass(
       id=123,
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       feature_names=["load_entsoe", "temperature", "windspeed"]
   )
   
   # V4 configuration (flexible workflow configuration)
   from openstef_models.config import ModelConfig, FeatureConfig
   
   model_config = ModelConfig(
       model_type="xgb_quantile",
       quantiles=[0.1, 0.5, 0.9],
       hyperparameters={
           "n_estimators": 100,
           "max_depth": 6
       }
   )
   
   feature_config = FeatureConfig(
       features=["load_entsoe", "temperature", "windspeed"],
       lag_features=["load_entsoe"],
       weather_features=["temperature", "windspeed"]
   )
   
   pj = PredictionJobDataClass(
       id=123,
       model_config=model_config,
       feature_config=feature_config
   )

Pipeline to Workflow Migration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Replace V3 pipeline calls with V4 workflow classes:

.. code-block:: python

   # V3 pipeline approach
   from openstef.pipeline.train_model import train_model_pipeline
   
   model = train_model_pipeline(
       pj=prediction_job,
       input_data=training_data,
       mlflow_tracking_uri="sqlite:///mlruns.db"
   )
   
   # V4 workflow approach
   from openstef_models.workflows import TrainingWorkflow
   from openstef_models.serialization import MLflowModelStore
   
   # Optional: configure model storage
   model_store = MLflowModelStore(tracking_uri="sqlite:///mlruns.db")
   
   workflow = TrainingWorkflow(model_store=model_store)
   model = workflow.run(
       data=training_data,
       prediction_job=prediction_job
   )

Data Validation Updates
^^^^^^^^^^^^^^^^^^^^^^^

V4 provides more flexible data validation:

.. code-block:: python

   # V3 validation (automatic in pipelines)
   # Validation was hardcoded in pipeline execution
   
   # V4 validation (explicit and configurable)
   from openstef_models.validation import DataValidator, ValidationConfig
   
   validation_config = ValidationConfig(
       check_missing_values=True,
       check_flatliners=True,
       max_missing_percentage=0.1,
       flatliner_threshold_hours=6
   )
   
   validator = DataValidator(validation_config)
   
   # Validate before training
   validation_result = validator.validate(training_data)
   if not validation_result.is_valid:
       print(f"Validation errors: {validation_result.errors}")
       # Handle validation errors appropriately

Migration Checklist
^^^^^^^^^^^^^^^^^^^^

Use this checklist to ensure complete migration:

1. **Update dependencies**: Replace `openstef` with appropriate V4 packages
2. **Update imports**: Change import statements to new package structure  
3. **Refactor pipeline calls**: Replace pipeline functions with workflow classes
4. **Update configuration**: Move from hardcoded to flexible configuration objects
5. **Review data validation**: Implement explicit validation where needed
6. **Test thoroughly**: V4's type safety will catch many issues at development time
7. **Update deployment scripts**: Modify cron jobs and orchestration to use new APIs

.. note::
   For complex migrations, consider running V3 and V4 in parallel during the transition period to validate results match your expectations.

For additional migration support, see the :doc:`../guides/faq` or contact the OpenSTEF community through our `GitHub discussions <https://github.com/OpenSTEF/openstef/discussions>`_.