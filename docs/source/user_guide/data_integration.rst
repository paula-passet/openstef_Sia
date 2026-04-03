Data Integration
================

OpenSTEF is designed to integrate with your existing data infrastructure. This page covers practical patterns for reading data from various sources, writing forecasts back to storage, handling missing data, and validating data quality in your forecasting pipelines.

OpenSTEF doesn't prescribe a specific data storage solution. Instead, it provides flexible abstractions that work with pandas DataFrames, allowing you to integrate with any data source that can produce tabular time series data.

Reading Data from Sources
--------------------------

OpenSTEF works with standard pandas DataFrames wrapped in ``TimeSeriesDataset`` objects. This means you can load data from any source that pandas supports, then convert it to OpenSTEF's format.

Basic Pattern
^^^^^^^^^^^^^

The general pattern for loading data is:

1. Load data into a pandas DataFrame using your preferred method
2. Ensure the DataFrame has a datetime index
3. Wrap it in a ``TimeSeriesDataset``

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load from any pandas-compatible source
   df = pd.read_csv("energy_data.csv", index_col="timestamp", parse_dates=True)
   
   # Convert to OpenSTEF format
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1)
   )

PostgreSQL Integration
^^^^^^^^^^^^^^^^^^^^^^

For PostgreSQL databases, use pandas' built-in SQL support:

.. code-block:: python

   from sqlalchemy import create_engine
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Connect to database
   engine = create_engine("postgresql://user:password@localhost:5432/energy_db")
   
   # Query time series data
   query = """
       SELECT timestamp, load, temperature, wind_speed, solar_radiation
       FROM energy_measurements
       WHERE timestamp >= %s AND timestamp < %s
       ORDER BY timestamp
   """
   
   start_time = datetime(2025, 1, 1)
   end_time = datetime(2025, 4, 1)
   
   df = pd.read_sql_query(
       query,
       engine,
       params=(start_time, end_time),
       index_col="timestamp",
       parse_dates=["timestamp"]
   )
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

