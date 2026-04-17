Data Integration
================

OpenSTEF is a library — it does not dictate where your data lives or how it is stored. Instead, it defines clear data structures that you populate from whatever source is appropriate for your infrastructure. This page explains how to bring data in from common storage systems, how to write forecast results back out, and how to handle the practical challenges of missing data and validation that arise in real energy data pipelines.

.. note::

   For deployment patterns that orchestrate these pipelines in production, see :doc:`deployment`.
   For end-to-end use case examples that combine data integration with modelling, see :doc:`use_cases`.

.. contents:: On this page
   :local:
   :depth: 2

Understanding OpenSTEF's Data Model
------------------------------------

Before connecting any data source, it helps to understand what OpenSTEF expects. The library's core data container is ``TimeSeriesDataset``, a wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex``. It enforces a consistent ``sample_interval`` and provides persistence helpers. For data that tracks *when* each observation became available — essential for realistic backtesting — ``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts and adds an ``available_at`` dimension.

Your integration job is straightforward: query your storage system, assemble a ``pandas.DataFrame`` with a ``DatetimeIndex``, and hand it to one of these constructors. OpenSTEF handles everything downstream.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Minimal example: wrap any DataFrame with a DatetimeIndex
   df = pd.DataFrame(
       {"load": [100.0, 102.5, 98.0], "temperature": [15.1, 15.3, 14.9]},
       index=pd.date_range("2025-01-01", periods=3, freq="15min", name="timestamp"),
   )
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Reading from Common Sources
----------------------------

PostgreSQL
^^^^^^^^^^

A typical energy data warehouse stores metered load and weather features in a relational database. Use ``psycopg2`` or ``SQLAlchemy`` to execute a query and pass the result directly to ``VersionedTimeSeriesDataset.from_dataframe``. The ``available_at`` column — recording when each row was ingested — enables temporally honest training.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from sqlalchemy import create_engine
   from openstef_core.datasets import VersionedTimeSeriesDataset

   engine = create_engine("postgresql+psycopg2://<user>:<password>@<host>/<dbname>")

   query = """
       SELECT
           timestamp,
           available_at,
           load_mw,
           temperature_c,
           wind_speed_ms
       FROM measurements
       WHERE timestamp BETWEEN :start AND :end
       ORDER BY timestamp
   """

   df = pd.read_sql(
       query,
       engine,
       params={"start": "2024-01-01", "end": "2025-01-01"},
       parse_dates=["timestamp", "available_at"],
       index_col="timestamp",
   )

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data=df,
       sample_interval=timedelta(minutes=15),
       available_at_column="available_at",
   )

InfluxDB
^^^^^^^^

InfluxDB is common for high-frequency meter data. Query a time range, pivot the result into a wide DataFrame, and wrap it as usual.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://<host>:8086", token="<token>", org="<org>")
   query_api = client.query_api()

   flux_query = """
   from(bucket: "energy")
     |> range(start: 2025-01-01T00:00:00Z, stop: 2025-02-01T00:00:00Z)
     |> filter(fn: (r) => r._measurement == "grid_load")
     |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
   """

   result = query_api.query_data_frame(flux_query)
   result = result.set_index("_time").rename_axis("timestamp")
   result.index = result.index.tz_localize(None)  # strip timezone if needed

   dataset = TimeSeriesDataset(
       data=result[["load_mw", "temperature_c"]],
       sample_interval=timedelta(minutes=15),
   )

AWS S3 / Azure Blob / GCS
^^^^^^^^^^^^^^^^^^^^^^^^^^

Object storage is the most common landing zone for pre-processed feature data. OpenSTEF's ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` both expose ``to_parquet`` and ``read_parquet`` methods. For cloud paths, use ``fsspec``-backed file systems so the path is transparent to OpenSTEF.

.. code-block:: python

   import s3fs
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import timedelta

   fs = s3fs.S3FileSystem(anon=False)

   # Read a parquet file written by a previous pipeline run
   with fs.open("s3://<bucket>/features/substation_42.parquet", "rb") as f:
       dataset = VersionedTimeSeriesDataset.read_parquet(
           path=f,
           sample_interval=timedelta(minutes=15),
       )

   # Write back after enrichment
   with fs.open("s3://<bucket>/features/substation_42_enriched.parquet", "wb") as f:
       dataset.to_parquet(path=f)

.. note::

   ``read_parquet`` and ``to_parquet`` preserve all dataset metadata (sample interval, versioning columns) in the Parquet file's custom metadata block. Round-tripping through object storage is lossless.

Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^^

