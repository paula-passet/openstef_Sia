The openstef_core Package
=========================

The ``openstef_core`` package is the shared foundation that all other OpenSTEF packages build on.
It defines the validated dataset hierarchy that data flows through at every stage of the forecasting
pipeline, the domain types that enforce correctness at the boundaries between components, and the
mixin protocols that give every dataset a consistent persistence and transformation interface.
This page covers those building blocks in depth.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

-----------

The Mixin System
----------------

Two lightweight protocols underpin every dataset class in ``openstef_core``.

``TimeSeriesMixin`` enforces the invariants that make a DataFrame a *time series*: a
``pd.DatetimeIndex``, a consistent ``sample_interval``, and sorted timestamps. It also exposes
horizon and availability metadata when present.

``DatasetMixin`` adds persistence and functional-pipeline utilities that are independent of the
time series semantics:

- ``to_parquet(path)`` / ``read_parquet(path)`` — round-trip a dataset to disk while preserving
  all metadata stored in ``DataFrame.attrs``.
- ``pipe(func, *args, **kwargs)`` — apply an arbitrary transformation and return the result,
  enabling method-chaining without subclassing.

Because both mixins are defined as protocols, any class that satisfies their interface is
structurally compatible — there is no forced inheritance from a heavyweight base class.

-----------

TimeSeriesDataset
-----------------

``TimeSeriesDataset`` is the concrete workhorse that combines both mixins.  It wraps a
``pd.DataFrame`` and guarantees:

- The index is a ``pd.DatetimeIndex`` sorted in ascending order.
- Every row is separated by exactly ``sample_interval``.
- Optional *horizon* and *available_at* columns are validated as ``timedelta`` and ``datetime``
  values respectively, enabling versioned access patterns.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    index = pd.date_range("2025-01-01", periods=96, freq="15min")
    df = pd.DataFrame({"load": range(96), "temperature": range(96)}, index=index)

    ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    print(ds.sample_interval)   # 0:15:00
    print(ds.feature_names)     # ['load', 'temperature']
    print(ds.is_versioned())    # False

Key properties at a glance:

- ``ds.index`` — the underlying ``pd.DatetimeIndex``
- ``ds.horizons`` — list of ``LeadTime`` values present in the horizon column, or ``None``
- ``ds.available_at_series`` — the availability column as a ``pd.Series``, or ``None``
- ``ds.calculate_time_coverage()`` — total ``timedelta`` spanned by the dataset

Slicing by lead time is a first-class operation:

.. code-block:: python

    from openstef_core.types import LeadTime

    # Restrict to rows whose horizon is at most 24 hours
    subset = ds.select_lead_time(LeadTime("PT24H"))

-----------

VersionedTimeSeriesDataset
--------------------------

``VersionedTimeSeriesDataset`` composes *multiple* ``TimeSeriesDataset`` parts into a single
unified view that tracks when each data point became available.  This is the key enabler for
realistic backtesting: rather than training on data that would not yet have existed at the
simulated forecast time, you call ``select_version(available_at)`` to obtain only the rows that
were available at that moment.

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset
    from datetime import timedelta
    import pandas as pd

    part_a = TimeSeriesDataset(
        pd.DataFrame({"load": [1, 2, 3]},
                     index=pd.date_range("2025-01-01", periods=3, freq="h")),
        sample_interval=timedelta(hours=1),
    )
    part_b = TimeSeriesDataset(
        pd.DataFrame({"load": [4, 5, 6]},
                     index=pd.date_range("2025-01-04", periods=3, freq="h")),
        sample_interval=timedelta(hours=1),
    )

    versioned = VersionedTimeSeriesDataset([part_a, part_b])

    # Retrieve only data available as of a specific point in time
    from datetime import datetime, timezone
    snapshot = versioned.select_version(datetime(2025, 1, 3, tzinfo=timezone.utc))

``VersionedTimeSeriesDataset`` validates that all parts share the same ``sample_interval`` and
that their columns do not overlap (``validate_disjoint_columns``, ``validate_same_sample_intervals``).
Concatenation mode — ``"left"``, ``"outer"``, or ``"inner"`` — controls how the time index is
merged across parts.

.. note::

   ``VersionedTimeSeriesDataset`` is a *sibling* of ``TimeSeriesDataset``, not a subclass.
   Both inherit directly from ``TimeSeriesMixin`` and ``DatasetMixin``.  This means you cannot
   pass a ``VersionedTimeSeriesDataset`` where a ``TimeSeriesDataset`` is expected; call
   ``select_version()`` first to materialise a concrete ``TimeSeriesDataset``.

-----------

Validated Dataset Subclasses
-----------------------------

The four validated datasets in ``openstef_core.datasets.validated_datasets`` extend
``TimeSeriesDataset`` with domain-specific column checks.  Validation runs at construction time,
so errors surface immediately rather than propagating silently through a pipeline.

ForecastInputDataset
^^^^^^^^^^^^^^^^^^^^

Requires a named *target column* to be present in the DataFrame.  This is the standard container
for training and prediction input data.

.. code-block:: python

    from openstef_core.datasets import ForecastInputDataset

    ds = ForecastInputDataset(df, target_column="load")
    # Raises MissingColumnsError immediately if "load" is absent

ForecastDataset
^^^^^^^^^^^^^^^

