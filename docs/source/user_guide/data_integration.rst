Data Integration
================

OpenSTEF is a Python library that operates on standard pandas DataFrames wrapped in its own dataset abstractions. This means it integrates naturally with any data source you can read into a DataFrame — whether that is a cloud object store, a time-series database, a relational database, or a flat file. This page covers practical patterns for feeding data into OpenSTEF pipelines and writing forecast results back to storage.

For production deployment considerations (scheduling, containerisation, orchestration), see :doc:`deployment`. For worked end-to-end use cases, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

The Central Abstraction: TimeSeriesDataset
------------------------------------------

All data moving through OpenSTEF passes through ``TimeSeriesDataset`` (or its versioned counterpart ``VersionedTimeSeriesDataset``). These classes wrap a pandas DataFrame with a ``DatetimeIndex`` and carry metadata such as the sampling interval, horizon column, and availability timestamps.

The key entry point for custom data sources is ``TimeSeriesDataset.from_pandas()``, which accepts any well-formed DataFrame and validates it on construction:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Any DataFrame with a DatetimeIndex can become a TimeSeriesDataset
    df = pd.DataFrame(
        {"load": [100.2, 101.5, 99.8], "temperature": [12.1, 11.9, 12.3]},
        index=pd.date_range("2024-01-01", periods=3, freq="15min"),
    )

    dataset = TimeSeriesDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
    )

The ``sample_interval`` parameter tells OpenSTEF what cadence to expect. Mismatches between the declared interval and the actual index spacing will surface as validation errors early in the pipeline, before any model code runs.

Reading from Common Sources
---------------------------

PostgreSQL
^^^^^^^^^^

Use ``psycopg2`` or ``SQLAlchemy`` to pull data into a DataFrame, then wrap it:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")

    query = """
        SELECT measured_at AS timestamp, load_mw, temperature_c
        FROM measurements
        WHERE grid_id = 42
          AND measured_at BETWEEN '2024-01-01' AND '2024-02-01'
        ORDER BY measured_at
    """
    df = pd.read_sql(query, con=engine, index_col="timestamp", parse_dates=["timestamp"])
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = TimeSeriesDataset(
        data=df.rename(columns={"load_mw": "load", "temperature_c": "temperature"}),
        sample_interval=timedelta(minutes=15),
    )

.. note::

   OpenSTEF expects the target column to be named ``"load"`` by default. Rename columns from your source schema before constructing the dataset.

InfluxDB
^^^^^^^^

InfluxDB's Python client returns DataFrames directly from flux queries:

.. code-block:: python

    from influxdb_client import InfluxDBClient
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="my-token", org="my-org")
    query_api = client.query_api()

    tables = query_api.query_data_frame(
        'from(bucket:"energy") '
        '|> range(start: -30d) '
        '|> filter(fn: (r) => r._measurement == "grid_load") '
        '|> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")'
    )

    df = tables.set_index("_time")[["load", "temperature"]]
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Amazon S3 / Object Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Parquet files on S3 are a natural fit because ``TimeSeriesDataset`` has first-class Parquet support. If you have previously saved a dataset with ``to_parquet()``, you can reload it directly:

.. code-block:: python

    import s3fs
    from openstef_core.datasets import TimeSeriesDataset

    fs = s3fs.S3FileSystem(anon=False)

    # Read a raw Parquet file from S3 into a DataFrame
    with fs.open("s3://my-bucket/energy/grid42/2024-01.parquet") as f:
        df = pd.read_parquet(f)

    df.index = pd.to_datetime(df.index, utc=True)
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

If the Parquet file was written by OpenSTEF's own ``to_parquet()`` method, the metadata (sample interval, horizon column, etc.) is embedded in the file attributes and is restored automatically:

.. code-block:: python

    # Round-trip: save and reload preserving all metadata
    dataset.to_parquet("/tmp/grid42.parquet")
    restored = TimeSeriesDataset.read_parquet("/tmp/grid42.parquet")

