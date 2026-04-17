Data Integration
================

OpenSTEF works with standard pandas DataFrames wrapped in typed dataset classes. This page explains how to bring data *into* that structure from common storage systems, how to write forecasts back out, and how to handle the data quality issues that arise in practice.

For how to run the forecasting pipeline itself once your data is loaded, see :doc:`use_cases`. For running these patterns in production, see :doc:`deployment`.

.. note::

   OpenSTEF does not ship built-in connectors for S3, InfluxDB, or Databricks. The integration layer is intentionally thin: you read data using whatever client library suits your infrastructure, build a ``TimeSeriesDataset``, and pass it to the pipeline. The examples below show that boundary clearly.

The ``TimeSeriesDataset`` contract
----------------------------------

Every data source must ultimately produce a ``TimeSeriesDataset`` (or ``VersionedTimeSeriesDataset`` for backtesting). The constructor validates the shape of the data immediately, so integration errors surface early rather than deep inside the pipeline.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Minimum viable dataset: a DatetimeIndex and a "load" column
   df = pd.DataFrame(
       {"load": [100.0, 102.5, 98.3, 101.1]},
       index=pd.date_range("2024-01-01", periods=4, freq="15min"),
   )

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

The index must be a ``DatetimeIndex``. The ``sample_interval`` tells the pipeline what cadence to expect; mismatches are caught during validation. Additional columns (weather features, calendar flags, lagged values) are passed through unchanged and become available to the feature pipeline.

Reading from common sources
---------------------------

PostgreSQL
^^^^^^^^^^

Use ``psycopg2`` or ``SQLAlchemy`` to pull a time-indexed query result directly into a DataFrame, then wrap it:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   engine = create_engine("postgresql+psycopg2://user:password@host:5432/mydb")

   query = """
       SELECT measured_at AS timestamp, load_mw AS load, temperature
       FROM meter_readings
       WHERE meter_id = 'grid-north-42'
         AND measured_at >= NOW() - INTERVAL '7 days'
       ORDER BY measured_at
   """

   df = pd.read_sql(query, engine, index_col="timestamp", parse_dates=["timestamp"])
   df.index = df.index.tz_localize("UTC")  # ensure timezone-aware index

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Keep the SQL query responsible for filtering and ordering. Avoid pulling large unfiltered tables into Python and filtering afterwards.

InfluxDB
^^^^^^^^

InfluxDB returns results as a long-format DataFrame. Pivot to wide format before constructing the dataset:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://influx:8086", token="<token>", org="my-org")
   query_api = client.query_api()

   flux_query = """
   from(bucket: "energy")
     |> range(start: -7d)
     |> filter(fn: (r) => r._measurement == "grid_load" and r.meter == "north-42")
     |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   """

   raw = query_api.query_data_frame(flux_query)
   raw = raw.set_index("_time")[["load", "temperature"]]
   raw.index = pd.to_datetime(raw.index, utc=True)
   raw = raw.sort_index()

   dataset = TimeSeriesDataset(data=raw, sample_interval=timedelta(minutes=15))

S3 / object storage
^^^^^^^^^^^^^^^^^^^^

Parquet files on S3 are a natural fit because ``TimeSeriesDataset`` serialises to and from Parquet natively. For raw CSV or Parquet files that were not written by OpenSTEF, read them with pandas first:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Reading a raw Parquet file from S3 via the filesystem abstraction
   df = pd.read_parquet(
       "s3://my-bucket/meter-data/north-42/2024-01.parquet",
       storage_options={"anon": False},  # uses boto3 credentials from environment
   )
   df.index = pd.to_datetime(df.index, utc=True)

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

If the file was previously saved by OpenSTEF using ``dataset.to_parquet()``, you can reconstruct it with full metadata intact:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset

   # Round-trip: metadata (sample_interval, etc.) is preserved in Parquet attrs
   dataset = TimeSeriesDataset.from_parquet("s3://my-bucket/datasets/north-42.parquet")

Databricks / Spark
^^^^^^^^^^^^^^^^^^

Collect a Spark DataFrame to the driver as a pandas DataFrame, then proceed as normal. Keep the Spark-side query as selective as possible to avoid moving large volumes of data:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # spark is an active SparkSession
   spark_df = spark.sql("""
       SELECT timestamp, load_mw AS load, temperature
       FROM hive_metastore.energy.meter_readings
       WHERE meter_id = 'north-42'
         AND timestamp >= current_timestamp() - INTERVAL 7 DAYS
       ORDER BY timestamp
   """)

   df = spark_df.toPandas().set_index("timestamp")
   df.index = df.index.dt.tz_localize("UTC")

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note:: [DIAGRAM: Data flow from external sources (PostgreSQL, InfluxDB, S3, Databricks) through a pandas DataFrame conversion step into TimeSeriesDataset, then into the OpenSTEF forecasting pipeline]

Handling missing data
---------------------

Real meter data contains gaps. OpenSTEF's validation transforms will flag or reject datasets with too many missing values, so it is better to handle gaps explicitly before constructing the dataset.

