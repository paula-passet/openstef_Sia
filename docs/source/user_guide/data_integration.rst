Data Integration
================

OpenSTEF is a library that sits inside your data pipeline — it does not manage connections to databases or cloud storage on its own. This page explains how to bring data *into* OpenSTEF from common sources, how to write forecasts back to storage, and how to use OpenSTEF's built-in validation tools to catch data quality problems before they reach the model.

For production deployment patterns (scheduling, containerisation, orchestration), see :doc:`deployment`. For worked end-to-end examples, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

Reading Data into OpenSTEF
--------------------------

OpenSTEF's core data structure is :class:`~openstef_core.datasets.TimeSeriesDataset`. Every integration pattern ultimately produces one of these objects. The constructor accepts a ``pandas.DataFrame`` with a ``DatetimeIndex`` and a ``sample_interval`` that describes the cadence of the series:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    df = pd.DataFrame(
        {"load": [...], "temperature": [...], "wind_speed": [...]},
        index=pd.date_range("2024-01-01", periods=96, freq="15min"),
    )

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Because the entry point is a plain ``DataFrame``, any library that can produce one works as a data source. The sections below show realistic patterns for the most common backends.

From Amazon S3 (Parquet)
^^^^^^^^^^^^^^^^^^^^^^^^

Parquet on S3 is a common pattern for storing historical load and weather data. Use ``s3fs`` (or any S3-compatible filesystem) to read the file into a ``DataFrame``, then wrap it:

.. code-block:: python

    import s3fs
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    fs = s3fs.S3FileSystem()

    with fs.open("s3://my-bucket/energy/load_2024.parquet", "rb") as f:
        df = pd.read_parquet(f)

    df.index = pd.to_datetime(df.index)
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

``TimeSeriesDataset`` also has a ``read_parquet`` class method that handles local paths directly. For S3 paths you still go through the filesystem abstraction above, but for local or mounted paths the built-in method is simpler:

.. code-block:: python

    dataset = TimeSeriesDataset.read_parquet(
        path="/mnt/data/load_2024.parquet",
        sample_interval=timedelta(minutes=15),
    )

From Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, use the Spark session to read a Delta table and convert to pandas before handing off to OpenSTEF:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    spark_df = spark.table("energy.load_measurements")  # noqa: F821 — spark injected by Databricks
    df = (
        spark_df
        .filter("timestamp >= '2024-01-01'")
        .toPandas()
        .set_index("timestamp")
        .sort_index()
    )

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

.. note::

   Keep the Spark-to-pandas conversion as late as possible. Filter and aggregate in Spark first to avoid pulling large tables into the driver's memory.

From InfluxDB
^^^^^^^^^^^^^

InfluxDB is widely used for real-time sensor and metering data. Query a time range and pivot the result into a wide ``DataFrame``:

.. code-block:: python

    from datetime import timedelta, datetime, timezone
    import pandas as pd
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="...", org="my-org")
    query_api = client.query_api()

    query = """
    from(bucket: "energy")
      |> range(start: 2024-01-01T00:00:00Z, stop: 2024-02-01T00:00:00Z)
      |> filter(fn: (r) => r._measurement == "grid_load")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(query)
    df = df.set_index("_time").sort_index()
    df.index = df.index.tz_convert("UTC").tz_localize(None)  # naive UTC

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

From PostgreSQL
^^^^^^^^^^^^^^^

For relational databases, ``pandas.read_sql`` with a SQLAlchemy engine is the most straightforward path:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    df = pd.read_sql(
        """
        SELECT timestamp, load, temperature, wind_speed
        FROM measurements
        WHERE timestamp BETWEEN '2024-01-01' AND '2024-02-01'
        ORDER BY timestamp
        """,
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Custom or Proprietary Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Any source that can produce a ``DataFrame`` with a ``DatetimeIndex`` works. A common pattern is to write a thin adapter function that encapsulates the connection logic and returns a ``TimeSeriesDataset``:

.. code-block:: python

    from datetime import timedelta, datetime
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset


    def load_from_scada(start: datetime, end: datetime) -> TimeSeriesDataset:
        """Fetch load data from an internal SCADA API."""
        raw = my_scada_client.fetch(start=start, end=end)  # noqa: F821
        df = pd.DataFrame(raw["measurements"]).set_index("ts").sort_index()
        df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
        return TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Keeping the adapter isolated makes it easy to swap backends without touching the forecasting code.

Validating Input Data
---------------------

OpenSTEF provides three built-in validation transforms in ``openstef_models.transforms.validation``. These are designed to be applied to a ``TimeSeriesDataset`` before it enters a workflow, and they raise descriptive exceptions when data quality is insufficient.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

**CompletenessChecker** raises ``InsufficientlyCompleteError`` when the ratio of non-missing values falls below a configurable threshold. You can restrict the check to specific columns and assign weights to reflect their relative importance:

.. code-block:: python

    from datetime import timedelta
    import numpy as np
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    df = pd.DataFrame(
        {
            "load": [100.0, np.nan, 102.0, 103.0],
            "temperature": [15.0, 15.5, np.nan, 16.0],
        },
        index=pd.date_range("2024-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    checker = CompletenessChecker(columns=["load", "temperature"])
    validated = checker.transform(dataset)  # raises InsufficientlyCompleteError if too sparse

**FlatlineChecker** detects when the most recent measurements are stuck at a constant value — a common sign of a failed sensor or a stale data feed:

.. code-block:: python

    from openstef_models.transforms.validation import FlatlineChecker

    flatline_checker = FlatlineChecker()
    validated = flatline_checker.transform(dataset)

**InputConsistencyChecker** is fitted on training data and then applied to prediction data to verify that the feature set and statistical properties are consistent between the two:

.. code-block:: python

    from openstef_models.transforms.validation import InputConsistencyChecker

    consistency_checker = InputConsistencyChecker()
    consistency_checker.fit(training_dataset)
    consistency_checker.transform(prediction_dataset)  # raises if columns differ

Handling Missing Data
---------------------

OpenSTEF does not silently impute missing values by default. The recommended approach is to handle gaps explicitly before constructing the dataset, using pandas interpolation or forward-fill for short gaps, and raising an error (or skipping the forecast window) for longer ones:

.. code-block:: python

    import pandas as pd

    # Fill gaps of up to 2 consecutive missing values by linear interpolation
    df["load"] = df["load"].interpolate(method="time", limit=2)

    # For longer gaps, flag the window rather than imputing
    max_gap = df["load"].isna().sum()
    if max_gap > 4:
        raise ValueError(f"Load data has {max_gap} consecutive missing values — skipping forecast.")

For weather features (temperature, wind, radiation) that arrive from a forecast provider, it is usually acceptable to forward-fill a single missing interval, since weather changes slowly relative to a 15-minute sample:

.. code-block:: python

    weather_cols = ["temperature", "wind_speed", "radiation"]
    df[weather_cols] = df[weather_cols].ffill(limit=1)

Writing Forecasts Back to Storage
----------------------------------

After calling ``workflow.predict()``, the result is a :class:`~openstef_core.datasets.validated_datasets.ForecastDataset`. Its underlying data is a ``DataFrame`` accessible via ``.data``, which you can write to any sink.

**To Parquet (local or mounted path):**

.. code-block:: python

    forecast = workflow.predict(dataset)
    forecast.to_parquet("/mnt/forecasts/grid_a_2024-01-15.parquet")

**To PostgreSQL:**

.. code-block:: python

    from sqlalchemy import create_engine

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")
    forecast.data.to_sql(
        "forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="timestamp",
    )

**To S3:**

.. code-block:: python

    import s3fs

    fs = s3fs.S3FileSystem()
    with fs.open("s3://my-bucket/forecasts/grid_a_2024-01-15.parquet", "wb") as f:
        forecast.data.to_parquet(f)

Persisting Intermediate Data with DataSaveCallback
---------------------------------------------------

During development and debugging it is useful to inspect the data at each stage of the workflow — raw training input, prepared features, and the final forecast. OpenSTEF's built-in :class:`~openstef_models.workflows.callbacks.data_save.DataSaveCallback` writes all of these to a local directory automatically:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback
    from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

    callback = DataSaveCallback(
        cache_dir=Path("/tmp/openstef_debug"),
        save_training_data=True,
        save_prepared_data=True,
        save_predict_data=True,
        save_forecast=True,
        save_contributions=False,
    )

    workflow = CustomForecastingWorkflow(
        model=model,
        model_id="grid_a",
        callbacks=[callback],
    )

    workflow.fit(training_dataset)
    forecast = workflow.predict(prediction_dataset)

After the run, ``/tmp/openstef_debug/`` will contain timestamped Parquet files for each stage, named using the workflow's ``run_name``. This is particularly useful when diagnosing unexpected forecast values or verifying that feature engineering is behaving as expected.

.. note::

   ``DataSaveCallback`` is intended for development and debugging. In production, prefer writing only the final ``ForecastDataset`` to your storage backend to avoid accumulating large intermediate files.

Building a Complete Data Pipeline
----------------------------------

The following example ties together all of the patterns above into a minimal but realistic pipeline that reads from PostgreSQL, validates the data, runs a forecast, and writes results back:

.. code-block:: python

    from datetime import timedelta, datetime
    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker

    # --- 1. Read ---
    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")
    df = pd.read_sql(
        "SELECT timestamp, load, temperature FROM measurements ORDER BY timestamp",
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )

    # --- 2. Light imputation for short gaps ---
    df["load"] = df["load"].interpolate(method="time", limit=2)
    df["temperature"] = df["temperature"].ffill(limit=1)

    # --- 3. Wrap in OpenSTEF dataset ---
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    # --- 4. Validate ---
    CompletenessChecker(columns=["load"]).transform(dataset)
    FlatlineChecker().transform(dataset)

    # --- 5. Forecast ---
    forecast = workflow.predict(dataset)  # workflow configured elsewhere

    # --- 6. Write results ---
    forecast.data["forecast_at"] = datetime.utcnow()
    forecast.data.to_sql(
        "forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="timestamp",
    )

This pattern keeps each concern — reading, cleaning, validating, forecasting, writing — in a distinct step, making it straightforward to replace any individual component without affecting the others.

.. note::

   For scheduling and running this pipeline in production (cron, Airflow, Databricks Jobs), see :doc:`deployment`.