When your feature engineering runs on Databricks, the simplest integration is to materialise a Delta table to a Pandas DataFrame using the Databricks ``dbutils`` or the ``delta-spark`` connector, then hand it to OpenSTEF on the driver.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Inside a Databricks notebook or job
   spark_df = spark.table("energy_features.substation_42_features")
   df = spark_df.toPandas().set_index("timestamp")

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data=df,
       sample_interval=timedelta(minutes=15),
       available_at_column="available_at",
   )

For large-scale parallel training across many substations, see the ``openstef-beam`` package, which distributes OpenSTEF workflows across Apache Beam runners (including Dataflow on GCP and Spark on Databricks).

Custom Sources
^^^^^^^^^^^^^^

Any source that can produce a ``pandas.DataFrame`` with a ``DatetimeIndex`` works. A common pattern is to wrap your data access logic in a thin function that returns a ``TimeSeriesDataset``, keeping the rest of your pipeline source-agnostic.

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset


   def load_from_custom_api(
       substation_id: str,
       start: datetime,
       end: datetime,
       sample_interval: timedelta = timedelta(minutes=15),
   ) -> TimeSeriesDataset:
       """Fetch features from an internal REST API and return an OpenSTEF dataset."""
       # Replace with your actual HTTP client call
       raw = _my_api_client.get_measurements(substation_id, start, end)
       df = pd.DataFrame(raw).set_index("timestamp")
       df.index = pd.to_datetime(df.index)
       return TimeSeriesDataset(data=df, sample_interval=sample_interval)

Writing Forecasts Back to Storage
-----------------------------------

After a prediction run, OpenSTEF produces a ``ForecastDataset`` — a validated ``TimeSeriesDataset`` subclass containing quantile forecasts. You can persist it with the built-in ``to_parquet`` method or write it to any database by accessing its underlying ``data`` DataFrame.

Using the Built-in DataSaveCallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For workflows built with ``CustomForecastingWorkflow``, the ``DataSaveCallback`` is the most convenient way to capture outputs without modifying your pipeline logic. It writes Parquet files at each lifecycle stage and is activated by setting ``debug=True`` on your forecaster factory, or by attaching it directly.

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback

   save_cb = DataSaveCallback(
       cache_dir=Path("/tmp/openstef_debug"),
       save_training_data=False,   # skip raw training data
       save_prepared_data=False,
       save_predict_data=False,
       save_forecast=True,         # only persist the forecast output
       save_contributions=False,
   )

   # Attach to your workflow before calling predict()
   workflow.callbacks.append(save_cb)

The callback writes files named ``debug_<run_name>_forecast.parquet`` into ``cache_dir``. These can be read back with ``TimeSeriesDataset.read_parquet`` or loaded directly with ``pandas.read_parquet`` for downstream processing.

Writing Directly to a Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you need to push forecasts to a live system — a dashboard database, an SCADA historian, or a message queue — access the ``ForecastDataset.data`` DataFrame and write it with your preferred client.

.. code-block:: python

   from sqlalchemy import create_engine

   engine = create_engine("postgresql+psycopg2://<user>:<password>@<host>/<dbname>")

   # forecast_result is a ForecastDataset returned by workflow.predict()
   df = forecast_result.data.reset_index()
   df["substation_id"] = "substation_42"
   df["created_at"] = pd.Timestamp.utcnow()

   df.to_sql(
       "forecasts",
       engine,
       if_exists="append",
       index=False,
       method="multi",
   )

Handling Missing Data
-----------------------

Real energy data is rarely complete. Meters go offline, communication links drop, and weather feeds have gaps. OpenSTEF's training pipeline will raise ``InsufficientlyCompleteError`` if the target column is entirely NaN after dropping missing rows, but it otherwise tolerates gaps in feature columns — the preprocessing transforms handle imputation internally.

Your responsibility is to ensure the *target* column (typically ``load``) has sufficient coverage before training, and that the *feature* columns used at prediction time are as complete as possible.

Reindexing to a Regular Grid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Irregular or gappy time series should be reindexed to the expected frequency before wrapping in a ``TimeSeriesDataset``. This makes gaps explicit as ``NaN`` rather than silently skipped rows.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # df has irregular timestamps due to dropped measurements
   expected_index = pd.date_range(
       start=df.index.min(),
       end=df.index.max(),
       freq="15min",
       name="timestamp",
   )
   df_regular = df.reindex(expected_index)

   # NaN rows are now explicit — OpenSTEF will drop NaN targets during training
   dataset = TimeSeriesDataset(data=df_regular, sample_interval=timedelta(minutes=15))

