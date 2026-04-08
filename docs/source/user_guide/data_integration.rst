Data Integration
=================

OpenSTEF is designed to integrate with diverse data sources and storage systems. This page demonstrates how to read input data from various backends, write forecasts to storage, validate data quality, and handle missing values in production pipelines.

As a library, OpenSTEF provides flexible integration patterns rather than prescriptive data connectors. You implement data loading and persistence logic that fits your infrastructure, then pass datasets to OpenSTEF's forecasting components.

Reading Data from Storage Systems
----------------------------------

OpenSTEF works with pandas DataFrames wrapped in ``TimeSeriesDataset`` objects. The general pattern is: load data from your storage system, validate it, convert to a dataset, and pass it to forecasting workflows.

Basic Data Loading Pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a robust data loading function with error handling:

.. code-block:: python

   from pathlib import Path
   import pandas as pd
   import logging
   from openstef_core.datasets import TimeSeriesDataset
   
   logger = logging.getLogger(__name__)
   
   def load_data_from_csv(file_path: Path) -> TimeSeriesDataset:
       """Load time series data with validation and error handling."""
       logger.info(f"Loading data from {file_path}")
       
       try:
           if not file_path.exists():
               raise FileNotFoundError(f"Data file not found: {file_path}")
           
           # Load raw data
           df = pd.read_csv(file_path, index_col=0, parse_dates=True)
           logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
           
           # Validate structure
           required_columns = ["load"]
           missing = set(required_columns) - set(df.columns)
           if missing:
               raise ValueError(f"Missing required columns: {missing}")
           
           return TimeSeriesDataset(df)
           
       except pd.errors.EmptyDataError:
           logger.error(f"File is empty: {file_path}")
           raise
       except pd.errors.ParserError as e:
           logger.error(f"Failed to parse CSV: {e}")
           raise

Loading from PostgreSQL
^^^^^^^^^^^^^^^^^^^^^^^^

Connect to PostgreSQL using SQLAlchemy and load time series data:

.. code-block:: python

   from sqlalchemy import create_engine
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import datetime
   
   def load_from_postgres(
       connection_string: str,
       table_name: str,
       start_time: datetime,
       end_time: datetime
   ) -> TimeSeriesDataset:
       """Load time series data from PostgreSQL."""
       engine = create_engine(connection_string)
       
       query = f"""
           SELECT timestamp, load, temperature, wind_speed
           FROM {table_name}
           WHERE timestamp >= %s AND timestamp < %s
           ORDER BY timestamp
       """
       
       df = pd.read_sql(
           query,
           engine,
           params=(start_time, end_time),
           index_col="timestamp",
           parse_dates=["timestamp"]
       )
       
       return TimeSeriesDataset(df)

Loading from InfluxDB
^^^^^^^^^^^^^^^^^^^^^

