The Core Package (``openstef_core``)
=====================================

The ``openstef_core`` package is the foundation of OpenSTEF's V4 architecture. Every other package in the library — ``openstef_models``, ``openstef_beam``, and any custom extensions you write — builds on the abstractions defined here. This page explains the key data structures, type system, mixin-based design patterns, and transform interfaces that ``openstef_core`` provides.

.. mermaid:: diagrams/architecture/core_diagram_1.mmd

----

The Type System
---------------

Before looking at datasets, it helps to understand the small but important type layer that underpins everything else. ``openstef_core.types`` defines typed wrappers for the temporal and quantile concepts that appear throughout the forecasting pipeline.

**LeadTime** wraps a ``datetime.timedelta`` and serialises it as an ISO 8601 duration string (e.g., ``PT6H`` for six hours). Using a dedicated type rather than a raw ``timedelta`` ensures consistent round-tripping through Parquet metadata, JSON configuration, and Pydantic models.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime

    # Construct from a timedelta
    lt = LeadTime(timedelta(hours=6))
    print(str(lt))          # 'PT6H'
    print(repr(lt))         # "LeadTime('PT6H')"

    # Parse back from an ISO 8601 string
    lt2 = LeadTime.from_string("PT24H")
    print(lt2.value)        # datetime.timedelta(days=1)
    print(lt2.total_hours)  # 24.0

**AvailableAt** encodes when a particular version of data became available, relative to a reference day. It uses the format ``DnTHHMM[Timezone]``, where ``n`` is a day offset and ``HHMM`` is the time of day. For example, ``D-1T0600[Europe/Amsterdam]`` means "06:00 Amsterdam time on the previous day". This type is central to versioned datasets, which track how forecasts would have looked given only the data that was available at a specific moment in the past.

.. code-block:: python

    from openstef_core.types import AvailableAt

    avail = AvailableAt.from_string("D-1T0600[Europe/Amsterdam]")
    print(avail)  # D-1T0600[Europe/Amsterdam]

Both types inherit from ``PydanticStringPrimitive``, so they integrate naturally with Pydantic models and are automatically validated when used as model fields.

----

Dataset Classes
---------------

The ``openstef_core.datasets`` sub-package provides two concrete dataset classes that represent time series data at different levels of complexity.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the primary data container in OpenSTEF. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a consistent sampling interval across all rows. The class mixes in both ``TimeSeriesMixin`` (temporal query operations) and ``DatasetMixin`` (persistence and piping), giving every dataset a uniform interface regardless of where it originates.

Key properties exposed by ``TimeSeriesDataset``:

- ``index`` — the underlying ``pd.DatetimeIndex``
- ``sample_interval`` — the ``timedelta`` between consecutive observations
- ``feature_names`` — list of non-target column names
- ``is_versioned`` — whether the dataset carries horizon or availability metadata
- ``horizons`` — list of ``LeadTime`` values present in the dataset (if versioned)
- ``available_at_series`` — a ``pd.Series`` of ``AvailableAt`` values (if versioned)

The class guarantees data integrity by sorting rows on construction and validates that the datetime index and any temporal columns conform to expected types. Persistence is handled through Parquet, preserving all metadata including the sample interval and versioning columns.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

    # Build a simple dataset from a DataFrame
    index = pd.date_range("2024-01-01", periods=96, freq="15min")
    df = pd.DataFrame(
        {"load_mw": [100.0 + i * 0.5 for i in range(96)]},
        index=index,
    )

    ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    print(ds.sample_interval)   # 0:15:00
    print(ds.feature_names)     # ['load_mw']
    print(len(ds.index))        # 96

    # Save and reload, preserving metadata
    ds.to_parquet("load_data.parquet")
    ds_loaded = TimeSeriesDataset.read_parquet("load_data.parquet")

The ``pipe`` method, inherited from ``DatasetMixin``, lets you chain transformations in a readable, functional style — similar to the ``DataFrame.pipe`` pattern you may already know from pandas:

