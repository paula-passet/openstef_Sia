Data Integration
================

OpenSTEF is a library that sits inside your own data pipeline — it does not manage connections to databases or cloud storage on your behalf. This page explains how to bring data *into* OpenSTEF's dataset types from common sources (S3, Databricks, InfluxDB, PostgreSQL, and custom systems), how to write forecast results back to storage, and how to handle the data quality concerns that arise along the way.

For production deployment patterns that wrap these pipelines, see :doc:`deployment`. For logging within your pipeline, see :doc:`logging`.

.. mermaid:: diagrams/user_guide/data_integration_diagram_1.mmd

Understanding OpenSTEF's Data Contract
---------------------------------------

OpenSTEF's core dataset type is ``TimeSeriesDataset``, a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex``. The library validates structure and frequency at construction time, so your job as an integrator is simply to produce a well-formed DataFrame and hand it over.

For forecasting workflows, you will typically work with ``ForecastInputDataset``, which additionally requires a named target column (e.g. ``"load"``) representing the quantity to be predicted. Feature columns — weather variables, calendar flags, market prices — sit alongside the target in the same DataFrame.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Any DataFrame with a DatetimeIndex at a consistent frequency
    df = pd.DataFrame(
        {
            "load": [120.5, 118.3, 121.0, 119.7],
            "temperature": [15.2, 14.8, 14.5, 14.1],
            "wind_speed": [3.1, 3.4, 3.0, 2.8],
        },
        index=pd.date_range("2024-01-01 00:00", periods=4, freq="15min", tz="UTC"),
    )

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

The ``sample_interval`` must match the actual frequency of your index. OpenSTEF will raise a ``TimeSeriesValidationError`` at construction time if the data does not conform, which is exactly the kind of early failure you want in a pipeline.

Reading from Common Sources
----------------------------

The pattern is always the same: use your preferred client library to fetch data, normalise it into a ``DatetimeIndex``-bearing DataFrame, then construct the appropriate OpenSTEF dataset. The sections below show concrete examples for the most common backends.

PostgreSQL
^^^^^^^^^^

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    import sqlalchemy
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    engine = sqlalchemy.create_engine(
        "postgresql+psycopg2://user:password@db-host:5432/energy"
    )

    query = """
        SELECT
            measured_at AS timestamp,
            load_mw      AS load,
            temperature  AS temperature,
            wind_speed   AS wind_speed
        FROM meter_readings
        WHERE meter_id = :meter_id
          AND measured_at >= :start
          AND measured_at <  :end
        ORDER BY measured_at
    """

    df = pd.read_sql(
        query,
        engine,
        params={"meter_id": "substation_42", "start": "2024-01-01", "end": "2024-02-01"},
        index_col="timestamp",
        parse_dates=["timestamp"],
    )
    df.index = df.index.tz_localize("UTC")  # ensure timezone-aware index

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

InfluxDB
^^^^^^^^

