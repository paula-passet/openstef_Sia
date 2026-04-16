The Core Package
================

The ``openstef-core`` package is the foundational layer of the OpenSTEF library. It defines the shared data structures, type system, and base abstractions that every other OpenSTEF package builds upon. If you are working with ``openstef-models`` or ``openstef-beam``, you are already using ``openstef-core`` — it is the common language spoken across the entire library.

This page covers the internal structure of ``openstef-core``: the ``TimeSeriesDataset`` class and its mixin hierarchy, the domain type system (``LeadTime``, ``AvailableAt``), persistence utilities, and the protocol-based design that keeps the library extensible.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

Package Structure
-----------------

``openstef-core`` is deliberately narrow in scope. It does not contain model training logic, feature engineering, or pipeline orchestration — those live in ``openstef-models`` and ``openstef-beam`` respectively. What it does provide is the stable contract that those packages rely on:

- **datasets** — the ``TimeSeriesDataset`` class and its mixin protocols
- **types** — typed wrappers for domain concepts like lead times and availability timestamps
- **utils** — serialization helpers and low-level pandas utilities
- **base_model** — ``PydanticStringPrimitive``, the root of the type hierarchy

This separation means that a downstream package can depend on ``openstef-core`` without pulling in the full model or beam stack.

TimeSeriesDataset
-----------------

``TimeSeriesDataset`` is the primary data container in OpenSTEF. It wraps a ``pandas.DataFrame`` and enforces a consistent sampling interval, automatic chronological sorting, and optional versioning metadata. Almost every function in the library that accepts or returns data does so through this class.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   # Build a simple 15-minute time series for one day
   index = pd.date_range("2024-01-01", periods=96, freq="15min")
   df = pd.DataFrame({"load_mw": range(96)}, index=index)

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
   )

   print(dataset.sample_interval)   # datetime.timedelta(seconds=900)
   print(dataset.feature_names)     # ['load_mw']
   print(dataset.index[:3])         # DatetimeIndex with first three timestamps

Key properties exposed by the class:

- ``index`` — the ``pd.DatetimeIndex`` of the underlying data
- ``sample_interval`` — the ``timedelta`` between consecutive observations
- ``feature_names`` — list of column names (excluding internal metadata columns)
- ``is_versioned`` — ``True`` when the dataset carries availability or horizon metadata
- ``horizons`` — list of ``LeadTime`` values present, or ``None`` for unversioned data

Versioned Datasets
^^^^^^^^^^^^^^^^^^

A versioned dataset tracks *when* each row of data became available, not just when it was observed. This is essential for realistic backtesting: a model trained on Monday should only see data that was actually published before Monday, even if the underlying measurements cover earlier periods.

Versioning is expressed through two optional columns:

- **horizon column** — a ``LeadTime`` (ISO 8601 duration string) indicating how far ahead each row was forecast
- **available_at column** — an ``AvailableAt`` timestamp indicating when the row was published

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.types import LeadTime

   index = pd.date_range("2024-01-01", periods=48, freq="30min")
   df = pd.DataFrame({
       "load_mw": range(48),
       "horizon": ["PT1H"] * 24 + ["PT2H"] * 24,
   }, index=index)

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=30),
       horizon_column="horizon",
   )

   # Select only the 1-hour-ahead rows
   one_hour_view = dataset.select_horizon(LeadTime(timedelta(hours=1)))
   print(len(one_hour_view.data))  # 24

The ``select_version()`` method resolves a versioned dataset into a plain snapshot by picking the most recently available row for each timestamp — the same operation a real-time system would perform when assembling its input features.

