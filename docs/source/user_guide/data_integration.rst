Data Integration
================

OpenSTEF is a library that integrates into your existing data infrastructure. This page covers practical patterns for connecting OpenSTEF to various data sources, writing forecasts back to storage systems, and handling common data quality challenges.

Reading Data from Storage Systems
----------------------------------

OpenSTEF operates on pandas DataFrames and the ``TimeSeriesDataset`` abstraction. Your integration code is responsible for loading data from your storage system and converting it to the expected format.

Reading from SQL Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^

PostgreSQL, MySQL, and other SQL databases are common sources for energy data:

.. code-block:: python

   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset
   
   # Connect to your database
   engine = create_engine("postgresql://user:password@host:5432/energy_db")
   
   # Query historical load and weather data
   query = """
       SELECT 
           timestamp,
           load_mw as load,
           temperature,
           wind_speed,
           radiation
       FROM energy_data
       WHERE timestamp >= %s AND timestamp < %s
       ORDER BY timestamp
   """
   
   df = pd.read_sql_query(
       query,
       engine,
       params=["2024-01-01", "2024-12-31"],
       parse_dates=["timestamp"],
       index_col="timestamp"
   )
   
   # Convert to OpenSTEF dataset
   dataset = TimeSeriesDataset(data=df)

Reading from Time Series Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

