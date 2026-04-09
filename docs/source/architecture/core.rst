Core Package
============

The ``openstef_core`` package provides the foundational data structures, base classes, and utilities that underpin all OpenSTEF forecasting operations. This package defines how time series data is represented, validated, and manipulated throughout the library, establishing patterns that other packages build upon.

At the heart of ``openstef_core`` is the ``TimeSeriesDataset`` class, which encapsulates time series data with consistent sampling intervals and optional versioning metadata. The package also includes base classes for transforms and stateful components, utility functions for common operations, and type definitions that ensure consistency across the library.

.. note:: [DIAGRAM: Component diagram showing openstef_core internal structure: TimeSeriesDataset at center, with connections to mixins (DatasetMixin, TimeSeriesMixin), validation module, utils module, base_model (BaseModel, BaseConfig), and types module. Show data flow from raw pandas DataFrames through validation to TimeSeriesDataset instances.]

TimeSeriesDataset Class
-----------------------

The ``TimeSeriesDataset`` class is the primary data structure for representing time series in OpenSTEF. It wraps a pandas DataFrame with additional metadata and validation, ensuring data integrity and providing convenient operations for forecasting workflows.

Core Concepts
^^^^^^^^^^^^^

A ``TimeSeriesDataset`` consists of:

- **Data**: A pandas DataFrame with a datetime index named ``timestamp``
- **Sample interval**: A consistent time step between observations (e.g., 15 minutes)
- **Feature columns**: The actual data columns (load, weather, etc.)
- **Optional versioning**: Metadata tracking when data became available, enabling realistic backtesting

The class automatically validates that the datetime index is properly formatted and can optionally verify that the sample interval is consistent throughout the dataset.

Creating Datasets
^^^^^^^^^^^^^^^^^

Basic usage requires a DataFrame with a datetime index and a specified sample interval:

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
    
    print(dataset.feature_names)  # ['load', 'temperature']
    print(dataset.sample_interval)  # 0:15:00

The constructor validates the datetime index and stores metadata about the dataset structure. By default, it does not check that every row matches the sample interval exactly, allowing for datasets with gaps. Set ``check_frequency=True`` to enforce strict frequency validation.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

For backtesting scenarios, you need to track when each data point became available. ``TimeSeriesDataset`` supports two versioning approaches:

**Horizon-based versioning** tracks how far ahead each observation represents:

.. code-block:: python

    # Data with horizon column
    versioned_data = pd.DataFrame({
        'load': [100, 120, 115, 130],
        'horizon': pd.to_timedelta(['1h', '1h', '2h', '2h'])
    }, index=pd.date_range('2025-01-01', periods=4, freq='15min'))
    
    dataset = TimeSeriesDataset(
        versioned_data,
        sample_interval=timedelta(minutes=15)
    )
    
    print(dataset.is_versioned)  # True
    print(dataset.horizons)  # List of unique horizons

**Available-at versioning** explicitly stores when data became available:

.. code-block:: python

    # Data with available_at column
    data_with_availability = pd.DataFrame({
        'load': [100, 120, 115, 130],
        'available_at': pd.date_range('2025-01-01 01:00', periods=4, freq='15min')
    }, index=pd.date_range('2025-01-01', periods=4, freq='15min'))
    
    dataset = TimeSeriesDataset(
        data_with_availability,
        sample_interval=timedelta(minutes=15)
    )

Versioned datasets enable the ``openstef_beam`` package to perform realistic backtesting that respects data availability constraints.

Data Access and Filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides methods for temporal slicing and filtering:

.. code-block:: python

    # Slice by time range
    subset = dataset.slice(
        start=pd.Timestamp('2025-01-01 00:30'),
        end=pd.Timestamp('2025-01-01 01:00')
    )
    
    # Access underlying DataFrame
    df = dataset.data
    
    # Get feature columns only (excludes internal columns like horizon)
    features = dataset.feature_names

The class maintains internal state about which columns are metadata (like ``horizon`` or ``available_at``) versus actual features, ensuring operations focus on the relevant data.

Persistence
^^^^^^^^^^^

Datasets can be saved to and loaded from Parquet files, preserving all metadata:

.. code-block:: python

    # Save dataset
    dataset.save('forecast_data.parquet')
    
    # Load dataset
    loaded = TimeSeriesDataset.load(
        'forecast_data.parquet',
        sample_interval=timedelta(minutes=15)
    )

The Parquet format efficiently stores time series data while maintaining type information and supporting fast columnar access.

Base Classes and Mixins
------------------------

