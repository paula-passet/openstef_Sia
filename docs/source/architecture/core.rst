The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. It defines the data structures, abstract base classes, type system, and composable utilities that every other package builds upon. Understanding ``openstef-core`` is essential before working with ``openstef-models`` or ``openstef-beam``, because those packages speak the language that ``openstef-core`` defines.

This page covers the internal structure of ``openstef-core``: its dataset classes, mixin hierarchy, transform pipeline, and type system. For the feature-engineering transforms that consume these structures, see the :doc:`models` page. For distributed backtesting that orchestrates them at scale, see the :doc:`beam` page.

.. note:: [DIAGRAM: Component-level diagram of the openstef-core package showing four internal layers — (1) types (LeadTime, AvailableAt), (2) datasets (DatasetMixin, TimeSeriesMixin → TimeSeriesDataset → VersionedTimeSeriesDataset), (3) mixins (Stateful → Transform → TransformPipeline; Stateful → Predictor → BatchPredictor), and (4) utils (pandas helpers, ISO 8601 duration parsing) — with arrows indicating inheritance and dependency relationships between layers and outward arrows to openstef-models and openstef-beam.]

Package Layout
--------------

``openstef-core`` is deliberately narrow in scope. It contains no ML models and no domain-specific feature logic. Its role is to establish contracts — through abstract base classes and typed data containers — that the rest of the library honours.

The package is organised into four areas:

- **datasets** — ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``, plus the mixins and validation logic they rely on.
- **mixins** — ``Stateful``, ``Transform``, ``TransformPipeline``, ``Predictor``, and ``BatchPredictor``.
- **types** — ``LeadTime`` and ``AvailableAt``, the domain-specific scalar types used throughout the API.
- **utils** — Pandas helpers and ISO 8601 duration utilities consumed internally.