InfluxDB and similar time series databases require different query patterns:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset
   
   client = InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org")
   query_api = client.query_api()
   
   # Query using Flux
   query = '''
       from(bucket: "energy")
           |> range(start: -30d)
           |> filter(fn: (r) => r["_measurement"] == "load")
           |> filter(fn: (r) => r["location"] == "substation_42")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''
   
   tables = query_api.query(query)
   
   # Convert to DataFrame
   records = []
   for table in tables:
       for record in table.records:
           records.append({
               "timestamp": record.get_time(),
               "load": record.values.get("power"),
               "temperature": record.values.get("temp"),
           })
   
   df = pd.DataFrame(records).set_index("timestamp")
   dataset = TimeSeriesDataset(data=df)

Reading from Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

S3, Azure Blob Storage, and Google Cloud Storage typically store data as files:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Read from S3 (requires s3fs)
   df = pd.read_parquet(
       "s3://my-bucket/energy-data/2024/load_data.parquet",
       storage_options={
           "key": "AWS_ACCESS_KEY",
           "secret": "AWS_SECRET_KEY",
       }
   )
   
   # Or read CSV from Azure Blob Storage (requires adlfs)
   df = pd.read_csv(
       "abfs://container/path/to/data.csv",
       storage_options={
           "account_name": "mystorageaccount",
           "account_key": "myaccountkey",
       },
       parse_dates=["timestamp"],
       index_col="timestamp"
   )
   
   dataset = TimeSeriesDataset(data=df)

Reading from Databricks
^^^^^^^^^^^^^^^^^^^^^^^

When running in Databricks notebooks or jobs:

.. code-block:: python

   from pyspark.sql import SparkSession
   from openstef_core.datasets import TimeSeriesDataset
   
   spark = SparkSession.builder.getOrCreate()
   
   # Query Delta table
   spark_df = spark.sql("""
       SELECT 
           timestamp,
           load,
           temperature,
           wind_speed
       FROM energy_analytics.load_history
       WHERE timestamp >= '2024-01-01'
   """)
   
   # Convert to pandas (ensure data fits in memory)
   df = spark_df.toPandas()
   df = df.set_index("timestamp")
   
   dataset = TimeSeriesDataset(data=df)

Writing Forecasts to Storage
-----------------------------

After generating forecasts, you'll typically want to persist them for downstream applications.

Writing to SQL Databases
^^^^^^^^^^^^^^^^^^^^^^^^^

Store forecasts with metadata for traceability:

.. code-block:: python

   from datetime import datetime
   from openstef_core.forecasting import Forecaster
   
   # Generate forecast
   forecaster = Forecaster.from_config(config)
   forecast = forecaster.predict(input_data)
   
   # Prepare for database insertion
   forecast_df = forecast.data.reset_index()
   forecast_df["forecast_created_at"] = datetime.utcnow()
   forecast_df["model_version"] = forecaster.model_version
   forecast_df["location_id"] = "substation_42"
   
   # Write to database
   forecast_df.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False,
       method="multi"  # Faster bulk insert
   )

Writing to Time Series Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

InfluxDB write pattern with proper tagging:

.. code-block:: python

   from influxdb_client import Point, WritePrecision
   from influxdb_client.client.write_api import SYNCHRONOUS
   
   write_api = client.write_api(write_options=SYNCHRONOUS)
   
   points = []
   for timestamp, row in forecast.data.iterrows():
       point = (
           Point("forecast")
           .tag("location", "substation_42")
           .tag("model_version", forecaster.model_version)
           .tag("horizon", row.get("horizon", 0))
           .field("load_mw", float(row["load"]))
           .time(timestamp, WritePrecision.NS)
       )
       points.append(point)
   
   write_api.write(bucket="forecasts", record=points)

Writing to Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^

Partition forecasts by date for efficient querying:

.. code-block:: python

   from datetime import datetime
   
   # Add partitioning columns
   forecast_df = forecast.data.reset_index()
   forecast_df["date"] = forecast_df["timestamp"].dt.date
   forecast_df["forecast_created_at"] = datetime.utcnow()
   
   # Write partitioned parquet to S3
   forecast_df.to_parquet(
       "s3://my-bucket/forecasts/",
       partition_cols=["date"],
       storage_options={
           "key": "AWS_ACCESS_KEY",
           "secret": "AWS_SECRET_KEY",
       }
   )

Handling Missing Data
---------------------

Real-world energy data often has gaps. OpenSTEF provides validation utilities and expects you to handle missing data appropriately.

Detecting Missing Data
^^^^^^^^^^^^^^^^^^^^^^^

Use OpenSTEF's validation utilities:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.exceptions import MissingColumnsError
   
   required_columns = ["load", "temperature", "wind_speed"]
   
   try:
       validate_required_columns(df, required_columns)
   except MissingColumnsError as e:
       print(f"Missing columns: {e}")
       # Handle missing columns

Check for temporal gaps:

.. code-block:: python

   import pandas as pd
   
   # Detect missing timestamps (assuming 15-minute intervals)
   expected_freq = pd.Timedelta(minutes=15)
   actual_freq = df.index.to_series().diff().mode()[0]
   
   if actual_freq != expected_freq:
       print(f"Warning: Irregular time series detected")
   
   # Find gaps
   time_diffs = df.index.to_series().diff()
   gaps = time_diffs[time_diffs > expected_freq]
   
   if not gaps.empty:
       print(f"Found {len(gaps)} gaps in data:")
       for timestamp, gap_size in gaps.items():
           print(f"  Gap at {timestamp}: {gap_size}")

Filling Missing Values
^^^^^^^^^^^^^^^^^^^^^^^

Different strategies for different data types:

.. code-block:: python

   # Forward fill for slowly changing variables (temperature)
   df["temperature"] = df["temperature"].fillna(method="ffill", limit=4)
   
   # Interpolate for continuous variables
   df["wind_speed"] = df["wind_speed"].interpolate(method="linear")
   
   # Use historical average for load (same hour, same day of week)
   df["load"] = df.groupby([df.index.hour, df.index.dayofweek])["load"].transform(
       lambda x: x.fillna(x.mean())
   )
   
   # Drop rows if too much data is missing
   threshold = 0.8  # Require 80% completeness
   df = df.dropna(thresh=int(threshold * len(df.columns)))

The forecaster will raise ``InsufficientlyCompleteError`` if training data has too many missing target values after preprocessing.

Data Validation
---------------

Validate data quality before training or forecasting:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.exceptions import TimeSeriesValidationError
   
   def validate_energy_data(df: pd.DataFrame) -> None:
       """Validate energy dataset meets quality requirements."""
       
       # Check for negative load values
       if (df["load"] < 0).any():
           raise ValueError("Load values cannot be negative")
       
       # Check for unrealistic values
       if (df["load"] > 1000).any():  # MW threshold
           raise ValueError("Load values exceed realistic maximum")
       
       # Check temperature range
       if not df["temperature"].between(-40, 50).all():
           raise ValueError("Temperature values outside expected range")
       
       # Check for sufficient data density
       completeness = df.notna().mean()
       if (completeness < 0.9).any():
           low_quality_cols = completeness[completeness < 0.9].index.tolist()
           raise ValueError(f"Insufficient data in columns: {low_quality_cols}")
   
   # Use in pipeline
   try:
       validate_energy_data(df)
       dataset = TimeSeriesDataset(data=df)
   except ValueError as e:
       print(f"Data validation failed: {e}")
       # Handle validation failure

Complete Integration Example
-----------------------------

A realistic data pipeline combining reading, validation, forecasting, and writing:

.. code-block:: python

   import pandas as pd
   from sqlalchemy import create_engine
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, ForecastInputDataset
   from openstef_core.forecasting import Forecaster
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   def run_forecast_pipeline(location_id: str, forecast_date: datetime):
       """Complete forecast pipeline with data integration."""
       
       # 1. Read training data from database
       engine = create_engine("postgresql://user:pass@host/db")
       
       train_start = forecast_date - timedelta(days=90)
       query = """
           SELECT timestamp, load, temperature, wind_speed, radiation
           FROM energy_data
           WHERE location_id = %s 
             AND timestamp >= %s 
             AND timestamp < %s
           ORDER BY timestamp
       """
       
       train_df = pd.read_sql_query(
           query,
           engine,
           params=[location_id, train_start, forecast_date],
           parse_dates=["timestamp"],
           index_col="timestamp"
       )
       
       # 2. Validate and clean data
       train_df = train_df.dropna(subset=["load"])  # Target must be present
       train_df["temperature"] = train_df["temperature"].fillna(method="ffill", limit=4)
       train_df["wind_speed"] = train_df["wind_speed"].interpolate(method="linear")
       
       if train_df["load"].notna().mean() < 0.8:
           raise ValueError(f"Insufficient training data for {location_id}")
       
       # 3. Create dataset and train forecaster
       train_data = TimeSeriesDataset(data=train_df)
       
       forecaster = Forecaster.from_config(config)
       
       try:
           forecaster.fit(data=train_data)
       except InsufficientlyCompleteError:
           print(f"Cannot train model for {location_id}: insufficient data")
           return None
       
       # 4. Prepare forecast input (with weather predictions)
       forecast_df = pd.read_sql_query(
           "SELECT * FROM weather_forecasts WHERE location_id = %s AND timestamp >= %s",
           engine,
           params=[location_id, forecast_date],
           parse_dates=["timestamp"],
           index_col="timestamp"
       )
       
       forecast_input = ForecastInputDataset(
           data=forecast_df,
           forecast_start=forecast_date
       )
       
       # 5. Generate forecast
       forecast = forecaster.predict(forecast_input)
       
       # 6. Write results back to database
       result_df = forecast.data.reset_index()
       result_df["location_id"] = location_id
       result_df["forecast_created_at"] = datetime.utcnow()
       result_df["model_version"] = forecaster.model_version
       
       result_df.to_sql(
           "forecasts",
           engine,
           if_exists="append",
           index=False
       )
       
       return forecast
   
   # Run for multiple locations
   for location in ["substation_42", "substation_43"]:
       try:
           run_forecast_pipeline(location, datetime.now())
           print(f"Forecast completed for {location}")
       except Exception as e:
           print(f"Forecast failed for {location}: {e}")

Custom Storage Backends
-----------------------

For benchmarking workflows, OpenSTEF provides a storage abstraction in ``openstef-beam``. You can implement custom backends:

.. code-block:: python

   from openstef_beam.benchmarking.storage import BenchmarkStorage
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   
   class CustomDatabaseStorage(BenchmarkStorage):
       """Store benchmark results in a custom database."""
       
       def __init__(self, connection_string: str):
           self.engine = create_engine(connection_string)
       
       def save_backtest_output(
           self, 
           target: BenchmarkTarget, 
           output: TimeSeriesDataset
       ) -> None:
           """Save backtest predictions to database."""
           df = output.data.reset_index()
           df["target_name"] = target.name
           df["target_metadata"] = str(target.metadata)
           
           df.to_sql(
               "backtest_outputs",
               self.engine,
               if_exists="append",
               index=False
           )
       
       def load_backtest_output(
           self, 
           target: BenchmarkTarget
       ) -> TimeSeriesDataset:
           """Load backtest predictions from database."""
           query = """
               SELECT * FROM backtest_outputs 
               WHERE target_name = %s
               ORDER BY timestamp
           """
           df = pd.read_sql_query(
               query,
               self.engine,
               params=[target.name],
               parse_dates=["timestamp"],
               index_col="timestamp"
           )
           
           return TimeSeriesDataset(data=df)
   
   # Use in benchmark pipeline
   storage = CustomDatabaseStorage("postgresql://user:pass@host/benchmarks")
   pipeline = BenchmarkPipeline(storage=storage, ...)

The built-in ``S3BenchmarkStorage`` provides a reference implementation that combines local caching with S3 persistence.

Next Steps
----------

- See :doc:`use_cases` for complete application examples
- Review :doc:`deployment` for production infrastructure patterns  
- Check :doc:`logging` for monitoring data pipeline health