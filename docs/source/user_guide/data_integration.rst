Data Integration
================

OpenSTEF is a library — it does not prescribe where your data lives or how it moves. Instead, it defines clear data contracts through its dataset classes, and leaves the ingestion and egress layers entirely to you. This page explains how to feed data into OpenSTEF from common storage systems, how to write forecasts back out, and how to handle the practical realities of missing values and data quality issues along the way.

For deployment patterns that wrap these pipelines in schedulers or containers, see :doc:`deployment`. For end-to-end worked examples, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

The OpenSTEF Data Contract
--------------------------

All data entering OpenSTEF must be wrapped in one of two dataset classes from ``openstef_core``:

- ``TimeSeriesDataset`` — a single snapshot of time series data with a ``DatetimeIndex`` and a fixed ``sample_interval``.
- ``VersionedTimeSeriesDataset`` — a composition of multiple ``TimeSeriesDataset`` parts, each with its own ``available_at`` column recording when each observation became known. This is the correct choice for realistic backtesting and production pipelines where data arrives with delays or revisions.

Both classes validate the data on construction and expose a ``.data`` attribute that is a plain ``pandas.DataFrame``. The target column is named ``load`` by default. Feature columns (weather, calendar, etc.) can carry any name.

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # Minimal dataset: a DatetimeIndex, a target column, and at least one feature
    df = pd.DataFrame(
        {
            "load": [100.0, 110.0, 105.0],
            "temperature": [12.5, 13.0, 12.8],
        },
        index=pd.date_range("2025-01-01", periods=3, freq="h", name="timestamp"),
    )

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Once you have a ``TimeSeriesDataset``, you can pass it directly to ``ForecastingModel.fit()`` or ``ForecastingModel.predict()``. Everything else on this page is about getting your raw data into that shape.

Reading from Common Sources
---------------------------

PostgreSQL
^^^^^^^^^^

Use ``psycopg2`` or ``SQLAlchemy`` to pull data into a DataFrame, then wrap it in a dataset. The key step is ensuring the index is a timezone-aware ``DatetimeIndex``.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")

    query = """
        SELECT timestamp, load, temperature
        FROM measurements
        WHERE timestamp >= NOW() - INTERVAL '30 days'
        ORDER BY timestamp
    """

    df = pd.read_sql(query, engine, index_col="timestamp", parse_dates=["timestamp"])
    df.index = df.index.tz_localize("UTC")  # ensure timezone-aware index

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

InfluxDB
^^^^^^^^

InfluxDB returns data in a wide-format DataFrame when using the ``influxdb-client`` library with the pandas extra. The index is already a ``DatetimeIndex``, so the conversion is straightforward.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://localhost:8086", token="my-token", org="my-org")
    query_api = client.query_api()

    tables = query_api.query_data_frame(
        'from(bucket:"energy") |> range(start: -30d) '
        '|> filter(fn: (r) => r._measurement == "grid_load") '
        '|> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")'
    )

    # InfluxDB returns _time as the index; rename to match OpenSTEF convention
    df = tables.rename(columns={"_time": "timestamp"}).set_index("timestamp")
    df.index.name = "timestamp"

    dataset = TimeSeriesDataset(data=df[["load", "temperature"]], sample_interval=timedelta(minutes=15))

S3 (Parquet)
^^^^^^^^^^^^

OpenSTEF's dataset classes have first-class Parquet support. If your data lake stores observations as Parquet files, you can load them directly without going through a plain DataFrame:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # Load a single snapshot
    dataset = TimeSeriesDataset.read_parquet(
        path="s3://my-bucket/measurements/2025-01.parquet",
        sample_interval=timedelta(hours=1),
    )

    # Load a versioned dataset (data with available_at tracking)
    versioned = VersionedTimeSeriesDataset.read_parquet(
        path="s3://my-bucket/measurements/versioned_2025-01.parquet",
        sample_interval=timedelta(hours=1),
    )

.. note::

   ``read_parquet`` accepts any path that ``pandas.read_parquet`` accepts, including ``s3://`` URIs when ``s3fs`` is installed. For authenticated access, configure your AWS credentials via environment variables or an IAM role before calling this method.

Databricks
^^^^^^^^^^

When running inside a Databricks notebook or job, use the Spark-to-pandas bridge. The pattern is identical to the PostgreSQL case once you have a pandas DataFrame:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # spark is available in the Databricks runtime
    spark_df = spark.sql("""
        SELECT timestamp, load, temperature
        FROM hive_metastore.energy.measurements
        WHERE timestamp >= current_timestamp() - INTERVAL 30 DAYS
    """)

    df = spark_df.toPandas()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").sort_index()

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

Custom Sources
^^^^^^^^^^^^^^

Any source that can produce a ``pandas.DataFrame`` with a ``DatetimeIndex`` works. The pattern is always the same: fetch → clean index → wrap in ``TimeSeriesDataset``. For sources that deliver data with a known publication delay (e.g., weather forecasts revised every six hours), use ``VersionedTimeSeriesDataset.from_dataframe()`` and include an ``available_at`` column:

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Suppose your API returns observations with a known publication timestamp
    df = pd.DataFrame(
        {
            "available_at": [datetime(2025, 1, 1, 6, 0), datetime(2025, 1, 1, 6, 0)],
            "load": [100.0, 110.0],
            "temperature": [12.5, 13.0],
        },
        index=pd.DatetimeIndex(
            [datetime(2025, 1, 1, 0, 0), datetime(2025, 1, 1, 1, 0)],
            name="timestamp",
        ),
    )

    versioned = VersionedTimeSeriesDataset.from_dataframe(
        data=df,
        sample_interval=timedelta(hours=1),
        available_at_column="available_at",
    )

