Data Integration
================

This page covers how to bring data into OpenSTEF from common storage backends, write forecasts back to those systems, and ensure data quality before it reaches the forecasting pipeline. It focuses on the practical plumbing that surrounds the model — reading, validating, and writing time series data.

For how to use that data to train models and generate forecasts, see :doc:`use_cases`. For running these pipelines in production, see :doc:`deployment`.

.. note::

   All examples on this page target OpenSTEF V4. If you are migrating from V3, see :doc:`migration_v3_v4` for breaking changes in the data layer.

Reading Data
------------

OpenSTEF's core data structure is ``TimeSeriesDataset``, a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex``. Any source that can produce a DataFrame with a timezone-aware datetime index can feed into the pipeline. The sections below show how to construct that DataFrame from the most common backends.

From a CSV or Parquet File
^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest starting point is a local file. This pattern is also useful for testing pipelines before connecting to a live source.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.read_parquet("measurements.parquet")
   df.index = pd.to_datetime(df.index, utc=True)

   dataset = TimeSeriesDataset(data=df)

The index must be timezone-aware. If your source returns naive timestamps, convert them explicitly:

.. code-block:: python

   df.index = df.index.tz_localize("Europe/Amsterdam")

From Amazon S3
^^^^^^^^^^^^^^

Use ``boto3`` or any S3-compatible client to download a file, then construct the dataset as above. OpenSTEF's ``openstef_beam`` package also ships ``S3BenchmarkStorage`` for persisting benchmark artefacts to S3, which you can use as a reference for building your own S3 read/write helpers.

.. code-block:: python

   import io
   import boto3
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   s3 = boto3.client("s3")
   obj = s3.get_object(Bucket="my-energy-data", Key="measurements/grid_A.parquet")
   df = pd.read_parquet(io.BytesIO(obj["Body"].read()))
   df.index = pd.to_datetime(df.index, utc=True)

   dataset = TimeSeriesDataset(data=df)

For high-throughput ingestion, consider reading directly into a Beam pipeline via ``openstef_beam`` — see :doc:`deployment` for distributed pipeline patterns.

From Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When your data lives in a Delta table on Databricks, use the ``databricks-connect`` or ``pyspark`` client to read it into a Pandas DataFrame:

.. code-block:: python

   from pyspark.sql import SparkSession
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   spark = SparkSession.builder.getOrCreate()

   df = (
       spark.table("energy_catalog.measurements.grid_a")
       .filter("timestamp >= '2024-01-01'")
       .toPandas()
   )
   df = df.set_index("timestamp")
   df.index = pd.to_datetime(df.index, utc=True)

   dataset = TimeSeriesDataset(data=df)

Keep the Spark-to-Pandas conversion as late as possible to avoid pulling large volumes of data into the driver. Apply time range filters and column selection in Spark before calling ``toPandas()``.

From InfluxDB
^^^^^^^^^^^^^

InfluxDB returns data in a format that maps naturally to a time-indexed DataFrame. Use the official ``influxdb-client`` package:

.. code-block:: python

   from influxdb_client import InfluxDBClient
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="my-org")
   query_api = client.query_api()

   tables = query_api.query_data_frame(
       'from(bucket:"energy") '
       '|> range(start: -7d) '
       '|> filter(fn: (r) => r._measurement == "grid_load") '
       '|> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")'
   )
   tables = tables.set_index("_time").drop(columns=["result", "table"], errors="ignore")
   tables.index = pd.to_datetime(tables.index, utc=True)

   dataset = TimeSeriesDataset(data=tables)

From PostgreSQL
^^^^^^^^^^^^^^^

Use ``psycopg2`` or ``SQLAlchemy`` to query a relational database and load the result directly into a DataFrame:

.. code-block:: python

   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   engine = create_engine("postgresql+psycopg2://user:pass@db-host:5432/energy_db")

   df = pd.read_sql(
       """
       SELECT timestamp, load_mw, wind_speed, temperature
       FROM measurements
       WHERE grid_id = 'A' AND timestamp >= NOW() - INTERVAL '7 days'
       ORDER BY timestamp
       """,
       con=engine,
       index_col="timestamp",
       parse_dates={"timestamp": {"utc": True}},
   )

   dataset = TimeSeriesDataset(data=df)

.. note::

   Always pass ``utc=True`` when parsing timestamps from SQL. Mixed-timezone data will cause silent errors downstream.

Custom Sources
^^^^^^^^^^^^^^

Any callable that returns a timezone-aware ``pandas.DataFrame`` can act as a data source. A clean pattern is to wrap the source in a small adapter class that implements a ``load() -> TimeSeriesDataset`` interface, keeping the rest of your pipeline source-agnostic.

.. code-block:: python

   from datetime import datetime, timedelta, timezone
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset


   class MyApiAdapter:
       def __init__(self, base_url: str, api_key: str):
           self.base_url = base_url
           self.api_key = api_key

       def load(self, start: datetime, end: datetime) -> TimeSeriesDataset:
           # Replace with your actual HTTP call
           df = self._fetch(start, end)
           df.index = pd.to_datetime(df.index, utc=True)
           return TimeSeriesDataset(data=df)

       def _fetch(self, start: datetime, end: datetime) -> pd.DataFrame:
           raise NotImplementedError

Validating Input Data
---------------------

OpenSTEF provides three built-in validation transforms in ``openstef_models.transforms.validation``. Apply them before passing data to a model to catch quality issues early.

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker,
   )

**CompletenessChecker** raises an error (or logs a warning, depending on configuration) when the fraction of missing values in any column exceeds a threshold.

**FlatlineChecker** detects columns that have been stuck at a constant value for too long — a common symptom of a broken sensor or a stale cache.

