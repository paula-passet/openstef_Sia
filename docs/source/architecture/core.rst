Core Package (openstef_core)
=============================

The ``openstef_core`` package provides the foundational data structures and utilities that underpin all OpenSTEF functionality. This package defines how time series data is represented, validated, and manipulated throughout the library.

At the heart of ``openstef_core`` is the ``TimeSeriesDataset`` class, which handles regular time series data with consistent sampling intervals. The package also includes base classes for configuration management, utility functions for common operations, and custom exceptions for error handling.

.. note:: [DIAGRAM: Component diagram showing openstef_core internal structure: TimeSeriesDataset (with TimeSeriesMixin and DatasetMixin), BaseModel/BaseConfig, utils module (datetime, invariants, multiprocessing, pydantic), and exceptions module. Show how TimeSeriesDataset is used by openstef_models and openstef_beam packages.]

TimeSeriesDataset Class
-----------------------

The ``TimeSeriesDataset`` class is the primary data structure for working with time series in OpenSTEF. It wraps a pandas DataFrame with metadata about sampling intervals and optional versioning information.

Basic Usage
^^^^^^^^^^^

Creating a ``TimeSeriesDataset`` requires a pandas DataFrame with a datetime index and a specified sampling interval:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create sample data with 15-minute intervals
   index = pd.date_range('2024-01-01', periods=96, freq='15min')
   data = pd.DataFrame({
       'load': [100 + i * 0.5 for i in range(96)],
       'temperature': [15 + (i % 24) * 0.3 for i in range(96)]
   }, index=index)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )
   
   # Access the underlying data
   print(dataset.data.head())
   print(f"Sample interval: {dataset.sample_interval}")

The ``TimeSeriesDataset`` automatically validates that the data has a datetime index and can optionally check that the sampling frequency matches the specified interval.

Versioned Time Series
^^^^^^^^^^^^^^^^^^^^^

For backtesting and operational forecasting, OpenSTEF supports versioned time series where each data point has associated metadata about when it became available. This is critical for preventing lookahead bias:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create versioned data with 'available_at' column
   index = pd.date_range('2024-01-01', periods=24, freq='1h')
   data = pd.DataFrame({
       'load': [100 + i for i in range(24)],
       'available_at': [
           datetime(2024, 1, 1, i, 5)  # Available 5 minutes after each hour
           for i in range(24)
       ]
   }, index=index)
   
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(hours=1),
       available_at_column='available_at'
   )
   
   # Select data available at a specific time
   available_data = dataset.select_version(
       available_at=datetime(2024, 1, 1, 12, 0)
   )
   print(f"Rows available: {len(available_data.data)}")

Alternatively, you can use a ``horizon`` column to track lead times for forecast data. This is useful when working with predictions made at different forecast horizons.

Persistence
^^^^^^^^^^^

``TimeSeriesDataset`` provides methods to save and load data in Parquet format, preserving all metadata:

.. code-block:: python

   from pathlib import Path
   from openstef_core.datasets import TimeSeriesDataset
   
   # Save dataset with metadata
   dataset.to_parquet(Path('forecast_data.parquet'))
   
   # Load dataset - metadata is automatically restored
   loaded_dataset = TimeSeriesDataset.read_parquet(
       Path('forecast_data.parquet')
   )
   
   # Verify metadata is preserved
   assert loaded_dataset.sample_interval == dataset.sample_interval

The Parquet file's attributes dictionary stores metadata like sample intervals and column names, ensuring complete reconstruction of the dataset.

Data Structures and Mixins
---------------------------

``TimeSeriesDataset`` inherits from two mixins that define its behavior:

- ``TimeSeriesMixin``: Provides time series operations like temporal filtering, version selection, and time range queries
- ``DatasetMixin``: Defines the interface for persistence operations (saving/loading Parquet files)

This design allows other dataset types to reuse these capabilities. For example, ``VersionedTimeSeriesDataset`` extends these mixins to handle datasets split into multiple versioned segments.

The mixins ensure consistent behavior across different dataset implementations while keeping the code modular and testable.

Utility Functions
-----------------

The ``openstef_core.utils`` module provides essential utilities used throughout OpenSTEF:

Datetime Utilities
^^^^^^^^^^^^^^^^^^

Functions for aligning timestamps to regular intervals:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.utils import align_datetime, align_datetime_to_time
   
   # Align to 15-minute intervals
   timestamp = datetime(2024, 1, 1, 10, 17, 30)
   aligned = align_datetime(timestamp, timedelta(minutes=15))
   # Result: 2024-01-01 10:15:00
   
   # Align to specific time of day (e.g., midnight)
   aligned_midnight = align_datetime_to_time(
       timestamp,
       align_time=datetime(2024, 1, 1, 0, 0, 0).time()
   )

Type Utilities
^^^^^^^^^^^^^^

Helper functions for type validation and conversion:

.. code-block:: python

   from openstef_core.utils import not_none, timedelta_to_isoformat
   from datetime import timedelta
   
   # Assert non-None values (useful for type narrowing)
   value = some_function_that_might_return_none()
   checked_value = not_none(value)  # Raises if None
   
   # Convert timedelta to ISO 8601 format for serialization
   interval = timedelta(hours=1, minutes=30)
   iso_string = timedelta_to_isoformat(interval)
   # Result: "PT1H30M"

Parallel Processing
^^^^^^^^^^^^^^^^^^^

The ``run_parallel`` function simplifies multiprocessing for batch operations:

.. code-block:: python

   from openstef_core.utils import run_parallel
   
   def process_forecast(prediction_id: int) -> dict:
       # Process a single forecast
       return {"id": prediction_id, "result": "processed"}
   
   # Process multiple forecasts in parallel
   prediction_ids = [1, 2, 3, 4, 5]
   results = run_parallel(
       process_fn=process_forecast,
       items=prediction_ids,
       n_processes=4
   )

Base Classes
------------

BaseModel and BaseConfig
^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_core`` provides Pydantic-based base classes for configuration management:

.. code-block:: python

   from openstef_core.base_model import BaseModel, BaseConfig
   from pathlib import Path
   
   class ForecastConfig(BaseConfig):
       model_type: str
       horizon_minutes: int
       sample_interval_minutes: int = 15
   
   # Create configuration
   config = ForecastConfig(
       model_type="xgb",
       horizon_minutes=1440
   )
   
   # Save to YAML
   config.to_yaml(Path('forecast_config.yaml'))
   
   # Load from YAML
   loaded_config = ForecastConfig.from_yaml(Path('forecast_config.yaml'))

``BaseModel`` is configured to allow arbitrary types and handle special numeric values (inf, nan) in JSON serialization. This makes it suitable for machine learning configurations that may include numpy arrays or special float values.

Exception Handling
------------------

The ``openstef_core.exceptions`` module defines custom exceptions for clear error reporting:

- ``TimeSeriesValidationError``: Raised when time series data fails validation (e.g., irregular sampling, missing datetime index)
- Other domain-specific exceptions for data integrity issues

These exceptions help distinguish between different failure modes and provide actionable error messages.

Integration with Other Packages
--------------------------------

The core package serves as the foundation for higher-level functionality:

- **openstef_models**: Uses ``TimeSeriesDataset`` for feature engineering and model training. See :doc:`models` for details on the transforms module.
- **openstef_beam**: Operates on ``TimeSeriesDataset`` instances for backtesting and evaluation. See :doc:`beam` for information on metrics and backtesting workflows.

By centralizing data structures in ``openstef_core``, OpenSTEF ensures consistent data handling across all forecasting operations.