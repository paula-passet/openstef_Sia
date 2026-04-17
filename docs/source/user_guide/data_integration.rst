Data Integration
================

OpenSTEF works with standard pandas DataFrames and its own ``TimeSeriesDataset`` / ``VersionedTimeSeriesDataset`` wrappers, which means you can pull data from any source that can produce a DataFrame. This page covers practical patterns for reading training and feature data from common storage backends, writing forecasts back to storage, and ensuring data quality before it reaches the model.

For how to wire these patterns into a full production system, see :doc:`deployment`. For end-to-end use-case examples that combine data loading with model training, see :doc:`use_cases`.

.. note::

   All examples on this page assume you have installed OpenSTEF and its dependencies. Adjust connection strings and credentials to match your environment.

.. contents:: On this page
   :local:
   :depth: 2

Core data structures
--------------------

Before connecting to any external system, it helps to understand what OpenSTEF expects at its boundaries.

``TimeSeriesDataset``
   A thin wrapper around a ``pd.DataFrame`` with a ``pd.DatetimeIndex``. It enforces a fixed ``sample_interval`` and validates that required columns are present. This is the concrete type consumed by model training and inference.

``VersionedTimeSeriesDataset``
   A lazy composition of multiple ``TimeSeriesDataset`` parts, each carrying an ``available_at`` column that records when each row became available. This is the right structure for realistic backtesting and for combining data sources that arrive with different latencies. Calling ``.select_version()`` materialises the lazy composition into a concrete ``TimeSeriesDataset``.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Minimal TimeSeriesDataset from a plain DataFrame
   df = pd.DataFrame(
       {"load": [100.0, 102.5, 99.8]},
       index=pd.date_range("2024-01-01", periods=3, freq="15min"),
   )
   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   # VersionedTimeSeriesDataset from a parquet file (lazy, no materialisation yet)
   versioned = VersionedTimeSeriesDataset.read_parquet("load_measurements/grid_a.parquet")

The ``available_at`` column is optional for simple use cases but becomes essential when you need point-in-time correctness — for example, weather forecasts that are revised several times before the target hour arrives.

Reading data from storage
--------------------------

Parquet files (local or cloud object storage)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Parquet is the most convenient interchange format because ``VersionedTimeSeriesDataset`` has first-class support for it. The same API works for local paths, S3 URIs, and Azure Blob Storage paths via ``fsspec``.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Local file
   load_ds = VersionedTimeSeriesDataset.read_parquet("data/load_measurements/grid_a.parquet")

   # S3 — requires s3fs: pip install s3fs
   load_ds = VersionedTimeSeriesDataset.read_parquet(
       "s3://my-bucket/openstef/load_measurements/grid_a.parquet"
   )

   # Azure Blob Storage — requires adlfs: pip install adlfs
   load_ds = VersionedTimeSeriesDataset.read_parquet(
       "abfs://container/openstef/load_measurements/grid_a.parquet",
       storage_options={"account_name": "mystorageaccount", "sas_token": "<sas>"},
   )

When combining multiple sources, use ``VersionedTimeSeriesDataset.concat`` with a join mode that matches your data availability assumptions:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   load_ds    = VersionedTimeSeriesDataset.read_parquet("data/load/grid_a.parquet")
   weather_ds = VersionedTimeSeriesDataset.read_parquet("data/weather/grid_a.parquet")
   epex_ds    = VersionedTimeSeriesDataset.read_parquet("data/epex.parquet")

   # "left" keeps all timestamps from load_ds; weather and price are matched where available
   combined = VersionedTimeSeriesDataset.concat(
       [load_ds, weather_ds, epex_ds],
       mode="left",
   )

   # Materialise into a concrete TimeSeriesDataset for training
   dataset = combined.select_version()
   print(f"Shape: {dataset.data.shape}")
   print(f"Features: {dataset.feature_names}")

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

PostgreSQL
^^^^^^^^^^

