How-To Guides
=============

This page provides practical, task-specific guides for common OpenSTEF implementation scenarios. Unlike tutorials that teach concepts, these guides focus on solving specific problems you may encounter when deploying OpenSTEF in production environments.

.. note::
   Looking for step-by-step learning? See the :doc:`../getting_started/tutorials` page. For understanding different forecasting applications, visit :doc:`use_cases`.


Setting Up Forecast Scheduling
-------------------------------

OpenSTEF is a library, not a standalone application. You need to integrate it into your own scheduling infrastructure. Here are common approaches.

Simple Cron-Based Deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For small-scale deployments, a cron job can periodically execute forecasting tasks. OpenSTEF provides task modules designed for this pattern.

**Example cron setup:**

.. code-block:: bash

   # Run forecast creation every hour at 5 minutes past the hour
   5 * * * * /usr/bin/python /path/to/your_forecast_script.py

**Forecast script example:**

.. code-block:: python

   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.tasks.utils.taskcontext import TaskContext
   
   # Define your prediction job
   prediction_job = PredictionJobDataClass(
       id=123,
       name="substation_forecast",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       horizon_minutes=2880,  # 48 hours
   )
   
   # Set up context with your database and configuration
   context = TaskContext(
       database=your_database_connection,
       config=your_config,
   )
   
   # Create forecast
   create_forecast_task(
       pj=prediction_job,
       context=context,
       t_behind_days=14,  # Use 14 days of historical data
   )

This approach assumes:

- Trained models are available in persistent storage
- Database connections are configured
- Historical data (load, weather, prices) is accessible

If models aren't trained yet, run the model training task first using ``openstef.tasks.train_model``.

Orchestration with Dagster
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For production deployments requiring dependency management, monitoring, and retry logic, use a workflow orchestrator like Dagster.

**Example Dagster pipeline:**

.. code-block:: python

   from dagster import job, op, schedule, DailyPartitionsDefinition
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   @op
   def load_prediction_jobs(context):
       """Load all active prediction jobs from configuration."""
       # Your logic to retrieve prediction jobs
       return [
           PredictionJobDataClass(id=1, name="station_a", model="xgb"),
           PredictionJobDataClass(id=2, name="station_b", model="xgb"),
       ]
   
   @op
   def create_forecast(context, prediction_job):
       """Create forecast for a single prediction job."""
       from your_project.context import get_task_context
       
       task_context = get_task_context()
       create_forecast_task(
           pj=prediction_job,
           context=task_context,
           t_behind_days=14,
       )
       
       context.log.info(f"Forecast created for {prediction_job.name}")
   
   @job
   def hourly_forecast_job():
       """Run forecasts for all prediction jobs."""
       jobs = load_prediction_jobs()
       jobs.map(create_forecast)
   
   @schedule(
       job=hourly_forecast_job,
       cron_schedule="5 * * * *",  # Every hour at 5 minutes past
   )
   def hourly_forecast_schedule(context):
       return {}

**Benefits of orchestration:**

- Automatic retries on failure
- Dependency management between tasks
- Monitoring and alerting integration
- Parallel execution of independent forecasts
- Historical run tracking

Other orchestrators like Airflow, Prefect, or Argo Workflows follow similar patterns—wrap OpenSTEF task functions in your orchestrator's task abstraction.


Integrating Data Sources
-------------------------

OpenSTEF expects data in specific formats but doesn't prescribe where it comes from. Here's how to integrate common data systems.

Amazon S3 Integration
^^^^^^^^^^^^^^^^^^^^^

Store and retrieve forecast data, trained models, or benchmark results using S3.

**Storing forecast outputs:**

.. code-block:: python

   import pandas as pd
   import s3fs
   from datetime import datetime
   
   def save_forecast_to_s3(forecast_df, bucket, prediction_job_id):
       """Save forecast DataFrame to S3 as parquet."""
       s3 = s3fs.S3FileSystem()
       
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       s3_path = f"s3://{bucket}/forecasts/{prediction_job_id}/{timestamp}.parquet"
       
       with s3.open(s3_path, 'wb') as f:
           forecast_df.to_parquet(f)
       
       return s3_path

**Loading historical data from S3:**