**Reindexing to a regular grid** is the most reliable approach. It makes gaps visible as ``NaN`` rather than silently skipping timestamps:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Enforce a complete 15-minute grid over the desired window
   full_index = pd.date_range(
       start="2024-01-01 00:00", end="2024-01-07 23:45",
       freq="15min", tz="UTC",
   )
   df = df.reindex(full_index)

   # Interpolate short gaps (up to 1 hour = 4 intervals)
   df["load"] = df["load"].interpolate(method="time", limit=4)

   # Flag remaining gaps rather than silently forward-filling
   missing_fraction = df["load"].isna().mean()
   if missing_fraction > 0.05:
       raise ValueError(f"Too many missing load values: {missing_fraction:.1%}")

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For weather features that are forecasts rather than measurements, forward-filling is usually appropriate because the feature itself represents a future value.

Data validation transforms
--------------------------

OpenSTEF provides three validation transforms that can be inserted into a preprocessing pipeline to catch quality issues at runtime:

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker,
   )

``CompletenessChecker``
   Raises if the fraction of non-null values in any column falls below a configurable threshold.

``FlatlineChecker``
   Detects runs of identical consecutive values, which typically indicate a stuck sensor or a failed data feed.

``InputConsistencyChecker``
   Verifies that the columns present at prediction time match those seen during training.

These transforms are designed to be composed into a ``FeaturePipeline``. A minimal validation-only pipeline looks like this:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker

   validation_steps = [
       CompletenessChecker(min_completeness=0.95),
       FlatlineChecker(max_flatline_length=8),  # 8 × 15 min = 2 hours
   ]

If a check fails, the transform raises an exception with a descriptive message. In a production pipeline you would catch these exceptions and route the affected meter to an alert queue rather than letting the whole batch fail. See :doc:`deployment` for patterns around error handling in production.

Writing forecasts back to storage
----------------------------------

The pipeline returns a ``ForecastDataset``. Its ``.data`` attribute is a standard pandas DataFrame, so writing it back to any storage system is straightforward.

**To Parquet on S3:**

.. code-block:: python

   # result is a ForecastDataset returned by the workflow
   result.data.to_parquet(
       "s3://my-bucket/forecasts/north-42/2024-01-08.parquet",
       storage_options={"anon": False},
   )

**To PostgreSQL:**

.. code-block:: python

   from sqlalchemy import create_engine

   engine = create_engine("postgresql+psycopg2://user:password@host:5432/mydb")

   df_out = result.data.reset_index()
   df_out["meter_id"] = "north-42"
   df_out["created_at"] = pd.Timestamp.utcnow()

   df_out.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False,
       method="multi",
   )

**To InfluxDB:**

.. code-block:: python

   from influxdb_client import InfluxDBClient, WriteOptions

   client = InfluxDBClient(url="http://influx:8086", token="<token>", org="my-org")
   write_api = client.write_api(write_options=WriteOptions(batch_size=500))

   df_out = result.data.copy()
   df_out["meter"] = "north-42"

   write_api.write(
       bucket="forecasts",
       record=df_out,
       data_frame_measurement_name="grid_load_forecast",
       data_frame_tag_columns=["meter"],
   )
   write_api.close()

Saving intermediate data for debugging
---------------------------------------

During development it is useful to inspect what the pipeline sees at each stage. The ``DataSaveCallback`` writes training data, prepared inputs, forecasts, and feature contributions to Parquet files without modifying the pipeline itself:

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback

   debug_callback = DataSaveCallback(
       cache_dir=Path("/tmp/openstef-debug"),
       save_prepared_data=True,
       save_predict_data=True,
       save_forecast=True,
       save_contributions=True,
   )

   # Pass to the workflow alongside any other callbacks
   workflow.fit(dataset, callbacks=[debug_callback])

The files land in ``cache_dir`` with names like ``debug_<run_name>_forecast.parquet``, which you can load with ``pd.read_parquet()`` for inspection.

.. note:: [VISUALIZATION: Example forecast output DataFrame showing columns for quantile predictions alongside the point forecast, indexed by timestamp]

Building a reusable data loader
---------------------------------

For production use it is worth wrapping your source-specific logic in a small function that always returns a ``TimeSeriesDataset``. This keeps the rest of the pipeline source-agnostic:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta, datetime
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset


   def load_meter_data(
       meter_id: str,
       start: datetime,
       end: datetime,
       engine,
       sample_interval: timedelta = timedelta(minutes=15),
   ) -> TimeSeriesDataset:
       """Load and validate meter data from PostgreSQL."""
       query = """
           SELECT measured_at AS timestamp, load_mw AS load, temperature
           FROM meter_readings
           WHERE meter_id = :meter_id
             AND measured_at BETWEEN :start AND :end
           ORDER BY measured_at
       """
       df = pd.read_sql(
           query, engine,
           params={"meter_id": meter_id, "start": start, "end": end},
           index_col="timestamp",
           parse_dates=["timestamp"],
       )
       df.index = df.index.tz_localize("UTC")

       # Enforce regular grid and interpolate short gaps
       full_index = pd.date_range(start=start, end=end, freq=sample_interval, tz="UTC")
       df = df.reindex(full_index)
       df["load"] = df["load"].interpolate(method="time", limit=4)

       return TimeSeriesDataset(data=df, sample_interval=sample_interval)

This pattern makes unit testing straightforward: replace the ``engine`` argument with a mock or a SQLite in-memory database, and the rest of the pipeline is unaffected.

.. note::

   When running multiple meters in parallel, create one engine per process rather than sharing a connection pool across threads. See :doc:`deployment` for concurrency patterns.