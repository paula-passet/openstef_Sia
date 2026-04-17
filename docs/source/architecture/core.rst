The Core Package
================

The ``openstef_core`` package is the foundation of the OpenSTEF library. Every other
package — ``openstef_models``, ``openstef_beam``, and ``openstef_meta`` — depends on it.
Rather than containing forecasting logic itself, ``openstef_core`` defines the data
structures, abstract base classes, validation utilities, and type aliases that give the
rest of the library a consistent, well-typed interface to build on.

This page covers the internal structure of ``openstef_core``: its dataset classes, the
mixin and transform abstractions, and the utilities that underpin the whole framework.
For the models that consume these structures see :doc:`models`, and for the backtesting
and metrics layer that evaluates them see :doc:`beam`.

.. note:: [DIAGRAM: Component-level diagram of the openstef_core package showing four
   internal sub-packages — datasets, transforms, mixins, and utils — with arrows
   indicating that datasets depend on mixins and validation, transforms depend on
   datasets and mixins, and that all other OpenSTEF packages (openstef_models,
   openstef_beam, openstef_meta) depend on openstef_core at the boundary.]

----

Dataset Classes
---------------

The ``openstef_core.datasets`` module is the most important part of the package. It
provides two concrete dataset classes and a set of validated domain-specific subtypes
that are used throughout the library.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the primary data container in OpenSTEF. It wraps a
``pandas.DataFrame`` and enforces a *regular sampling interval* — every row in the
underlying data must be separated by the same ``timedelta``. This constraint is
intentional: short-term energy forecasting models rely on evenly-spaced observations,
and encoding that assumption in the type system catches data quality problems early.

Beyond the raw data, ``TimeSeriesDataset`` carries metadata that matters for
forecasting:

- **``sample_interval``** — the fixed time step between observations (e.g. 15 minutes).
- **``feature_names``** — the list of input feature columns, distinct from the target.
- **``horizons``** — when present, the list of forecast lead times represented in the
  dataset.
- **``is_versioned``** — whether the dataset tracks when each row of data became
  available, enabling realistic backtesting.

The class also provides temporal slicing, persistence to Parquet, and a ``pipe()``
method for chaining transformations in a readable way.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Build a simple dataset from a DataFrame with a DatetimeIndex
   df = pd.DataFrame(
       {"load_mw": [100.0, 102.5, 98.3, 105.1]},
       index=pd.date_range("2024-01-01", periods=4, freq="15min"),
   )

   ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   print(ds.sample_interval)   # 0:15:00
   print(ds.feature_names)     # ['load_mw']
   print(ds.index[:2])         # DatetimeIndex(['2024-01-01 00:00:00', ...])

   # Persist and reload without losing metadata
   ds.to_parquet("load_data.parquet")
   ds_reloaded = TimeSeriesDataset.read_parquet("load_data.parquet")

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts into a
single object that tracks *when each observation became available*. This is the key
enabler for realistic backtesting: rather than training on data as it looks today, you
can reconstruct the exact dataset that would have been visible at any historical point
in time.

Internally the class stores a sequence of ``TimeSeriesDataset`` parts with disjoint
column sets and validates that all parts share the same sample interval. The
``select_version()`` method on ``TimeSeriesDataset`` and the slicing utilities on
``VersionedTimeSeriesDataset`` both use the ``available_at`` metadata to filter rows
appropriately.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   interval = timedelta(minutes=15)
   idx = pd.date_range("2024-01-01", periods=96, freq="15min")

   # Two parts with different availability characteristics
   actuals = TimeSeriesDataset(
       pd.DataFrame({"load_mw": range(96)}, index=idx),
       sample_interval=interval,
   )
   forecasts = TimeSeriesDataset(
       pd.DataFrame({"forecast_mw": [x * 1.02 for x in range(96)]}, index=idx),
       sample_interval=interval,
   )

   versioned = VersionedTimeSeriesDataset([actuals, forecasts])
   print(versioned.is_versioned)  # True

Validated Domain Datasets
^^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_core.datasets`` also exports several validated subclasses that encode
domain knowledge as type constraints:

- ``ForecastInputDataset`` — input features ready to be passed to a model.
- ``ForecastDataset`` — model output containing point forecasts.
- ``EnergyComponentDataset`` — decomposed energy components (e.g. solar, wind, load).
- ``EnsembleForecastDataset`` — forecasts from multiple ensemble members.

These types are used as the declared input and output signatures of pipelines and
transforms across the library, making it possible to catch mismatched data at the
boundary between components rather than deep inside model code.

----

Mixins and Abstract Base Classes
---------------------------------

The ``openstef_core.mixins`` module defines the ``Transform`` generic base class that
all data transformations in the library inherit from. The pattern mirrors
scikit-learn's ``fit`` / ``transform`` split, but is typed against OpenSTEF's own
dataset classes rather than NumPy arrays.

``openstef_core.datasets.mixins`` provides two protocol classes:

- **``TimeSeriesMixin``** — declares the temporal interface: ``index``,
  ``sample_interval``, ``horizons``, ``calculate_time_coverage()``, and so on.
- **``DatasetMixin``** — declares the persistence and composition interface:
  ``to_parquet()``, ``read_parquet()``, and ``pipe()``.

Both ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` inherit from both mixins,
which means any code written against the protocol interface works with either class.

Transform Abstractions
^^^^^^^^^^^^^^^^^^^^^^

``openstef_core.transforms.dataset_transforms`` provides two abstract base classes
that sit above the concrete transforms implemented in ``openstef_models``:

- **``TimeSeriesTransform``** — operates on ``TimeSeriesDataset`` in, ``TimeSeriesDataset`` out.
- **``VersionedTimeSeriesTransform``** — operates on ``VersionedTimeSeriesDataset``.

Both follow the same contract: implement ``transform()``, optionally override ``fit()``
for stateful transforms, and expose ``is_fitted`` as a property. Stateless transforms
get a default ``is_fitted = True`` implementation for free.

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class ClipTransform(TimeSeriesTransform):
       """Clip all feature values to a fixed range."""

       def __init__(self, lower: float, upper: float):
           self.lower = lower
           self.upper = upper

       def features_added(self) -> list[str]:
           return []  # no new columns, modifies in place

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           clipped = data.data.clip(lower=self.lower, upper=self.upper)
           return TimeSeriesDataset(clipped, data.sample_interval)


   # Usage
   transform = ClipTransform(lower=0.0, upper=500.0)
   transform.fit(ds)          # no-op for stateless transforms
   clipped_ds = transform.transform(ds)

Because ``TimeSeriesTransform`` is generic over its input and output types, the type
checker can verify that transforms are composed in a compatible order — a property that
the pipeline machinery in ``openstef_beam`` relies on. See :doc:`beam` for how
transforms are assembled into full training and backtesting pipelines.

----

Types and Utilities
--------------------

``openstef_core.types`` defines two type aliases used throughout the library:

- **``LeadTime``** — a ``timedelta`` representing a forecast horizon (e.g. 1 hour ahead).
- **``AvailableAt``** — a ``datetime`` representing when a data point became available.

Using named type aliases rather than bare ``timedelta`` and ``datetime`` makes function
signatures self-documenting and allows type checkers to flag accidental swaps between
the two.

``openstef_core.utils`` provides helpers for working with ISO 8601 duration strings
(``timedelta_from_isoformat``, ``timedelta_to_isoformat``) and
``openstef_core.utils.pandas`` provides low-level DataFrame utilities such as
``unsafe_sorted_range_slice_idxs`` and ``combine_timeseries_indexes`` that are used
internally by the dataset classes for efficient temporal slicing.

Validation
^^^^^^^^^^

``openstef_core.datasets.validation`` contains the validation functions that dataset
constructors call automatically:

- ``validate_datetime_column`` — ensures a column contains valid, non-null datetimes.
- ``validate_timedelta_column`` — ensures a column contains valid timedelta values.
- ``validate_disjoint_columns`` — used by ``VersionedTimeSeriesDataset`` to confirm
  that parts do not share column names.
- ``validate_same_sample_intervals`` — ensures all parts of a versioned dataset share
  the same sampling frequency.

When validation fails, ``openstef_core.exceptions.TimeSeriesValidationError`` is
raised with a descriptive message. Catching this specific exception type lets
application code distinguish data quality problems from programming errors.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.exceptions import TimeSeriesValidationError

   # Irregular index — will raise TimeSeriesValidationError
   bad_idx = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 00:17", "2024-01-01 00:30"])
   df = pd.DataFrame({"load_mw": [1.0, 2.0, 3.0]}, index=bad_idx)

   try:
       ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))
   except TimeSeriesValidationError as exc:
       print(f"Data quality problem: {exc}")

----

How Core Underpins the Rest of the Library
-------------------------------------------

Every other OpenSTEF package takes ``openstef_core`` as a direct dependency and builds
on the abstractions described above:

- **openstef_models** implements concrete ``TimeSeriesTransform`` subclasses for
  feature engineering and wraps trained models in ``ForecastDataset``-returning
  callables. See :doc:`models` for details.
- **openstef_beam** assembles transforms and models into backtesting pipelines that
  accept ``VersionedTimeSeriesDataset`` as input and produce scored
  ``ForecastDataset`` outputs. See :doc:`beam` for details.
- **openstef_meta** builds ensemble models on top of the same dataset types, combining
  multiple ``ForecastDataset`` outputs into ``EnsembleForecastDataset`` results. See
  :doc:`meta` for details.

The practical consequence is that any custom transform or model you write against the
``openstef_core`` abstractions will compose cleanly with the rest of the library
without modification.

.. note::

   Install ``openstef-core`` on its own if you only need the data structures and
   validation utilities:

   .. code-block:: bash

      pip install openstef-core

   All other packages install it automatically as a dependency.