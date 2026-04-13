Data Integration
================

OpenSTEF is a library, not a managed platform — it does not ship with built-in connectors for every data store you might use. Instead, it defines clear data structures (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``) that you populate from whatever source fits your infrastructure. This page explains how to feed data into OpenSTEF from common storage systems, how to write forecasts back to storage, and how to handle the practical problems of missing values and data quality that arise in real energy-data pipelines.

For deployment patterns that wrap these integrations in a production service, see :doc:`deployment`. For concrete end-to-end forecasting examples, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

Understanding OpenSTEF's Data Model
------------------------------------

Before connecting any source, it helps to understand what OpenSTEF actually expects. The library's core data container is ``TimeSeriesDataset``, a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex`` and an explicit ``sample_interval``. For multi-version or point-in-time-correct data (i.e., data that was available *at* a given moment in the past), the library uses ``VersionedTimeSeriesDataset``, which stores multiple time-stamped snapshots of the same series.

Your job as an integrator is straightforward: pull data from your store, shape it into one of these containers, and pass it to the pipeline. The library validates structure and raises ``TimeSeriesValidationError`` if something is wrong, so errors surface early rather than silently corrupting a forecast.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Minimal construction from a DataFrame you already have
    df = pd.DataFrame(
        {"load_mw": [100.0, 102.5, 98.3, 101.1]},
        index=pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC"),
    )

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Reading from Local and Cloud Parquet Files
-------------------------------------------

