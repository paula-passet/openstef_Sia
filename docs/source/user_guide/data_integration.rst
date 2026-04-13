Data Integration
================

OpenSTEF is a library, not an application — it does not prescribe where your data lives or how it moves. Instead, it provides a set of abstractions (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, validation transforms) that you populate from whatever storage system your organisation uses. This page explains how to feed data into those abstractions from common sources, how to write forecasts back to storage, and how to handle the data-quality problems that arise in real pipelines.

For production scheduling and orchestration of these pipelines, see :doc:`deployment`. For worked end-to-end examples that combine data integration with model training, see :doc:`use_cases`.

.. note:: [DIAGRAM: Data flow — external sources → TimeSeriesDataset → OpenSTEF pipeline → VersionedTimeSeriesDataset → external sink]

Core Data Abstractions
----------------------

Before connecting any source, it helps to understand the two dataset types you will be constructing:

- ``TimeSeriesDataset`` — a thin wrapper around a ``pandas.DataFrame`` with a known ``sample_interval``. It carries a datetime index, one or more feature columns, and optional metadata in ``attrs``. This is the type consumed by transforms and models.
- ``VersionedTimeSeriesDataset`` — extends the above with a notion of *when* each observation became available (``available_at``). This is essential for backtesting and for combining data from sources that publish revisions (e.g. weather forecasts).

Both types support Parquet round-trips out of the box:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Construct from a pandas DataFrame you have loaded yourself
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

    # Persist and reload
    dataset.to_parquet("measurements.parquet")
    reloaded = TimeSeriesDataset.read_parquet(
        "measurements.parquet",
        sample_interval=timedelta(minutes=15),
    )

The ``read_parquet`` / ``to_parquet`` methods are the recommended intermediate format when bridging heterogeneous sources, because Parquet preserves the ``attrs`` metadata that carries ``sample_interval`` and versioning information.

Reading from External Sources
------------------------------

The pattern is always the same: query your source, assemble a ``pandas.DataFrame`` with a ``DatetimeIndex``, then wrap it in a ``TimeSeriesDataset``. The sections below show this for several common backends.

**Amazon S3 (Parquet files)**

If your organisation stores time-series snapshots as Parquet files on S3, the simplest approach is to use ``pandas`` with the ``s3fs`` engine and then hand the result to OpenSTEF:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    df = pd.read_parquet(
        "s3://my-bucket/energy/measurements/substation_42.parquet",
        storage_options={"anon": False},  # uses your AWS credentials
    )
    df.index = pd.to_datetime(df.index, utc=True)

    measurements = TimeSeriesDataset(
        data=df[["load_mw"]],
        sample_interval=timedelta(minutes=15),
    )

For versioned weather forecasts stored as partitioned datasets on S3, wrap the result in ``VersionedTimeSeriesDataset`` instead, ensuring the ``available_at`` column is present in the DataFrame before construction.

**Databricks / Delta Lake**

When running inside a Databricks notebook or job, you can read a Delta table via the Spark session and convert to pandas before wrapping:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    spark_df = spark.table("energy.measurements.substation_42")
    df = (
        spark_df
        .filter("timestamp >= '2024-01-01'")
        .toPandas()
        .set_index("timestamp")
    )
    df.index = df.index.tz_localize("UTC")

    measurements = TimeSeriesDataset(
        data=df[["load_mw"]],
        sample_interval=timedelta(minutes=15),
    )

.. note::

   For large tables, push date-range filters into Spark before calling ``toPandas()`` to avoid pulling the full table into driver memory.

**InfluxDB**

InfluxDB returns results as a ``pandas.DataFrame`` when using the ``influxdb-client`` library with the ``query_data_frame`` method:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="...", org="my-org")
    query_api = client.query_api()

    df = query_api.query_data_frame(
        'from(bucket:"energy") '
        '|> range(start: -7d) '
        '|> filter(fn: (r) => r["_measurement"] == "load_mw")'
    )
    df = df.set_index("_time")[["_value"]].rename(columns={"_value": "load_mw"})
    df.index = pd.to_datetime(df.index, utc=True)

    measurements = TimeSeriesDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
    )

**PostgreSQL / TimescaleDB**

For relational databases, use ``pandas.read_sql`` with a SQLAlchemy engine:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    df = pd.read_sql(
        sql="""
            SELECT timestamp, load_mw
            FROM measurements
            WHERE substation_id = 42
              AND timestamp >= NOW() - INTERVAL '7 days'
            ORDER BY timestamp
        """,
        con=engine,
        index_col="timestamp",
        parse_dates={"timestamp": {"utc": True}},
    )

    measurements = TimeSeriesDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
    )

Combining Multiple Sources
--------------------------

A realistic pipeline typically merges measurements from one source with weather predictors from another. ``VersionedTimeSeriesDataset.concat`` handles this alignment:

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Both datasets must share the same sample_interval
    combined = VersionedTimeSeriesDataset.concat(
        datasets=[measurements_versioned, weather_versioned],
        mode="inner",  # keep only timestamps present in all datasets
    )

Use ``mode="inner"`` when you need strict temporal alignment (e.g. for training). Use ``mode="outer"`` when you want to preserve all timestamps and accept NaNs for gaps — but then apply the validation transforms described below before passing data to a model.

Data Validation
---------------

OpenSTEF ships validation transforms in ``openstef_models.transforms.validation`` that should be applied before any model sees the data. They raise typed exceptions rather than silently passing bad data through.

**Completeness checking**

``CompletenessChecker`` computes the ratio of non-missing values and raises ``InsufficientlyCompleteError`` if the dataset falls below the configured threshold:

.. code-block:: python

    from datetime import timedelta
    import numpy as np
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    df = pd.DataFrame(
        {"load_mw": [100.0, np.nan, 102.0, np.nan]},
        index=pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC"),
    )
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

    checker = CompletenessChecker()
    try:
        validated = checker.transform(dataset)
    except Exception as exc:
        # InsufficientlyCompleteError: The dataset is not sufficiently complete.
        print(f"Data quality gate failed: {exc}")

You can restrict the check to specific columns and adjust thresholds via ``CompletenessChecker`` configuration fields.

**Flatline detection**

``FlatlineChecker`` detects when the most recent measurements repeat the same value — a common symptom of a stuck sensor or a failed data feed:

.. code-block:: python

    from openstef_models.transforms.validation import FlatlineChecker

    flatline_checker = FlatlineChecker()
    validated = flatline_checker.transform(dataset)

**Input consistency**

``InputConsistencyChecker`` is a stateful transform: you ``fit`` it on a reference dataset (e.g. the training window) and then call ``transform`` on new inference batches to confirm that the feature schema has not drifted:

.. code-block:: python

    from openstef_models.transforms.validation import InputConsistencyChecker

    consistency_checker = InputConsistencyChecker()
    consistency_checker.fit(training_dataset)

    # Later, at inference time:
    consistency_checker.transform(inference_dataset)

Handling Missing Data
---------------------

Validation transforms tell you *whether* data is acceptable; they do not fill gaps. Gap-filling strategy depends on the nature of the gap:

- **Short gaps (1–3 intervals):** Forward-fill or linear interpolation via ``TimeSeriesDataset.pipe_pandas``:

  .. code-block:: python

      filled = dataset.pipe_pandas(
          lambda df: df.interpolate(method="time", limit=3)
      )

- **Longer gaps:** Treat as a data availability problem rather than an imputation problem. Log the gap, skip the affected forecast window, and alert the upstream data team. OpenSTEF's ``FlatlineChecker`` and ``CompletenessChecker`` are the right place to catch these before they silently degrade model accuracy.

- **Columns that are entirely missing:** The ``DropEmptyColumns`` transform (in ``openstef_models.transforms``) removes feature columns that contain only ``NaN`` or a configured sentinel value, and logs a warning so the drop is auditable.

.. warning::

   Avoid imputing large gaps with statistical methods (e.g. seasonal means) without domain knowledge. Energy load data has strong day-of-week and holiday effects; naive imputation can introduce systematic bias into model training.

Writing Forecasts Back to Storage
----------------------------------

After running the OpenSTEF pipeline you will have a ``TimeSeriesDataset`` (or a plain ``pandas.DataFrame``) containing forecast values. Writing it back follows the same pattern as reading — construct the output DataFrame and use your storage client directly.

**Writing to Parquet on S3:**

.. code-block:: python

    forecast_dataset.to_parquet("s3://my-bucket/forecasts/substation_42.parquet")

**Writing to PostgreSQL:**

.. code-block:: python

    forecast_df = forecast_dataset.data.reset_index()
    forecast_df["substation_id"] = 42
    forecast_df["created_at"] = pd.Timestamp.utcnow()

    forecast_df.to_sql(
        name="forecasts",
        con=engine,
        if_exists="append",
        index=False,
    )

**Writing to InfluxDB:**

.. code-block:: python

    from influxdb_client import WriteOptions

    write_api = client.write_api(write_options=WriteOptions(batch_size=500))
    write_api.write(
        bucket="energy",
        record=forecast_df,
        data_frame_measurement_name="forecast_load_mw",
        data_frame_tag_columns=["substation_id"],
    )

Building a Reusable Data Manager
----------------------------------

For production use, encapsulate source-specific logic behind a class that returns ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` objects. This keeps OpenSTEF pipeline code independent of storage details and makes it straightforward to swap backends (e.g. from local Parquet files in development to S3 in production):

.. code-block:: python

    from pathlib import Path
    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset


    class SubstationDataManager:
        """Thin data-access layer that isolates storage details from pipeline logic."""

        def __init__(self, engine, sample_interval: timedelta = timedelta(minutes=15)):
            self.engine = engine
            self.sample_interval = sample_interval

        def get_measurements(self, substation_id: int, lookback_days: int = 14) -> TimeSeriesDataset:
            df = pd.read_sql(
                sql=f"""
                    SELECT timestamp, load_mw
                    FROM measurements
                    WHERE substation_id = {substation_id}
                      AND timestamp >= NOW() - INTERVAL '{lookback_days} days'
                    ORDER BY timestamp
                """,
                con=self.engine,
                index_col="timestamp",
                parse_dates={"timestamp": {"utc": True}},
            )
            return TimeSeriesDataset(data=df, sample_interval=self.sample_interval)

        def write_forecast(self, substation_id: int, forecast: TimeSeriesDataset) -> None:
            out = forecast.data.reset_index()
            out["substation_id"] = substation_id
            out["created_at"] = pd.Timestamp.utcnow()
            out.to_sql("forecasts", con=self.engine, if_exists="append", index=False)

This pattern mirrors the ``AbstractDataManager`` approach used in the OpenSTEF reference implementations, where methods like ``get_measurements_for_target``, ``get_weather_for_target``, and ``get_predictors_for_target`` each return a typed dataset object ready for the pipeline.

.. note::

   The ``openstef_models`` package includes a file-based ``DataManager`` that reads measurements, weather, profiles, and prices from a directory of Parquet files. If your data can be exported to Parquet, this is the fastest way to get a working pipeline without writing any connector code.

Related Pages
-------------

- :doc:`use_cases` — end-to-end examples that combine data integration with training and inference
- :doc:`deployment` — scheduling and containerising data pipelines in production
- :doc:`logging` — configuring structured logging for data pipeline observability