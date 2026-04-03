Data Integration
=================

OpenSTEF is a library designed to integrate into your existing data infrastructure. This page covers practical patterns for reading input data from various sources, writing forecasts back to storage systems, and handling data quality issues that arise in production pipelines.

Overview
--------

A typical OpenSTEF data integration workflow involves:

1. **Reading input data** from your storage system (database, data lake, files)
2. **Validating and preparing** the data for forecasting
3. **Running forecasts** using OpenSTEF models
4. **Writing results** back to your storage system
5. **Handling missing data** and validation errors

OpenSTEF provides the core forecasting functionality as a library. You're responsible for implementing the data integration layer that connects OpenSTEF to your specific infrastructure.

Reading Data from Storage Systems
----------------------------------

OpenSTEF works with ``TimeSeriesDataset`` objects. Your integration code needs to load data from your storage system and convert it to this format.

Basic Pattern
^^^^^^^^^^^^^

The fundamental pattern for loading data:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load data from your source (example: CSV file)
   df = pd.read_csv("energy_data.csv", parse_dates=["timestamp"])
   df = df.set_index("timestamp")
   
   # Convert to OpenSTEF dataset
   dataset = TimeSeriesDataset.from_pandas(
       df=df,
       sample_interval=pd.Timedelta("15min")
   )

The ``from_pandas`` method is your primary entry point. It accepts any pandas DataFrame with a datetime index and converts it to OpenSTEF's internal format.

PostgreSQL Integration
^^^^^^^^^^^^^^^^^^^^^^

Reading from a PostgreSQL database:

.. code-block:: python

   import pandas as pd
   import psycopg2
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_postgres(connection_string, query, sample_interval):
       """Load time series data from PostgreSQL."""
       conn = psycopg2.connect(connection_string)
       
       # Load data with timestamp as index
       df = pd.read_sql_query(
           query,
           conn,
           parse_dates=["timestamp"],
           index_col="timestamp"
       )
       conn.close()
       
       # Convert to OpenSTEF dataset
       return TimeSeriesDataset.from_pandas(
           df=df,
           sample_interval=sample_interval
       )
   
   # Usage
   dataset = load_from_postgres(
       connection_string="postgresql://user:pass@host:5432/db",
       query="""
           SELECT timestamp, load, temperature, wind_speed
           FROM energy_measurements
           WHERE timestamp >= NOW() - INTERVAL '30 days'
           ORDER BY timestamp
       """,
       sample_interval=pd.Timedelta("15min")
   )

InfluxDB Integration
^^^^^^^^^^^^^^^^^^^^

