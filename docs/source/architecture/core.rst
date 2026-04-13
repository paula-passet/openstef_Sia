The Core Package
================

The ``openstef_core`` package is the foundation on which the rest of OpenSTEF is built. It defines the primary data structures, abstract base classes, protocol interfaces, and utility functions that every other package in the library depends on. This page explains how those building blocks fit together and how to use them directly when extending or integrating with OpenSTEF.

.. mermaid:: diagrams/architecture/core_diagram_1.mmd

----

Package Layout
--------------

``openstef_core`` is organised into four cohesive sub-packages:

- **datasets** — ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and validated domain-specific dataset classes.
- **mixins** — Protocol interfaces and abstract base classes (``TimeSeriesMixin``, ``DatasetMixin``, ``Transform``, ``Stateful``).
- **transforms** — Abstract transform interfaces that specialise the mixin layer for time series use cases.
- **utils** — Datetime alignment helpers, invariant checks, pandas utilities, and multiprocessing support.

Each sub-package has a narrow responsibility. The datasets layer is the most visible to library users; the mixins and utils layers are what you reach for when writing new components that integrate with OpenSTEF.

----

Datasets
--------

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the central data structure in OpenSTEF. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a consistent sampling interval across all rows. Every pipeline stage — from feature engineering through model training to forecast output — passes data through this type.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Build a simple time series with two feature columns
    index = pd.date_range("2025-01-01", periods=96, freq="15min")
    data = pd.DataFrame(
        {
            "load_mw": [100.0 + i * 0.5 for i in range(96)],
            "temperature": [5.0 + i * 0.02 for i in range(96)],
        },
        index=index,
    )

    dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

    print(dataset.feature_names)   # ['load_mw', 'temperature']
    print(dataset.is_versioned)    # False
    print(dataset.sample_interval) # 0:15:00

The constructor sorts the data by timestamp automatically and optionally validates that the index frequency matches ``sample_interval`` when ``check_frequency=True``.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

A ``TimeSeriesDataset`` becomes *versioned* when its underlying ``DataFrame`` contains either a ``horizon`` column (``timedelta`` values) or an ``available_at`` column (``datetime`` values). Versioning lets the dataset represent the state of knowledge at a particular point in time — essential for realistic backtesting.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    index = pd.date_range("2025-01-01", periods=4, freq="1h")
    data = pd.DataFrame(
        {
            "load_mw": [110.0, 115.0, 108.0, 120.0],
            "horizon": pd.to_timedelta(["1h", "2h", "3h", "4h"]),
        },
        index=index,
    )

    versioned = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))
    print(versioned.is_versioned)  # True
    print(versioned.horizons)      # [Timedelta('0 days 01:00:00'), ...]

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

For scenarios where data arrives in multiple parts (for example, different forecast horizons produced by separate model runs), ``VersionedTimeSeriesDataset`` composes several ``TimeSeriesDataset`` instances into a single logical dataset. It validates that all constituent parts share the same sampling interval and that their columns do not overlap.

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Compose two dataset parts into a single versioned view
    combined = VersionedTimeSeriesDataset.from_parts([part_1h, part_24h])

Domain-Specific Validated Datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``openstef_core.datasets.validated_datasets`` module provides subclasses that add domain validation on top of ``TimeSeriesDataset``:

- ``ForecastInputDataset`` — validates that the required input features for a forecast are present.
- ``ForecastDataset`` — validates forecast output columns and horizons.
- ``EnsembleForecastDataset`` — wraps ensemble member forecasts.
- ``EnergyComponentDataset`` — validates energy component decompositions.

These classes raise ``TimeSeriesValidationError`` on construction if the data does not meet their requirements, catching problems early rather than propagating bad data through a pipeline.

----

Mixins and Protocols
--------------------

The ``openstef_core.mixins`` sub-package defines the contracts that datasets and transforms must satisfy. Using Python protocols means that components can be type-checked without requiring a rigid class hierarchy.

TimeSeriesMixin and DatasetMixin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesMixin`` declares the filtering and versioning interface that every dataset must expose: methods for slicing by time range, restricting to specific horizons, and querying availability. ``DatasetMixin`` adds persistence — ``save`` and ``load`` class methods backed by Parquet.

Any class that implements these two protocols is compatible with the rest of the OpenSTEF pipeline, regardless of its inheritance chain.

Transform Base Class
^^^^^^^^^^^^^^^^^^^^

``Transform[I, O]`` is the generic abstract base for all data transformations. It follows the scikit-learn ``fit`` / ``transform`` pattern and inherits from ``Stateful``, which provides serialisation support so that fitted transform state can be persisted alongside a trained model.