Filtering and Windowing
^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` provides several methods for slicing data without leaving the typed container:

.. code-block:: python

   from datetime import datetime, timedelta

   start = datetime(2024, 1, 1, 6, 0)
   end   = datetime(2024, 1, 1, 18, 0)

   window = dataset.filter_by_range(start=start, end=end)
   print(dataset.calculate_time_coverage())  # timedelta for the full dataset span

The ``pipe()`` method (inherited from ``DatasetMixin``) lets you chain arbitrary transformations while keeping the fluent style familiar from pandas:

.. code-block:: python

   def add_rolling_mean(ds: TimeSeriesDataset) -> TimeSeriesDataset:
       df = ds.data.copy()
       df["load_rolling"] = df["load_mw"].rolling(4).mean()
       return TimeSeriesDataset(data=df, sample_interval=ds.sample_interval)

   enriched = dataset.pipe(add_rolling_mean)

Mixin Architecture
------------------

``TimeSeriesDataset`` inherits from two protocol mixins defined in ``openstef_core.datasets.mixins``:

**TimeSeriesMixin**
   Provides the temporal interface: ``index``, ``sample_interval``, ``horizons``, ``available_at_series``, ``filter_by_range``, ``filter_by_available_before``, ``select_horizon``, and ``select_version``. Any class implementing this protocol can be used wherever a time series is expected.

**DatasetMixin**
   Provides the persistence interface: ``to_parquet``, ``read_parquet``, and ``pipe``. This keeps I/O concerns separate from the temporal logic.

Using protocols rather than concrete base classes means that alternative dataset implementations — for example, a lazy-loading wrapper over a remote store — can satisfy the same interface without inheriting from ``TimeSeriesDataset`` directly.

Persistence
^^^^^^^^^^^

Saving and loading a dataset preserves all metadata, including ``sample_interval`` and column role annotations, via ``DataFrame.attrs``:

.. code-block:: python

   from pathlib import Path
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   path = Path("/tmp/my_dataset.parquet")

   # Round-trip through parquet
   dataset.to_parquet(path)
   restored = TimeSeriesDataset.read_parquet(path)

   assert restored.sample_interval == dataset.sample_interval
   assert restored.feature_names == dataset.feature_names

Internally, ``to_pandas()`` serialises ``sample_interval`` as an ISO 8601 duration string (e.g. ``"PT15M"``), and ``from_pandas()`` reconstructs it. This means the parquet file is self-describing and can be read by any tool that understands parquet, while OpenSTEF can recover the full typed object.

The Type System
---------------

``openstef-core`` defines a small set of domain types that appear throughout the library's API. These are not plain strings or floats — they are validated, serialisable wrappers built on ``PydanticStringPrimitive``.

**LeadTime**
   A ``timedelta`` stored as an ISO 8601 duration string (``"PT1H"``, ``"PT30M"``, etc.). Used to label forecast horizons consistently across datasets, models, and pipeline outputs.

**AvailableAt**
   A timezone-aware ``datetime`` marking when a data point was published. Used by versioned datasets to enforce data availability constraints during backtesting.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime

   h = LeadTime(timedelta(hours=24))
   print(str(h))        # 'PT24H'
   print(h.value)       # datetime.timedelta(days=1)

   # LeadTime supports ordering
   assert LeadTime(timedelta(hours=1)) < LeadTime(timedelta(hours=6))

Because ``LeadTime`` serialises to a plain string, it round-trips cleanly through JSON, parquet attrs, and Pydantic model fields — no custom encoder configuration required.

Utilities
---------

``openstef_core.utils`` contains helpers that are too low-level for the dataset layer but too specialised for a general-purpose library.

**Timedelta serialisation** (``openstef_core.utils.pydantic``)

.. code-block:: python

   from datetime import timedelta
   from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat

   s = timedelta_to_isoformat(timedelta(minutes=15))  # 'PT15M'
   td = timedelta_from_isoformat("PT15M")             # timedelta(seconds=900)

These functions underpin the parquet round-trip described above and are also used directly by ``LeadTime``.

**Pandas helpers** (``openstef_core.utils.pandas``)

``unsafe_sorted_range_slice_idxs`` is an internal helper that computes integer slice boundaries for a sorted ``DatetimeIndex`` without the overhead of label-based indexing. It is used by ``filter_by_range`` to keep windowing operations fast on large datasets.

.. note::

   The ``unsafe_`` prefix signals that this function skips bounds checking for performance. It is not part of the public API and may change between releases. Use ``filter_by_range`` instead.

Validation
----------

``openstef_core.datasets.validation`` provides column-level validators called during ``TimeSeriesDataset`` construction:

- ``validate_datetime_column`` — checks that a column contains timezone-aware datetimes
- ``validate_timedelta_column`` — checks that a column contains valid ISO 8601 duration strings
- ``TimeSeriesValidationError`` — the exception raised when validation fails

These validators run automatically when you construct a ``TimeSeriesDataset`` with ``available_at_column`` or ``horizon_column`` set, so malformed data is caught at ingestion time rather than silently propagating through the pipeline.

How Core Underpins the Rest of OpenSTEF
---------------------------------------

The relationship between ``openstef-core`` and the other packages is straightforward:

- **openstef-models** receives ``TimeSeriesDataset`` objects as inputs to its transform pipeline and returns them as outputs. The validation transforms (``CompletenessChecker``, ``FlatlineChecker``) operate on the same ``feature_names`` property exposed by ``TimeSeriesDataset``. See the :doc:`models` page for details on the transform layer.

- **openstef-beam** uses ``TimeSeriesDataset`` as the unit of data flowing through distributed backtesting pipelines. The ``RestrictedHorizonVersionedTimeSeries`` wrapper — which enforces that a pipeline step cannot see data beyond a given horizon — is built directly on top of ``TimeSeriesDataset.filter_by_available_before`` and ``select_version``. See the :doc:`beam` page for how this integrates with Apache Beam runners.

In both cases, ``openstef-core`` provides the contract; the higher-level packages provide the behaviour.

.. note::

   If you are extending OpenSTEF with a custom data source, implementing the ``TimeSeriesMixin`` and ``DatasetMixin`` protocols is the recommended integration point. You do not need to subclass ``TimeSeriesDataset`` itself — satisfying the protocols is sufficient for compatibility with both ``openstef-models`` and ``openstef-beam``.