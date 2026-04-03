Core Package
============

The ``openstef_core`` package provides the foundational data structures and utilities that underpin the entire OpenSTEF library. This package defines how time series data is represented, validated, and manipulated throughout the forecasting pipeline.

At its heart, ``openstef_core`` centers on the ``TimeSeriesDataset`` class—a specialized container for time series data with consistent sampling intervals. The package also includes base classes for configuration management, utility functions for datetime handling and parallel processing, and custom exceptions for error handling.

TimeSeriesDataset Class
-----------------------

The ``TimeSeriesDataset`` class is the primary data structure in OpenSTEF. It wraps a pandas DataFrame with metadata about sampling intervals and provides methods for data access, persistence, and temporal filtering.

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
       'load': [100 + i for i in range(96)],
       'temperature': [15 + (i % 24) for i in range(96)]
   }, index=index)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )

The class validates that the data has a consistent sampling interval matching the specified ``sample_interval`` parameter. Set ``check_frequency=True`` to enforce strict validation during initialization.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` supports versioned data where the availability of information changes over time. This is crucial for backtesting, where you need to know what data was available at each forecast creation time:

.. code-block:: python

   # Create versioned dataset with horizon column
   versioned_data = pd.DataFrame({
       'load': [100, 105, 110, 115],
       'horizon': [0.25, 0.5, 0.75, 1.0],  # hours ahead
       'temperature': [15, 16, 17, 18]
   }, index=pd.date_range('2024-01-01', periods=4, freq='15min'))
   
   versioned_dataset = TimeSeriesDataset(
       data=versioned_data,
       sample_interval=timedelta(minutes=15),
       horizon_column='horizon'
   )

Alternatively, use an ``available_at`` column to track when each data point became available:

.. code-block:: python

   # Dataset with availability timestamps
   availability_data = pd.DataFrame({
       'load': [100, 105, 110],
       'available_at': pd.to_datetime([
           '2024-01-01 00:00',
           '2024-01-01 00:15',
           '2024-01-01 00:30'
       ])
   }, index=pd.date_range('2024-01-01', periods=3, freq='15min'))
   
   dataset_with_availability = TimeSeriesDataset(
       data=availability_data,
       sample_interval=timedelta(minutes=15),
       available_at_column='available_at'
   )

Data Access and Persistence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` inherits from ``DatasetMixin`` and ``TimeSeriesMixin``, providing methods for data manipulation and I/O operations. Access the underlying DataFrame directly via the ``data`` attribute, or use built-in methods for filtering and transformation.

The class supports serialization to various formats for persistence and exchange between pipeline stages. This makes it easy to save intermediate results during model training or backtesting workflows.

Base Classes and Configuration
-------------------------------

The ``base_model`` module provides foundational classes for configuration management across OpenSTEF components.

BaseModel
^^^^^^^^^

``BaseModel`` extends Pydantic's ``BaseModel`` with OpenSTEF-specific configuration:

.. code-block:: python

   from openstef_core.base_model import BaseModel
   
   class ForecastConfig(BaseModel):
       prediction_horizon: timedelta
       feature_names: list[str]
       model_type: str

The base configuration allows arbitrary types (like pandas DataFrames or numpy arrays), disables protected namespace warnings, and serializes special float values (inf, nan) as null in JSON.

BaseConfig
^^^^^^^^^^

``BaseConfig`` extends ``BaseModel`` with YAML serialization support, making it ideal for configuration files:

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   
   class PipelineConfig(BaseConfig):
       input_path: str
       output_path: str
       sample_interval: timedelta
   
   # Load from YAML file
   config = PipelineConfig.from_yaml('config.yaml')
   
   # Save to YAML file
   config.to_yaml('output_config.yaml')

This pattern is used throughout OpenSTEF for managing model configurations, pipeline parameters, and backtesting settings.

Utility Functions
-----------------

The ``utils`` module provides helper functions used across the library.

