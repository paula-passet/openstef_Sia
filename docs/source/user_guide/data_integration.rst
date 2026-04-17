Data Integration
================

OpenSTEF works with plain ``pandas`` DataFrames wrapped in typed dataset classes.
This page explains how to bring data in from common storage systems, assemble it
into the structures OpenSTEF expects, validate it before training or inference,
and write forecasts back out. For how those datasets are used inside a training
run, see :doc:`use_cases`; for running pipelines in production, see
:doc:`deployment`.

.. note:: [DIAGRAM: Data flow from external sources (S3, Databricks, InfluxDB, PostgreSQL) through OpenSTEF dataset classes (TimeSeriesDataset, VersionedTimeSeriesDataset) into the forecasting pipeline, and forecast outputs written back to storage]

Dataset Fundamentals
--------------------

OpenSTEF centres on two dataset types from ``openstef_core.datasets``:

- ``TimeSeriesDataset`` — a single, flat DataFrame with a ``DatetimeIndex``.
  Every row is one timestamp; every column is a feature or the target.
- ``VersionedTimeSeriesDataset`` — a collection of ``TimeSeriesDataset`` parts
  that each carry an ``available_at`` timestamp. This models the reality that
  weather forecasts, market prices, and meter readings arrive at different times
  and with different latencies.

Both classes enforce a ``sample_interval`` and validate column types on
construction, so data problems surface early rather than inside the model.

Reading Data
------------

Parquet Files (S3, Azure Blob, local)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset.read_parquet`` accepts any path that ``pandas``
understands, including ``s3://`` and ``abfs://`` URIs when the appropriate
``fsspec`` storage backend is installed.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Local or cloud path — same API
    load_ds = VersionedTimeSeriesDataset.read_parquet("s3://my-bucket/load/site_42.parquet")
    weather_ds = VersionedTimeSeriesDataset.read_parquet("s3://my-bucket/weather/site_42.parquet")
    epex_ds = VersionedTimeSeriesDataset.read_parquet("s3://my-bucket/market/epex.parquet")

    # Combine with a left join so all load timestamps are preserved
    dataset = VersionedTimeSeriesDataset.concat(
        [load_ds, weather_ds, epex_ds],
        mode="left",
    ).select_version()

    print(dataset.data.shape)
    print(dataset.data.index.min(), "→", dataset.data.index.max())

``select_version()`` materialises the lazy versioned dataset into a concrete
``TimeSeriesDataset`` by resolving each feature to the value that was actually
available at the time of the corresponding load observation. This is important
for backtesting: it prevents future information from leaking into training data.

The ``mode`` argument mirrors a SQL join:

- ``"left"`` — keep every timestamp from the first dataset; fill gaps in
  features with ``NaN``.
- ``"inner"`` — keep only timestamps present in all datasets.
- ``"outer"`` — keep every timestamp from any dataset.

PostgreSQL
^^^^^^^^^^

There is no built-in PostgreSQL connector; load data with ``psycopg2`` or
``SQLAlchemy`` and wrap the result in a ``TimeSeriesDataset``.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    load_df = pd.read_sql(
        """
        SELECT measured_at AS timestamp, load_mw
        FROM meter_readings
        WHERE connection_id = 42
          AND measured_at >= NOW() - INTERVAL '90 days'
        ORDER BY measured_at
        """,
        engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )

    weather_df = pd.read_sql(
        """
        SELECT valid_at AS timestamp, temperature, wind_speed, available_at
        FROM weather_forecasts
        WHERE site_id = 42
        ORDER BY valid_at, available_at
        """,
        engine,
        index_col="timestamp",
        parse_dates=["timestamp", "available_at"],
    )

    load_ds = TimeSeriesDataset(load_df, sample_interval=timedelta(minutes=15))
    weather_ds = TimeSeriesDataset(
        weather_df,
        sample_interval=timedelta(minutes=15),
        available_at_column="available_at",
    )

    dataset = VersionedTimeSeriesDataset([load_ds, weather_ds]).select_version()

InfluxDB
^^^^^^^^

Query InfluxDB with the official ``influxdb-client`` library, pivot the result
into a wide DataFrame, then wrap it as usual.

