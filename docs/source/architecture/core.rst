The Core Package
================

The ``openstef_core`` package is the foundation on which the rest of OpenSTEF is built. It defines the canonical data structures for time series data, the abstract base classes that govern how transforms and models behave, and a collection of utility functions that the higher-level packages—``openstef_models``, ``openstef_beam``, and ``openstef_meta``—all depend on. Understanding ``openstef_core`` is the key to understanding how the library fits together.

This page covers the internal structure of ``openstef_core``: the dataset classes, the mixin/protocol system, the domain type definitions, and the utility layer.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

----

Dataset Classes
---------------

The ``datasets`` sub-package provides the primary data container used throughout OpenSTEF.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the workhorse of the library. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a fixed ``sample_interval``, guaranteeing that every downstream component—transforms, models, and evaluation pipelines—can rely on a consistent temporal structure.

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
   print(dataset.is_versioned)    # False
   print(dataset.sample_interval) # 0:15:00

On construction the class validates that the index is a ``DatetimeIndex``, sorts the data in ascending order, and optionally checks that the observed frequency matches the declared ``sample_interval``. Passing ``is_sorted=True`` skips the sort step when you already know the data is ordered, which matters for performance in tight loops.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

Real forecasting data is rarely a single clean time series. Observations arrive at different times, and a model trained today may need to know which data *was available* at the time a forecast was issued. ``TimeSeriesDataset`` handles this through two optional versioning columns:

- **horizon_column** — each row carries a ``timedelta`` indicating how far ahead the value was forecast.
- **available_at_column** — each row carries a timestamp indicating when the data became available.

When either column is present, ``dataset.is_versioned`` returns ``True``. The higher-level ``VersionedTimeSeriesDataset`` wraps multiple ``TimeSeriesDataset`` parts and provides a ``to_horizons()`` method that assembles a single horizon-indexed dataset from the versioned parts:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Two data parts with different availability times
   part_a = pd.DataFrame(
       {"load": [100.0, 120.0], "temperature": [20.0, 22.0]},
       index=pd.DatetimeIndex(
           ["2025-01-01T10:00:00", "2025-01-01T10:15:00"], name="timestamp"
       ),
   )
   versioned = VersionedTimeSeriesDataset.from_dataframe(
       part_a, timedelta(minutes=15)
   )

   # Convert to horizon-indexed format for model training
   horizons = [timedelta(hours=1), timedelta(hours=4)]
   horizon_dataset = versioned.to_horizons(horizons)

.. note::

   ``VersionedTimeSeriesDataset`` is the entry point used by the backtesting
   pipelines in ``openstef_beam``. See the :doc:`beam` page for how versioned
   datasets feed into walk-forward evaluation.

----

The Mixin and Protocol System
------------------------------

``openstef_core`` uses Python protocols (``typing.Protocol``) rather than deep inheritance hierarchies. This keeps the library composable: a class only needs to satisfy a protocol's interface to be treated as a valid dataset or transform—it does not need to inherit from a specific base class.

The two core protocols are:

- **TimeSeriesMixin** — defines the essential read interface: ``feature_names``, ``sample_interval``, ``is_versioned``, and temporal filtering methods.
- **DatasetMixin** — defines the persistence interface: ``save()`` and ``load()`` for round-tripping datasets to disk while preserving all metadata.

``TimeSeriesDataset`` implements both, which is why it can be passed to any function that accepts either protocol.

The ``Transform`` Generic Base
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``openstef_core.mixins.Transform`` class is a generic abstract base that follows the scikit-learn ``fit`` / ``transform`` pattern. It is parameterised over its input and output dataset types:

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   class NormalisationTransform(TimeSeriesTransform):
       """Subtract the training mean from every feature column."""

       def __init__(self):
           self._means: dict[str, float] = {}

       @property
       def features_added(self) -> list[str]:
           return []  # this transform modifies in-place, adds no new columns

       def fit(self, data: TimeSeriesDataset) -> None:
           self._means = data.data.mean().to_dict()

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           shifted = data.data - data.data.apply(lambda col: self._means.get(col.name, 0))
           return TimeSeriesDataset(shifted, sample_interval=data.sample_interval)

Two concrete abstract subclasses are provided out of the box:

- **TimeSeriesTransform** — for transforms that operate on ``TimeSeriesDataset`` in, ``TimeSeriesDataset`` out.
- **VersionedTimeSeriesTransform** — for transforms that operate on ``VersionedTimeSeriesDataset``.

