Core Package (openstef_core)
=============================

The ``openstef_core`` package provides the foundational data structures and utilities that underpin all OpenSTEF forecasting operations. This package defines how time series data is represented, validated, and manipulated throughout the library.

At its heart, ``openstef_core`` centers around the ``TimeSeriesDataset`` class, which handles regular time series data with consistent sampling intervals. The package also includes base classes for configuration management, utility functions for time alignment and parallel processing, and custom exceptions for error handling.

TimeSeriesDataset: The Core Data Structure
-------------------------------------------

The ``TimeSeriesDataset`` class is the primary way to work with time series data in OpenSTEF. It wraps a pandas DataFrame and enforces consistent sampling intervals, making it suitable for forecasting workflows that require regular time steps.

Basic Usage
^^^^^^^^^^^

Creating a ``TimeSeriesDataset`` is straightforward. You provide a DataFrame with a datetime index and specify the sampling interval:

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

The ``TimeSeriesDataset`` validates that your data has a datetime index and optionally checks that the frequency matches the specified ``sample_interval``. Set ``check_frequency=True`` to enable strict frequency validation.

Versioned Data and Data Availability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

One of the most powerful features of ``TimeSeriesDataset`` is its support for versioned data. In real-world forecasting, different features become available at different times. Weather forecasts arrive periodically, while load measurements are available immediately. ``TimeSeriesDataset`` tracks this through two optional columns:

- ``horizon``: Time difference between when data is available and when it represents (e.g., a 6-hour ahead weather forecast has horizon=6h)
- ``available_at``: Explicit timestamp when each data point became available

This versioning enables realistic backtesting where the model only uses data that would have been available at forecast time:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   # Create versioned dataset with horizon column
   index = pd.date_range('2024-01-01', periods=48, freq='15min')
   data = pd.DataFrame({
       'load': [100 + i for i in range(48)],
       'weather_forecast': [20 + (i % 24) for i in range(48)],
       'horizon': [timedelta(hours=1)] * 48  # 1-hour ahead forecast
   }, index=index)

   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
       horizon_column='horizon'
   )

   # Get data available at a specific time
   available_data = dataset.get_data_at(datetime(2024, 1, 1, 12, 0))

The ``get_data_at()`` method returns only the rows where the data would have been available at the specified timestamp, accounting for the horizon values.

