Data Integration
=================

OpenSTEF is designed to integrate with diverse data sources and storage systems. This page shows how to read data from common storage backends, write forecasts back to storage, handle missing data, and validate inputs. Whether you're loading historical data from a database, streaming from cloud storage, or implementing custom data connectors, OpenSTEF provides flexible patterns for data integration.

Reading Data from Storage
--------------------------

OpenSTEF uses the ``TimeSeriesDataset`` class as its core data structure. You can load data from various sources by first reading it with standard tools (pandas, database clients, cloud SDKs) and then wrapping it in a ``TimeSeriesDataset``.

Loading from Parquet Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Parquet is the recommended format for storing time series data due to its compression and performance characteristics:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load from local parquet file
   dataset = TimeSeriesDataset.read_parquet(
       path="data/historical_load.parquet",
       sample_interval=timedelta(minutes=15),
       timestamp_column="timestamp"
   )
   
   # For versioned datasets with available_at information
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   versioned_dataset = VersionedTimeSeriesDataset.read_parquet(
       path="data/versioned_forecasts.parquet",
       sample_interval=timedelta(hours=1),
       timestamp_column="timestamp",
       available_at_column="available_at",
       horizon_column="horizon"
   )

Loading from CSV Files
^^^^^^^^^^^^^^^^^^^^^^

For CSV data, use pandas to read the file and then create a ``TimeSeriesDataset``:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Read CSV with pandas
   df = pd.read_csv(
       "data/load_data.csv",
       parse_dates=["timestamp"],
       index_col="timestamp"
   )
   
   # Create dataset
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

Reading from Databases
^^^^^^^^^^^^^^^^^^^^^^

PostgreSQL Example
""""""""""""""""""

Use standard database connectors to query data and convert to ``TimeSeriesDataset``:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   import psycopg2
   from psycopg2.extras import RealDictCursor
   
   # Connect and query
   conn = psycopg2.connect(
       host="localhost",
       database="energy_data",
       user="forecast_user",
       password="secure_password"
   )
   
   query = """
       SELECT timestamp, load, temperature, radiation
       FROM load_measurements
       WHERE timestamp >= %s AND timestamp < %s
       ORDER BY timestamp
   """
   
   df = pd.read_sql_query(
       query,
       conn,
       params=("2024-01-01", "2024-12-31"),
       parse_dates=["timestamp"],
       index_col="timestamp"
   )
   conn.close()
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

InfluxDB Example
""""""""""""""""

For time series databases like InfluxDB:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Connect to InfluxDB
   client = InfluxDBClient(
       url="http://localhost:8086",
       token="my-token",
       org="my-org"
   )
   
   # Query data
   query = '''
       from(bucket: "energy_data")
           |> range(start: -30d)
           |> filter(fn: (r) => r["_measurement"] == "load")
           |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''
   
   query_api = client.query_api()
   result = query_api.query_data_frame(query)
   
   # Convert to TimeSeriesDataset
   df = result.set_index("_time")[["load", "temperature", "radiation"]]
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
   
   client.close()

Reading from Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Amazon S3
"""""""""

OpenSTEF includes S3 integration utilities. For direct data loading:

.. code-block:: python

   import boto3
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from io import BytesIO
   
   # Initialize S3 client
   s3_client = boto3.client(
       's3',
       aws_access_key_id='your-access-key',
       aws_secret_access_key='your-secret-key',
       region_name='eu-west-1'
   )
   
   # Read parquet from S3
   bucket = "energy-forecasts"
   key = "historical/load_2024.parquet"
   
   obj = s3_client.get_object(Bucket=bucket, Key=key)
   df = pd.read_parquet(BytesIO(obj['Body'].read()))
   
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

