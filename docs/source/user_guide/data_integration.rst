Data Integration
================

OpenSTEF is a library that integrates into your existing data infrastructure. This page shows how to connect OpenSTEF to various data sources, write forecasts to storage systems, and handle common data quality challenges in production forecasting pipelines.

Reading Data from Sources
--------------------------

OpenSTEF works with standard pandas DataFrames and its own ``TimeSeriesDataset`` wrapper. You're responsible for loading data from your sources—OpenSTEF doesn't include database connectors or cloud storage clients. This design keeps the library focused and lets you use your organization's existing data access patterns.

Reading from SQL Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^

Load data using your preferred database library, then convert to OpenSTEF's format:

.. code-block:: python

   import pandas as pd
   import psycopg2
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   
   # Load from PostgreSQL
   conn = psycopg2.connect("dbname=energy user=forecast")
   query = """
       SELECT timestamp, load, temperature, windspeed, radiation
       FROM measurements
       WHERE timestamp >= NOW() - INTERVAL '90 days'
       ORDER BY timestamp
   """
   df = pd.read_sql(query, conn, parse_dates=["timestamp"])
   df.set_index("timestamp", inplace=True)
   
   # Convert to OpenSTEF format
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

For InfluxDB or other time-series databases, the pattern is similar—query the data, convert to a DataFrame, and wrap it in a ``TimeSeriesDataset``.

Reading from Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's datasets support reading from Parquet files, which works well with cloud storage:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   import s3fs
   
   # Read directly from S3
   dataset = VersionedTimeSeriesDataset.read_parquet(
       path="s3://my-bucket/forecasting-data/load_2024.parquet",
       sample_interval=timedelta(minutes=15)
   )
   
   # Or use your cloud provider's SDK
   import boto3
   
   s3 = boto3.client("s3")
   obj = s3.get_object(Bucket="my-bucket", Key="data/latest.parquet")
   df = pd.read_parquet(obj["Body"])
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For Databricks, you can read from Delta tables or mounted storage:

.. code-block:: python

   # In a Databricks notebook
   spark_df = spark.table("energy_forecasting.load_measurements")
   df = spark_df.toPandas()
   df.set_index("timestamp", inplace=True)
   
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

Custom Data Providers
^^^^^^^^^^^^^^^^^^^^^

For benchmarking workflows, implement the ``TargetProvider`` interface to load data for multiple forecasting targets:

.. code-block:: python

   from openstef_beam.benchmarking import TargetProvider, BenchmarkTarget
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   class DatabaseTargetProvider(TargetProvider):
       def __init__(self, db_connection):
           self.db = db_connection
       
       def get_targets(self) -> list[BenchmarkTarget]:
           # Load target configurations from your database
           targets = self.db.query("SELECT * FROM forecast_targets")
           return [
               BenchmarkTarget(name=row["name"], metadata=row["config"])
               for row in targets
           ]
       
       def get_load(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           # Load historical load data for this target
           query = f"""
               SELECT timestamp, load, available_at
               FROM load_measurements
               WHERE target_id = '{target.name}'
           """
           df = pd.read_sql(query, self.db, parse_dates=["timestamp", "available_at"])
           df.set_index("timestamp", inplace=True)
           
           return VersionedTimeSeriesDataset(
               data=df,
               sample_interval=timedelta(minutes=15)
           )
       
       def get_weather(self, target: BenchmarkTarget) -> VersionedTimeSeriesDataset:
           # Load weather data for this target's location
           # Similar pattern to get_load()
           pass

Writing Forecasts to Storage
-----------------------------

After generating forecasts, you'll typically want to persist them for downstream systems or analysis.

Writing to Databases
^^^^^^^^^^^^^^^^^^^^

Convert forecast results to DataFrames and write using your database library:

.. code-block:: python

   from openstef_workflows import CustomForecastingWorkflow
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Generate forecast
   workflow = CustomForecastingWorkflow(model=my_model)
   forecast = workflow.predict(data=input_data)
   
   # Write to PostgreSQL
   import psycopg2
   from psycopg2.extras import execute_values
   
   conn = psycopg2.connect("dbname=energy user=forecast")
   cursor = conn.cursor()
   
   # Prepare data for insertion
   records = [
       (
           row.Index,  # timestamp
           row["load"],  # forecast value
           forecast.forecast_start,  # when forecast was made
           target_id
       )
       for row in forecast.data.itertuples()
   ]
   
   execute_values(
       cursor,
       """
       INSERT INTO forecasts (timestamp, value, forecast_start, target_id)
       VALUES %s
       ON CONFLICT (timestamp, forecast_start, target_id) DO UPDATE
       SET value = EXCLUDED.value
       """,
       records
   )
   conn.commit()

Writing to Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^

Save forecasts as Parquet files for efficient storage and retrieval:

.. code-block:: python

   from datetime import datetime
   
   # Save locally
   forecast.to_parquet(path="forecasts/forecast_2024-01-15.parquet")
   
   # Save to S3
   forecast_date = datetime.now().strftime("%Y-%m-%d")
   s3_path = f"s3://my-bucket/forecasts/{target_id}/{forecast_date}.parquet"
   forecast.to_parquet(path=s3_path)
   
   # Or use boto3 for more control
   import boto3
   import io
   
   buffer = io.BytesIO()
   forecast.data.to_parquet(buffer)
   
   s3 = boto3.client("s3")
   s3.put_object(
       Bucket="my-bucket",
       Key=f"forecasts/{target_id}/{forecast_date}.parquet",
       Body=buffer.getvalue(),
       Metadata={
           "forecast_start": str(forecast.forecast_start),
           "model_version": "v2.1"
       }
   )

Custom Storage for Benchmarking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For benchmark pipelines, implement ``BenchmarkStorage`` to control where results are saved:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkStorage, BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   
   class DatabaseStorage(BenchmarkStorage):
       def __init__(self, db_connection):
           self.db = db_connection
       
       def save_backtest_output(
           self, target: BenchmarkTarget, output: TimeSeriesDataset
       ) -> None:
           # Store forecast data preserving temporal versioning
           records = [
               (target.name, row.Index, row["load"], row.get("available_at"))
               for row in output.data.itertuples()
           ]
           
           cursor = self.db.cursor()
           cursor.executemany(
               """
               INSERT INTO backtest_results 
               (target_id, timestamp, predicted_load, available_at)
               VALUES (?, ?, ?, ?)
               """,
               records
           )
           self.db.commit()
       
       def load_backtest_output(
           self, target: BenchmarkTarget
       ) -> TimeSeriesDataset | None:
           # Retrieve data maintaining temporal versioning structure
           query = f"""
               SELECT timestamp, predicted_load, available_at
               FROM backtest_results
               WHERE target_id = '{target.name}'
           """
           df = pd.read_sql(query, self.db, parse_dates=["timestamp", "available_at"])
           if df.empty:
               return None
           
           df.set_index("timestamp", inplace=True)
           return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Handling Missing Data
---------------------

Real-world data always has gaps. OpenSTEF provides tools to detect and handle missing values.

Checking Data Completeness
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``CompletenessChecker`` transform to validate data quality before training or prediction:

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   # Check that load data is at least 80% complete
   checker = CompletenessChecker(
       columns={"load": 1.0},  # Weight of 1.0 for load column
       min_completeness=0.8
   )
   
   try:
       validated_data = checker.transform(dataset)
   except InsufficientlyCompleteError as e:
       print(f"Data quality insufficient: {e}")
       # Handle the error - skip this target, use fallback model, etc.

You can check multiple columns with different importance weights:

.. code-block:: python

   # Weather features are less critical than load
   checker = CompletenessChecker(
       columns={
           "load": 1.0,
           "temperature": 0.5,
           "windspeed": 0.3
       },
       min_completeness=0.75
   )

Handling Missing Values
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF doesn't automatically impute missing data—you decide how to handle gaps based on your domain knowledge:

.. code-block:: python

   # Forward fill for short gaps (common for sensor data)
   df["temperature"].fillna(method="ffill", limit=4, inplace=True)
   
   # Interpolate for smooth variables
   df["radiation"].interpolate(method="linear", inplace=True)
   
   # Drop rows with critical missing values
   df.dropna(subset=["load"], inplace=True)
   
   # Or use domain-specific defaults
   df["windspeed"].fillna(0, inplace=True)  # Assume calm if missing

For production systems, log data quality issues for monitoring:

.. code-block:: python

   import logging
   
   logger = logging.getLogger(__name__)
   
   missing_count = df["load"].isna().sum()
   total_count = len(df)
   completeness = 1 - (missing_count / total_count)
   
   if completeness < 0.95:
       logger.warning(
           f"Data completeness below threshold: {completeness:.2%} "
           f"({missing_count}/{total_count} missing)"
       )

Data Validation
---------------

Validate data structure and content before using it with OpenSTEF.

Required Columns
^^^^^^^^^^^^^^^^

OpenSTEF's validation utilities check for required columns:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.exceptions import MissingColumnsError
   
   required = ["load", "temperature", "windspeed", "radiation"]
   
   try:
       validate_required_columns(df, required)
   except MissingColumnsError as e:
       print(f"Missing columns: {e}")
       # Handle missing features - use simpler model, fetch additional data, etc.

Temporal Consistency
^^^^^^^^^^^^^^^^^^^^

The ``TimeSeriesDataset`` constructor validates temporal properties:

.. code-block:: python

   from datetime import timedelta
   
   # This will raise ValueError if data frequency doesn't match
   try:
       dataset = TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(minutes=15),
           check_frequency=True  # Validate data frequency
       )
   except ValueError as e:
       print(f"Frequency mismatch: {e}")
       # Resample data to correct frequency
       df = df.resample("15min").mean()
       dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For versioned datasets with ``available_at`` columns, OpenSTEF validates temporal versioning:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Validates that available_at is a datetime column
   versioned_dataset = VersionedTimeSeriesDataset(
       data=df,  # Must include 'available_at' column
       sample_interval=timedelta(minutes=15)
   )

