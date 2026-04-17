The Core Package
================

The ``openstef_core`` package is the foundation of the OpenSTEF library. Every other
package — ``openstef_models``, ``openstef_beam``, and ``openstef_meta`` — depends on it.
Rather than containing forecasting logic itself, ``openstef_core`` defines the shared
data structures, abstract base classes, type aliases, and utilities that give the rest
of the library a consistent vocabulary. This page explains what those building blocks
are, how they relate to each other, and how to use them directly in your own code.

.. note:: [DIAGRAM: Component-level diagram of the openstef_core package showing four internal sub-modules — datasets, transforms, mixins, and utils — with arrows indicating that datasets depend on mixins and utils, transforms depend on datasets and mixins, and external packages (openstef_models, openstef_beam, openstef_meta) all depend on openstef_core at the boundary.]


The Dataset Hierarchy
---------------------

The most important concept in ``openstef_core`` is the *dataset*. All data flowing
through an OpenSTEF pipeline is wrapped in one of three concrete dataset classes,
each building on the same pair of mixins.

``TimeSeriesDataset`` is the fundamental unit. It wraps a ``pandas.DataFrame`` whose
index is a ``DatetimeIndex`` and enforces a single, consistent ``sample_interval``
across all rows. On construction the data is sorted automatically, so callers never
need to worry about row ordering. The class exposes a small but complete interface:
temporal metadata (``index``, ``sample_interval``, ``calculate_time_coverage``),
feature introspection (``feature_names``), horizon-aware slicing
(``select_horizon``, ``horizons``), versioning queries (``is_versioned``,
``select_version``, ``available_at_series``), and persistence (``to_parquet`` /
``read_parquet``).

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts into a
single object that tracks *when* each observation became available. This is the
structure used for realistic backtesting: rather than pretending all historical data
was always present, a versioned dataset records the ``available_at`` timestamp for
every row, letting pipelines simulate the information that would have been on hand at
any given moment in the past.

The validated dataset subclasses — ``ForecastInputDataset``, ``ForecastDataset``,
``EnergyComponentDataset``, and ``EnsembleForecastDataset`` — add domain-specific
column constraints on top of ``TimeSeriesDataset``. They are the types that
``openstef_models`` and ``openstef_meta`` produce and consume, so you will encounter
them at pipeline boundaries even if you never construct them directly.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   # Build a simple dataset from a DataFrame
   df = pd.DataFrame(
       {"load_mw": [100.0, 102.5, 98.0, 101.0]},
       index=pd.date_range("2024-01-01", periods=4, freq="15min"),
   )
   ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   print(ds.sample_interval)      # 0:15:00
   print(ds.feature_names)        # ['load_mw']
   print(ds.calculate_time_coverage())  # 0:45:00

   # Persist and reload
   ds.to_parquet("load.parquet")
   ds_reloaded = TimeSeriesDataset.read_parquet("load.parquet")

The ``pipe`` method (inherited from ``DatasetMixin``) lets you chain arbitrary
functions in a readable, method-chaining style without leaving the dataset abstraction:

.. code-block:: python

   def add_rolling_mean(dataset: TimeSeriesDataset) -> TimeSeriesDataset:
       df = dataset.data.copy()
       df["load_rolling"] = df["load_mw"].rolling(4).mean()
       return TimeSeriesDataset(df, dataset.sample_interval)

   enriched = ds.pipe(add_rolling_mean)


Mixins and the Protocol Layer
------------------------------

The dataset classes are assembled from two protocol mixins defined in
``openstef_core.datasets.mixins``:

- **``TimeSeriesMixin``** — contributes the temporal interface: ``index``,
  ``sample_interval``, ``horizons``, ``available_at_series``, ``is_versioned``,
  ``select_horizon``, ``select_version``, and ``calculate_time_coverage``.
- **``DatasetMixin``** — contributes the persistence and composition interface:
  ``to_parquet``, ``read_parquet``, and ``pipe``.

Because these are protocols rather than concrete base classes, any object that
implements the required methods satisfies the type constraints — you are not forced
to inherit from a particular class hierarchy. This design makes it straightforward to
introduce custom dataset types that still interoperate with the rest of the library.


The Transform Abstraction
--------------------------

``openstef_core`` also defines the abstract base classes for data transformations.
These live in ``openstef_core.transforms`` and follow the scikit-learn convention of
separate ``fit`` and ``transform`` phases, making stateful transformations (those that
learn parameters from training data) first-class citizens.

Two specialised abstract classes are provided:

- **``TimeSeriesTransform``** — operates on ``TimeSeriesDataset`` in, ``TimeSeriesDataset`` out.
- **``VersionedTimeSeriesTransform``** — operates on ``VersionedTimeSeriesDataset``.

Both inherit from the generic ``Transform`` mixin in ``openstef_core.mixins``. The
``openstef_models`` package builds its entire feature-engineering pipeline on top of
these abstractions; see the :doc:`models` page for details.

The following example shows how to implement a custom stateful transform:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform

   class NormalisationTransform(TimeSeriesTransform):
       """Normalise all features to the [0, 1] range using training-set statistics."""

       def __init__(self):
           self._min = None
           self._max = None

       @property
       def is_fitted(self) -> bool:
           return self._min is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           self._min = data.data.min()
           self._max = data.data.max()

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           normalised = (data.data - self._min) / (self._max - self._min)
           return TimeSeriesDataset(normalised, data.sample_interval)

       def features_added(self) -> list[str]:
           return []   # no new columns, existing ones are modified in-place

   transform = NormalisationTransform()
   transform.fit(ds)
   ds_normalised = transform.transform(ds)

