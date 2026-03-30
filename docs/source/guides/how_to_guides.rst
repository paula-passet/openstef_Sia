How-To Guides
=============

This section provides task-specific implementation guides for common OpenSTEF deployment scenarios and integrations. These guides focus on practical implementation details for specific tasks that go beyond the basic tutorials.

Setting Up Production Deployments
----------------------------------

OpenSTEF provides several deployment patterns depending on your infrastructure and orchestration preferences.

Simple Cron-Based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, OpenSTEF tasks can be executed directly via cron jobs. The library includes several pre-built task modules designed for this purpose:

.. code-block:: python

   # Example: Direct task execution for forecasting
   from openstef.tasks.create_forecast import main as create_forecast
   from openstef.tasks.train_model import main as train_model
   
   # Train models (typically run daily or weekly)
   train_model(config=your_config, database=your_db)
   
   # Create forecasts (typically run every 15 minutes)
   create_forecast(config=your_config, database=your_db)

Each task uses a ``TaskContext`` that manages database connections and error handling:

.. code-block:: python

   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Tasks automatically handle context management
   with TaskContext("forecast_task", config, database) as context:
       # Task logic runs here with proper error handling
       # and automatic Teams notifications on failure
       pass

The cron job approach works well for smaller deployments where you need reliable, scheduled execution without complex orchestration requirements.

Dagster Integration
^^^^^^^^^^^^^^^^^^^

For more sophisticated workflow orchestration, OpenSTEF integrates well with Dagster. The modular pipeline design allows you to compose forecasting workflows as Dagster assets:

.. code-block:: python

   from dagster import asset, Config
   from openstef.pipelines.train_model import train_model_pipeline
   from openstef.pipelines.create_forecast import create_forecast_pipeline
   
   class ForecastConfig(Config):
       prediction_job_id: int
       horizon_minutes: int = 2880
   
   @asset
   def trained_model(config: ForecastConfig):
       """Train and persist a forecasting model."""
       return train_model_pipeline(
           prediction_job=get_prediction_job(config.prediction_job_id),
           input_data=load_training_data()
       )
   
   @asset(deps=[trained_model])
   def forecast(config: ForecastConfig):
       """Generate forecast using trained model."""
       return create_forecast_pipeline(
           prediction_job=get_prediction_job(config.prediction_job_id),
           input_data=load_forecast_data()
       )

This approach provides better dependency management, monitoring, and retry capabilities compared to simple cron jobs.

Data Integration Patterns
--------------------------

OpenSTEF supports various data sources through flexible integration patterns. The key is implementing the appropriate data connectors for your infrastructure.

S3 Integration
^^^^^^^^^^^^^^

For cloud-based deployments, OpenSTEF includes S3 storage capabilities through the benchmarking framework:

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   
   # Configure S3 storage with local caching
   local_storage = LocalBenchmarkStorage(base_path="/tmp/openstef")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="your-openstef-bucket",
       s3_prefix="forecasts/",
       s3fs_kwargs={
           "key": "your-aws-access-key",
           "secret": "your-aws-secret-key",
           "endpoint_url": "https://s3.amazonaws.com"
       }
   )
   
   # Storage automatically syncs local files to S3
   s3_storage.save_backtest_output(target, forecast_results)

The hybrid approach ensures fast local access while maintaining cloud persistence.

Custom Database Connectors
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For enterprise deployments with existing data infrastructure, implement custom data providers:

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipelines.train_model import train_model_pipeline
   import pandas as pd
   
   class CustomDataProvider:
       def __init__(self, connection_string):
           self.connection = create_connection(connection_string)
       
       def get_training_data(self, pj: PredictionJobDataClass) -> pd.DataFrame:
           """Fetch training data from your data warehouse."""
           query = f"""
           SELECT datetime, load, temperature, wind_speed
           FROM energy_data 
           WHERE location_id = {pj.id}
           AND datetime >= NOW() - INTERVAL '2 years'
           """
           return pd.read_sql(query, self.connection)
       
       def save_forecast(self, pj: PredictionJobDataClass, forecast: pd.DataFrame):
           """Save forecast results to your database."""
           forecast.to_sql(
               f"forecasts_{pj.id}", 
               self.connection, 
               if_exists="append"
           )

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

For time series databases like InfluxDB, leverage the time series dataset interfaces:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset
   
   class InfluxDBConnector:
       def __init__(self, url, token, org, bucket):
           self.client = InfluxDBClient(url=url, token=token, org=org)
           self.bucket = bucket
       
       def load_timeseries(self, measurement: str, start: str, stop: str) -> pd.DataFrame:
           """Load time series data from InfluxDB."""
           query = f'''
           from(bucket: "{self.bucket}")
               |> range(start: {start}, stop: {stop})
               |> filter(fn: (r) => r["_measurement"] == "{measurement}")
           '''
           result = self.client.query_api().query_data_frame(query)
           return result.pivot(index="_time", columns="_field", values="_value")

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 introduces significant architectural changes that require careful migration planning. The key changes affect how you structure your forecasting workflows and integrate with external systems.

Core Architectural Changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^

V4 adopts a modular mono-repo structure with distinct packages:

- ``openstef-core``: Data types and base interfaces
- ``openstef-models``: Forecasting models and preprocessing  
- ``openstef-beam``: Backtesting and evaluation framework
- ``openstef-meta``: Advanced ensemble models

Migration typically involves updating import statements and workflow organization:

.. code-block:: python

   # V3 approach
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   
   # V4 approach  
   from openstef_models.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.workflows import TrainingWorkflow

Configuration Updates
^^^^^^^^^^^^^^^^^^^^^

V4 introduces more flexible configuration patterns. Update your prediction job configurations:

.. code-block:: python

   # V3 prediction job structure
   pj_v3 = {
       "id": 123,
       "model": "xgb",
       "quantiles": [0.1, 0.5, 0.9],
       "feature_names": ["load_7d", "temp", "wind"]
   }
   
   # V4 prediction job structure
   from openstef_core.data_classes import PredictionJobDataClass
   
   pj_v4 = PredictionJobDataClass(
       id=123,
       model_type="xgb_quantile",
       quantiles=[0.1, 0.5, 0.9],
       feature_modules=["weather", "lagged_load"],
       horizon_minutes=2880
   )

Pipeline Refactoring
^^^^^^^^^^^^^^^^^^^^

V4 separates tasks (database integration) from pipelines (pure ML logic). Migrate your workflows accordingly:

.. code-block:: python

   # V3 task-based approach
   from openstef.tasks.create_forecast import create_forecast_task
   create_forecast_task(pj, context)
   
   # V4 pipeline-based approach
   from openstef_models.workflows import ForecastingWorkflow
   
   workflow = ForecastingWorkflow(pj)
   forecast = workflow.create_forecast(input_data)
   
   # Separate data persistence logic
   your_data_connector.save_forecast(pj, forecast)

This separation improves testability and allows better integration with different orchestration systems.

.. note::
   
   V4 migration requires updating both code structure and deployment patterns. Start with a pilot project to validate the new architecture before migrating production systems. The V4 documentation provides detailed migration examples for common scenarios.

For complex migration scenarios or enterprise deployments, consider the migration support resources available through the OpenSTEF community channels listed in the main documentation.