Parquet is the native persistence format in OpenSTEF. Both ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` expose ``read_parquet`` / ``to_parquet`` class methods that round-trip all metadata (sample interval, version columns, horizon columns) through the file's ``attrs`` dictionary, so you never need to reconstruct that metadata manually.

.. code-block:: python

    from pathlib import Path
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # Load a plain time series
    measurements = TimeSeriesDataset.read_parquet(
        path=Path("data/measurements/substation_a.parquet"),
        sample_interval=timedelta(minutes=15),
    )

    # Load a versioned (point-in-time) dataset
    weather = VersionedTimeSeriesDataset.read_parquet(
        path=Path("data/weather/knmi_forecast.parquet"),
    )

Because ``read_parquet`` ultimately calls ``pandas.read_parquet``, any filesystem that pandas supports works transparently — including S3, Azure Blob Storage, and GCS — by passing a URI string or an ``fsspec``-compatible path object.

**Reading from S3**

.. code-block:: python

    import s3fs
    from openstef_core.datasets import VersionedTimeSeriesDataset

    fs = s3fs.S3FileSystem(anon=False)  # uses your AWS credentials

    weather = VersionedTimeSeriesDataset.read_parquet(
        path="s3://my-energy-bucket/weather/knmi_2024.parquet",
    )

    measurements = TimeSeriesDataset.read_parquet(
        path="s3://my-energy-bucket/measurements/substation_a.parquet",
        sample_interval=timedelta(minutes=15),
    )

**Reading from Databricks / Delta Lake**

When your data lives in a Delta table on Databricks, the cleanest approach is to read it into a pandas DataFrame via the Databricks ``dbutils`` or the ``delta-spark`` connector, then wrap the result:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    # Inside a Databricks notebook or job
    spark_df = spark.table("energy_data.measurements_substation_a")
    df = (
        spark_df
        .filter("timestamp >= '2023-01-01'")
        .toPandas()
        .set_index("timestamp")
        .sort_index()
    )
    df.index = pd.DatetimeIndex(df.index, tz="UTC")

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Reading from InfluxDB
----------------------

InfluxDB is a common choice for storing high-frequency meter readings. Use the official ``influxdb-client`` package to query data and convert the result to a ``TimeSeriesDataset``:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta, timezone
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    INFLUX_URL = "http://localhost:8086"
    INFLUX_TOKEN = "my-token"
    INFLUX_ORG = "my-org"
    INFLUX_BUCKET = "energy"

    query = """
    from(bucket: "energy")
      |> range(start: -30d)
      |> filter(fn: (r) => r._measurement == "load" and r.substation == "A")
      |> aggregateWindow(every: 15m, fn: mean, createEmpty: true)
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        df = client.query_api().query_data_frame(query)

    df = (
        df.rename(columns={"_time": "timestamp", "load_mw": "load_mw"})
        .set_index("timestamp")
        .sort_index()
        [["load_mw"]]
    )
    df.index = df.index.tz_convert("UTC")

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   The ``aggregateWindow`` step in the Flux query is important: it ensures the
   returned series has a regular cadence and introduces explicit ``null`` values
   for missing windows, which you can then handle explicitly (see
   `Handling Missing Data`_ below).

Reading from PostgreSQL
------------------------

For relational databases, ``pandas.read_sql`` provides a direct path to a ``TimeSeriesDataset``:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine(
        "postgresql+psycopg2://user:password@db-host:5432/energy_db"
    )

    query = """
        SELECT timestamp, load_mw, temperature_c
        FROM measurements
        WHERE substation_id = 'A'
          AND timestamp >= NOW() - INTERVAL '30 days'
        ORDER BY timestamp ASC
    """

    df = pd.read_sql(query, con=engine, index_col="timestamp", parse_dates=["timestamp"])
    df.index = df.index.tz_localize("UTC")

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Building a Custom Data Source
------------------------------

If your organisation uses a bespoke data store or an API not covered above, the pattern is always the same: write a class that encapsulates the connection and returns ``TimeSeriesDataset`` objects. This keeps integration logic separate from forecasting logic and makes unit testing straightforward.

.. code-block:: python

    from datetime import timedelta
    from pathlib import Path
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset


    class MyEnergyDataSource:
        """Thin adapter between our internal API and OpenSTEF data structures."""

        def __init__(self, api_client, sample_interval: timedelta = timedelta(minutes=15)):
            self._client = api_client
            self._sample_interval = sample_interval

        def get_measurements(self, substation_id: str, start, end) -> TimeSeriesDataset:
            raw = self._client.fetch_load(substation_id, start, end)
            df = pd.DataFrame(raw).set_index("timestamp").sort_index()
            df.index = pd.DatetimeIndex(df.index, tz="UTC")
            return TimeSeriesDataset(data=df, sample_interval=self._sample_interval)

        def get_weather(self, location: str) -> VersionedTimeSeriesDataset:
            raw = self._client.fetch_weather_forecast(location)
            df = pd.DataFrame(raw).set_index("timestamp").sort_index()
            df.index = pd.DatetimeIndex(df.index, tz="UTC")
            # available_at column records when each forecast version was issued
            return VersionedTimeSeriesDataset(
                data=df,
                sample_interval=timedelta(hours=1),
                available_at_column="issued_at",
            )

The ``openstef-models`` package follows this same pattern internally: a ``LocalParquetDataSource`` class owns all path resolution and Parquet I/O, returning typed dataset objects to the pipeline. Studying that implementation is a good starting point for more complex adapters.

Combining Multiple Sources
---------------------------

Real forecasting pipelines typically merge measurements, weather forecasts, energy profiles, and price signals. ``VersionedTimeSeriesDataset.concat`` handles this with explicit alignment strategies:

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset

    # "inner" mode keeps only timestamps present in all datasets
    predictors = VersionedTimeSeriesDataset.concat(
        datasets=[weather, profiles, prices],
        mode="inner",
    )

    # Restrict to the training window
    predictors = predictors.filter_by_range(start=train_start, end=train_end)

Use ``mode="inner"`` when all predictor sources must be present for every timestamp. Use ``mode="outer"`` when some sources may have gaps and you intend to impute them downstream.

Handling Missing Data
----------------------

Energy meter data is rarely complete. Sensors go offline, communication links drop, and database writes fail. OpenSTEF's pipeline will raise ``InsufficientlyCompleteError`` if the target column contains only ``NaN`` values after preprocessing, so you need a strategy before data reaches the model.

**Detecting gaps**

.. code-block:: python

    import pandas as pd

    # Reindex to the expected regular cadence to surface implicit gaps
    expected_index = pd.date_range(
        start=dataset.data.index.min(),
        end=dataset.data.index.max(),
        freq="15min",
        tz="UTC",
    )
    reindexed = dataset.data.reindex(expected_index)
    missing_pct = reindexed.isna().mean() * 100
    print(missing_pct)

**Imputation strategies**

For short gaps (one or two missing intervals), linear interpolation is usually sufficient:

.. code-block:: python

    df_filled = dataset.data.interpolate(method="time", limit=4)

For longer outages, a seasonal fill using the same period from the previous week is more appropriate for load data:

.. code-block:: python

    # Fill using values from 7 days prior (same weekday, same time)
    lag_7d = dataset.data.shift(freq="7D")
    df_filled = dataset.data.fillna(lag_7d)

.. warning::

   Imputed values in the **target column** will be used as training labels.
   Clearly mark imputed rows (e.g., with a boolean flag column) so you can
   exclude them from model evaluation later.

Data Validation
----------------

Before passing data to the pipeline, a few lightweight checks prevent hard-to-debug errors downstream:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.datasets.validated_datasets import validate_horizons_present

    # 1. Confirm the index is timezone-aware
    assert dataset.data.index.tz is not None, "Index must be timezone-aware"

    # 2. Confirm the cadence matches the declared sample_interval
    assert dataset.frequency_matches(dataset.data.index), (
        "Data cadence does not match declared sample_interval"
    )

    # 3. For forecast input, confirm required horizons are present
    validate_horizons_present(dataset, horizons=[1, 2, 4, 8, 16, 24])

    # 4. Check for extreme outliers before training
    z_scores = (dataset.data - dataset.data.mean()) / dataset.data.std()
    outliers = (z_scores.abs() > 6).any(axis=1)
    if outliers.sum() > 0:
        print(f"Warning: {outliers.sum()} potential outlier rows detected")

Writing Forecasts Back to Storage
-----------------------------------

Once the pipeline produces a forecast, you write it back using the same ``to_parquet`` method or your own sink adapter.

**Writing to Parquet (local or S3)**

.. code-block:: python

    from pathlib import Path

    # forecast is a TimeSeriesDataset returned by the pipeline
    forecast.to_parquet(Path("output/forecasts/substation_a_2024-01-15.parquet"))

    # S3 works the same way — pandas handles the URI
    forecast.to_parquet("s3://my-energy-bucket/forecasts/substation_a_2024-01-15.parquet")

**Writing to PostgreSQL**

.. code-block:: python

    from sqlalchemy import create_engine

    engine = create_engine("postgresql+psycopg2://user:password@db-host:5432/energy_db")

    forecast_df = forecast.to_pandas()
    forecast_df["substation_id"] = "A"
    forecast_df["created_at"] = pd.Timestamp.utcnow()

    forecast_df.to_sql(
        name="forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="forecast_timestamp",
    )

**Writing to InfluxDB**

.. code-block:: python

    from influxdb_client import InfluxDBClient, WriteOptions
    from influxdb_client.client.write_api import SYNCHRONOUS

    forecast_df = forecast.to_pandas().rename(columns={"forecast": "load_mw_forecast"})

    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(
            bucket="energy_forecasts",
            record=forecast_df,
            data_frame_measurement_name="load_forecast",
            data_frame_tag_columns=["substation_id"],
        )

A Complete Pipeline Example
-----------------------------

The following sketch ties the patterns above into a single runnable pipeline that reads from PostgreSQL, combines weather data from S3, runs a forecast, and writes results back to PostgreSQL:

.. code-block:: python

    from datetime import timedelta, datetime, timezone
    from pathlib import Path
    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # --- Configuration ---
    DB_URL = "postgresql+psycopg2://user:password@db-host:5432/energy_db"
    SUBSTATION = "substation_a"
    SAMPLE_INTERVAL = timedelta(minutes=15)

    engine = create_engine(DB_URL)
    now = datetime.now(tz=timezone.utc)
    train_start = now - timedelta(days=90)

    # --- Load measurements ---
    df_meas = pd.read_sql(
        f"""
        SELECT timestamp, load_mw FROM measurements
        WHERE substation_id = '{SUBSTATION}'
          AND timestamp >= %(start)s
        ORDER BY timestamp
        """,
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
        params={"start": train_start},
    )
    df_meas.index = df_meas.index.tz_localize("UTC")
    measurements = TimeSeriesDataset(data=df_meas, sample_interval=SAMPLE_INTERVAL)

    # --- Load weather from S3 ---
    weather = VersionedTimeSeriesDataset.read_parquet(
        path=f"s3://my-energy-bucket/weather/{SUBSTATION}.parquet",
    )

    # --- Combine predictors ---
    predictors = VersionedTimeSeriesDataset.concat(
        datasets=[weather],
        mode="inner",
    ).filter_by_range(start=train_start, end=now + timedelta(days=2))

    # --- Run pipeline (see use_cases for full pipeline setup) ---
    # pipeline = build_pipeline(...)
    # forecast = pipeline.run(measurements=measurements, predictors=predictors)

    # --- Write forecast back ---
    # forecast.to_pandas().to_sql("forecasts", engine, if_exists="append", index=True)

.. note::

   The ``build_pipeline`` step is intentionally abbreviated here. See
   :doc:`use_cases` for complete pipeline construction examples, and
   :doc:`deployment` for patterns that schedule this pipeline in production.