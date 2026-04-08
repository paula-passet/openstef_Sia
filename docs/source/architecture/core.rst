Core Package
============

The ``openstef_core`` package provides the foundational data structures, types, and utilities that underpin all OpenSTEF forecasting operations. This package defines how time series data is represented, validated, and manipulated throughout the library, establishing consistent patterns used by ``openstef_models``, ``openstef_beam``, and other components.

At the heart of ``openstef_core`` is the ``TimeSeriesDataset`` class, which handles regular time series data with optional versioning support for realistic backtesting. The package also includes type definitions for temporal concepts like lead times and availability times, base configuration classes, and utility functions for data processing.

.. note:: [DIAGRAM: Component diagram showing openstef_core internal structure: datasets module (TimeSeriesDataset, mixins, validation), types module (LeadTime, AvailableAt, Quantile), base_model module (BaseModel, BaseConfig), and utils module (datetime, pandas, multiprocessing helpers). Arrows showing how other packages depend on these components.]

TimeSeriesDataset Class
-----------------------

The ``TimeSeriesDataset`` class is the primary data structure for working with time series in OpenSTEF. It wraps a pandas DataFrame with a datetime index and enforces consistent sampling intervals, providing methods for temporal operations, persistence, and data access.

Basic Usage
^^^^^^^^^^^

Creating a ``TimeSeriesDataset`` requires a DataFrame with a datetime index and a specified sample interval:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create sample data
   data = pd.DataFrame({
       'load': [100, 120, 115, 130],
       'temperature': [15.2, 16.1, 15.8, 16.5]
   }, index=pd.date_range('2025-01-01', periods=4, freq='15min'))
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data,
       sample_interval=timedelta(minutes=15)
   )
   
   # Access properties
   print(dataset.sample_interval)  # timedelta(minutes=15)
   print(dataset.feature_names)    # ['load', 'temperature']
   print(dataset.index)            # DatetimeIndex

The dataset automatically sorts data by timestamp and validates the datetime index. Set ``is_sorted=True`` if your data is already sorted to skip this step.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

For backtesting scenarios where you need to track when data became available, ``TimeSeriesDataset`` supports versioned data through either a ``horizon`` column (forecast lead time) or an ``available_at`` column (data availability timestamp):

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime
   import pandas as pd
   from datetime import timedelta
   
   # Create versioned data with horizon column
   data = pd.DataFrame({
       'load': [100, 120, 115, 130],
       'horizon': pd.to_timedelta(['1h', '2h', '1h', '2h'])
   }, index=pd.date_range('2025-01-01', periods=4, freq='1h'))
   
   dataset = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))
   
   # Check versioning status
   print(dataset.is_versioned)  # True
   print(dataset.horizons)      # List of LeadTime objects
   
   # Select data for specific lead time
   lead_time = LeadTime.from_string('PT1H')
   subset = dataset.select_lead_time(lead_time)

Versioned datasets enable realistic backtesting by ensuring you only use data that would have been available at prediction time. The ``select_version()`` method filters data based on availability constraints.

Data Access and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides several methods for temporal filtering and data access:

.. code-block:: python

   from datetime import datetime
   
   # Time-based slicing
   subset = dataset.slice(
       start=datetime(2025, 1, 1, 6, 0),
       end=datetime(2025, 1, 1, 12, 0)
   )
   
   # Calculate time coverage
   coverage = dataset.calculate_time_coverage()
   
   # Access underlying DataFrame
   df = dataset.data
   
   # Apply custom transformations with pipe
   result = dataset.pipe(lambda ds: ds.data.describe())

The ``slice()`` method efficiently extracts time ranges while preserving all dataset metadata. This is particularly useful when splitting data into training and validation sets.

Persistence
^^^^^^^^^^^

Save and load datasets while preserving all metadata including sample interval and versioning information:

.. code-block:: python

   from pathlib import Path
   
   # Save to parquet
   dataset.to_parquet(Path('forecast_data.parquet'))
   
   # Load from parquet
   loaded = TimeSeriesDataset.read_parquet(Path('forecast_data.parquet'))
   
   # Metadata is preserved
   assert loaded.sample_interval == dataset.sample_interval
   assert loaded.feature_names == dataset.feature_names

Parquet format provides efficient storage and fast loading for large time series datasets. Metadata is stored in the parquet file's custom metadata fields.

Core Types
----------

The ``openstef_core.types`` module defines typed wrappers for temporal and forecasting concepts, ensuring consistent serialization and validation across the library.

LeadTime
^^^^^^^^

``LeadTime`` represents the time interval between when a forecast is made and the target timestamp. It wraps a ``timedelta`` with ISO 8601 string serialization:

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta
   
   # Create from string (ISO 8601 duration format)
   lead_time = LeadTime.from_string('PT36H')
   
   # Create from timedelta
   lead_time = LeadTime(timedelta(hours=36))
   
   # Access underlying timedelta
   td = lead_time.value  # timedelta(hours=36)
   
   # Get hours as float
   hours = lead_time.hours()  # 36.0
   
   # String representation for serialization
   print(str(lead_time))  # 'PT36H'

