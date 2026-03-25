How-To Guides
=============

This section provides practical, task-specific guides for implementing OpenSTEF in production environments. These guides focus on specific implementation challenges that go beyond the basic tutorials, helping you integrate OpenSTEF into your existing infrastructure and workflows.

Setting Up Production Deployment
---------------------------------

Simple Cron Job Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most straightforward way to deploy OpenSTEF for regular forecasting is using cron jobs. OpenSTEF provides several task modules designed to run as scheduled jobs:

.. code-block:: python

   # Example cron job setup for model training
   from openstef.tasks.train_model import main as train_model_main
   from openstef.tasks.create_basecase_forecast import main as forecast_main
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Train models weekly (runs every Sunday at 2 AM)
   # 0 2 * * 0 python -c "from openstef.tasks.train_model import main; main()"
   
   # Create forecasts every 15 minutes
   # */15 * * * * python -c "from openstef.tasks.create_basecase_forecast import main; main()"

Each task uses a ``TaskContext`` to manage database connections and configuration:

.. code-block:: python

   from openstef.tasks.utils.taskcontext import TaskContext
   
   def run_forecast_task():
       with TaskContext("forecast_task", config=my_config, database=my_db) as context:
           # Your forecasting logic here
           create_basecase_forecast_task(pj, context, t_ahead_days=14)

.. note::
   The ``TaskContext`` automatically handles exception logging, database connection management, and optional Teams notifications for production monitoring.

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^^

For more sophisticated orchestration needs, you can integrate OpenSTEF with Dagster to create data pipelines with dependency management, monitoring, and scheduling:

.. code-block:: python

   from dagster import op, job, schedule, DailyPartitionsDefinition
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   @op
   def train_models(context):
       """Train models for all prediction jobs."""
       # Load your prediction jobs and data
       for pj in prediction_jobs:
           model = train_model_pipeline(pj, training_data)
           context.log.info(f"Trained model for PJ {pj.id}")
   
   @op
   def create_forecasts(context):
       """Generate forecasts using trained models."""
       for pj in prediction_jobs:
           forecast = create_forecast_pipeline(pj, input_data)
           # Store forecast to your database
           context.log.info(f"Created forecast for PJ {pj.id}")
   
   @job(partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"))
   def forecasting_pipeline():
       create_forecasts(train_models())
   
   @schedule(job=forecasting_pipeline, cron_schedule="0 6 * * *")
   def daily_forecast_schedule(_context):
       return {}

This approach provides better observability, retry mechanisms, and dependency management compared to simple cron jobs.

Data Integration Patterns
--------------------------

AWS S3 Integration
^^^^^^^^^^^^^^^^^^

OpenSTEF can integrate with S3 for both input data retrieval and forecast storage. Here's a pattern for loading training data from S3 and storing results:

.. code-block:: python

   import boto3
   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   
   def train_with_s3_data(bucket_name, data_key, pj):
       # Load training data from S3
       s3 = boto3.client('s3')
       obj = s3.get_object(Bucket=bucket_name, Key=data_key)
       training_data = pd.read_parquet(obj['Body'])
       
       # Train model
       model = train_model_pipeline(pj, training_data)
       
       # Store model artifacts back to S3
       model_key = f"models/{pj.id}/model_{pd.Timestamp.now().strftime('%Y%m%d')}.pkl"
       s3.put_object(
           Bucket=bucket_name,
           Key=model_key,
           Body=pickle.dumps(model)
       )
       
       return model

For benchmarking workflows, OpenSTEF provides built-in S3 storage support:

.. code-block:: python

   from openstef_beam.benchmarking.storage.s3_storage import S3BenchmarkStorage
   
   # Configure S3 storage for benchmark results
   storage = S3BenchmarkStorage(
       bucket_name="my-benchmark-bucket",
       local_path="/tmp/benchmarks"
   )
   
   # Storage automatically syncs local results to S3
   storage.save_backtest_output(target, predictions)
   storage.save_evaluation_output(target, evaluation_report)

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time series databases like InfluxDB, you can create custom data adapters:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   
   class InfluxDataProvider:
       def __init__(self, url, token, org, bucket):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.bucket = bucket
           self.org = org
       
       def get_load_data(self, pj, start_time, end_time):
           """Retrieve load data for a prediction job."""
           query = f'''
           from(bucket: "{self.bucket}")
               |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
               |> filter(fn: (r) => r["_measurement"] == "load")
               |> filter(fn: (r) => r["pj_id"] == "{pj.id}")
           '''
           
           result = self.client.query_api().query_data_frame(query, org=self.org)
           return result.set_index('_time')['_value']
       
       def store_forecast(self, pj, forecast_df):
           """Store forecast results to InfluxDB."""
           write_api = self.client.write_api()
           
           for timestamp, row in forecast_df.iterrows():
               point = Point("forecast") \
                   .tag("pj_id", pj.id) \
                   .field("forecast", row['forecast']) \
                   .field("quantile_10", row.get('quantile_10', None)) \
                   .field("quantile_90", row.get('quantile_90', None)) \
                   .time(timestamp)
               
               write_api.write(bucket=self.bucket, org=self.org, record=point)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For Databricks environments, you can leverage Delta Lake for data storage and Databricks workflows for orchestration:

.. code-block:: python

   from pyspark.sql import SparkSession
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   def databricks_forecast_job():
       spark = SparkSession.builder.appName("OpenSTEF-Forecast").getOrCreate()
       
       # Read input data from Delta Lake
       input_df = spark.read.format("delta").load("/path/to/input/data")
       input_pandas = input_df.toPandas()
       
       # Create forecasts
       forecasts = []
       for pj in prediction_jobs:
           forecast = create_forecast_pipeline(pj, input_pandas)
           forecast['pj_id'] = pj.id
           forecasts.append(forecast)
       
       # Combine and write back to Delta Lake
       all_forecasts = pd.concat(forecasts)
       spark_df = spark.createDataFrame(all_forecasts)
       spark_df.write.format("delta").mode("overwrite").save("/path/to/forecasts")

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity and flexibility. Here are the key migration considerations:

Breaking Changes and New Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 introduces a modular mono-repo structure with separate packages:

- ``openstef-core``: Base classes and interfaces
- ``openstef-models``: Forecasting models and preprocessing
- ``openstef-meta``: Advanced ensemble models
- ``openstef-beam``: Backtesting and evaluation tools

.. code-block:: python

   # V3 approach
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # V4 approach - more modular imports
   from openstef_models.regressors import XGBRegressor
   from openstef_models.preprocessing import FeatureEngineer

Configuration and Context Changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 moves away from hard-coded assumptions toward flexible configuration:

.. code-block:: python

   # V3: Hard-coded database and configuration
   from openstef.tasks.train_model import train_model_task
   
   # V4: Explicit configuration and context management
   from openstef.tasks.utils.taskcontext import TaskContext
   from openstef_models.workflows import TrainingWorkflow
   
   # More explicit configuration in V4
   config = {
       'model_type': 'xgb',
       'feature_modules': ['weather', 'calendar', 'lag'],
       'training_period_days': 120
   }
   
   with TaskContext("training", config=config, database=db) as context:
       workflow = TrainingWorkflow(config)
       model = workflow.train(pj, training_data)

Pipeline API Updates
^^^^^^^^^^^^^^^^^^^^

V4 provides more flexible pipeline interfaces:

.. code-block:: python

   # V3: Fixed pipeline structure
   from openstef.pipeline.train_model import train_model_pipeline
   
   # V4: Configurable workflows
   from openstef_models.workflows import create_workflow
   
   # V4 allows custom workflow composition
   workflow = create_workflow({
       'preprocessing': ['outlier_detection', 'feature_engineering'],
       'model': 'xgb_quantile',
       'postprocessing': ['clip_negative']
   })
   
   result = workflow.run(pj, input_data)

Migration Strategy
^^^^^^^^^^^^^^^^^^

1. **Start with V4 presets**: Use the preset configurations that match your V3 setup
2. **Gradual migration**: Migrate one prediction job at a time to validate results
3. **Test thoroughly**: Use the benchmarking tools in ``openstef-beam`` to compare V3 and V4 performance
4. **Update integrations**: Modify your orchestration code to use the new modular imports

.. warning::
   V4 is a major release with breaking changes. Plan for thorough testing and validation of your forecasting accuracy before deploying to production.

For detailed migration examples and troubleshooting, see the tutorials section which includes V4-specific examples and best practices.