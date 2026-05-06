The openstef_core Package
=========================

The ``openstef_core`` package is the foundation of the OpenSTEF library. It defines the
validated data structures, domain types, and base abstractions that every other package
builds on. This page covers the dataset hierarchy, the mixin system, and the domain types
that give the rest of the library its vocabulary.

.. note::

   This page focuses on ``openstef_core`` internals. For how these datasets flow through
   training and inference pipelines, see the :doc:`beam` page. For the model layer that
   consumes them, see :doc:`models`.

Dataset Hierarchy
-----------------

All datasets in OpenSTEF share two lightweight protocol mixins — ``TimeSeriesMixin`` and
``DatasetMixin`` — and then specialise through inheritance. The full hierarchy looks like
this:

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

The two mixins are pure protocols: they carry no state of their own, only the interface
contract. ``TimeSeriesMixin`` guarantees that any conforming class exposes a
``DatetimeIndex``, a ``sample_interval``, and horizon/availability metadata.
``DatasetMixin`` adds persistence (``to_parquet`` / ``read_parquet``) and a ``pipe``
method for chaining transformations.

The Mixin System
^^^^^^^^^^^^^^^^

Because both mixins are protocols rather than concrete base classes, they can be composed
freely without the fragility of deep inheritance chains. ``TimeSeriesDataset`` and
``VersionedTimeSeriesDataset`` are siblings — they share the same interface contract but
have different internal representations.

``DatasetMixin`` exposes three methods that every dataset inherits:

- ``to_parquet(path)`` — serialise to Parquet, preserving ``attrs`` metadata.
- ``read_parquet(path)`` — class-method round-trip that reconstructs the typed dataset.
- ``pipe(func, *args, **kwargs)`` — apply an arbitrary transformation and return the
  result, enabling fluent method chaining without subclassing.

TimeSeriesDataset
-----------------

``TimeSeriesDataset`` is the workhorse of the library. It wraps a ``pd.DataFrame`` with a
``DatetimeIndex``, enforces a consistent ``sample_interval``, and optionally tracks
forecast horizons or data-availability timestamps.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.DataFrame(
       {"load": [100.0, 102.5, 98.0]},
       index=pd.date_range("2024-01-01", periods=3, freq="15min"),
   )

   ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   print(ds.sample_interval)   # 0:15:00
   print(ds.feature_names)     # ['load']
   print(ds.is_versioned())    # False

Key properties at a glance:

- ``index`` — the underlying ``DatetimeIndex``.
- ``sample_interval`` — enforced regularity; construction raises
  ``TimeSeriesValidationError`` if the data violates it.
- ``horizons`` — ``list[LeadTime] | None``; present when the dataset carries a
  ``horizon`` column.
- ``available_at_series`` — ``pd.Series | None``; present when the dataset carries an
  ``available_at`` column, enabling point-in-time queries.
- ``feature_names`` — column names excluding the reserved ``horizon`` and
  ``available_at`` columns.

VersionedTimeSeriesDataset
--------------------------

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts into a
single object that tracks *when* each row of data became available. This is the key
enabler for realistic backtesting: instead of training on data that would not yet have
existed at the time of the forecast, you can call ``select_version`` to obtain the slice
of data that was actually available at a given moment.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset, TimeSeriesDataset
   from datetime import timedelta
   import pandas as pd

   part_a = TimeSeriesDataset(
       pd.DataFrame(
           {"load": [100.0, 101.0]},
           index=pd.date_range("2024-01-01 00:00", periods=2, freq="15min"),
       ),
       sample_interval=timedelta(minutes=15),
   )
   part_b = TimeSeriesDataset(
       pd.DataFrame(
           {"load": [102.0, 103.0]},
           index=pd.date_range("2024-01-01 00:30", periods=2, freq="15min"),
       ),
       sample_interval=timedelta(minutes=15),
   )

   versioned = VersionedTimeSeriesDataset.from_parts([part_a, part_b])
   snapshot = versioned.select_version(available_at=pd.Timestamp("2024-01-01 00:20"))

``VersionedTimeSeriesDataset`` validates that the constituent parts share the same
``sample_interval`` and have disjoint columns, raising ``TimeSeriesValidationError``
otherwise.

Validated Domain Datasets
--------------------------

Four specialised subclasses of ``TimeSeriesDataset`` add domain-specific column
validation. They are the typed currency passed between pipeline stages.

.. code-block:: python

   from openstef_core.datasets import (
       ForecastInputDataset,
       ForecastDataset,
       EnergyComponentDataset,
       EnsembleForecastDataset,
   )

