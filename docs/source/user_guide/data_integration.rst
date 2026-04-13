Data Integration
================

OpenSTEF is a library that sits in the middle of your data pipeline — it consumes time series data from wherever you store it and produces forecasts that you write back to wherever they need to go. This page covers the practical patterns for wiring OpenSTEF into real-world storage systems: reading training and prediction data from S3, Databricks, InfluxDB, and PostgreSQL; writing forecast results back to storage; handling missing or incomplete data; and validating inputs before they reach the model.

For production deployment patterns (scheduling, containerisation, orchestration), see :doc:`deployment`. For worked end-to-end use cases, see :doc:`use_cases`.

.. note:: [DIAGRAM: Data flow — external sources → DataFrame → ForecastInputDataset → OpenSTEF workflow → ForecastDataset → external sinks]


The Central Contract: ``ForecastInputDataset``
----------------------------------------------

Regardless of where your data lives, OpenSTEF always works with a ``ForecastInputDataset`` (or the lower-level ``TimeSeriesDataset``). The contract is simple: produce a ``pandas.DataFrame`` with a ``DatetimeIndex``, the required columns for your use case, and hand it to the dataset constructor. Everything else — feature engineering, model training, inference — happens inside the library.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Any DataFrame with a DatetimeIndex and the right columns works
    df = pd.DataFrame(
        {"load": load_series, "weather_temp": temp_series},
        index=pd.date_range("2024-01-01", periods=2016, freq="15min"),
    )

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
    )

The ``sample_interval`` parameter tells OpenSTEF the expected cadence of your data. Mismatches between the declared interval and the actual index frequency surface as ``TimeSeriesValidationError`` early, before any expensive computation begins.


Reading Data from External Sources
-----------------------------------

The examples below show how to fetch data from common storage backends and convert it into a ``ForecastInputDataset``. The integration code is plain Python — OpenSTEF imposes no framework or connector requirements.

**Amazon S3 / object storage (Parquet)**

Parquet on S3 is a common pattern for storing historical time series. ``TimeSeriesDataset`` has a built-in ``read_parquet`` class method that handles the round-trip correctly, including restoring the ``horizon`` and ``available_at`` columns:

.. code-block:: python

    import s3fs
    from openstef_core.datasets import TimeSeriesDataset

    fs = s3fs.S3FileSystem()

    # Read directly from S3 using fsspec-compatible path
    with fs.open("s3://my-bucket/openstef/training_data.parquet") as f:
        dataset = TimeSeriesDataset.read_parquet(f, sample_interval=timedelta(minutes=15))

If you are assembling data from multiple Parquet partitions (e.g., a Hive-partitioned layout), read each partition into a DataFrame, concatenate, and then construct the dataset:

.. code-block:: python

    import pandas as pd
    import s3fs
    from openstef_core.datasets.validated_datasets import ForecastInputDataset
    from datetime import timedelta

    fs = s3fs.S3FileSystem()
    partitions = fs.glob("s3://my-bucket/openstef/load/year=2024/month=*/data.parquet")

    frames = [pd.read_parquet(fs.open(p)) for p in partitions]
    df = pd.concat(frames).sort_index()

    dataset = ForecastInputDataset(data=df, sample_interval=timedelta(minutes=15))

**Databricks / Delta Lake**

When running inside a Databricks notebook or job, use a Spark DataFrame and convert to pandas before constructing the dataset:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    spark_df = spark.table("energy_data.load_measurements")

    df = (
        spark_df
        .filter("measurement_date >= '2023-01-01'")
        .toPandas()
        .set_index("timestamp")
        .sort_index()
    )
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = ForecastInputDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   When converting from Spark, always call ``sort_index()`` after ``toPandas()``. Spark does not guarantee row order, and an unsorted ``DatetimeIndex`` will cause validation errors downstream.

**InfluxDB**