The output of a single forecaster.  Carries ``forecast_start``, a ``target_column``, and a list
of ``Quantile`` values corresponding to the quantile columns present in the DataFrame.

EnsembleForecastDataset
^^^^^^^^^^^^^^^^^^^^^^^

Aggregates the outputs of multiple forecasters into one dataset.  Each forecaster's predictions
are stored in columns named ``<forecaster_name>__<original_column>`` (the separator is the module
constant ``ENSEMBLE_COLUMN_SEP = "__"``).  The class exposes ``forecaster_names`` and
``quantiles`` as first-class attributes and provides the factory method
``EnsembleForecastDataset.from_forecast_datasets(predictions, target_series)`` used by the
ensemble training loop in ``openstef_meta``.

.. code-block:: python

    from openstef_core.datasets import EnsembleForecastDataset

    # Typically produced by the ensemble trainer, not constructed by hand:
    ensemble = EnsembleForecastDataset.from_forecast_datasets(
        predictions={"model_a": forecast_a, "model_b": forecast_b},
        target_series=df["load"],
    )
    print(ensemble.forecaster_names)  # ['model_a', 'model_b']
    print(ensemble.quantiles)         # [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

EnergyComponentDataset
^^^^^^^^^^^^^^^^^^^^^^

Validates that all ``EnergyComponentType`` columns (``wind``, ``solar``, ``other``) are present.
Used for component-level energy analysis.

.. code-block:: python

    from openstef_core.datasets import EnergyComponentDataset
    from datetime import timedelta

    component_df = pd.DataFrame(
        {"wind": [50, 60], "solar": [30, 40], "other": [20, 25]},
        index=pd.date_range("2025-01-01", periods=2, freq="h"),
    )
    ds = EnergyComponentDataset(component_df, timedelta(hours=1))
    print(ds.feature_names)  # ['wind', 'solar', 'other']

-----------

Domain Types
------------

``openstef_core.types`` provides typed wrappers that prevent unit confusion and enable consistent
serialisation across the whole library.

LeadTime
^^^^^^^^

A ``timedelta`` subclass that serialises to and from ISO 8601 duration strings (e.g. ``"PT15M"``,
``"PT24H"``).  Pydantic validation is built in, so any model field typed as ``LeadTime`` accepts
both ``timedelta`` objects and ISO strings.

.. code-block:: python

    from openstef_core.types import LeadTime
    from datetime import timedelta

    lt = LeadTime(timedelta(hours=24))
    print(str(lt))          # 'PT24H'
    print(lt == timedelta(hours=24))  # True

    lt2 = LeadTime.from_timedelta(timedelta(minutes=15))
    print(str(lt2))         # 'PT15M'

Quantile
^^^^^^^^

A ``float`` subclass constrained to ``[0, 1]``.  Provides helpers for percentile conversion and
complementary quantile calculation.

.. code-block:: python

    from openstef_core.types import Quantile

    q = Quantile(0.9)
    print(q.to_percentile())   # 90.0
    print(q.complementary())   # Quantile(0.1)
    print(q.format())          # 'q0.90'

AvailableAt
^^^^^^^^^^^

Encodes a *data availability offset* — the delay between a measurement's timestamp and when it
actually becomes available for use.  The ``apply(date)`` and ``apply_index(index)`` methods shift
a reference datetime or a full ``DatetimeIndex`` by the encoded offset, including timezone
handling.

.. code-block:: python

    from openstef_core.types import AvailableAt
    from datetime import datetime, timezone

    offset = AvailableAt.from_string("D0T0800UTC")
    reference = datetime(2025, 6, 1, tzinfo=timezone.utc)
    print(offset.apply(reference))  # 2025-06-01 08:00:00+00:00

EnergyComponentType
^^^^^^^^^^^^^^^^^^^

A ``StrEnum`` whose members define the canonical column names expected by
``EnergyComponentDataset``.  Using the enum rather than raw strings makes column references
refactor-safe.

.. code-block:: python

    from openstef_core.types import EnergyComponentType

    for component in EnergyComponentType:
        print(component.value)
    # wind
    # solar
    # other

-----------

How Other Packages Build on Core
---------------------------------

``openstef_core`` deliberately contains no ML logic.  Its role is to define the *contracts* —
validated data shapes and typed domain values — that the other packages rely on:

- **openstef_models** receives ``ForecastInputDataset`` for training and returns
  ``ForecastDataset`` objects.  See :doc:`models` for how transforms and forecasters consume
  these types.
- **openstef_meta** assembles individual ``ForecastDataset`` results into
  ``EnsembleForecastDataset`` and orchestrates the ensemble training loop.  See :doc:`meta` for
  details.
- **openstef_beam** pipelines accept ``VersionedTimeSeriesDataset`` as their primary input,
  calling ``select_version()`` at each backtesting step to simulate realistic data availability.
  See :doc:`beam` for pipeline architecture.

Because every stage speaks the same dataset language, data can move between packages without
conversion layers.  A ``ForecastDataset`` produced by a model in ``openstef_models`` is
immediately consumable by the ensemble combiner in ``openstef_meta`` without any intermediate
transformation.

.. note::

   All public dataset classes and domain types are re-exported from their respective top-level
   ``__init__.py`` modules, so the canonical import paths are
   ``from openstef_core.datasets import <ClassName>`` and
   ``from openstef_core.types import <TypeName>``.