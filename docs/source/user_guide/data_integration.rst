Data Integration Patterns
=========================

This page covers how to integrate OpenSTEF with your existing data infrastructure. As a library, OpenSTEF does not impose a specific database or storage system. Instead, it provides clean interfaces—primarily built around pandas DataFrames and the ``TimeSeriesDataset`` class—that you can connect to any data source. This page walks through reading data from common sources, writing forecasts back to storage, handling missing data, and implementing custom storage backends.

.. note::

   For deployment architecture decisions, see :doc:`deployment`. For logging
   configuration during data pipeline operations, see :doc:`logging`.


The Core Data Contract
----------------------

All data flows through OpenSTEF via ``TimeSeriesDataset``, which wraps a pandas DataFrame with metadata about time series structure. Understanding this contract is the key to integrating any data source:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # The fundamental contract: a DataFrame with a datetime index
   # and at least a 'load' column (your target variable)
   df = pd.DataFrame({
       "load": [100.0, 120.5, 115.3, 130.0],
       "temperature": [15.2, 16.1, 15.8, 17.0],
   }, index=pd.date_range("2025-01-01", periods=4, freq="15min"))
   df.index.name = "timestamp"

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

The ``TimeSeriesDataset`` also supports versioned forecasts with ``horizon`` and ``available_at`` columns for temporal versioning—tracking when each forecast was made and for which future time step:

.. code-block:: python

   df_versioned = pd.DataFrame({
       "load": [100, 120],
       "horizon": pd.to_timedelta(["1h", "2h"]),
   }, index=pd.date_range("2025-01-01", periods=2, freq="1h"))
   df_versioned.index.name = "timestamp"

   dataset = TimeSeriesDataset(
       df_versioned,
       sample_interval=timedelta(hours=1),
   )
   assert dataset.is_versioned is True


Reading Data from External Sources
-----------------------------------

Since OpenSTEF operates on pandas DataFrames, integrating with any data source is a matter of loading data into a DataFrame and wrapping it in a ``TimeSeriesDataset``. Below are patterns for common sources.

From CSV or Parquet files
^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest integration pattern. Use ``TimeSeriesDataset.from_csv`` for direct loading:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   # From CSV with a timestamp column
   dataset = TimeSeriesDataset.from_csv(
       "measurements.csv",
       timestamp_column="timestamp",
       sample_interval=timedelta(minutes=15),
   )

   # Or load via pandas first for more control
   df = pd.read_parquet("measurements.parquet")
   df = df.set_index("timestamp").sort_index()
   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

From PostgreSQL
^^^^^^^^^^^^^^^

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   engine = create_engine("postgresql://user:pass@host:5432/energy_db")

   query = """
       SELECT timestamp, load_mw AS load, temperature, wind_speed
       FROM measurements
       WHERE timestamp >= '2024-01-01'
       ORDER BY timestamp
   """
   df = pd.read_sql(query, engine, index_col="timestamp", parse_dates=["timestamp"])

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

From InfluxDB
^^^^^^^^^^^^^

.. code-block:: python

   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org")
   query_api = client.query_api()

   query = '''
       from(bucket: "energy")
       |> range(start: -30d)
       |> filter(fn: (r) => r._measurement == "grid_load")
       |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   '''
   df = query_api.query_data_frame(query)
   df = df.set_index("_time").rename(columns={"_value": "load"})
   df.index.name = "timestamp"

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

From S3 / Cloud Storage
^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes S3 integration in the ``openstef_beam`` package for benchmark storage, but you can also load raw data from S3 using standard tools:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # Using pandas with s3fs (pip install s3fs)
   df = pd.read_parquet("s3://my-bucket/energy-data/measurements.parquet")
   df = df.set_index("timestamp")

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

From Databricks
^^^^^^^^^^^^^^^

.. code-block:: python

   from databricks import sql
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   connection = sql.connect(
       server_hostname="my-workspace.cloud.databricks.com",
       http_path="/sql/1.0/warehouses/abc123",
       access_token="dapi_token",
   )

   df = pd.read_sql(
       "SELECT timestamp, load, temperature FROM energy.measurements",
       connection,
       parse_dates=["timestamp"],
   )
   df = df.set_index("timestamp").sort_index()

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))


