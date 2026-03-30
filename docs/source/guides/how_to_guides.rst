How-to Guides
=============

This page provides practical guides for specific implementation tasks with the OpenSTEF library. These guides focus on real-world deployment scenarios and integration patterns that go beyond the basic tutorials.

Setting up Deployment Orchestration
------------------------------------

Simple Cron Job Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most straightforward way to deploy OpenSTEF forecasting is using cron jobs. OpenSTEF tasks are designed to be called directly from cron jobs for production scheduling.

.. code-block:: python

   # forecast_runner.py
   from openstef.tasks.create_forecast import main as create_forecast
   from openstef.tasks.train_model import main as train_model
   import logging

   def run_daily_forecast():
       """Run daily forecasting task"""
       try:
           # Train models weekly (add logic to check if training is needed)
           train_model(config=config, database=database)
           
           # Create forecasts daily
           create_forecast(config=config, database=database)
           
       except Exception as e:
           logging.error(f"Forecast task failed: {e}")
           # Add notification logic here

   if __name__ == "__main__":
       run_daily_forecast()

Add this to your crontab for daily execution:

.. code-block:: bash

   # Run forecasts daily at 6 AM
   0 6 * * * /path/to/python /path/to/forecast_runner.py

   # Train models weekly on Sunday at 2 AM
   0 2 * * 0 /path/to/python -c "from forecast_runner import train_model; train_model()"

Kubernetes CronJob Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For more robust production deployments, use Kubernetes CronJobs. OpenSTEF includes example CronJob configurations in the `/k8s/CronJobs` folder.

.. code-block:: yaml

   # forecast-cronjob.yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: openstef-forecast
   spec:
     schedule: "0 6 * * *"  # Daily at 6 AM
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: forecast
               image: your-registry/openstef-runner:latest
               command: ["python", "-m", "openstef.tasks.create_forecast"]
               env:
               - name: DATABASE_URL
                 valueFrom:
                   secretKeyRef:
                     name: openstef-secrets
                     key: database-url
             restartPolicy: OnFailure

Dagster Orchestration
^^^^^^^^^^^^^^^^^^^^^^

For complex workflows with dependencies and monitoring, integrate OpenSTEF with Dagster:

.. code-block:: python

   from dagster import op, job, schedule, DailyPartitionsDefinition
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   @op
   def train_models():
       """Train OpenSTEF models"""
       # Configure your prediction jobs
       prediction_jobs = get_prediction_jobs()  # Your implementation
       
       for pj in prediction_jobs:
           train_model_pipeline(pj, input_data=get_training_data(pj))

   @op
   def create_forecasts():
       """Generate forecasts using trained models"""
       prediction_jobs = get_prediction_jobs()
       
       for pj in prediction_jobs:
           create_forecast_pipeline(pj, input_data=get_recent_data(pj))

   @job(partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"))
   def openstef_workflow():
       create_forecasts(train_models())

   @schedule(job=openstef_workflow, cron_schedule="0 6 * * *")
   def daily_forecast_schedule(_context):
       return {}

Data Integration Patterns
--------------------------

S3 Integration
^^^^^^^^^^^^^^

OpenSTEF supports S3 integration through the `S3BenchmarkStorage` class for storing benchmark results and model artifacts:

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   import boto3

   # Set up S3 storage for benchmarks and models
   local_storage = LocalBenchmarkStorage("/tmp/openstef_cache")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="your-openstef-bucket",
       s3_prefix="benchmarks/",
       s3fs_kwargs={
           "key": "your-access-key",
           "secret": "your-secret-key",
           "endpoint_url": "https://s3.amazonaws.com"
       }
   )

   # Use in your forecasting workflow
   def store_forecast_results(forecast_data, model_name):
       """Store forecast results and model artifacts to S3"""
       s3_storage.store_benchmark_result(
           model_name=model_name,
           data=forecast_data,
           metadata={"timestamp": datetime.now().isoformat()}
       )

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

OpenSTEF integrates with InfluxDB through the `openstef-dbc` package for time-series data storage:

.. code-block:: python

   # Requires openstef-dbc package
   from openstef_dbc.database import DataBase
   from openstef.tasks.utils.taskcontext import TaskContext

   # Configure InfluxDB connection
   database_config = {
       "influxdb": {
           "host": "your-influxdb-host",
           "port": 8086,
           "database": "energy_forecasts",
           "username": "your-username",
           "password": "your-password"
       }
   }

   def run_forecast_with_influxdb():
       """Run forecasting with InfluxDB data storage"""
       database = DataBase(database_config)
       
       with TaskContext("forecast_task", config=None, database=database) as context:
           # Your forecasting logic here
           # Data will be automatically read from and written to InfluxDB
           from openstef.tasks.create_forecast import create_forecast_task
           
           prediction_jobs = context.database.get_prediction_jobs()
           for pj in prediction_jobs:
               create_forecast_task(pj, context)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^

For large-scale data processing, integrate OpenSTEF with Databricks:

.. code-block:: python

   from pyspark.sql import SparkSession
   from openstef.pipeline.train_model import train_model_pipeline
   import pandas as pd

   def run_openstef_on_databricks():
       """Run OpenSTEF training on Databricks cluster"""
       spark = SparkSession.builder.appName("OpenSTEF").getOrCreate()
       
       # Read data from Databricks tables
       energy_data = spark.sql("""
           SELECT timestamp, load, temperature, wind_speed
           FROM energy_measurements
           WHERE timestamp >= current_date() - interval 365 days
       """).toPandas()
       
       # Configure prediction job
       prediction_job = {
           "name": "substation_forecast",
           "model": "xgb",
           "quantiles": [0.1, 0.5, 0.9]
       }
       
       # Train model using OpenSTEF
       model = train_model_pipeline(
           prediction_job,
           input_data=energy_data
       )
       
       # Store model back to Databricks
       model_path = "/dbfs/openstef/models/substation_forecast.pkl"
       model.save(model_path)

Custom Data Source Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create custom data adapters for your specific data sources:

.. code-block:: python

   from abc import ABC, abstractmethod
   import pandas as pd

   class DataAdapter(ABC):
       """Abstract base class for data adapters"""
       
       @abstractmethod
       def get_training_data(self, start_date, end_date) -> pd.DataFrame:
           pass
       
       @abstractmethod
       def get_forecast_data(self, forecast_date) -> pd.DataFrame:
           pass
       
       @abstractmethod
       def store_forecast(self, forecast_data: pd.DataFrame):
           pass

   class CustomAPIAdapter(DataAdapter):
       """Example adapter for a custom REST API"""
       
       def __init__(self, api_base_url, api_key):
           self.api_base_url = api_base_url
           self.api_key = api_key
       
       def get_training_data(self, start_date, end_date) -> pd.DataFrame:
           # Implement your API calls here
           response = requests.get(
               f"{self.api_base_url}/historical_data",
               params={"start": start_date, "end": end_date},
               headers={"Authorization": f"Bearer {self.api_key}"}
           )
           return pd.DataFrame(response.json())
       
       def get_forecast_data(self, forecast_date) -> pd.DataFrame:
           # Get recent data for forecasting
           response = requests.get(
               f"{self.api_base_url}/recent_data",
               params={"date": forecast_date},
               headers={"Authorization": f"Bearer {self.api_key}"}
           )
           return pd.DataFrame(response.json())
       
       def store_forecast(self, forecast_data: pd.DataFrame):
           # Post forecast results back to your system
           requests.post(
               f"{self.api_base_url}/forecasts",
               json=forecast_data.to_dict(orient="records"),
               headers={"Authorization": f"Bearer {self.api_key}"}
           )

Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural refactor focused on modularity and flexibility. This section helps you migrate existing V3 implementations to the new V4 structure.

Key Changes in V4
^^^^^^^^^^^^^^^^^^

The most significant change in V4 is the modular mono-repo structure:

- **openstef-core**: Data types, interfaces, and base classes
- **openstef-models**: Forecasting models and preprocessing
- **openstef-meta**: Advanced ensemble models
- **openstef-beam**: Backtesting, evaluation, analysis, and metrics

Migration Steps
^^^^^^^^^^^^^^^

1. **Update Dependencies**

.. code-block:: bash

   # V3 installation
   pip install openstef==3.x.x

   # V4 installation - install specific modules you need
   pip install openstef-models openstef-beam openstef-core

2. **Update Import Statements**

.. code-block:: python

   # V3 imports
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.validation.validation import calc_metrics

   # V4 imports
   from openstef_models.regressors import XGBQuantileOpenstfRegressor
   from openstef_models.pipeline.train_model import train_model_pipeline
   from openstef_beam.validation import calc_metrics

3. **Configuration Changes**

V4 introduces more flexible configuration mechanisms:

.. code-block:: python

   # V3 - Hard-coded configurations
   from openstef.tasks.create_forecast import main

   main(config=config, database=database)

   # V4 - Modular configuration
   from openstef_models.pipeline.create_forecast import create_forecast_pipeline
   from openstef_core.data_classes import PredictionJobDataClass

   # More explicit configuration
   prediction_job = PredictionJobDataClass(
       name="my_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       feature_names=["load", "temperature", "wind_speed"]
   )

   forecast = create_forecast_pipeline(prediction_job, input_data)

4. **Database Integration Changes**

V4 decouples database dependencies for better modularity:

.. code-block:: python

   # V3 - Tight coupling with openstef-dbc
   from openstef.tasks.create_forecast import create_forecast_task

   # V4 - Optional database integration
   from openstef_models.pipeline.create_forecast import create_forecast_pipeline

   # Use pipelines directly without database dependency
   forecast_result = create_forecast_pipeline(
       prediction_job=my_pj,
       input_data=my_data
   )

   # Or integrate with your preferred database solution
   my_database.store_forecast(forecast_result)

Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

**Issue 1: Missing Model Artifacts**

.. code-block:: python

   # V3 - Models stored in single location
   model_path = "/models/my_model.pkl"

   # V4 - Organize by module
   model_path = "/models/openstef_models/my_model.pkl"

**Issue 2: Changed Evaluation Metrics**

.. code-block:: python

   # V3 - Metrics in main package
   from openstef.validation.validation import calc_metrics

   # V4 - Metrics in dedicated beam package
   from openstef_beam.validation import calc_metrics

**Issue 3: Pipeline Interface Changes**

.. code-block:: python

   # V3 - Task-based approach
   from openstef.tasks.train_model import main
   main(config=config, database=database)

   # V4 - Pipeline-based approach (more flexible)
   from openstef_models.pipeline.train_model import train_model_pipeline
   
   model = train_model_pipeline(
       prediction_job=pj,
       input_data=training_data,
       # More explicit parameters
   )

Testing Your Migration
^^^^^^^^^^^^^^^^^^^^^^^

Create a validation script to ensure your migration is working correctly:

.. code-block:: python

   def validate_v4_migration():
       """Validate that V4 migration produces equivalent results to V3"""
       
       # Load same test data
       test_data = load_test_data()
       
       # Run V4 pipeline
       v4_forecast = create_forecast_pipeline(
           prediction_job=test_pj,
           input_data=test_data
       )
       
       # Compare with V3 baseline (if available)
       v3_baseline = load_v3_baseline()
       
       # Validate key metrics are within acceptable range
       mae_diff = abs(v4_forecast.mae - v3_baseline.mae)
       assert mae_diff < 0.01, f"MAE difference too large: {mae_diff}"
       
       print("✅ Migration validation passed")

.. note::
   V4 is designed to maintain forecasting quality while providing better modularity. If you see significant performance differences, check your configuration and data preprocessing steps.

.. warning::
   V4 removes some hard-coded assumptions from V3. Make sure to explicitly configure parameters that were previously set automatically, such as feature engineering settings and model hyperparameters.

For more detailed migration assistance, see the :doc:`../reference/changelog` or join our community discussions on the LF Energy Slack workspace.