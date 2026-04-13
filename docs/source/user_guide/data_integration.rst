Data Integration
================

OpenSTEF is a library that processes time series data through its own dataset abstractions — it does not ship connectors to specific storage backends. This page explains how to bridge your existing data infrastructure (S3, Databricks, InfluxDB, PostgreSQL, or any other source) to the ``TimeSeriesDataset`` and ``ForecastInputDataset`` types that OpenSTEF expects, and how to write forecast results back to storage once a workflow completes.

.. note::

   This page covers data plumbing. For how forecasting workflows themselves are structured, see :doc:`use_cases`. For running these pipelines in production, see :doc:`deployment`.

The Core Contract
-----------------

Every OpenSTEF workflow operates on ``TimeSeriesDataset`` (or its subclass ``ForecastInputDataset``). Both wrap a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforce a small set of invariants:

- The index must be timezone-aware and sorted in ascending order.
- The data frequency must match the declared ``sample_interval`` (default: 15 minutes).
- A ``load`` column must be present in ``ForecastInputDataset``.

Your integration layer has one job: produce a DataFrame that satisfies these constraints, then hand it to OpenSTEF. Everything else — feature engineering, model training, forecasting — is handled by the library.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   # Minimal example: wrap any DataFrame you have loaded
   df = pd.DataFrame(
       {"load": [100.0, 102.5, 98.3]},
       index=pd.to_datetime(
           ["2024-01-01 00:00", "2024-01-01 00:15", "2024-01-01 00:30"],
           utc=True,
       ),
   )

   dataset = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

If the DataFrame violates any constraint, OpenSTEF raises a ``MissingColumnsError``, ``InvalidColumnTypeError``, or ``ValueError`` immediately — before any model code runs. This fail-fast behaviour makes it straightforward to debug integration issues.

Reading from Storage Backends
------------------------------

The pattern is always the same: use your preferred library to read data into a ``pandas.DataFrame``, normalise the index and column names, then construct a ``TimeSeriesDataset``.

**Amazon S3 / Parquet**

Parquet on S3 is a natural fit because ``TimeSeriesDataset`` exposes a ``to_parquet`` method and pandas reads Parquet natively via ``pyarrow`` or ``fastparquet``.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Read one or more partitioned Parquet files from S3
   df = pd.read_parquet(
       "s3://my-bucket/energy/substation_42/",
       storage_options={"anon": False},  # uses your AWS credentials
   )

   # Ensure the index is a tz-aware DatetimeIndex
   df.index = pd.to_datetime(df.index, utc=True)
   df = df.sort_index()

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
   )

**Databricks / Delta Lake**

When running inside a Databricks notebook or job, read a Delta table via the Spark session and convert to pandas before handing off to OpenSTEF.

.. code-block:: python

   from datetime import timedelta, timezone
   import pandas as pd
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   # spark is available in Databricks notebooks automatically
   spark_df = spark.table("energy.measurements.substation_42")

   df = spark_df.toPandas()
   df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
   df = df.set_index("timestamp").sort_index()

   dataset = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

.. note::

   For large tables, push time-range filters into Spark before calling ``toPandas()`` to avoid materialising unnecessary data. OpenSTEF only needs the training window and the forecast horizon period.

**InfluxDB**

Query InfluxDB using the official ``influxdb-client`` library and pivot the result into a wide DataFrame.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   client = InfluxDBClient(url="http://influxdb:8086", token="...", org="my-org")
   query_api = client.query_api()

   flux_query = """
   from(bucket: "energy")
     |> range(start: -90d)
     |> filter(fn: (r) => r["_measurement"] == "substation" and r["id"] == "42")
     |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
   """

   df = query_api.query_data_frame(flux_query)
   df = df.set_index("_time")[["load", "wind_speed", "temperature"]]
   df.index = df.index.tz_convert("UTC")
   df = df.sort_index()

   dataset = ForecastInputDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

**PostgreSQL**

