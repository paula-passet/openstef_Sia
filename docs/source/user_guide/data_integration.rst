Data Integration
================

OpenSTEF is storage-agnostic by design: it operates on ``pandas.DataFrame`` objects and
``TimeSeriesDataset`` instances, so you are free to pull data from any source and push
forecasts to any destination. This page covers practical patterns for the most common
storage backends, how to wrap custom sources, how to handle missing data, and how to
validate inputs before they reach the model.

For how these patterns fit into a production deployment, see :doc:`deployment`. For
end-to-end use-case examples that combine data integration with model training, see
:doc:`use_cases`.

.. mermaid:: /diagrams/user_guide/data_integration_diagram_1.mmd

---

Reading Data
------------

OpenSTEF expects time-indexed ``pandas.DataFrame`` objects as input. The index must be a
``DatetimeIndex`` with a consistent sample interval (e.g. 15 minutes). Any library that
can produce such a DataFrame — ``boto3``, ``influxdb-client``, ``psycopg2``,
``databricks-connect`` — works without any adapter layer.

From PostgreSQL
^^^^^^^^^^^^^^^

A straightforward pattern using ``psycopg2`` and ``pandas``:

.. code-block:: python

    import pandas as pd
    import psycopg2
    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    conn = psycopg2.connect(
        host="db.example.com",
        dbname="energy",
        user="reader",
        password="<password>",
    )

    query = """
        SELECT timestamp, load, temperature, wind_speed
        FROM measurements
        WHERE grid_point = 'substation_42'
          AND timestamp BETWEEN %(start)s AND %(end)s
        ORDER BY timestamp
    """

    df = pd.read_sql(
        query,
        conn,
        params={"start": "2024-01-01", "end": "2024-06-01"},
        index_col="timestamp",
        parse_dates=["timestamp"],
    )
    df.index = df.index.tz_localize("UTC")

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

The ``TimeSeriesDataset`` constructor validates that the index is monotonically increasing
and that the sample interval is consistent. Pass ``sample_interval`` explicitly so that
gap detection works correctly downstream.

From InfluxDB
^^^^^^^^^^^^^

InfluxDB returns data in a format that maps naturally to a time-indexed DataFrame:

.. code-block:: python

    from influxdb_client import InfluxDBClient
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    client = InfluxDBClient(url="http://influx.example.com:8086", token="<token>", org="energy")
    query_api = client.query_api()

    tables = query_api.query_data_frame("""
        from(bucket: "grid_measurements")
          |> range(start: 2024-01-01T00:00:00Z, stop: 2024-06-01T00:00:00Z)
          |> filter(fn: (r) => r["_measurement"] == "substation_42")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """)

    df = tables.set_index("_time")[["load", "temperature", "wind_speed"]]
    df.index.name = "timestamp"

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

From S3
^^^^^^^

OpenSTEF's ``openstef-beam`` package includes an ``S3BenchmarkStorage`` class for
persisting benchmark artefacts, but for raw time series data the simplest approach is to
read Parquet or CSV files directly:

.. code-block:: python

    import boto3
    import pandas as pd
    from io import BytesIO
    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket="energy-data", Key="measurements/substation_42/2024.parquet")
    df = pd.read_parquet(BytesIO(obj["Body"].read()))

    df.index = pd.to_datetime(df.index, utc=True)
    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

For large datasets spread across many S3 objects, consider using ``pandas`` with
``s3fs`` or Apache Beam (see the ``openstef-beam`` package) to parallelise the reads
before constructing a single ``TimeSeriesDataset``.

From Databricks
^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, convert a Spark DataFrame to pandas
before handing it to OpenSTEF:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    spark_df = spark.table("energy.measurements").filter(
        "grid_point = 'substation_42' AND timestamp BETWEEN '2024-01-01' AND '2024-06-01'"
    )

    df = spark_df.toPandas().set_index("timestamp")
    df.index = pd.to_datetime(df.index, utc=True).sort_values()

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   For very large Databricks tables, apply time-range and column filters in Spark
   before calling ``toPandas()``. OpenSTEF models typically need weeks to months of
   history, not years.

---

Validating Input Data
---------------------

OpenSTEF provides three built-in validation transforms in
``openstef_models.transforms.validation`` that should be applied before training or
inference.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )
    from openstef_core.datasets import TimeSeriesDataset

    # Configure thresholds
    completeness = CompletenessChecker(min_completeness=0.85)
    flatline = FlatlineChecker(max_flatline_length=4)  # max consecutive identical values
    consistency = InputConsistencyChecker()

    # Fit consistency checker on training data so it knows expected columns
    consistency.fit(training_dataset)

    # Apply to new data before inference
    dataset = completeness.transform(dataset)
    dataset = flatline.transform(dataset)
    dataset = consistency.transform(dataset)  # warns and drops unexpected columns

``CompletenessChecker`` raises ``TimeSeriesValidationError`` if too many values are
missing. ``FlatlineChecker`` flags suspiciously constant stretches that often indicate
a stuck sensor. ``InputConsistencyChecker`` ensures that the columns seen at inference
time match those seen during training, logging warnings for extras and raising an error
for missing required features.