.. code-block:: python

    from openstef_core.mixins import Transform
    from openstef_core.datasets import TimeSeriesDataset

    class MyScaler(Transform[TimeSeriesDataset, TimeSeriesDataset]):
        """Scales a single feature column by a fixed factor."""

        def __init__(self, column: str, factor: float) -> None:
            self.column = column
            self.factor = factor

        def fit(self, data: TimeSeriesDataset) -> None:
            # Stateless transform — nothing to learn
            pass

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            scaled = data.data.copy()
            scaled[self.column] = scaled[self.column] * self.factor
            return TimeSeriesDataset(scaled, sample_interval=data.sample_interval)

The ``openstef_core.transforms.dataset_transforms`` module provides two ready-made specialisations of this pattern:

- ``TimeSeriesTransform`` — operates on ``TimeSeriesDataset`` inputs and outputs.
- ``VersionedTimeSeriesTransform`` — operates on ``VersionedTimeSeriesDataset``.

These are the base classes to subclass when writing transforms for use with the models package. See the :doc:`models` page for concrete transform implementations.

----

Utilities
---------

The ``openstef_core.utils`` package collects small, focused helpers used throughout the library.

Datetime Alignment
^^^^^^^^^^^^^^^^^^

Forecast pipelines frequently need to snap timestamps to interval boundaries. ``align_datetime`` does this with a modulo approach and supports both ceiling and floor modes:

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef_core.utils import align_datetime

    ts = datetime(2025, 6, 15, 14, 37, 22)
    interval = timedelta(minutes=15)

    # Snap up to the next 15-minute boundary
    ceiled = align_datetime(ts, interval, mode="ceil")
    print(ceiled)  # 2025-06-15 14:45:00

    # Snap down to the previous 15-minute boundary
    floored = align_datetime(ts, interval, mode="floor")
    print(floored)  # 2025-06-15 14:30:00

``align_datetime_to_time`` provides the same behaviour but aligns to a specific time-of-day rather than a fixed interval — useful when constructing training windows that must start at midnight.

Invariant Checking
^^^^^^^^^^^^^^^^^^

``not_none`` is a lightweight runtime guard that asserts a value is not ``None`` and narrows its type for the type checker:

.. code-block:: python

    from openstef_core.utils import not_none

    horizons = dataset.horizons
    # horizons is list[LeadTime] | None here
    first = not_none(horizons)[0]
    # first is LeadTime — no Optional unwrapping needed

Timedelta Serialisation
^^^^^^^^^^^^^^^^^^^^^^^

``timedelta_to_isoformat`` and ``timedelta_from_isoformat`` convert between Python ``timedelta`` objects and ISO 8601 duration strings (e.g. ``"PT15M"``). These are used internally when serialising dataset metadata to Parquet and JSON, but are also useful when building configuration-driven pipelines:

.. code-block:: python

    from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat
    from datetime import timedelta

    iso = timedelta_to_isoformat(timedelta(hours=24))
    print(iso)  # 'PT24H' (or equivalent ISO 8601 form)

    restored = timedelta_from_isoformat(iso)
    assert restored == timedelta(hours=24)

Parallel Execution
^^^^^^^^^^^^^^^^^^

``run_parallel`` wraps Python's ``multiprocessing`` to apply a callable across an iterable of inputs. It is used internally by the beam package for local execution but is available directly when you need to parallelise a custom preprocessing step.

----

How Other Packages Depend on Core
----------------------------------

The dependency relationship is strictly one-directional:

- **openstef_models** imports ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and the ``Transform`` base classes from ``openstef_core`` to define its feature engineering pipeline and model interfaces. See the :doc:`models` page for details on how transforms are composed into pipelines.
- **openstef_beam** imports the same dataset types and uses them as the unit of data flowing through Apache Beam pipelines. Backtesting and metrics computation in that package all operate on ``TimeSeriesDataset`` instances. See the :doc:`beam` page for how this is orchestrated at scale.

Neither package modifies or re-exports core types — they consume them. This means that code written against ``openstef_core`` types is automatically compatible with both the local and distributed execution paths.

.. note::

   When writing a custom component — a new transform, a custom validator, or a bespoke data loader — import from ``openstef_core`` directly rather than from the higher-level packages. This keeps your component decoupled from execution-environment concerns and makes it reusable across both ``openstef_models`` and ``openstef_beam``.

----

Further Reading
---------------

- :doc:`models` — Transform implementations and model interfaces built on top of ``openstef_core``.
- :doc:`beam` — Distributed backtesting and metrics pipelines that consume ``openstef_core`` data structures.