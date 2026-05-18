Datasets
========

This guide covers OpenSTEF's dataset classes—``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``—which provide structured containers for time series data used throughout the forecasting pipeline. You'll learn how to create, filter, split, and persist datasets for training and evaluation.

Overview
--------

OpenSTEF provides two core dataset classes in ``openstef_core.datasets``:

- **TimeSeriesDataset** — A regular time series with a fixed sample interval, suitable for single-version data (e.g., historical measurements).
- **VersionedTimeSeriesDataset** — A composition of multiple ``TimeSeriesDataset`` parts that tracks data availability over time, enabling realistic backtesting without lookahead bias.

Both classes share a common interface providing access to feature metadata, temporal properties, filtering, and version selection.

.. mermaid:: /diagrams/user_guide/guides/datasets_diagram_1.mmd

TimeSeriesDataset
-----------------

A ``TimeSeriesDataset`` wraps a pandas DataFrame with a ``DatetimeIndex`` and enforces a fixed sample interval. It provides feature access, filtering, and serialization.

Creating a TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   # Create a DataFrame with a DatetimeIndex
   data = pd.DataFrame(
       {
           "load": [100.0, 120.0, 115.0, 130.0],
           "temperature": [20.0, 22.0, 21.5, 23.0],
       },
       index=pd.DatetimeIndex(
           [
               datetime(2025, 1, 1, 10, 0),
               datetime(2025, 1, 1, 10, 15),
               datetime(2025, 1, 1, 10, 30),
               datetime(2025, 1, 1, 10, 45),
           ],
           name="timestamp",
       ),
   )

   dataset = TimeSeriesDataset(data=data, sample_interval=timedelta(minutes=15))

Key Properties
^^^^^^^^^^^^^^

.. code-block:: python

   # Access the datetime index
   dataset.index
   # DatetimeIndex(['2025-01-01 10:00:00', ...], name='timestamp')

   # Get the sample interval
   dataset.sample_interval
   # timedelta(seconds=900)

   # List available features
   dataset.feature_names
   # ['load', 'temperature']

   # Check if dataset tracks versioning
   dataset.is_versioned
   # False

Filtering Data
^^^^^^^^^^^^^^

All filter methods return new dataset instances (immutable pattern):

.. code-block:: python

   from datetime import datetime

   # Filter by time range (inclusive start, exclusive end)
   subset = dataset.filter_by_range(
       start=datetime(2025, 1, 1, 10, 0),
       end=datetime(2025, 1, 1, 10, 30),
   )

   # Select specific features
   temp_only = dataset.select_features(["temperature"])

Persistence
^^^^^^^^^^^

Datasets can be saved and loaded from Parquet files:

.. code-block:: python

   # Save to parquet
   dataset.to_parquet("my_dataset.parquet")

   # Load from parquet
   loaded = TimeSeriesDataset.read_parquet(
       "my_dataset.parquet",
       sample_interval=timedelta(minutes=15),
   )

Pandas Interoperability
^^^^^^^^^^^^^^^^^^^^^^^

Convert between datasets and DataFrames when needed:

.. code-block:: python

   # Convert to pandas DataFrame
   df = dataset.to_pandas()

   # Create from pandas DataFrame (metadata stored in df.attrs)
   dataset = TimeSeriesDataset.from_pandas(df, sample_interval=timedelta(minutes=15))

   # Apply a pandas transformation while preserving dataset structure
   cleaned = dataset.pipe_pandas(lambda df: df.dropna())

VersionedTimeSeriesDataset
--------------------------

The ``VersionedTimeSeriesDataset`` tracks *when* data became available, which is critical for realistic backtesting. It solves the O(n²) space complexity problem of concatenating DataFrames with misaligned ``(timestamp, available_at)`` pairs by using lazy composition.

Creating a VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**From multiple data parts:**

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   # Weather forecast data with availability tracking
   weather_data = pd.DataFrame(
       {
           "temperature": [20.5, 21.0],
           "available_at": [
               datetime(2025, 1, 1, 8, 0),
               datetime(2025, 1, 1, 8, 0),
           ],
       },
       index=pd.DatetimeIndex(
           [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 11, 0)],
           name="timestamp",
       ),
   )

   weather_part = TimeSeriesDataset(weather_data, timedelta(hours=1))

   # Combine parts into a versioned dataset
   dataset = VersionedTimeSeriesDataset([weather_part])
   dataset.is_versioned  # True