Datetime Utilities
^^^^^^^^^^^^^^^^^^

Time alignment functions ensure timestamps match expected sampling intervals:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.utils import align_datetime, align_datetime_to_time
   
   # Align to nearest 15-minute interval
   timestamp = datetime(2024, 1, 1, 10, 17, 30)
   aligned = align_datetime(timestamp, timedelta(minutes=15))
   # Result: 2024-01-01 10:15:00
   
   # Align to specific time of day (e.g., midnight)
   aligned_to_midnight = align_datetime_to_time(
       timestamp,
       align_time=datetime.min.time()
   )

Timedelta serialization helpers enable ISO 8601 format conversion for configuration files:

.. code-block:: python

   from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat
   
   # Convert to ISO format
   td = timedelta(hours=2, minutes=30)
   iso_string = timedelta_to_isoformat(td)  # "PT2H30M"
   
   # Parse from ISO format
   parsed_td = timedelta_from_isoformat("PT2H30M")

Parallel Processing
^^^^^^^^^^^^^^^^^^^

The ``run_parallel`` function simplifies multiprocessing for batch operations:

.. code-block:: python

   from openstef_core.utils import run_parallel
   
   def process_forecast(prediction_job):
       # Process single forecast job
       return generate_forecast(prediction_job)
   
   # Process multiple jobs in parallel
   results = run_parallel(
       process_fn=process_forecast,
       items=prediction_jobs,
       max_workers=4
   )

This utility handles process pool management and result collection, making it straightforward to parallelize forecasting operations across multiple prediction jobs.

Invariant Checking
^^^^^^^^^^^^^^^^^^

The ``not_none`` function provides runtime validation for required values:

.. code-block:: python

   from openstef_core.utils import not_none
   
   def process_data(dataset, config):
       # Assert required values are present
       validated_dataset = not_none(dataset)
       validated_config = not_none(config)
       
       # Continue processing...

This helps catch configuration errors early in the pipeline rather than failing during model training or prediction.

Exception Handling
------------------

The ``exceptions`` module defines custom exception types for OpenSTEF-specific error conditions. These exceptions provide clear error messages and enable targeted exception handling in application code.

Using custom exceptions allows library users to distinguish between OpenSTEF-specific errors (like invalid sampling intervals or missing required columns) and general Python errors.

Package Structure
-----------------

.. note::
   [DIAGRAM: Component diagram showing openstef_core internal structure - TimeSeriesDataset at center, inheriting from TimeSeriesMixin and DatasetMixin; BaseModel and BaseConfig in base_model module; utils module with datetime, multiprocessing, pydantic, and invariants submodules; exceptions module]

The core package is organized into focused modules:

- ``datasets``: ``TimeSeriesDataset`` class and related mixins
- ``base_model``: ``BaseModel`` and ``BaseConfig`` base classes
- ``utils``: Utility functions for datetime, multiprocessing, serialization, and validation
- ``exceptions``: Custom exception types

This structure provides a clean foundation for the higher-level ``openstef_models`` and ``openstef_beam`` packages. Models rely on ``TimeSeriesDataset`` for data representation, while BEAM components use ``BaseConfig`` for configuration management and ``run_parallel`` for distributed backtesting.

Integration with Other Packages
--------------------------------

The core package serves as the foundation for OpenSTEF's other packages:

- **openstef_models**: Uses ``TimeSeriesDataset`` as input/output for all model operations. Feature engineering transforms operate on datasets, and trained models produce predictions as datasets. See :doc:`models` for details on the transforms and model implementations.

- **openstef_beam**: Relies on ``BaseConfig`` for backtesting configuration and ``TimeSeriesDataset`` for storing evaluation results. The parallel processing utilities enable distributed backtesting across multiple prediction jobs. See :doc:`beam` for information on backtesting and metrics.

By centralizing data structures and utilities in ``openstef_core``, OpenSTEF maintains consistency across the entire forecasting pipeline while keeping each package focused on its specific responsibilities.