.. note::

   ``TimeSeriesTransform`` is stateless by default — its ``is_fitted`` property
   returns ``True`` without any ``fit`` call. Override both ``is_fitted`` and ``fit``
   only when your transform genuinely needs to learn from data.


Types and Validation Utilities
--------------------------------

``openstef_core.types`` provides a small set of type aliases used consistently across
all packages:

- ``LeadTime`` — a ``timedelta`` representing a forecast horizon.
- ``AvailableAt`` — a ``datetime`` representing when a data point became available.

Using these aliases rather than raw ``timedelta`` or ``datetime`` makes function
signatures self-documenting and allows type checkers to catch horizon/availability
mix-ups at analysis time.

The ``openstef_core.datasets.validation`` module exposes the validation helpers that
the dataset classes use internally:

- ``validate_datetime_column`` — asserts that a column contains valid, non-null
  datetimes.
- ``validate_timedelta_column`` — asserts that a column contains valid timedeltas.
- ``validate_disjoint_columns`` — used by ``VersionedTimeSeriesDataset`` to ensure
  that the parts being composed do not share column names.

``TimeSeriesValidationError`` is the exception raised when any of these checks fail.
Catching it lets you distinguish data-quality problems from programming errors:

.. code-block:: python

   from openstef_core.datasets.validation import TimeSeriesValidationError
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   import pandas as pd

   bad_df = pd.DataFrame(
       {"load_mw": [None, None]},
       index=pd.date_range("2024-01-01", periods=2, freq="15min"),
   )

   try:
       ds = TimeSeriesDataset(bad_df, sample_interval=timedelta(minutes=15))
   except TimeSeriesValidationError as exc:
       print(f"Data quality problem: {exc}")


Utility Modules
----------------

``openstef_core.utils`` contains helpers that are used pervasively throughout the
library but are also useful in application code:

- ``timedelta_from_isoformat`` / ``timedelta_to_isoformat`` — round-trip conversion
  between ``timedelta`` objects and ISO 8601 duration strings (e.g. ``"PT15M"``).
  These are used when serialising dataset metadata to Parquet.
- ``openstef_core.utils.pandas.unsafe_sorted_range_slice_idxs`` — a low-level helper
  for efficient positional slicing of sorted DatetimeIndexes, used internally by
  ``select_horizon`` and ``select_version``.
- ``openstef_core.utils.pandas.combine_timeseries_indexes`` — merges multiple
  DatetimeIndexes with configurable ``left``, ``inner``, or ``outer`` join semantics,
  used by ``VersionedTimeSeriesDataset`` when composing parts.

.. code-block:: python

   from openstef_core.utils import timedelta_from_isoformat, timedelta_to_isoformat
   from datetime import timedelta

   interval = timedelta(minutes=15)
   iso = timedelta_to_isoformat(interval)   # "PT15M"
   back = timedelta_from_isoformat(iso)     # timedelta(seconds=900)
   assert interval == back


How Other Packages Depend on Core
-----------------------------------

``openstef_core`` is a *pure foundation*: it has no dependency on
``openstef_models``, ``openstef_beam``, or ``openstef_meta``. The dependency graph
flows in one direction only.

- **openstef_models** imports ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``,
  the validated dataset subclasses, and the ``TimeSeriesTransform`` /
  ``VersionedTimeSeriesTransform`` base classes to build its feature-engineering
  transforms and model wrappers. See :doc:`models` for details.
- **openstef_beam** imports the dataset types as the inputs and outputs of its
  backtesting and metrics pipelines. See :doc:`beam` for details.
- **openstef_meta** imports the ensemble-specific validated datasets
  (``EnsembleForecastDataset``) and the transform abstractions to implement its
  meta-model layer. See :doc:`meta` for details.

This one-directional dependency means you can use ``openstef_core`` in isolation —
for example, to build a custom data-loading layer or a bespoke transform — without
pulling in the heavier model or backtesting dependencies.

.. code-block:: python

   # openstef_core alone is sufficient for data wrangling tasks
   from openstef_core.datasets import (
       TimeSeriesDataset,
       VersionedTimeSeriesDataset,
       ForecastInputDataset,
   )
   from openstef_core.types import LeadTime, AvailableAt

   # All dataset types, type aliases, and utilities are available
   # without importing any model or pipeline package.


Summary
--------

``openstef_core`` provides four interlocking layers:

- **Datasets** — ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and the
  validated subclasses form the shared data contract between all packages.
- **Mixins** — ``TimeSeriesMixin`` and ``DatasetMixin`` define the protocols that
  any compatible dataset must satisfy.
- **Transforms** — ``TimeSeriesTransform`` and ``VersionedTimeSeriesTransform``
  provide the abstract interface for all feature-engineering steps.
- **Utilities** — type aliases, validation helpers, and pandas utilities that keep
  the rest of the library consistent and reduce boilerplate.

Understanding these four layers is the key to reading any other part of the OpenSTEF
codebase, and to extending the library with your own datasets, transforms, or
pipelines.