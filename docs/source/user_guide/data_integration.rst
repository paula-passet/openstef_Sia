Data Integration
=================

OpenSTEF is a library that integrates into your existing data infrastructure. This page shows how to connect OpenSTEF to various data sources, write forecasts back to storage systems, and handle common data quality challenges in production pipelines.

Reading Data from Storage Systems
----------------------------------

OpenSTEF works with pandas DataFrames and its own ``TimeSeriesDataset`` abstraction. You can load data from any source that pandas supports, then wrap it for use with OpenSTEF workflows.

Reading from Parquet Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The most common pattern for local or cloud storage uses Parquet files. OpenSTEF's dataset classes provide built-in Parquet support:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from datetime import timedelta

   # Load standard time series data
   dataset = TimeSeriesDataset.read_parquet(
       path="data/load_data.parquet",
       sample_interval=timedelta(minutes=15),
       timestamp_column="timestamp"
   )

   # Load versioned data (with available_at timestamps)
   versioned_dataset = VersionedTimeSeriesDataset.read_parquet(
       path="data/weather_forecasts.parquet",
       sample_interval=timedelta(hours=1),
       timestamp_column="timestamp",
       available_at_column="available_at",
       horizon_column="horizon"
   )

The ``read_parquet`` method automatically restores dataset metadata including sample intervals and versioning columns. This ensures consistency when moving data between storage and processing.

Reading from S3
^^^^^^^^^^^^^^^

For cloud storage, combine pandas S3 support with OpenSTEF datasets:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # Read from S3 using pandas
   df = pd.read_parquet(
       "s3://my-bucket/energy-data/load_2024.parquet",
       storage_options={
           "key": "YOUR_ACCESS_KEY",
           "secret": "YOUR_SECRET_KEY"
       }
   )

   # Convert to OpenSTEF dataset
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

For production use, consider using the S3 storage backend pattern from ``openstef-beam``. This provides hybrid local/cloud storage with automatic synchronization:

.. code-block:: python

   from openstef_beam.benchmarking.storage import S3BenchmarkStorage

   # Hybrid storage: local performance with S3 durability
   storage = S3BenchmarkStorage(
       local_dir="./cache",
       s3_bucket="my-forecasting-bucket",
       s3_prefix="benchmarks/"
   )

Reading from Databases
^^^^^^^^^^^^^^^^^^^^^^

For PostgreSQL, InfluxDB, or other databases, use pandas database connectors:

.. code-block:: python

   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   # PostgreSQL example
   engine = create_engine("postgresql://user:pass@localhost/energy_db")
   
   query = """
       SELECT timestamp, load, temperature, windspeed
       FROM measurements
       WHERE timestamp >= %s AND timestamp < %s
       ORDER BY timestamp
   """
   
   df = pd.read_sql(
       query,
       engine,
       params=["2024-01-01", "2024-02-01"],
       index_col="timestamp",
       parse_dates=["timestamp"]
   )
   
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

