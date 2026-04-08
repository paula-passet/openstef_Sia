Core Package
============

The ``openstef_core`` package provides the foundational data structures, types, and utilities that underpin all OpenSTEF forecasting operations. This package defines how time series data is represented, validated, and manipulated throughout the library, offering a consistent interface for handling both simple time series and complex versioned datasets used in backtesting scenarios.

At the heart of ``openstef_core`` is the ``TimeSeriesDataset`` class, which wraps pandas DataFrames with domain-specific functionality for energy forecasting. The package also includes specialized type definitions like ``LeadTime`` and ``AvailableAt`` that ensure consistent serialization and validation of temporal concepts, plus a collection of utilities for data manipulation and configuration management.

TimeSeriesDataset Class
-----------------------

The ``TimeSeriesDataset`` class is the primary data structure for working with time series in OpenSTEF. It enforces regular sampling intervals, provides temporal metadata, and supports both simple time series and versioned datasets where data availability is tracked over time.

Basic Usage
^^^^^^^^^^^

Creating a ``TimeSeriesDataset`` from a pandas DataFrame:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    
    # Create a simple time series
    data = pd.DataFrame({
        'load': [100, 120, 130, 115],
        'temperature': [15.2, 16.1, 15.8, 14.9]
    }, index=pd.date_range('2025-01-01', periods=4, freq='15min'))
    
    dataset = TimeSeriesDataset(
        data,
        sample_interval=timedelta(minutes=15)
    )
    
    # Access properties
    print(dataset.sample_interval)  # timedelta(minutes=15)
    print(dataset.feature_names)    # ['load', 'temperature']
    print(dataset.index)            # DatetimeIndex

The ``TimeSeriesDataset`` automatically sorts data by timestamp and validates that the index is a proper ``DatetimeIndex``. The ``sample_interval`` parameter defines the expected time between consecutive observations.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

For backtesting and realistic forecasting scenarios, ``TimeSeriesDataset`` supports versioned data where each observation tracks when it became available. This is crucial for avoiding look-ahead bias:

.. code-block:: python

    # Create versioned dataset with horizon column
    data_with_horizon = pd.DataFrame({
        'load': [100, 120, 130, 115],
        'temperature': [15.2, 16.1, 15.8, 14.9],
        'horizon': pd.to_timedelta(['1h', '2h', '1h', '2h'])
    }, index=pd.date_range('2025-01-01', periods=4, freq='1h'))
    
    dataset = TimeSeriesDataset(
        data_with_horizon,
        sample_interval=timedelta(hours=1)
    )
    
    # Check if dataset is versioned
    print(dataset.is_versioned)  # True
    print(dataset.horizons)      # List of LeadTime objects
    
    # Select specific forecast horizon
    one_hour_ahead = dataset.select_horizon(timedelta(hours=1))

Versioned datasets can track availability in two ways:

- **Horizon column**: Stores the forecast lead time for each observation (e.g., "1h ahead", "2h ahead")
- **Available_at column**: Stores the exact timestamp when data became available

Data Access and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides efficient methods for temporal filtering:

.. code-block:: python

    # Calculate time coverage
    coverage = dataset.calculate_time_coverage()
    
    # Slice by time range
    subset = dataset[start_time:end_time]
    
    # Access underlying DataFrame
    df = dataset.data
    
    # Get specific version of data
    if dataset.is_versioned:
        version = dataset.select_version()

Persistence
^^^^^^^^^^^

Save and load datasets while preserving all metadata:

.. code-block:: python

    from pathlib import Path
    
    # Save to parquet
    dataset.to_parquet(Path('forecast_data.parquet'))
    
    # Load from parquet
    loaded = TimeSeriesDataset.read_parquet(Path('forecast_data.parquet'))

The parquet format preserves the sample interval, column metadata, and all temporal information.

Core Type Definitions
---------------------

The ``openstef_core.types`` module defines specialized types for temporal concepts in forecasting.

LeadTime
^^^^^^^^

``LeadTime`` represents forecast horizons as validated timedelta objects with consistent serialization:

.. code-block:: python

    from openstef_core.types import LeadTime
    
    # Create from timedelta
    lead = LeadTime(timedelta(hours=2))
    
    # Create from ISO 8601 string
    lead = LeadTime.from_string('PT2H')
    
    # Convert to hours
    hours = lead.to_hours()  # 2.0
    
    # Serializes consistently
    str(lead)  # 'PT2H'

``LeadTime`` is used throughout OpenSTEF to represent forecast horizons in a type-safe manner.

AvailableAt
^^^^^^^^^^^

``AvailableAt`` represents when data becomes available relative to a reference day, using the format ``DnTHHMM[tz]``:

.. code-block:: python

    from openstef_core.types import AvailableAt
    from datetime import datetime
    
    # Data available next day at 09:00 UTC
    avail = AvailableAt.from_string('D1T0900')
    
    # Apply to reference date
    ref_date = datetime(2025, 1, 1, 12, 0)
    available_time = avail.apply(ref_date)
    
    # Apply to entire index
    index = pd.date_range('2025-01-01', periods=10, freq='1h')
    available_times = avail.apply_index(index)

