Data Integration
================

OpenSTEF is a library, not a data platform — it does not prescribe where your time series data lives or how it moves between systems. Instead, it provides a clean boundary: bring your data in as a :class:`~openstef_core.datasets.TimeSeriesDataset` (or its validated subclasses), run the forecasting pipeline, and take the results back out as a :class:`~openstef_core.datasets.validated_datasets.ForecastDataset`. Everything outside that boundary is your integration code.

This page covers the practical patterns for that integration work: reading from common storage backends, validating data quality before it reaches the model, handling gaps and missing values, and writing forecasts back to storage.

.. note::

   This page focuses on data plumbing. For how forecasts are used in production workflows, see :doc:`deployment`. For worked end-to-end examples, see :doc:`use_cases`.

---

Reading Data into OpenSTEF
--------------------------

Regardless of where your data lives, the goal is the same: produce a :class:`pandas.DataFrame` with a timezone-aware :class:`pandas.DatetimeIndex` and hand it to OpenSTEF's dataset classes. The library does not care how you obtained the DataFrame — you can use any client library, ORM, or query engine that suits your infrastructure.

The minimal structure OpenSTEF expects for forecasting input is a time-indexed DataFrame containing at least a ``load`` column (the target) and any feature columns (weather, calendar signals, etc.). The :class:`~openstef_core.datasets.validated_datasets.ForecastInputDataset` constructor will raise :class:`~openstef_core.exceptions.MissingColumnsError` immediately if required columns are absent, giving you a fast failure before any model code runs.

.. code-block:: python

    from datetime import timedelta

    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # df is a plain pandas DataFrame you obtained from any source
    df = pd.DataFrame(...)  # must have a DatetimeIndex and a "load" column

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

The sections below show how to build that DataFrame from several common backends.

Reading from PostgreSQL
^^^^^^^^^^^^^^^^^^^^^^^

Use any PostgreSQL client (``psycopg2``, ``SQLAlchemy``, ``asyncpg``) to run your query and load the result into a DataFrame. The key step is ensuring the index is a timezone-aware :class:`pandas.DatetimeIndex`.

.. code-block:: python

    from datetime import timedelta

    import pandas as pd
    import sqlalchemy
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    engine = sqlalchemy.create_engine(
        "postgresql+psycopg2://user:password@host:5432/mydb"
    )

    query = """
        SELECT
            timestamp AT TIME ZONE 'UTC' AS timestamp,
            load,
            temperature,
            wind_speed
        FROM measurements
        WHERE timestamp >= NOW() - INTERVAL '90 days'
        ORDER BY timestamp
    """

    df = pd.read_sql(query, con=engine, index_col="timestamp", parse_dates=["timestamp"])
    df.index = df.index.tz_localize("UTC")  # ensure tz-aware if not already

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Reading from InfluxDB
^^^^^^^^^^^^^^^^^^^^^

InfluxDB's Python client returns results that map naturally to a DataFrame. Query your measurement, pivot tags into columns, and convert the index:

.. code-block:: python

    from datetime import timedelta

    import pandas as pd
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="my-token", org="my-org")
    query_api = client.query_api()

    tables = query_api.query_data_frame(
        'from(bucket: "energy") '
        '|> range(start: -90d) '
        '|> filter(fn: (r) => r._measurement == "grid_load") '
        '|> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")'
    )

    df = tables.set_index("_time")[["load", "temperature", "wind_speed"]]
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Reading from S3 (Parquet)
^^^^^^^^^^^^^^^^^^^^^^^^^

Parquet on S3 is a common pattern for historical training data. Use ``pandas`` with ``s3fs`` or ``pyarrow`` to read directly from a bucket:

.. code-block:: python

    from datetime import timedelta

    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    df = pd.read_parquet(
        "s3://my-bucket/energy-data/measurements/",
        storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
    )

    # Ensure the index is tz-aware
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Reading from Databricks
^^^^^^^^^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, use a Spark DataFrame and convert it to pandas before passing it to OpenSTEF. Keep the conversion late — do all filtering and aggregation in Spark first:

.. code-block:: python

    from datetime import timedelta

    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # spark is the active SparkSession
    spark_df = spark.table("catalog.schema.measurements").filter(
        "timestamp >= date_sub(current_date(), 90)"
    )

    # Convert to pandas only after filtering
    df = spark_df.toPandas()
    df = df.set_index("timestamp")
    df.index = df.index.dt.tz_localize("UTC")

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

.. note::

   For very large datasets, consider reading a rolling window rather than the full history. OpenSTEF models typically need weeks to months of history for training, not years.

---

Validating Data Quality
-----------------------

OpenSTEF provides three built-in validation transforms in ``openstef_models.transforms.validation`` that you should apply before training or inference. These transforms follow the standard :class:`~openstef_core.transforms.TimeSeriesTransform` interface and raise descriptive exceptions when data quality thresholds are not met.

:class:`~openstef_models.transforms.validation.CompletenessChecker`
   Checks the ratio of non-missing values to total values. Raises :class:`~openstef_core.exceptions.InsufficientlyCompleteError` if completeness falls below the configured threshold.

:class:`~openstef_models.transforms.validation.FlatlineChecker`
   Detects flatline patterns — sequences of identical values that indicate a stuck sensor or feed failure.