Handling Missing Data
---------------------

OpenSTEF's training pipeline drops rows where the target column (``load``) is ``NaN`` and raises ``InsufficientlyCompleteError`` if no training data remains. Feature columns with missing values are handled by the preprocessing pipeline, but sparse or heavily gapped data will degrade model quality.

The recommended approach is to impute or flag missing values before constructing the dataset:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Reindex to a regular grid to expose implicit gaps as explicit NaNs
    full_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="h",
        name="timestamp",
    )
    df = df.reindex(full_index)

    # Interpolate feature columns; leave target NaNs for OpenSTEF to handle
    df["temperature"] = df["temperature"].interpolate(method="time", limit=3)

    # Optionally flag rows that were imputed
    df["temperature_imputed"] = df["temperature"].isna().shift(1).fillna(False)

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

.. note::

   Lag-based preprocessing transforms (e.g., a 14-day lag feature) will introduce ``NaN`` values at the start of the dataset. Use the ``cutoff_history`` parameter on ``ForecastingModel`` to exclude these incomplete rows from training automatically.

Data Validation
---------------

Before passing data to a model, it is good practice to assert basic structural invariants. ``TimeSeriesDataset`` performs some validation on construction (consistent sample interval, required columns for specialised dataset types), but domain-level checks are your responsibility.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.exceptions import TimeSeriesValidationError

    def validate_and_wrap(df: pd.DataFrame, sample_interval: timedelta) -> TimeSeriesDataset:
        required_columns = {"load", "temperature"}
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Input DataFrame is missing columns: {missing}")

        if df.index.duplicated().any():
            raise ValueError("Input DataFrame contains duplicate timestamps.")

        gap_threshold = sample_interval * 3
        gaps = df.index.to_series().diff().dropna()
        large_gaps = gaps[gaps > gap_threshold]
        if not large_gaps.empty:
            import warnings
            warnings.warn(
                f"Found {len(large_gaps)} gaps larger than {gap_threshold} in input data. "
                "Model quality may be reduced.",
                stacklevel=2,
            )

        try:
            return TimeSeriesDataset(data=df, sample_interval=sample_interval)
        except TimeSeriesValidationError as exc:
            raise ValueError(f"Dataset construction failed: {exc}") from exc

Writing Forecasts Back to Storage
----------------------------------

After calling ``model.predict()``, you receive a ``ForecastDataset``. Its ``.data`` attribute is a plain DataFrame that you can write to any sink.

Writing to Parquet (local or S3)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ForecastDataset`` inherits the ``.to_parquet()`` method from the dataset base classes:

.. code-block:: python

    from openstef_core.datasets.validated_datasets import ForecastDataset

    forecast: ForecastDataset = model.predict(dataset)

    # Write locally
    forecast.to_parquet("forecasts/2025-01-01.parquet")

    # Write to S3 (requires s3fs)
    forecast.to_parquet("s3://my-bucket/forecasts/2025-01-01.parquet")

Writing to a Database
^^^^^^^^^^^^^^^^^^^^^

Extract the underlying DataFrame and use standard pandas or SQLAlchemy tooling:

.. code-block:: python

    from sqlalchemy import create_engine

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/mydb")

    result_df = forecast.data.reset_index()  # move DatetimeIndex to a column
    result_df.to_sql(
        name="forecasts",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
    )

Using the DataSaveCallback for Debugging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During development it is useful to persist intermediate datasets — training inputs, prepared features, and raw forecasts — without modifying your pipeline code. The ``DataSaveCallback`` handles this automatically:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

    callback = DataSaveCallback(
        cache_dir=Path("debug_output"),
        save_prepared_data=True,
        save_predict_data=True,
        save_forecast=True,
        save_contributions=True,
    )

    workflow = CustomForecastingWorkflow(
        model=model,
        callbacks=[callback],
    )

Each callback invocation writes a timestamped Parquet file under ``cache_dir``, named after the workflow's ``run_name``. This is particularly useful when diagnosing unexpected forecast behaviour without adding ad-hoc ``print`` statements.

Implementing a Custom Storage Backend
--------------------------------------

For benchmarking pipelines that need to persist backtest results to a non-standard location (e.g., a proprietary data warehouse), implement the ``BenchmarkStorage`` abstract interface from ``openstef_beam``:

.. code-block:: python

    from openstef_beam.benchmarking.storage.benchmark_storage import BenchmarkStorage
    from openstef_beam.benchmarking.benchmark_target import BenchmarkTarget
    from openstef_core.datasets import TimeSeriesDataset

    class MyWarehouseStorage(BenchmarkStorage):
        def __init__(self, connection):
            self.conn = connection

        def save_backtest_output(self, target: BenchmarkTarget, output: TimeSeriesDataset) -> None:
            self.conn.write(
                table="backtest_predictions",
                data=output.data,
                target_id=target.name,
            )

        def load_backtest_output(self, target: BenchmarkTarget) -> TimeSeriesDataset:
            df = self.conn.read(table="backtest_predictions", target_id=target.name)
            return TimeSeriesDataset(data=df, sample_interval=target.sample_interval)

        def has_backtest_output(self, target: BenchmarkTarget) -> bool:
            return self.conn.exists(table="backtest_predictions", target_id=target.name)

        # Implement remaining abstract methods: save/load/has for evaluation and analysis outputs

For S3-backed benchmarking pipelines, ``openstef_beam`` ships a ready-made ``S3BenchmarkStorage`` that writes locally and syncs to S3, so you do not need to implement this interface yourself in most cloud deployments.

.. note::

   See :doc:`deployment` for guidance on wiring storage backends into scheduled production pipelines, and :doc:`use_cases` for complete end-to-end examples that combine data ingestion, model training, and forecast persistence.