Databricks
""""""""""

When running in Databricks, use Spark DataFrames and convert to pandas:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Query data using Spark SQL
   spark_df = spark.sql("""
       SELECT timestamp, load, temperature, radiation
       FROM energy_data.load_measurements
       WHERE timestamp >= '2024-01-01'
       ORDER BY timestamp
   """)
   
   # Convert to pandas and create dataset
   df = spark_df.toPandas().set_index("timestamp")
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Writing Forecasts to Storage
-----------------------------

After generating forecasts, you typically need to write them back to storage for consumption by other systems.

Writing to Parquet
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # After generating forecasts
   forecasts = workflow.predict(dataset)
   
   # Write to local parquet file
   forecasts.to_parquet("output/forecasts_2024.parquet")
   
   # For versioned datasets
   versioned_forecasts.to_parquet("output/versioned_forecasts.parquet")

Writing to Databases
^^^^^^^^^^^^^^^^^^^^

PostgreSQL Example
""""""""""""""""""

.. code-block:: python

   import psycopg2
   from psycopg2.extras import execute_values
   
   # Generate forecasts
   forecasts = workflow.predict(dataset)
   df = forecasts.to_pandas()
   
   # Prepare data for insertion
   records = [
       (row.Index, row.forecast, row.forecast_q10, row.forecast_q90)
       for row in df.itertuples()
   ]
   
   # Insert into database
   conn = psycopg2.connect(
       host="localhost",
       database="energy_data",
       user="forecast_user",
       password="secure_password"
   )
   
   cursor = conn.cursor()
   
   insert_query = """
       INSERT INTO forecasts (timestamp, forecast, q10, q90)
       VALUES %s
       ON CONFLICT (timestamp) DO UPDATE SET
           forecast = EXCLUDED.forecast,
           q10 = EXCLUDED.q10,
           q90 = EXCLUDED.q90
   """
   
   execute_values(cursor, insert_query, records)
   conn.commit()
   cursor.close()
   conn.close()

Writing to InfluxDB
"""""""""""""""""""

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   
   # Generate forecasts
   forecasts = workflow.predict(dataset)
   df = forecasts.to_pandas()
   
   # Connect to InfluxDB
   client = InfluxDBClient(
       url="http://localhost:8086",
       token="my-token",
       org="my-org"
   )
   
   write_api = client.write_api(write_options=SYNCHRONOUS)
   
   # Write forecast points
   points = []
   for timestamp, row in df.iterrows():
       point = Point("forecast") \
           .tag("model_id", "production_model_v1") \
           .field("value", float(row["forecast"])) \
           .field("q10", float(row["forecast_q10"])) \
           .field("q90", float(row["forecast_q90"])) \
           .time(timestamp)
       points.append(point)
   
   write_api.write(bucket="forecasts", record=points)
   client.close()

Writing to S3
^^^^^^^^^^^^^

.. code-block:: python

   import boto3
   from io import BytesIO
   
   # Generate forecasts
   forecasts = workflow.predict(dataset)
   
   # Convert to parquet in memory
   buffer = BytesIO()
   forecasts.to_pandas().to_parquet(buffer)
   buffer.seek(0)
   
   # Upload to S3
   s3_client = boto3.client('s3')
   s3_client.put_object(
       Bucket='energy-forecasts',
       Key='forecasts/2024/forecast_latest.parquet',
       Body=buffer.getvalue()
   )

Handling Missing Data
---------------------

Real-world data often contains gaps and missing values. OpenSTEF provides several strategies for handling incomplete data.

Detecting Missing Data
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import numpy as np
   import pandas as pd
   
   # Check for missing values
   missing_summary = dataset.data.isna().sum()
   print(f"Missing values per column:\n{missing_summary}")
   
   # Check completeness percentage
   completeness = (1 - dataset.data.isna().sum() / len(dataset.data)) * 100
   print(f"Data completeness:\n{completeness}")

Removing Empty Features
^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes transforms to automatically remove features with insufficient data:

.. code-block:: python

   from openstef_models.transforms.general import EmptyFeatureRemover
   from openstef_models.preprocessing import FeaturePipeline
   
   # Configure preprocessing to remove empty columns
   preprocessing = FeaturePipeline(
       transforms=[
           EmptyFeatureRemover(),  # Removes columns with all NaN values
           # ... other transforms
       ]
   )
   
   # Apply to dataset
   preprocessing.fit(dataset)
   cleaned_dataset = preprocessing.transform(dataset)

Handling Missing Targets
^^^^^^^^^^^^^^^^^^^^^^^^^

During training, OpenSTEF automatically drops rows where the target variable is NaN. If all targets are missing, it raises an ``InsufficientlyCompleteError``:

.. code-block:: python

   from openstef_core.exceptions import InsufficientlyCompleteError
   
   try:
       model.fit(dataset)
   except InsufficientlyCompleteError as e:
       print(f"Cannot train model: {e}")
       # Handle the error - perhaps load more data or adjust time range

Data Validation
---------------

Validating data before training or prediction helps catch issues early and ensures model reliability.

Frequency Validation
^^^^^^^^^^^^^^^^^^^^

OpenSTEF validates that input data matches the expected frequency:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create dataset with explicit frequency
   df = pd.DataFrame(
       {"load": [100, 110, 120]},
       index=pd.date_range("2024-01-01", periods=3, freq="15min")
   )
   
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
   
   # OpenSTEF will validate frequency during prediction
   # If data has gaps or wrong frequency, it will raise ValueError

Feature Validation
^^^^^^^^^^^^^^^^^^

Ensure required features are present:

.. code-block:: python

   # Check for required features
   required_features = ["temperature", "radiation", "windspeed"]
   missing_features = set(required_features) - set(dataset.feature_names)
   
   if missing_features:
       raise ValueError(f"Missing required features: {missing_features}")

Horizon Validation
^^^^^^^^^^^^^^^^^^

OpenSTEF validates that training data includes the required forecast horizons:

.. code-block:: python

   from openstef_models.validation import validate_horizons_present
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   try:
       validate_horizons_present(dataset, model.forecaster.horizons)
   except InsufficientlyCompleteError as e:
       print(f"Data validation failed: {e}")

Complete Data Pipeline Example
-------------------------------

Here's a realistic end-to-end data pipeline that combines loading, validation, forecasting, and storage:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from pathlib import Path
   import psycopg2
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.forecasting import ForecastingModel
   from openstef_models.forecasters import ConstantMedianForecaster
   from openstef_models.preprocessing import FeaturePipeline
   from openstef_models.transforms.general import EmptyFeatureRemover
   from openstef_models.transforms.lag import LagTransform
   from openstef_beam.workflows import CustomForecastingWorkflow
   from openstef_beam.storage import LocalModelStorage
   from openstef_core.types import LeadTime, Q
   
   def load_training_data(start_date: str, end_date: str) -> TimeSeriesDataset:
       """Load historical data from PostgreSQL."""
       conn = psycopg2.connect(
           host="db.example.com",
           database="energy_data",
           user="forecast_user",
           password="secure_password"
       )
       
       query = """
           SELECT timestamp, load, temperature, radiation, windspeed
           FROM load_measurements
           WHERE timestamp >= %s AND timestamp < %s
           ORDER BY timestamp
       """
       
       df = pd.read_sql_query(
           query,
           conn,
           params=(start_date, end_date),
           parse_dates=["timestamp"],
           index_col="timestamp"
       )
       conn.close()
       
       # Validate data completeness
       completeness = (1 - df.isna().sum() / len(df)) * 100
       if (completeness < 80).any():
           print(f"Warning: Low data completeness:\n{completeness}")
       
       return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
   
   def save_forecasts_to_db(forecasts: TimeSeriesDataset, model_id: str):
       """Write forecasts to PostgreSQL."""
       from psycopg2.extras import execute_values
       
       df = forecasts.to_pandas()
       records = [
           (model_id, row.Index, row.forecast)
           for row in df.itertuples()
       ]
       
       conn = psycopg2.connect(
           host="db.example.com",
           database="energy_data",
           user="forecast_user",
           password="secure_password"
       )
       
       cursor = conn.cursor()
       insert_query = """
           INSERT INTO forecasts (model_id, timestamp, forecast)
           VALUES %s
           ON CONFLICT (model_id, timestamp) DO UPDATE SET
               forecast = EXCLUDED.forecast,
               updated_at = NOW()
       """
       
       execute_values(cursor, insert_query, records)
       conn.commit()
       cursor.close()
       conn.close()
   
   # Main pipeline
   def run_forecast_pipeline():
       # Load training data
       print("Loading training data...")
       train_data = load_training_data("2024-01-01", "2024-11-01")
       
       # Configure model
       horizons = [LeadTime.from_string("PT24H")]
       preprocessing = FeaturePipeline(
           transforms=[
               EmptyFeatureRemover(),
               LagTransform(horizons=horizons, target_column="load"),
           ]
       )
       
       model = ForecastingModel(
           forecaster=ConstantMedianForecaster(
               horizons=horizons,
               quantiles=[Q(0.5)]
           ),
           preprocessing=preprocessing,
           target_column="load"
       )
       
       # Set up storage and workflow
       storage = LocalModelStorage(base_path=Path("models"))
       workflow = CustomForecastingWorkflow(
           model=model,
           model_id="production_load_forecast",
           storage=storage
       )
       
       # Train model
       print("Training model...")
       workflow.fit(train_data)
       
       # Load recent data for prediction
       print("Loading recent data for prediction...")
       recent_data = load_training_data("2024-11-01", "2024-12-01")
       
       # Generate forecasts
       print("Generating forecasts...")
       forecasts = workflow.predict(recent_data)
       
       # Save to database
       print("Saving forecasts to database...")
       save_forecasts_to_db(forecasts, "production_load_forecast")
       
       print("Pipeline complete!")
   
   if __name__ == "__main__":
       run_forecast_pipeline()

Custom Data Sources
-------------------

For specialized data sources, implement a custom loader function that returns a ``TimeSeriesDataset``:

.. code-block:: python

   from typing import Any
   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_custom_api(
       api_endpoint: str,
       api_key: str,
       start_date: str,
       end_date: str
   ) -> TimeSeriesDataset:
       """Load data from a custom REST API."""
       import requests
       
       response = requests.get(
           api_endpoint,
           headers={"Authorization": f"Bearer {api_key}"},
           params={"start": start_date, "end": end_date}
       )
       response.raise_for_status()
       
       # Parse JSON response
       data = response.json()
       df = pd.DataFrame(data["measurements"])
       df["timestamp"] = pd.to_datetime(df["timestamp"])
       df = df.set_index("timestamp")
       
       return TimeSeriesDataset(
           data=df,
           sample_interval=timedelta(minutes=15)
       )

See Also
--------

- :doc:`use_cases` - Common OpenSTEF use cases with practical examples
- :doc:`deployment` - Production deployment patterns
- :doc:`logging` - Logging configuration for monitoring data pipelines