:class:`~openstef_models.transforms.validation.InputConsistencyChecker`
   Validates that prediction input is consistent with the feature set seen during training. Fit it on training data; call ``transform`` on prediction data.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    # Build a dataset (replace with your real data)
    df = pd.DataFrame(
        {
            "load": [100.0, 102.0, np.nan, 99.0, 101.0],
            "temperature": [15.0, 15.1, 15.2, 15.3, 15.4],
            "wind_speed": [3.0, 3.1, 3.0, 2.9, 3.0],
        },
        index=pd.date_range("2025-01-01", periods=5, freq="15min", tz="UTC"),
    )
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    # Check completeness (raises InsufficientlyCompleteError if too many NaNs)
    completeness_check = CompletenessChecker()
    dataset = completeness_check.transform(dataset)

    # Check for flatliners
    flatline_check = FlatlineChecker()
    dataset = flatline_check.transform(dataset)

    # Fit consistency checker on training data, then use on prediction data
    consistency_check = InputConsistencyChecker()
    consistency_check.fit(dataset)
    # Later, during prediction:
    # consistency_check.transform(prediction_dataset)

These checks are most valuable at the boundary between your data pipeline and the forecasting workflow — run them immediately after loading data, before any model code executes.

---

Handling Missing Data
---------------------

OpenSTEF's dataset classes accept DataFrames with ``NaN`` values; the library's internal transforms handle imputation as part of the model pipeline. Your responsibility as the integrator is to decide what constitutes *acceptable* missingness before data enters the pipeline.

A practical approach:

1. **Interpolate short gaps** (one or two missing samples) in your integration code using :meth:`pandas.DataFrame.interpolate` with ``method="time"`` before constructing the dataset.
2. **Use** :class:`~openstef_models.transforms.validation.CompletenessChecker` to reject datasets that are too sparse to be useful.
3. **Leave longer gaps** as ``NaN`` — the model's internal handling is more sophisticated than simple interpolation and will produce better results.

.. code-block:: python

    import pandas as pd

    # Interpolate gaps of at most 2 consecutive missing samples
    df["load"] = df["load"].interpolate(method="time", limit=2)

    # Feature columns from external sources (weather APIs, etc.) can tolerate
    # more aggressive forward-fill since they change slowly
    df[["temperature", "wind_speed"]] = (
        df[["temperature", "wind_speed"]].ffill(limit=4)
    )

.. warning::

   Do not forward-fill the target (``load``) column aggressively. Fabricated load values will corrupt model training. Prefer leaving gaps as ``NaN`` or using short-limit interpolation only.

---

Writing Forecasts Back to Storage
----------------------------------

After a forecasting workflow completes, the result is a :class:`~openstef_core.datasets.validated_datasets.ForecastDataset`. Its underlying data is accessible via the ``.data`` attribute as a standard :class:`pandas.DataFrame`, which you can write to any destination.

**Writing to Parquet (local or S3):**

.. code-block:: python

    # forecast_result is a ForecastDataset returned by the workflow
    forecast_df = forecast_result.data

    # Local file
    forecast_df.to_parquet("/data/forecasts/forecast_2025_01_01.parquet")

    # S3
    forecast_df.to_parquet(
        "s3://my-bucket/forecasts/forecast_2025_01_01.parquet",
        storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
    )

**Writing to PostgreSQL:**

.. code-block:: python

    import sqlalchemy

    engine = sqlalchemy.create_engine(
        "postgresql+psycopg2://user:password@host:5432/mydb"
    )

    forecast_df.to_sql(
        "forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="timestamp",
    )

**Using the built-in** ``DataSaveCallback`` **for workflow-level persistence:**

For debugging or audit trails, OpenSTEF's :class:`~openstef_models.workflows.callbacks.data_save.DataSaveCallback` can automatically persist intermediate datasets — training data, prepared inputs, forecasts, and feature contributions — to Parquet files at each stage of the workflow:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    callback = DataSaveCallback(
        cache_dir=Path("/data/debug"),
        save_forecast=True,
        save_predict_data=True,
        save_contributions=True,
    )

    # Pass the callback when constructing your workflow
    # workflow = CustomForecastingWorkflow(..., callbacks=[callback])

This is particularly useful during development and when diagnosing unexpected forecast behaviour in production.

---

Building a Custom Data Source
------------------------------

If your data source does not fit the patterns above, the integration pattern is always the same: implement a function or class that returns a :class:`~openstef_core.datasets.validated_datasets.ForecastInputDataset`. There is no base class to inherit from — OpenSTEF is a library and the data loading layer is entirely yours to design.

A clean pattern is a thin loader function:

.. code-block:: python

    from datetime import datetime, timedelta

    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset


    def load_forecast_input(
        connection_string: str,
        start: datetime,
        end: datetime,
        sample_interval: timedelta = timedelta(minutes=15),
    ) -> ForecastInputDataset:
        """Load and validate forecasting input from a custom source."""
        # Replace with your actual data retrieval logic
        df = _query_your_backend(connection_string, start, end)

        # Normalise index
        df.index = pd.to_datetime(df.index, utc=True)
        df = df.sort_index()

        return ForecastInputDataset(
            data=df,
            sample_interval=sample_interval,
            target_column="load",
        )


    def _query_your_backend(
        connection_string: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        # Your custom query logic here
        ...

Keeping the data loading logic isolated in a function like this makes it straightforward to swap backends, add caching, or mock the source in tests.

---

.. note:: [DIAGRAM: End-to-end data flow — external storage (S3/DB/InfluxDB) → loader function → ForecastInputDataset → validation transforms → forecasting workflow → ForecastDataset → write-back to storage]

---

For deployment patterns that orchestrate these data pipelines in production (scheduling, retries, containerisation), see :doc:`deployment`. For concrete end-to-end examples that combine data loading with specific forecasting scenarios, see :doc:`use_cases`.