Datasets
--------

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the primary data container in OpenSTEF. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a consistent ``sample_interval``. On construction the data is automatically sorted by timestamp, so downstream code can rely on monotonic ordering without additional checks.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   data = pd.DataFrame(
       {
           "temperature": [20.1, 22.3, 21.5],
           "load": [100, 120, 110],
       },
       index=pd.date_range("2025-01-01", periods=3, freq="15min"),
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

   print(dataset.feature_names)   # ['temperature', 'load']
   print(dataset.is_versioned)    # False

The class supports *versioned* datasets — situations where the same timestamp may have multiple observations depending on when the data was available. Versioning is detected automatically:

- If the DataFrame contains a **horizon column**, data is versioned by forecast horizon (a ``timedelta`` per row indicating how far ahead the value was predicted).
- If the DataFrame contains an **available_at column**, data is versioned by the wall-clock time at which each row became available.
- Otherwise the dataset is treated as a plain time series.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   data_with_horizon = pd.DataFrame(
       {
           "load": [100, 120],
           "horizon": [timedelta(hours=1), timedelta(hours=2)],
       },
       index=pd.date_range("2025-01-01", periods=2, freq="15min"),
   )

   versioned = TimeSeriesDataset(
       data_with_horizon,
       sample_interval=timedelta(minutes=15),
       horizon_column="horizon",
   )

   print(versioned.is_versioned)  # True

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

For realistic backtesting, data often arrives in multiple batches with different availability times, and naively concatenating those batches into a single DataFrame creates O(n²) memory growth due to misaligned ``(timestamp, available_at)`` pairs. ``VersionedTimeSeriesDataset`` solves this with **lazy composition**: it holds a list of ``TimeSeriesDataset`` parts and defers the actual DataFrame merge until ``select_version()`` is called.

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Two data parts arriving at different times
   part_a = TimeSeriesDataset(
       pd.DataFrame(
           {"temperature": [20.5, 21.0]},
           index=pd.date_range("2025-01-01 00:00", periods=2, freq="1h"),
       ),
       sample_interval=timedelta(hours=1),
   )

   part_b = TimeSeriesDataset(
       pd.DataFrame(
           {"temperature": [21.5, 22.0]},
           index=pd.date_range("2025-01-01 02:00", periods=2, freq="1h"),
       ),
       sample_interval=timedelta(hours=1),
   )

   versioned = VersionedTimeSeriesDataset(data_parts=[part_a, part_b])

   # Materialise a point-in-time view — no unnecessary concatenation before this call
   snapshot = versioned.select_version(
       as_of=datetime(2025, 1, 1, 3, 0)
   )

This pattern is central to how ``openstef-beam`` implements backtesting without inflating memory usage across large historical windows.

Mixin Hierarchy
---------------

All stateful objects in OpenSTEF — transforms, predictors, and pipelines — inherit from a common ``Stateful`` mixin. ``Stateful`` provides a versioned serialisation contract (``__getstate__`` / ``__setstate__``) so that fitted objects can be persisted and restored without losing the library version they were fitted with.

.. code-block:: text

   Stateful
   ├── Transform[I, O]          # fit() + transform() + fit_transform()
   │   ├── TimeSeriesTransform  # specialised for TimeSeriesDataset
   │   ├── VersionedTimeSeriesTransform
   │   └── TransformPipeline    # sequential composition of transforms
   └── Predictor[I, O]          # fit() + predict() + fit_predict()
       └── BatchPredictor[I, O] # adds predict_batch() for lists of inputs

The generic type parameters ``I`` and ``O`` mean the same mixin can describe a transform that converts a ``TimeSeriesDataset`` to a ``TimeSeriesDataset``, or a predictor that accepts a ``TimeSeriesDataset`` and returns a ``pd.DataFrame`` of forecasts. The concrete type bindings are enforced at the subclass level.

Transform and TransformPipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Transform`` is the scikit-learn-style base class for all data transformations. Subclasses implement ``transform()`` and optionally ``fit()`` if the transformation must learn parameters from training data. The ``is_fitted`` property guards against calling ``transform()`` before ``fit()``.

``TransformPipeline`` composes multiple transforms into a single object that behaves as a ``Transform`` itself. Fitting the pipeline fits each stage in sequence, passing the output of each stage as the input to the next:

.. code-block:: python

   from openstef_core.mixins import Transform, TransformPipeline

   # Assuming MyScaler and MyImputer are concrete Transform subclasses
   pipeline = TransformPipeline(transforms=[MyImputer(), MyScaler()])

   pipeline.fit(training_dataset)
   transformed = pipeline.transform(inference_dataset)

Because ``TransformPipeline`` is itself a ``Transform``, pipelines can be nested. The ``openstef-models`` package ships a library of ready-made ``TimeSeriesTransform`` subclasses (clipping, wind-power features, temporal features, and more) that plug directly into this pipeline abstraction — see the :doc:`models` page for details.

Predictor and BatchPredictor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Predictor`` mirrors the ``Transform`` interface but separates the *fitting* phase (learning from labelled data) from the *prediction* phase (generating outputs for new inputs). ``BatchPredictor`` extends this with ``predict_batch()``, which accepts a list of input datasets and returns a ``BatchResult`` — useful when the same model must generate forecasts for many grid connections in a single pass, as ``openstef-beam`` does.

.. note::

   ``Predictor`` and ``BatchPredictor`` define the *interface*. Concrete model implementations live in ``openstef-models``, keeping ``openstef-core`` free of ML framework dependencies.

Type System
-----------

Two domain-specific scalar types in ``openstef_core.types`` appear throughout the API and deserve explicit attention.

``LeadTime``
^^^^^^^^^^^^

``LeadTime`` is a ``timedelta`` subtype that can be constructed from an ISO 8601 duration string. It is used wherever a forecast horizon is expressed as a configuration value rather than a computed column.

.. code-block:: python

   from openstef_core.types import LeadTime

   lt = LeadTime.from_string("PT1H")   # 1-hour lead time
   print(lt.to_hours())                # 1.0

   # Pydantic models accept raw strings and coerce automatically
   # e.g. HyperParams(lead_time="PT15M") → LeadTime of 15 minutes

``AvailableAt``
^^^^^^^^^^^^^^^

``AvailableAt`` encodes a relative availability offset in the compact ``DnTHHMM[tz]`` format. Given a reference date it computes the absolute ``datetime`` at which data for that day becomes available. This is the mechanism that drives realistic data-availability simulation in backtesting.

.. code-block:: python

   from datetime import datetime
   from openstef_core.types import AvailableAt

   # Data for day D is available at 06:00 UTC on day D+1
   availability = AvailableAt.from_string("D1T0600UTC")
   reference = datetime(2025, 1, 1)

   print(availability.apply(reference))
   # 2025-01-02 06:00:00+00:00

``apply_index()`` vectorises this operation over a ``pd.DatetimeIndex``, which is how ``VersionedTimeSeriesDataset`` filters data parts efficiently during backtesting.

Utilities
---------

The ``openstef_core.utils`` sub-package contains helpers that support the dataset and mixin layers:

- **``timedelta_from_isoformat`` / ``timedelta_to_isoformat``** — round-trip conversion between ``timedelta`` and ISO 8601 duration strings, used when serialising ``TimeSeriesDataset`` metadata to Parquet.
- **``unsafe_sorted_range_slice_idxs``** — a fast integer-index lookup for sorted ``DatetimeIndex`` slices, used internally by ``TimeSeriesDataset`` to avoid the overhead of label-based ``loc`` slicing in tight loops.
- **``combine_timeseries_indexes``** — merges multiple ``DatetimeIndex`` objects with configurable ``left``, ``outer``, or ``inner`` join semantics, used by ``VersionedTimeSeriesDataset`` when materialising a version snapshot.

These utilities are intentionally low-level and internal. They are not part of the public API surface; prefer the dataset methods that call them.

How Core Provides the Foundation
---------------------------------

The relationship between ``openstef-core`` and the rest of the library follows a strict dependency direction: ``openstef-core`` has no knowledge of ``openstef-models`` or ``openstef-beam``. The dependency flows outward only.

- ``openstef-models`` imports ``TimeSeriesDataset``, ``TimeSeriesTransform``, and ``Predictor`` to build concrete feature transforms and forecasting models.
- ``openstef-beam`` imports ``VersionedTimeSeriesDataset`` and ``BatchPredictor`` to orchestrate distributed backtesting across Apache Beam workers.

This means that any code written against the ``openstef-core`` abstractions — a custom ``Transform`` subclass, a bespoke ``Predictor`` — will compose cleanly with both packages without modification.

.. note::

   If you are implementing a custom transform or model, subclass the appropriate mixin from ``openstef-core`` rather than from ``openstef-models``. This keeps your code decoupled from the built-in feature library and ensures compatibility with the full pipeline infrastructure.