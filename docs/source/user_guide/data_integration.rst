Data Integration
================

OpenSTEF is a library — it does not prescribe where your data lives or how it moves through your infrastructure. Instead, it defines clear data structures (primarily :class:`TimeSeriesDataset` and :class:`ForecastDataset`) that sit at the boundary between your storage layer and the forecasting pipeline. This page explains how to connect those structures to real-world data sources, write forecast results back to storage, and handle the data quality issues that inevitably arise in production.

For deployment patterns that orchestrate these pipelines end-to-end, see :doc:`deployment`. For worked examples of specific forecasting use cases, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

Reading Input Data
------------------

OpenSTEF's forecasting pipeline expects a :class:`~openstef_core.datasets.TimeSeriesDataset` (or its versioned variant :class:`~openstef_core.datasets.VersionedTimeSeriesDataset`). Both wrap a ``pandas.DataFrame`` with a ``DatetimeIndex`` named ``timestamp``. The key insight is that **all source-specific logic lives outside OpenSTEF** — you are responsible for fetching and shaping a DataFrame; OpenSTEF takes it from there.

The minimal shape for training data is a DataFrame with:

- A ``DatetimeIndex`` (timezone-aware recommended)
- A target column (e.g. ``load``) containing the quantity to forecast
- Any number of feature columns (weather, calendar, etc.)

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # df is a plain pandas DataFrame you have loaded from any source
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
   )

The sections below show how to produce that DataFrame from common storage backends.

From PostgreSQL
^^^^^^^^^^^^^^^

A straightforward SQLAlchemy query is all that is needed. Shape the result so that the timestamp column becomes the index before handing it to OpenSTEF.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")

   query = """
       SELECT timestamp, load, temperature, wind_speed
       FROM measurements
       WHERE timestamp >= %(start)s AND timestamp < %(end)s
       ORDER BY timestamp
   """

   df = pd.read_sql(
       query,
       engine,
       params={"start": "2024-01-01", "end": "2024-04-01"},
       index_col="timestamp",
       parse_dates=["timestamp"],
   )

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   Ensure your ``timestamp`` column is stored with timezone information in PostgreSQL (``TIMESTAMPTZ``). Naive timestamps can cause subtle alignment bugs when combining data from multiple sources.

From InfluxDB
^^^^^^^^^^^^^

InfluxDB returns data in a format that maps naturally to a time-indexed DataFrame. Use the official ``influxdb-client`` package and pivot the result before constructing the dataset.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://influxdb:8086", token="my-token", org="my-org")
   query_api = client.query_api()

   flux_query = """
   from(bucket: "energy")
     |> range(start: 2024-01-01T00:00:00Z, stop: 2024-04-01T00:00:00Z)
     |> filter(fn: (r) => r._measurement == "grid_load")
     |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
   """

   df = query_api.query_data_frame(flux_query)
   df = df.set_index("_time").rename_axis("timestamp")
   df.index = pd.to_datetime(df.index, utc=True)

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

From Amazon S3
^^^^^^^^^^^^^^

Parquet files on S3 are a common pattern for storing historical feature datasets. ``pandas`` reads them directly via ``s3fs``.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.read_parquet(
       "s3://my-bucket/energy-data/features/substation_42.parquet",
       storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
   )
   df.index = pd.to_datetime(df.index, utc=True)
   df.index.name = "timestamp"

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For large datasets, consider reading only the required time window using Parquet predicate pushdown:

.. code-block:: python

   import pyarrow.dataset as ds

   arrow_ds = ds.dataset("s3://my-bucket/energy-data/features/", format="parquet")
   table = arrow_ds.to_table(
       filter=(ds.field("timestamp") >= "2024-01-01") & (ds.field("timestamp") < "2024-04-01")
   )
   df = table.to_pandas().set_index("timestamp")

From Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, use a Spark DataFrame and convert to pandas after filtering. Keep the Spark-to-pandas conversion as late and narrow as possible to avoid memory pressure.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # spark is the SparkSession available in Databricks notebooks
   spark_df = (
       spark.table("catalog.energy.measurements")
       .filter("timestamp >= '2024-01-01' AND timestamp < '2024-04-01'")
       .select("timestamp", "load", "temperature", "wind_speed")
   )

   df = spark_df.toPandas()
   df = df.set_index("timestamp")
   df.index = df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   If your Databricks environment uses Unity Catalog with Delta tables that have versioning or ``available_at`` metadata, consider using :class:`~openstef_core.datasets.VersionedTimeSeriesDataset` instead. Its ``from_dataframe`` constructor accepts an ``available_at_column`` argument that captures when each observation became available — important for avoiding data leakage in backtesting.

Building a Custom Source Adapter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For sources not covered above, the pattern is always the same: implement a function (or class) that returns a ``pandas.DataFrame`` with a ``DatetimeIndex``, then wrap it in a ``TimeSeriesDataset``. Keeping this adapter thin and stateless makes it easy to test and swap out.

.. code-block:: python

   from datetime import timedelta
   from typing import Protocol
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset


   class MeasurementSource(Protocol):
       def fetch(self, start: str, end: str) -> pd.DataFrame:
           ...


   def load_training_dataset(
       source: MeasurementSource,
       start: str,
       end: str,
       sample_interval: timedelta = timedelta(minutes=15),
   ) -> TimeSeriesDataset:
       df = source.fetch(start=start, end=end)
       df.index = pd.to_datetime(df.index, utc=True)
       df.index.name = "timestamp"
       return TimeSeriesDataset(data=df, sample_interval=sample_interval)

Handling Missing Data
---------------------

Real-world energy data contains gaps. OpenSTEF's training pipeline drops rows where the **target column** contains ``NaN`` values — it raises ``InsufficientlyCompleteError`` if nothing remains after that step. Feature columns with missing values are handled by the preprocessing pipeline, but it is good practice to address obvious gaps before constructing the dataset.

A typical pre-processing pattern:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Reindex to a complete regular grid, introducing NaN for missing rows
   full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="15min", tz="UTC")
   df = df.reindex(full_index)
   df.index.name = "timestamp"

   # Interpolate short gaps in feature columns (e.g. weather data)
   feature_cols = ["temperature", "wind_speed"]
   df[feature_cols] = df[feature_cols].interpolate(method="time", limit=4)

   # Leave the target column (load) as NaN — OpenSTEF will exclude those rows
   # from training automatically, which is the correct behaviour.

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. warning::

   Do not forward-fill or interpolate the target column (``load``) before passing data to OpenSTEF. Fabricated target values will silently corrupt your model. Let OpenSTEF handle missing targets by dropping them.

For very sparse data — more than roughly 20% of target values missing over the training window — consider widening the training window rather than imputing values.

Data Validation
---------------

OpenSTEF performs structural validation when you construct a :class:`~openstef_core.datasets.TimeSeriesDataset`: it checks that the index is a ``DatetimeIndex``, that timestamps are sorted, and that the sample interval is consistent. Specialised subclasses add domain-specific checks — for example, :class:`~openstef_core.datasets.validated_datasets.ForecastInputDataset` verifies that the target column is present.

You can add your own validation before constructing the dataset:

.. code-block:: python

   import pandas as pd

   def validate_input_dataframe(df: pd.DataFrame, target_col: str = "load") -> None:
       if target_col not in df.columns:
           raise ValueError(f"Target column '{target_col}' not found. Got: {list(df.columns)}")

       if not isinstance(df.index, pd.DatetimeIndex):
           raise TypeError("DataFrame index must be a DatetimeIndex.")

       if df.index.tz is None:
           raise ValueError("DatetimeIndex must be timezone-aware.")

       duplicate_ts = df.index[df.index.duplicated()]
       if not duplicate_ts.empty:
           raise ValueError(f"Duplicate timestamps found: {duplicate_ts[:5].tolist()}")

       missing_pct = df[target_col].isna().mean() * 100
       if missing_pct > 50:
           raise ValueError(
               f"Target column '{target_col}' is {missing_pct:.1f}% missing. "
               "Check your data source."
           )

   validate_input_dataframe(df)
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Writing Forecasts Back to Storage
----------------------------------

