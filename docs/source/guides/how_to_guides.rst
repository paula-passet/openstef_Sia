How-To Guides
=============

This section provides practical, task-specific guides for implementing OpenSTEF in production environments. These guides focus on specific deployment patterns, data integrations, and migration scenarios that go beyond the basic tutorials.

Setting Up Production Deployments
----------------------------------

OpenSTEF is a Python machine learning library that can be deployed in various ways depending on your infrastructure and orchestration preferences. Here are the most common deployment patterns.

Simple Cron-Based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, OpenSTEF tasks can be executed directly via cron jobs. This approach works well for smaller-scale implementations or when you need minimal infrastructure overhead.

.. code-block:: python

   # Example cron task execution
   from openstef.tasks.create_forecast import main as create_forecast
   from openstef.tasks.train_model import main as train_model
   
   # Configuration and database objects (from openstef-dbc)
   config = ConfigManager()
   database = DatabaseConnection()
   
   # Execute forecasting task
   create_forecast(config=config, database=database)
   
   # Execute training task periodically
   train_model(config=config, database=database)

The OpenSTEF repository includes example cron job configurations in the ``/k8s/CronJobs`` folder that demonstrate how to schedule tasks like wind forecasting, hyperparameter optimization, and model training.

Orchestration with Dagster
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more complex workflows requiring dependency management, monitoring, and retry logic, Dagster provides excellent integration with OpenSTEF:

.. code-block:: python

   from dagster import asset, Config, OpExecutionContext
   from openstef.tasks.utils.taskcontext import TaskContext
   from openstef.tasks.create_forecast import make_forecast_pj
   
   class ForecastConfig(Config):
       prediction_job_id: int
       forecast_horizon_hours: int = 48
   
   @asset
   def daily_forecast(context: OpExecutionContext, config: ForecastConfig):
       """Generate daily energy forecast using OpenSTEF."""
       
       with TaskContext("daily_forecast") as task_context:
           # Load prediction job configuration
           pj = task_context.database.get_prediction_job(config.prediction_job_id)
           
           # Generate forecast
           make_forecast_pj(pj, task_context)
           
           context.log.info(f"Forecast completed for PJ {config.prediction_job_id}")

This pattern allows you to build complex forecasting pipelines with proper dependency tracking and monitoring.

Data Integration Patterns
-------------------------

OpenSTEF supports various data sources and storage backends through flexible integration patterns. The library separates data retrieval/storage from the core forecasting logic, enabling integration with diverse systems.

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

For cloud-based deployments, OpenSTEF provides built-in S3 integration through the benchmarking storage system:

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   
   # Set up hybrid local/S3 storage
   local_storage = LocalBenchmarkStorage(base_path="./benchmarks")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="my-openstef-bucket",
       s3_prefix="forecasting-results/",
       s3fs_kwargs={"key": "access_key", "secret": "secret_key"}
   )
   
   # Storage automatically syncs to S3 after local writes
   s3_storage.store_evaluation_report(target_metadata, report)

This hybrid approach ensures fast local access while providing cloud backup and sharing capabilities.

InfluxDB Time Series Data
^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF integrates with InfluxDB for time series data storage through the openstef-dbc package:

.. code-block:: python

   # Database configuration (requires openstef-dbc)
   from openstef_dbc import InfluxDBConnector
   
   # Configure InfluxDB connection
   influx_config = {
       'host': 'localhost',
       'port': 8086,
       'database': 'openstef_timeseries',
       'username': 'forecaster',
       'password': 'password'
   }
   
   connector = InfluxDBConnector(**influx_config)
   
   # Use with TaskContext for automatic connection management
   with TaskContext("forecast_task", database=connector) as context:
       # OpenSTEF tasks automatically use the database connection
       # for reading input data and writing forecast results
       pass

The InfluxDB integration handles both feature data (weather, load, prices) and forecast output storage with automatic time series optimization.

