Data Integration
================

OpenSTEF is a library, not a data platform — it does not prescribe where your data lives or how it moves. Instead, it works with standard pandas DataFrames and its own ``TimeSeriesDataset`` wrapper, which means you can read from any source you already use and write forecasts back to any destination. This page covers practical patterns for doing exactly that: loading time series data from common storage systems, constructing the dataset objects OpenSTEF expects, handling gaps and outliers before they reach the model, and persisting forecast results.

For production scheduling and orchestration of these pipelines, see :doc:`deployment`. For end-to-end worked examples that combine data integration with model training, see :doc:`use_cases`.

.. contents:: On this page
   :local:
   :depth: 2

What OpenSTEF Expects
---------------------

Every training and prediction call in OpenSTEF takes a ``TimeSeriesDataset``. This is a thin, validated wrapper around a pandas DataFrame with a ``DatetimeIndex``. The only hard requirement is that the DataFrame has a ``load`` column (the target) and that the index is a timezone-aware datetime series at a consistent frequency. Feature columns — weather variables, calendar flags, lagged values — sit alongside ``load`` in the same DataFrame.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Minimal viable dataset: one target column, datetime index
   df = pd.DataFrame(
       {
           "load": [142.3, 138.7, 145.1, 150.4],
           "temperature": [12.1, 11.8, 12.5, 13.0],
           "wind_speed": [4.2, 5.1, 4.8, 3.9],
       },
       index=pd.date_range("2024-01-01 00:00", periods=4, freq="15min", tz="UTC"),
   )

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

The ``sample_interval`` parameter tells OpenSTEF the expected cadence of your data. Mismatches between the declared interval and the actual index frequency will surface as validation errors early, before any model code runs.

Reading from Common Sources
---------------------------

The examples below show how to load data from typical storage backends and convert the result into a ``TimeSeriesDataset``. The conversion step is always the same; only the loading differs.

**[DIAGRAM: Data flow from source systems (S3/Parquet, InfluxDB, PostgreSQL, Databricks) through a common pandas DataFrame stage into TimeSeriesDataset, then into OpenSTEF training and prediction pipelines]**

Amazon S3 / Parquet
^^^^^^^^^^^^^^^^^^^

Parquet on S3 is a natural fit because ``TimeSeriesDataset`` has a ``from_parquet`` class method that preserves metadata (``sample_interval``, column roles) written by a previous ``to_parquet`` call.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Reading a raw Parquet file written by an external system
   df = pd.read_parquet("s3://<bucket>/energy/substation_42/2024.parquet")

   # Ensure the index is a timezone-aware DatetimeIndex
   if df.index.tz is None:
       df.index = df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

If the Parquet file was previously saved by OpenSTEF itself (via ``dataset.to_parquet(...)``), use the class method to recover all metadata automatically:

.. code-block:: python

   # Round-trip: metadata (sample_interval, horizon column, etc.) is restored
   dataset = TimeSeriesDataset.from_parquet(
       path="s3://<bucket>/energy/substation_42/2024.parquet"
   )

.. note::

   ``s3://`` URIs work transparently when ``s3fs`` is installed in your environment. For authenticated access, configure credentials via environment variables (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``) or an IAM role before calling ``read_parquet``.

InfluxDB
^^^^^^^^

InfluxDB returns query results as DataFrames when using the ``influxdb-client`` library with ``query_api.query_data_frame()``. The main task is aligning the column names and index to OpenSTEF's conventions.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from influxdb_client import InfluxDBClient
   from openstef_core.datasets import TimeSeriesDataset

   client = InfluxDBClient(url="http://influxdb:8086", token="<token>", org="<org>")
   query_api = client.query_api()

   flux_query = """
   from(bucket: "energy")
     |> range(start: -90d)
     |> filter(fn: (r) => r["_measurement"] == "substation_load")
     |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
   """

   df = query_api.query_data_frame(flux_query)

   # InfluxDB returns _time as the index; rename to match OpenSTEF conventions
   df = df.rename(columns={"_time": "timestamp", "load_mw": "load"})
   df = df.set_index("timestamp").sort_index()

   # Ensure UTC timezone
   if df.index.tz is None:
       df.index = df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(data=df[["load", "temperature"]], sample_interval=timedelta(minutes=15))

PostgreSQL / TimescaleDB
^^^^^^^^^^^^^^^^^^^^^^^^

