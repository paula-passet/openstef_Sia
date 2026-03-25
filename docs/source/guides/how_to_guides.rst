How-to Guides
=============

This section provides practical, task-specific guides for implementing OpenSTEF in production environments. These guides focus on specific implementation challenges that go beyond basic tutorials, helping you integrate OpenSTEF with your existing infrastructure and migrate from previous versions.

Setting up Deployment Orchestration
------------------------------------

OpenSTEF is a Python library that requires orchestration for production forecasting workflows. Here are two common deployment approaches.

Simple Cron-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, you can run OpenSTEF tasks directly using cron jobs. The library provides several main task entry points that can be executed from the command line:

.. code-block:: python

   # Train models
   python -m openstef.tasks.train_model

   # Create forecasts
   python -m openstef.tasks.create_forecast

   # Generate basecase forecasts
   python -m openstef.tasks.create_basecase_forecast

   # Optimize hyperparameters
   python -m openstef.tasks.optimize_hyperparameters

Each task requires a TaskContext that manages configuration and database connections:

.. code-block:: python

   from openstef.tasks.utils.taskcontext import TaskContext
   from openstef.tasks.train_model import train_model_task

   # Set up context with your config and database
   with TaskContext("model_training", config=your_config, database=your_db) as context:
       # Run training for specific prediction job
       train_model_task(prediction_job, context, train_period_days=120)

A typical cron schedule might look like:

.. code-block:: bash

   # Train models daily at 2 AM
   0 2 * * * /path/to/python -m openstef.tasks.train_model

   # Create forecasts every 15 minutes
   */15 * * * * /path/to/python -m openstef.tasks.create_forecast

   # Optimize hyperparameters weekly
   0 3 * * 0 /path/to/python -m openstef.tasks.optimize_hyperparameters

Dagster Integration
^^^^^^^^^^^^^^^^^^^

For more sophisticated orchestration with dependency management, monitoring, and scheduling, you can integrate OpenSTEF with Dagster:

.. code-block:: python

   from dagster import asset, job, schedule, ConfigurableResource
   from openstef.tasks.train_model import train_model_task
   from openstef.tasks.create_forecast import create_forecast_task

   class OpenSTEFResource(ConfigurableResource):
       config: dict
       database: object

   @asset
   def trained_models(openstef: OpenSTEFResource, prediction_jobs):
       """Train models for all prediction jobs."""
       with TaskContext("train_models", openstef.config, openstef.database) as context:
           for pj in prediction_jobs:
               train_model_task(pj, context)
       return "models_trained"

   @asset(deps=[trained_models])
   def forecasts(openstef: OpenSTEFResource, prediction_jobs):
       """Generate forecasts using trained models."""
       with TaskContext("create_forecasts", openstef.config, openstef.database) as context:
           for pj in prediction_jobs:
               create_forecast_task(pj, context)
       return "forecasts_created"

   @job
   def forecasting_pipeline():
       forecasts()

   @schedule(cron_schedule="*/15 * * * *", job=forecasting_pipeline)
   def forecast_schedule():
       return {}

Data Integration Patterns
--------------------------

OpenSTEF can integrate with various data storage and processing systems. Here are common integration patterns.

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

For cloud-based deployments, you can integrate OpenSTEF with S3 for model storage and data exchange:

.. code-block:: python

   import boto3
   from openstef.model.serializer import MLflowSerializer

   class S3ModelStorage:
       def __init__(self, bucket_name, region='us-east-1'):
           self.s3_client = boto3.client('s3', region_name=region)
           self.bucket = bucket_name

       def save_model(self, model, model_id):
           """Save trained model to S3."""
           serializer = MLflowSerializer()
           model_data = serializer.serialize(model)
           
           self.s3_client.put_object(
               Bucket=self.bucket,
               Key=f"models/{model_id}/model.pkl",
               Body=model_data
           )

       def load_model(self, model_id):
           """Load model from S3."""
           response = self.s3_client.get_object(
               Bucket=self.bucket,
               Key=f"models/{model_id}/model.pkl"
           )
           
           serializer = MLflowSerializer()
           return serializer.deserialize(response['Body'].read())

   # Use in your forecasting pipeline
   storage = S3ModelStorage('my-openstef-bucket')
   model = storage.load_model('pj_123_latest')

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time series data storage, InfluxDB is a common choice. Here's how to integrate it with OpenSTEF:

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   import pandas as pd

   class InfluxDataProvider:
       def __init__(self, url, token, org, bucket):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.bucket = bucket
           self.org = org

       def get_load_data(self, pj_id, start_time, end_time):
           """Retrieve load data for forecasting."""
           query = f'''
           from(bucket: "{self.bucket}")
               |> range(start: {start_time}, stop: {end_time})
               |> filter(fn: (r) => r["_measurement"] == "load")
               |> filter(fn: (r) => r["pj_id"] == "{pj_id}")
           '''
           
           result = self.client.query_api().query_data_frame(query)
           return result.set_index('_time')['_value']

       def store_forecast(self, pj_id, forecast_data):
           """Store forecast results."""
           write_api = self.client.write_api(write_options=SYNCHRONOUS)
           
           points = []
           for timestamp, value in forecast_data.items():
               point = Point("forecast") \
                   .tag("pj_id", pj_id) \
                   .field("value", float(value)) \
                   .time(timestamp)
               points.append(point)
           
           write_api.write(bucket=self.bucket, org=self.org, record=points)

   # Integration with OpenSTEF workflow
   influx_provider = InfluxDataProvider(
       url="http://localhost:8086",
       token="your-token",
       org="your-org",
       bucket="energy-data"
   )

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For large-scale data processing, you can run OpenSTEF on Databricks:

.. code-block:: python

   # Databricks notebook cell
   from openstef.model.model import OpenstfRegressor
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   import mlflow

   # Enable MLflow tracking
   mlflow.set_tracking_uri("databricks")
   mlflow.set_experiment("/Shared/openstef-forecasting")

   def train_models_spark(prediction_jobs_df):
       """Train models using Spark for parallel processing."""
       
       def train_single_model(pj_data):
           with mlflow.start_run():
               # Load data for this prediction job
               load_data = load_prediction_job_data(pj_data['id'])
               
               # Apply feature engineering
               feature_applicator = TrainFeatureApplicator()
               features = feature_applicator.add_features(load_data)
               
               # Train model
               model = OpenstfRegressor()
               model.fit(features)
               
               # Log model to MLflow
               mlflow.sklearn.log_model(model, "model")
               
               return pj_data['id']
       
       # Use Spark to parallelize training
       results = prediction_jobs_df.rdd.map(train_single_model).collect()
       return results

   # Run training job
   pj_df = spark.table("prediction_jobs")
   trained_models = train_models_spark(pj_df)

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign with improved modularity and flexibility. This section helps you migrate existing V3 implementations.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant changes in V4 include:

- **Modular architecture**: Core functionality split into separate packages (openstef-core, openstef-models, openstef-beam, openstef-meta)
- **Improved type safety**: Full type annotations throughout the codebase
- **Flexible configuration**: Reduced hard-coded assumptions, more customizable behavior
- **Enhanced extensibility**: Clear interfaces for custom models and transformations
- **Better separation of concerns**: Cleaner boundaries between forecasting, evaluation, and deployment logic

Migration Steps
^^^^^^^^^^^^^^^

1. **Update imports**: Many classes have moved to new packages:

.. code-block:: python

   # V3 imports
   from openstef.model.regressors import OpenstfRegressor
   from openstef.validation.validation import ValidationApplication
   
   # V4 imports
   from openstef_models.model.regressors import OpenstfRegressor
   from openstef_beam.validation.validation import ValidationApplication

2. **Update configuration patterns**: V4 uses more structured configuration:

.. code-block:: python

   # V3 style - direct parameter passing
   model = OpenstfRegressor(
       model_type='xgb',
       quantiles=[0.05, 0.5, 0.95]
   )
   
   # V4 style - configuration objects
   from openstef_models.config import ModelConfig
   
   config = ModelConfig(
       model_type='xgb',
       quantiles=[0.05, 0.5, 0.95],
       hyperparameters={'max_depth': 6}
   )
   model = OpenstfRegressor(config=config)

3. **Update feature engineering**: V4 provides more flexible feature engineering:

.. code-block:: python

   # V3 - limited customization
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   
   applicator = TrainFeatureApplicator()
   features = applicator.add_features(data)
   
   # V4 - configurable pipeline
   from openstef_models.preprocessing import FeaturePipeline
   from openstef_models.preprocessing.transformers import WeatherTransformer, LagTransformer
   
   pipeline = FeaturePipeline([
       WeatherTransformer(weather_columns=['temperature', 'wind_speed']),
       LagTransformer(lags=[1, 24, 168])
   ])
   features = pipeline.fit_transform(data)

4. **Update evaluation workflows**: V4 separates evaluation into openstef-beam:

.. code-block:: python

   # V4 evaluation
   from openstef_beam.evaluation import BacktestEvaluator
   from openstef_beam.metrics import MAE, RMSE
   
   evaluator = BacktestEvaluator(
       metrics=[MAE(), RMSE()],
       forecast_horizon_hours=48
   )
   results = evaluator.evaluate(model, test_data)

Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

**Issue**: Import errors for moved classes
**Solution**: Update imports according to the new package structure. Use the migration guide in the V4 release notes.

**Issue**: Configuration validation errors
**Solution**: V4 has stricter type checking. Ensure all configuration parameters match expected types.

**Issue**: Changed API signatures
**Solution**: Some method signatures have changed for consistency. Check the API reference for updated signatures.

.. note::
   For complex migrations, consider running V3 and V4 in parallel initially to validate that forecasting results remain consistent. The openstef-beam package provides tools for comparing model performance across versions.

For detailed migration assistance and community support, see the quickstart guide for V4 setup, or consult the community forums for specific migration questions.