InfluxDB's Python client returns data as a DataFrame when you use the ``query_data_frame`` method. The main normalisation step is renaming the ``_time`` column and ensuring the index is timezone-aware.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    client = InfluxDBClient(url="http://influx-host:8086", token="my-token", org="my-org")
    query_api = client.query_api()

    flux_query = """
        from(bucket: "energy")
          |> range(start: 2024-01-01T00:00:00Z, stop: 2024-02-01T00:00:00Z)
          |> filter(fn: (r) => r["_measurement"] == "substation_42")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(flux_query)
    df = df.set_index("_time").rename_axis("timestamp")
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[["load", "temperature", "wind_speed"]]  # keep only relevant columns

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Amazon S3
^^^^^^^^^

Parquet files on S3 are a natural fit for time series archives. ``pandas`` reads them directly via ``s3fs``.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Requires: pip install s3fs pyarrow
    df = pd.read_parquet(
        "s3://my-energy-bucket/substations/substation_42/2024-01.parquet",
        storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
    )
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

For larger date ranges stored as partitioned Parquet datasets, pass a directory path and ``pandas`` will merge the partitions automatically.

Databricks / Spark
^^^^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, collect the Spark DataFrame to the driver before constructing an OpenSTEF dataset. Keep the time window reasonable — OpenSTEF operates on in-memory DataFrames.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    spark_df = spark.table("energy.meter_readings").filter(
        "meter_id = 'substation_42' AND measured_at >= '2024-01-01'"
    )

    df = spark_df.toPandas()
    df = df.set_index("measured_at")
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Custom or REST Sources
^^^^^^^^^^^^^^^^^^^^^^

Any source that can produce a ``pandas.DataFrame`` with a ``DatetimeIndex`` works. The pattern below applies equally to custom REST APIs, CSV files, or proprietary historian systems:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    import requests
    from openstef_core.datasets import TimeSeriesDataset

    response = requests.get(
        "https://api.example.com/timeseries",
        params={"asset": "substation_42", "from": "2024-01-01", "to": "2024-02-01"},
        headers={"Authorization": "Bearer my-token"},
    )
    response.raise_for_status()

    records = response.json()["data"]
    df = pd.DataFrame(records).set_index("timestamp")
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Validating Input Data
----------------------

OpenSTEF provides three validation transforms in ``openstef_models.transforms.validation`` that you should apply before passing data to a workflow. Each implements the ``TimeSeriesTransform`` interface and raises a descriptive exception when a check fails, making them easy to embed in a pipeline.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    # CompletenessChecker: raises InsufficientlyCompleteError if too many NaNs
    completeness = CompletenessChecker(
        columns=["load", "temperature", "wind_speed"],
    )
    dataset = completeness.transform(dataset)

    # FlatlineChecker: detects stuck-sensor patterns (constant values over time)
    flatline = FlatlineChecker()
    dataset = flatline.transform(dataset)

    # InputConsistencyChecker: fit on training data, then validate prediction data
    consistency = InputConsistencyChecker()
    consistency.fit(training_dataset)
    prediction_dataset = consistency.transform(prediction_dataset)

``CompletenessChecker`` computes the ratio of non-missing values to total values. You can pass column-level weights if some features matter more than others. ``FlatlineChecker`` is particularly useful for catching sensor faults before they silently degrade forecast quality. ``InputConsistencyChecker`` is most valuable at inference time — fit it on your training window and use it to flag prediction inputs that fall outside the expected distribution.

Handling Missing Data
----------------------

OpenSTEF does not impute missing values automatically; that responsibility belongs to your pipeline. The recommended approach is to resample your DataFrame to the target frequency (which introduces ``NaN`` rows for any gaps) and then apply your chosen fill strategy before constructing the dataset.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Resample to enforce a uniform 15-minute grid
    df = df.resample("15min").mean()

    # Forward-fill short gaps (e.g. up to 1 hour) for feature columns
    df[["temperature", "wind_speed"]] = (
        df[["temperature", "wind_speed"]].ffill(limit=4)
    )

    # For the target column, leave gaps as NaN — the model will treat
    # these rows as missing observations during training
    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

.. warning::

   Avoid forward-filling the target column (``load``) for training data. Imputed target values look like real measurements to the model and will bias it toward predicting flat segments during periods that were actually missing.

Writing Forecasts Back to Storage
-----------------------------------

After a workflow produces a ``ForecastDataset``, its underlying DataFrame is accessible via the ``.data`` attribute and can be written to any sink using standard pandas I/O.

.. code-block:: python

    import sqlalchemy

    # forecast_result is a ForecastDataset returned by the workflow
    forecast_df = forecast_result.data.reset_index()  # moves DatetimeIndex to column

    # Write to PostgreSQL
    engine = sqlalchemy.create_engine("postgresql+psycopg2://user:password@db-host/energy")
    forecast_df.to_sql(
        "forecasts",
        engine,
        if_exists="append",
        index=False,
        method="multi",
    )

    # Write to S3 as Parquet
    forecast_df.to_parquet(
        "s3://my-energy-bucket/forecasts/substation_42/2024-01-15.parquet",
        storage_options={"key": "ACCESS_KEY", "secret": "SECRET_KEY"},
    )

For debugging and backtesting, OpenSTEF's built-in ``DataSaveCallback`` writes intermediate datasets — training data, prepared inputs, forecasts, and feature contributions — to local Parquet files without any extra code in your pipeline:

.. code-block:: python

    from pathlib import Path
    from openstef_models.workflows.callbacks.data_save import DataSaveCallback

    callback = DataSaveCallback(
        cache_dir=Path("/tmp/openstef_debug"),
        save_training_data=True,
        save_forecast=True,
        save_contributions=True,
    )

    # Pass the callback when constructing your workflow
    workflow = CustomForecastingWorkflow(..., callbacks=[callback])

Each file is named using the workflow's ``run_name``, making it straightforward to correlate files across multiple runs.

Combining Multiple Data Sources
---------------------------------

When your feature data comes from a different system than your load measurements, use ``combine_forecast_input_datasets`` to merge them before passing to a workflow. The function performs an inner join on the time index.

.. code-block:: python

    from openstef_core.datasets.operations import combine_forecast_input_datasets

    # Load measurements from PostgreSQL
    load_dataset = ForecastInputDataset(data=load_df, sample_interval=timedelta(minutes=15))

    # Weather features from a separate REST API
    weather_dataset = TimeSeriesDataset(data=weather_df, sample_interval=timedelta(minutes=15))

    combined = combine_forecast_input_datasets(load_dataset, weather_dataset)

.. note::

   Only ``"inner"`` joins are currently supported. Rows present in one source but not the other will be dropped. Ensure your sources cover the same time window before combining, or use the missing-data handling approach described above to fill gaps first.

Summary
--------

The integration pattern in OpenSTEF is deliberately simple: produce a ``pandas.DataFrame`` with a timezone-aware ``DatetimeIndex``, wrap it in the appropriate dataset class, validate it with the built-in checkers, and write results back using standard pandas I/O. The library imposes no opinion on which database or cloud platform you use — those choices remain entirely within your own pipeline code.

For orchestrating these pipelines in production, see :doc:`deployment`. For practical end-to-end examples that combine data integration with model training and inference, see :doc:`use_cases`.