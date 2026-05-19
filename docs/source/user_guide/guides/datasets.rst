Datasets
========

This guide covers OpenSTEF's dataset classes—``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``—which provide structured containers for time series data used throughout the forecasting pipeline. You'll learn how to create, filter, split, and compose datasets for training and prediction workflows.

Overview
--------

OpenSTEF provides two core dataset classes:

- **TimeSeriesDataset**: A regular time series with a fixed sample interval, a datetime index, and named features. This is the fundamental data container used by models.
- **VersionedTimeSeriesDataset**: A composition of one or more ``TimeSeriesDataset`` instances that tracks *when* data became available. This enables realistic backtesting without lookahead bias.

Both classes live in the ``openstef_core.datasets`` package and share a common interface for filtering, serialization, and pipeline integration.

.. mermaid:: /diagrams/user_guide/guides/datasets_diagram_1.mmd

Creating a TimeSeriesDataset
----------------------------

A ``TimeSeriesDataset`` wraps a pandas DataFrame with a ``DatetimeIndex`` and a known sample interval:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

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

   print(dataset.feature_names)   # ['load', 'temperature']
   print(dataset.sample_interval) # 0:15:00
   print(dataset.is_versioned)    # False

Key properties:

- ``index`` — the ``DatetimeIndex`` of all timestamps
- ``sample_interval`` — the fixed interval between consecutive points
- ``feature_names`` — list of feature column names (excludes metadata columns)
- ``is_versioned`` — whether the dataset tracks data availability

Creating a VersionedTimeSeriesDataset
-------------------------------------

When data arrives with delays or gets revised over time, use ``VersionedTimeSeriesDataset`` to track availability via an ``available_at`` column:

.. code-block:: python

   from openstef_core.datasets.versioned_timeseries_dataset import VersionedTimeSeriesDataset

   weather_data = pd.DataFrame(
       {
           "temperature": [20.5, 21.0],
           "available_at": [
               datetime(2025, 1, 1, 16, 0),
               datetime(2025, 1, 1, 17, 0),
           ],
       },
       index=pd.DatetimeIndex(
           [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 11, 0)],
           name="timestamp",
       ),
   )

   weather_part = TimeSeriesDataset(
       data=weather_data, sample_interval=timedelta(hours=1), available_at_column="available_at"
   )

   dataset = VersionedTimeSeriesDataset(data_parts=[weather_part])
   print(dataset.is_versioned)  # True

For simpler cases, use the convenience constructor:

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

   dataset = VersionedTimeSeriesDataset.from_dataframe(data, timedelta(minutes=15))

.. note::

   All data parts in a ``VersionedTimeSeriesDataset`` must have identical sample intervals and disjoint feature sets. This lazy composition avoids O(n²) space complexity from concatenating DataFrames with misaligned ``(timestamp, available_at)`` pairs.

Filtering Datasets
------------------

Both dataset classes support a rich filtering interface that returns new instances (immutable pattern):

Filtering by time range
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Include only data within [start, end)
   subset = dataset.filter_by_range(
       start=datetime(2025, 1, 1, 10, 0),
       end=datetime(2025, 1, 1, 11, 0),
   )

Filtering by availability
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Only data available before a cutoff (prevents lookahead)
   subset = dataset.filter_by_available_before(
       available_before=datetime(2025, 1, 1, 12, 0)
   )

Filtering by lead time
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Only data available with at least the specified lead time
   subset = dataset.filter_by_lead_time(lead_time=timedelta(hours=6))

Selecting a version snapshot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``select_version()`` method creates a point-in-time snapshot by selecting the latest available version for each timestamp. This is essential for preventing lookahead bias in backtesting:

.. code-block:: python

   # Get a non-versioned snapshot from a versioned dataset
   snapshot = dataset.select_version()
   print(snapshot.is_versioned)  # False

Converting to Horizon-Based Format
-----------------------------------

For multi-horizon forecasting, convert a versioned dataset into a format with explicit horizon columns:

.. code-block:: python

   horizons = [timedelta(hours=1), timedelta(hours=6), timedelta(hours=24)]
   horizon_dataset = dataset.to_horizons(horizons)

This selects data for each specified lead time, adds a horizon column, and combines everything into a single ``TimeSeriesDataset`` suitable for training multi-horizon models.

Splitting Data for Training
----------------------------

OpenSTEF provides a ``DataSplitter`` class for dividing datasets into train, validation, and test sets:

.. code-block:: python

   from openstef_models.utils.evaluation_functions import DataSplitter

   splitter = DataSplitter(
       val_fraction=0.15,
       test_fraction=0.15,
   )

   train_data, val_data, test_data = splitter.split_dataset(
       data=dataset,
       target_column="load",
   )

The splitter uses stratified splitting by default to ensure representative distributions across all sets. You can also use the lower-level functions directly:

.. code-block:: python

   from openstef_models.utils.evaluation_functions import train_val_test_split

   train, val, test = train_val_test_split(
       dataset=data,
       split_func=my_split_function,
       val_fraction=0.15,
       test_fraction=0.15,
   )

.. warning::

   The sum of ``val_fraction`` and ``test_fraction`` must be less than 1.0, or a ``ValueError`` is raised.

Serialization
-------------

Datasets support Parquet serialization for efficient storage and retrieval:

.. code-block:: python

   # Save to disk
   dataset.to_parquet("path/to/dataset.parquet")

   # Load from disk
   loaded = TimeSeriesDataset.read_parquet("path/to/dataset.parquet")

Pandas Interoperability
-----------------------

Convert between datasets and DataFrames when you need raw pandas access:

.. code-block:: python

   # Dataset → DataFrame
   df = dataset.to_pandas()

   # DataFrame → Dataset
   restored = TimeSeriesDataset.from_pandas(df, sample_interval=timedelta(minutes=15))

Apply pandas transformations while preserving dataset metadata:

.. code-block:: python

   # Apply a function that operates on the underlying DataFrame
   cleaned = dataset.pipe_pandas(lambda df: df.dropna())

Feature Selection
-----------------

Select a subset of features from a dataset:

.. code-block:: python

   subset = dataset.select_features(["load", "temperature"])

This is useful when your pipeline requires only specific columns for a particular model or processing step.

Integration with the Pipeline
-----------------------------

Datasets are the primary data containers passed through OpenSTEF's forecasting pipeline. A typical workflow:

1. Load raw data into a ``VersionedTimeSeriesDataset``
2. Filter by time range and availability constraints
3. Select a version snapshot for training
4. Split into train/validation/test sets
5. Pass to the model for training or prediction

.. code-block:: python

   # End-to-end example
   raw_dataset = VersionedTimeSeriesDataset.from_dataframe(raw_df, timedelta(minutes=15))

   # Filter to training period, respecting data availability
   filtered = raw_dataset.filter_by_range(
       start=datetime(2024, 1, 1),
       end=datetime(2025, 1, 1),
   ).filter_by_available_before(datetime(2025, 1, 1))

   # Get a clean snapshot without lookahead
   training_data = filtered.select_version()

   # Split for model training
   splitter = DataSplitter(val_fraction=0.15, test_fraction=0.15)
   train, val, test = splitter.split_dataset(training_data, target_column="load")

For details on what happens next in the pipeline, see the :doc:`forecasting` guide. For information on how features are constructed before they enter the dataset, see the :doc:`feature_engineering` guide.