Reading from InfluxDB:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_influxdb(url, token, org, bucket, measurement, start_time):
       """Load time series data from InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       query_api = client.query_api()
       
       query = f'''
           from(bucket: "{bucket}")
               |> range(start: {start_time})
               |> filter(fn: (r) => r["_measurement"] == "{measurement}")
               |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
       '''
       
       # Execute query and convert to DataFrame
       result = query_api.query_data_frame(query)
       client.close()
       
       # Prepare DataFrame
       df = result.set_index("_time")
       df.index.name = "timestamp"
       
       # Select only feature columns (remove InfluxDB metadata)
       feature_cols = [col for col in df.columns 
                      if not col.startswith("_") and col not in ["result", "table"]]
       df = df[feature_cols]
       
       return TimeSeriesDataset.from_pandas(
           df=df,
           sample_interval=pd.Timedelta("15min")
       )

S3 / Cloud Storage Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Reading from S3 or similar cloud storage:

.. code-block:: python

   import pandas as pd
   import s3fs
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_s3(bucket, key, aws_access_key_id, aws_secret_access_key):
       """Load time series data from S3."""
       # Create S3 filesystem
       fs = s3fs.S3FileSystem(
           key=aws_access_key_id,
           secret=aws_secret_access_key
       )
       
       # Read CSV from S3
       with fs.open(f"{bucket}/{key}", "rb") as f:
           df = pd.read_csv(f, parse_dates=["timestamp"], index_col="timestamp")
       
       return TimeSeriesDataset.from_pandas(
           df=df,
           sample_interval=pd.Timedelta("15min")
       )
   
   # For Parquet files (more efficient for large datasets)
   def load_parquet_from_s3(bucket, key, aws_access_key_id, aws_secret_access_key):
       """Load time series data from S3 Parquet file."""
       fs = s3fs.S3FileSystem(
           key=aws_access_key_id,
           secret=aws_secret_access_key
       )
       
       with fs.open(f"{bucket}/{key}", "rb") as f:
           df = pd.read_parquet(f)
       
       if "timestamp" in df.columns:
           df = df.set_index("timestamp")
       
       return TimeSeriesDataset.from_pandas(
           df=df,
           sample_interval=pd.Timedelta("15min")
       )

Databricks Integration
^^^^^^^^^^^^^^^^^^^^^^^

Reading from Databricks Delta tables:

.. code-block:: python

   from pyspark.sql import SparkSession
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_databricks(table_name, start_date, end_date):
       """Load time series data from Databricks Delta table."""
       spark = SparkSession.builder.getOrCreate()
       
       # Query Delta table
       df_spark = spark.sql(f"""
           SELECT timestamp, load, temperature, wind_speed
           FROM {table_name}
           WHERE timestamp BETWEEN '{start_date}' AND '{end_date}'
           ORDER BY timestamp
       """)
       
       # Convert to pandas (use .toPandas() for smaller datasets)
       df = df_spark.toPandas()
       df = df.set_index("timestamp")
       
       return TimeSeriesDataset.from_pandas(
           df=df,
           sample_interval=pd.Timedelta("15min")
       )

Writing Forecasts to Storage
-----------------------------

After generating forecasts, you need to write the results back to your storage system. OpenSTEF forecasting models return predictions as pandas DataFrames, which you can write to any destination.

Basic Pattern
^^^^^^^^^^^^^

.. code-block:: python

   from openstef_models.forecasting import ForecastingModel
   
   # Generate forecast
   predictions = model.predict(data=input_data)
   
   # predictions is a pandas DataFrame with:
   # - Index: forecast timestamps
   # - Columns: forecast values and optionally quantiles
   
   # Write to your storage system
   write_to_storage(predictions)

Writing to PostgreSQL
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import psycopg2
   from sqlalchemy import create_engine
   
   def write_forecasts_to_postgres(predictions, connection_string, table_name):
       """Write forecast results to PostgreSQL."""
       engine = create_engine(connection_string)
       
       # Reset index to include timestamp as column
       df = predictions.reset_index()
       df.rename(columns={"index": "forecast_timestamp"}, inplace=True)
       
       # Add metadata columns
       df["created_at"] = pd.Timestamp.now()
       df["model_version"] = "v4.0"
       
       # Write to database (append mode)
       df.to_sql(
           table_name,
           engine,
           if_exists="append",
           index=False,
           method="multi"  # Faster bulk insert
       )
       
       engine.dispose()

Writing to InfluxDB
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   
   def write_forecasts_to_influxdb(predictions, url, token, org, bucket, measurement):
       """Write forecast results to InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       write_api = client.write_api(write_options=SYNCHRONOUS)
       
       # Convert predictions to InfluxDB points
       points = []
       for timestamp, row in predictions.iterrows():
           point = Point(measurement) \
               .time(timestamp) \
               .field("forecast", float(row["forecast"])) \
               .tag("model_type", "openstef")
           
           # Add quantile fields if present
           for col in row.index:
               if col.startswith("quantile_"):
                   point = point.field(col, float(row[col]))
           
           points.append(point)
       
       # Write batch
       write_api.write(bucket=bucket, org=org, record=points)
       client.close()

Writing to S3
^^^^^^^^^^^^^

.. code-block:: python

   import s3fs
   from datetime import datetime
   
   def write_forecasts_to_s3(predictions, bucket, prefix, aws_access_key_id, 
                             aws_secret_access_key):
       """Write forecast results to S3 as Parquet."""
       fs = s3fs.S3FileSystem(
           key=aws_access_key_id,
           secret=aws_secret_access_key
       )
       
       # Create timestamped filename
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       key = f"{prefix}/forecasts_{timestamp}.parquet"
       
       # Write as Parquet (more efficient than CSV)
       with fs.open(f"{bucket}/{key}", "wb") as f:
           predictions.to_parquet(f, compression="snappy")
       
       return f"s3://{bucket}/{key}"

Complete Data Pipeline Example
-------------------------------

Here's a realistic end-to-end pipeline that reads from PostgreSQL, generates forecasts, and writes results back:

.. code-block:: python

   import pandas as pd
   import psycopg2
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.forecasting import ForecastingModel
   from openstef_models.storage import LocalModelStorage
   import logging
   
   logger = logging.getLogger(__name__)
   
   class ForecastPipeline:
       """Complete forecasting pipeline with data integration."""
       
       def __init__(self, db_connection_string, model_storage_path):
           self.db_connection = db_connection_string
           self.model_storage = LocalModelStorage(base_path=model_storage_path)
       
       def load_input_data(self, location_id, lookback_days=30):
           """Load historical data for forecasting."""
           engine = create_engine(self.db_connection)
           
           query = f"""
               SELECT timestamp, load, temperature, wind_speed, solar_radiation
               FROM energy_measurements
               WHERE location_id = '{location_id}'
                 AND timestamp >= NOW() - INTERVAL '{lookback_days} days'
               ORDER BY timestamp
           """
           
           df = pd.read_sql_query(
               query,
               engine,
               parse_dates=["timestamp"],
               index_col="timestamp"
           )
           engine.dispose()
           
           # Validate data before creating dataset
           if df.empty:
               raise ValueError(f"No data found for location {location_id}")
           
           logger.info(f"Loaded {len(df)} rows for location {location_id}")
           
           return TimeSeriesDataset.from_pandas(
               df=df,
               sample_interval=pd.Timedelta("15min")
           )
       
       def generate_forecast(self, location_id):
           """Generate forecast for a location."""
           # Load input data
           input_data = self.load_input_data(location_id)
           
           # Load trained model
           model = self.model_storage.load(model_id=location_id)
           
           # Generate predictions
           predictions = model.predict(data=input_data)
           
           logger.info(f"Generated {len(predictions)} forecast points")
           
           return predictions
       
       def save_forecasts(self, location_id, predictions):
           """Save forecast results to database."""
           engine = create_engine(self.db_connection)
           
           # Prepare forecast data
           df = predictions.reset_index()
           df.rename(columns={"index": "forecast_timestamp"}, inplace=True)
           df["location_id"] = location_id
           df["created_at"] = pd.Timestamp.now()
           
           # Write to database
           df.to_sql(
               "forecasts",
               engine,
               if_exists="append",
               index=False,
               method="multi"
           )
           
           engine.dispose()
           logger.info(f"Saved forecasts for location {location_id}")
       
       def run(self, location_id):
           """Execute complete forecasting pipeline."""
           try:
               predictions = self.generate_forecast(location_id)
               self.save_forecasts(location_id, predictions)
               return predictions
           except Exception as e:
               logger.error(f"Pipeline failed for {location_id}: {e}")
               raise
   
   # Usage
   pipeline = ForecastPipeline(
       db_connection_string="postgresql://user:pass@host:5432/db",
       model_storage_path="/models"
   )
   
   predictions = pipeline.run(location_id="substation_123")

Handling Missing Data
---------------------

Real-world data often has gaps, outliers, and quality issues. OpenSTEF provides validation but you need to handle missing data appropriately for your use case.

Detecting Missing Data
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   def analyze_data_quality(dataset: TimeSeriesDataset):
       """Analyze data quality and missing values."""
       df = dataset.data
       
       # Check for missing values
       missing_counts = df.isnull().sum()
       missing_pct = (missing_counts / len(df)) * 100
       
       print("Missing data summary:")
       for col in df.columns:
           if missing_counts[col] > 0:
               print(f"  {col}: {missing_counts[col]} ({missing_pct[col]:.1f}%)")
       
       # Check for gaps in time series
       expected_freq = dataset.sample_interval
       actual_gaps = df.index.to_series().diff()
       large_gaps = actual_gaps[actual_gaps > expected_freq]
       
       if len(large_gaps) > 0:
           print(f"\nFound {len(large_gaps)} gaps larger than {expected_freq}")
           print("Largest gaps:")
           print(large_gaps.nlargest(5))
       
       return {
           "missing_counts": missing_counts.to_dict(),
           "missing_percentages": missing_pct.to_dict(),
           "time_gaps": len(large_gaps)
       }

Handling Strategies
^^^^^^^^^^^^^^^^^^^

Different strategies for handling missing data:

.. code-block:: python

   def handle_missing_data(dataset: TimeSeriesDataset, strategy="forward_fill"):
       """Handle missing data with various strategies."""
       df = dataset.data.copy()
       
       if strategy == "forward_fill":
           # Forward fill (carry last observation forward)
           df = df.fillna(method="ffill", limit=4)  # Limit to 4 periods
       
       elif strategy == "interpolate":
           # Linear interpolation
           df = df.interpolate(method="linear", limit=4)
       
       elif strategy == "drop":
           # Drop rows with any missing values
           df = df.dropna()
       
       elif strategy == "median_fill":
           # Fill with median of each column
           df = df.fillna(df.median())
       
       elif strategy == "time_of_day_median":
           # Fill with median for same time of day
           for col in df.columns:
               df[col] = df.groupby(df.index.hour)[col].transform(
                   lambda x: x.fillna(x.median())
               )
       
       # Return new dataset with cleaned data
       return TimeSeriesDataset.from_pandas(
           df=df,
           sample_interval=dataset.sample_interval
       )

Data Validation
---------------

Validate data quality before forecasting to catch issues early:

.. code-block:: python

   from openstef_core.exceptions import InsufficientlyCompleteError
   
   def validate_input_data(dataset: TimeSeriesDataset, required_features):
       """Validate input data meets requirements for forecasting."""
       df = dataset.data
       
       # Check required features are present
       missing_features = set(required_features) - set(df.columns)
       if missing_features:
           raise ValueError(f"Missing required features: {missing_features}")
       
       # Check minimum data length
       min_length = 96  # e.g., 1 day at 15-min resolution
       if len(df) < min_length:
           raise ValueError(
               f"Insufficient data: {len(df)} rows, need at least {min_length}"
           )
       
       # Check for excessive missing data in target
       target_missing_pct = (df["load"].isnull().sum() / len(df)) * 100
       if target_missing_pct > 10:
           raise InsufficientlyCompleteError(
               f"Target has {target_missing_pct:.1f}% missing values (max 10%)"
           )
       
       # Check for data freshness
       latest_timestamp = df.index.max()
       age = pd.Timestamp.now() - latest_timestamp
       if age > pd.Timedelta("2 hours"):
           logger.warning(f"Data is {age} old, may be stale")
       
       # Check for outliers (simple z-score method)
       for col in df.select_dtypes(include=["float64", "int64"]).columns:
           z_scores = (df[col] - df[col].mean()) / df[col].std()
           outliers = (z_scores.abs() > 5).sum()
           if outliers > 0:
               logger.warning(f"Found {outliers} potential outliers in {col}")
       
       return True

Custom Data Source Integration
-------------------------------

For custom data sources, implement a data loader that converts your format to ``TimeSeriesDataset``:

.. code-block:: python

   from abc import ABC, abstractmethod
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class DataLoader(ABC):
       """Abstract base class for data loaders."""
       
       @abstractmethod
       def load(self, **kwargs) -> TimeSeriesDataset:
           """Load data and return TimeSeriesDataset."""
           pass
   
   class CustomAPILoader(DataLoader):
       """Load data from a custom REST API."""
       
       def __init__(self, api_url, api_key):
           self.api_url = api_url
           self.api_key = api_key
       
       def load(self, location_id, start_date, end_date) -> TimeSeriesDataset:
           """Load data from API."""
           import requests
           
           response = requests.get(
               f"{self.api_url}/timeseries",
               headers={"Authorization": f"Bearer {self.api_key}"},
               params={
                   "location": location_id,
                   "start": start_date.isoformat(),
                   "end": end_date.isoformat()
               }
           )
           response.raise_for_status()
           
           # Parse API response
           data = response.json()
           df = pd.DataFrame(data["measurements"])
           df["timestamp"] = pd.to_datetime(df["timestamp"])
           df = df.set_index("timestamp")
           
           return TimeSeriesDataset.from_pandas(
               df=df,
               sample_interval=pd.Timedelta(data["sample_interval"])
           )
   
   # Usage
   loader = CustomAPILoader(
       api_url="https://api.example.com",
       api_key="your-api-key"
   )
   
   dataset = loader.load(
       location_id="site_123",
       start_date=pd.Timestamp("2024-01-01"),
       end_date=pd.Timestamp("2024-01-31")
   )

Next Steps
----------

- See :doc:`deployment` for production deployment patterns
- See :doc:`logging` for monitoring data pipeline issues
- See :doc:`use_cases` for complete forecasting examples