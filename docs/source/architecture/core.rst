Core Package
============

The ``openstef_core`` package provides the foundational data structures, utilities, and base classes that underpin the entire OpenSTEF library. This package defines how time series data is represented, validated, and manipulated throughout the forecasting pipeline.

At the heart of ``openstef_core`` is the ``TimeSeriesDataset`` class, which handles regular time series data with consistent sampling intervals. The package also provides type definitions for temporal concepts like lead times and data availability, utilities for datetime alignment and parallel processing, and base classes that establish common patterns across OpenSTEF components.

TimeSeriesDataset Class
-----------------------

The ``TimeSeriesDataset`` class is the primary data structure for working with time series in OpenSTEF. It wraps a pandas DataFrame with temporal metadata and provides operations for data access, persistence, and filtering.

Basic Usage
^^^^^^^^^^^

Creating a ``TimeSeriesDataset`` requires a DataFrame with a datetime index and a sample interval:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create a simple time series
   data = pd.DataFrame({
       'load': [100, 120, 110, 130],
       'temperature': [15.2, 16.1, 15.8, 16.5]
   }, index=pd.date_range('2025-01-01', periods=4, freq='15min'))
   
   dataset = TimeSeriesDataset(
       data,
       sample_interval=timedelta(minutes=15)
   )
   
   # Access the underlying DataFrame
   print(dataset.data)
   
   # Get feature names (excludes internal columns)
   print(dataset.feature_names)  # ['load', 'temperature']

The ``sample_interval`` parameter defines the expected time between consecutive observations. This is typically 15 minutes for energy forecasting applications, though other intervals are supported.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

OpenSTEF supports versioned datasets that track when data becomes available over time. This is essential for realistic backtesting, ensuring models only use data that would have been available at forecast time.

A dataset becomes versioned when it includes either a ``horizon`` column (representing forecast lead time) or an ``available_at`` column (representing when the data became available):

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create versioned data with horizon column
   data = pd.DataFrame({
       'load': [100, 120, 110, 130],
       'horizon': pd.to_timedelta(['1h', '2h', '1h', '2h'])
   }, index=pd.date_range('2025-01-01', periods=4, freq='15min'))
   
   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))
   
   # Check if versioned
   print(dataset.is_versioned)  # True
   
   # Get available horizons
   print(dataset.horizons)  # List of LeadTime objects

The horizon column uses ``timedelta`` values to represent how far ahead each observation was made. For example, a horizon of ``1h`` means the data represents a forecast made 1 hour before the timestamp.

Data Access and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides methods for temporal filtering and data access:

.. code-block:: python

   from datetime import datetime, timedelta
   
   # Filter by time range
   subset = dataset.filter_on_time_range(
       start=datetime(2025, 1, 1, 6, 0),
       end=datetime(2025, 1, 1, 12, 0)
   )
   
   # Get data at specific horizon (for versioned datasets)
   horizon_data = dataset.at_horizon(timedelta(hours=1))
   
   # Access temporal metadata
   print(dataset.sample_interval)  # timedelta(minutes=15)
   print(dataset.start_time)       # First timestamp
   print(dataset.end_time)         # Last timestamp

Persistence
^^^^^^^^^^^

Datasets can be saved to and loaded from Parquet files, preserving all metadata:

.. code-block:: python

   from pathlib import Path
   
   # Save dataset
   dataset.to_parquet(Path('forecast_data.parquet'))
   
   # Load dataset
   loaded = TimeSeriesDataset.from_parquet(Path('forecast_data.parquet'))
   
   # Metadata is preserved
   assert loaded.sample_interval == dataset.sample_interval
   assert loaded.is_versioned == dataset.is_versioned

Core Type Definitions
---------------------

The ``openstef_core.types`` module provides typed wrappers for temporal and quantile concepts used throughout OpenSTEF.

LeadTime
^^^^^^^^

``LeadTime`` represents a forecast lead time as a typed timedelta with consistent serialization:

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta
   
   # Create from timedelta
   lead = LeadTime(timedelta(hours=2))
   
   # Create from ISO 8601 string
   lead = LeadTime.from_string('PT2H')
   
   # Convert to hours
   hours = lead.to_hours()  # 2.0
   
   # String representation uses ISO 8601
   print(str(lead))  # 'PT2H'