InfluxDB is popular for real-time measurement storage. Query via the ``influxdb-client`` package and pivot the result into a wide DataFrame:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="...", org="my-org")
    query_api = client.query_api()

    query = """
    from(bucket: "energy")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "grid_load")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(query)
    df = df.set_index("_time").sort_index()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[["load", "weather_temp"]]  # keep only the columns you need

    dataset = ForecastInputDataset(data=df, sample_interval=timedelta(minutes=15))

**PostgreSQL**

For relational databases, ``pandas.read_sql`` is the most straightforward path:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    df = pd.read_sql(
        """
        SELECT timestamp, load, weather_temp
        FROM measurements
        WHERE timestamp >= NOW() - INTERVAL '60 days'
        ORDER BY timestamp
        """,
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )
    df.index = df.index.tz_localize("UTC")

    dataset = ForecastInputDataset(data=df, sample_interval=timedelta(minutes=15))


Handling Missing Data
----------------------

Real-world time series almost always contain gaps. OpenSTEF raises ``InsufficientlyCompleteError`` when too much target data is missing to train a model, and it raises ``TimeSeriesValidationError`` for structural problems such as duplicate timestamps or wrong frequency. You should handle both before passing data to the workflow.

The recommended approach is to validate and clean your DataFrame *before* constructing the dataset, so problems are caught at the integration boundary rather than deep inside the library:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset
    from openstef_core.exceptions import InsufficientlyCompleteError

    def prepare_dataset(df: pd.DataFrame) -> ForecastInputDataset:
        # 1. Remove duplicate timestamps (keep last reading)
        df = df[~df.index.duplicated(keep="last")]

        # 2. Enforce a regular frequency, introducing NaN for missing slots
        full_index = pd.date_range(df.index.min(), df.index.max(), freq="15min", tz="UTC")
        df = df.reindex(full_index)

        # 3. Interpolate short gaps in feature columns (not the target)
        feature_cols = [c for c in df.columns if c != "load"]
        df[feature_cols] = df[feature_cols].interpolate(method="time", limit=4)

        # 4. Guard against too many missing target values
        missing_frac = df["load"].isna().mean()
        if missing_frac > 0.10:
            raise InsufficientlyCompleteError(
                f"Target column 'load' is {missing_frac:.1%} NaN — cannot train reliably."
            )

        return ForecastInputDataset(data=df, sample_interval=timedelta(minutes=15))

.. warning::

   Do not interpolate or forward-fill the target column (``load``) before training. Synthetic target values will bias the model. Interpolation is appropriate only for exogenous features such as weather or calendar variables.

OpenSTEF's own training pipeline will drop rows where the target is ``NaN`` internally, but it cannot know whether the gap is acceptable for your use case — that judgement belongs in your integration layer.


Data Validation
----------------

``openstef_core.datasets.validation`` provides utilities you can call directly to validate DataFrames before they enter the pipeline:

.. code-block:: python

    from openstef_core.datasets.validation import validate_required_columns
    from openstef_core.exceptions import MissingColumnsError, InvalidColumnTypeError

    REQUIRED = ["load", "weather_temp", "weather_irradiance"]

    try:
        validate_required_columns(df, required_columns=REQUIRED)
    except MissingColumnsError as exc:
        print(f"Schema mismatch: {exc}")
        # exc.missing_columns lists exactly what is absent
        # exc.columns lists what was actually present

For type-level validation, check column dtypes explicitly before constructing the dataset:

.. code-block:: python

    from openstef_core.exceptions import InvalidColumnTypeError

    def assert_numeric(df: pd.DataFrame, columns: list[str]) -> None:
        for col in columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                raise InvalidColumnTypeError(
                    column=col,
                    expected_type="numeric",
                    actual_type=str(df[col].dtype),
                )

    assert_numeric(df, ["load", "weather_temp"])


Writing Forecasts Back to Storage
-----------------------------------

After the workflow runs, the result is a ``ForecastDataset``. Its ``.data`` attribute is a standard ``pandas.DataFrame``, so writing it back to any storage system is straightforward.

**Parquet (local or cloud)**

``ForecastDataset`` exposes a ``to_parquet`` method that preserves all metadata attributes needed to reload the dataset later:

.. code-block:: python

    # Write locally or to any fsspec-compatible path
    forecast_result.to_parquet(path="output/forecast_2024_01_01.parquet")

    # Write to S3
    import s3fs
    fs = s3fs.S3FileSystem()
    with fs.open("s3://my-bucket/forecasts/2024-01-01.parquet", "wb") as f:
        forecast_result.to_parquet(path=f)

**PostgreSQL**

.. code-block:: python

    from sqlalchemy import create_engine

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    df_out = forecast_result.data.reset_index()  # move DatetimeIndex to column
    df_out["created_at"] = pd.Timestamp.utcnow()

    df_out.to_sql(
        "forecasts",
        con=engine,
        if_exists="append",
        index=False,
        method="multi",
    )

**InfluxDB**

.. code-block:: python

    from influxdb_client import InfluxDBClient, WriteOptions
    from influxdb_client.client.write_api import SYNCHRONOUS

    client = InfluxDBClient(url="http://influxdb:8086", token="...", org="my-org")
    write_api = client.write_api(write_options=SYNCHRONOUS)

    df_out = forecast_result.data[["load"]].copy()
    df_out.index.name = "timestamp"

    write_api.write(
        bucket="forecasts",
        record=df_out,
        data_frame_measurement_name="grid_load_forecast",
        data_frame_tag_columns=[],
    )


Using the ``DataSaveCallback`` for Debugging
---------------------------------------------

During development it is useful to persist intermediate datasets — training inputs, prepared features, and forecast outputs — without modifying your main pipeline code. OpenSTEF provides ``DataSaveCallback`` for exactly this purpose:

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

    # Pass the callback when running the workflow
    workflow.predict(dataset, callbacks=[debug_callback])

After the run, ``/tmp/openstef_debug/`` will contain Parquet files for each stage, named by the workflow's ``run_name``. These files can be loaded back with ``TimeSeriesDataset.read_parquet`` for inspection or backtesting analysis.


Building a Complete Data Pipeline
-----------------------------------

The following example assembles the patterns above into a minimal but realistic pipeline that reads from PostgreSQL, runs a forecast, and writes results back:

.. code-block:: python

    from datetime import timedelta
    from pathlib import Path

    import pandas as pd
    from sqlalchemy import create_engine

    from openstef_core.datasets.validated_datasets import ForecastInputDataset
    from openstef_core.datasets.validation import validate_required_columns
    from openstef_core.exceptions import MissingColumnsError, InsufficientlyCompleteError
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

    REQUIRED_COLUMNS = ["load", "weather_temp"]
    SAMPLE_INTERVAL = timedelta(minutes=15)

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    # --- Read ---
    df = pd.read_sql(
        "SELECT timestamp, load, weather_temp FROM measurements ORDER BY timestamp",
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )
    df.index = df.index.tz_localize("UTC")

    # --- Validate ---
    validate_required_columns(df, required_columns=REQUIRED_COLUMNS)

    df = df[~df.index.duplicated(keep="last")]
    full_index = pd.date_range(df.index.min(), df.index.max(), freq="15min", tz="UTC")
    df = df.reindex(full_index)
    df[["weather_temp"]] = df[["weather_temp"]].interpolate(method="time", limit=4)

    if df["load"].isna().mean() > 0.10:
        raise InsufficientlyCompleteError("Too many missing load values.")

    dataset = ForecastInputDataset(data=df, sample_interval=SAMPLE_INTERVAL)

    # --- Forecast ---
    workflow = CustomForecastingWorkflow.load(Path("models/grid_point_42"))
    forecast = workflow.predict(dataset)

    # --- Write ---
    df_out = forecast.data.reset_index()
    df_out["created_at"] = pd.Timestamp.utcnow()
    df_out.to_sql("forecasts", con=engine, if_exists="append", index=False)

This pipeline is intentionally thin. OpenSTEF handles the modelling; your integration layer handles I/O and validation at the boundaries.

.. note::

   For scheduling and retry logic around pipelines like this, see :doc:`deployment`. For logging within the pipeline, see :doc:`logging`.