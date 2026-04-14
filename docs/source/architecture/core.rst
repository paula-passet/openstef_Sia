The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. It defines the shared data structures, type system, abstract base classes, and utilities that every other package depends on. Understanding ``openstef-core`` is key to understanding how the library fits together — it establishes the contracts that models, transforms, and evaluation pipelines all speak.

This page covers the internal structure of ``openstef-core``: its dataset classes, domain types, transform abstractions, and configuration utilities. For how transforms are applied in practice, see the :doc:`models` page. For evaluation and backtesting workflows that consume these structures, see the :doc:`beam` page.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

Package Overview
----------------

``openstef-core`` is intentionally narrow in scope. It does not implement any forecasting models or evaluation logic — those live in ``openstef-models`` and ``openstef-beam`` respectively. Instead, it provides:

- **Domain types** — validated, serializable wrappers for temporal concepts like lead times and data availability offsets
- **Dataset classes** — a ``TimeSeriesDataset`` that enforces structural guarantees on time series data
- **Transform abstractions** — scikit-learn-style base classes for stateful, fittable data transformations
- **Configuration utilities** — Pydantic-based models for reading and writing YAML configuration

This separation keeps the library modular. A downstream package can depend on ``openstef-core`` for its interfaces without pulling in the full model stack.

Domain Types
------------

The ``openstef_core.types`` module defines typed wrappers for the temporal concepts that appear throughout the forecasting pipeline. Rather than passing raw ``timedelta`` or ``datetime`` objects, OpenSTEF uses validated types that carry serialization semantics and domain meaning.

**LeadTime**

``LeadTime`` wraps a ``timedelta`` and serializes it as an ISO 8601 duration string (e.g., ``"PT1H"`` for one hour). It supports ordering and arithmetic, and can be constructed from a string, a ``timedelta``, or another ``LeadTime``:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime

   # Construct from ISO 8601 string
   lead = LeadTime.from_string("PT4H")
   print(lead.to_hours())  # 4.0

   # Construct from timedelta
   lead2 = LeadTime.validate(timedelta(hours=24))
   print(str(lead2))  # "PT24H"

   # LeadTime supports comparison
   assert LeadTime.from_string("PT1H") < LeadTime.from_string("PT6H")

**AvailableAt**

``AvailableAt`` represents a data availability offset relative to a reference day, expressed in the format ``DnTHHMM[tz]``. This is used to model the real-world constraint that measurements and forecasts are not always available immediately — a weather forecast issued at 06:00 UTC on the day before the target period has a specific ``AvailableAt`` value that the pipeline can reason about.

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_core.types import AvailableAt

   availability = AvailableAt.from_string("D0T0600UTC")
   reference = datetime(2025, 6, 1, tzinfo=timezone.utc)
   print(availability.apply(reference))  # 2025-06-01 06:00:00+00:00

Both types inherit from ``PydanticStringPrimitive``, which provides consistent Pydantic validation and round-trip string serialization. This means they integrate cleanly into any Pydantic model used for configuration or data contracts.

The TimeSeriesDataset
---------------------

``TimeSeriesDataset`` is the central data structure in ``openstef-core``. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a consistent sampling interval across all rows. All data passed through the OpenSTEF pipeline is represented as a ``TimeSeriesDataset`` or its versioned subclass.

