The openstef_core Package
=========================

The ``openstef_core`` package is the foundation on which the rest of the
OpenSTEF ecosystem is built. It defines the validated dataset hierarchy
that flows through every pipeline stage, the domain types that give
numeric values semantic meaning, and the mixin protocol that all dataset
classes share. Understanding ``openstef_core`` is the key to understanding
how data moves through OpenSTEF — from raw time series all the way to
ensemble forecasts.

This page covers the dataset class hierarchy, the mixin system, and the
domain types. For the model layer that consumes these datasets see
:doc:`models`, and for the pipeline layer that orchestrates them see
:doc:`beam`.


The Dataset Hierarchy
---------------------

All datasets in OpenSTEF descend from two lightweight protocol mixins —
``TimeSeriesMixin`` and ``DatasetMixin`` — which together define the
interface every dataset must satisfy. ``TimeSeriesDataset`` and
``VersionedTimeSeriesDataset`` are the two concrete base classes that
implement those mixins. The domain-specific validated datasets
(``ForecastInputDataset``, ``ForecastDataset``, ``EnsembleForecastDataset``,
and ``EnergyComponentDataset``) all extend ``TimeSeriesDataset``.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

The split between ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``
reflects a real distinction in how data arrives in practice. A
``TimeSeriesDataset`` holds a single, consistent snapshot of a time series
with a fixed sample interval. A ``VersionedTimeSeriesDataset`` composes
multiple such snapshots and tracks *when* each observation became
available — a distinction that matters enormously for realistic
backtesting, where you must never use data that would not yet have existed
at the time a forecast was made.


The Mixin System
----------------

``TimeSeriesMixin`` and ``DatasetMixin`` are defined as ``Protocol`` classes,
meaning any class that implements their methods satisfies the contract
without explicit inheritance. In practice, all OpenSTEF dataset classes
do inherit from both, which gives them a consistent, composable interface.

``TimeSeriesMixin`` exposes the time-series-specific surface:

- ``index`` — a ``pd.DatetimeIndex`` over the dataset's timestamps
- ``sample_interval`` — the ``timedelta`` between consecutive samples
- ``feature_names`` — the list of non-index column names
- ``is_versioned`` — whether the dataset carries availability metadata
- ``horizons`` — the forecast lead times present, if any
- ``select_horizon(horizon)`` — slice the dataset to a single lead time
- ``select_version(available_at)`` — materialise the view of the data as
  it would have appeared at a given point in time
- ``calculate_time_coverage()`` — total ``timedelta`` spanned by the data

``DatasetMixin`` adds persistence and functional-style composition:

- ``to_parquet(path)`` / ``read_parquet(path)`` — round-trip to Parquet
- ``pipe(func, *args, **kwargs)`` — apply an arbitrary transformation
  while keeping the fluent call chain readable

The ``pipe`` method is particularly useful when building preprocessing
chains without losing type information:

.. code-block:: python

    from openstef_core.datasets import ForecastInputDataset

    dataset = (
        ForecastInputDataset.read_parquet("input.parquet")
        .pipe(drop_outliers, threshold=3.0)
        .pipe(fill_gaps)
    )


TimeSeriesDataset
-----------------

``TimeSeriesDataset`` is the workhorse of the library. It wraps a
``pd.DataFrame`` whose index is a ``DatetimeIndex``, enforces a consistent
``sample_interval``, and optionally carries either a ``horizon`` column (for
multi-horizon datasets) or an ``available_at`` column (for versioned data).

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    index = pd.date_range("2024-01-01", periods=96, freq="15min")
    df = pd.DataFrame({"load": range(96), "temperature": range(96)}, index=index)

    ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    print(ds.sample_interval)   # 0:15:00
    print(ds.feature_names)     # ['load', 'temperature']
    print(ds.calculate_time_coverage())  # 23:45:00

Slicing by lead time is straightforward when the dataset contains a
horizon column:

.. code-block:: python

    from openstef_core.types import LeadTime
    from datetime import timedelta

    horizon_24h = LeadTime(timedelta(hours=24))
    single_horizon = ds.select_horizon(horizon_24h)


VersionedTimeSeriesDataset
--------------------------

``VersionedTimeSeriesDataset`` composes several ``TimeSeriesDataset`` parts
into a single object that remembers when each row of data became available.
Calling ``select_version(available_at)`` returns a plain
``TimeSeriesDataset`` containing only the observations that existed at the
requested point in time — exactly the semantics needed for honest
backtesting.

.. code-block:: python

    from datetime import datetime
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
    from openstef_core.types import AvailableAt

    # Two data deliveries, each covering overlapping periods
    part_early = TimeSeriesDataset.read_parquet("delivery_2024_01.parquet")
    part_late  = TimeSeriesDataset.read_parquet("delivery_2024_02.parquet")

    versioned = VersionedTimeSeriesDataset([part_early, part_late])

    # Reconstruct the dataset as it looked on 1 Feb 2024
    snapshot = versioned.select_version(
        AvailableAt(datetime(2024, 2, 1, 6, 0))
    )