Query time series data from InfluxDB:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import datetime
   
   def load_from_influxdb(
       url: str,
       token: str,
       org: str,
       bucket: str,
       measurement: str,
       start_time: datetime,
       end_time: datetime
   ) -> TimeSeriesDataset:
       """Load time series data from InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       query_api = client.query_api()
       
       query = f'''
           from(bucket: "{bucket}")
               |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
               |> filter(fn: (r) => r["_measurement"] == "{measurement}")
               |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
       '''
       
       tables = query_api.query(query)
       
       # Convert to DataFrame
       records = []
       for table in tables:
           for record in table.records:
               records.append(record.values)
       
       df = pd.DataFrame(records)
       df = df.set_index("_time")
       df.index.name = "timestamp"
       
       return TimeSeriesDataset(df)

Loading from S3
^^^^^^^^^^^^^^^

OpenSTEF includes S3 integration patterns in its benchmarking storage. For loading input data from S3:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   def load_from_s3(bucket: str, key: str, s3_kwargs: dict = None) -> TimeSeriesDataset:
       """Load time series data from S3 using pandas."""
       s3_kwargs = s3_kwargs or {}
       
       # Pandas can read directly from S3 paths
       s3_path = f"s3://{bucket}/{key}"
       df = pd.read_parquet(s3_path, storage_options=s3_kwargs)
       
       return TimeSeriesDataset(df)
   
   # Example usage
   data = load_from_s3(
       bucket="energy-forecasts",
       key="measurements/substation_001.parquet",
       s3_kwargs={"key": "...", "secret": "..."}
   )

Loading from Databricks
^^^^^^^^^^^^^^^^^^^^^^^

Access Databricks tables using the Databricks SQL connector:

.. code-block:: python

   from databricks import sql
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import datetime
   
   def load_from_databricks(
       server_hostname: str,
       http_path: str,
       access_token: str,
       catalog: str,
       schema: str,
       table: str,
       start_time: datetime,
       end_time: datetime
   ) -> TimeSeriesDataset:
       """Load time series data from Databricks."""
       with sql.connect(
           server_hostname=server_hostname,
           http_path=http_path,
           access_token=access_token
       ) as connection:
           with connection.cursor() as cursor:
               query = f"""
                   SELECT timestamp, load, temperature, wind_speed
                   FROM {catalog}.{schema}.{table}
                   WHERE timestamp >= '{start_time.isoformat()}'
                     AND timestamp < '{end_time.isoformat()}'
                   ORDER BY timestamp
               """
               cursor.execute(query)
               
               # Fetch results and convert to DataFrame
               columns = [desc[0] for desc in cursor.description]
               rows = cursor.fetchall()
               df = pd.DataFrame(rows, columns=columns)
               df = df.set_index("timestamp")
               
       return TimeSeriesDataset(df)

Custom Data Providers
^^^^^^^^^^^^^^^^^^^^^

For benchmarking workflows, implement custom data providers by subclassing ``TargetProvider``:

.. code-block:: python

   from pathlib import Path
   from datetime import datetime
   from openstef_beam.benchmarking.target_providers import TargetProvider
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   class CustomDatabaseProvider(TargetProvider):
       """Load benchmark targets and data from a custom database."""
       
       def __init__(self, db_connection_string: str, region: str):
           super().__init__()
           self.db_connection = db_connection_string
           self.region = region
       
       def get_targets(self, filter_args=None):
           """Retrieve list of forecast targets from database."""
           # Query database for target configurations
           targets = []
           # ... database query logic ...
           
           return [
               BenchmarkTarget(
                   name=f"substation_{i:03d}",
                   description=f"Load for substation {i}",
                   group_name=self.region,
                   latitude=52.0 + i * 0.001,
                   longitude=4.0 + i * 0.001,
                   benchmark_start=datetime(2024, 1, 1),
                   benchmark_end=datetime(2024, 3, 1),
                   train_start=datetime(2022, 1, 1)
               ) for i in range(1, 11)
           ]
       
       def get_measurements_for_target(self, target):
           """Load measurement data for a specific target."""
           # Query time series data from database
           query = f"SELECT * FROM measurements WHERE target_id = '{target.name}'"
           df = pd.read_sql(query, self.db_connection, parse_dates=["timestamp"])
           return TimeSeriesDataset(df.set_index("timestamp"))

Writing Forecasts to Storage
-----------------------------

After generating forecasts, write them back to your storage system for downstream consumption.

Saving Forecasts to Files
^^^^^^^^^^^^^^^^^^^^^^^^^^

Use OpenSTEF's built-in parquet export:

.. code-block:: python

   from pathlib import Path
   from openstef_core.datasets import ForecastDataset
   
   def save_forecast_to_file(forecast: ForecastDataset, output_path: Path) -> None:
       """Save forecast to parquet file."""
       forecast.to_parquet(output_path)
   
   # Example usage in a workflow
   from openstef_workflows import CustomForecastingWorkflow
   
   workflow = CustomForecastingWorkflow(...)
   result = workflow.predict(data=input_data)
   
   save_forecast_to_file(
       result,
       Path("forecasts") / f"forecast_{workflow.run_name}.parquet"
   )

Saving to PostgreSQL
^^^^^^^^^^^^^^^^^^^^

Write forecast results to a PostgreSQL table:

.. code-block:: python

   from sqlalchemy import create_engine
   from openstef_core.datasets import ForecastDataset
   
   def save_forecast_to_postgres(
       forecast: ForecastDataset,
       connection_string: str,
       table_name: str,
       target_id: str
   ) -> None:
       """Write forecast to PostgreSQL."""
       engine = create_engine(connection_string)
       
       # Add metadata columns
       df = forecast.data.copy()
       df["target_id"] = target_id
       df["forecast_created_at"] = forecast.forecast_start
       
       # Write to database (append mode)
       df.to_sql(
           table_name,
           engine,
           if_exists="append",
           index=True,
           index_label="forecast_time"
       )

Saving to InfluxDB
^^^^^^^^^^^^^^^^^^

Write forecasts to InfluxDB for time series storage:

.. code-block:: python

   from influxdb_client import InfluxDBClient, Point
   from influxdb_client.client.write_api import SYNCHRONOUS
   from openstef_core.datasets import ForecastDataset
   
   def save_forecast_to_influxdb(
       forecast: ForecastDataset,
       url: str,
       token: str,
       org: str,
       bucket: str,
       measurement: str,
       target_id: str
   ) -> None:
       """Write forecast to InfluxDB."""
       client = InfluxDBClient(url=url, token=token, org=org)
       write_api = client.write_api(write_options=SYNCHRONOUS)
       
       points = []
       for timestamp, row in forecast.data.iterrows():
           point = (
               Point(measurement)
               .tag("target_id", target_id)
               .tag("forecast_created_at", forecast.forecast_start.isoformat())
               .time(timestamp)
           )
           
           # Add all forecast columns as fields
           for column, value in row.items():
               if pd.notna(value):
                   point = point.field(column, float(value))
           
           points.append(point)
       
       write_api.write(bucket=bucket, org=org, record=points)
       client.close()

Using Workflow Callbacks for Persistence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF workflows support callbacks that automatically save data at different pipeline stages:

.. code-block:: python

   from pathlib import Path
   from openstef_workflows.callbacks import DataSaveCallback
   from openstef_workflows import CustomForecastingWorkflow
   
   # Configure callback to save forecasts automatically
   callback = DataSaveCallback(
       cache_dir=Path("output"),
       save_training_data=True,
       save_forecast=True,
       save_predict_data=True
   )
   
   workflow = CustomForecastingWorkflow(
       model=my_model,
       callbacks=[callback],
       run_name="substation_001"
   )
   
   # Forecasts automatically saved to:
   # output/debug_substation_001_forecast.parquet
   result = workflow.predict(data=input_data)

For custom persistence logic, implement your own callback:

.. code-block:: python

   from openstef_workflows.callbacks import WorkflowCallback
   from openstef_workflows.context import WorkflowContext
   from openstef_core.datasets import ForecastDataset
   
   class DatabasePersistenceCallback(WorkflowCallback):
       """Save forecasts to database after prediction."""
       
       def __init__(self, db_connection_string: str):
           self.db_connection = db_connection_string
       
       def on_predict_end(
           self,
           context: WorkflowContext,
           data,
           result: ForecastDataset
       ) -> None:
           """Called after prediction completes."""
           target_id = context.workflow.run_name
           save_forecast_to_postgres(
               result,
               self.db_connection,
               table_name="forecasts",
               target_id=target_id
           )

Data Validation
---------------

Validate data quality before passing to forecasting models using OpenSTEF's validation utilities.

Validating Required Columns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Check that datasets contain required columns:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   import pandas as pd
   
   df = pd.DataFrame({
       "timestamp": pd.date_range("2024-01-01", periods=100, freq="15min"),
       "load": range(100),
       "temperature": range(100)
   })
   
   # Raises MissingColumnsError if columns are missing
   validate_required_columns(df, required_columns=["load", "temperature"])

Validating Temporal Alignment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensure datasets have consistent temporal resolution:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   def validate_temporal_resolution(
       dataset: TimeSeriesDataset,
       expected_interval: timedelta
   ) -> bool:
       """Check if dataset has consistent time intervals."""
       df = dataset.data
       
       if len(df) < 2:
           return True
       
       # Calculate intervals between consecutive timestamps
       intervals = df.index.to_series().diff()
       
       # Check if all intervals match expected (allowing small tolerance)
       tolerance = timedelta(seconds=1)
       is_consistent = (
           (intervals[1:] >= expected_interval - tolerance) &
           (intervals[1:] <= expected_interval + tolerance)
       ).all()
       
       return is_consistent

Custom Validation Functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement domain-specific validation:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.exceptions import TimeSeriesValidationError
   
   def validate_energy_data(dataset: TimeSeriesDataset) -> None:
       """Validate energy-specific data constraints."""
       df = dataset.data
       
       # Check for negative load values
       if "load" in df.columns and (df["load"] < 0).any():
           raise TimeSeriesValidationError("Load values cannot be negative")
       
       # Check for unrealistic temperature values
       if "temperature" in df.columns:
           temp = df["temperature"]
           if (temp < -50).any() or (temp > 60).any():
               raise TimeSeriesValidationError(
                   "Temperature values outside realistic range (-50 to 60°C)"
               )
       
       # Check for sufficient data completeness
       completeness = df.notna().mean()
       if (completeness < 0.8).any():
           raise TimeSeriesValidationError(
               f"Insufficient data completeness: {completeness.min():.1%}"
           )

Handling Missing Data
---------------------

OpenSTEF provides strategies for handling missing values in time series data.

Automatic Handling During Training
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Models automatically drop rows with missing target values during training:

.. code-block:: python

   from openstef_workflows import CustomForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   # Data with some missing target values
   df = pd.DataFrame({
       "timestamp": pd.date_range("2024-01-01", periods=100, freq="15min"),
       "load": [None if i % 10 == 0 else i for i in range(100)],
       "temperature": range(100)
   })
   data = TimeSeriesDataset(df.set_index("timestamp"))
   
   workflow = CustomForecastingWorkflow(model=my_model)
   
   # Rows with NaN in 'load' column are automatically dropped during fit
   workflow.fit(data=data)

The workflow raises ``InsufficientlyCompleteError`` if no valid training data remains after dropping NaN targets.

Handling Missing Predictors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For missing predictor values, implement preprocessing strategies:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd
   
   def handle_missing_predictors(dataset: TimeSeriesDataset) -> TimeSeriesDataset:
       """Fill missing predictor values using forward fill."""
       df = dataset.data.copy()
       
       # Forward fill for short gaps (up to 4 hours)
       predictor_columns = [col for col in df.columns if col != "load"]
       df[predictor_columns] = df[predictor_columns].fillna(method="ffill", limit=16)
       
       # Backward fill for remaining gaps at start
       df[predictor_columns] = df[predictor_columns].fillna(method="bfill")
       
       return TimeSeriesDataset(df)

Cutoff History for Incomplete Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Lag-based features create NaN values at the start of datasets. Use ``cutoff_history`` to exclude incomplete rows:

.. code-block:: python

   from datetime import timedelta
   from openstef_workflows import CustomForecastingWorkflow
   from openstef_models import XGBForecastingModel
   
   model = XGBForecastingModel(
       # Exclude first 14 days due to lag-14 features
       cutoff_history=timedelta(days=14)
   )
   
   workflow = CustomForecastingWorkflow(model=model)
   workflow.fit(data=training_data)

Complete Data Pipeline Example
-------------------------------

Here's a complete example integrating data loading, validation, forecasting, and persistence:

.. code-block:: python

   from pathlib import Path
   from datetime import datetime, timedelta
   import pandas as pd
   from sqlalchemy import create_engine
   
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_workflows import CustomForecastingWorkflow
   from openstef_models import XGBForecastingModel
   
   def run_forecast_pipeline(
       target_id: str,
       db_connection: str,
       forecast_start: datetime
   ) -> None:
       """Complete pipeline: load, validate, forecast, save."""
       
       # 1. Load training data from PostgreSQL
       engine = create_engine(db_connection)
       train_end = forecast_start
       train_start = train_end - timedelta(days=365)
       
       query = """
           SELECT timestamp, load, temperature, wind_speed, solar_radiation
           FROM measurements
           WHERE target_id = %s
             AND timestamp >= %s
             AND timestamp < %s
           ORDER BY timestamp
       """
       df = pd.read_sql(
           query,
           engine,
           params=(target_id, train_start, train_end),
           index_col="timestamp",
           parse_dates=["timestamp"]
       )
       
       # 2. Validate data
       validate_required_columns(df, ["load", "temperature"])
       training_data = TimeSeriesDataset(df)
       
       # 3. Train model
       model = XGBForecastingModel(
           horizons=[0.25, 24.0, 47.0],
           cutoff_history=timedelta(days=14)
       )
       workflow = CustomForecastingWorkflow(
           model=model,
           run_name=target_id
       )
       workflow.fit(data=training_data)
       
       # 4. Load prediction data
       predict_end = forecast_start + timedelta(hours=48)
       query = """
           SELECT timestamp, temperature, wind_speed, solar_radiation
           FROM measurements
           WHERE target_id = %s
             AND timestamp >= %s
             AND timestamp < %s
           ORDER BY timestamp
       """
       df_predict = pd.read_sql(
           query,
           engine,
           params=(target_id, forecast_start, predict_end),
           index_col="timestamp",
           parse_dates=["timestamp"]
       )
       predict_data = TimeSeriesDataset(df_predict)
       
       # 5. Generate forecast
       forecast = workflow.predict(data=predict_data)
       
       # 6. Save to database
       df_output = forecast.data.copy()
       df_output["target_id"] = target_id
       df_output["forecast_created_at"] = forecast_start
       df_output.to_sql(
           "forecasts",
           engine,
           if_exists="append",
           index=True,
           index_label="forecast_time"
       )
       
       print(f"Forecast saved for {target_id}: {len(forecast.data)} timesteps")

See Also
--------

- :doc:`use_cases` - Common forecasting scenarios and patterns
- :doc:`deployment` - Production deployment strategies
- :doc:`logging` - Logging configuration for data pipelines