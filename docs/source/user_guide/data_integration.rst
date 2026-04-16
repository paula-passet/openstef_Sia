Data Integration
================

OpenSTEF is a Python library that operates on standard pandas DataFrames and its own ``TimeSeriesDataset`` abstraction. It does not prescribe how you fetch or store data — that responsibility belongs to your application. This page covers practical patterns for reading time series data from common sources, wrapping it in the structures OpenSTEF expects, writing forecasts back to storage, and handling the data quality issues that arise in real energy systems.

For deployment context around these patterns, see :doc:`deployment`. For end-to-end use-case examples that build on these foundations, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

Understanding OpenSTEF's Data Model
------------------------------------

Before connecting any source, it helps to understand what OpenSTEF actually expects. The core container is ``TimeSeriesDataset``, a thin wrapper around a pandas DataFrame with a ``pd.DatetimeIndex`` and a fixed ``sample_interval``. A ``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts — useful when different features arrive from different sources or at different cadences.

The minimum requirement for training is a DataFrame whose index is a timezone-aware ``DatetimeIndex`` and which contains at least a ``load`` column (the target variable). Feature columns such as weather variables, calendar features, or lagged values are added alongside it.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # Minimal structure: DatetimeIndex + target column
    df = pd.DataFrame(
        {
            "load": [142.3, 145.1, 139.8, 141.0],
            "temperature": [12.5, 12.3, 12.1, 11.9],
        },
        index=pd.date_range("2024-01-01 00:00", periods=4, freq="15min", tz="UTC"),
    )

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

The ``sample_interval`` must match the actual spacing of your index. OpenSTEF uses it to validate data completeness and to compute lag-based features correctly.


Reading from Common Sources
----------------------------

PostgreSQL
^^^^^^^^^^

PostgreSQL is a common choice for storing metered load data. Use ``psycopg2`` or ``SQLAlchemy`` to pull data into a DataFrame, then wrap it:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")

    query = """
        SELECT timestamp AT TIME ZONE 'UTC' AS timestamp,
               load_mw                       AS load,
               temperature_c                 AS temperature
        FROM   meter_readings
        WHERE  meter_id = %(meter_id)s
          AND  timestamp >= %(start)s
          AND  timestamp <  %(end)s
        ORDER  BY timestamp
    """

    df = pd.read_sql(
        query,
        engine,
        params={"meter_id": "substation_42", "start": "2024-01-01", "end": "2024-04-01"},
        index_col="timestamp",
        parse_dates={"timestamp": {"utc": True}},
    )

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   Always request timestamps in UTC from the database. OpenSTEF's internal logic assumes a consistent timezone throughout a dataset.

InfluxDB
^^^^^^^^