.. code-block:: python

    from datetime import timedelta, timezone, datetime
    import pandas as pd
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="my-org")
    query_api = client.query_api()

    tables = query_api.query_data_frame(
        """
        from(bucket: "energy")
          |> range(start: -90d)
          |> filter(fn: (r) => r._measurement == "meter" and r.site == "42")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
        """
    )

    df = tables.set_index("_time").rename_axis("timestamp")[["load_mw", "temperature"]]
    df.index = df.index.tz_convert(timezone.utc)

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^

From a Databricks notebook, use the ``spark`` session to read a Delta table and
convert to pandas before handing off to OpenSTEF.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    spark_df = spark.read.format("delta").load("/mnt/energy/load_versioned")
    df = (
        spark_df
        .filter("connection_id = 42")
        .orderBy("timestamp")
        .toPandas()
        .set_index("timestamp")
    )
    df.index = df.index.tz_localize("UTC")

    dataset = VersionedTimeSeriesDataset.from_dataframe(df, timedelta(minutes=15))

``from_dataframe`` is a convenience constructor that wraps a plain DataFrame in
a ``VersionedTimeSeriesDataset`` without requiring you to build ``TimeSeriesDataset``
parts manually.

Custom Sources
^^^^^^^^^^^^^^

Any source that can produce a ``pandas`` DataFrame with a timezone-aware
``DatetimeIndex`` works. The minimal contract is:

1. Index is a ``DatetimeIndex`` with a consistent frequency matching
   ``sample_interval``.
2. The target column (typically ``"load"``) contains numeric values.
3. If the data is versioned, an ``available_at`` column holds the timestamp at
   which each row became known.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    # Replace this with your actual data retrieval logic
    df = pd.DataFrame(
        {"load": [100.0, 102.5, 98.3], "temperature": [15.0, 14.8, 14.5]},
        index=pd.date_range("2024-01-01", periods=3, freq="15min", tz="UTC"),
    )
    df.index.name = "timestamp"

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Validating Data
---------------

OpenSTEF provides three validation transforms in
``openstef_models.transforms.validation`` that can be applied before training or
inference:

- ``CompletenessChecker`` — flags or raises when the fraction of non-null values
  falls below a threshold.
- ``FlatlineChecker`` — detects runs of identical consecutive values, which
  often indicate a stuck sensor.
- ``InputConsistencyChecker`` — verifies that inference data has the same
  columns and dtypes as the training data.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    completeness = CompletenessChecker(min_completeness=0.95)
    flatline = FlatlineChecker(max_flatline_length=4)

    # Apply sequentially; each raises or logs a warning on failure
    completeness.check(dataset)
    flatline.check(dataset)

Column-level validation uses ``validate_required_columns`` from
``openstef_core.datasets.validation``:

.. code-block:: python

    from openstef_core.datasets.validation import validate_required_columns

    validate_required_columns(
        df,
        required_columns=["load", "temperature", "wind_speed"],
    )
    # Raises MissingColumnsError listing any absent columns

.. note::

   ``MissingColumnsError`` and ``TimeSeriesValidationError`` are both importable
   from ``openstef_core.exceptions``. Catch them explicitly in production code
   so that data quality failures produce actionable log messages rather than
   generic tracebacks.

Handling Missing Data
---------------------

OpenSTEF does not silently impute missing values before model training; gaps
remain as ``NaN`` and tree-based models handle them natively. For models that
cannot tolerate missing inputs (linear models, neural networks), apply
interpolation before constructing the dataset:

.. code-block:: python

    import pandas as pd

    # Forward-fill short gaps (e.g. one or two missing intervals)
    df["temperature"] = df["temperature"].ffill(limit=2)

    # Linear interpolation for longer gaps in smooth signals
    df["wind_speed"] = df["wind_speed"].interpolate(method="time", limit=4)

    # Drop rows where the target itself is missing
    df = df.dropna(subset=["load"])

Keep imputation conservative. Filling large gaps with synthetic values can
degrade model quality more than leaving them as ``NaN``.

When using ``VersionedTimeSeriesDataset.concat`` with ``mode="left"``, features
that have no observation for a given timestamp are automatically ``NaN`` in the
materialised dataset. This is the expected behaviour — it reflects genuine data
unavailability at that point in time.