You can also validate structural requirements directly using the lower-level utilities in
``openstef_core.datasets.validation``:

.. code-block:: python

    from openstef_core.datasets.validation import validate_required_columns

    validate_required_columns(df, required_columns=["load", "temperature", "wind_speed"])

This raises ``MissingColumnsError`` immediately if any required column is absent, giving
a clear error message before the data enters the pipeline.

---

Handling Missing Data
---------------------

OpenSTEF does not silently impute missing values by default. The recommended approach is
to handle gaps explicitly before constructing a ``TimeSeriesDataset``:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from datetime import timedelta

    # Reindex to a complete 15-minute grid, exposing all gaps as NaN
    full_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="15min",
        tz="UTC",
    )
    df = df.reindex(full_index)

    # Short gaps (up to 1 hour): linear interpolation
    df["load"] = df["load"].interpolate(method="time", limit=4)

    # Longer gaps: fill with a seasonal naive value (same time, previous week)
    df["load"] = df["load"].fillna(df["load"].shift(7 * 24 * 4))

    # Drop rows that are still NaN after filling
    df = df.dropna(subset=["load"])

    dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   The ``limit`` parameter in ``interpolate`` controls how many consecutive NaN values
   are filled. Setting it to ``4`` means gaps up to one hour (4 × 15 min) are
   interpolated; longer gaps remain as NaN and are handled by the seasonal fallback.

For weather features (temperature, irradiance, wind speed) that come from a forecast
provider, missing values are typically best filled by re-fetching from the source rather
than interpolating, since these features have strong diurnal patterns that linear
interpolation distorts.

---

Writing Forecasts Back to Storage
----------------------------------

After calling ``model.predict()``, you receive a ``ForecastDataset``. Its ``to_pandas()``
method returns a standard DataFrame that you can write to any backend.

.. code-block:: python

    from openstef_core.datasets.validated_datasets import ForecastDataset

    forecast: ForecastDataset = model.predict(dataset)
    forecast_df = forecast.to_pandas()

    # forecast_df has a DatetimeIndex and columns for each quantile,
    # e.g. "quantile_0.05", "quantile_0.50", "quantile_0.95"

**To PostgreSQL:**

.. code-block:: python

    from sqlalchemy import create_engine

    engine = create_engine("postgresql+psycopg2://writer:<password>@db.example.com/energy")
    forecast_df["grid_point"] = "substation_42"
    forecast_df.to_sql("forecasts", engine, if_exists="append", index=True, index_label="timestamp")

**To InfluxDB:**

.. code-block:: python

    from influxdb_client import InfluxDBClient, WriteOptions

    with InfluxDBClient(url="http://influx.example.com:8086", token="<token>", org="energy") as client:
        write_api = client.write_api(write_options=WriteOptions(batch_size=500))
        write_api.write(
            bucket="forecasts",
            record=forecast_df,
            data_frame_measurement_name="substation_42",
            data_frame_tag_columns=["grid_point"],
        )

**To S3 (Parquet):**

.. code-block:: python

    import boto3
    from io import BytesIO

    buffer = BytesIO()
    forecast_df.to_parquet(buffer)
    buffer.seek(0)

    s3 = boto3.client("s3")
    s3.put_object(
        Bucket="energy-forecasts",
        Key="substation_42/2024-06-01.parquet",
        Body=buffer.read(),
    )

---

Capturing Intermediate Data with Callbacks
-------------------------------------------

The ``DataSaveCallback`` in ``openstef_models.workflows.callbacks`` lets you intercept
and persist intermediate pipeline outputs — useful for debugging feature engineering or
auditing preprocessing steps — without modifying the pipeline itself:

.. code-block:: python

    from openstef_models.workflows.callbacks import DataSaveCallback
    from pathlib import Path

    save_cb = DataSaveCallback(output_dir=Path("/tmp/pipeline_debug"))

    # Pass the callback when constructing or running the workflow
    model.fit(training_dataset, callbacks=[save_cb])

Each stage that supports callbacks will write its output to the specified directory,
named by stage. Swap the ``output_dir`` for an S3-backed path or a database writer to
route these artefacts to your preferred storage.

---

Building a Custom Data Source
------------------------------

If your data lives in a proprietary system, the integration point is simply a function
that returns a ``TimeSeriesDataset``. There is no base class to implement:

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset


    def load_from_scada(
        grid_point: str,
        start: datetime,
        end: datetime,
        sample_interval: timedelta = timedelta(minutes=15),
    ) -> TimeSeriesDataset:
        """Fetch measurements from the internal SCADA API."""
        raw = _scada_client.fetch(grid_point, start, end)  # returns list[dict]
        df = pd.DataFrame(raw).set_index("timestamp")
        df.index = pd.to_datetime(df.index, utc=True)
        df = df.sort_index()
        return TimeSeriesDataset(data=df, sample_interval=sample_interval)

Keep the function narrow: fetch, reshape, and return. Validation, gap-filling, and
feature engineering belong in separate steps so they can be tested and reused
independently.

---

.. note::

   For patterns around scheduling these data pipelines in production (cron, Airflow,
   Databricks Jobs), see :doc:`deployment`. For complete worked examples that combine
   data loading with model training and evaluation, see :doc:`use_cases`.