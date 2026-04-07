Data Integration
=================

OpenSTEF is a library that integrates into your data infrastructure. This page shows how to connect OpenSTEF to various data sources, write forecasts back to storage, and handle data quality issues in production pipelines.

Reading Data from Sources
--------------------------

OpenSTEF works with time series data through the ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` classes. These can be constructed from pandas DataFrames, making it straightforward to integrate with any data source that pandas supports.

Basic Pattern
^^^^^^^^^^^^^

The fundamental pattern for data integration is: read data from your source into a pandas DataFrame, then wrap it in the appropriate dataset class:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Read from your data source
   df = pd.read_csv("energy_data.csv", parse_dates=["timestamp"])
   df = df.set_index("timestamp")
   
   # Wrap in OpenSTEF dataset
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1)
   )

For versioned data (where you have multiple forecasts made at different times), use ``VersionedTimeSeriesDataset``:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # DataFrame with 'timestamp' and 'available_at' columns
   df = pd.read_parquet("versioned_forecasts.parquet")
   
   dataset = VersionedTimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1),
       timestamp_column="timestamp",
       available_at_column="available_at"
   )

Reading from Databases
^^^^^^^^^^^^^^^^^^^^^^

PostgreSQL and other SQL databases integrate through pandas' database connectors:

.. code-block:: python

   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset
   
   # Connect to PostgreSQL
   engine = create_engine("postgresql://user:password@host:5432/database")
   
   # Query historical data
   query = """
       SELECT timestamp, load, temperature, windspeed
       FROM energy_measurements
       WHERE timestamp >= %s AND timestamp < %s
       ORDER BY timestamp
   """
   
   df = pd.read_sql(
       query,
       engine,
       params=["2024-01-01", "2024-02-01"],
       parse_dates=["timestamp"],
       index_col="timestamp"
   )
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

For InfluxDB, use the InfluxDB client library:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   
   # Connect to InfluxDB
   client = InfluxDBClient(url="http://localhost:8086", token="your-token", org="your-org")
   query_api = client.query_api()
   
   # Query data
   query = '''
       from(bucket: "energy")
           |> range(start: -30d)
           |> filter(fn: (r) => r["_measurement"] == "load")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''
   
   result = query_api.query_data_frame(query)
   result = result.set_index("_time")
   result.index.name = "timestamp"
   
   dataset = TimeSeriesDataset(data=result, sample_interval=timedelta(minutes=15))

Reading from Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For S3 and similar cloud storage, pandas can read directly from URLs or you can use cloud-specific libraries:

.. code-block:: python

   import pandas as pd
   import boto3
   from io import BytesIO
   
   # Using pandas with S3 URLs (requires s3fs)
   df = pd.read_parquet("s3://my-bucket/energy-data/2024/01/data.parquet")
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))
   
   # Or using boto3 for more control
   s3 = boto3.client("s3")
   obj = s3.get_object(Bucket="my-bucket", Key="energy-data/2024/01/data.parquet")
   df = pd.read_parquet(BytesIO(obj["Body"].read()))
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

For Databricks, use the Databricks SQL connector or read from Delta tables:

.. code-block:: python

   from databricks import sql
   import pandas as pd
   
   # Connect to Databricks SQL warehouse
   connection = sql.connect(
       server_hostname="your-workspace.cloud.databricks.com",
       http_path="/sql/1.0/warehouses/your-warehouse-id",
       access_token="your-token"
   )
   
   cursor = connection.cursor()
   cursor.execute("SELECT * FROM energy_schema.load_measurements WHERE date >= '2024-01-01'")
   
   df = cursor.fetchall_arrow().to_pandas()
   df = df.set_index("timestamp")
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Custom Data Providers
^^^^^^^^^^^^^^^^^^^^^

For reusable data integration patterns, create custom provider classes. This is particularly useful when working with the benchmarking pipeline:

.. code-block:: python

   from openstef_models.benchmarking import TargetProvider, BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class CustomDatabaseProvider(TargetProvider):
       """Provides benchmark targets from a custom database."""
       
       def __init__(self, db_connection):
           self.db = db_connection
       
       def get_targets(self):
           """Return list of available forecast targets."""
           targets_df = pd.read_sql("SELECT * FROM forecast_targets", self.db)
           return [
               BenchmarkTarget(
                   name=row["target_id"],
                   metadata={"location": row["location"], "type": row["type"]}
               )
               for _, row in targets_df.iterrows()
           ]
       
       def get_training_data(self, target):
           """Load training data for a specific target."""
           query = """
               SELECT timestamp, load, temperature, windspeed
               FROM measurements
               WHERE target_id = %s AND timestamp >= %s
               ORDER BY timestamp
           """
           df = pd.read_sql(
               query,
               self.db,
               params=[target.name, "2023-01-01"],
               parse_dates=["timestamp"],
               index_col="timestamp"
           )
           return TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Writing Forecasts to Storage
-----------------------------

After generating forecasts, you typically need to write them back to a database or storage system for downstream use.

Writing to Databases
^^^^^^^^^^^^^^^^^^^^

Write forecast results to PostgreSQL or other SQL databases:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from sqlalchemy import create_engine
   
   # Generate forecast
   workflow = CustomForecastingWorkflow(...)
   forecast = workflow.predict(data=input_data)
   
   # Write to database
   engine = create_engine("postgresql://user:password@host:5432/database")
   
   forecast_df = forecast.data.reset_index()
   forecast_df["forecast_created_at"] = pd.Timestamp.now()
   forecast_df["model_version"] = "v4.2"
   
   forecast_df.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False,
       method="multi"  # Faster bulk insert
   )

For time-versioned forecasts (tracking when each forecast was made):

.. code-block:: python

   # forecast is a ForecastDataset with forecast_start
   forecast_df = forecast.data.reset_index()
   forecast_df["forecast_start"] = forecast.forecast_start
   forecast_df["created_at"] = pd.Timestamp.now()
   
   # Store with temporal versioning
   forecast_df.to_sql("versioned_forecasts", engine, if_exists="append", index=False)

Writing to Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^

Write forecasts to S3, Azure Blob Storage, or Google Cloud Storage:

.. code-block:: python

   import boto3
   from datetime import datetime
   
   # Generate forecast
   forecast = workflow.predict(data=input_data)
   
   # Write to S3 as parquet
   s3_path = f"s3://forecasts-bucket/predictions/{datetime.now():%Y/%m/%d}/forecast.parquet"
   forecast.to_parquet(s3_path)
   
   # Or using boto3 for more control
   s3 = boto3.client("s3")
   buffer = BytesIO()
   forecast.data.to_parquet(buffer)
   
   s3.put_object(
       Bucket="forecasts-bucket",
       Key=f"predictions/{datetime.now():%Y/%m/%d}/forecast.parquet",
       Body=buffer.getvalue(),
       Metadata={"model_version": "v4.2", "forecast_start": str(forecast.forecast_start)}
   )

Custom Storage Backends
^^^^^^^^^^^^^^^^^^^^^^^

For benchmarking workflows, implement custom storage backends:

.. code-block:: python

   from openstef_models.benchmarking import BenchmarkStorage
   from openstef_core.datasets import TimeSeriesDataset
   
   class DatabaseStorage(BenchmarkStorage):
       """Store benchmark results in a database."""
       
       def __init__(self, db_connection):
           self.db = db_connection
       
       def save_backtest_output(self, target, output):
           """Store forecast data preserving temporal versioning."""
           df = output.data.reset_index()
           df["target_id"] = target.name
           df["stored_at"] = pd.Timestamp.now()
           
           df.to_sql(
               "backtest_predictions",
               self.db,
               if_exists="append",
               index=False
           )
       
       def load_backtest_output(self, target):
           """Retrieve data maintaining temporal versioning structure."""
           query = """
               SELECT * FROM backtest_predictions
               WHERE target_id = %s
               ORDER BY timestamp
           """
           df = pd.read_sql(
               query,
               self.db,
               params=[target.name],
               parse_dates=["timestamp"],
               index_col="timestamp"
           )
           return TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Handling Missing Data
---------------------

Real-world data pipelines frequently encounter missing values. OpenSTEF provides several mechanisms to handle this.

Validation During Loading
^^^^^^^^^^^^^^^^^^^^^^^^^^

Validate data completeness when loading:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   
   # Load data
   df = pd.read_csv("energy_data.csv", parse_dates=["timestamp"], index_col="timestamp")
   
   # Validate required columns exist
   required_columns = ["load", "temperature", "windspeed"]
   validate_required_columns(df, required_columns)
   
   # Check for missing values in critical columns
   if df["load"].isna().any():
       missing_count = df["load"].isna().sum()
       print(f"Warning: {missing_count} missing load values")
       
       # Option 1: Drop rows with missing target values
       df = df.dropna(subset=["load"])
       
       # Option 2: Fill with interpolation
       df["load"] = df["load"].interpolate(method="time")

Training with Missing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF models automatically handle missing target values during training:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   
   # Data with some missing load values
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))
   
   workflow = CustomForecastingWorkflow(target_column="load", ...)
   
   # Fit automatically drops rows where target is NaN
   # This raises InsufficientlyCompleteError if too much data is missing
   try:
       workflow.fit(data=dataset)
   except InsufficientlyCompleteError as e:
       print(f"Not enough training data: {e}")
       # Handle insufficient data (e.g., skip this target, use fallback model)

For feature columns with missing values, apply transforms before fitting:

.. code-block:: python

   from openstef_core.transforms import FillNA
   
   # Fill missing feature values
   dataset = dataset.pipe_pandas(lambda df: df.fillna(method="ffill"))
   
   # Or use a transform in the preprocessing pipeline
   workflow = CustomForecastingWorkflow(
       target_column="load",
       preprocessing=[
           FillNA(columns=["temperature", "windspeed"], method="interpolate")
       ],
       ...
   )

Handling Gaps in Time Series
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Reindex data to ensure consistent time intervals:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   
   # Load data that may have gaps
   df = pd.read_sql(query, engine, parse_dates=["timestamp"], index_col="timestamp")
   
   # Create complete time range
   expected_index = pd.date_range(
       start=df.index.min(),
       end=df.index.max(),
       freq="1h"
   )
   
   # Reindex and fill gaps
   df = df.reindex(expected_index)
   
   # Fill missing values appropriately for each column
   df["load"] = df["load"].interpolate(method="time")
   df["temperature"] = df["temperature"].interpolate(method="time")
   df["is_holiday"] = df["is_holiday"].fillna(False)  # Categorical features
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Data Validation
---------------

Validate data quality before training or prediction to catch issues early.

Input Consistency Checking
^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes built-in validation transforms:

.. code-block:: python

   from openstef_models.transforms.validation import InputConsistencyChecker
   
   # Add to preprocessing pipeline
   workflow = CustomForecastingWorkflow(
       target_column="load",
       preprocessing=[
           InputConsistencyChecker(),  # Validates features match training
           ...
       ],
       ...
   )
   
   # During prediction, this will:
   # - Warn if extra columns are present (and remove them)
   # - Raise error if required columns are missing
   # - Ensure consistent column ordering

Custom Validation
^^^^^^^^^^^^^^^^^

Implement custom validation for domain-specific requirements:

.. code-block:: python

   from openstef_core.exceptions import TimeSeriesValidationError
   
   def validate_energy_data(df):
       """Validate energy data meets domain requirements."""
       
       # Check load values are non-negative
       if (df["load"] < 0).any():
           raise TimeSeriesValidationError("Load values cannot be negative")
       
       # Check temperature is in reasonable range
       if (df["temperature"] < -50).any() or (df["temperature"] > 60).any():
           raise TimeSeriesValidationError("Temperature values out of reasonable range")
       
       # Check for sufficient data density
       expected_rows = (df.index.max() - df.index.min()) / timedelta(hours=1) + 1
       actual_rows = len(df)
       completeness = actual_rows / expected_rows
       
       if completeness < 0.8:
           raise TimeSeriesValidationError(
               f"Data only {completeness:.1%} complete, need at least 80%"
           )
       
       return df
   
   # Use in pipeline
   df = pd.read_sql(query, engine, parse_dates=["timestamp"], index_col="timestamp")
   df = validate_energy_data(df)
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Complete Pipeline Example
--------------------------

Here's a realistic end-to-end data integration pipeline:

.. code-block:: python

   import pandas as pd
   from sqlalchemy import create_engine
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_models.workflows import CustomForecastingWorkflow
   
   # Configuration
   DB_URL = "postgresql://user:password@host:5432/energy_db"
   REQUIRED_COLUMNS = ["load", "temperature", "windspeed", "solar_radiation"]
   
   def load_training_data(target_id, start_date, end_date):
       """Load and validate training data from database."""
       engine = create_engine(DB_URL)
       
       query = """
           SELECT timestamp, load, temperature, windspeed, solar_radiation
           FROM measurements
           WHERE target_id = %s
             AND timestamp >= %s
             AND timestamp < %s
           ORDER BY timestamp
       """
       
       df = pd.read_sql(
           query,
           engine,
           params=[target_id, start_date, end_date],
           parse_dates=["timestamp"],
           index_col="timestamp"
       )
       
       # Validate
       validate_required_columns(df, REQUIRED_COLUMNS)
       
       # Handle missing values
       df = df.interpolate(method="time", limit=3)  # Max 3 consecutive NaNs
       df = df.dropna()  # Drop remaining gaps
       
       # Ensure consistent frequency
       expected_index = pd.date_range(
           start=df.index.min(),
           end=df.index.max(),
           freq="1h"
       )
       df = df.reindex(expected_index).interpolate(method="time")
       
       return TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))
   
   def save_forecast(target_id, forecast, model_version):
       """Save forecast to database."""
       engine = create_engine(DB_URL)
       
       df = forecast.data.reset_index()
       df["target_id"] = target_id
       df["forecast_start"] = forecast.forecast_start
       df["created_at"] = pd.Timestamp.now()
       df["model_version"] = model_version
       
       df.to_sql(
           "forecasts",
           engine,
           if_exists="append",
           index=False,
           method="multi"
       )
   
   # Run pipeline
   target_id = "grid_section_123"
   training_data = load_training_data(target_id, "2023-01-01", "2024-01-01")
   
   workflow = CustomForecastingWorkflow(target_column="load", horizons=[1, 6, 24])
   workflow.fit(data=training_data)
   
   # Load recent data for prediction
   predict_data = load_training_data(target_id, "2024-01-01", "2024-01-15")
   forecast = workflow.predict(data=predict_data)
   
   save_forecast(target_id, forecast, model_version="v4.2")

For production deployment patterns and monitoring, see :doc:`deployment`. For logging configuration in data pipelines, see :doc:`logging`.