This type is essential for modeling realistic data availability in backtesting scenarios.

Base Classes and Mixins
-----------------------

The core package provides base classes that establish common patterns across OpenSTEF.

DatasetMixin
^^^^^^^^^^^^

The ``DatasetMixin`` protocol defines standard operations for dataset persistence and transformation:

- ``to_parquet(path)``: Save dataset to parquet file
- ``read_parquet(path)``: Load dataset from parquet file  
- ``pipe(func, *args, **kwargs)``: Apply a function to the dataset

All dataset classes implement this mixin, ensuring consistent persistence behavior.

TimeSeriesMixin
^^^^^^^^^^^^^^^

The ``TimeSeriesMixin`` provides temporal properties and operations:

- ``index``: Access to the DatetimeIndex
- ``sample_interval``: Time between observations
- ``feature_names``: List of data columns
- ``calculate_time_coverage()``: Total time span

BaseModel and BaseConfig
^^^^^^^^^^^^^^^^^^^^^^^^^

``BaseModel`` and ``BaseConfig`` extend Pydantic's base model with YAML serialization:

.. code-block:: python

    from pathlib import Path
    from openstef_core.base_model import BaseConfig
    
    class ForecastConfig(BaseConfig):
        model_type: str
        horizon_hours: int
    
    # Read from YAML
    config = ForecastConfig.read_yaml(Path('config.yaml'))
    
    # Write to YAML
    config.write_yaml(Path('output.yaml'))

These base classes are used throughout OpenSTEF for configuration management and ensure consistent serialization across the library.

Utilities
---------

The ``openstef_core.utils`` module provides helper functions used throughout the library.

Datetime Utilities
^^^^^^^^^^^^^^^^^^

Functions for aligning timestamps to regular intervals:

.. code-block:: python

    from openstef_core.utils import align_datetime, align_datetime_to_time
    from datetime import datetime, time, timedelta
    
    # Align to 15-minute intervals
    dt = datetime(2025, 1, 1, 10, 23, 45)
    aligned = align_datetime(dt, timedelta(minutes=15))
    # Result: 2025-01-01 10:15:00
    
    # Align to specific time of day
    aligned = align_datetime_to_time(dt, time(9, 0))

Timedelta Serialization
^^^^^^^^^^^^^^^^^^^^^^^

Convert timedeltas to and from ISO 8601 format:

.. code-block:: python

    from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat
    from datetime import timedelta
    
    # Serialize
    iso_str = timedelta_to_isoformat(timedelta(hours=2, minutes=30))
    # Result: 'PT2H30M'
    
    # Deserialize
    td = timedelta_from_isoformat('PT2H30M')

Multiprocessing
^^^^^^^^^^^^^^^

Run functions in parallel across multiple processes:

.. code-block:: python

    from openstef_core.utils import run_parallel
    
    def process_item(item):
        # Expensive computation
        return item * 2
    
    items = [1, 2, 3, 4, 5]
    results = run_parallel(process_item, items, n_jobs=4)

Validation
----------

The ``openstef_core.datasets.validation`` module provides functions for validating time series data:

- ``validate_datetime_column()``: Ensure column contains valid datetime values
- ``validate_timedelta_column()``: Ensure column contains valid timedelta values
- ``TimeSeriesValidationError``: Exception raised for validation failures

These validators are used internally by ``TimeSeriesDataset`` to ensure data integrity but can also be used directly when building custom data pipelines.

Package Structure
-----------------

.. note:: [DIAGRAM: Component diagram showing openstef_core internal structure: TimeSeriesDataset at center, using types (LeadTime, AvailableAt), mixins (DatasetMixin, TimeSeriesMixin), base classes (BaseModel, BaseConfig), validation module, and utils module. Arrows show dependencies between components.]

The ``openstef_core`` package is organized into focused modules:

- **datasets/**: ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and mixins
- **types.py**: Domain-specific types (``LeadTime``, ``AvailableAt``, enums)
- **base_model.py**: Base classes for configuration and models
- **utils/**: Helper functions for datetime, serialization, and multiprocessing
- **datasets/validation.py**: Data validation functions

This modular structure allows other OpenSTEF packages to import only what they need while maintaining clear dependency boundaries.

Integration with Other Packages
--------------------------------

The core package serves as the foundation for all other OpenSTEF packages:

- **openstef_models**: Uses ``TimeSeriesDataset`` as input/output for all transforms and models
- **openstef_beam**: Builds backtesting pipelines using versioned datasets and temporal types
- **openstef_dbc**: Converts database records to ``TimeSeriesDataset`` instances

By centralizing data structures and types in ``openstef_core``, OpenSTEF ensures consistency across the entire forecasting pipeline. See :doc:`models` for how transforms operate on these datasets, and :doc:`beam` for how versioned datasets enable realistic backtesting.