After a forecasting run, the pipeline produces a :class:`~openstef_core.datasets.validated_datasets.ForecastDataset`. Its underlying data is accessible as a ``pandas.DataFrame`` via the ``.data`` attribute, which you can write to any storage backend.

**Writing to Parquet / S3:**

.. code-block:: python

   # result is a ForecastDataset returned by the workflow
   result.to_parquet("s3://my-bucket/forecasts/substation_42_latest.parquet",
                     storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"})

**Writing to PostgreSQL:**

.. code-block:: python

   from sqlalchemy import create_engine

   engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")

   forecast_df = result.data.reset_index()  # move timestamp back to a column
   forecast_df["substation_id"] = 42
   forecast_df["created_at"] = pd.Timestamp.now(tz="UTC")

   forecast_df.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False,
       method="multi",
   )

**Writing to InfluxDB:**

.. code-block:: python

   from influxdb_client import InfluxDBClient, WriteOptions

   client = InfluxDBClient(url="http://influxdb:8086", token="my-token", org="my-org")
   write_api = client.write_api(write_options=WriteOptions(batch_size=500))

   forecast_df = result.data.copy()
   forecast_df["substation_id"] = "42"

   write_api.write(
       bucket="forecasts",
       record=forecast_df,
       data_frame_measurement_name="grid_load_forecast",
       data_frame_tag_columns=["substation_id"],
   )

Using the DataSaveCallback for Intermediate Outputs
----------------------------------------------------

During development and debugging it is useful to persist intermediate pipeline artefacts — prepared training data, raw predictions, feature contributions — without modifying your main pipeline code. OpenSTEF provides :class:`~openstef_models.workflows.callbacks.data_save.DataSaveCallback` for exactly this purpose.

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback

   debug_callback = DataSaveCallback(
       cache_dir=Path("/tmp/openstef_debug"),
       save_prepared_data=True,
       save_predict_data=True,
       save_forecast=True,
       save_contributions=True,
   )

   # Pass the callback when constructing your workflow
   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[debug_callback],
   )

After a run, the ``cache_dir`` will contain Parquet files for each stage, named by the workflow's ``run_name``. This is particularly useful when diagnosing data quality issues in production — you can inspect exactly what the model saw without adding print statements.

.. note::

   ``DataSaveCallback`` is intended for debugging and analysis, not as a primary write-back mechanism. For production forecast storage, write from the ``ForecastDataset`` directly as shown in the previous section.

Building a Complete Pipeline
-----------------------------

Putting the pieces together, a realistic pipeline that reads from PostgreSQL, runs a forecast, and writes results back might look like this:

.. code-block:: python

   from datetime import timedelta, datetime, timezone
   from pathlib import Path
   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   # --- 1. Read ---
   engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")
   df = pd.read_sql(
       "SELECT timestamp, load, temperature FROM measurements "
       "WHERE timestamp >= %(start)s ORDER BY timestamp",
       engine,
       params={"start": "2024-01-01"},
       index_col="timestamp",
       parse_dates=["timestamp"],
   )
   df.index = df.index.tz_localize("UTC")

   # --- 2. Validate and wrap ---
   full_index = pd.date_range(df.index.min(), df.index.max(), freq="15min", tz="UTC")
   df = df.reindex(full_index)
   df.index.name = "timestamp"
   df["temperature"] = df["temperature"].interpolate(method="time", limit=4)

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

   # --- 3. Forecast (workflow and model assumed pre-configured) ---
   result = workflow.predict(data=dataset)

   # --- 4. Write back ---
   result.data.reset_index().to_sql(
       "forecasts", engine, if_exists="append", index=False, method="multi"
   )

For production scheduling and error handling around this pattern, see :doc:`deployment`.