Lead times are used throughout OpenSTEF to specify forecast horizons and filter versioned datasets.

AvailableAt
^^^^^^^^^^^

``AvailableAt`` represents when data or predictions become available relative to a reference day, using the format ``DnTHHMM`` where ``n`` is the day offset and ``HHMM`` is the time:

.. code-block:: python

   from openstef_core.types import AvailableAt
   from datetime import date
   
   # Parse availability time
   avail = AvailableAt.from_string('D-1T0600')  # 6 AM previous day
   
   # With timezone
   avail_tz = AvailableAt.from_string('D-1T0600[Europe/Amsterdam]')
   
   # Resolve to absolute datetime for a specific date
   reference_date = date(2025, 1, 15)
   absolute_time = avail.resolve(reference_date)
   # Returns: datetime(2025, 1, 14, 6, 0)

This type is essential for backtesting pipelines where you need to simulate data availability constraints. See the :doc:`beam` page for examples of using ``AvailableAt`` in evaluation pipelines.

Quantile
^^^^^^^^

``Quantile`` represents probability levels for quantile forecasts, with validation ensuring values are in the range [0, 1]:

.. code-block:: python

   from openstef_core.types import Quantile
   
   # Create quantiles
   q50 = Quantile(0.5)   # Median
   q95 = Quantile(0.95)  # 95th percentile
   
   # Parse from string
   q = Quantile.from_string('0.95')
   
   # Access value
   value = q.value  # 0.95

Quantiles are used extensively in probabilistic forecasting models and evaluation metrics.

Base Configuration Classes
---------------------------

The ``openstef_core.base_model`` module provides base classes for configuration management using Pydantic:

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from pathlib import Path
   
   class ModelConfig(BaseConfig):
       learning_rate: float = 0.01
       max_depth: int = 5
       n_estimators: int = 100
   
   # Save configuration
   config = ModelConfig(learning_rate=0.05)
   config.write_yaml(Path('model_config.yaml'))
   
   # Load configuration
   loaded = ModelConfig.read_yaml(Path('model_config.yaml'))

``BaseConfig`` provides YAML serialization with proper type validation, making it easy to manage configuration files for models, pipelines, and experiments. The ``openstef_models`` package uses these base classes extensively for model configuration.

Utility Functions
-----------------

The ``openstef_core.utils`` module provides helper functions for common operations:

Datetime Utilities
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_core.utils import align_datetime, align_datetime_to_time
   from datetime import datetime, timedelta, time
   
   # Align datetime to interval
   dt = datetime(2025, 1, 1, 10, 23)
   aligned = align_datetime(dt, timedelta(minutes=15))
   # Returns: datetime(2025, 1, 1, 10, 15)
   
   # Align to specific time of day
   aligned_time = align_datetime_to_time(dt, time(6, 0))
   # Returns: datetime(2025, 1, 1, 6, 0)

These functions are useful for ensuring timestamps match expected sampling intervals or daily schedules.

Timedelta Serialization
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat
   from datetime import timedelta
   
   # Convert to ISO 8601 string
   td = timedelta(hours=36, minutes=30)
   iso_str = timedelta_to_isoformat(td)  # 'PT36H30M'
   
   # Parse from ISO 8601 string
   parsed = timedelta_from_isoformat('PT36H30M')

These utilities ensure consistent timedelta serialization in configuration files and data storage.

Multiprocessing
^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_core.utils import run_parallel
   
   def process_item(item):
       # Expensive computation
       return item ** 2
   
   items = range(100)
   results = run_parallel(process_item, items, n_jobs=4)

The ``run_parallel`` function provides a simple interface for parallel processing, automatically handling process pool management.

Data Validation
---------------

The ``openstef_core.datasets.validation`` module provides validation functions for time series data:

.. code-block:: python

   from openstef_core.datasets.validation import (
       validate_datetime_column,
       validate_timedelta_column,
       TimeSeriesValidationError
   )
   import pandas as pd
   
   try:
       # Validate datetime column
       validate_datetime_column(df['timestamp'])
       
       # Validate timedelta column
       validate_timedelta_column(df['horizon'])
   except TimeSeriesValidationError as e:
       print(f"Validation failed: {e}")

These validators are used internally by ``TimeSeriesDataset`` but can also be used directly when preparing data.

Integration with Other Packages
--------------------------------

The core package provides the foundation for all other OpenSTEF components:

- **openstef_models**: Uses ``TimeSeriesDataset`` for training data and ``BaseConfig`` for model configuration. See :doc:`models` for details on model training and transforms.

- **openstef_beam**: Builds backtesting and evaluation pipelines on top of ``TimeSeriesDataset`` versioning capabilities. The ``LeadTime`` and ``AvailableAt`` types are central to evaluation configuration. See :doc:`beam` for backtesting examples.

- **openstef_dbc**: Database connectors return data as ``TimeSeriesDataset`` instances, ensuring consistent data structures throughout the pipeline.

By establishing these core abstractions, ``openstef_core`` enables the rest of the library to focus on domain-specific logic while maintaining consistent data handling patterns.