Data Access and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` inherits from ``TimeSeriesMixin`` and ``DatasetMixin``, which provide convenient methods for accessing and filtering data:

.. code-block:: python

   # Access the underlying DataFrame
   df = dataset.data

   # Get the sampling interval
   interval = dataset.sample_interval  # timedelta(minutes=15)

   # Filter by time range
   subset = dataset.filter_time_range(
       start=datetime(2024, 1, 1, 6, 0),
       end=datetime(2024, 1, 1, 12, 0)
   )

   # Check if dataset is empty
   if not dataset.is_empty():
       print(f"Dataset has {len(dataset.data)} rows")

Persistence
^^^^^^^^^^^

``TimeSeriesDataset`` supports saving to and loading from Parquet files, preserving all metadata including the sampling interval:

.. code-block:: python

   from pathlib import Path

   # Save to file
   dataset.to_parquet(Path('forecast_data.parquet'))

   # Load from file
   loaded_dataset = TimeSeriesDataset.from_parquet(
       Path('forecast_data.parquet')
   )

The Parquet format efficiently stores time series data while maintaining type information and compression.

Base Classes and Configuration
-------------------------------

The ``base_model`` module provides two key base classes built on Pydantic:

BaseModel
^^^^^^^^^

``BaseModel`` extends Pydantic's ``BaseModel`` with configuration suitable for OpenSTEF components:

.. code-block:: python

   from openstef_core.base_model import BaseModel

   class ForecastConfig(BaseModel):
       horizon_hours: int = 24
       confidence_level: float = 0.95
       model_type: str = "xgboost"

This base class allows arbitrary types, disables protected namespace warnings, and handles NaN/Inf serialization in JSON.

BaseConfig
^^^^^^^^^^

``BaseConfig`` extends ``BaseModel`` with YAML serialization capabilities, making it ideal for configuration files:

.. code-block:: python

   from pathlib import Path
   from openstef_core.base_model import BaseConfig

   class PipelineConfig(BaseConfig):
       input_path: Path
       output_path: Path
       sample_interval_minutes: int = 15

   # Save to YAML
   config = PipelineConfig(
       input_path=Path('/data/input'),
       output_path=Path('/data/output')
   )
   config.to_yaml(Path('config.yaml'))

   # Load from YAML
   loaded_config = PipelineConfig.from_yaml(Path('config.yaml'))

Utility Functions
-----------------

The ``utils`` module provides essential utilities used throughout OpenSTEF:

Time Alignment
^^^^^^^^^^^^^^

Time alignment functions ensure timestamps match expected intervals:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.utils import align_datetime, align_datetime_to_time

   # Align to nearest 15-minute interval
   timestamp = datetime(2024, 1, 1, 10, 17, 30)
   aligned = align_datetime(timestamp, timedelta(minutes=15))
   # Result: 2024-01-01 10:15:00

   # Align to specific time of day (e.g., midnight)
   aligned_midnight = align_datetime_to_time(timestamp, datetime.min.time())
   # Result: 2024-01-01 00:00:00

Parallel Processing
^^^^^^^^^^^^^^^^^^^

The ``run_parallel`` function simplifies parallel execution across multiple processes:

.. code-block:: python

   from openstef_core.utils import run_parallel

   def process_forecast(prediction_id: int) -> dict:
       # Process a single forecast
       return {'id': prediction_id, 'result': prediction_id * 2}

   # Process multiple forecasts in parallel
   prediction_ids = [1, 2, 3, 4, 5]
   results = run_parallel(
       process_fn=process_forecast,
       items=prediction_ids,
       n_processes=4
   )

Timedelta Serialization
^^^^^^^^^^^^^^^^^^^^^^^

Convert timedelta objects to and from ISO 8601 format for serialization:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat

   # Convert to string
   td = timedelta(hours=2, minutes=30)
   iso_string = timedelta_to_isoformat(td)  # "PT2H30M"

   # Parse from string
   parsed_td = timedelta_from_isoformat("PT2H30M")

Type Safety
^^^^^^^^^^^

The ``not_none`` function provides runtime type assertions:

.. code-block:: python

   from openstef_core.utils import not_none

   def process_data(value: int | None) -> int:
       # Assert value is not None and narrow type
       validated_value = not_none(value)
       return validated_value * 2

Exception Handling
------------------

The ``exceptions`` module defines custom exceptions for OpenSTEF operations. These exceptions provide clear error messages and help distinguish between different failure modes in forecasting pipelines.

How Core Supports Other Packages
---------------------------------

The ``openstef_core`` package serves as the foundation for the entire OpenSTEF library:

- **openstef_models**: Uses ``TimeSeriesDataset`` for all feature engineering and model training. The transforms module operates on ``TimeSeriesDataset`` instances to create lagged features, add temporal features, and prepare data for machine learning models.

- **openstef_beam**: Relies on ``TimeSeriesDataset`` for backtesting and evaluation. The versioned data capabilities enable realistic simulations where models are tested with data availability constraints matching production environments.

By centralizing data structures and utilities in ``openstef_core``, the library maintains consistency across all forecasting operations while keeping each package focused on its specific responsibilities.

.. note:: [DIAGRAM: Component diagram showing openstef_core internal structure with TimeSeriesDataset at center, connected to TimeSeriesMixin and DatasetMixin, with utils, base_model, and exceptions as supporting modules. Arrows showing dependencies to openstef_models and openstef_beam packages.]

Related Topics
--------------

- :doc:`models` - Feature engineering and model implementations that operate on TimeSeriesDataset
- :doc:`beam` - Backtesting and evaluation using versioned TimeSeriesDataset instances