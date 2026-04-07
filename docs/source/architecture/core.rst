Core Package (``openstef_core``)
================================

The ``openstef_core`` package provides the foundational data structures, configuration base classes, and utility functions that underpin the entire OpenSTEF library. Every other package---``openstef_models`` for machine learning and ``openstef_beam`` for evaluation---depends on ``openstef_core`` for consistent data handling and shared conventions.

This page covers the internal structure of the core package in detail: the ``TimeSeriesDataset`` class, the configuration system built on Pydantic, the utility toolkit, and the exception hierarchy.

.. note:: [DIAGRAM: Component diagram showing openstef_core internal structure. Four modules arranged horizontally: ``datasets`` (containing TimeSeriesDataset, mixins, validated datasets), ``base_model`` (containing BaseModel, BaseConfig, YAML helpers), ``utils`` (containing datetime alignment, multiprocessing, serialization), and ``exceptions`` (containing custom exception classes). Arrows from openstef_models and openstef_beam point inward to openstef_core, indicating dependency.]

Package Structure
-----------------

The core package is organized into four modules:

- **datasets** --- The ``TimeSeriesDataset`` class and its validated variants for representing time series data with consistent sampling intervals and optional versioning.
- **base_model** --- Pydantic-based configuration classes (``BaseModel``, ``BaseConfig``) with YAML serialization support.
- **utils** --- Shared utility functions for datetime alignment, parallel processing, and type conversion.
- **exceptions** --- Custom exception types used throughout OpenSTEF.


TimeSeriesDataset
-----------------

``TimeSeriesDataset`` is the central data abstraction in OpenSTEF. It wraps a pandas ``DataFrame`` with a ``DatetimeIndex`` and enforces a regular sampling interval, providing a type-safe container that other components can rely on.

Creating a Dataset
^^^^^^^^^^^^^^^^^^

At its simplest, you pass a DataFrame with a ``DatetimeIndex`` and a sample interval:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Create a simple time series
   index = pd.date_range("2025-01-01", periods=96, freq="15min")
   data = pd.DataFrame({"load": range(96)}, index=index)

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

   print(dataset.sample_interval)   # timedelta(minutes=15)
   print(dataset.feature_names)     # ['load']
   print(dataset.is_versioned)      # False

The constructor validates that the index is a ``DatetimeIndex`` and optionally checks that the data frequency matches the declared ``sample_interval`` (when ``check_frequency=True``).

Versioned Datasets
^^^^^^^^^^^^^^^^^^

Energy forecasting often involves multiple forecast horizons---predictions made at different lead times. ``TimeSeriesDataset`` natively supports this through versioning columns:

- **horizon column** --- A ``timedelta`` column indicating the forecast horizon (e.g., 1 hour ahead, 2 hours ahead).
- **available_at column** --- A ``datetime`` column indicating when a particular data point became available.

If either column is present, the dataset is automatically detected as versioned:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   data = pd.DataFrame({
       "load": [100, 120, 100, 120],
       "horizon": pd.to_timedelta(["1h", "2h", "1h", "2h"]),
   }, index=pd.date_range("2025-01-01", periods=4, freq="1h"))

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))

   print(dataset.is_versioned)  # True
   print(dataset.horizons)      # list of LeadTime values

You can then filter to a single horizon:

.. code-block:: python

   from openstef_core.datasets import LeadTime

   horizon_1h = dataset.select_horizon(LeadTime(timedelta(hours=1)))

Key Methods and Properties
^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides a rich interface for data manipulation:

**Data access:**

- ``data`` --- The underlying pandas ``DataFrame``.
- ``feature_names`` --- List of feature column names (excludes internal columns like ``horizon``).
- ``sample_interval`` --- The fixed interval between data points.
- ``is_versioned`` --- Whether the dataset contains versioning information.
- ``horizons`` --- List of available ``LeadTime`` values (``None`` if not versioned).

**Filtering and selection:**

- ``select_horizon(horizon)`` --- Return a new dataset for a specific forecast horizon.
- ``select_features(feature_names)`` --- Return a new dataset with only the specified features.
- ``filter_index(mask)`` --- Return a new dataset containing only timestamps present in the mask.

**Serialization:**

- ``to_pandas()`` --- Convert to a DataFrame, storing metadata (sample interval, column names) in ``df.attrs``.
- ``from_pandas(df)`` --- Reconstruct a dataset from a DataFrame with metadata in ``attrs``.
- ``to_parquet(path)`` / ``read_parquet(path)`` --- Persist to and load from Parquet files.

**Transformation:**

- ``pipe_pandas(func, *args, **kwargs)`` --- Apply an arbitrary pandas transformation function while preserving dataset metadata.
- ``copy_with(data)`` --- Create a copy of the dataset with new data but the same configuration.