AvailableAt
^^^^^^^^^^^

``AvailableAt`` represents when data becomes available relative to a reference day, using the format ``DnTHHMM[tz]`` where ``n`` is the day offset:

.. code-block:: python

   from openstef_core.types import AvailableAt
   from datetime import datetime
   
   # Data available at 09:00 on the same day
   avail = AvailableAt.from_string('D0T0900')
   
   # Apply to a reference date
   ref_date = datetime(2025, 1, 15)
   available_time = avail.apply(ref_date)
   # Returns: datetime(2025, 1, 15, 9, 0)
   
   # Data available at 06:00 the next day
   next_day = AvailableAt.from_string('D1T0600')

Utilities
---------

The ``openstef_core.utils`` module provides common utilities used throughout the library.

Datetime Alignment
^^^^^^^^^^^^^^^^^^

Functions for aligning timestamps to specific intervals or times:

.. code-block:: python

   from openstef_core.utils import align_datetime, align_datetime_to_time
   from datetime import datetime, timedelta, time
   
   # Align to 15-minute intervals
   dt = datetime(2025, 1, 1, 10, 17, 30)
   aligned = align_datetime(dt, timedelta(minutes=15))
   # Returns: datetime(2025, 1, 1, 10, 15)
   
   # Align to specific time of day
   aligned_time = align_datetime_to_time(dt, time(9, 0))
   # Returns: datetime(2025, 1, 1, 9, 0)

Parallel Processing
^^^^^^^^^^^^^^^^^^^

The ``run_parallel`` utility simplifies parallel execution of functions:

.. code-block:: python

   from openstef_core.utils import run_parallel
   
   def process_item(item):
       # Expensive computation
       return item * 2
   
   items = [1, 2, 3, 4, 5]
   results = run_parallel(process_item, items, n_processes=4)

Base Classes
------------

The ``openstef_core.base_model`` module provides base classes for configuration and model components.

BaseConfig
^^^^^^^^^^

Configuration classes inherit from ``BaseConfig`` to gain YAML serialization:

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from pathlib import Path
   
   class ForecastConfig(BaseConfig):
       model_type: str
       horizon_hours: int
       quantiles: list[float]
   
   # Create configuration
   config = ForecastConfig(
       model_type='xgb',
       horizon_hours=48,
       quantiles=[0.1, 0.5, 0.9]
   )
   
   # Save to YAML
   config.write_yaml(Path('config.yaml'))
   
   # Load from YAML
   loaded = ForecastConfig.read_yaml(Path('config.yaml'))

Package Structure
-----------------

The ``openstef_core`` package is organized into several modules:

- ``datasets/``: TimeSeriesDataset and related data structures
- ``types.py``: Core type definitions (LeadTime, AvailableAt, Quantile)
- ``utils/``: Common utilities for datetime, multiprocessing, and serialization
- ``base_model.py``: Base classes for configuration and components

.. note::

   [DIAGRAM: Component diagram showing openstef_core internal structure with modules: datasets (TimeSeriesDataset, VersionedTimeSeriesDataset), types (LeadTime, AvailableAt, Quantile), utils (datetime, multiprocessing, pydantic), and base_model (BaseConfig, BaseModel). Show dependencies between modules.]

This structure provides a clean separation of concerns, with data structures isolated from utilities and type definitions. Other OpenSTEF packages build on this foundation - ``openstef_models`` uses these datasets for training and prediction, while ``openstef_beam`` uses them for pipeline operations.

Integration with Other Packages
--------------------------------

The core package provides the foundation that other OpenSTEF packages build upon:

- **openstef_models**: Uses ``TimeSeriesDataset`` for model training and prediction. Transform classes operate on these datasets to add features. See :doc:`models` for details on the transform pipeline.

- **openstef_beam**: Pipeline components consume and produce ``TimeSeriesDataset`` objects. Backtesting operations rely on versioned datasets to ensure temporal validity. See :doc:`beam` for pipeline architecture.

The type definitions in ``openstef_core.types`` ensure consistent serialization across package boundaries, while the base classes establish common patterns for configuration management.