SQL databases are straightforward via ``pandas.read_sql``. TimescaleDB hypertables behave identically to regular PostgreSQL tables from the client's perspective.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from sqlalchemy import create_engine
   from openstef_core.datasets import TimeSeriesDataset

   engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")

   query = """
       SELECT timestamp, load_mw AS load, temperature, wind_speed
       FROM substation_measurements
       WHERE timestamp >= NOW() - INTERVAL '90 days'
       ORDER BY timestamp
   """

   df = pd.read_sql(query, engine, index_col="timestamp", parse_dates=["timestamp"])

   if df.index.tz is None:
       df.index = df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

Databricks / Delta Lake
^^^^^^^^^^^^^^^^^^^^^^^

When running inside a Databricks notebook or job, you can convert a Spark DataFrame to pandas and then wrap it as a ``TimeSeriesDataset``. For large datasets, push filtering and aggregation into Spark before converting.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # spark is the SparkSession available in Databricks notebooks
   spark_df = spark.table("energy.substation_measurements").filter(
       "timestamp >= date_sub(current_date(), 90)"
   )

   df = spark_df.toPandas()
   df = df.set_index("timestamp").sort_index()

   if df.index.tz is None:
       df.index = df.index.tz_localize("UTC")

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

.. note::

   ``toPandas()`` collects all data to the driver. For datasets spanning multiple years or many substations, consider partitioning by substation and processing each in a separate Databricks job rather than collecting everything at once.

Handling Missing Data
---------------------

Real-world energy time series always contain gaps. OpenSTEF's training pipeline will raise ``InsufficientlyCompleteError`` if the data is too sparse, and it silently drops rows where the target (``load``) is ``NaN`` before fitting. Understanding this behaviour lets you decide how much imputation to do upstream versus letting the library handle it.

Checking Completeness Before Training
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``CompletenessChecker`` as an explicit guard in your pipeline. It raises ``InsufficientlyCompleteError`` if the fraction of non-null values falls below a configurable threshold.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms.completeness import CompletenessChecker

   df = pd.DataFrame(
       {
           "load": [100.0, np.nan, np.nan, 105.0],
           "temperature": [12.0, np.nan, 13.0, 13.5],
       },
       index=pd.date_range("2024-01-01", periods=4, freq="15min", tz="UTC"),
   )

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

   # Raises InsufficientlyCompleteError if completeness < threshold (default 0.5)
   checker = CompletenessChecker(completeness_threshold=0.7)
   try:
       checker.transform(dataset)
   except Exception as e:
       print(f"Data quality gate failed: {e}")
       # Handle: skip this substation, alert, or fall back to a simpler model

Imputing Gaps Upstream
^^^^^^^^^^^^^^^^^^^^^^

For feature columns (weather, prices), forward-filling or interpolation before constructing the dataset is often appropriate. For the ``load`` target, be conservative — imputed targets can silently degrade model quality.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Reindex to a complete time grid to make gaps explicit
   full_index = pd.date_range("2024-01-01", "2024-04-01", freq="15min", tz="UTC")
   df = df.reindex(full_index)

   # Impute feature columns only; leave load NaN where missing
   feature_cols = ["temperature", "wind_speed", "radiation"]
   df[feature_cols] = df[feature_cols].interpolate(method="time", limit=4)

   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))
   # OpenSTEF will drop NaN load rows during training automatically

Handling Outliers
^^^^^^^^^^^^^^^^^

``OutlierHandler`` is a preprocessing transform that learns feature bounds during training and clips or nullifies out-of-range values at inference time. It is included by default in the ensemble workflow preprocessing chain, but you can also apply it manually.

.. code-block:: python

   from openstef_models.transforms.general.outlier_handler import OutlierHandler
   from openstef_core.transforms.feature_selection import Exclude

   # Clip all features except the target to learned [min, max] bounds
   handler = OutlierHandler(
       selection=Exclude("load"),
       mode="standard",   # uses mean ± N*std bounds
       action="clip",
   )

   # Fit on training data, then apply to inference data
   handler.fit(training_dataset)
   clean_inference_dataset = handler.transform(inference_dataset)

Data Validation Utilities
--------------------------

OpenSTEF provides lightweight validation helpers in ``openstef_core.datasets.validation`` that you can call at the boundary between your data loading code and the library.

.. code-block:: python

   from openstef_core.datasets.validation import validate_required_columns

   # Fail fast if expected columns are missing before constructing the dataset
   validate_required_columns(
       df,
       required_columns=["load", "temperature", "wind_speed"],
   )
   # Raises MissingColumnsError with a clear message listing the absent columns

This is particularly useful when your data pipeline has multiple upstream sources that are joined together — validating the merged DataFrame before passing it to OpenSTEF surfaces schema drift early.

Writing Forecasts Back to Storage
----------------------------------

After calling ``workflow.predict()``, you receive a ``ForecastDataset``. Its underlying DataFrame is accessible via ``.data`` and can be written to any destination using standard pandas or Spark APIs.