.. code-block:: python

   # Round-trip through pandas
   df = dataset.to_pandas()
   restored = TimeSeriesDataset.from_pandas(df)

   # Save and load from Parquet
   dataset.to_parquet("forecast_data.parquet")
   loaded = TimeSeriesDataset.read_parquet("forecast_data.parquet")

   # Apply a pandas transformation
   normalized = dataset.pipe_pandas(lambda df: (df - df.mean()) / df.std())


Configuration System (``base_model``)
--------------------------------------

OpenSTEF uses Pydantic for configuration management. The ``base_model`` module provides two base classes and YAML helpers that all configuration objects inherit from.

BaseModel
^^^^^^^^^

``BaseModel`` extends Pydantic's ``BaseModel`` with OpenSTEF-specific defaults:

.. code-block:: python

   from openstef_core.base_model import BaseModel

   class ForecastTarget(BaseModel):
       name: str
       location_id: int
       sample_interval_minutes: int = 15

   target = ForecastTarget(name="substation_a", location_id=42)

The base class configures ``arbitrary_types_allowed=True`` and serializes ``inf``/``NaN`` as ``null`` in JSON---both important for energy data that may contain missing values.

BaseConfig
^^^^^^^^^^

``BaseConfig`` adds YAML file support, making it straightforward to manage forecasting configurations:

.. code-block:: python

   from openstef_core.base_model import BaseConfig, write_yaml_config, read_yaml_config

   class PipelineConfig(BaseConfig):
       model_type: str = "xgboost"
       horizons: list[str] = ["1h", "6h", "24h"]
       retrain_interval_days: int = 7

   config = PipelineConfig()
   write_yaml_config(config, "pipeline.yaml")

   loaded_config = read_yaml_config("pipeline.yaml", PipelineConfig)

The ``PydanticStringPrimitive`` base class is also provided for creating custom types that serialize to strings in Pydantic models---used internally for types like ``LeadTime``.


Utility Functions (``utils``)
-----------------------------

The ``utils`` module collects small, focused helpers used across the library:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Function
     - Purpose
   * - ``align_datetime(timestamp, interval)``
     - Round a timestamp to the nearest interval boundary (floor or ceil).
   * - ``align_datetime_to_time(timestamp, align_time)``
     - Snap a timestamp to the nearest occurrence of a specific time of day.
   * - ``run_parallel(process_fn, items)``
     - Execute a function across items using multiprocessing.
   * - ``timedelta_to_isoformat(td)``
     - Convert a ``timedelta`` to an ISO 8601 duration string.
   * - ``timedelta_from_isoformat(s)``
     - Parse an ISO 8601 duration string back to a ``timedelta``.
   * - ``not_none(value)``
     - Assert that a value is not ``None``, raising ``TypeError`` otherwise.

Example---aligning timestamps to 15-minute boundaries:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.utils import align_datetime

   ts = datetime(2025, 6, 15, 14, 7, 30)
   aligned = align_datetime(ts, timedelta(minutes=15))
   print(aligned)  # 2025-06-15 14:00:00


Custom Exceptions (``exceptions``)
-----------------------------------

The ``exceptions`` module defines a hierarchy of exception types that provide clear, actionable error messages. Rather than raising generic ``ValueError`` or ``RuntimeError``, OpenSTEF components raise domain-specific exceptions that callers can catch and handle appropriately.

This is particularly useful when integrating OpenSTEF into larger systems where different error types require different recovery strategies (e.g., retrying on data availability errors versus alerting on configuration errors).


How Core Supports Other Packages
---------------------------------

The core package is deliberately minimal---it contains no machine learning logic and no evaluation code. This separation provides several benefits:

- **openstef_models** depends on ``openstef_core`` for ``TimeSeriesDataset`` as input/output to model training and prediction, and for ``BaseModel`` as the base class for model configurations. See :doc:`models` for details.
- **openstef_beam** depends on ``openstef_core`` for ``TimeSeriesDataset`` as the data format for backtesting and metrics computation, and for ``BaseConfig`` with YAML support for evaluation configurations. See :doc:`beam` for details.

This layered design means you can use ``openstef_core`` on its own for data handling without pulling in ML dependencies, and each higher-level package builds on a stable, well-tested foundation.

.. note:: [DIAGRAM: Dependency flow diagram. Three boxes stacked: ``openstef_beam`` (top) depends on both ``openstef_models`` (middle) and ``openstef_core`` (bottom). ``openstef_models`` depends on ``openstef_core``. Arrows point downward showing dependency direction.]


Further Reading
---------------

- :doc:`models` --- How ``openstef_models`` uses core data structures for feature engineering and model training.
- :doc:`beam` --- How ``openstef_beam`` uses core data structures for backtesting and evaluation.
- Full API reference: :doc:`/api/generated/openstef_core.datasets`, :doc:`/api/generated/openstef_core.base_model`, :doc:`/api/generated/openstef_core.utils`.