.. code-block:: python

   def load_training_data_from_s3(bucket, prediction_job_id):
       """Load historical data from S3 for model training."""
       s3 = s3fs.S3FileSystem()
       s3_path = f"s3://{bucket}/historical_data/{prediction_job_id}.parquet"
       
       with s3.open(s3_path, 'rb') as f:
           data = pd.read_parquet(f)
       
       return data

For benchmark storage, OpenSTEF-Beam provides ``S3BenchmarkStorage`` that automatically syncs local benchmark results to S3:

.. code-block:: python

   from openstef_beam.benchmarking import S3BenchmarkStorage, LocalBenchmarkStorage
   
   local_storage = LocalBenchmarkStorage(base_path="./benchmarks")
   s3_storage = S3BenchmarkStorage(
       local_storage=local_storage,
       bucket_name="my-benchmark-bucket",
       s3_prefix="openstef/benchmarks",
   )
   
   # Save operations automatically sync to S3
   s3_storage.save_backtest_output(target, output)

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^^

Access data from Databricks tables and write forecasts back to Delta tables.

**Reading from Databricks:**

.. code-block:: python

   from databricks import sql
   import pandas as pd
   
   def load_data_from_databricks(server_hostname, http_path, access_token, query):
       """Load data from Databricks SQL warehouse."""
       with sql.connect(
           server_hostname=server_hostname,
           http_path=http_path,
           access_token=access_token,
       ) as connection:
           with connection.cursor() as cursor:
               cursor.execute(query)
               result = cursor.fetchall()
               columns = [desc[0] for desc in cursor.description]
       
       return pd.DataFrame(result, columns=columns)
   
   # Example usage
   query = """
       SELECT timestamp, load, temperature, wind_speed
       FROM energy_data.measurements
       WHERE station_id = 'station_a'
       AND timestamp >= current_date() - INTERVAL 30 DAYS
   """
   
   training_data = load_data_from_databricks(
       server_hostname="your-workspace.databricks.com",
       http_path="/sql/1.0/warehouses/abc123",
       access_token=your_token,
       query=query,
   )

**Writing forecasts to Delta tables:**

.. code-block:: python

   from pyspark.sql import SparkSession
   
   def write_forecast_to_delta(forecast_df, table_name):
       """Write forecast DataFrame to Databricks Delta table."""
       spark = SparkSession.builder.getOrCreate()
       
       spark_df = spark.createDataFrame(forecast_df)
       
       spark_df.write \
           .format("delta") \
           .mode("append") \
           .saveAsTable(table_name)

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

Time-series databases like InfluxDB are well-suited for storing forecast data and measurements.

**Writing forecasts to InfluxDB:**

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   
   def write_forecast_to_influx(forecast_df, bucket, org, token, url):
       """Write forecast data to InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       write_api = client.write_api(write_options=SYNCHRONOUS)
       
       points = []
       for _, row in forecast_df.iterrows():
           point = Point("forecast") \
               .tag("prediction_job_id", row["prediction_job_id"]) \
               .tag("quantile", row["quantile"]) \
               .field("value", row["forecast"]) \
               .time(row["timestamp"])
           points.append(point)
       
       write_api.write(bucket=bucket, record=points)
       client.close()

**Reading measurements from InfluxDB:**

.. code-block:: python

   def load_measurements_from_influx(bucket, org, token, url, start_time, station_id):
       """Load historical measurements from InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       query_api = client.query_api()
       
       query = f'''
           from(bucket: "{bucket}")
               |> range(start: {start_time})
               |> filter(fn: (r) => r["_measurement"] == "load")
               |> filter(fn: (r) => r["station_id"] == "{station_id}")
       '''
       
       result = query_api.query_data_frame(query)
       client.close()
       
       return result


Migrating from OpenSTEF V3 to V4
---------------------------------

OpenSTEF V4 represents a major architectural redesign focused on modularity, flexibility, and enterprise integration. This section helps you migrate existing V3 implementations.

Key Changes in V4
^^^^^^^^^^^^^^^^^

**Architectural changes:**