**ForecastInputDataset** requires a ``target_column`` (default ``"load"``) and is the
standard input to both training and inference. It exposes ``target_series``,
``input_data``, and ``create_forecast_range`` to make feature/target splitting
straightforward:

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset, TimeSeriesDataset
   from datetime import timedelta
   import pandas as pd

   raw = TimeSeriesDataset(
       pd.DataFrame(
           {"load": [100.0, 102.0], "temperature": [15.0, 14.5]},
           index=pd.date_range("2024-06-01", periods=2, freq="15min"),
       ),
       sample_interval=timedelta(minutes=15),
   )

   fid = ForecastInputDataset.from_timeseries(raw, target_column="load")
   X = fid.input_data()        # DataFrame without 'load'
   y = fid.target_series()     # Series of load values

**ForecastDataset** holds probabilistic forecasts. It validates that quantile columns are
present and exposes ``median_series`` and ``target_series`` (the latter optional, for
evaluation).

**EnergyComponentDataset** validates that all members of ``EnergyComponentType`` are
present as columns. This enforces the contract that energy decomposition (e.g. solar,
wind, base load) is complete before downstream aggregation.

**EnsembleForecastDataset** is the first-stage output of ensemble forecasters. It carries
``forecast_start``, ``quantiles``, ``forecaster_names``, and ``target_column`` as
attributes alongside the data, so downstream stages can reconstruct context without
out-of-band metadata.

.. note::

   Construction of any validated dataset raises ``MissingColumnsError`` immediately if
   required columns are absent. This fail-fast behaviour is intentional: it surfaces data
   quality problems at the boundary between pipeline stages rather than deep inside model
   code.

Domain Types
------------

``openstef_core.types`` provides a small set of value types that give the library a
precise, self-documenting vocabulary.

LeadTime
^^^^^^^^

``LeadTime`` is a ``timedelta`` subclass representing a forecast horizon. It is used
throughout the API wherever a horizon duration is expected, making it impossible to
accidentally pass a raw integer or an unrelated ``timedelta``.

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta

   horizon = LeadTime(timedelta(hours=24))

Quantile
^^^^^^^^

``Quantile`` is a ``float`` subclass constrained to ``[0, 1]``. It provides formatting
and parsing helpers so that quantile column names are generated and interpreted
consistently across the library:

.. code-block:: python

   from openstef_core.types import Quantile

   q = Quantile(0.9)
   print(q.format())                    # "0.90"
   print(q.complementary())             # Quantile(0.1)
   print(Quantile.from_percentile(10))  # Quantile(0.1)

AvailableAt
^^^^^^^^^^^

``AvailableAt`` encodes a data-availability offset in the compact ``DnTHHMM[tz]`` format.
It can be applied to a reference datetime or vectorised over a ``DatetimeIndex``, which
is how ``VersionedTimeSeriesDataset`` computes availability windows:

.. code-block:: python

   from openstef_core.types import AvailableAt
   from datetime import datetime

   offset = AvailableAt.from_string("D1T0800")
   reference = datetime(2024, 6, 1, 0, 0)
   print(offset.apply(reference))   # 2024-06-02 08:00:00

EnergyComponentType
^^^^^^^^^^^^^^^^^^^

``EnergyComponentType`` is a ``StrEnum`` whose members define the required columns of an
``EnergyComponentDataset``. Using an enum rather than bare strings means that column
names are a single source of truth: renaming a component is a one-line change that the
type checker propagates everywhere.

.. code-block:: python

   from openstef_core.types import EnergyComponentType

   for component in EnergyComponentType:
       print(component.value)

How Core Underpins the Rest of OpenSTEF
---------------------------------------

Every other package in OpenSTEF depends on ``openstef_core`` for its data contracts:

- **openstef_models** receives ``ForecastInputDataset`` and returns ``ForecastDataset``
  or ``EnsembleForecastDataset``. See :doc:`models` for how transforms and estimators
  consume these types.
- **openstef_beam** pipelines accept and emit the validated dataset types as their
  stage boundaries, so Apache Beam workers can validate data integrity at each step.
  See :doc:`beam` for pipeline construction.
- **openstef_meta** uses ``EnsembleForecastDataset`` as the handoff between individual
  forecasters and the meta-model that combines them. See :doc:`meta` for ensemble
  architecture.

The practical consequence is that any function accepting a ``ForecastInputDataset`` can
trust that the ``load`` column exists, the index is a sorted ``DatetimeIndex``, and the
``sample_interval`` is consistent — no defensive checks required inside the function
body.