InfluxDB is popular for high-frequency sensor data. The ``influxdb-client`` library returns results as DataFrames when you use the ``query_data_frame`` method:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="my-token", org="my-org")
    query_api = client.query_api()

    flux_query = """
        from(bucket: "energy")
          |> range(start: 2024-01-01T00:00:00Z, stop: 2024-04-01T00:00:00Z)
          |> filter(fn: (r) => r["_measurement"] == "substation_load")
          |> filter(fn: (r) => r["meter_id"] == "substation_42")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(flux_query)
    df = df.set_index("_time").rename(columns={"load_mw": "load", "temp_c": "temperature"})
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[["load", "temperature"]].sort_index()

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

S3 / Parquet
^^^^^^^^^^^^

For batch workflows, Parquet files on S3 are an efficient format. ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` both expose ``to_parquet`` and ``read_parquet`` methods, so you can round-trip datasets without any custom serialisation logic:

.. code-block:: python

    import boto3
    import tempfile
    from pathlib import Path
    from datetime import timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    s3 = boto3.client("s3")
    bucket, key = "my-energy-bucket", "datasets/substation_42/training.parquet"

    with tempfile.NamedTemporaryFile(suffix=".parquet") as tmp:
        s3.download_file(bucket, key, tmp.name)
        dataset = VersionedTimeSeriesDataset.read_parquet(
            Path(tmp.name),
            sample_interval=timedelta(minutes=15),
        )

Saving back is equally straightforward:

.. code-block:: python

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        dataset.to_parquet(Path(tmp.name))
        s3.upload_file(tmp.name, bucket, key)

Databricks / Spark
^^^^^^^^^^^^^^^^^^

When your data lives in a Databricks lakehouse, convert a Spark DataFrame to pandas before handing it to OpenSTEF. Keep the conversion as late as possible to exploit Spark's distributed filtering:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # spark is a SparkSession available in Databricks notebooks
    spark_df = (
        spark.table("energy.meter_readings")
        .filter("meter_id = 'substation_42'")
        .filter("timestamp >= '2024-01-01' AND timestamp < '2024-04-01'")
        .select("timestamp", "load_mw", "temperature_c")
        .orderBy("timestamp")
    )

    df = spark_df.toPandas()
    df = df.rename(columns={"load_mw": "load", "temperature_c": "temperature"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Composing Multiple Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Real forecasting pipelines often combine load measurements from one system with weather data from another. ``VersionedTimeSeriesDataset`` is designed for exactly this:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # Load data from your SCADA / metering system
    load_dataset = TimeSeriesDataset(data=load_df, sample_interval=timedelta(minutes=15))

    # Weather data from a separate API or database
    weather_dataset = TimeSeriesDataset(data=weather_df, sample_interval=timedelta(minutes=15))

    # Combine — feature sets must be disjoint, sample intervals must match
    combined = VersionedTimeSeriesDataset(data_parts=[load_dataset, weather_dataset])

The combined dataset's index is the union of both parts, so gaps in one source do not silently discard rows from the other.


Handling Missing Data
----------------------

Energy time series routinely contain gaps: meter outages, communication failures, and scheduled maintenance all produce NaN values. OpenSTEF handles missing *feature* values through its preprocessing pipeline, but missing *target* values require attention before training.

OpenSTEF will raise ``InsufficientlyCompleteError`` if the target column is entirely NaN after dropping missing rows. For partial gaps, it silently drops those rows from training. This means you should inspect your data before passing it to a workflow:

.. code-block:: python

    import pandas as pd

    def check_data_quality(df: pd.DataFrame, target_col: str = "load") -> None:
        total = len(df)
        missing_target = df[target_col].isna().sum()
        missing_pct = 100 * missing_target / total

        print(f"Total rows:          {total}")
        print(f"Missing target rows: {missing_target} ({missing_pct:.1f}%)")

        for col in df.columns:
            n = df[col].isna().sum()
            if n > 0:
                print(f"  {col}: {n} missing ({100*n/total:.1f}%)")

    check_data_quality(df)

For short gaps in feature columns (e.g., a few missing temperature readings), forward-fill or linear interpolation is usually appropriate:

.. code-block:: python

    # Fill short gaps in feature columns only — leave target NaNs intact
    feature_cols = [c for c in df.columns if c != "load"]
    df[feature_cols] = (
        df[feature_cols]
        .interpolate(method="time", limit=4)   # fill gaps up to 1 hour (4 × 15 min)
        .ffill(limit=2)                         # catch any remaining edge NaNs
    )

.. warning::

   Do not interpolate the target column (``load``) before training. OpenSTEF intentionally drops NaN targets so the model is never trained on fabricated ground truth. Interpolating targets before passing data to the library will silently corrupt your training set.

Lag-based features (created during preprocessing) introduce NaN values at the start of the dataset — for example, a 14-day lag produces 14 days of NaN at the beginning. Use the ``cutoff_history`` parameter on ``ForecastingModel`` to exclude these incomplete rows automatically rather than trimming the DataFrame manually.


Writing Forecasts Back to Storage
-----------------------------------

After a workflow produces a ``ForecastDataset``, you need to persist it. The simplest approach for debugging or batch pipelines is the built-in ``DataSaveCallback``, which writes Parquet files at each stage of the workflow:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    callback = DataSaveCallback(
        cache_dir=Path("/tmp/openstef_debug"),
        save_forecast=True,
        save_predict_data=True,
        save_contributions=True,
    )

    # Pass to your workflow — forecasts are written automatically on predict_end
    workflow = CustomForecastingWorkflow(model=model, callbacks=[callback])

For production systems, implement a thin writer that reads the ``ForecastDataset`` after the workflow completes and pushes it to your target system:

.. code-block:: python

    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets.validated_datasets import ForecastDataset

    def write_forecast_to_postgres(
        forecast: ForecastDataset,
        meter_id: str,
        engine,
    ) -> None:
        df = forecast.data.copy()
        df["meter_id"] = meter_id
        df["created_at"] = pd.Timestamp.utcnow()

        df.to_sql(
            "forecasts",
            engine,
            if_exists="append",
            index=True,
            index_label="timestamp",
        )

For S3-backed benchmark pipelines, ``S3BenchmarkStorage`` from ``openstef_beam`` handles the upload/download cycle and local caching automatically. See the benchmarking documentation for details.

Custom Storage Backends
^^^^^^^^^^^^^^^^^^^^^^^^

If you need a fully custom persistence layer — for example, writing to InfluxDB or a proprietary time-series store — implement the ``BenchmarkStorage`` interface:

.. code-block:: python

    from openstef_beam.benchmarking.storage import BenchmarkStorage
    from openstef_beam.benchmarking.target_provider import BenchmarkTarget
    from openstef_core.datasets import TimeSeriesDataset

    class InfluxDBStorage(BenchmarkStorage):
        def __init__(self, write_api, query_api, bucket: str) -> None:
            self.write_api = write_api
            self.query_api = query_api
            self.bucket = bucket

        def save_backtest_output(
            self, target: BenchmarkTarget, output: TimeSeriesDataset
        ) -> None:
            # Convert to line protocol and write
            df = output.data
            df["meter_id"] = target.name
            self.write_api.write(
                bucket=self.bucket,
                record=df,
                data_frame_measurement_name="backtest_forecast",
                data_frame_tag_columns=["meter_id"],
            )

        def load_backtest_output(self, target: BenchmarkTarget) -> TimeSeriesDataset:
            # Query and reconstruct
            ...

The storage interface ensures that switching backends — from local files during development to S3 or a database in production — requires no changes to the pipeline logic itself.


Data Validation Tips
---------------------

A few practical checks before feeding data into any OpenSTEF workflow:

- **Index uniqueness**: duplicate timestamps cause silent data loss. Use ``df.index.duplicated().any()`` and deduplicate with ``df[~df.index.duplicated(keep="last")]``.
- **Monotonic index**: ``TimeSeriesDataset`` sorts on construction, but an unsorted index is a sign of upstream problems worth investigating.
- **Timezone consistency**: mix of tz-aware and tz-naive timestamps will raise errors. Standardise to UTC early in your pipeline.
- **Sample interval alignment**: if your data is nominally 15-minute but contains occasional 14- or 16-minute gaps due to clock drift, resample to a fixed grid before wrapping in ``TimeSeriesDataset``.
- **Outlier detection**: extreme load spikes (e.g., from meter faults) can distort model training. A simple IQR-based filter on the target column before training is often sufficient.

.. code-block:: python

    # Resample to a fixed 15-minute grid, forward-filling short gaps
    df = df.resample("15min").mean().ffill(limit=2)

    # Remove obvious outliers in the target column
    q_low  = df["load"].quantile(0.01)
    q_high = df["load"].quantile(0.99)
    df.loc[(df["load"] < q_low) | (df["load"] > q_high), "load"] = float("nan")

These steps belong in your data ingestion layer, before constructing a ``TimeSeriesDataset``. Once data enters OpenSTEF's pipeline, the library assumes it is structurally sound.

----

For guidance on running these patterns in production — scheduling, containerisation, and monitoring — see :doc:`deployment`. For worked examples that combine data integration with model training and evaluation, see :doc:`use_cases`.