Building a Reusable Data Provider
---------------------------------

For production use, encapsulate your data loading logic in a provider class. This keeps your forecasting pipeline decoupled from your storage infrastructure:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset

   class EnergyDataProvider:
       """Loads measurement data from your infrastructure."""

       def __init__(self, db_engine):
           self.engine = db_engine

       def get_measurements(
           self,
           location_id: str,
           start: datetime,
           end: datetime,
       ) -> TimeSeriesDataset:
           query = """
               SELECT timestamp, load_mw AS load, temperature, wind_speed
               FROM measurements
               WHERE location_id = %(loc)s
                 AND timestamp BETWEEN %(start)s AND %(end)s
               ORDER BY timestamp
           """
           df = pd.read_sql(
               query, self.engine,
               params={"loc": location_id, "start": start, "end": end},
               index_col="timestamp",
               parse_dates=["timestamp"],
           )
           return TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   # Usage in your pipeline
   provider = EnergyDataProvider(engine)
   dataset = provider.get_measurements("substation_42", start, end)


Writing Forecasts Back to Storage
---------------------------------

After generating forecasts, you typically need to persist results. OpenSTEF's ``BenchmarkStorage`` interface provides a pattern you can follow for any storage backend. The key insight is that forecasts carry temporal versioning—each forecast records *when* it was made (``available_at``) and *what horizon* it covers.

Using built-in storage backends
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides ``LocalBenchmarkStorage`` and ``S3BenchmarkStorage`` out of the box:

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage

   # Local file-based storage
   storage = LocalBenchmarkStorage(base_path=Path("./forecast_results"))

   # S3-backed storage (syncs local files to S3)
   from openstef_beam.benchmarking.storage.s3_storage import S3BenchmarkStorage

   s3_storage = S3BenchmarkStorage(
       base_path=Path("./local_cache"),
       bucket="my-forecast-bucket",
       prefix="forecasts/",
   )

Custom storage implementation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement the ``BenchmarkStorage`` abstract base class to write forecasts to any backend:

.. code-block:: python

   from openstef_beam.benchmarking.storage.base import BenchmarkStorage
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from openstef_beam.evaluation import EvaluationReport
   from openstef_core.datasets import TimeSeriesDataset

   class PostgresForecastStorage(BenchmarkStorage):
       """Store forecast results in PostgreSQL."""

       def __init__(self, engine):
           self.engine = engine

       def save_backtest_output(
           self, target: BenchmarkTarget, output: TimeSeriesDataset
       ) -> None:
           df = output.data.copy()
           df["target_name"] = target.name
           df.to_sql("forecast_results", self.engine, if_exists="append")

       def load_backtest_output(
           self, target: BenchmarkTarget
       ) -> TimeSeriesDataset:
           df = pd.read_sql(
               f"SELECT * FROM forecast_results WHERE target_name = '{target.name}'",
               self.engine,
               index_col="timestamp",
               parse_dates=["timestamp"],
           )
           df = df.drop(columns=["target_name"])
           return TimeSeriesDataset(df)

       def has_backtest_output(self, target: BenchmarkTarget) -> bool:
           result = pd.read_sql(
               f"SELECT 1 FROM forecast_results WHERE target_name = '{target.name}' LIMIT 1",
               self.engine,
           )
           return len(result) > 0

       # ... implement remaining abstract methods similarly


Handling Missing Data
---------------------

Real-world energy data invariably has gaps. OpenSTEF expects regular time series, so you need to handle missing data before creating a ``TimeSeriesDataset``.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Load raw data (may have gaps)
   df = pd.read_sql("SELECT timestamp, load FROM measurements", engine,
                     index_col="timestamp", parse_dates=["timestamp"])

   # 1. Reindex to ensure regular intervals
   full_index = pd.date_range(
       start=df.index.min(),
       end=df.index.max(),
       freq="15min",
       name="timestamp",
   )
   df = df.reindex(full_index)

   # 2. Handle small gaps with interpolation
   df["load"] = df["load"].interpolate(method="time", limit=4)  # up to 1 hour

   # 3. Flag remaining gaps (don't silently fill large gaps)
   missing_mask = df["load"].isna()
   if missing_mask.sum() > 0:
       print(f"Warning: {missing_mask.sum()} intervals still missing after interpolation")

   # 4. Drop or fill remaining NaNs based on your policy
   df = df.dropna(subset=["load"])

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