Read directly with ``pandas`` and wrap the result:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")

   df = pd.read_sql(
       """
       SELECT timestamp, load_mw, temperature_c
       FROM measurements
       WHERE grid_id = 'grid_a'
         AND timestamp >= NOW() - INTERVAL '90 days'
       ORDER BY timestamp
       """,
       con=engine,
       index_col="timestamp",
       parse_dates=["timestamp"],
   )
   df.index = df.index.tz_localize("UTC")  # ensure timezone-aware index

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

InfluxDB
^^^^^^^^

Use the ``influxdb-client`` package to query and convert to a DataFrame:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="my-org")
   query_api = client.query_api()

   tables = query_api.query_data_frame(
       """
       from(bucket: "energy")
         |> range(start: -90d)
         |> filter(fn: (r) => r._measurement == "grid_load" and r.grid_id == "grid_a")
         |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
       """
   )

   df = tables.set_index("_time").rename_axis("timestamp")[["load_mw", "temperature_c"]]
   df.index = pd.to_datetime(df.index, utc=True)

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^

From a Databricks notebook or a Spark-enabled environment, convert a Spark DataFrame to pandas before wrapping it:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   spark_df = spark.table("energy.measurements.grid_a_load")

   pdf = (
       spark_df
       .filter("grid_id = 'grid_a'")
       .orderBy("timestamp")
       .toPandas()
       .set_index("timestamp")
   )
   pdf.index = pdf.index.tz_localize("UTC")

   dataset = VersionedTimeSeriesDataset.from_dataframe(pdf, timedelta(minutes=15))

For large datasets, write to parquet first and use ``VersionedTimeSeriesDataset.read_parquet`` — this avoids pulling the entire Spark result into driver memory.

Custom sources
^^^^^^^^^^^^^^

Any callable that returns a ``pd.DataFrame`` with a ``pd.DatetimeIndex`` can feed OpenSTEF. A minimal adapter pattern:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset


   def load_from_custom_api(grid_id: str, lookback_days: int = 90) -> TimeSeriesDataset:
       """Fetch measurements from an internal REST API."""
       import requests

       response = requests.get(
           f"https://internal-api/measurements/{grid_id}",
           params={"lookback_days": lookback_days},
       )
       response.raise_for_status()

       df = pd.DataFrame(response.json()["data"])
       df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
       df = df.set_index("timestamp").sort_index()

       return TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Handling missing data
---------------------

OpenSTEF provides validation transforms that catch common data quality issues before they silently degrade model accuracy.

Completeness and flatlines
^^^^^^^^^^^^^^^^^^^^^^^^^^

``CompletenessChecker`` raises or warns when the fraction of non-null values falls below a threshold. ``FlatlineChecker`` detects runs of identical consecutive values, which often indicate a stuck sensor or a failed data feed.

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker
   from openstef_core.datasets import TimeSeriesDataset

   # Raise if any column is less than 95 % complete
   checker = CompletenessChecker(min_completeness=0.95)
   checker.transform(dataset)

   # Warn if a column has more than 4 consecutive identical values
   flatline_checker = FlatlineChecker(max_flatline_length=4)
   flatline_checker.transform(dataset)

Input consistency
^^^^^^^^^^^^^^^^^

``InputConsistencyChecker`` validates that training and inference data share the same feature columns and sample interval — a common source of silent failures when a data pipeline changes upstream:

.. code-block:: python

   from openstef_models.transforms.validation import InputConsistencyChecker

   consistency_checker = InputConsistencyChecker(reference_dataset=training_dataset)
   consistency_checker.transform(inference_dataset)  # raises if columns or interval differ

Column validation
^^^^^^^^^^^^^^^^^

For energy component forecasting, ``validate_required_columns`` ensures that mandatory columns (e.g. ``load``) are present before training begins:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns

   validate_required_columns(df, required_columns=["load", "temperature_c"])
   # raises MissingColumnsError with a clear message listing the absent columns

