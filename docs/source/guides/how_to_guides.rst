How-to Guides
=============

This section provides practical, task-focused guides for implementing specific OpenSTEF functionality in production environments. These guides assume you're familiar with OpenSTEF basics and focus on real-world deployment scenarios.

Deployment and Orchestration
----------------------------

Setting up Production Forecasting with Cron Jobs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides built-in task modules designed for periodic execution in production environments. The library includes ready-to-use cron job implementations for common forecasting workflows.

.. code-block:: python

   # Basic forecast creation task
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Set up your prediction job configuration
   pj = PredictionJobDataClass(
       id=1,
       name="substation_forecast",
       model_type="xgb",
       resolution_minutes=15
   )
   
   # Create context with database connection
   context = TaskContext(database=your_database_connection)
   
   # Execute forecast task (typically called from cron)
   create_forecast_task(pj, context, t_behind_days=14)

The forecast creation task follows these steps:

1. Retrieves historic training data (TDCV, Load, Weather, day-ahead electricity prices)
2. Applies feature engineering
3. Loads the trained model from persistent storage
4. Makes predictions
5. Writes predictions to database
6. Sends notifications if errors occur

For hyperparameter optimization, use the dedicated task:

.. code-block:: python

   from openstef.tasks.optimize_hyperparameters import optimize_hyperparameters_task
   
   # Run hyperparameter optimization (typically weekly/monthly)
   optimize_hyperparameters_task(pj, context, check_hyper_param_age=True)

.. note::
   Task modules are designed to be called directly from cron jobs. Example cron configurations can be found in the ``/k8s/CronJobs`` folder of the OpenSTEF repository.

Orchestration with Dagster
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more sophisticated workflow orchestration, integrate OpenSTEF tasks with Dagster:

.. code-block:: python

   from dagster import asset, job, schedule
   from openstef.tasks.create_forecast import create_forecast_task
   
   @asset
   def forecast_asset(context):
       """Generate forecasts for all prediction jobs."""
       prediction_jobs = get_prediction_jobs()  # Your implementation
       
       for pj in prediction_jobs:
           task_context = TaskContext(database=context.resources.database)
           create_forecast_task(pj, task_context)
       
       return len(prediction_jobs)
   
   @job
   def daily_forecast_job():
       forecast_asset()
   
   @schedule(
       job=daily_forecast_job,
       cron_schedule="0 6 * * *"  # Daily at 6 AM
   )
   def daily_forecast_schedule(_context):
       return {}

This approach provides better monitoring, retry logic, and dependency management compared to simple cron jobs.

Data Integration
----------------

Integrating with S3 Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF supports S3 integration through the benchmarking storage system, which can be adapted for general data storage:

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   
   # Set up S3 storage with local fallback
   local_storage = LocalBenchmarkStorage(base_path="/tmp/openstef_data")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="your-openstef-bucket",
       s3_prefix="forecasts/",
       s3fs_kwargs={
           "key": "your-access-key",
           "secret": "your-secret-key",
           "endpoint_url": "https://s3.amazonaws.com"
       }
   )
   
   # Use for storing/retrieving forecast results
   forecast_data = create_forecast(model, input_data)
   s3_storage.save_forecast("forecast_20241201.parquet", forecast_data)

Working with InfluxDB
^^^^^^^^^^^^^^^^^^^^^

For time-series data storage and retrieval, integrate OpenSTEF with InfluxDB:

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   import pandas as pd
   
   class InfluxDBDataProvider:
       def __init__(self, url, token, org, bucket):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.bucket = bucket
           self.org = org
       
       def get_load_data(self, pj_id: int, start: str, end: str) -> pd.DataFrame:
           """Retrieve load data for OpenSTEF prediction job."""
           query = f'''
           from(bucket: "{self.bucket}")
               |> range(start: {start}, stop: {end})
               |> filter(fn: (r) => r["_measurement"] == "load")
               |> filter(fn: (r) => r["pj_id"] == "{pj_id}")
               |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
           '''
           
           result = self.client.query_api().query_data_frame(query)
           return result.set_index('_time')
       
       def write_forecast(self, pj_id: int, forecast: pd.DataFrame):
           """Write forecast results back to InfluxDB."""
           points = []
           for timestamp, row in forecast.iterrows():
               point = Point("forecast") \
                   .tag("pj_id", pj_id) \
                   .field("forecast", row['forecast']) \
                   .field("quantile_10", row.get('quantile_10')) \
                   .field("quantile_90", row.get('quantile_90')) \
                   .time(timestamp)
               points.append(point)
           
           self.client.write_api().write(bucket=self.bucket, record=points)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For large-scale data processing with Databricks:

.. code-block:: python

   from databricks import sql
   import pandas as pd
   
   class DatabricksDataProvider:
       def __init__(self, server_hostname, http_path, access_token):
           self.connection = sql.connect(
               server_hostname=server_hostname,
               http_path=http_path,
               access_token=access_token
           )
       
       def get_training_data(self, pj_id: int, days_back: int = 365) -> pd.DataFrame:
           """Retrieve training data from Databricks Delta tables."""
           query = f"""
           SELECT 
               datetime,
               load,
               temperature,
               wind_speed,
               solar_irradiance
           FROM energy_data.forecasting_input
           WHERE pj_id = {pj_id}
             AND datetime >= current_date() - INTERVAL {days_back} DAYS
           ORDER BY datetime
           """
           
           return pd.read_sql(query, self.connection)
       
       def save_forecast_results(self, pj_id: int, forecast: pd.DataFrame):
           """Save forecast results to Delta table."""
           # Convert DataFrame to Spark DataFrame and write
           forecast['pj_id'] = pj_id
           forecast['created_at'] = pd.Timestamp.now()
           
           # Use Delta Lake MERGE for upserts
           forecast.to_sql(
               'energy_data.forecast_results',
               self.connection,
               if_exists='append',
               index=False
           )

Migration from OpenSTEF V3 to V4
---------------------------------

Understanding the V4 Architecture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF V4 represents a major architectural redesign focused on modularity and flexibility. The monolithic V3 structure has been replaced with a modular mono-repo containing specialized packages:

- **openstef-core**: Data types, interfaces, and base classes
- **openstef-models**: Forecasting models and preprocessing pipelines  
- **openstef-meta**: Advanced ensemble models and meta-learning
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics

Key Changes from V3
^^^^^^^^^^^^^^^^^^^^

**Modular Design**: V4 adopts a component-based architecture where each module can work independently:

.. code-block:: python

   # V3 approach - monolithic imports
   from openstef.model.regressors import ARIMAOpenstef
   from openstef.pipeline.train_model import train_model_pipeline
   
   # V4 approach - modular imports
   from openstef_models.regressors import ARIMAModel
   from openstef_models.pipelines import TrainingPipeline
   from openstef_core.data_types import PredictionJob

**Decoupled Dependencies**: External dependencies like MLflow and database connections are now optional and configurable:

.. code-block:: python

   # V4 - flexible configuration
   from openstef_models.config import ModelConfig
   
   config = ModelConfig(
       model_type="xgb",
       mlflow_tracking=False,  # Optional
       custom_features=["temperature_lag_24h"],
       optimization_metric="mae"
   )

**Type Safety**: V4 introduces comprehensive type annotations throughout the codebase:

.. code-block:: python

   from typing import Optional
   from openstef_core.data_types import ForecastResult, PredictionJob
   
   def create_forecast(
       pj: PredictionJob, 
       input_data: pd.DataFrame,
       horizon_hours: int = 48
   ) -> ForecastResult:
       # Fully type-safe implementation
       pass

Migration Steps
^^^^^^^^^^^^^^^

1. **Update Import Statements**: Replace V3 imports with V4 modular equivalents:

.. code-block:: python

   # Before (V3)
   from openstef.model.regressors.xgb import XGBOpenstef
   from openstef.pipeline.create_forecast import make_forecast
   
   # After (V4)  
   from openstef_models.regressors import XGBModel
   from openstef_models.pipelines import ForecastPipeline

2. **Migrate Configuration**: Convert hard-coded parameters to configuration objects:

.. code-block:: python

   # V3 style
   model = XGBOpenstef(
       max_depth=6,
       n_estimators=100,
       subsample=0.8
   )
   
   # V4 style
   from openstef_models.config import XGBConfig
   
   config = XGBConfig(
       max_depth=6,
       n_estimators=100,
       subsample=0.8
   )
   model = XGBModel(config=config)

3. **Update Data Handling**: Use new data type classes for better type safety:

.. code-block:: python

   # V4 data types
   from openstef_core.data_types import PredictionJob, TrainingData
   
   pj = PredictionJob(
       id=1,
       name="substation_forecast",
       model_type="xgb",
       resolution_minutes=15,
       horizon_hours=48
   )
   
   training_data = TrainingData(
       load=load_df,
       weather=weather_df,
       features=feature_df
   )

4. **Migrate Custom Components**: Implement custom models using V4 interfaces:

.. code-block:: python

   from openstef_core.interfaces import BaseModel
   from openstef_core.data_types import ForecastResult
   
   class CustomModel(BaseModel):
       def fit(self, training_data: TrainingData) -> None:
           # Your custom training logic
           pass
       
       def predict(self, input_data: pd.DataFrame) -> ForecastResult:
           # Your custom prediction logic
           pass

.. warning::
   V4 introduces breaking changes in API design. Thoroughly test your migration with the new interfaces before deploying to production.

For detailed migration assistance and community support, visit the `OpenSTEF GitHub discussions <https://github.com/OpenSTEF/openstef/discussions>`_ or join our community channels.