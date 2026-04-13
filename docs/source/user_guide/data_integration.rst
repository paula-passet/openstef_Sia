Data Integration
================

OpenSTEF operates on standard pandas DataFrames wrapped in typed dataset objects, which means it integrates naturally with any data source you can read into Python. This page covers practical patterns for pulling data from common storage systems, feeding it into OpenSTEF's dataset classes, validating it before training or inference, handling missing values, and writing forecasts back to storage.

For production deployment concerns such as scheduling and containerisation, see :doc:`deployment`. For worked end-to-end examples, see :doc:`use_cases`.

.. mermaid:: diagrams/user_guide/data_integration_diagram_1.mmd

Understanding OpenSTEF's Data Contract
---------------------------------------

Before connecting any source, it helps to understand what OpenSTEF expects. The library's core input type is ``ForecastInputDataset``, a thin wrapper around a ``pandas.DataFrame`` with a ``DatetimeIndex``. The wrapper validates that required columns are present and that the time series has a consistent sample interval.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # Any DataFrame with a DatetimeIndex can become a TimeSeriesDataset
    df = pd.DataFrame(
        {
            "load": [100.0, 102.5, None, 98.0],
            "temperature": [12.1, 12.3, 12.6, 12.9],
            "wind_speed": [3.2, 3.5, 3.1, 2.8],
        },
        index=pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC"),
    )

    # Wrap as a generic time series (15-minute interval)
    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    # Or as a validated forecasting input (requires a target column)
    forecast_input = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

The ``sample_interval`` argument is the only structural requirement beyond a ``DatetimeIndex``. Everything else — column names, feature engineering, imputation — is handled by the transform pipeline described later in this page.

Reading from Common Sources
-----------------------------

PostgreSQL
^^^^^^^^^^

A typical energy utility stores metered load data in a relational database. Use ``psycopg2`` or ``SQLAlchemy`` to fetch a result set and hand it directly to OpenSTEF:

.. code-block:: python

    from datetime import timedelta, timezone
    import pandas as pd
    from sqlalchemy import create_engine
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")

    query = """
        SELECT
            measured_at   AS datetime,
            load_mw,
            temperature_c,
            wind_speed_ms
        FROM measurements
        WHERE connection_id = %(conn_id)s
          AND measured_at BETWEEN %(start)s AND %(end)s
        ORDER BY measured_at
    """

    df = pd.read_sql(
        query,
        engine,
        params={"conn_id": "GS-001", "start": "2024-01-01", "end": "2024-04-01"},
        index_col="datetime",
        parse_dates={"datetime": {"utc": True}},
    )
    df.index = df.index.tz_convert("UTC")

    dataset = ForecastInputDataset(
        data=df.rename(columns={"load_mw": "load"}),
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

.. note::

   Always normalise your index to UTC before constructing an OpenSTEF dataset. Mixed-timezone indices cause subtle alignment bugs when combining data from multiple sources.

InfluxDB
^^^^^^^^

InfluxDB is popular for high-frequency time series storage. The ``influxdb-client`` library returns data as a pandas DataFrame when you use the ``query_api`` with ``to_dataframe()``:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from influxdb_client import InfluxDBClient
    from openstef_core.datasets import TimeSeriesDataset

    client = InfluxDBClient(
        url="http://influxdb:8086",
        token="my-token",
        org="my-org",
    )
    query_api = client.query_api()

    flux_query = """
        from(bucket: "energy")
          |> range(start: -90d)
          |> filter(fn: (r) => r["_measurement"] == "grid_load")
          |> filter(fn: (r) => r["connection"] == "GS-001")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    df = query_api.query_data_frame(flux_query)
    df = df.set_index("_time").drop(columns=["result", "table"], errors="ignore")
    df.index = pd.to_datetime(df.index, utc=True)

    dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

Amazon S3
^^^^^^^^^

Parquet files on S3 are a common archival format for historical load data. ``pandas`` reads them directly via ``s3fs``:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # pandas uses s3fs automatically when the path starts with s3://
    df = pd.read_parquet(
        "s3://my-energy-bucket/measurements/connection=GS-001/year=2024/",
        storage_options={"anon": False},  # uses ~/.aws/credentials or IAM role
    )

    df.index = pd.to_datetime(df["datetime"], utc=True)
    df = df.drop(columns=["datetime"])

    dataset = ForecastInputDataset(
        data=df,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

For large datasets, consider reading only the date partitions you need by passing a ``filters`` argument to ``pd.read_parquet``.

Databricks / Apache Spark
^^^^^^^^^^^^^^^^^^^^^^^^^^

When your data lives in a Databricks lakehouse, convert a Spark DataFrame to pandas before wrapping it in an OpenSTEF dataset. Keep the conversion as late as possible to benefit from Spark's distributed query execution:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # spark is a SparkSession available in Databricks notebooks
    spark_df = spark.table("energy.measurements").filter(
        "connection_id = 'GS-001' AND measured_at >= '2024-01-01'"
    )

    # Convert only after filtering — avoids pulling the full table into the driver
    pdf = spark_df.toPandas()
    pdf = pdf.set_index(pd.to_datetime(pdf["measured_at"], utc=True)).drop(
        columns=["measured_at"]
    )

    dataset = ForecastInputDataset(
        data=pdf,
        sample_interval=timedelta(minutes=15),
        target_column="load",
    )

Custom Sources
^^^^^^^^^^^^^^

Any source that produces a ``pandas.DataFrame`` with a ``DatetimeIndex`` works. A minimal adapter pattern keeps source-specific code isolated:

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset


    def load_from_custom_api(
        connection_id: str,
        start: datetime,
        end: datetime,
        interval: timedelta = timedelta(minutes=15),
    ) -> ForecastInputDataset:
        """Fetch data from a proprietary REST API and return an OpenSTEF dataset."""
        raw = my_api_client.get_measurements(connection_id, start, end)
        df = pd.DataFrame(raw["data"])
        df.index = pd.to_datetime(df.pop("timestamp"), utc=True)
        df = df.rename(columns={"power_kw": "load"})
        return ForecastInputDataset(data=df, sample_interval=interval, target_column="load")

Validating Input Data
----------------------

OpenSTEF provides three built-in validation transforms in ``openstef_models.transforms.validation``. Apply them as a pre-flight check before training or inference to catch data quality issues early rather than silently producing bad forecasts.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )
    from openstef_core.exceptions import InsufficientlyCompleteError

    # 1. Completeness — raises InsufficientlyCompleteError if too many NaNs
    completeness = CompletenessChecker(
        columns=["load", "temperature", "wind_speed"],
    )

    # 2. Flatline detection — flags series stuck at a constant value
    flatline = FlatlineChecker()

    # 3. Consistency — checks that the data matches the distribution seen at fit time
    consistency = InputConsistencyChecker()
    consistency.fit(training_dataset)

    try:
        completeness.transform(dataset)
        flatline.transform(dataset)
        consistency.transform(dataset)
    except InsufficientlyCompleteError as exc:
        # Log and skip this connection for this forecast cycle
        print(f"Skipping forecast: {exc}")

``CompletenessChecker`` computes the ratio of non-missing values to total values. The following example demonstrates the error it raises when data is too sparse:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    df = pd.DataFrame(
        {
            "radiation":    [100, np.nan, np.nan, np.nan],
            "temperature":  [20,  np.nan, 24,     np.nan],
            "wind_speed":   [np.nan, np.nan, np.nan, np.nan],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(df, timedelta(minutes=15))

    checker = CompletenessChecker()
    checker.transform(dataset)
    # Raises: InsufficientlyCompleteError: The dataset is not sufficiently complete.
    #         Completeness: 0.25

Handling Missing Data
----------------------

After validation you will typically want to fill gaps rather than discard the dataset entirely. OpenSTEF's ``Imputer`` transform supports several strategies and integrates cleanly into the same pipeline:

.. code-block:: python

    from openstef_models.transforms.imputation import Imputer
    from openstef_models.utils.feature_selection import FeatureSelection

    # Simple mean imputation for weather features
    imputer = Imputer(
        imputation_strategy="mean",
        selection=FeatureSelection(include={"temperature", "wind_speed", "radiation"}),
    )
    imputer.fit(training_dataset)
    clean_dataset = imputer.transform(dataset)

    # Iterative (multivariate) imputation for correlated features
    from sklearn.ensemble import RandomForestRegressor

    iterative_imputer = Imputer(
        imputation_strategy="iterative",
        selection=FeatureSelection(include={"temperature", "wind_speed"}),
        impute_estimator=RandomForestRegressor(n_estimators=50),
    )
    iterative_imputer.fit(training_dataset)
    clean_dataset = iterative_imputer.transform(dataset)

.. note::

   The ``Imputer`` intentionally leaves trailing NaN values (future time steps with no observations) unfilled. Imputing beyond the last valid index would introduce look-ahead bias during training.

Available strategies are ``"mean"``, ``"median"``, ``"most_frequent"``, ``"constant"``, and ``"iterative"``. The iterative strategy uses a ``BayesianRidge`` estimator by default but accepts any scikit-learn compatible regressor via ``impute_estimator``.

Combining Data from Multiple Sources
--------------------------------------

It is common to source the target load series from one system and weather features from another. Use ``combine_forecast_input_datasets`` to merge them on a shared time index:

.. code-block:: python

    from openstef_meta.utils.datasets import combine_forecast_input_datasets

    load_dataset = load_from_postgres(connection_id="GS-001", ...)
    weather_dataset = load_from_influxdb(station="KNMI-260", ...)

    combined = combine_forecast_input_datasets(
        input_data=load_dataset,
        additional_features=weather_dataset,
        join="inner",   # only timestamps present in both sources
    )

The function drops duplicate target columns from the additional features before joining, so there is no risk of accidentally overwriting the load series.

Writing Forecasts Back to Storage
-----------------------------------

After running inference, the output is a ``TimeSeriesDataset`` (or ``EnsembleForecastDataset``) whose underlying ``pandas.DataFrame`` is accessible via ``.data``. Writing it back is straightforward:

.. code-block:: python

    # forecast_result is a TimeSeriesDataset returned by the forecaster
    output_df = forecast_result.data

    # --- PostgreSQL ---
    output_df.to_sql(
        "forecasts",
        engine,
        if_exists="append",
        index=True,
        index_label="forecast_at",
    )

    # --- InfluxDB ---
    write_api = client.write_api()
    write_api.write(
        bucket="energy",
        record=output_df,
        data_frame_measurement_name="grid_load_forecast",
        data_frame_tag_columns=["connection_id"],
    )

    # --- S3 (Parquet) ---
    output_df.to_parquet(
        f"s3://my-energy-bucket/forecasts/connection=GS-001/run={run_id}.parquet",
        storage_options={"anon": False},
    )

A Realistic Pipeline
---------------------

Putting the pieces together, a complete read-validate-impute-forecast-write cycle looks like this:

.. code-block:: python

    from datetime import datetime, timedelta, timezone
    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset
    from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker
    from openstef_models.transforms.imputation import Imputer
    from openstef_core.exceptions import InsufficientlyCompleteError

    CONNECTION_ID = "GS-001"
    NOW = datetime.now(tz=timezone.utc)
    LOOKBACK = timedelta(days=90)
    INTERVAL = timedelta(minutes=15)

    # 1. Ingest
    df = pd.read_sql(
        "SELECT measured_at, load_mw AS load, temperature_c AS temperature "
        "FROM measurements WHERE connection_id = %(cid)s AND measured_at > %(start)s "
        "ORDER BY measured_at",
        engine,
        params={"cid": CONNECTION_ID, "start": NOW - LOOKBACK},
        index_col="measured_at",
        parse_dates={"measured_at": {"utc": True}},
    )
    dataset = ForecastInputDataset(data=df, sample_interval=INTERVAL, target_column="load")

    # 2. Validate
    try:
        CompletenessChecker(columns=["load", "temperature"]).transform(dataset)
        FlatlineChecker().transform(dataset)
    except InsufficientlyCompleteError as exc:
        raise RuntimeError(f"Data quality check failed for {CONNECTION_ID}: {exc}") from exc

    # 3. Impute
    imputer = Imputer(imputation_strategy="mean")
    imputer.fit(dataset)
    clean_dataset = imputer.transform(dataset)

    # 4. Forecast (forecaster loaded separately — see use_cases page)
    forecast_result = forecaster.predict(clean_dataset)

    # 5. Write back
    forecast_result.data.to_sql(
        "forecasts", engine, if_exists="append", index=True, index_label="forecast_at"
    )

.. note::

   This example omits model loading and forecaster configuration for brevity. See :doc:`use_cases` for complete training and inference examples, and :doc:`deployment` for patterns around scheduling this pipeline in production.