The ``openstef_models`` package builds its full feature-engineering pipeline on top of these abstractions. See the :doc:`models` page for details on the transforms that ship with that package.

----

Domain Types
------------

The ``openstef_core.types`` module defines typed wrappers for the temporal and probabilistic concepts that appear throughout the library. Using these types instead of raw ``timedelta`` or ``datetime`` objects gives you automatic ISO 8601 serialisation, Pydantic validation, and consistent string representations.

**LeadTime**
   A ``timedelta`` subclass that serialises to and from ISO 8601 duration strings (e.g. ``"PT1H"`` for one hour). It supports ordering and provides a ``to_hours()`` convenience method.

   .. code-block:: python

      from openstef_core.types import LeadTime

      lt = LeadTime.from_string("PT4H")
      print(lt.to_hours())  # 4.0
      print(str(lt))        # PT4H

**AvailableAt**
   Represents a data-availability offset relative to a reference day, expressed in the format ``DnTHHMM[tz]`` (e.g. ``"D0T0800"`` means "day 0 at 08:00"). Calling ``apply(date)`` resolves the offset against a concrete date to produce a ``datetime``.

   .. code-block:: python

      from datetime import date, datetime
      from openstef_core.types import AvailableAt

      availability = AvailableAt.from_string("D0T0800")
      resolved = availability.apply(datetime(2025, 6, 1))
      print(resolved)  # 2025-06-01 08:00:00

These types are used extensively in ``VersionedTimeSeriesDataset`` and in the backtesting configuration objects defined in ``openstef_beam``.

----

Utility Layer
-------------

The ``openstef_core.utils`` sub-package provides low-level helpers that keep the higher-level code clean.

**Pandas utilities** (``openstef_core.utils.pandas``)

- ``unsafe_sorted_range_slice_idxs`` — returns integer start/end indices for a datetime range on a sorted index without copying data. Used internally by ``TimeSeriesDataset`` for efficient temporal slicing.
- ``normalize_to_unit_sum`` — normalises each column of a DataFrame so that the sum of absolute values equals 1.0. Useful for weight normalisation in ensemble models.
- ``combine_timeseries_indexes`` — merges multiple ``DatetimeIndex`` objects into a single sorted index, handling overlaps correctly.
- ``nan_aware_weighted_mean`` — computes a weighted mean that redistributes the weight of NaN cells proportionally to the remaining non-NaN values.

**Pydantic utilities** (``openstef_core.utils.pydantic``)

- ``timedelta_to_isoformat`` / ``timedelta_from_isoformat`` — round-trip conversion between Python ``timedelta`` and ISO 8601 duration strings. These underpin the serialisation of ``LeadTime`` and are used whenever datasets are saved to disk.

.. code-block:: python

   from openstef_core.utils.pydantic import timedelta_to_isoformat, timedelta_from_isoformat
   from datetime import timedelta

   s = timedelta_to_isoformat(timedelta(hours=6, minutes=30))
   print(s)  # PT6H30M

   td = timedelta_from_isoformat("PT6H30M")
   print(td)  # 6:30:00

----

How Core Provides the Foundation
---------------------------------

Every other OpenSTEF package imports from ``openstef_core`` but nothing in ``openstef_core`` imports from them. This strict one-way dependency means:

- You can use ``openstef_core`` data structures and utilities in isolation without pulling in model training or Beam pipeline dependencies.
- New packages can be added to the ecosystem simply by depending on ``openstef_core``—they automatically gain access to the shared dataset contracts, type system, and utilities.
- The protocol-based design means third-party code can satisfy the ``TimeSeriesMixin`` or ``Transform`` interfaces without subclassing anything from OpenSTEF.

In practice this means that if you are writing a custom transform for ``openstef_models``, a custom metric for ``openstef_beam``, or an ensemble strategy for ``openstef_meta``, the only import you need from the core layer is the relevant dataset class or base transform—everything else is your own logic.

.. note::

   The ``openstef_models`` package extends the ``Transform`` base with a rich
   library of feature-engineering transforms. The ``openstef_meta`` package
   uses ``VersionedTimeSeriesDataset`` as the input contract for its ensemble
   models. See the :doc:`models` and :doc:`meta` pages respectively for those
   details.