.. warning::

   Avoid filling large data gaps with interpolation or constant values. This can
   silently degrade model quality. It is better to split your data into
   contiguous segments or explicitly mark low-confidence periods.


Data Validation
---------------

Validate your data before feeding it into OpenSTEF pipelines. Catching issues early saves debugging time later.

.. code-block:: python

   def validate_energy_data(df: pd.DataFrame) -> list[str]:
       """Check common data quality issues before creating a TimeSeriesDataset."""
       issues = []

       # Check index
       if not isinstance(df.index, pd.DatetimeIndex):
           issues.append("Index must be a DatetimeIndex")

       if df.index.duplicated().any():
           issues.append(f"Found {df.index.duplicated().sum()} duplicate timestamps")

       # Check target column
       if "load" not in df.columns:
           issues.append("Missing required 'load' column")
       else:
           if df["load"].isna().mean() > 0.1:
               issues.append(f"High missing rate: {df['load'].isna().mean():.1%} of load values are NaN")

           # Physical sanity checks
           if (df["load"] < 0).any():
               issues.append("Negative load values detected (check sign convention)")

       # Check regularity
       if len(df) > 1:
           diffs = df.index.to_series().diff().dropna()
           if diffs.nunique() > 1:
               issues.append(f"Irregular intervals detected: {diffs.value_counts().to_dict()}")

       return issues

   # Use before creating datasets
   issues = validate_energy_data(df)
   if issues:
       for issue in issues:
           print(f"  ⚠ {issue}")
       raise ValueError(f"Data validation failed with {len(issues)} issue(s)")

OpenSTEF also provides built-in validation for forecast datasets. Use ``validate_horizons_present`` to confirm that expected forecast horizons exist in a versioned dataset:

.. code-block:: python

   from openstef_core.datasets import validate_horizons_present

   validate_horizons_present(dataset, horizons=expected_horizons)


Complete Data Pipeline Example
------------------------------

Putting it all together—a realistic pipeline that loads data, validates it, runs a forecast, and stores results:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from pathlib import Path
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage

   # 1. Configure data sources
   engine = create_engine("postgresql://user:pass@host/energy_db")
   storage = LocalBenchmarkStorage(base_path=Path("./results"))

   # 2. Load and validate
   end = datetime.now()
   start = end - timedelta(days=30)

   df = pd.read_sql(
       "SELECT timestamp, load_mw AS load, temperature FROM measurements "
       "WHERE timestamp BETWEEN %(start)s AND %(end)s ORDER BY timestamp",
       engine, params={"start": start, "end": end},
       index_col="timestamp", parse_dates=["timestamp"],
   )

   # Reindex and handle gaps
   full_index = pd.date_range(start=df.index.min(), end=df.index.max(),
                              freq="15min", name="timestamp")
   df = df.reindex(full_index).interpolate(method="time", limit=4)

   dataset = TimeSeriesDataset(df.dropna(), sample_interval=timedelta(minutes=15))

   # 3. Feed into OpenSTEF forecasting pipeline
   # (See deployment guide for full pipeline configuration)
   # model.predict(dataset) -> forecast_dataset

   # 4. Store results
   # storage.save_backtest_output(target, forecast_dataset)

.. note:: [DIAGRAM: Data flow showing external sources → pandas DataFrame → TimeSeriesDataset → OpenSTEF pipeline → BenchmarkStorage → external sinks]


Summary
-------

The key principles for data integration with OpenSTEF:

- **All data flows through pandas DataFrames** wrapped in ``TimeSeriesDataset``—connect any source that can produce a DataFrame
- **Encapsulate data access** in provider classes to keep pipelines portable across environments
- **Validate early**—check data quality before it enters the forecasting pipeline
- **Handle missing data explicitly**—interpolate small gaps, flag or remove large ones
- **Use the storage interface** (``BenchmarkStorage``) for writing results, making it easy to swap backends

For production deployment patterns that build on these integration techniques, see :doc:`deployment`.