Forward-Filling Feature Columns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For slowly-changing features (e.g., weather forecasts updated hourly), forward-filling short gaps is usually appropriate before constructing the dataset.

.. code-block:: python

   # Forward-fill weather features for up to 4 steps (1 hour at 15-min resolution)
   df_regular[["temperature_c", "wind_speed_ms"]] = (
       df_regular[["temperature_c", "wind_speed_ms"]].ffill(limit=4)
   )

.. warning::

   Do not forward-fill the target column (``load``). OpenSTEF's training logic intentionally drops rows with NaN targets; imputing them would introduce artificial data that degrades model quality.

Concatenating Datasets from Multiple Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When features come from different systems with different update cadences, build each source as a separate ``TimeSeriesDataset`` and combine them using ``VersionedTimeSeriesDataset.concat``.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   meter_dataset = VersionedTimeSeriesDataset.from_dataframe(
       meter_df, sample_interval=timedelta(minutes=15)
   )
   weather_dataset = VersionedTimeSeriesDataset.from_dataframe(
       weather_df, sample_interval=timedelta(minutes=15)
   )

   # "outer" union preserves all timestamps from both sources
   combined = VersionedTimeSeriesDataset.concat(
       [meter_dataset, weather_dataset], mode="outer"
   )

Data Validation
-----------------

OpenSTEF performs structural validation when you construct a dataset — it checks that the index is a ``DatetimeIndex``, that required columns are present, and that the sample interval is consistent. Validation errors surface as ``TimeSeriesValidationError``.

For domain-level validation (e.g., checking that load values are within physically plausible bounds, or that timestamps are timezone-consistent), add these checks in your data loading layer before constructing the dataset.

.. code-block:: python

   from openstef_core.exceptions import TimeSeriesValidationError

   def validate_load_data(df: pd.DataFrame) -> None:
       """Raise ValueError if the DataFrame fails domain checks."""
       if df["load_mw"].lt(0).any():
           raise ValueError("Negative load values detected — check meter sign convention.")
       if df["load_mw"].gt(5000).any():
           raise ValueError("Load values exceed physical limit — possible unit error.")
       if df.index.duplicated().any():
           raise ValueError("Duplicate timestamps found — deduplicate before ingestion.")

   validate_load_data(df)

   try:
       dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
   except TimeSeriesValidationError as exc:
       logger.error("Dataset construction failed: %s", exc)
       raise

.. note::

   ``TimeSeriesValidationError`` is a subclass of ``ValueError``, so it can be caught generically or specifically depending on how much detail your error handling needs.

Putting It Together: A Realistic Pipeline
------------------------------------------

The following sketch combines the patterns above into a single function that could be called by a scheduler or orchestration tool (Airflow, Prefect, etc.) on each forecast cycle.

.. code-block:: python

   from datetime import datetime, timedelta
   from pathlib import Path

   import pandas as pd
   from sqlalchemy import create_engine

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.exceptions import TimeSeriesValidationError
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback


   def run_forecast_pipeline(
       substation_id: str,
       forecast_time: datetime,
       db_url: str,
       output_dir: Path,
   ) -> None:
       engine = create_engine(db_url)

       # 1. Load historical features from PostgreSQL
       df = pd.read_sql(
           "SELECT timestamp, available_at, load_mw, temperature_c "
           "FROM measurements WHERE substation_id = :sid "
           "AND timestamp >= :start ORDER BY timestamp",
           engine,
           params={"sid": substation_id, "start": forecast_time - timedelta(days=90)},
           parse_dates=["timestamp", "available_at"],
           index_col="timestamp",
       )

       # 2. Reindex to regular grid and validate
       expected_index = pd.date_range(
           df.index.min(), df.index.max(), freq="15min", name="timestamp"
       )
       df = df.reindex(expected_index)
       df[["temperature_c"]] = df[["temperature_c"]].ffill(limit=4)

       dataset = VersionedTimeSeriesDataset.from_dataframe(
           df, sample_interval=timedelta(minutes=15), available_at_column="available_at"
       )

       # 3. Run prediction (workflow setup omitted — see use_cases page)
       save_cb = DataSaveCallback(
           cache_dir=output_dir / substation_id,
           save_forecast=True,
       )
       workflow.callbacks.append(save_cb)
       forecast = workflow.predict(dataset, forecast_start=forecast_time)

       # 4. Write results back to database
       result_df = forecast.data.reset_index()
       result_df["substation_id"] = substation_id
       result_df.to_sql("forecasts", engine, if_exists="append", index=False)

This pattern keeps data access, validation, and persistence concerns separate from the modelling logic, making each layer independently testable and replaceable.