**[DIAGRAM: ForecastDataset output flowing to storage destinations: Parquet/S3, PostgreSQL, InfluxDB, Delta Lake]**

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   forecast: ForecastDataset = workflow.predict(inference_dataset)

   # Access the underlying DataFrame
   df_out = forecast.data
   # Columns include quantile forecasts (e.g., "q0.1", "q0.5", "q0.9") and "load"

   # --- Write to Parquet on S3 ---
   df_out.to_parquet("s3://<bucket>/forecasts/substation_42/latest.parquet")

   # --- Write to PostgreSQL ---
   from sqlalchemy import create_engine
   engine = create_engine("postgresql+psycopg2://user:password@host:5432/energy_db")
   df_out.to_sql("forecasts", engine, if_exists="append", index=True)

   # --- Write to InfluxDB ---
   from influxdb_client import InfluxDBClient, WriteOptions
   with InfluxDBClient(url="http://influxdb:8086", token="<token>", org="<org>") as client:
       write_api = client.write_api(write_options=WriteOptions(batch_size=500))
       write_api.write(
           bucket="energy_forecasts",
           record=df_out,
           data_frame_measurement_name="substation_load_forecast",
       )

Using the DataSaveCallback for Debugging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

During development, ``DataSaveCallback`` is the most convenient way to persist intermediate datasets without modifying your pipeline code. It hooks into the workflow lifecycle and writes training data, prepared inputs, forecasts, and feature contributions to Parquet files automatically.

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.callbacks.data_save import DataSaveCallback
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   callback = DataSaveCallback(
       cache_dir=Path("/tmp/openstef_debug"),
       save_forecast=True,
       save_prepared_data=True,
       save_contributions=True,
   )

   workflow = CustomForecastingWorkflow(model=model, callbacks=[callback])
   workflow.fit(training_dataset)
   workflow.predict(inference_dataset)
   # Parquet files are written to /tmp/openstef_debug/

This is particularly useful when diagnosing unexpected forecast values: the ``contrib_<run>_predict.parquet`` file shows the per-feature contribution to each prediction, making it easy to identify which input drove an anomalous result.

Building a Custom Source Adapter
----------------------------------

If your data source does not fit the patterns above, the integration point is always the same: produce a pandas DataFrame with a timezone-aware ``DatetimeIndex`` and the correct column names, then wrap it in ``TimeSeriesDataset``. A clean pattern is to encapsulate the source-specific logic in a loader class:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validation import validate_required_columns


   class SubstationDataLoader:
       """Loads substation measurements from a custom internal API."""

       def __init__(self, api_client, sample_interval: timedelta = timedelta(minutes=15)):
           self._client = api_client
           self._sample_interval = sample_interval

       def load(self, substation_id: str, lookback_days: int = 90) -> TimeSeriesDataset:
           raw = self._client.get_measurements(substation_id, days=lookback_days)

           df = pd.DataFrame(raw).set_index("timestamp")
           df.index = pd.to_datetime(df.index, utc=True)
           df = df.sort_index().rename(columns={"power_mw": "load"})

           # Reindex to a complete grid so gaps are explicit NaNs
           full_index = pd.date_range(
               df.index.min(), df.index.max(),
               freq=self._sample_interval, tz="UTC"
           )
           df = df.reindex(full_index)

           validate_required_columns(df, required_columns=["load"])

           return TimeSeriesDataset(data=df, sample_interval=self._sample_interval)

This pattern keeps all source-specific logic isolated, makes the validation boundary explicit, and produces a ``TimeSeriesDataset`` that any OpenSTEF workflow can consume without modification.

.. note::

   OpenSTEF does not impose any particular scheduler or orchestration framework. These loader classes work equally well called from a cron job, an Airflow task, a Databricks notebook, or a Kubernetes CronJob. See :doc:`deployment` for production scheduling patterns.

Summary
-------

The key points for data integration with OpenSTEF:

- The integration boundary is always a ``TimeSeriesDataset`` wrapping a pandas DataFrame with a timezone-aware ``DatetimeIndex`` and a ``load`` column.
- Source-specific loading (S3, InfluxDB, PostgreSQL, Databricks) is handled by standard Python libraries; OpenSTEF takes over once you have a DataFrame.
- Use ``validate_required_columns`` and ``CompletenessChecker`` as explicit quality gates before passing data to the model.
- ``OutlierHandler`` handles feature outliers at inference time without requiring upstream data cleaning.
- Forecast results are plain DataFrames and can be written to any destination with standard pandas I/O.
- ``DataSaveCallback`` provides zero-code persistence of intermediate datasets for debugging and backtesting.