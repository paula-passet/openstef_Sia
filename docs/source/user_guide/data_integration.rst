Data Integration
=================

OpenSTEF is a library that integrates into your existing data infrastructure. This page shows how to connect OpenSTEF to various data sources, write forecasts back to storage systems, validate incoming data, and handle missing values in production pipelines.

Data Source Patterns
--------------------

OpenSTEF operates on pandas DataFrames wrapped in dataset classes like ``ForecastInputDataset`` and ``TimeSeriesDataset``. You're responsible for loading data from your sources and converting it to the expected format.

Reading from Files
^^^^^^^^^^^^^^^^^^

The simplest integration pattern uses local files. OpenSTEF datasets provide built-in parquet support:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   
   # Load from parquet with metadata preserved
   dataset = TimeSeriesDataset.read_parquet(
       path="historical_data.parquet",
       sample_interval=timedelta(minutes=15)
   )
   
   # Save forecasts back to parquet
   forecast_result.to_parquet(path="forecast_output.parquet")

For CSV or other formats, load with pandas first:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import ForecastInputDataset
   
   # Load CSV with datetime index
   df = pd.read_csv(
       "load_data.csv",
       index_col="timestamp",
       parse_dates=True
   )
   
   # Wrap in OpenSTEF dataset
   input_data = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

Reading from Databases
^^^^^^^^^^^^^^^^^^^^^^

For SQL databases like PostgreSQL, use standard database connectors to query data, then wrap the result:

.. code-block:: python

   import psycopg2
   import pandas as pd
   from openstef_core.datasets import ForecastInputDataset
   from datetime import datetime, timedelta
   
   # Query PostgreSQL
   conn = psycopg2.connect(
       host="db.example.com",
       database="energy_data",
       user="forecaster"
   )
   
   query = """
       SELECT timestamp, load, temperature, wind_speed
       FROM measurements
       WHERE timestamp >= %s
       ORDER BY timestamp
   """
   
   df = pd.read_sql_query(
       query,
       conn,
       params=(datetime.now() - timedelta(days=30),),
       index_col="timestamp",
       parse_dates=["timestamp"]
   )
   
   conn.close()
   
   # Convert to OpenSTEF format
   input_data = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

Reading from Time Series Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

