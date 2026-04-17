Data Integration
================

OpenSTEF is a library — it does not prescribe where your data lives or how it moves. Instead, it defines a clear data contract through ``TimeSeriesDataset``, and everything outside that boundary is your responsibility to wire up. This page explains how to bring data from common storage systems into OpenSTEF, how to write forecast results back out, and how to handle the practical issues of missing values and data quality that arise in real energy systems.

For production scheduling and orchestration patterns, see :doc:`deployment`. For worked examples of specific forecasting scenarios, see :doc:`use_cases`.

.. note:: [DIAGRAM: Data flow showing external sources (S3, InfluxDB, PostgreSQL, Databricks) feeding into TimeSeriesDataset, flowing through the OpenSTEF model workflow, and forecast outputs being written back to storage]

The Data Contract: ``TimeSeriesDataset``
-----------------------------------------

Every OpenSTEF model expects its input as a ``TimeSeriesDataset``. This is a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex``, a declared ``sample_interval``, and optional ``horizon`` and ``available_at`` columns for versioned forecasting. Understanding this contract is the key to integrating any data source.

The minimum requirements for a training dataset are:

- A ``DatetimeIndex`` with a consistent frequency matching ``sample_interval``
- A ``load`` column (the default target variable) containing the measured energy values
- Any additional feature columns (weather, calendar flags, etc.) alongside the target

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # A minimal DataFrame ready for OpenSTEF
    df = pd.DataFrame(
        {
            "load": [142.3, 138.7, 145.1, 151.0],
            "temperature": [12.4, 12.1, 11.8, 11.5],
        },
        index=pd.date_range("2024-01-01 00:00", periods=4, freq="15min"),
    )

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Once you can produce a ``TimeSeriesDataset``, the source of the underlying data is irrelevant to OpenSTEF. The sections below show how to do that from several common backends.


Reading from Common Sources
----------------------------

PostgreSQL
^^^^^^^^^^

A typical pattern is to query a time-windowed slice of measurements and feature data, then join them before wrapping in ``TimeSeriesDataset``.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta, datetime, timezone
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=90)

    query = """
        SELECT
            m.timestamp,
            m.load_mw        AS load,
            w.temperature_c  AS temperature,
            w.wind_speed_ms  AS wind_speed
        FROM measurements m
        LEFT JOIN weather_features w
            ON m.timestamp = w.timestamp
            AND m.location_id = w.location_id
        WHERE m.location_id = <location_id>
          AND m.timestamp BETWEEN :start AND :end
        ORDER BY m.timestamp
    """

    df = pd.read_sql(
        query,
        engine,
        params={"start": start, "end": end},
        index_col="timestamp",
        parse_dates=["timestamp"],
    )

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

InfluxDB
^^^^^^^^

