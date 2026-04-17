openstef\_core: Datasets, Types, and Base Classes
==================================================

The ``openstef_core`` package is the foundation of the OpenSTEF library. It defines
the validated dataset hierarchy that flows through every pipeline stage, the domain
types that enforce correctness at the boundary of your data, and the mixin system
that keeps the class hierarchy composable. Every other OpenSTEF package — ``openstef_models``,
``openstef_beam``, and ``openstef_meta`` — builds on these primitives.

This page covers the internals of ``openstef_core``. For how these datasets are used
inside pipelines, see :doc:`beam`. For the models that consume and produce them, see
:doc:`models`.

Dataset Hierarchy
-----------------

All datasets in OpenSTEF share two mixins: ``TimeSeriesMixin``, which enforces a
consistent sampling interval and sorted timestamps, and ``DatasetMixin``, which
provides serialisation helpers (``read_parquet`` / ``write_parquet``) and metadata
persistence. Neither mixin is a dataset on its own — they exist solely to be composed.

``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` are the two concrete base
classes. They both inherit from the same pair of mixins but serve different purposes:
``TimeSeriesDataset`` holds a materialised, in-memory DataFrame, while
``VersionedTimeSeriesDataset`` is a lazy, multi-part structure that tracks *when*
each value became available — essential for realistic backtesting.

The specialised, validated datasets (``ForecastInputDataset``, ``ForecastDataset``,
``EnergyComponentDataset``, ``EnsembleForecastDataset``) all extend
``TimeSeriesDataset`` and add domain-specific column validation on top.

.. note:: [DIAGRAM: Dataset class hierarchy — TimeSeriesMixin and DatasetMixin as shared bases; TimeSeriesDataset and VersionedTimeSeriesDataset as siblings both inheriting from those mixins; ForecastInputDataset, ForecastDataset, EnergyComponentDataset, and EnsembleForecastDataset as subclasses of TimeSeriesDataset]

The Mixin System
^^^^^^^^^^^^^^^^

``TimeSeriesMixin`` is the structural contract: every dataset has a
``sample_interval`` (a ``timedelta``), a ``DatetimeIndex`` that is always sorted,
and optional ``horizon_column`` / ``available_at_column`` metadata. Validation runs
at construction time, so an invalid dataset cannot exist.

``DatasetMixin`` adds persistence and introspection. The ``read_parquet`` /
``write_parquet`` class methods round-trip all metadata — including ``sample_interval``
and custom attributes — through Parquet file metadata, so you never lose context when
saving to disk.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the workhorse. It wraps a ``pd.DataFrame`` with a
``DatetimeIndex`` and exposes slicing, horizon filtering, and feature access:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.DataFrame(
       {"load": [1.0, 2.0, 3.0], "temperature": [10.0, 11.0, 12.0]},
       index=pd.date_range("2024-01-01", periods=3, freq="15min"),
   )

   ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   print(ds.feature_names)   # ['load', 'temperature']
   print(ds.sample_interval) # 0:15:00

The constructor rejects data with irregular intervals or an unsorted index, catching
data quality issues before they propagate into model training.

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts, each
stamped with an ``available_at`` timestamp. Calling ``select_version()`` materialises
a concrete ``TimeSeriesDataset`` that reflects only the data that would have been
visible at a given point in time — the key primitive for point-in-time-correct
backtesting.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   load = VersionedTimeSeriesDataset.read_parquet("load_measurements/site_a.parquet")
   weather = VersionedTimeSeriesDataset.read_parquet("weather_forecasts/site_a.parquet")
   epex = VersionedTimeSeriesDataset.read_parquet("EPEX.parquet")

   # Combine with a left join: keep all load timestamps, attach features where available
   combined = VersionedTimeSeriesDataset.concat(
       [load, weather, epex],
       mode="left",
   )

   # Materialise the view as it would have looked at a specific moment
   snapshot: TimeSeriesDataset = combined.select_version()

The ``concat`` method accepts three modes: ``"left"`` (keep all timestamps from the
first part), ``"inner"`` (intersection), and ``"outer"`` (union). Columns across
parts must be disjoint — the dataset validates this at construction time.

Validated Datasets
------------------

The four validated dataset classes each represent a distinct stage in the forecasting
pipeline. Their constructors raise ``MissingColumnsError`` immediately if required
columns are absent, so pipeline stages fail fast with a clear error rather than
silently producing wrong results.

ForecastInputDataset
^^^^^^^^^^^^^^^^^^^^

Wraps training or prediction input. Requires a designated ``target_column`` and
optionally a ``sample_weight_column``. A ``forecast_start`` timestamp marks the
boundary between historical context and the forecast horizon.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   ds = ForecastInputDataset(
       df,
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )
   print(ds.target_column)    # 'load'
   print(ds.forecast_start)   # first timestamp in the index

ForecastDataset
^^^^^^^^^^^^^^^

The output of a single forecaster. Carries quantile columns alongside the point
forecast, and records which quantiles are present via the ``quantiles`` attribute.
Models in ``openstef_models`` return ``ForecastDataset`` instances directly from
their ``predict`` methods.

EnsembleForecastDataset
^^^^^^^^^^^^^^^^^^^^^^^

The first-stage output when multiple forecasters are combined. Columns are named
``<forecaster_name>__<quantile>`` (separated by ``ENSEMBLE_COLUMN_SEP = "__"``),
allowing the combiner in ``openstef_meta`` to identify each member's contribution.
Use ``EnsembleForecastDataset.from_forecast_datasets`` to assemble one from a
dictionary of ``ForecastDataset`` objects:

.. code-block:: python

   from openstef_core.datasets.validated_datasets import EnsembleForecastDataset

   ensemble = EnsembleForecastDataset.from_forecast_datasets(
       predictions,                          # dict[str, ForecastDataset]
       target_series=data.data["load"],
   )
   print(ensemble.forecaster_names)  # ['xgb', 'lgbm', 'linear']
   print(ensemble.quantiles)         # [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

EnergyComponentDataset
^^^^^^^^^^^^^^^^^^^^^^

Validates that all ``EnergyComponentType`` columns (``wind``, ``solar``, ``other``)
are present. Returned by component-splitting models in ``openstef_models``:

.. code-block:: python

   from openstef_core.datasets.validated_datasets import EnergyComponentDataset
   from datetime import timedelta

   component_df = pd.DataFrame(
       {"wind": [50.0, 60.0], "solar": [30.0, 40.0], "other": [20.0, 25.0]},
       index=pd.date_range("2025-01-01", periods=2, freq="h"),
   )
   ds = EnergyComponentDataset(component_df, timedelta(hours=1))
   print(ds.feature_names)  # ['wind', 'solar', 'other']

Domain Types
------------

``openstef_core.types`` provides typed wrappers for the primitive values that appear
throughout the forecasting pipeline. Using these types instead of raw ``float`` or
``str`` values means validation and serialisation are handled once, centrally.

LeadTime
^^^^^^^^

A ``timedelta`` subclass that serialises to and from ISO 8601 duration strings
(e.g. ``"PT15M"``, ``"P1D"``). It supports ordering, so lead times can be sorted
and compared directly:

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta

   lt = LeadTime(timedelta(hours=24))
   print(str(lt))   # 'PT24H' (ISO 8601)

   lt2 = LeadTime.from_timedelta(timedelta(hours=48))
   print(lt < lt2)  # True

Quantile
^^^^^^^^

A ``float`` subclass constrained to ``[0, 1]``. It provides ``format()`` /
``parse()`` for consistent string representation, ``complementary()`` to get
``1 - q``, and ``from_percentile`` / ``to_percentile`` for interoperability:

.. code-block:: python

   from openstef_core.types import Quantile

   q = Quantile(0.9)
   print(q.format())          # 'q0.90'
   print(q.complementary())   # Quantile(0.1)
   print(q.to_percentile())   # 90.0

AvailableAt
^^^^^^^^^^^

Encodes a data-availability offset in ``DnTHHMM[tz]`` format. It can be applied to
a reference datetime (or a whole ``DatetimeIndex``) to compute the timestamp at
which a data point would have become available — the building block for
point-in-time-correct feature construction:

.. code-block:: python

   from openstef_core.types import AvailableAt
   from datetime import datetime, timezone

   offset = AvailableAt.from_string("D0T0600UTC")
   reference = datetime(2024, 6, 1, tzinfo=timezone.utc)
   print(offset.apply(reference))  # 2024-06-01 06:00:00+00:00

EnergyComponentType
^^^^^^^^^^^^^^^^^^^

A ``StrEnum`` whose members (``wind``, ``solar``, ``other``) define the required
columns for ``EnergyComponentDataset``. Using the enum rather than bare strings
means column names are validated at import time and refactoring is safe:

.. code-block:: python

   from openstef_core.types import EnergyComponentType

   for component in EnergyComponentType:
       print(component.value)  # 'wind', 'solar', 'other'

How Core Underpins the Rest of OpenSTEF
---------------------------------------

Every other package depends on ``openstef_core`` but never the reverse. The
dependency graph is strictly layered:

- **openstef_models** receives ``ForecastInputDataset`` and returns
  ``ForecastDataset`` or ``EnergyComponentDataset``. Model interfaces are typed
  against these classes, so the compiler catches mismatches before runtime.
  See :doc:`models` for details.

- **openstef_meta** assembles ``EnsembleForecastDataset`` instances produced by
  multiple models and combines them into a final ``ForecastDataset``. The
  ``ENSEMBLE_COLUMN_SEP`` convention defined in ``openstef_core`` is the shared
  contract between the two packages. See :doc:`meta` for details.

- **openstef_beam** orchestrates end-to-end pipelines. It reads raw data into
  ``VersionedTimeSeriesDataset``, calls ``select_version()`` to produce
  point-in-time snapshots, passes them through models, and writes the resulting
  ``ForecastDataset`` objects to storage. See :doc:`beam` for details.

.. note::

   Because all validation happens inside the dataset constructors, pipeline stages
   never need to validate their inputs manually. A function that accepts a
   ``ForecastInputDataset`` can trust that the target column exists and the index
   is sorted — those invariants are structural, not conventional.