**InputConsistencyChecker** is used after fitting: it ensures that the columns present at prediction time match those seen during training. Extra columns are dropped with a warning; missing columns raise an error.

A typical pre-training validation pipeline looks like this:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker

   raw: TimeSeriesDataset = my_adapter.load(start=..., end=...)

   completeness = CompletenessChecker()
   flatline = FlatlineChecker()

   checked = completeness.fit_transform(raw)
   checked = flatline.fit_transform(checked)

   # checked is now safe to pass to a model

Handling Missing Data
---------------------

After validation, gaps in the time series still need to be resolved before training or inference. The recommended approach is to resample to the target interval and then interpolate or forward-fill, depending on the physical meaning of the feature.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   df = dataset.to_pandas()

   # Resample to 15-minute intervals, filling short gaps by interpolation
   df = df.resample("15min").mean().interpolate(method="time", limit=4)

   # For features where forward-fill is more appropriate (e.g. weather forecasts)
   df[["temperature", "wind_speed"]] = (
       df[["temperature", "wind_speed"]].ffill(limit=8)
   )

   clean_dataset = TimeSeriesDataset(data=df)

.. note::

   ``limit=4`` in the example above allows gaps of up to one hour (4 × 15 min) to be interpolated. Longer gaps should be flagged rather than silently filled, as they can distort model training.

Constructing a ``ForecastInputDataset``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the data is clean, wrap it in a ``ForecastInputDataset`` to attach the target column and forecast start time. This is the type expected by the model's ``prepare_input`` and ``predict`` methods.

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   forecast_start = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)

   input_dataset = ForecastInputDataset.from_timeseries(
       dataset=clean_dataset,
       target_column="load_mw",
       forecast_start=forecast_start,
   )

   # Access helpers
   print(input_dataset.target_series.head())
   print(input_dataset.forecast_start)

Writing Forecasts Back to Storage
----------------------------------

After calling ``model.predict()``, you receive a ``ForecastDataset``. Convert it to a DataFrame and write it to your storage backend.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastDataset

   forecast: ForecastDataset = model.predict(input_dataset)
   df_out = forecast.to_pandas()

The resulting DataFrame has a ``DatetimeIndex`` and one column per quantile (e.g. ``q05``, ``q50``, ``q95``), plus a ``median`` column.

Writing to PostgreSQL
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   df_out["grid_id"] = "A"
   df_out.to_sql(
       "forecasts",
       con=engine,
       if_exists="append",
       index=True,
       index_label="timestamp",
   )

Writing to InfluxDB
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from influxdb_client import WriteOptions
   from influxdb_client.client.write_api import SYNCHRONOUS

   write_api = client.write_api(write_options=SYNCHRONOUS)
   write_api.write(
       bucket="energy",
       record=df_out,
       data_frame_measurement_name="grid_load_forecast",
       data_frame_tag_columns=["grid_id"],
   )

Writing to S3 (Parquet)
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import io
   import boto3

   buffer = io.BytesIO()
   df_out.to_parquet(buffer)
   buffer.seek(0)

   s3 = boto3.client("s3")
   s3.put_object(
       Bucket="my-energy-data",
       Key="forecasts/grid_A/2024-06-01T12.parquet",
       Body=buffer.read(),
   )

Persisting Pipeline Artefacts with DataSaveCallback
-----------------------------------------------------

When running a full training workflow, use ``DataSaveCallback`` to automatically capture intermediate datasets (e.g. preprocessed training data, feature importance) without modifying the pipeline itself.

.. code-block:: python

   from openstef_models.workflows.callbacks import DataSaveCallback
   from pathlib import Path

   callback = DataSaveCallback(output_dir=Path("/tmp/pipeline_artefacts"))

   # Pass the callback when constructing or running your workflow
   # (exact API depends on the workflow class you are using)

This is particularly useful during development and debugging, where you want to inspect what the pipeline saw at each stage without adding ad-hoc print statements.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

Putting It All Together
-----------------------

A complete end-to-end integration pattern combining the steps above:

.. code-block:: python

   from datetime import datetime, timedelta, timezone
   from sqlalchemy import create_engine
   import pandas as pd

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastInputDataset
   from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker

   # 1. Read
   engine = create_engine("postgresql+psycopg2://user:pass@db:5432/energy")
   df = pd.read_sql(
       "SELECT timestamp, load_mw, temperature, wind_speed "
       "FROM measurements WHERE grid_id = 'A' ORDER BY timestamp",
       con=engine,
       index_col="timestamp",
       parse_dates={"timestamp": {"utc": True}},
   )

   # 2. Validate
   dataset = TimeSeriesDataset(data=df)
   dataset = CompletenessChecker().fit_transform(dataset)
   dataset = FlatlineChecker().fit_transform(dataset)

   # 3. Fill gaps
   df_clean = dataset.to_pandas().resample("15min").mean().interpolate(method="time", limit=4)
   dataset = TimeSeriesDataset(data=df_clean)

   # 4. Prepare for forecasting
   forecast_start = datetime.now(tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
   input_dataset = ForecastInputDataset.from_timeseries(
       dataset=dataset,
       target_column="load_mw",
       forecast_start=forecast_start,
   )

   # 5. Predict (assumes a fitted model is already available)
   forecast = model.predict(input_dataset)

   # 6. Write back
   forecast.to_pandas().to_sql(
       "forecasts", con=engine, if_exists="append",
       index=True, index_label="timestamp",
   )

For scheduling this pipeline in production and handling failures gracefully, see :doc:`deployment`. For domain-specific examples such as congestion forecasting, see :doc:`use_cases`.