InfluxDB is commonly used for time series data. Here's how to integrate it:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Connect to InfluxDB
   client = InfluxDBClient(
       url="http://localhost:8086",
       token="your-token",
       org="your-org"
   )
   
   # Query data
   query = '''
   from(bucket: "energy_data")
       |> range(start: -90d)
       |> filter(fn: (r) => r["_measurement"] == "load")
       |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''
   
   query_api = client.query_api()
   result = query_api.query_data_frame(query)
   
   # Convert to OpenSTEF format
   df = result.set_index("_time")[["load", "temperature", "wind_speed"]]
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
   
   client.close()

S3 and Cloud Storage
^^^^^^^^^^^^^^^^^^^^

For S3 or other cloud storage, read files directly with pandas:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Read from S3 (requires s3fs installed)
   df = pd.read_parquet(
       "s3://my-bucket/energy-data/2025/Q1/data.parquet",
       storage_options={
           "key": "your-access-key",
           "secret": "your-secret-key"
       }
   )
   
   # Ensure datetime index
   if "timestamp" in df.columns:
       df = df.set_index("timestamp")
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

OpenSTEF Beam includes ``S3BenchmarkStorage`` for storing benchmark results in S3, which demonstrates a hybrid approach combining local caching with S3 synchronization.

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^^

When working with Databricks, convert Spark DataFrames to pandas:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Query from Databricks table
   spark_df = spark.sql("""
       SELECT timestamp, load, temperature, wind_speed
       FROM energy_data.measurements
       WHERE timestamp >= '2025-01-01'
       ORDER BY timestamp
   """)
   
   # Convert to pandas (be mindful of data size)
   df = spark_df.toPandas()
   df = df.set_index("timestamp")
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

For large datasets, consider filtering or aggregating in Spark before converting to pandas.

Writing Forecasts to Storage
-----------------------------

After generating forecasts, you'll typically want to persist them for downstream applications.

Writing to PostgreSQL
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from sqlalchemy import create_engine
   from openstef_core.workflows import ForecastingWorkflow
   
   # Generate forecasts
   workflow = ForecastingWorkflow.from_storage(
       model_id="grid_123",
       storage=my_storage
   )
   forecasts = workflow.predict(input_data)
   
   # Write to database
   engine = create_engine("postgresql://user:password@localhost:5432/energy_db")
   
   # Convert forecast dataset to DataFrame
   forecast_df = forecasts.data.reset_index()
   forecast_df["model_id"] = "grid_123"
   forecast_df["created_at"] = pd.Timestamp.now()
   
   # Write to table
   forecast_df.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False,
       method="multi"  # Faster bulk insert
   )

Writing to InfluxDB
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   
   client = InfluxDBClient(url="http://localhost:8086", token="your-token", org="your-org")
   write_api = client.write_api(write_options=SYNCHRONOUS)
   
   # Convert forecasts to InfluxDB points
   points = []
   for timestamp, row in forecasts.data.iterrows():
       point = (
           Point("forecast")
           .tag("model_id", "grid_123")
           .tag("horizon", row.get("horizon", "24h"))
           .field("load_q0.5", float(row["load_q0.5"]))
           .field("load_q0.1", float(row["load_q0.1"]))
           .field("load_q0.9", float(row["load_q0.9"]))
           .time(timestamp)
       )
       points.append(point)
   
   write_api.write(bucket="forecasts", record=points)
   client.close()

Writing to S3
^^^^^^^^^^^^^

.. code-block:: python

   from datetime import datetime
   
   # Generate forecasts
   forecasts = workflow.predict(input_data)
   
   # Write to S3 as parquet
   forecast_date = datetime.now().strftime("%Y-%m-%d")
   s3_path = f"s3://my-bucket/forecasts/grid_123/{forecast_date}/forecast.parquet"
   
   forecasts.data.to_parquet(
       s3_path,
       storage_options={
           "key": "your-access-key",
           "secret": "your-secret-key"
       }
   )

Handling Missing Data
---------------------

Real-world data often has gaps. OpenSTEF provides several strategies for handling missing data.

Validation and Detection
^^^^^^^^^^^^^^^^^^^^^^^^

Use OpenSTEF's validation utilities to detect missing data:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.exceptions import MissingColumnsError
   
   # Check for required columns
   try:
       validate_required_columns(
           df=dataset.data,
           required_columns=["load", "temperature", "wind_speed"]
       )
   except MissingColumnsError as e:
       print(f"Missing columns: {e}")
   
   # Check for missing values
   missing_summary = dataset.data.isnull().sum()
   if missing_summary.any():
       print("Missing values detected:")
       print(missing_summary[missing_summary > 0])

Dropping Missing Target Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF automatically drops rows with missing target values during training. The ``ForecastingModel`` validates this:

.. code-block:: python

   from openstef_core.models import ForecastingModel
   from openstef_core.forecasters import GBLinearForecaster
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   model = ForecastingModel(
       forecaster=GBLinearForecaster(horizons=[...]),
       target_column="load"
   )
   
   try:
       workflow.fit(dataset)
   except InsufficientlyCompleteError as e:
       print(f"Insufficient data: {e}")
       # Handle the error - perhaps fetch more data or skip training

Imputation Strategies
^^^^^^^^^^^^^^^^^^^^^

For missing feature values, you can impute before creating the dataset:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load data
   df = pd.read_csv("data.csv", index_col="timestamp", parse_dates=True)
   
   # Forward fill for short gaps (e.g., sensor dropouts)
   df["temperature"] = df["temperature"].fillna(method="ffill", limit=3)
   
   # Interpolate for longer gaps
   df["wind_speed"] = df["wind_speed"].interpolate(method="time")
   
   # Fill remaining with historical median
   df = df.fillna(df.median())
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Handling Lag-Based Feature Gaps
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Lag-based features create NaN values at the start of your dataset. Use ``cutoff_history`` to exclude these:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.models import ForecastingModel
   from openstef_core.preprocessing import TransformPipeline, LagTransform
   from openstef_core.feature_engineering import FeatureSelection
   
   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               LagTransform(
                   lags=[timedelta(days=1), timedelta(days=7), timedelta(days=14)],
                   selection=FeatureSelection(include={"load"})
               )
           ]
       ),
       forecaster=my_forecaster,
       cutoff_history=timedelta(days=14)  # Exclude first 14 days
   )

Data Validation
---------------

Robust data validation prevents training failures and poor forecast quality.

Schema Validation
^^^^^^^^^^^^^^^^^

Validate that your data has the expected structure:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.exceptions import MissingColumnsError
   
   def validate_energy_data(dataset):
       """Validate energy dataset schema and quality."""
       required_cols = ["load", "temperature", "wind_speed", "solar_radiation"]
       
       try:
           validate_required_columns(dataset.data, required_cols)
       except MissingColumnsError as e:
           raise ValueError(f"Dataset missing required columns: {e}")
       
       # Check data types
       if not pd.api.types.is_numeric_dtype(dataset.data["load"]):
           raise ValueError("Load column must be numeric")
       
       # Check for reasonable value ranges
       if (dataset.data["load"] < 0).any():
           raise ValueError("Load values cannot be negative")
       
       # Check temporal consistency
       if not dataset.data.index.is_monotonic_increasing:
           raise ValueError("Timestamps must be monotonically increasing")
       
       return True

Quality Checks
^^^^^^^^^^^^^^

Implement quality checks for data completeness and consistency:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   
   def check_data_quality(dataset, max_gap_hours=6, min_completeness=0.95):
       """Check data quality metrics."""
       data = dataset.data
       
       # Check completeness
       completeness = 1 - (data.isnull().sum() / len(data))
       if (completeness < min_completeness).any():
           incomplete_cols = completeness[completeness < min_completeness]
           print(f"Warning: Low completeness in columns: {incomplete_cols.to_dict()}")
       
       # Check for large time gaps
       time_diffs = data.index.to_series().diff()
       max_gap = time_diffs.max()
       expected_interval = dataset.sample_interval
       
       if max_gap > expected_interval * max_gap_hours:
           print(f"Warning: Large time gap detected: {max_gap}")
       
       # Check for duplicates
       if data.index.duplicated().any():
           raise ValueError("Duplicate timestamps detected")
       
       return True

Complete Pipeline Example
--------------------------

Here's a complete example integrating data loading, validation, forecasting, and storage:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.workflows import ForecastingWorkflow
   from openstef_core.storage import LocalStorage
   
   def run_forecasting_pipeline(model_id, start_date, end_date):
       """Complete forecasting pipeline with data integration."""
       
       # 1. Load data from PostgreSQL
       engine = create_engine("postgresql://user:password@localhost/energy_db")
       query = """
           SELECT timestamp, load, temperature, wind_speed, solar_radiation
           FROM measurements
           WHERE timestamp >= %s AND timestamp < %s
           ORDER BY timestamp
       """
       df = pd.read_sql_query(
           query,
           engine,
           params=(start_date, end_date),
           index_col="timestamp",
           parse_dates=["timestamp"]
       )
       
       # 2. Validate and clean data
       required_columns = ["load", "temperature", "wind_speed", "solar_radiation"]
       validate_required_columns(df, required_columns)
       
       # Handle missing values
       df = df.fillna(method="ffill", limit=3)
       df = df.interpolate(method="time")
       
       # 3. Create dataset
       dataset = TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(hours=1)
       )
       
       # 4. Load model and generate forecasts
       storage = LocalStorage(base_path="./models")
       workflow = ForecastingWorkflow.from_storage(
           model_id=model_id,
           storage=storage
       )
       
       forecasts = workflow.predict(dataset)
       
       # 5. Write forecasts back to database
       forecast_df = forecasts.data.reset_index()
       forecast_df["model_id"] = model_id
       forecast_df["created_at"] = pd.Timestamp.now()
       
       forecast_df.to_sql(
           "forecasts",
           engine,
           if_exists="append",
           index=False
       )
       
       print(f"Generated {len(forecast_df)} forecast points for {model_id}")
       return forecasts
   
   # Run pipeline
   forecasts = run_forecasting_pipeline(
       model_id="grid_123",
       start_date=datetime(2025, 1, 1),
       end_date=datetime(2025, 4, 1)
   )

Custom Data Sources
-------------------

For custom data sources, implement a simple adapter:

.. code-block:: python

   from abc import ABC, abstractmethod
   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   class DataSourceAdapter(ABC):
       """Abstract adapter for custom data sources."""
       
       @abstractmethod
       def load_data(self, start: datetime, end: datetime) -> pd.DataFrame:
           """Load data from source."""
           pass
       
       def to_dataset(self, start: datetime, end: datetime, 
                      sample_interval: timedelta) -> TimeSeriesDataset:
           """Load and convert to OpenSTEF dataset."""
           df = self.load_data(start, end)
           return TimeSeriesDataset(data=df, sample_interval=sample_interval)
   
   class CustomAPIAdapter(DataSourceAdapter):
       """Example adapter for a custom API."""
       
       def __init__(self, api_url: str, api_key: str):
           self.api_url = api_url
           self.api_key = api_key
       
       def load_data(self, start: datetime, end: datetime) -> pd.DataFrame:
           """Load data from custom API."""
           import requests
           
           response = requests.get(
               f"{self.api_url}/timeseries",
               params={
                   "start": start.isoformat(),
                   "end": end.isoformat()
               },
               headers={"Authorization": f"Bearer {self.api_key}"}
           )
           response.raise_for_status()
           
           data = response.json()
           df = pd.DataFrame(data["measurements"])
           df["timestamp"] = pd.to_datetime(df["timestamp"])
           df = df.set_index("timestamp")
           
           return df

See Also
--------

- :doc:`use_cases` - Common forecasting use cases and patterns
- :doc:`deployment` - Production deployment strategies
- :doc:`logging` - Logging configuration for data pipelines