Gap filling
^^^^^^^^^^^

OpenSTEF does not impose a specific imputation strategy — you own the gap-filling logic before constructing a ``TimeSeriesDataset``. A common approach is pandas ``resample`` + ``interpolate``:

.. code-block:: python

   # Resample to a regular 15-minute grid, then linearly interpolate short gaps
   df_filled = (
       df
       .resample("15min")
       .mean()
       .interpolate(method="time", limit=4)  # fill gaps up to 1 hour
   )

   # Drop rows where gaps were too long to fill
   df_filled = df_filled.dropna()

Writing forecasts back to storage
----------------------------------

After inference, ``ForecastDataset`` holds the model output. Write it back to whichever sink your downstream systems consume.

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   # forecast_ds is returned by your workflow's predict() call
   forecast_df: pd.DataFrame = forecast_ds.data

Parquet (local or S3)
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Local
   forecast_df.to_parquet("output/forecasts/grid_a_2024-01-01.parquet")

   # S3 — requires s3fs
   forecast_df.to_parquet("s3://my-bucket/openstef/forecasts/grid_a_2024-01-01.parquet")

PostgreSQL
^^^^^^^^^^

.. code-block:: python

   from sqlalchemy import create_engine

   engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")

   forecast_df.to_sql(
       name="forecasts",
       con=engine,
       if_exists="append",
       index=True,           # writes the DatetimeIndex as the timestamp column
       index_label="timestamp",
   )

InfluxDB
^^^^^^^^

.. code-block:: python

   from influxdb_client import InfluxDBClient, WriteOptions
   from influxdb_client.client.write_api import SYNCHRONOUS

   client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="my-org")
   write_api = client.write_api(write_options=SYNCHRONOUS)

   write_api.write(
       bucket="energy",
       record=forecast_df,
       data_frame_measurement_name="grid_load_forecast",
       data_frame_tag_columns=["quantile"],
   )

MLflow (experiment tracking)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use the built-in MLflow callback, forecasts, metrics, and artefacts are logged automatically during the workflow lifecycle. See ``openstef_models.integrations.mlflow.mlflow_storage_callback`` for configuration options.

A complete pipeline example
----------------------------

The following sketch ties together reading, validation, and writing in a single function that can be scheduled as a recurring job:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from sqlalchemy import create_engine
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker

   DB_URL = "postgresql+psycopg2://user:password@host:5432/energy_db"
   S3_FORECAST_PATH = "s3://my-bucket/openstef/forecasts"


   def run_forecast_pipeline(grid_id: str, workflow) -> None:
       # 1. Read
       load_ds = VersionedTimeSeriesDataset.read_parquet(
           f"s3://my-bucket/openstef/load/{grid_id}.parquet"
       )
       weather_ds = VersionedTimeSeriesDataset.read_parquet(
           f"s3://my-bucket/openstef/weather/{grid_id}.parquet"
       )
       dataset = VersionedTimeSeriesDataset.concat(
           [load_ds, weather_ds], mode="left"
       ).select_version()

       # 2. Validate
       validate_required_columns(dataset.data, required_columns=["load"])
       CompletenessChecker(min_completeness=0.95).transform(dataset)
       FlatlineChecker(max_flatline_length=4).transform(dataset)

       # 3. Forecast
       forecast_ds = workflow.predict(dataset)

       # 4. Write
       forecast_ds.data.to_parquet(f"{S3_FORECAST_PATH}/{grid_id}_latest.parquet")

       engine = create_engine(DB_URL)
       forecast_ds.data.to_sql(
           "forecasts", engine, if_exists="append",
           index=True, index_label="timestamp",
       )

.. mermaid:: /diagrams/user_guide/data_integration_diagram_2.mmd

.. note::

   For scheduling and containerising this pipeline in production, see :doc:`deployment`.
   For backtesting patterns that replay this pipeline over historical windows, see :doc:`use_cases`.