Writing Forecasts Back to Storage
----------------------------------

The forecasting pipeline returns a ``ForecastDataset``. Its ``.data`` attribute
is a standard ``pandas`` DataFrame that you can write to any destination.

.. code-block:: python

    from openstef_core.datasets import ForecastDataset

    # forecast_ds is returned by your workflow's predict() call
    forecast_df = forecast_ds.data  # plain DataFrame

    # --- Parquet on S3 ---
    forecast_df.to_parquet("s3://my-bucket/forecasts/site_42.parquet")

    # --- PostgreSQL ---
    forecast_df.to_sql(
        "forecasts",
        engine,
        if_exists="append",
        index=True,
        index_label="timestamp",
    )

    # --- InfluxDB ---
    from influxdb_client import WriteOptions
    write_api = client.write_api(write_options=WriteOptions(batch_size=500))
    write_api.write(
        bucket="energy",
        record=forecast_df,
        data_frame_measurement_name="forecast",
        data_frame_tag_columns=["horizon"],
    )

.. note:: [VISUALIZATION: Example forecast DataFrame showing timestamp index, quantile columns (q05, q50, q95), and horizon column]

For MLflow-based experiment tracking and model artefact storage, see the
``MLflowStorageCallback`` in
``openstef_models.integrations.mlflow.mlflow_storage_callback``. It logs
training data, metrics, and feature-importance plots automatically when attached
to a ``ForecastingModel``.

Assembling a Full Data Pipeline
--------------------------------

The following example combines the patterns above into a realistic end-to-end
pipeline that reads from two sources, validates, trains, and writes results back.

.. code-block:: python

    import logging
    from datetime import timedelta
    from pathlib import Path

    import pandas as pd
    from sqlalchemy import create_engine

    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
    from openstef_core.datasets.validation import validate_required_columns
    from openstef_core.exceptions import MissingColumnsError
    from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker

    log = logging.getLogger(__name__)

    SAMPLE_INTERVAL = timedelta(minutes=15)
    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")


    def load_training_data(connection_id: int) -> VersionedTimeSeriesDataset:
        load_df = pd.read_sql(
            "SELECT measured_at AS timestamp, load_mw AS load "
            "FROM meter_readings WHERE connection_id = %(cid)s "
            "AND measured_at >= NOW() - INTERVAL '90 days' ORDER BY measured_at",
            engine,
            index_col="timestamp",
            parse_dates=["timestamp"],
            params={"cid": connection_id},
        )
        weather_df = pd.read_sql(
            "SELECT valid_at AS timestamp, temperature, wind_speed, available_at "
            "FROM weather_forecasts WHERE site_id = %(cid)s ORDER BY valid_at",
            engine,
            index_col="timestamp",
            parse_dates=["timestamp", "available_at"],
            params={"cid": connection_id},
        )

        try:
            validate_required_columns(load_df, ["load"])
            validate_required_columns(weather_df, ["temperature", "wind_speed", "available_at"])
        except MissingColumnsError as exc:
            log.error("Data validation failed for connection %s: %s", connection_id, exc)
            raise

        load_ds = TimeSeriesDataset(load_df, sample_interval=SAMPLE_INTERVAL)
        weather_ds = TimeSeriesDataset(
            weather_df,
            sample_interval=SAMPLE_INTERVAL,
            available_at_column="available_at",
        )

        dataset = VersionedTimeSeriesDataset.concat(
            [load_ds, weather_ds], mode="left"
        ).select_version()

        CompletenessChecker(min_completeness=0.90).check(dataset)
        FlatlineChecker(max_flatline_length=6).check(dataset)

        return dataset


    def write_forecasts(forecast_df: pd.DataFrame, connection_id: int) -> None:
        forecast_df["connection_id"] = connection_id
        forecast_df.to_sql("forecasts", engine, if_exists="append", index=True)
        log.info("Wrote %d forecast rows for connection %s", len(forecast_df), connection_id)

.. note::

   For scheduling and orchestrating pipelines like this in production, see
   :doc:`deployment`. For concrete use-case walkthroughs (congestion
   forecasting, load disaggregation), see :doc:`use_cases`.