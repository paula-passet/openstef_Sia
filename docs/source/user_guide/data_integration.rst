Data Integration
================

OpenSTEF is a library that sits in the middle of your data pipeline: it consumes time series data from wherever you store it, produces forecasts, and leaves the question of *where to put those forecasts* entirely up to you. This page explains how to connect OpenSTEF to real-world data sources, how to write forecast results back to storage, and how to use OpenSTEF's built-in validation tools to catch data quality problems before they reach the model.

For deployment patterns and scheduling concerns, see :doc:`deployment`. For a broader look at what you can build with OpenSTEF, see :doc:`use_cases`.

.. note:: [DIAGRAM: Data flow from external sources (S3, Databricks, InfluxDB, PostgreSQL) → pandas DataFrame → TimeSeriesDataset → OpenSTEF workflow → ForecastDataset → write back to storage]

The Central Contract: ``TimeSeriesDataset``
-------------------------------------------

Regardless of where your data lives, OpenSTEF always works with a ``TimeSeriesDataset`` (or its validated subclass ``ForecastInputDataset``). The entry point is a ``pandas.DataFrame`` with a ``DatetimeIndex``. Once you have that DataFrame, wrapping it is a single line:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    # df must have a DatetimeIndex and at least a "load" column for training
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

The ``sample_interval`` tells OpenSTEF the expected spacing between observations. All integration patterns below converge on producing this ``df``.

Reading Data from Common Sources
---------------------------------

Amazon S3 / Object Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Parquet files on S3 are a natural fit for energy time series data. The ``pandas`` S3 integration (via ``s3fs``) lets you read directly into a DataFrame:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    df = pd.read_parquet(
        "s3://my-energy-bucket/measurements/substation_42/",
        storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
    )
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

For production use, prefer reading credentials from environment variables or an IAM role rather than hardcoding them. If you write forecasts back to S3 (see `Writing Forecasts Back to Storage`_), using a consistent path scheme such as ``s3://bucket/forecasts/substation_42/YYYY/MM/DD/`` makes downstream queries straightforward.

Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^

When your data lives in a Delta table on Databricks, the cleanest approach is to query it with a Spark session and convert the result to a pandas DataFrame before handing it to OpenSTEF:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # spark is a SparkSession, available automatically in Databricks notebooks
    spark_df = spark.sql("""
        SELECT
            measurement_time AS timestamp,
            load_mw          AS load,
            temperature_c    AS temperature,
            wind_speed_ms    AS wind_speed
        FROM energy_catalog.measurements.substation_42
        WHERE measurement_time >= '2024-01-01'
        ORDER BY measurement_time
    """)

    df = spark_df.toPandas()
    df = df.set_index("timestamp")
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

.. note::

    The ``toPandas()`` call collects all data to the driver. For very large
    date ranges, filter aggressively in SQL first. OpenSTEF only needs a
    rolling window of historical data — typically a few weeks to a few months
    depending on your model configuration.

InfluxDB
^^^^^^^^