InfluxDB stores measurements as tagged time series, making it a natural fit for energy meter data. Use the ``influxdb-client`` package to query and pivot the result into a wide DataFrame.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="<org>")
    query_api = client.query_api()

    flux_query = """
        from(bucket: "energy")
          |> range(start: -90d)
          |> filter(fn: (r) => r["_measurement"] == "grid_load")
          |> filter(fn: (r) => r["location"] == "<location_id>")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    result = query_api.query_data_frame(flux_query)
    result = result.set_index("_time").rename_axis("timestamp")
    result.index = result.index.tz_convert("UTC")

    # Keep only the columns OpenSTEF needs
    df = result[["load", "temperature"]].sort_index()

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Amazon S3 / Parquet Files
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` has a built-in ``read_parquet`` class method that reconstructs the dataset — including its ``sample_interval`` and column metadata — from a Parquet file written by OpenSTEF itself. For files stored on S3, pass an ``s3://`` URI directly to ``pandas`` (via ``pyarrow`` with ``s3fs`` installed) and then wrap the result.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Reading a file that was previously saved by OpenSTEF (preserves all metadata)
    dataset = TimeSeriesDataset.read_parquet(
        path="s3://my-bucket/openstef/training/location_42.parquet"
    )

    # Reading arbitrary Parquet data from S3
    df = pd.read_parquet(
        "s3://my-bucket/raw/measurements/location_42/2024-01.parquet",
        storage_options={"anon": False},  # uses default AWS credentials
    )
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, use the Spark session to read a Delta table and convert to a pandas DataFrame before constructing the dataset. Keep the Spark-to-pandas conversion as late as possible to benefit from Spark's pushdown optimisations.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Inside a Databricks notebook, `spark` is available in the global scope
    df_spark = (
        spark.table("energy.measurements")
        .filter("location_id = '<location_id>'")
        .filter("timestamp >= '2024-01-01'")
        .orderBy("timestamp")
    )

    df = df_spark.toPandas().set_index("timestamp")
    df.index = df.index.tz_localize("UTC")

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   When using Databricks, consider running OpenSTEF workflows as standard Python jobs
   rather than distributed Spark jobs. OpenSTEF models are single-node by design;
   parallelism is best achieved by running independent jobs per location.


Handling Missing Data
----------------------

Real-world energy data always has gaps. OpenSTEF's training pipeline will raise ``InsufficientlyCompleteError`` if the target column is entirely NaN after preprocessing, and it silently drops rows where the target is NaN during training. This means gaps in *features* are tolerated (they become NaN inputs to the model), but gaps in the *target* reduce your effective training set.

A practical strategy is to handle gaps before constructing the dataset:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Reindex to a complete regular grid, introducing NaN for missing timestamps
    full_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="15min",
    )
    df_complete = df.reindex(full_index)

    # Interpolate short gaps in features (e.g. up to 1 hour = 4 intervals)
    df_complete[["temperature", "wind_speed"]] = (
        df_complete[["temperature", "wind_speed"]]
        .interpolate(method="time", limit=4)
    )

    # Leave the target column (load) as NaN for genuine outages —
    # OpenSTEF will exclude those rows from training automatically.

    dataset = TimeSeriesDataset(
        data=df_complete,
        sample_interval=timedelta(minutes=15),
    )

.. warning::

   Do not forward-fill or interpolate the target column (``load``) to fill outage
   periods. Fabricated target values will silently corrupt your model. Leave them
   as ``NaN`` and let OpenSTEF's pipeline handle exclusion.

The ``cutoff_history`` parameter on the workflow model is also relevant here: lag-based feature engineering creates NaN values at the start of the dataset (e.g. a 14-day lag leaves the first 14 days unusable). Set ``cutoff_history=timedelta(days=14)`` to exclude this warm-up period from training rather than letting it pollute the feature matrix.


Data Validation
----------------

``TimeSeriesDataset`` performs lightweight structural validation on construction — it checks that the index is a ``DatetimeIndex`` and that ``horizon`` and ``available_at`` columns, if present, contain the correct types. For domain-level validation (range checks, stale data detection, sensor drift), you should add your own checks before constructing the dataset.

A minimal validation layer might look like:

.. code-block:: python

    import pandas as pd

    def validate_energy_dataframe(df: pd.DataFrame, max_load_mw: float = 5000.0) -> None:
        """Raise ValueError if the DataFrame fails basic sanity checks."""
        if df.index.duplicated().any():
            raise ValueError("Duplicate timestamps detected in input data.")

        if not df.index.is_monotonic_increasing:
            raise ValueError("Timestamps are not sorted in ascending order.")

        if df["load"].isna().mean() > 0.10:
            raise ValueError(
                f"More than 10% of load values are missing "
                f"({df['load'].isna().mean():.1%}). Check the data pipeline."
            )

        if (df["load"].dropna() < 0).any():
            raise ValueError("Negative load values detected.")

        if (df["load"].dropna() > max_load_mw).any():
            raise ValueError(f"Load values exceed physical maximum of {max_load_mw} MW.")

    validate_energy_dataframe(df)
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For validated forecast *output* datasets, OpenSTEF uses ``ForecastDataset`` internally — a subclass of ``TimeSeriesDataset`` that enforces the presence of required energy component columns. You will encounter this type when reading forecast results back from storage.


Writing Forecasts Back to Storage
-----------------------------------

Using ``DataSaveCallback``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest way to persist forecast outputs is ``DataSaveCallback``, which hooks into the workflow lifecycle and writes Parquet files at each stage — training data, preprocessed inputs, forecast outputs, and optionally feature contributions.

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    callback = DataSaveCallback(
        cache_dir=Path("/data/openstef/debug/location_42"),
        save_training_data=True,
        save_prepared_data=False,   # skip intermediate feature matrix
        save_predict_data=False,
        save_forecast=True,         # write forecast output to parquet
        save_contributions=False,
    )

    # Pass the callback when constructing your workflow
    # workflow = CustomForecastingWorkflow(..., callbacks=[callback])

The callback writes files named ``debug_<run_name>_forecast.parquet`` into ``cache_dir``. These can be read back with ``TimeSeriesDataset.read_parquet()``.

Custom Storage Backends
^^^^^^^^^^^^^^^^^^^^^^^^

For writing to a database or object store, implement a ``ForecastingCallback`` that fires on ``on_predict_end``:

.. code-block:: python

    from typing import Any, override
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
    from openstef_core.datasets.validated_datasets import ForecastDataset
    from openstef_models.mixins.callbacks import WorkflowContext
    from openstef_models.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
        ForecastingCallback,
    )

    class PostgreSQLForecastCallback(ForecastingCallback):
        """Writes forecast results to a PostgreSQL table after each prediction."""

        def __init__(self, engine, location_id: str) -> None:
            self.engine = engine
            self.location_id = location_id

        @override
        def on_predict_end(
            self,
            context: WorkflowContext[CustomForecastingWorkflow],
            data: VersionedTimeSeriesDataset | TimeSeriesDataset,
            result: ForecastDataset,
        ) -> None:
            df = result.to_pandas().reset_index()
            df["location_id"] = self.location_id
            df["created_at"] = pd.Timestamp.utcnow()
            df.to_sql(
                "forecasts",
                self.engine,
                if_exists="append",
                index=False,
                method="multi",
            )

The same pattern works for InfluxDB (write the DataFrame as line protocol), S3 (call ``result.to_parquet("s3://...")``), or any other backend.

For backtesting pipelines, the ``BenchmarkStorage`` abstract class provides a parallel interface — see the backtesting documentation for details.


Building a Complete Data Pipeline
-----------------------------------

Putting the pieces together, a realistic pipeline for a single location looks like this:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta, datetime, timezone
    from pathlib import Path
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    # --- 1. Read from source ---
    engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=90)

    df = pd.read_sql(
        "SELECT timestamp, load_mw AS load, temperature_c AS temperature "
        "FROM measurements WHERE location_id = <location_id> "
        "AND timestamp BETWEEN :start AND :end ORDER BY timestamp",
        engine,
        params={"start": start, "end": end},
        index_col="timestamp",
        parse_dates=["timestamp"],
    )

    # --- 2. Fill index gaps, validate ---
    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="15min")
    df = df.reindex(full_index)
    df["temperature"] = df["temperature"].interpolate(method="time", limit=4)

    if df["load"].isna().mean() > 0.10:
        raise RuntimeError("Too many missing load values — aborting pipeline.")

    # --- 3. Wrap in TimeSeriesDataset ---
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

    # --- 4. Configure output callback ---
    save_callback = DataSaveCallback(
        cache_dir=Path("/data/forecasts/location_42"),
        save_forecast=True,
    )

    # --- 5. Run workflow (model construction shown schematically) ---
    # workflow = CustomForecastingWorkflow(model=my_model, callbacks=[save_callback])
    # workflow.fit(dataset)
    # forecast = workflow.predict(dataset)

This pattern is intentionally simple. For scheduling, retries, and multi-location parallelism, see :doc:`deployment`.