.. code-block:: python

    def add_hour_feature(dataset: TimeSeriesDataset) -> TimeSeriesDataset:
        df = dataset.to_dataframe().copy()
        df["hour"] = df.index.hour
        return TimeSeriesDataset(df, sample_interval=dataset.sample_interval)

    ds_with_hour = ds.pipe(add_hour_feature)

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` extends the dataset concept to handle the reality of operational forecasting: the data available when a forecast is *made* is not the same as the data available in hindsight. It composes multiple ``TimeSeriesDataset`` parts, each representing a different "version" of the data, and exposes methods for selecting the view that would have been visible at a given point in time.

This is particularly important for honest backtesting. When evaluating a model's historical performance, you must ensure it only sees features that would have been available at forecast time — not data that arrived later. ``VersionedTimeSeriesDataset`` makes this constraint explicit and enforceable.

.. code-block:: python

    from openstef_core.datasets.versioned_timeseries_dataset import (
        VersionedTimeSeriesDataset,
    )
    from openstef_core.types import AvailableAt

    # Combine two dataset parts with different availability timestamps
    # (ds_early was available at D-1T0600, ds_late at D0T0000)
    versioned = VersionedTimeSeriesDataset.from_parts(
        [ds_early, ds_late],
        available_at=[
            AvailableAt.from_string("D-1T0600[Europe/Amsterdam]"),
            AvailableAt.from_string("D0T0000[Europe/Amsterdam]"),
        ],
    )

    # Select only the data that would have been visible at a specific moment
    snapshot = versioned.select_version(
        AvailableAt.from_string("D-1T0600[Europe/Amsterdam]")
    )

.. note::

   Backtesting utilities in ``openstef_beam`` consume ``VersionedTimeSeriesDataset``
   directly. See the :doc:`beam` page for how versioned datasets feed into
   distributed evaluation pipelines.

----

The Mixin Architecture
-----------------------

``openstef_core`` uses Python protocols and mixins rather than deep inheritance hierarchies. This is a deliberate design choice: it keeps classes composable and makes it straightforward to add new dataset types without touching existing code.

The two primary mixins are:

- **``TimeSeriesMixin``** — provides temporal query methods such as slicing by time range, calculating time coverage, and selecting by lead time or availability.
- **``DatasetMixin``** — provides persistence (``to_parquet`` / ``read_parquet``) and the ``pipe`` method for functional chaining.

Both are defined as ``Protocol`` classes, meaning any class that implements the required methods satisfies the interface without needing to subclass explicitly. This makes ``openstef_core`` types easy to use in type-checked code and straightforward to mock in tests.

----

Transform Interfaces
--------------------

The ``openstef_core.transforms`` sub-package defines abstract base classes for data transformations. These follow the scikit-learn convention of separate ``fit`` and ``transform`` phases, allowing stateful transforms that learn parameters from training data before being applied to new observations.

Two specialised abstract classes are provided:

- **``TimeSeriesTransform``** — operates on ``TimeSeriesDataset`` inputs and outputs.
- **``VersionedTimeSeriesTransform``** — operates on ``VersionedTimeSeriesDataset``, useful for transforms that must respect data availability boundaries.

Both inherit from the generic ``Transform[InputT, OutputT]`` mixin defined in ``openstef_core.mixins``.

.. code-block:: python

    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset


    class NormalisationTransform(TimeSeriesTransform):
        """Normalise each feature column to zero mean and unit variance."""

        def fit(self, dataset: TimeSeriesDataset) -> "NormalisationTransform":
            df = dataset.to_dataframe()
            self._mean = df.mean()
            self._std = df.std().replace(0, 1)  # avoid division by zero
            return self

        def transform(self, dataset: TimeSeriesDataset) -> TimeSeriesDataset:
            df = dataset.to_dataframe()
            normalised = (df - self._mean) / self._std
            return TimeSeriesDataset(normalised, sample_interval=dataset.sample_interval)


    # Usage
    transform = NormalisationTransform()
    transform.fit(ds)
    ds_normalised = transform.transform(ds)

.. note::

   The ``openstef_models`` package provides a rich library of ready-made transforms
   for energy-specific feature engineering — solar irradiance decomposition,
   calendar features, lag generation, and more. See :doc:`models` for details.
   The interfaces defined here in ``openstef_core`` are the contracts those
   transforms fulfil.

----

Utilities
---------

``openstef_core.utils`` contains helpers that are used pervasively across the library:

- **``timedelta_from_isoformat`` / ``timedelta_to_isoformat``** — convert between ``timedelta`` objects and ISO 8601 duration strings, used internally by ``LeadTime`` and Parquet serialisation.
- **``openstef_core.utils.pandas``** — low-level pandas helpers including ``unsafe_sorted_range_slice_idxs`` for efficient index slicing and ``combine_timeseries_indexes`` for merging multi-part dataset indexes.

These utilities are intentionally kept small and focused. They solve problems that arise repeatedly when working with time series data in pandas and are available for use in your own transforms and pipelines.

----

How Core Provides the Foundation
---------------------------------

The relationship between ``openstef_core`` and the rest of OpenSTEF is straightforward: ``openstef_core`` defines *what data looks like* and *how transformations are structured*; the other packages define *what to do with that data*.

- ``openstef_models`` implements ``TimeSeriesTransform`` and ``VersionedTimeSeriesTransform`` to provide feature engineering steps and wraps scikit-learn-compatible estimators in interfaces that accept ``TimeSeriesDataset`` directly.
- ``openstef_beam`` uses ``VersionedTimeSeriesDataset`` as the unit of work in its distributed backtesting pipelines, relying on the ``select_version`` method to reconstruct historically accurate training windows.

Because ``openstef_core`` depends only on ``pandas``, ``pydantic``, and the Python standard library, it is lightweight enough to import in any context — including environments where you may not want the full model or Beam dependencies.

.. note::

   If you are building a custom integration or extending OpenSTEF for a new use
   case, start with ``openstef_core``. Implementing the ``TimeSeriesTransform``
   interface and working with ``TimeSeriesDataset`` gives you immediate
   compatibility with the rest of the library.