Complete Pipeline Example
--------------------------

Here's a realistic data integration pipeline that combines these patterns:

.. code-block:: python

   import logging
   from datetime import datetime, timedelta
   import pandas as pd
   import psycopg2
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_workflows import CustomForecastingWorkflow
   
   logger = logging.getLogger(__name__)
   
   def run_forecast_pipeline(target_id: str, model, db_config: dict):
       """Complete forecasting pipeline with data integration."""
       
       # 1. Load data from database
       conn = psycopg2.connect(**db_config)
       query = """
           SELECT timestamp, load, temperature, windspeed, radiation
           FROM measurements
           WHERE target_id = %s
             AND timestamp >= NOW() - INTERVAL '90 days'
           ORDER BY timestamp
       """
       df = pd.read_sql(query, conn, params=(target_id,), parse_dates=["timestamp"])
       df.set_index("timestamp", inplace=True)
       
       # 2. Validate required columns
       try:
           validate_required_columns(df, ["load", "temperature", "windspeed"])
       except Exception as e:
           logger.error(f"Missing required columns for {target_id}: {e}")
           return None
       
       # 3. Handle missing data
       missing_pct = df["load"].isna().sum() / len(df)
       if missing_pct > 0.05:
           logger.warning(f"High missing data rate for {target_id}: {missing_pct:.2%}")
       
       df["temperature"].fillna(method="ffill", limit=4, inplace=True)
       df.dropna(subset=["load"], inplace=True)
       
       # 4. Create dataset and validate completeness
       dataset = TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(minutes=15)
       )
       
       checker = CompletenessChecker(
           columns={"load": 1.0, "temperature": 0.5},
           min_completeness=0.8
       )
       
       try:
           dataset = checker.transform(dataset)
       except Exception as e:
           logger.error(f"Data quality check failed for {target_id}: {e}")
           return None
       
       # 5. Generate forecast
       workflow = CustomForecastingWorkflow(model=model)
       forecast = workflow.predict(data=dataset)
       
       # 6. Write results to database
       cursor = conn.cursor()
       records = [
           (target_id, row.Index, row["load"], datetime.now())
           for row in forecast.data.itertuples()
       ]
       
       cursor.executemany(
           """
           INSERT INTO forecasts (target_id, timestamp, value, created_at)
           VALUES (%s, %s, %s, %s)
           """,
           records
       )
       conn.commit()
       conn.close()
       
       logger.info(f"Forecast generated for {target_id}: {len(forecast.data)} points")
       return forecast

This pipeline demonstrates the complete flow: loading data, validation, quality checks, forecasting, and persistence. Adapt this pattern to your specific data sources and requirements.

For deployment patterns and production considerations, see :doc:`deployment`. For logging configuration in production pipelines, see :doc:`logging`.