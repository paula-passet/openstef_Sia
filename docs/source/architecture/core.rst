Core Package (openstef_core)
=============================

The ``openstef_core`` package provides the foundational data structures, utilities, and base classes that underpin the entire OpenSTEF library. It defines how time series data is represented, validated, and manipulated throughout the forecasting workflow. This package is the bedrock upon which ``openstef_models`` and ``openstef_beam`` are built.

At the heart of ``openstef_core`` is the ``TimeSeriesDataset`` class, which handles regular time series data with consistent sampling intervals. The package also includes specialized dataset classes for validated forecasting inputs, utilities for datetime alignment and multiprocessing, and shared type definitions used across all OpenSTEF packages.

TimeSeriesDataset: The Foundation
----------------------------------

The ``TimeSeriesDataset`` class is the primary data structure for working with time series in OpenSTEF. It wraps a pandas DataFrame with additional metadata and validation to ensure data integrity and provide convenient operations for forecasting workflows.

Key features of ``TimeSeriesDataset``:

- **Regular sampling intervals**: Enforces consistent time steps between observations
- **Automatic sorting**: Maintains temporal order automatically
- **Versioned data support**: Tracks data availability over time via ``horizon`` or ``available_at`` columns
- **Persistence**: Save and load datasets with metadata preservation
- **Temporal slicing**: Efficient filtering by time ranges

Basic Usage
^^^^^^^^^^^

Creating a ``TimeSeriesDataset`` is straightforward:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create time series data
   index = pd.date_range(
       start="2025-01-01", 
       periods=24, 
       freq="1h"
   )
   data = pd.DataFrame({
       "load": [100 + i * 2 for i in range(24)],
       "temperature": [15 + i * 0.5 for i in range(24)],
       "wind_speed": [10 - i * 0.2 for i in range(24)]
   }, index=index)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(hours=1)
   )
   
   # Access the underlying DataFrame
   print(dataset.data.head())
   
   # Get temporal metadata
   print(f"Sample interval: {dataset.sample_interval}")
   print(f"Start time: {dataset.start_datetime}")
   print(f"End time: {dataset.end_datetime}")

The ``sample_interval`` parameter defines the expected time step between consecutive observations. By default, the dataset validates that the actual frequency matches this interval, though you can disable this check with ``check_frequency=False`` for performance.

Temporal Slicing and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides efficient methods for extracting time ranges:

.. code-block:: python

   # Slice by datetime range
   subset = dataset.slice(
       start=datetime(2025, 1, 1, 6, 0),
       end=datetime(2025, 1, 1, 18, 0)
   )
   
   # Filter to specific time window
   morning_data = dataset.filter_by_time(
       start_time=datetime(2025, 1, 1, 6, 0).time(),
       end_time=datetime(2025, 1, 1, 12, 0).time()
   )

These operations return new ``TimeSeriesDataset`` instances, preserving metadata while operating on the filtered data.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

For backtesting and realistic forecasting scenarios, OpenSTEF supports versioned datasets that track when data became available. This enables you to simulate historical forecasting conditions accurately:

.. code-block:: python

   # Create dataset with availability tracking
   index = pd.date_range(start="2025-01-01", periods=24, freq="1h")
   data = pd.DataFrame({
       "load": range(24),
       "available_at": [
           datetime(2025, 1, 1, i, 30) for i in range(24)
       ]
   }, index=index)
   
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(hours=1)
   )
   
   # Extract data available at a specific time
   available_data = dataset.get_data_at(
       available_at=datetime(2025, 1, 1, 12, 0)
   )

Alternatively, you can use a ``horizon`` column to represent forecast lead times, which is useful for organizing predictions made at different horizons.

Validated Dataset Classes
--------------------------

The ``openstef_core.datasets.validated_datasets`` module provides specialized dataset classes that extend ``TimeSeriesDataset`` with domain-specific validation and convenience methods.

ForecastInputDataset
^^^^^^^^^^^^^^^^^^^^

``ForecastInputDataset`` represents validated input data for forecasting, ensuring that required columns (like the target variable) are present:

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset
   
   # Create forecast input with validated target column
   forecast_input = ForecastInputDataset(
       data=data,
       sample_interval=timedelta(hours=1),
       target_column="load",
       forecast_start=datetime(2025, 1, 2, 0, 0)
   )
   
   # Access target series directly
   target = forecast_input.target_series
   
   # Get input features (excludes target)
   features = forecast_input.input_data()
   
   # Create forecast time range
   forecast_index = forecast_input.create_forecast_range(
       horizon=timedelta(hours=48)
   )