Databricks / Spark
^^^^^^^^^^^^^^^^^^

When working inside a Databricks notebook or job, convert a Spark DataFrame to pandas before handing it to OpenSTEF:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    spark_df = spark.table("energy.measurements").filter("grid_id = 42")

    # Convert to pandas — keep this step close to the model code
    df = (
        spark_df
        .select("measured_at", "load_mw", "temperature_c")
        .toPandas()
        .rename(columns={"load_mw": "load", "temperature_c": "temperature"})
        .set_index("measured_at")
    )
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   For large datasets, apply time-range and column filters in Spark *before* calling ``toPandas()``. OpenSTEF operates in-memory on the pandas side, so only pull the rows and columns you actually need.

Building a Custom Source Connector
-----------------------------------

For recurring pipelines it is worth encapsulating the source-specific logic in a thin loader function. This keeps the OpenSTEF pipeline code clean and makes the connector independently testable:

.. code-block:: python

    from datetime import datetime, timedelta, timezone
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset


    def load_grid_dataset(
        grid_id: int,
        start: datetime,
        end: datetime,
        engine,
    ) -> TimeSeriesDataset:
        """Load measurement data for a single grid connection from PostgreSQL."""
        query = """
            SELECT measured_at, load_mw AS load, temperature_c AS temperature
            FROM measurements
            WHERE grid_id = %(grid_id)s
              AND measured_at BETWEEN %(start)s AND %(end)s
            ORDER BY measured_at
        """
        df = pd.read_sql(
            query,
            con=engine,
            params={"grid_id": grid_id, "start": start, "end": end},
            index_col="measured_at",
            parse_dates=["measured_at"],
        )
        df.index = pd.to_datetime(df.index, utc=True)
        return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))


    # Usage in a pipeline
    now = datetime.now(tz=timezone.utc)
    dataset = load_grid_dataset(
        grid_id=42,
        start=now - timedelta(days=30),
        end=now,
        engine=engine,
    )

Handling Missing Data
---------------------

Real-world energy data contains gaps: meter outages, communication failures, and maintenance windows all produce ``NaN`` values. OpenSTEF's validation layer will surface missing required columns immediately (raising ``MissingColumnsError``), but it does not automatically impute gaps in the time series values themselves.

A pragmatic approach is to handle imputation in the loader, before constructing the dataset:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    # Reindex to a complete regular grid, then fill short gaps
    full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq="15min", tz="UTC")
    df = df.reindex(full_index)

    # Forward-fill gaps up to 1 hour (4 intervals), leave longer gaps as NaN
    df["load"] = df["load"].ffill(limit=4)

    # Drop rows where the target is still missing — the model cannot use them
    df = df.dropna(subset=["load"])

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. warning::

   Avoid imputing long gaps with forward-fill or interpolation — this introduces artificial patterns that can degrade model quality. It is better to leave extended gaps as ``NaN`` and let the training pipeline handle them, or to exclude those periods entirely.

Data Validation
---------------

OpenSTEF provides validation utilities in ``openstef_core.datasets.validation`` that you can call directly in your pipeline:

.. code-block:: python

    from openstef_core.datasets.validation import validate_required_columns
    from openstef_core.exceptions import MissingColumnsError

    required = ["load", "temperature"]

    try:
        validate_required_columns(df, required_columns=required)
    except MissingColumnsError as exc:
        # exc.missing_columns lists exactly which columns are absent
        raise ValueError(f"Source data is missing columns: {exc.missing_columns}") from exc

For more structural checks — such as verifying that the sampling interval is consistent — construct the ``TimeSeriesDataset`` inside a try/except block and treat ``TimeSeriesValidationError`` as a data quality signal:

.. code-block:: python

    from openstef_core.datasets.validation import TimeSeriesValidationError

    try:
        dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
    except TimeSeriesValidationError as exc:
        # Log and route to a dead-letter queue or alerting system
        logger.error("Dataset validation failed for grid %s: %s", grid_id, exc)
        raise