**From a single DataFrame (convenience method):**

.. code-block:: python

   data = pd.DataFrame(
       {
           "available_at": [
               datetime(2025, 1, 1, 10, 5),
               datetime(2025, 1, 1, 10, 20),
           ],
           "load": [100.0, 120.0],
           "temperature": [20.0, 22.0],
       },
       index=pd.DatetimeIndex(
           [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 10, 15)],
           name="timestamp",
       ),
   )

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       data, timedelta(minutes=15)
   )

Version Selection and Availability Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These methods prevent lookahead bias by ensuring you only use data that was actually available at a given point in time:

.. code-block:: python

   # Filter to data available before a specific time
   available_data = dataset.filter_by_available_before(
       available_before=datetime(2025, 1, 1, 10, 10)
   )

   # Select the latest available version for each timestamp
   # (creates a point-in-time snapshot)
   snapshot = dataset.select_version()

   # Filter by lead time (minimum gap between availability and target time)
   ahead_data = dataset.filter_by_lead_time(lead_time=timedelta(hours=2))

Converting to Horizon-Based Format
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For multi-horizon forecasting, convert a versioned dataset into a format with explicit horizon columns:

.. code-block:: python

   from datetime import timedelta

   horizons = [timedelta(hours=1), timedelta(hours=6), timedelta(hours=24)]
   horizon_dataset = dataset.to_horizons(horizons)

Splitting Data for Training
----------------------------

OpenSTEF provides utilities to split datasets into train, validation, and test sets. The ``DataSplitter`` class handles stratified splitting to maintain representative distributions.

.. code-block:: python

   from openstef_models.utils.splitting import DataSplitter

   splitter = DataSplitter(
       val_fraction=0.15,
       test_fraction=0.15,
   )

   train_data, val_data, test_data = splitter.split_dataset(
       data=dataset,
       target_column="load",
   )

You can also use the lower-level splitting functions directly:

.. code-block:: python

   from openstef_models.utils.splitting import (
       train_val_test_split,
       stratified_train_test_split,
   )

   train, val, test = train_val_test_split(
       dataset=data,
       split_func=lambda ds, fraction: stratified_train_test_split(
           dataset=ds,
           test_fraction=fraction,
           target_column="load",
       ),
       val_fraction=0.15,
       test_fraction=0.15,
   )

.. warning::

   The sum of ``val_fraction`` and ``test_fraction`` must be less than 1.0. A ``ValueError`` is raised otherwise.

Integration with the Forecasting Pipeline
------------------------------------------

Datasets are the primary input to OpenSTEF's training and prediction pipelines. A typical workflow:

1. **Load data** into a ``VersionedTimeSeriesDataset`` from your data source or Parquet files.
2. **Filter** by time range and availability constraints appropriate for your use case.
3. **Split** into train/validation/test sets using ``DataSplitter``.
4. **Pass** the splits to the training pipeline.

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset
   from openstef_models.utils.splitting import DataSplitter

   # Load dataset
   dataset = VersionedTimeSeriesDataset.read_parquet(
       "historical_data.parquet",
       sample_interval=timedelta(minutes=15),
   )

   # Filter to training period
   training_data = dataset.filter_by_range(
       start=datetime(2024, 1, 1),
       end=datetime(2025, 1, 1),
   )

   # Get point-in-time snapshot (prevents lookahead bias)
   snapshot = training_data.select_version()

   # Split for model training
   splitter = DataSplitter(val_fraction=0.15, test_fraction=0.15)
   train, val, test = splitter.split_dataset(snapshot, target_column="load")

.. mermaid:: /diagrams/user_guide/guides/datasets_diagram_2.mmd

Best Practices
--------------

- **Always use** ``select_version()`` before training to prevent lookahead bias—this ensures your model only sees data that was realistically available.
- **Compose data parts** with disjoint feature sets. All parts in a ``VersionedTimeSeriesDataset`` must share the same sample interval.
- **Use Parquet** for persistence—it preserves index types and is efficient for large time series.
- **Prefer** ``pipe_pandas()`` over manual DataFrame extraction when applying transformations, as it preserves dataset metadata.
- **Filter early** to reduce memory usage—apply ``filter_by_range()`` before expensive operations.

Related Topics
--------------

- For feature engineering applied to datasets, see :doc:`features`
- For model training workflows that consume datasets, see :doc:`training`
- For backtesting with versioned data, see :doc:`backtesting`