The ``VersionedTimeSeriesDataset`` validates that the component parts share
the same sample interval and that their columns do not overlap, raising a
``TimeSeriesValidationError`` early rather than silently producing
incorrect results downstream.


Validated Datasets
------------------

The four validated dataset classes extend ``TimeSeriesDataset`` with
column-level contracts that correspond to specific stages of the
forecasting pipeline. Attempting to construct one with missing required
columns raises a ``MissingColumnsError`` immediately.

**ForecastInputDataset** represents training or prediction input. It
requires a target column (default ``"load"``) and exposes helpers that
keep pipeline code clean:

.. code-block:: python

    from openstef_core.datasets import ForecastInputDataset

    input_ds = ForecastInputDataset.from_timeseries(
        dataset=raw_ds,
        target_column="load",
    )

    X = input_ds.input_data()          # features only, target excluded
    y = input_ds.target_series()       # the target as a pd.Series
    w = input_ds.sample_weight_series()  # optional sample weights

**ForecastDataset** holds probabilistic forecasts. It requires quantile
columns (formatted by ``Quantile``) and optionally a target column for
evaluation. The ``median_series()`` property extracts the ``q50`` column
directly.

**EnsembleForecastDataset** stores the output of an ensemble of models.
Columns are namespaced with a double-underscore separator
(``ENSEMBLE_COLUMN_SEP = "__"``), so a column named
``"model_a__q0.5"`` belongs to the ``"model_a"`` member.

**EnergyComponentDataset** validates that columns correspond to known
``EnergyComponentType`` values, making it safe to pass to downstream
aggregation logic without defensive checks.


Domain Types
------------

``openstef_core.types`` provides thin wrappers around Python primitives
that carry domain semantics and prevent category errors at the type-checker
level.

``LeadTime``
   A ``timedelta`` subclass representing a forecast horizon. Using
   ``LeadTime`` instead of a bare ``timedelta`` makes function signatures
   self-documenting and allows type checkers to catch accidental misuse.

   .. code-block:: python

       from openstef_core.types import LeadTime
       from datetime import timedelta

       h24 = LeadTime(timedelta(hours=24))
       h48 = LeadTime(timedelta(hours=48))

``Quantile``
   A ``float`` subclass constrained to ``[0, 1]``. It provides formatting
   and parsing helpers so that quantile column names are always consistent
   across the codebase:

   .. code-block:: python

       from openstef_core.types import Quantile

       q = Quantile(0.5)
       print(q.format())                    # "q0.5"
       print(Quantile.parse("q0.1"))        # Quantile(0.1)
       print(q.complementary())             # Quantile(0.5)
       print(Quantile.from_percentile(90))  # Quantile(0.9)

``AvailableAt``
   Represents the timestamp at which a data observation became available.
   It supports an offset notation (``DnTHHMM[tz]``) for expressing
   availability relative to a reference date, and provides ``apply()`` and
   ``apply_index()`` for vectorised application over a ``DatetimeIndex``.

   .. code-block:: python

       from openstef_core.types import AvailableAt
       from datetime import datetime

       # Data available 1 day and 6 hours after the reference date
       offset = AvailableAt.from_string("D1T0600")
       ref = datetime(2024, 3, 1)
       print(offset.apply(ref))  # 2024-03-02 06:00:00

``EnergyComponentType``
   A ``StrEnum`` enumerating the recognised energy component categories
   (e.g. solar, wind, load). ``EnergyComponentDataset`` uses this enum to
   validate its column names, and downstream aggregation code can branch
   on it safely.

   .. code-block:: python

       from openstef_core.types import EnergyComponentType

       for component in EnergyComponentType:
           print(component)


How core Underpins the Rest of OpenSTEF
---------------------------------------

Every other OpenSTEF package depends on ``openstef_core`` for its data
contracts:

- **openstef_models** (see :doc:`models`) receives ``ForecastInputDataset``
  as training input and returns ``ForecastDataset`` or
  ``EnsembleForecastDataset`` as output. The validated column contracts
  mean models never need to defensively check for required columns.

- **openstef_beam** (see :doc:`beam`) pipelines pass ``VersionedTimeSeriesDataset``
  through backtesting stages, calling ``select_version()`` at each
  evaluation point to reconstruct the historically accurate view of the
  data.

- **openstef_meta** (see :doc:`meta`) uses ``EnsembleForecastDataset`` as
  the input to meta-learning, relying on the ``ENSEMBLE_COLUMN_SEP``
  convention to identify individual model contributions.

The result is that data validation happens once — at construction time in
``openstef_core`` — and every downstream component can trust the shape and
semantics of what it receives.

.. note::

   ``TimeSeriesValidationError`` and ``MissingColumnsError`` are both
   importable from ``openstef_core.exceptions``. Catching them at pipeline
   boundaries gives a clean separation between data quality failures and
   algorithmic failures.