For InfluxDB:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org")
   query_api = client.query_api()

   query = '''
       from(bucket: "energy")
           |> range(start: -30d)
           |> filter(fn: (r) => r["_measurement"] == "load")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''

   result = query_api.query_data_frame(query)
   result = result.set_index("_time")
   
   dataset = TimeSeriesDataset(
       data=result,
       sample_interval=timedelta(minutes=15)
   )

Reading from Databricks
^^^^^^^^^^^^^^^^^^^^^^^

When running on Databricks, read from Delta tables or Spark DataFrames:

.. code-block:: python

   # Read Delta table to pandas
   spark_df = spark.table("energy_data.load_measurements")
   df = spark_df.toPandas()
   df = df.set_index("timestamp")
   
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

For large datasets, consider filtering in Spark before converting to pandas:

.. code-block:: python

   from datetime import datetime

   spark_df = (
       spark.table("energy_data.load_measurements")
       .filter(col("timestamp") >= "2024-01-01")
       .filter(col("location_id") == "SUBSTATION_42")
   )
   
   df = spark_df.toPandas().set_index("timestamp")
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Writing Forecasts to Storage
-----------------------------

After generating forecasts, write them back to your storage system for consumption by downstream applications.

Writing to Parquet
^^^^^^^^^^^^^^^^^^

Use the built-in ``to_parquet`` method to preserve all dataset metadata:

.. code-block:: python

   from openstef_models.workflows import ForecastingWorkflow

   workflow = ForecastingWorkflow(...)
   forecast = workflow.predict(data=input_data)

   # Save forecast with metadata
   forecast.to_parquet("output/forecast_2024_01_15.parquet")

The saved file includes sample interval, forecast start time, and column metadata, enabling correct reconstruction later.

Writing to Databases
^^^^^^^^^^^^^^^^^^^^

For PostgreSQL or other SQL databases:

.. code-block:: python

   from sqlalchemy import create_engine
   import pandas as pd

   engine = create_engine("postgresql://user:pass@localhost/energy_db")

   # Convert forecast to DataFrame
   forecast_df = forecast.to_pandas().reset_index()
   
   # Add metadata columns
   forecast_df["forecast_created_at"] = pd.Timestamp.now()
   forecast_df["model_version"] = "v4.2.0"
   forecast_df["location_id"] = "SUBSTATION_42"

   # Write to database
   forecast_df.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False
   )

For InfluxDB, write points with appropriate tags:

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS

   client = InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org")
   write_api = client.write_api(write_options=SYNCHRONOUS)

   forecast_df = forecast.to_pandas().reset_index()
   
   points = []
   for _, row in forecast_df.iterrows():
       point = (
           Point("forecast")
           .tag("location", "SUBSTATION_42")
           .tag("model", "xgboost")
           .field("load", float(row["load"]))
           .time(row["timestamp"])
       )
       points.append(point)
   
   write_api.write(bucket="forecasts", record=points)

Writing to S3 or Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Write directly to cloud storage using pandas:

.. code-block:: python

   # Write to S3
   forecast.to_pandas().to_parquet(
       "s3://my-bucket/forecasts/2024/01/forecast_20240115.parquet",
       storage_options={
           "key": "YOUR_ACCESS_KEY",
           "secret": "YOUR_SECRET_KEY"
       }
   )

For production workflows with multiple outputs, use the storage callback pattern:

.. code-block:: python

   from openstef_models.workflows.callbacks import DataSaveCallback
   from pathlib import Path

   # Automatically save forecasts during workflow execution
   callback = DataSaveCallback(
       cache_dir=Path("s3://my-bucket/forecasts/"),
       save_forecast=True,
       save_contributions=True
   )

   workflow = ForecastingWorkflow(callbacks=[callback], ...)
   forecast = workflow.predict(data=input_data)
   # Forecast automatically saved to S3

Handling Missing Data
---------------------

Real-world energy data often contains gaps. OpenSTEF provides validation and handling strategies for missing data.

Checking Data Completeness
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use the ``CompletenessChecker`` transform to validate data quality before training:

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_core.exceptions import InsufficientlyCompleteError

   checker = CompletenessChecker(
       columns=["load"],
       min_completeness=0.9,  # Require 90% non-missing values
       raise_on_insufficient=True
   )

   try:
       validated_data = checker.transform(dataset)
   except InsufficientlyCompleteError as e:
       print(f"Data quality issue: {e}")
       # Handle insufficient data (e.g., skip training, use fallback)

For weighted completeness across multiple columns:

.. code-block:: python

   checker = CompletenessChecker(
       columns=["load", "temperature", "windspeed"],
       weights={"load": 1.0, "temperature": 0.5, "windspeed": 0.3},
       min_completeness=0.85
   )

Handling Missing Values
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF workflows automatically drop rows with missing target values during training:

.. code-block:: python

   # Training automatically handles missing targets
   workflow = ForecastingWorkflow(
       target_column="load",
       ...
   )
   
   # Rows with NaN in 'load' column are dropped before fitting
   workflow.fit(data=training_data)

For missing feature values, apply imputation before passing data to workflows:

.. code-block:: python

   import pandas as pd

   # Forward-fill missing weather data
   df = dataset.to_pandas()
   df["temperature"] = df["temperature"].fillna(method="ffill", limit=4)
   df["windspeed"] = df["windspeed"].fillna(method="ffill", limit=4)
   
   # Interpolate for longer gaps
   df["solar_radiation"] = df["solar_radiation"].interpolate(method="time", limit=12)
   
   dataset = TimeSeriesDataset(data=df, sample_interval=dataset.sample_interval)

Data Validation
---------------

Validate dataset structure and content before processing to catch issues early.

Column Validation
^^^^^^^^^^^^^^^^^

Check for required columns:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns

   required = ["load", "temperature", "windspeed", "solar_radiation"]
   
   try:
       validate_required_columns(dataset.data, required)
   except MissingColumnsError as e:
       print(f"Missing columns: {e}")

Horizon Validation
^^^^^^^^^^^^^^^^^^

For versioned datasets, validate that required forecast horizons are present:

.. code-block:: python

   from openstef_core.datasets.validation import validate_horizons_present

   required_horizons = [0.25, 0.5, 1.0, 24.0, 47.0]  # hours
   
   try:
       validate_horizons_present(versioned_dataset, required_horizons)
   except TimeSeriesValidationError as e:
       print(f"Missing horizons: {e}")

Complete Pipeline Example
--------------------------

Here's a realistic end-to-end data pipeline integrating multiple sources:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_models.workflows import ForecastingWorkflow
   from openstef_models.transforms.validation import CompletenessChecker

   # 1. Load historical load data from PostgreSQL
   db_engine = create_engine("postgresql://user:pass@localhost/energy_db")
   load_df = pd.read_sql(
       "SELECT timestamp, load FROM measurements WHERE timestamp >= %s",
       db_engine,
       params=[datetime.now() - timedelta(days=90)],
       index_col="timestamp",
       parse_dates=["timestamp"]
   )

   # 2. Load weather forecasts from S3
   weather_df = pd.read_parquet(
       "s3://weather-data/forecasts/latest.parquet",
       storage_options={"key": "KEY", "secret": "SECRET"}
   )

   # 3. Combine into datasets
   load_data = TimeSeriesDataset(data=load_df, sample_interval=timedelta(minutes=15))
   weather_data = VersionedTimeSeriesDataset.read_parquet(
       path="s3://weather-data/forecasts/latest.parquet",
       sample_interval=timedelta(hours=1)
   )

   # 4. Validate data quality
   checker = CompletenessChecker(columns=["load"], min_completeness=0.9)
   load_data = checker.transform(load_data)

   # 5. Merge data sources
   combined = load_data.merge(weather_data, mode="outer")

   # 6. Generate forecast
   workflow = ForecastingWorkflow.from_config("config.yaml")
   workflow.fit(data=combined)
   forecast = workflow.predict(data=combined)

   # 7. Write forecast to database
   forecast_df = forecast.to_pandas().reset_index()
   forecast_df["created_at"] = pd.Timestamp.now()
   forecast_df.to_sql("forecasts", db_engine, if_exists="append", index=False)

This pattern separates concerns: data loading, validation, processing, and storage. Each step can be tested and monitored independently.

Custom Data Sources
-------------------

For proprietary systems or APIs, implement custom loaders that return pandas DataFrames:

.. code-block:: python

   def load_from_custom_api(location_id: str, start: datetime, end: datetime) -> TimeSeriesDataset:
       """Load data from custom energy management API."""
       import requests
       
       response = requests.get(
           f"https://api.example.com/measurements",
           params={
               "location": location_id,
               "start": start.isoformat(),
               "end": end.isoformat()
           }
       )
       
       data = response.json()
       df = pd.DataFrame(data["measurements"])
       df["timestamp"] = pd.to_datetime(df["timestamp"])
       df = df.set_index("timestamp")
       
       return TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(minutes=15)
       )

   # Use in pipeline
   dataset = load_from_custom_api("SUBSTATION_42", start_date, end_date)

See Also
--------

- :doc:`use_cases` - Common forecasting scenarios and patterns
- :doc:`deployment` - Production deployment strategies
- :doc:`logging` - Monitoring and debugging data pipelines