Writing Forecasts Back to Storage
----------------------------------

``ForecastingModel.predict()`` returns a ``ForecastDataset``. Its underlying DataFrame is accessible via ``.data`` and can be written to any storage backend using standard pandas or database connectors.

.. code-block:: python

    from datetime import datetime, timezone

    forecast: ForecastDataset = pipeline.predict(dataset)

    # forecast.data is a regular pandas DataFrame
    result_df = forecast.data.copy()
    result_df["grid_id"] = 42
    result_df["produced_at"] = datetime.now(tz=timezone.utc)

    # Write to PostgreSQL
    result_df.to_sql(
        "forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="forecast_at",
    )

    # Write to Parquet on S3
    with fs.open("s3://my-bucket/forecasts/grid42/latest.parquet", "wb") as f:
        result_df.to_parquet(f)

For systems that need to store quantile forecasts alongside the median, use ``forecast.quantiles_data``, which returns a DataFrame with one column per quantile level.

Custom Storage Backends
^^^^^^^^^^^^^^^^^^^^^^^^

For benchmark and backtest workflows, OpenSTEF defines a ``BenchmarkStorage`` abstract interface that you can implement to plug in any persistence layer:

.. code-block:: python

    from openstef_models.benchmarking.storage import BenchmarkStorage
    from openstef_core.datasets import TimeSeriesDataset

    class DatabaseStorage(BenchmarkStorage):
        def __init__(self, engine):
            self.engine = engine

        def save_backtest_output(self, target, output: TimeSeriesDataset) -> None:
            df = output.data.copy()
            df["target_id"] = target.name
            df.to_sql("backtest_results", con=self.engine, if_exists="append")

        def load_backtest_output(self, target) -> TimeSeriesDataset:
            df = pd.read_sql(
                "SELECT * FROM backtest_results WHERE target_id = %(id)s",
                con=self.engine,
                params={"id": target.name},
                index_col="timestamp",
            )
            return TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

A Complete Pipeline Example
----------------------------

The following example ties together reading, validation, forecasting, and writing in a single function suitable for use as a scheduled job:

.. code-block:: python

    import logging
    from datetime import datetime, timedelta, timezone

    import pandas as pd
    from sqlalchemy import create_engine

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.datasets.validation import TimeSeriesValidationError
    from openstef_models.models.forecasting_model import ForecastingModel

    logger = logging.getLogger(__name__)


    def run_forecast_pipeline(grid_id: int, pipeline: ForecastingModel) -> None:
        engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")
        now = datetime.now(tz=timezone.utc)

        # 1. Load
        df = pd.read_sql(
            "SELECT measured_at, load_mw AS load, temperature_c AS temperature "
            "FROM measurements WHERE grid_id = %(g)s AND measured_at > %(t)s "
            "ORDER BY measured_at",
            con=engine,
            params={"g": grid_id, "t": now - timedelta(days=30)},
            index_col="measured_at",
            parse_dates=["measured_at"],
        )
        df.index = pd.to_datetime(df.index, utc=True)

        # 2. Impute short gaps
        full_index = pd.date_range(df.index.min(), df.index.max(), freq="15min", tz="UTC")
        df = df.reindex(full_index).ffill(limit=4).dropna(subset=["load"])

        # 3. Validate and wrap
        try:
            dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
        except TimeSeriesValidationError:
            logger.exception("Validation failed for grid %s", grid_id)
            return

        # 4. Forecast
        forecast = pipeline.predict(dataset)

        # 5. Write results
        result = forecast.data.assign(grid_id=grid_id, produced_at=now)
        result.to_sql("forecasts", con=engine, if_exists="append", index_label="forecast_at")
        logger.info("Stored %d forecast rows for grid %s", len(result), grid_id)

See :doc:`deployment` for guidance on scheduling this kind of pipeline in production environments, and :doc:`use_cases` for domain-specific examples such as congestion forecasting.