**Construction**

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   data = pd.DataFrame(
       {
           "temperature": [20.1, 22.3, 21.5, 19.8],
           "load": [100.0, 120.0, 110.0, 105.0],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

   print(dataset.feature_names)   # ['temperature', 'load']
   print(dataset.sample_interval) # 0:15:00
   print(dataset.is_versioned)    # False

On construction, the dataset automatically sorts data by timestamp and validates that the index is a proper ``DatetimeIndex``. The ``feature_names`` property returns all columns that are not internal bookkeeping columns (such as ``horizon`` or ``available_at``).

**Versioned Datasets**

A ``TimeSeriesDataset`` becomes *versioned* when it contains either a ``horizon`` column (tracking forecast lead times) or an ``available_at`` column (tracking when each data point became available). Versioning is detected automatically:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   data = pd.DataFrame(
       {
           "load": [100.0, 120.0, 115.0],
           "horizon": pd.to_timedelta(["1h", "2h", "3h"]),
       },
       index=pd.date_range("2025-01-01", periods=3, freq="1h"),
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))

   print(dataset.is_versioned)  # True
   print(dataset.horizons)      # list of LeadTime values

The ``VersionedTimeSeriesDataset`` subclass (from ``openstef_core.datasets``) extends this with richer filtering and slicing operations suited to multi-horizon forecasting scenarios.

**Key Guarantees**

The dataset class enforces several invariants that the rest of the library relies on:

- Data is always sorted by timestamp in ascending order
- The ``DatetimeIndex`` is named ``"timestamp"``
- The sampling interval is consistent and explicitly declared
- Internal columns (``horizon``, ``available_at``) are excluded from ``feature_names``

These guarantees mean that downstream transforms and models can make assumptions about data layout without defensive checks.

Transform Abstractions
----------------------

``openstef-core`` defines the abstract base classes for all data transformations in the library. These live in ``openstef_core.mixins.transform`` and follow the scikit-learn pattern of separate ``fit`` and ``transform`` phases.

The class hierarchy is:

- ``Stateful`` — base class providing state management and serialization via Pydantic
- ``Transform[I, O]`` — generic abstract base parameterized by input and output types
- ``TimeSeriesTransform`` — concrete abstract base for ``TimeSeriesDataset → TimeSeriesDataset`` transforms
- ``VersionedTimeSeriesTransform`` — variant for versioned dataset transforms

.. code-block:: python

   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class RollingMeanFeature(TimeSeriesTransform):
       """Adds a rolling mean of 'load' as a new feature column."""

       window: int = 4  # Pydantic field — serializable

       def fit(self, data: TimeSeriesDataset) -> None:
           # No parameters to learn in this example
           pass

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df["load_rolling_mean"] = df["load"].rolling(self.window).mean()
           return TimeSeriesDataset(df, sample_interval=data.sample_interval)

       @property
       def features_added(self) -> list[str]:
           return ["load_rolling_mean"]

Because ``Transform`` inherits from ``Stateful`` (which is itself a Pydantic ``BaseModel``), any fields declared on a transform subclass are automatically serializable. This enables transforms to be saved and restored as part of a pipeline without custom pickling logic.

The ``is_fitted()`` method on ``Transform`` lets callers check whether ``fit`` has been called before invoking ``transform``, providing a clear error boundary.

Configuration Utilities
-----------------------

``openstef-core`` provides ``BaseModel`` and ``BaseConfig`` — thin Pydantic wrappers that add YAML serialization to any configuration object:

.. code-block:: python

   from pathlib import Path
   from openstef_core.base_model import BaseConfig


   class ForecastConfig(BaseConfig):
       horizon_hours: int = 24
       sample_interval_minutes: int = 15
       target_column: str = "load"


   config = ForecastConfig(horizon_hours=48, target_column="net_load")

   # Write to YAML
   config.write_yaml(Path("forecast_config.yaml"))

   # Read back
   loaded = ForecastConfig.read_yaml(Path("forecast_config.yaml"))
   assert loaded.horizon_hours == 48

The module-level helpers ``write_yaml_config`` and ``read_yaml_config`` support the same pattern for cases where the config type is determined at runtime rather than statically.

How Core Provides the Foundation
---------------------------------

Every other OpenSTEF package imports from ``openstef-core`` but not vice versa. This one-way dependency is what makes the library modular:

- ``openstef-models`` imports ``TimeSeriesDataset``, ``TimeSeriesTransform``, and ``VersionedTimeSeriesTransform`` to build its preprocessing pipelines and model interfaces
- ``openstef-beam`` imports the same dataset types to define the inputs and outputs of its backtesting and evaluation runners
- Both packages use ``LeadTime`` and ``AvailableAt`` to express temporal constraints in a consistent, validated way

The practical consequence is that code written against ``openstef-core`` interfaces — a custom transform, a configuration class, a dataset loader — will work with any part of the library without modification.

.. note::

   When writing custom transforms or extending the pipeline, always subclass from ``openstef-core`` abstractions rather than implementing the interface from scratch. This ensures your code participates correctly in serialization, state management, and pipeline composition.

Testing Utilities
-----------------

``openstef-core`` ships a ``create_timeseries_dataset`` factory function intended for use in tests. It provides a concise way to construct ``TimeSeriesDataset`` instances with controlled properties:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import create_timeseries_dataset

   index = pd.date_range("2025-01-01", periods=96, freq="15min")

   dataset = create_timeseries_dataset(
       index=index,
       sample_interval=timedelta(minutes=15),
       load=pd.Series([100.0] * 96, index=index),
       temperature=pd.Series([15.0] * 96, index=index),
   )

   print(len(dataset.data))       # 96
   print(dataset.feature_names)  # ['load', 'temperature']

This factory handles index alignment and optional ``available_at`` / ``horizon`` columns, making it straightforward to construct realistic test fixtures without boilerplate.

Further Reading
---------------

- :doc:`models` — how ``openstef-models`` builds on these abstractions to implement preprocessing transforms and forecasting pipelines
- :doc:`beam` — how ``openstef-beam`` uses ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` in backtesting and metrics evaluation