How-To Guides
=============

This section provides practical, task-oriented guides for implementing specific OpenSTEF functionality in production environments. These guides focus on real-world deployment scenarios and system integrations that extend beyond the basic tutorials.

Setting up Production Deployment
---------------------------------

OpenSTEF is a Python library designed to integrate into your existing forecasting infrastructure. Here are common deployment patterns for running forecasting tasks in production.

Simple Cron-based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For straightforward deployments, you can run OpenSTEF tasks using standard cron jobs. This approach works well for small to medium-scale operations with predictable scheduling requirements.

.. code-block:: python

   # model_train_job.py
   from openstef.tasks.train_model import main as train_model_main
   from openstef.tasks.utils.taskcontext import TaskContext
   
   def run_training_job():
       """Run model training with proper context management."""
       with TaskContext(
           name="model_training",
           config=your_config_object,
           database=your_database_connection
       ) as context:
           train_model_main(
               model_type=None,  # Train all model types
               config=context.config,
               database=context.database
           )
   
   if __name__ == "__main__":
       run_training_job()

Create a cron job to run this script:

.. code-block:: bash

   # Run model training daily at 2 AM
   0 2 * * * /usr/bin/python /path/to/model_train_job.py
   
   # Run forecast creation every 15 minutes
   */15 * * * * /usr/bin/python /path/to/create_forecast_job.py

The TaskContext manager handles error reporting, logging, and cleanup automatically. Set ``suppress_exceptions=False`` to ensure cron receives proper exit codes for monitoring.

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^

For more sophisticated workflow orchestration, OpenSTEF integrates well with Dagster. The modular design of OpenSTEF V4 makes it easy to create Dagster assets and jobs.

.. code-block:: python

   from dagster import asset, job, op, Config
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.data.time_series_dataset import TimeSeriesDataset
   
   class ForecastConfig(Config):
       model_id: str
       forecast_horizon_hours: int = 48
   
   @asset
   def training_data() -> TimeSeriesDataset:
       """Load and prepare training data."""
       # Your data loading logic here
       return TimeSeriesDataset(...)
   
   @asset
   def trained_model(training_data: TimeSeriesDataset, config: ForecastConfig):
       """Train forecasting model."""
       workflow = CustomForecastingWorkflow(
           model_id=config.model_id,
           # Configure your workflow
       )
       workflow.fit(training_data)
       return workflow
   
   @asset
   def forecast(trained_model: CustomForecastingWorkflow, 
                forecast_data: TimeSeriesDataset) -> TimeSeriesDataset:
       """Generate forecast predictions."""
       return trained_model.predict(forecast_data)
   
   @job(config=ForecastConfig)
   def forecasting_job():
       forecast(trained_model(training_data()), forecast_data())

This approach provides dependency tracking, retry logic, and monitoring capabilities that scale with your operational needs.

Data Integration Patterns
--------------------------

OpenSTEF V4's modular architecture supports integration with various data sources and storage systems. Here are common integration patterns.

S3 Integration for Model Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the S3 storage backend for distributed model artifacts and benchmark results:

.. code-block:: python

   from openstef_beam.benchmarking.storage.s3_storage import S3BenchmarkStorage
   from openstef_models.integrations.mlflow.mlflow_storage import MLFlowStorage
   
   # Configure S3 storage for benchmarking results
   s3_storage = S3BenchmarkStorage(
       bucket_name="your-openstef-bucket",
       local_cache_dir="/tmp/openstef_cache",
       s3_prefix="benchmarks/"
   )
   
   # Configure MLflow with S3 backend
   mlflow_storage = MLFlowStorage(
       tracking_uri="s3://your-mlflow-bucket/mlruns",
       experiment_name="energy_forecasting"
   )
   
   # Use in your workflow
   workflow = CustomForecastingWorkflow(
       model_id="substation_001",
       storage_backend=mlflow_storage
   )

MLflow Integration
^^^^^^^^^^^^^^^^^^

Track experiments and model versions using MLflow integration:

.. code-block:: python

   from openstef_models.integrations.mlflow.mlflow_storage_callback import MLFlowStorageCallback
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   
   # Configure MLflow callback
   mlflow_callback = MLFlowStorageCallback(
       tracking_uri="http://your-mlflow-server:5000",
       experiment_name="production_forecasts"
   )
   
   # Add callback to workflow
   workflow = CustomForecastingWorkflow(
       model_id="grid_point_123",
       callbacks=[mlflow_callback]
   )
   
   # Training and prediction runs are automatically logged
   workflow.fit(training_data)
   predictions = workflow.predict(forecast_data)

Database Integration
^^^^^^^^^^^^^^^^^^^^

For custom database backends, implement the data provider interface:

.. code-block:: python

   from openstef_core.data.base import DataProvider
   from openstef_models.data.time_series_dataset import TimeSeriesDataset
   import pandas as pd
   
   class InfluxDBProvider(DataProvider):
       def __init__(self, client, database_name):
           self.client = client
           self.database_name = database_name
       
       def get_load_data(self, start_time, end_time, location_id):
           """Fetch load data from InfluxDB."""
           query = f"""
           SELECT mean("load") as load
           FROM "energy_measurements"
           WHERE "location_id" = '{location_id}'
           AND time >= '{start_time}' AND time <= '{end_time}'
           GROUP BY time(15m)
           """
           result = self.client.query(query, database=self.database_name)
           df = pd.DataFrame(result.get_points())
           return TimeSeriesDataset(df)
       
       def get_weather_data(self, start_time, end_time, location_id):
           """Fetch weather data from InfluxDB."""
           # Similar implementation for weather data
           pass

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity and flexibility. This section guides you through the migration process.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant changes in V4 include:

- **Modular package structure**: Core functionality split into focused packages (openstef-core, openstef-models, openstef-beam, openstef-meta)
- **Workflow-based API**: Replaced task-based approach with composable workflows
- **Type safety**: Full type annotations throughout the codebase
- **Decoupled dependencies**: External systems (MLflow, databases) are now optional integrations

Migration Strategy
^^^^^^^^^^^^^^^^^^

Start by identifying your current V3 usage patterns:

.. code-block:: python

   # V3 approach - task-based
   from openstef.tasks.train_model import train_model_task
   from openstef.tasks.create_basecase_forecast import create_basecase_forecast_task
   
   # Direct task execution
   train_model_task(prediction_job, context)
   create_basecase_forecast_task(prediction_job, context)

Migrate to V4 workflow-based approach:

.. code-block:: python

   # V4 approach - workflow-based
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.data.time_series_dataset import TimeSeriesDataset
   
   # Create workflow instance
   workflow = CustomForecastingWorkflow(
       model_id="your_model_id",
       # Configure based on your prediction job settings
   )
   
   # Train and predict
   workflow.fit(training_data)
   forecast = workflow.predict(forecast_data)

Data Structure Migration
^^^^^^^^^^^^^^^^^^^^^^^^

V4 introduces standardized data structures. Migrate your data handling:

.. code-block:: python

   # V3 - Direct pandas DataFrame usage
   import pandas as pd
   load_data = pd.DataFrame(...)  # Your load data
   
   # V4 - Use TimeSeriesDataset
   from openstef_models.data.time_series_dataset import TimeSeriesDataset
   
   # Convert existing DataFrames
   dataset = TimeSeriesDataset(
       data=load_data,
       target_column="load",
       datetime_column="datetime"
   )

Configuration Migration
^^^^^^^^^^^^^^^^^^^^^^^

V4 uses Pydantic models for configuration instead of dictionary-based configs:

.. code-block:: python

   # V3 configuration (dictionary-based)
   config = {
       "model_type": "xgb",
       "horizon_hours": 48,
       "feature_names": ["temperature", "wind_speed"]
   }
   
   # V4 configuration (type-safe)
   from openstef_models.config.model_config import ModelConfig
   
   config = ModelConfig(
       model_type="xgb",
       horizon_hours=48,
       feature_names=["temperature", "wind_speed"]
   )

.. note::
   Migration from V3 to V4 requires updating both code structure and data handling patterns. Start with a small subset of your forecasting jobs to validate the migration approach before applying it system-wide.

For detailed migration examples and troubleshooting, see the V4 migration guide in our GitHub repository.