InfluxDB is commonly used for high-frequency sensor data. Query a time range and pivot the result into a wide DataFrame:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta, datetime, timezone
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="TOKEN", org="my-org")
    query_api = client.query_api()

    query = """
    from(bucket: "energy")
      |> range(start: -30d)
      |> filter(fn: (r) => r["_measurement"] == "substation" and r["location"] == "42")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(query)
    df = df.set_index("_time")[["load", "temperature", "wind_speed"]]
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

PostgreSQL / Relational Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For relational databases, ``pandas.read_sql`` with a SQLAlchemy engine is the standard approach:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from sqlalchemy import create_engine
    from openstef_core.datasets import TimeSeriesDataset

    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")

    df = pd.read_sql(
        """
        SELECT
            measured_at  AS timestamp,
            load_mw      AS load,
            temperature  AS temperature,
            wind_speed   AS wind_speed
        FROM measurements
        WHERE substation_id = 42
          AND measured_at >= NOW() - INTERVAL '60 days'
        ORDER BY measured_at
        """,
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )
    df.index = df.index.tz_localize("UTC")

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Custom and Composite Sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Real pipelines often combine data from multiple systems — measured load from a database, weather forecasts from an API, and calendar features from a local file. OpenSTEF provides ``combine_forecast_input_datasets`` to merge a primary dataset with additional feature datasets:

.. code-block:: python

    from openstef_core.datasets.operations import combine_forecast_input_datasets
    from openstef_core.datasets.validated_datasets import ForecastInputDataset
    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    # Primary dataset: measured load
    primary = ForecastInputDataset(load_df, sample_interval=timedelta(minutes=15))

    # Additional features: weather forecast from a separate source
    weather = TimeSeriesDataset(weather_df, sample_interval=timedelta(minutes=15))

    combined = combine_forecast_input_datasets(primary, weather)

The merge uses an inner join on the time index, so both datasets must overlap in time. Columns present in both datasets (except the target) are deduplicated automatically.

Data Validation
---------------

OpenSTEF ships three validation transforms in ``openstef_models.transforms.validation`` that you should apply before passing data to a model. Each transform follows the standard ``TimeSeriesTransform`` interface and raises a descriptive exception when it detects a problem.

``CompletenessChecker``
^^^^^^^^^^^^^^^^^^^^^^^

Checks that the ratio of non-missing values meets a minimum threshold. This is the most important check to run on incoming measurement data:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    df = pd.DataFrame(
        {
            "load": [100.0, np.nan, 102.0, 103.0],
            "temperature": [15.0, 15.5, np.nan, 16.0],
        },
        index=pd.date_range("2024-06-01", periods=4, freq="15min", tz="UTC"),
    )
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    checker = CompletenessChecker(columns=["load"])  # check only the target column
    validated = checker.transform(dataset)  # raises InsufficientlyCompleteError if too many NaNs

You can restrict the check to specific columns using the ``columns`` parameter. If you omit it, all columns are evaluated together.

``FlatlineChecker``
^^^^^^^^^^^^^^^^^^^

Detects flatliner patterns — consecutive identical values that indicate a stuck sensor rather than genuine data. This is particularly important for load measurements where a sensor may silently stop reporting real values:

.. code-block:: python

    from openstef_models.transforms.validation import FlatlineChecker

    flatline_checker = FlatlineChecker()
    validated = flatline_checker.transform(dataset)

``InputConsistencyChecker``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Validates that prediction-time data is consistent with the data the model was trained on — same columns, compatible value ranges, and matching sample interval. Fit it once on training data, then apply it at prediction time:

.. code-block:: python

    from openstef_models.transforms.validation import InputConsistencyChecker

    consistency_checker = InputConsistencyChecker()
    consistency_checker.fit(training_dataset)

    # Later, at prediction time:
    consistency_checker.transform(prediction_dataset)  # raises if columns are missing or ranges differ

Chaining Validators
^^^^^^^^^^^^^^^^^^^

In practice, you will want to run all three checks in sequence before training or predicting:

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    def validate_input(dataset, consistency_checker=None):
        dataset = CompletenessChecker(columns=["load"]).transform(dataset)
        dataset = FlatlineChecker().transform(dataset)
        if consistency_checker is not None:
            dataset = consistency_checker.transform(dataset)
        return dataset

Handling Missing Data
---------------------

OpenSTEF's validation layer will raise an ``InsufficientlyCompleteError`` when data is too sparse, but it does not impute missing values for you. The right strategy depends on the column:

- **Target column (load):** Missing values in the recent past are a real data quality problem. Alert on them rather than silently filling them. For gaps in historical training data, forward-fill or interpolation may be acceptable if the gaps are short (one or two intervals).
- **Weather features:** Short gaps (a few intervals) can be linearly interpolated. Longer gaps should be filled from a backup weather source or flagged.
- **Categorical features (day type, holiday flags):** These are deterministic and can always be reconstructed.

A minimal gap-filling step before constructing the dataset:

.. code-block:: python

    # Interpolate short gaps in weather features, leave load gaps as NaN
    df["temperature"] = df["temperature"].interpolate(method="time", limit=4)
    df["wind_speed"] = df["wind_speed"].interpolate(method="time", limit=4)
    # Do NOT interpolate load — let CompletenessChecker surface the problem

Writing Forecasts Back to Storage
----------------------------------

After running a workflow, the result is a ``ForecastDataset``. Its ``.data`` property is a standard pandas DataFrame, so you can write it to any storage system that accepts DataFrames.

**Parquet on local disk or S3:**

.. code-block:: python

    # Using OpenSTEF's built-in method
    forecast_result.to_parquet(path="forecasts/substation_42_forecast.parquet")

    # Or write directly to S3
    forecast_result.data.to_parquet(
        "s3://my-energy-bucket/forecasts/substation_42/2024-06-01.parquet",
        storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
    )

**PostgreSQL:**

.. code-block:: python

    forecast_result.data.to_sql(
        name="forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="forecast_time",
    )

**InfluxDB:**

.. code-block:: python

    from influxdb_client import WriteOptions

    write_api = client.write_api(write_options=WriteOptions(batch_size=500))
    write_api.write(
        bucket="energy",
        record=forecast_result.data,
        data_frame_measurement_name="forecast",
        data_frame_tag_columns=["substation_id"],
    )

Saving Intermediate Data for Debugging
----------------------------------------

During development it is often useful to inspect the data at each stage of a workflow — prepared training inputs, raw predictions, and feature contributions. The built-in ``DataSaveCallback`` handles this without any custom code:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    callback = DataSaveCallback(
        cache_dir=Path("/tmp/openstef_debug"),
        save_prepared_data=True,
        save_predict_data=True,
        save_forecast=True,
        save_contributions=True,
    )

    # Pass the callback when constructing your workflow
    workflow = CustomForecastingWorkflow(..., callbacks=[callback])

After the workflow runs, the ``cache_dir`` will contain Parquet files for each stage, named after the workflow's ``run_name``. This is preferable to adding ``print`` statements or manual ``to_parquet`` calls scattered through your pipeline.

.. note::

    ``DataSaveCallback`` is intended for debugging and backtesting analysis.
    In production, use a dedicated callback that writes only the final
    ``ForecastDataset`` to your target storage system.

Building a Complete Pipeline
-----------------------------

Putting the pieces together, a realistic integration looks like this:

.. code-block:: python

    from datetime import timedelta
    from pathlib import Path
    import pandas as pd
    from sqlalchemy import create_engine

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
    )

    # 1. Read from PostgreSQL
    engine = create_engine("postgresql+psycopg2://user:pass@host:5432/energy_db")
    df = pd.read_sql(
        "SELECT measured_at AS timestamp, load_mw AS load, temperature, wind_speed "
        "FROM measurements WHERE substation_id = 42 AND measured_at >= NOW() - INTERVAL '60 days' "
        "ORDER BY measured_at",
        con=engine,
        index_col="timestamp",
        parse_dates=["timestamp"],
    )
    df.index = df.index.tz_localize("UTC")

    # 2. Fill short weather gaps
    df["temperature"] = df["temperature"].interpolate(method="time", limit=4)
    df["wind_speed"] = df["wind_speed"].interpolate(method="time", limit=4)

    # 3. Wrap in TimeSeriesDataset
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    # 4. Validate
    dataset = CompletenessChecker(columns=["load"]).transform(dataset)
    dataset = FlatlineChecker().transform(dataset)

    # 5. Run your workflow (see use_cases for workflow construction)
    # forecast_result = workflow.predict(dataset)

    # 6. Write forecasts back
    # forecast_result.data.to_sql("forecasts", con=engine, if_exists="append", index=True)

.. note::

    Step 5 (workflow construction and model loading) is covered in detail in
    :doc:`use_cases`. Production scheduling and containerisation are covered
    in :doc:`deployment`.