InfluxDB and similar time series databases follow the same pattern:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Query InfluxDB
   client = InfluxDBClient(
       url="https://influx.example.com",
       token="your-token",
       org="your-org"
   )
   
   query_api = client.query_api()
   query = '''
       from(bucket: "energy")
           |> range(start: -30d)
           |> filter(fn: (r) => r["_measurement"] == "load")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''
   
   result = query_api.query_data_frame(query)
   result.set_index("_time", inplace=True)
   
   client.close()
   
   # Wrap for OpenSTEF
   dataset = TimeSeriesDataset(
       data=result,
       sample_interval=timedelta(minutes=15)
   )

Reading from Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For S3, Azure Blob Storage, or Google Cloud Storage, use cloud-specific libraries to fetch data:

.. code-block:: python

   import boto3
   import pandas as pd
   from io import BytesIO
   from openstef_core.datasets import ForecastInputDataset
   
   # Read from S3
   s3_client = boto3.client('s3')
   response = s3_client.get_object(
       Bucket='energy-forecasting',
       Key='historical/load_2024.parquet'
   )
   
   # Load parquet from bytes
   df = pd.read_parquet(BytesIO(response['Body'].read()))
   
   # Convert to OpenSTEF dataset
   input_data = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

Reading from Databricks
^^^^^^^^^^^^^^^^^^^^^^^

When running in Databricks notebooks, access Delta tables directly:

.. code-block:: python

   from pyspark.sql import SparkSession
   from openstef_core.datasets import ForecastInputDataset
   from datetime import timedelta
   
   spark = SparkSession.builder.getOrCreate()
   
   # Query Delta table
   df_spark = spark.sql("""
       SELECT timestamp, load, temperature, wind_speed
       FROM energy_data.measurements
       WHERE timestamp >= current_date() - INTERVAL 30 DAYS
       ORDER BY timestamp
   """)
   
   # Convert to pandas
   df = df_spark.toPandas()
   df.set_index("timestamp", inplace=True)
   
   # Wrap for OpenSTEF
   input_data = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

Writing Forecasts to Storage
-----------------------------

After generating forecasts, write results back to your storage system.

Writing to Databases
^^^^^^^^^^^^^^^^^^^^

Write forecast results to PostgreSQL or other SQL databases:

.. code-block:: python

   import psycopg2
   from datetime import datetime
   
   # Generate forecast
   forecast = model.predict(input_data)
   
   # Extract forecast data
   forecast_df = forecast.data.reset_index()
   
   # Write to database
   conn = psycopg2.connect(
       host="db.example.com",
       database="energy_data",
       user="forecaster"
   )
   
   cursor = conn.cursor()
   
   for _, row in forecast_df.iterrows():
       cursor.execute(
           """
           INSERT INTO forecasts (timestamp, horizon, forecast_value, quantile, created_at)
           VALUES (%s, %s, %s, %s, %s)
           """,
           (row['timestamp'], row['horizon'], row['load'], 
            row.get('quantile', 0.5), datetime.now())
       )
   
   conn.commit()
   conn.close()

Writing to Time Series Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For InfluxDB, convert forecast results to the appropriate format:

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   
   client = InfluxDBClient(
       url="https://influx.example.com",
       token="your-token",
       org="your-org"
   )
   
   write_api = client.write_api(write_options=SYNCHRONOUS)
   
   # Convert forecast to InfluxDB points
   forecast_df = forecast.data.reset_index()
   
   points = []
   for _, row in forecast_df.iterrows():
       point = Point("forecast") \
           .tag("model", "xgboost") \
           .field("load", float(row['load'])) \
           .field("horizon", int(row['horizon'])) \
           .time(row['timestamp'])
       points.append(point)
   
   write_api.write(bucket="energy", record=points)
   client.close()

Writing to Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^

Save forecasts to S3 or other cloud storage:

.. code-block:: python

   import boto3
   from io import BytesIO
   
   # Generate forecast
   forecast = model.predict(input_data)
   
   # Convert to parquet bytes
   buffer = BytesIO()
   forecast.data.to_parquet(buffer)
   buffer.seek(0)
   
   # Upload to S3
   s3_client = boto3.client('s3')
   s3_client.put_object(
       Bucket='energy-forecasting',
       Key=f'forecasts/{datetime.now().isoformat()}.parquet',
       Body=buffer.getvalue()
   )

Custom Storage Backends
^^^^^^^^^^^^^^^^^^^^^^^

For benchmarking workflows, implement the ``BenchmarkStorage`` interface to integrate with custom storage systems:

.. code-block:: python

   from openstef_core.benchmarking.storage import BenchmarkStorage
   from openstef_core.benchmarking.target import BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   
   class DatabaseStorage(BenchmarkStorage):
       def __init__(self, db_connection):
           self.db = db_connection
       
       def save_backtest_output(self, target: BenchmarkTarget, 
                               output: TimeSeriesDataset) -> None:
           """Save backtest results to database."""
           self.db.save_predictions(
               target_id=target.name,
               predictions=output.data,
               metadata=target.metadata
           )
       
       def load_backtest_output(self, target: BenchmarkTarget) -> TimeSeriesDataset:
           """Load backtest results from database."""
           df = self.db.load_predictions(target_id=target.name)
           return TimeSeriesDataset(data=df)
       
       def save_evaluation_report(self, target: BenchmarkTarget, 
                                  report: dict) -> None:
           """Save evaluation metrics to database."""
           self.db.save_metrics(
               target_id=target.name,
               metrics=report
           )

Data Validation
---------------

OpenSTEF provides validation utilities to ensure data quality before training or prediction.

Required Columns
^^^^^^^^^^^^^^^^

Use ``validate_required_columns`` to check for expected columns:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   import pandas as pd
   
   df = pd.read_csv("input_data.csv", index_col="timestamp", parse_dates=True)
   
   # Validate required columns exist
   try:
       validate_required_columns(
           df,
           required_columns=["load", "temperature", "wind_speed"]
       )
   except MissingColumnsError as e:
       print(f"Missing columns: {e}")
       # Handle missing columns - fetch from alternative source, abort, etc.

Dataset Compatibility
^^^^^^^^^^^^^^^^^^^^^

When combining datasets, validate compatibility:

.. code-block:: python

   from openstef_core.datasets.validation import validate_horizons_present
   from openstef_core.datasets import ForecastInputDataset
   
   # Ensure prediction data covers required forecast horizons
   horizons = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 24.0, 47.0]
   
   try:
       validate_horizons_present(prediction_data, horizons)
   except TimeSeriesValidationError as e:
       print(f"Missing horizons: {e}")
       # Extend data range or adjust horizons

Handling Missing Data
---------------------

Missing data is common in production systems. OpenSTEF provides several strategies for handling gaps.

Automatic Handling During Training
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``StandardForecastingModel`` automatically drops rows with missing target values during training:

.. code-block:: python

   from openstef_core.model import StandardForecastingModel
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   model = StandardForecastingModel(target_column="load")
   
   try:
       model.fit(training_data)
   except InsufficientlyCompleteError:
       print("No valid training data after removing missing targets")
       # Handle insufficient data - extend time range, use fallback model, etc.

The model raises ``InsufficientlyCompleteError`` if no training data remains after dropping NaN targets.

Handling Missing Features
^^^^^^^^^^^^^^^^^^^^^^^^^^

For missing feature values, decide on a strategy based on your use case:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import ForecastInputDataset
   
   df = pd.read_csv("data.csv", index_col="timestamp", parse_dates=True)
   
   # Strategy 1: Forward fill (use last known value)
   df_filled = df.fillna(method='ffill', limit=4)  # Max 4 periods
   
   # Strategy 2: Interpolate
   df_filled = df.interpolate(method='linear', limit=4)
   
   # Strategy 3: Drop rows with any missing values
   df_complete = df.dropna()
   
   # Strategy 4: Fill with domain-specific defaults
   df_filled = df.copy()
   df_filled['wind_speed'] = df_filled['wind_speed'].fillna(0)
   df_filled['temperature'] = df_filled['temperature'].fillna(df['temperature'].mean())
   
   # Convert to OpenSTEF dataset
   input_data = ForecastInputDataset(
       data=df_filled,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

Detecting Data Quality Issues
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check data completeness before processing:

.. code-block:: python

   import pandas as pd
   
   def check_data_quality(df: pd.DataFrame, max_missing_pct: float = 0.1):
       """Check if data meets quality thresholds."""
       total_rows = len(df)
       
       for col in df.columns:
           missing = df[col].isna().sum()
           missing_pct = missing / total_rows
           
           if missing_pct > max_missing_pct:
               raise ValueError(
                   f"Column '{col}' has {missing_pct:.1%} missing values "
                   f"(threshold: {max_missing_pct:.1%})"
               )
       
       return True
   
   # Use before creating OpenSTEF datasets
   df = pd.read_csv("data.csv", index_col="timestamp", parse_dates=True)
   check_data_quality(df, max_missing_pct=0.05)
   
   input_data = ForecastInputDataset(data=df, ...)

Complete Pipeline Example
--------------------------

Here's a realistic end-to-end pipeline integrating data loading, validation, forecasting, and storage:

.. code-block:: python

   import pandas as pd
   import psycopg2
   from datetime import datetime, timedelta
   from openstef_core.datasets import ForecastInputDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.model import StandardForecastingModel
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   def run_forecast_pipeline(config: dict):
       """Complete forecasting pipeline with data integration."""
       
       # 1. Load data from PostgreSQL
       conn = psycopg2.connect(**config['database'])
       
       query = """
           SELECT timestamp, load, temperature, wind_speed, solar_radiation
           FROM measurements
           WHERE timestamp >= %s AND timestamp < %s
           ORDER BY timestamp
       """
       
       train_start = datetime.now() - timedelta(days=90)
       train_end = datetime.now()
       
       df = pd.read_sql_query(
           query,
           conn,
           params=(train_start, train_end),
           index_col="timestamp",
           parse_dates=["timestamp"]
       )
       
       # 2. Validate data
       required_cols = ["load", "temperature", "wind_speed", "solar_radiation"]
       validate_required_columns(df, required_cols)
       
       # 3. Handle missing data
       missing_pct = df.isna().sum() / len(df)
       if (missing_pct > 0.1).any():
           raise ValueError(f"Too many missing values: {missing_pct}")
       
       df_filled = df.fillna(method='ffill', limit=4)
       
       # 4. Create OpenSTEF dataset
       training_data = ForecastInputDataset(
           data=df_filled,
           sample_interval=timedelta(minutes=15),
           target_column="load"
       )
       
       # 5. Train model
       model = StandardForecastingModel(target_column="load")
       
       try:
           model.fit(training_data)
       except InsufficientlyCompleteError:
           print("Insufficient training data")
           conn.close()
           return None
       
       # 6. Load recent data for prediction
       predict_start = datetime.now() - timedelta(hours=48)
       predict_end = datetime.now()
       
       df_predict = pd.read_sql_query(
           query,
           conn,
           params=(predict_start, predict_end),
           index_col="timestamp",
           parse_dates=["timestamp"]
       )
       
       conn.close()
       
       df_predict_filled = df_predict.fillna(method='ffill', limit=4)
       
       prediction_data = ForecastInputDataset(
           data=df_predict_filled,
           sample_interval=timedelta(minutes=15),
           target_column="load"
       )
       
       # 7. Generate forecast
       forecast = model.predict(prediction_data)
       
       # 8. Write results back to database
       conn = psycopg2.connect(**config['database'])
       cursor = conn.cursor()
       
       forecast_df = forecast.data.reset_index()
       
       for _, row in forecast_df.iterrows():
           cursor.execute(
               """
               INSERT INTO forecasts (timestamp, horizon, forecast_value, created_at)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (timestamp, horizon) DO UPDATE
               SET forecast_value = EXCLUDED.forecast_value,
                   created_at = EXCLUDED.created_at
               """,
               (row['timestamp'], row['horizon'], row['load'], datetime.now())
           )
       
       conn.commit()
       conn.close()
       
       return forecast
   
   # Run pipeline
   config = {
       'database': {
           'host': 'db.example.com',
           'database': 'energy_data',
           'user': 'forecaster',
           'password': 'secret'
       }
   }
   
   forecast = run_forecast_pipeline(config)

See Also
--------

- :doc:`deployment` - Production deployment patterns and best practices
- :doc:`logging` - Configure logging for data pipeline monitoring
- :doc:`use_cases` - Common OpenSTEF use cases with practical examples