- **Mono-repo structure**: V4 splits functionality into separate packages (``openstef-core``, ``openstef-models``, ``openstef-beam``, ``openstef-meta``)
- **Decoupled dependencies**: External dependencies like MLflow and database clients are no longer tightly coupled
- **Modular design**: Clear interfaces for custom models, transforms, and metrics
- **Type safety**: Full type annotations throughout the codebase

**API changes:**

- Configuration mechanisms are more flexible and less hard-coded
- Data preprocessing is centralized rather than scattered across validation and model components
- Model interfaces are more standardized and extensible

Migration Strategy
^^^^^^^^^^^^^^^^^^

**Step 1: Assess your current usage**

Identify which V3 components you use:

- Task modules (``create_forecast``, ``train_model``, etc.)
- Model training and prediction pipelines
- Custom feature engineering
- Database integration patterns

**Step 2: Update package dependencies**

V4 uses a modular package structure. Update your ``requirements.txt`` or ``pyproject.toml``:

.. code-block:: text

   # V3
   openstef==3.x.x
   
   # V4
   openstef-core==4.x.x
   openstef-models==4.x.x
   openstef-beam==4.x.x  # If using backtesting/evaluation

**Step 3: Update imports**

Many imports remain similar, but some modules have moved:

.. code-block:: python

   # V3
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   
   # V4 - check updated import paths
   from openstef.models.regressors.xgb import XGBOpenstfRegressor
   from openstef.models.preprocessing import apply_features

**Step 4: Adapt configuration patterns**

V4 replaces hard-coded assumptions with configurable options. Review your prediction job configurations:

.. code-block:: python

   # V3 - some settings were implicit
   prediction_job = PredictionJobDataClass(
       id=123,
       model="xgb",
   )
   
   # V4 - more explicit configuration
   prediction_job = PredictionJobDataClass(
       id=123,
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],
       resolution_minutes=15,
       horizon_minutes=2880,
       # Additional configurable options
   )

**Step 5: Update database integration**

V4 decouples database dependencies. If you used ``openstef-dbc``, you'll need to provide your own database adapter:

.. code-block:: python

   # V3 - used openstef-dbc directly
   from openstef.dbc import DataBase
   
   # V4 - implement your own adapter following the interface
   from your_project.database import YourDatabaseAdapter
   
   # Pass to TaskContext
   context = TaskContext(
       database=YourDatabaseAdapter(),
       config=your_config,
   )

**Step 6: Test thoroughly**

Use OpenSTEF-Beam to validate that V4 produces comparable results:

.. code-block:: python

   from openstef_beam.benchmarking import run_backtest
   
   # Run backtest with V3 and V4 models
   # Compare metrics to ensure migration didn't degrade performance

Common Migration Issues
^^^^^^^^^^^^^^^^^^^^^^^

**Issue: MLflow integration no longer automatic**

*Solution:* V4 decouples MLflow. If you need model tracking, explicitly integrate MLflow in your workflow:

.. code-block:: python

   import mlflow
   
   with mlflow.start_run():
       # Train model
       model = train_model(data, prediction_job)
       
       # Log manually
       mlflow.log_params(prediction_job.to_dict())
       mlflow.sklearn.log_model(model, "model")

**Issue: Custom feature engineering breaks**

*Solution:* V4 centralizes preprocessing. Review the new feature engineering API and adapt custom transformations to use the standardized interfaces.

**Issue: Hard-coded Dutch holidays no longer work for other regions**

*Solution:* V4 allows custom holiday calendars. Provide your own:

.. code-block:: python

   from openstef.models.preprocessing import set_holiday_calendar
   import holidays
   
   # Use German holidays instead of Dutch
   german_holidays = holidays.Germany()
   set_holiday_calendar(german_holidays)

Getting Help
^^^^^^^^^^^^

Migration questions? Reach out to the community:

- GitHub Discussions: https://github.com/OpenSTEF/openstef/discussions
- Slack: Join the LF Energy workspace
- Review the :doc:`../reference/changelog` for detailed breaking changes

The OpenSTEF team has successfully migrated Alliander's production system (10,000+ daily forecasts) to V4. Lessons learned from this migration and feedback from users like Sigholm inform these guides.

.. note::
   V4 is designed for easier enterprise integration. If you're building a new deployment, start with V4 rather than migrating from V3.