Custom Data Source Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For organizations with existing data infrastructure, you can implement custom data providers:

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import TrainModelPipeline
   import pandas as pd
   
   def custom_data_provider(pj: PredictionJobDataClass, 
                           start_time: pd.Timestamp, 
                           end_time: pd.Timestamp) -> pd.DataFrame:
       """Custom data retrieval from your existing systems."""
       
       # Example: Databricks integration
       from databricks import sql
       
       connection = sql.connect(
           server_hostname="your-workspace.cloud.databricks.com",
           http_path="/sql/1.0/warehouses/your-warehouse-id",
           access_token="your-access-token"
       )
       
       query = f"""
       SELECT timestamp, load, temperature, wind_speed
       FROM energy_data 
       WHERE prediction_job_id = {pj.id}
         AND timestamp BETWEEN '{start_time}' AND '{end_time}'
       ORDER BY timestamp
       """
       
       return pd.read_sql(query, connection)
   
   # Use custom data provider with OpenSTEF pipelines
   pipeline = TrainModelPipeline()
   input_data = custom_data_provider(prediction_job, train_start, train_end)
   trained_model = pipeline.run(input_data, prediction_job)

This pattern allows integration with any data source while leveraging OpenSTEF's forecasting capabilities.

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity, flexibility, and enterprise integration. The migration requires understanding key changes and following a structured approach.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The V4 architecture introduces several breaking changes:

- **Modular mono-repo structure**: Core functionality split into ``openstef-core``, ``openstef-models``, ``openstef-meta``, and ``openstef-beam`` packages
- **Decoupled dependencies**: External dependencies like MLFlow and xgboost are now optional and configurable
- **Type safety**: Full type annotations throughout the codebase
- **Flexible configuration**: Hard-coded assumptions replaced with configurable parameters
- **Enhanced data validation**: Improved data preprocessing and validation pipelines

Migration Strategy
^^^^^^^^^^^^^^^^^^

Follow this step-by-step approach to migrate existing V3 implementations:

1. **Assessment Phase**:

.. code-block:: python

   # V3 code example
   from openstef.tasks import create_forecast
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   
   # Direct task execution (V3 pattern)
   create_forecast.main(config, database)

2. **V4 Migration**:

.. code-block:: python

   # V4 equivalent with modular approach
   from openstef_core.data_classes import PredictionJobDataClass
   from openstef_models.regressors import XGBQuantileRegressor
   from openstef.pipeline.create_forecast import CreateForecastPipeline
   
   # Pipeline-based execution (V4 pattern)
   pipeline = CreateForecastPipeline()
   forecast = pipeline.run(input_data, prediction_job)

3. **Configuration Updates**:

.. code-block:: python

   # V3: Hard-coded model parameters
   model = XGBQuantileOpenstfRegressor()  # Fixed configuration
   
   # V4: Flexible configuration
   from openstef_models.config import ModelConfig
   
   config = ModelConfig(
       model_type="xgb_quantile",
       quantiles=[0.1, 0.5, 0.9],
       hyperparameters={"n_estimators": 100, "max_depth": 6}
   )
   model = XGBQuantileRegressor(config)

4. **Data Pipeline Migration**:

.. code-block:: python

   # V4 introduces explicit data validation
   from openstef_core.validation import DataValidator
   from openstef_models.preprocessing import FeatureEngineer
   
   validator = DataValidator()
   feature_engineer = FeatureEngineer()
   
   # Explicit validation and preprocessing steps
   validated_data = validator.validate(raw_data, prediction_job)
   features = feature_engineer.create_features(validated_data, prediction_job)

Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

Based on feedback from early adopters, these are the most common migration challenges:

**Import Path Changes**: Many modules have moved between packages. Use the V4 migration guide to map old imports to new locations.

**Configuration Format**: V3's implicit configuration is replaced with explicit config objects. Review your prediction job configurations and update them to use the new format.

**Database Interface**: The database abstraction layer has changed. Update your database connection code to use the new ``openstef-dbc`` interfaces.

**Model Storage**: MLFlow integration is now optional. If you're using custom model storage, implement the new storage interface.

.. note::
   The V4 migration is substantial but provides significant benefits in terms of flexibility and maintainability. Start with a pilot implementation to validate the migration approach before converting your entire system.

For detailed migration assistance, consult the :doc:`../reference/changelog` for breaking changes and the community forums for specific migration questions.