This class is particularly useful when preparing data for model training or prediction, as it separates the target variable from input features and tracks the forecast start time.

ForecastDataset
^^^^^^^^^^^^^^^

``ForecastDataset`` stores probabilistic forecast results with quantile estimates:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset
   
   # Create forecast dataset with quantiles
   forecast_data = pd.DataFrame({
       "forecast": [100, 105, 110],
       "quantile_0.10": [90, 95, 100],
       "quantile_0.50": [100, 105, 110],
       "quantile_0.90": [110, 115, 120]
   }, index=pd.date_range("2025-01-01", periods=3, freq="1h"))
   
   forecast_dataset = ForecastDataset(
       data=forecast_data,
       sample_interval=timedelta(hours=1)
   )
   
   # Access median forecast
   median = forecast_dataset.median_series

Core Utilities
--------------

The ``openstef_core.utils`` module provides general-purpose utilities used throughout OpenSTEF.

Datetime Alignment
^^^^^^^^^^^^^^^^^^

Datetime alignment functions ensure timestamps conform to expected intervals:

.. code-block:: python

   from openstef_core.utils import align_datetime, align_datetime_to_time
   from datetime import datetime, timedelta, time
   
   # Align to nearest 15-minute interval
   aligned = align_datetime(
       dt=datetime(2025, 1, 1, 10, 23, 45),
       interval=timedelta(minutes=15)
   )
   # Result: 2025-01-01 10:15:00
   
   # Align to specific time of day
   aligned_time = align_datetime_to_time(
       dt=datetime(2025, 1, 1, 10, 23, 45),
       target_time=time(12, 0)
   )
   # Result: 2025-01-01 12:00:00

These utilities are essential for ensuring temporal consistency in forecasting pipelines.

Parallel Processing
^^^^^^^^^^^^^^^^^^^

The ``run_parallel`` function simplifies multiprocessing for batch operations:

.. code-block:: python

   from openstef_core.utils import run_parallel
   
   def process_forecast(prediction_id: int) -> dict:
       # Your forecasting logic here
       return {"id": prediction_id, "result": prediction_id * 2}
   
   # Process multiple forecasts in parallel
   results = run_parallel(
       func=process_forecast,
       args_list=[(i,) for i in range(10)],
       n_processes=4
   )

This utility handles process pool management and result collection, making it easy to parallelize computationally intensive forecasting tasks.

Type Definitions
^^^^^^^^^^^^^^^^

The ``openstef_core.types`` module defines shared type aliases used across OpenSTEF:

.. code-block:: python

   from openstef_core.types import LeadTime, AvailableAt
   from datetime import timedelta, datetime
   
   # LeadTime represents forecast horizons
   horizon: LeadTime = timedelta(hours=24)
   
   # AvailableAt represents data availability timestamps
   availability: AvailableAt = datetime(2025, 1, 1, 12, 0)

These type aliases improve code clarity and enable better type checking throughout the library.

Data Validation
---------------

The ``openstef_core.datasets.validation`` module provides validation functions that ensure data integrity:

- ``validate_datetime_column``: Ensures a column contains valid datetime values
- ``validate_timedelta_column``: Ensures a column contains valid timedelta values
- ``TimeSeriesValidationError``: Exception raised when validation fails

These validators are used internally by ``TimeSeriesDataset`` but can also be used directly when building custom data processing pipelines.

Relationship to Other Packages
-------------------------------

The ``openstef_core`` package serves as the foundation for the entire OpenSTEF ecosystem:

- **openstef_models**: Uses ``TimeSeriesDataset`` and ``ForecastInputDataset`` for all model training and prediction operations. The transforms module (see :doc:`models`) operates on these core data structures.

- **openstef_beam**: Relies on ``ForecastDataset`` and versioned datasets for backtesting and metrics calculation. See :doc:`beam` for details on evaluation workflows.

By centralizing data structures and utilities in ``openstef_core``, OpenSTEF ensures consistency across all forecasting operations and makes it easy to extend the library with custom models or evaluation methods.

Persistence and Serialization
------------------------------

``TimeSeriesDataset`` supports saving and loading with full metadata preservation:

.. code-block:: python

   # Save dataset to disk
   dataset.save("my_dataset.parquet")
   
   # Load dataset with metadata
   loaded_dataset = TimeSeriesDataset.load("my_dataset.parquet")
   
   # Metadata is preserved
   assert loaded_dataset.sample_interval == dataset.sample_interval

This functionality is crucial for caching intermediate results in forecasting pipelines and sharing datasets between different components of your system.