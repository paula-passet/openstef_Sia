Data Integration
================

OpenSTEF is a library, not a managed service — it has no built-in database drivers or cloud connectors. Instead, it defines clean data structures (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``) that you populate from whatever source your infrastructure uses. This page shows practical patterns for reading data into those structures from common sources, writing forecasts back to storage, and handling the data quality problems that arise along the way.

For production deployment considerations such as scheduling and containerisation, see :doc:`deployment`. For end-to-end worked examples, see :doc:`use_cases`.

.. note::

   All examples on this page assume you have installed the relevant third-party connectors
   (``boto3``, ``influxdb-client``, ``psycopg2``, etc.) separately. OpenSTEF itself has no
   hard dependency on any of them.

.. contents:: On this page
   :local:
   :depth: 2


Core data structures
--------------------

Before connecting any source, it helps to understand what OpenSTEF expects. The two primary
input types are:

- ``TimeSeriesDataset`` — a single DataFrame slice with a ``pd.DatetimeIndex`` and a fixed
  ``sample_interval``.
- ``VersionedTimeSeriesDataset`` — a composition of multiple ``TimeSeriesDataset`` parts, each
  carrying an ``available_at`` column that records *when* each observation became available.
  This is the right structure whenever your features arrive from different systems at different
  latencies (e.g. metering data delayed by 15 minutes, weather forecasts updated hourly).

Both live in ``openstef_core.datasets``:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

A ``TimeSeriesDataset`` wraps a plain ``pd.DataFrame`` — so the integration work is simply
getting your data into a DataFrame with a ``DatetimeIndex``, then handing it to the constructor.


Reading from PostgreSQL
-----------------------

PostgreSQL (or any SQLAlchemy-compatible database) is a common home for metering and SCADA
data. The pattern is: query into a DataFrame, set the index, then wrap:

.. code-block:: python

   from datetime import datetime, timedelta, timezone

   import pandas as pd
   import psycopg2
   from openstef_core.datasets import TimeSeriesDataset

   def load_from_postgres(
       conn_str: str,
       location_id: str,
       start: datetime,
       end: datetime,
   ) -> TimeSeriesDataset:
       query = """
           SELECT
               timestamp,
               load_mw,
               temperature_c
           FROM measurements
           WHERE location_id = %(location_id)s
             AND timestamp BETWEEN %(start)s AND %(end)s
           ORDER BY timestamp
       """
       df = pd.read_sql(
           query,
           con=conn_str,
           params={"location_id": location_id, "start": start, "end": end},
           index_col="timestamp",
           parse_dates=["timestamp"],
       )
       df.index = df.index.tz_localize("UTC")
       return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

The ``sample_interval`` must match the actual cadence of your data. OpenSTEF uses it to
detect gaps and to align multi-part versioned datasets.


Reading from InfluxDB
---------------------

InfluxDB is popular for high-frequency sensor data. The ``influxdb-client`` library returns
results as a ``pd.DataFrame`` when you use the ``query_data_frame`` method:

.. code-block:: python

   from datetime import timedelta

   import pandas as pd
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   def load_from_influx(
       url: str,
       token: str,
       org: str,
       bucket: str,
       measurement: str,
       start: str,
       stop: str,
   ) -> TimeSeriesDataset:
       client = InfluxDBClient(url=url, token=token, org=org)
       query_api = client.query_api()

       flux_query = f"""
           from(bucket: "{bucket}")
             |> range(start: {start}, stop: {stop})
             |> filter(fn: (r) => r._measurement == "{measurement}")
             |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
       """
       df: pd.DataFrame = query_api.query_data_frame(flux_query)
       df = df.rename(columns={"_time": "timestamp"}).set_index("timestamp")
       df.index = df.index.tz_convert("UTC")

       # Drop InfluxDB metadata columns
       df = df.drop(columns=["result", "table", "_measurement"], errors="ignore")

       return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))


Reading from S3 / object storage
---------------------------------

When data is stored as Parquet files on S3 (or compatible object storage such as Azure Blob
or GCS via ``fsspec``), you can read directly with ``pandas``:

.. code-block:: python

   from datetime import timedelta

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   def load_from_s3(
       bucket: str,
       key: str,
       aws_profile: str = "default",
   ) -> TimeSeriesDataset:
       path = f"s3://{bucket}/{key}"
       df = pd.read_parquet(
           path,
           storage_options={"profile": aws_profile},
       )
       if not isinstance(df.index, pd.DatetimeIndex):
           df = df.set_index("timestamp")
       df.index = pd.DatetimeIndex(df.index, tz="UTC")
       return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For large date ranges, partition your S3 prefix by date and load only the relevant partitions
before constructing the dataset. This avoids pulling unnecessary data into memory.


Reading from Databricks / Spark
---------------------------------

When your feature store or data lake runs on Databricks, convert a Spark DataFrame to pandas
before wrapping it:

.. code-block:: python

   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset

   def load_from_spark(spark_df, sample_interval_minutes: int = 15) -> TimeSeriesDataset:
       """Convert a Spark DataFrame to a TimeSeriesDataset.

       The Spark DataFrame must have a 'timestamp' column and numeric feature columns.
       """
       pdf = spark_df.toPandas()
       pdf = pdf.set_index("timestamp")
       pdf.index = pd.DatetimeIndex(pdf.index, tz="UTC")
       return TimeSeriesDataset(
           data=pdf,
           sample_interval=timedelta(minutes=sample_interval_minutes),
       )

.. note::

   For very large datasets, consider using the ``openstef-beam`` package, which provides
   distributed backtesting pipelines built on Apache Beam and is designed to run on
   Dataflow or Spark runners.


Composing multi-source datasets
---------------------------------

Real forecasting pipelines rarely have a single data source. Metering data, weather forecasts,
and calendar features often come from different systems with different update schedules.
``VersionedTimeSeriesDataset`` is designed for exactly this:

.. code-block:: python

   from datetime import datetime, timedelta

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   # --- Part 1: metering data (available with ~15 min delay) ---
   metering_df = pd.DataFrame(
       {"load_mw": [120.5, 118.3, 122.1], "available_at": [...]},
       index=pd.date_range("2025-01-01", periods=3, freq="15min", tz="UTC"),
   )
   metering_part = TimeSeriesDataset(metering_df, timedelta(minutes=15))

   # --- Part 2: weather forecast (updated hourly, available immediately) ---
   weather_df = pd.DataFrame(
       {"temperature_c": [3.2, 3.1, 3.0], "wind_speed_ms": [5.1, 5.3, 5.0],
        "available_at": [...]},
       index=pd.date_range("2025-01-01", periods=3, freq="15min", tz="UTC"),
   )
   weather_part = TimeSeriesDataset(weather_df, timedelta(minutes=15))

   # Combine — columns must be disjoint across parts
   versioned = VersionedTimeSeriesDataset(data_parts=[metering_part, weather_part])

The ``available_at`` column in each part tells OpenSTEF when each row of data was actually
observable. This is critical for backtesting: it prevents the model from accidentally using
information that would not have been available at prediction time.

Alternatively, if all your data arrives in a single DataFrame that already has an
``available_at`` column, use the convenience constructor:

.. code-block:: python

   versioned = VersionedTimeSeriesDataset.from_dataframe(
       data=combined_df,
       sample_interval=timedelta(minutes=15),
   )


Handling missing data
---------------------

OpenSTEF does not silently impute missing values — it raises explicit errors so you know
exactly what is wrong before a model trains on bad data.

**Missing target values** cause ``InsufficientlyCompleteError`` during ``ForecastingModel.fit``
if all target rows are ``NaN`` after dropping nulls. Rows with ``NaN`` targets are dropped
automatically from the training set, but if *none* remain, training is aborted.