Use ``pandas.read_sql`` with a SQLAlchemy engine. The query should return one row per timestamp.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   engine = create_engine("postgresql+psycopg2://user:pass@host/dbname")

   df = pd.read_sql(
       """
       SELECT timestamp, load, wind_speed, temperature
       FROM measurements
       WHERE substation_id = 42
         AND timestamp >= NOW() - INTERVAL '90 days'
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

Handling Missing Data
---------------------

Real-world measurement data is rarely gap-free. OpenSTEF's ``TimeSeriesDataset`` validates that the index frequency matches ``sample_interval``, so gaps in the raw data will raise a ``ValueError`` before any model runs. The recommended approach is to reindex to a complete range and decide how to fill gaps before constructing the dataset.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   # Assume df has a tz-aware DatetimeIndex but with gaps
   full_range = pd.date_range(
       start=df.index.min(),
       end=df.index.max(),
       freq="15min",
       tz="UTC",
   )

   df = df.reindex(full_range)

   # Forward-fill short gaps (e.g. up to 1 hour of missing readings)
   df["load"] = df["load"].ffill(limit=4)

   # For weather features, linear interpolation is often more appropriate
   df[["wind_speed", "temperature"]] = df[["wind_speed", "temperature"]].interpolate(
       method="time", limit=8
   )

   # Rows that are still NaN after filling will cause issues downstream —
   # drop or flag them depending on your use case
   df = df.dropna(subset=["load"])

   dataset = ForecastInputDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   OpenSTEF's transform pipeline (``InputConsistencyChecker``, ``DropEmptyColumns``) will also drop feature columns that contain *only* missing values and log a warning. This is a safety net, not a substitute for cleaning your data before ingestion.

Data Validation
---------------

OpenSTEF provides ``validate_required_columns`` and related utilities in ``openstef_core.datasets.validation`` that you can call in your own integration code to give early, descriptive errors.

.. code-block:: python

   from openstef_core.datasets.validation import (
       validate_required_columns,
       validate_disjoint_columns,
   )
   from openstef_core.exceptions import MissingColumnsError

   REQUIRED = ["load", "wind_speed", "temperature"]

   try:
       validate_required_columns(df, required_columns=REQUIRED)
   except MissingColumnsError as exc:
       # exc.missing_columns lists exactly what is absent
       raise RuntimeError(
           f"Source data is missing columns: {exc.missing_columns}"
       ) from exc

When combining feature DataFrames from multiple sources (for example, measurements from InfluxDB and weather forecasts from S3), use ``validate_disjoint_columns`` to catch accidental column name collisions before the join:

.. code-block:: python

   from openstef_core.datasets.validation import validate_disjoint_columns

   # Raises TimeSeriesValidationError if any feature name appears in both datasets
   all_features = validate_disjoint_columns([measurements_dataset, weather_dataset])

Writing Forecasts Back to Storage
-----------------------------------

After a workflow produces a ``ForecastDataset``, its underlying DataFrame is accessible via ``.data`` and can be written to any storage backend using standard pandas I/O.

**Using the built-in DataSaveCallback**

For Parquet-based storage, the built-in ``DataSaveCallback`` is the simplest option. Attach it to a workflow and it will automatically persist training data, prepared inputs, and forecast outputs to a local or mounted directory:

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback

   callback = DataSaveCallback(
       cache_dir=Path("/mnt/forecasts/substation_42"),
       save_training_data=False,   # skip raw training data
       save_prepared_data=False,
       save_predict_data=False,
       save_forecast=True,         # only persist the final forecast
       save_contributions=False,
   )

   # Pass the callback when constructing your workflow
   workflow = CustomForecastingWorkflow(..., callbacks=[callback])

Files are named using the workflow's ``run_name``, e.g. ``debug_morning_run_forecast.parquet``.

**Writing to a database or object store**

For destinations other than Parquet, extract the DataFrame from the ``ForecastDataset`` and use the appropriate writer:

.. code-block:: python

   # After workflow.predict(...) returns a ForecastDataset
   forecast_df = forecast_result.data

   # Write to PostgreSQL
   forecast_df.to_sql(
       "forecasts",
       con=engine,
       if_exists="append",
       index=True,
       index_label="timestamp",
   )

   # Write to S3 as Parquet
   forecast_df.to_parquet(
       "s3://my-bucket/forecasts/substation_42/latest.parquet",
       storage_options={"anon": False},
   )

   # Write to InfluxDB (using influxdb-client write API)
   write_api.write(
       bucket="energy",
       record=forecast_df,
       data_frame_measurement_name="forecast",
       data_frame_tag_columns=["substation_id"],
   )

Building a Reusable Pipeline
-----------------------------

In practice, the read → validate → forecast → write steps are best encapsulated in a thin wrapper function or class that your scheduler or orchestrator calls. The following sketch shows the structure of a self-contained pipeline for a single substation:

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path
   import pandas as pd
   from sqlalchemy import create_engine
   from openstef_core.datasets.validated_datasets import ForecastInputDataset
   from openstef_core.datasets.validation import validate_required_columns
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback

   REQUIRED_COLUMNS = ["load", "wind_speed", "temperature"]
   SAMPLE_INTERVAL = timedelta(minutes=15)


   def run_forecast_pipeline(substation_id: int, workflow, engine, output_dir: Path):
       # 1. Read
       df = pd.read_sql(
           f"SELECT * FROM measurements WHERE substation_id = {substation_id} "
           "ORDER BY timestamp",
           con=engine,
           index_col="timestamp",
           parse_dates={"timestamp": {"utc": True}},
       )

       # 2. Validate
       validate_required_columns(df, REQUIRED_COLUMNS)

       # 3. Fill gaps
       full_range = pd.date_range(df.index.min(), df.index.max(), freq="15min", tz="UTC")
       df = df.reindex(full_range).ffill(limit=4).dropna(subset=["load"])

       # 4. Wrap in OpenSTEF dataset
       dataset = ForecastInputDataset(data=df, sample_interval=SAMPLE_INTERVAL)

       # 5. Forecast (workflow already trained)
       forecast = workflow.predict(dataset)

       # 6. Write back
       forecast.data.to_sql(
           "forecasts", con=engine, if_exists="append",
           index=True, index_label="timestamp",
       )

This pattern keeps integration logic separate from model logic, making it straightforward to swap out the storage backend without touching the forecasting code.

.. note::

   For scheduling and containerising this kind of pipeline, see :doc:`deployment`. For logging within the pipeline, see :doc:`logging`.