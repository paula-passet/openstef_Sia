Data Integration
================

This page covers how to bring data into OpenSTEF from common storage systems, how to write forecasts back to those systems, and how to handle the data quality issues that inevitably arise in real-world pipelines. It focuses on the mechanics of wiring up sources and sinks — for how forecasts are consumed once they exist, see :doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

Reading Input Data
------------------

OpenSTEF's forecasting pipeline expects a ``TimeSeriesDataset`` (or its validated subclass ``ForecastInputDataset``) as input. These are thin wrappers around a ``pandas.DataFrame`` with a ``DatetimeIndex``, so the integration pattern is always the same: read your data into a DataFrame, validate it, and wrap it.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Any DataFrame with a DatetimeIndex and a "load" column works
    df = pd.read_parquet("s3://my-bucket/grid/load_and_features.parquet")

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

``ForecastInputDataset`` immediately validates that the target column is present and raises ``MissingColumnsError`` if it is not, catching integration mistakes early.

From S3 / Object Storage
^^^^^^^^^^^^^^^^^^^^^^^^^

The most portable approach is Parquet on object storage. ``pandas`` reads S3 paths directly when ``s3fs`` is installed, and the resulting DataFrame drops straight into OpenSTEF:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    df = pd.read_parquet(
        "s3://energy-data/substations/substation_42/features.parquet",
        storage_options={"anon": False},  # uses boto3 credential chain
    )
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

For partitioned datasets (e.g. ``year=2024/month=06/``), pass a directory path and ``pandas`` will read all partitions automatically.

From Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When your feature store lives in a Databricks lakehouse, read via the ``databricks-connect`` or ``delta-spark`` client and convert the Spark DataFrame to pandas before wrapping:

.. code-block:: python

    from pyspark.sql import SparkSession
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    spark = SparkSession.builder.getOrCreate()

    sdf = spark.read.format("delta").load(
        "/mnt/energy/features/substation_42"
    ).filter("timestamp >= '2024-01-01'")

    df = sdf.toPandas().set_index("timestamp")
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

.. note::
    Keep the Spark-to-pandas conversion as late as possible. Apply all filters and aggregations in Spark before calling ``toPandas()`` to avoid pulling unnecessary data into the driver.

From InfluxDB
^^^^^^^^^^^^^

InfluxDB is common for real-time measurement streams. Query a time window and pivot the result into a wide DataFrame:

.. code-block:: python

    from influxdb_client import InfluxDBClient
    import pandas as pd
    from datetime import timedelta, datetime, timezone
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="energy")
    query_api = client.query_api()

    flux_query = """
    from(bucket: "measurements")
      |> range(start: -7d)
      |> filter(fn: (r) => r["_measurement"] == "substation_42")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(flux_query)
    df = df.set_index("_time").drop(columns=["result", "table", "_start", "_stop"])
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

From PostgreSQL
^^^^^^^^^^^^^^^

For relational stores, ``pandas.read_sql`` with a SQLAlchemy engine is the simplest path:

.. code-block:: python

    from sqlalchemy import create_engine
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    engine = create_engine("postgresql+psycopg2://user:pass@db-host/energy")

    df = pd.read_sql(
        """
        SELECT timestamp, load, temperature, wind_speed, solar_irradiance
        FROM substation_features
        WHERE substation_id = 42
          AND timestamp >= NOW() - INTERVAL '7 days'
        ORDER BY timestamp
        """,
        con=engine,
        index_col="timestamp",
        parse_dates={"timestamp": {"utc": True}},
    )

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Data Validation
---------------

Before feeding data to a model, OpenSTEF provides three validation transforms that catch common data quality problems. They live in ``openstef_models.transforms.validation`` and implement the standard ``TimeSeriesTransform`` interface, so they can be composed into a preprocessing chain.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    completeness = CompletenessChecker()
    flatline = FlatlineChecker()
    consistency = InputConsistencyChecker()

    # Fit on training data to learn expected structure
    completeness.fit(training_dataset)
    flatline.fit(training_dataset)
    consistency.fit(training_dataset)

    # Transform raises or warns on quality issues
    clean_dataset = completeness.transform(live_dataset)
    clean_dataset = flatline.transform(clean_dataset)
    clean_dataset = consistency.transform(clean_dataset)

- **CompletenessChecker** — flags time windows with too many missing values.
- **FlatlineChecker** — detects sensors that have stopped updating (constant value over a window).
- **InputConsistencyChecker** — ensures the live feature set matches the columns seen during training. Extra columns are dropped with a warning; missing columns raise an error.

Handling Missing Data
---------------------

Real measurement streams always have gaps. The recommended approach is to impute or forward-fill *before* constructing the dataset, so that the ``TimeSeriesDataset`` invariants (uniform sample interval, no index gaps) are satisfied:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Reindex to a complete grid, then interpolate
    full_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="15min",
        tz="UTC",
    )
    df = df.reindex(full_index)

    # Forward-fill sensor readings (max 4 steps = 1 hour)
    df["load"] = df["load"].ffill(limit=4)

    # Interpolate weather features linearly
    weather_cols = ["temperature", "wind_speed", "solar_irradiance"]
    df[weather_cols] = df[weather_cols].interpolate(method="time", limit=8)

    # Drop any remaining NaNs at the edges
    df = df.dropna()

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

.. warning::
    Avoid forward-filling the target column (``load``) for more than a few steps. Imputed load values used as training labels will degrade model quality. If a gap is too large, exclude that window from training entirely.

Writing Forecasts Back to Storage
----------------------------------

After running a forecast, the result is a ``ForecastDataset``. Its underlying DataFrame is accessible via ``.data`` and can be written to any sink.

.. code-block:: python

    from openstef_core.datasets.validated_datasets import ForecastDataset

    # forecast_result is a ForecastDataset returned by the workflow
    df_out = forecast_result.data

    # Write to Parquet on S3
    df_out.to_parquet("s3://energy-forecasts/substation_42/latest.parquet")

    # Write to PostgreSQL
    df_out.to_sql(
        "forecasts",
        con=engine,
        if_exists="append",
        index=True,
        index_label="timestamp",
    )

    # Write to InfluxDB
    write_api = client.write_api()
    write_api.write(
        bucket="forecasts",
        record=df_out,
        data_frame_measurement_name="substation_42",
        data_frame_tag_columns=[],
    )

Using the DataSaveCallback for Debugging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During development it is useful to persist intermediate pipeline artefacts — training data, prepared features, and contributions — without modifying the workflow itself. ``DataSaveCallback`` does this automatically:

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

    # Pass to your workflow
    workflow = CustomForecastingWorkflow(
        model=model,
        callbacks=[callback],
    )

After a run, ``/tmp/openstef_debug/`` will contain Parquet files for each stage, named by the workflow's ``run_name``. These are invaluable for diagnosing feature engineering issues or unexpected forecast shapes.

.. note:: [VISUALIZATION: Example forecast output DataFrame showing timestamp index, quantile columns, and load prediction values]

Building a Custom Source Adapter
---------------------------------

If your data source does not fit the patterns above, the cleanest approach is a small adapter function that returns a ``TimeSeriesDataset``. Keeping the adapter separate from the forecasting logic makes both easier to test:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset


    def load_from_custom_api(
        substation_id: int,
        lookback_hours: int = 168,
    ) -> TimeSeriesDataset:
        """Fetch features from an internal REST API and return a TimeSeriesDataset."""
        import requests

        response = requests.get(
            f"https://internal-api/substations/{substation_id}/features",
            params={"lookback_hours": lookback_hours},
            timeout=30,
        )
        response.raise_for_status()

        df = pd.DataFrame(response.json()["data"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp").sort_index()

        return TimeSeriesDataset(
            data=df,
            sample_interval=timedelta(minutes=15),
        )

The adapter is the only place that knows about the external system. The rest of the pipeline receives a plain ``TimeSeriesDataset`` and is completely source-agnostic.

.. note::
    For production deployments that run this adapter on a schedule, see :doc:`deployment` for patterns around orchestration and error handling. For concrete end-to-end examples that combine data loading with model training and serving, see :doc:`use_cases`.