**Sparse feature columns** are caught by ``CompletenessChecker``, a preprocessing transform
that computes the ratio of non-null values and raises ``InsufficientlyCompleteError`` if it
falls below a configurable threshold:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.exceptions import InsufficientlyCompleteError
   from openstef_models.transforms.validation import CompletenessChecker

   data = pd.DataFrame(
       {
           "load_mw": [100.0, np.nan, 102.0, np.nan],
           "temperature_c": [3.0, 3.1, np.nan, 3.3],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min", tz="UTC"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   checker = CompletenessChecker(
       columns=["load_mw", "temperature_c"],
       completeness_threshold=0.7,   # require at least 70 % non-null
   )

   try:
       checker.transform(dataset)
   except InsufficientlyCompleteError as exc:
       # Log, alert, or fall back to a simpler model
       print(f"Data quality check failed: {exc}")

You can weight columns differently if some features are more critical than others:

.. code-block:: python

   checker = CompletenessChecker(
       columns=["load_mw", "temperature_c"],
       weights={"load_mw": 2.0, "temperature_c": 1.0},
       completeness_threshold=0.6,
   )

For gaps that are acceptable to fill, apply standard pandas interpolation *before* wrapping
the DataFrame in a ``TimeSeriesDataset``:

.. code-block:: python

   # Fill short gaps (up to 2 consecutive missing values) by linear interpolation
   df["load_mw"] = df["load_mw"].interpolate(method="time", limit=2)

Keep gap-filling conservative. Interpolating over long outages produces plausible-looking
but misleading training data.


Validating column presence
---------------------------

Use ``validate_required_columns`` from ``openstef_core.datasets.validation`` to assert that
your DataFrame contains the columns your pipeline expects before constructing a dataset:

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns
   from openstef_core.exceptions import MissingColumnsError

   required = ["load_mw", "temperature_c", "wind_speed_ms"]

   try:
       validate_required_columns(df, required_columns=required)
   except MissingColumnsError as exc:
       raise ValueError(
           f"Source data is missing required columns: {exc.missing_columns}"
       ) from exc


Writing forecasts back to storage
-----------------------------------

After calling ``workflow.predict()``, you receive a ``ForecastDataset``. The simplest way to
persist it is via the built-in ``DataSaveCallback``, which writes Parquet files for forecasts,
intermediate inputs, and feature contributions:

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback

   callback = DataSaveCallback(
       cache_dir=Path("/data/forecasts"),
       save_forecast=True,
       save_predict_data=False,   # skip raw input snapshots in production
       save_contributions=True,   # keep SHAP-style feature contributions
   )

   # Pass the callback when constructing your workflow
   # workflow = CustomForecastingWorkflow(..., callbacks=[callback])

For writing to a database or message queue, implement a custom ``ForecastingCallback``. The
``on_predict_end`` hook receives the ``ForecastDataset`` result:

.. code-block:: python

   from typing import override
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastDataset
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )

   class DatabaseWriteCallback(ForecastingCallback):
       """Writes forecast results to a relational database after each prediction."""

       def __init__(self, conn_str: str, table: str) -> None:
           self.conn_str = conn_str
           self.table = table

       @override
       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: VersionedTimeSeriesDataset | TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           df = result.data.copy()
           df["run_name"] = context.workflow.run_name
           df["written_at"] = pd.Timestamp.utcnow()
           df.to_sql(
               self.table,
               con=self.conn_str,
               if_exists="append",
               index=True,
               index_label="timestamp",
           )

For MLflow tracking (metrics, artefacts, and model registry), OpenSTEF ships
``MLFlowStorageCallback`` in ``openstef_models.integrations.mlflow.mlflow_storage_callback``.
See the MLflow integration page for configuration details.


[DIAGRAM: Data integration flow showing external sources (PostgreSQL, InfluxDB, S3, Databricks/Spark) feeding into TimeSeriesDataset and VersionedTimeSeriesDataset, passing through CompletenessChecker validation, into ForecastingModel, and then out through ForecastingCallback to storage sinks (Parquet, database, MLflow)]


Custom data sources
--------------------

If your source does not fit any of the patterns above, the integration contract is minimal:
produce a ``pd.DataFrame`` with a ``pd.DatetimeIndex`` (timezone-aware, UTC recommended),
numeric feature columns, and — for versioned data — an ``available_at`` column. Everything
else is standard OpenSTEF.

A minimal custom loader skeleton:

.. code-block:: python

   from datetime import datetime, timedelta

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns


   class MySourceLoader:
       """Loads time series data from a proprietary API."""

       REQUIRED_COLUMNS = ["load_mw"]

       def __init__(self, api_client) -> None:
           self.client = api_client

       def load(self, start: datetime, end: datetime) -> TimeSeriesDataset:
           raw = self.client.fetch(start=start, end=end)          # returns list[dict]
           df = pd.DataFrame(raw).set_index("timestamp")
           df.index = pd.DatetimeIndex(df.index, tz="UTC")
           validate_required_columns(df, self.REQUIRED_COLUMNS)
           return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Keep loaders thin — their only job is to translate external representations into
``TimeSeriesDataset``. Validation, gap-filling, and feature engineering belong in separate
pipeline stages so they can be tested and swapped independently.