The ``openstef_core`` package defines several base classes that establish patterns used throughout OpenSTEF.

BaseModel and BaseConfig
^^^^^^^^^^^^^^^^^^^^^^^^^

``BaseModel`` extends Pydantic's ``BaseModel`` to provide a foundation for all OpenSTEF components. It enables:

- **Validation**: Automatic type checking and validation of component parameters
- **Serialization**: Conversion to/from dictionaries and JSON
- **Configuration**: Standard patterns for component configuration

``BaseConfig`` extends ``BaseModel`` with YAML file I/O capabilities:

.. code-block:: python

    from openstef_core.base_model import BaseConfig
    from pathlib import Path
    
    class ModelConfig(BaseConfig):
        learning_rate: float
        n_estimators: int
    
    # Write configuration
    config = ModelConfig(learning_rate=0.1, n_estimators=100)
    config.write_yaml(Path('model_config.yaml'))
    
    # Read configuration
    loaded_config = ModelConfig.read_yaml(Path('model_config.yaml'))

This pattern ensures consistent configuration management across all OpenSTEF components.

Transform Base Classes
^^^^^^^^^^^^^^^^^^^^^^

The ``Transform`` base class in ``openstef_core.mixins.transform`` defines the interface for data transformations. It follows the scikit-learn pattern with separate fit and transform phases:

.. code-block:: python

    from openstef_core.mixins.transform import Transform
    
    class MyTransform(Transform[pd.DataFrame, pd.DataFrame]):
        """Example transform that scales features."""
        
        def fit(self, data: pd.DataFrame) -> None:
            """Learn scaling parameters from data."""
            self.mean_ = data.mean()
            self.std_ = data.std()
        
        def transform(self, data: pd.DataFrame) -> pd.DataFrame:
            """Apply scaling to data."""
            return (data - self.mean_) / self.std_

Transforms support state serialization through the ``Stateful`` interface, allowing fitted transforms to be saved and reused. The ``openstef_models`` package builds on this foundation to provide production-ready feature engineering transforms.

Dataset Mixins
^^^^^^^^^^^^^^

``TimeSeriesDataset`` inherits from two mixins that provide specific capabilities:

- **TimeSeriesMixin**: Provides temporal operations like slicing, resampling, and time-based filtering
- **DatasetMixin**: Provides data access patterns, validation, and persistence operations

This composition-based design allows functionality to be shared across different dataset types while keeping the codebase maintainable.

Utilities and Types
-------------------

The ``openstef_core.utils`` module provides common utilities used throughout the library:

- **Datetime utilities**: Functions like ``align_datetime`` for rounding timestamps to specific intervals
- **Multiprocessing**: ``run_parallel`` for parallelizing operations across multiple cores
- **Type conversion**: ``timedelta_from_isoformat`` and ``timedelta_to_isoformat`` for serializing timedelta objects
- **Invariants**: ``not_none`` for asserting non-null values with proper type narrowing

The ``openstef_core.types`` module defines type aliases and custom types used across OpenSTEF:

.. code-block:: python

    from openstef_core.types import LeadTime, AvailableAt
    
    # LeadTime represents forecast horizons
    horizon: LeadTime = timedelta(hours=24)
    
    # AvailableAt represents data availability timestamps
    available: AvailableAt = pd.Timestamp('2025-01-01 12:00')

These type definitions improve code clarity and enable better static type checking with mypy.

Validation
----------

The ``openstef_core.datasets.validation`` module provides validation functions that ensure data integrity:

- **validate_datetime_column**: Verifies that a column contains valid datetime values
- **validate_timedelta_column**: Verifies that a column contains valid timedelta values
- **TimeSeriesValidationError**: Exception raised when validation fails

These validators are used internally by ``TimeSeriesDataset`` but can also be used directly when working with raw DataFrames before wrapping them in datasets.

Integration with Other Packages
--------------------------------

The ``openstef_core`` package serves as the foundation for the entire OpenSTEF library:

- **openstef_models**: Uses ``TimeSeriesDataset`` as input/output for all transforms and models. Transform base classes from core enable the feature engineering pipeline. See :doc:`models` for details on the transform ecosystem.

- **openstef_beam**: Operates on ``TimeSeriesDataset`` instances for backtesting and metrics calculation. Versioned datasets enable realistic simulation of forecasting scenarios. See :doc:`beam` for backtesting workflows.

- **openstef**: The main package orchestrates components from all packages, relying on core's data structures and base classes to ensure consistency.

By establishing these foundational patterns, ``openstef_core`` enables the rest of the library to focus on domain-specific functionality while maintaining a coherent architecture.