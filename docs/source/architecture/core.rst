The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. It defines the shared data structures, abstract base classes, type system, and utility functions that every other package — ``openstef-models``, ``openstef-beam``, and ``openstef-meta`` — builds upon. Understanding ``openstef-core`` means understanding the contracts that hold the whole library together.

This page covers the internal structure of ``openstef-core``: the ``TimeSeriesDataset`` class and its versioning model, the mixin and base-class hierarchy, the domain-specific type system, and the configuration utilities. For transforms implemented on top of these foundations in the models package, see the :doc:`models` page.

.. note:: [DIAGRAM: Component-level diagram of the openstef-core package showing four internal layers: (1) Types & Utilities — LeadTime, AvailableAt, timedelta helpers, pandas utilities; (2) Base Models & Config — BaseModel, BaseConfig, PydanticStringPrimitive, YAML I/O; (3) Mixins — Transform, TransformPipeline, Predictor, BatchPredictor, Stateful; (4) Datasets — DatasetMixin, TimeSeriesMixin, TimeSeriesDataset, VersionedTimeSeriesDataset. Arrows show upward dependency: Datasets depend on Mixins and Types; Mixins depend on Base Models; all other packages (openstef-models, openstef-beam) depend on the Datasets and Mixins layer.]

----

The ``TimeSeriesDataset`` Class
--------------------------------

``TimeSeriesDataset`` is the primary data container in OpenSTEF. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a consistent ``sample_interval``, guaranteeing that every downstream transform and model receives well-formed temporal data.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   # Build a simple 15-minute time series
   index = pd.date_range("2025-01-01", periods=96, freq="15min")
   data = pd.DataFrame(
       {"load_mw": [100 + i * 0.5 for i in range(96)]},
       index=index,
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

   print(dataset.sample_interval)   # 0:15:00
   print(dataset.feature_names)     # ['load_mw']
   print(dataset.is_versioned)      # False
   print(dataset.calculate_time_coverage())  # 23:45:00

The class automatically sorts data by timestamp on construction and exposes a ``DatetimeIndex`` through the ``index`` property. Persistence is handled through ``DatasetMixin``:

.. code-block:: python

   # Round-trip to Parquet — metadata is preserved
   dataset.to_parquet("load_data.parquet")
   restored = TimeSeriesDataset.read_parquet("load_data.parquet")

   assert restored.sample_interval == dataset.sample_interval

The ``pipe`` method, also from ``DatasetMixin``, allows fluent chaining of arbitrary functions without breaking out of the dataset abstraction:

.. code-block:: python

   def clip_outliers(ds: TimeSeriesDataset, upper: float) -> TimeSeriesDataset:
       clipped = ds.data.clip(upper=upper)
       return TimeSeriesDataset(clipped, sample_interval=ds.sample_interval)

   cleaned = dataset.pipe(clip_outliers, upper=200.0)

Versioned Datasets
^^^^^^^^^^^^^^^^^^

Many real-world forecasting problems involve data that was not available at the time a forecast was made — weather observations arrive with delay, meter readings are backfilled, and so on. ``TimeSeriesDataset`` handles this through an optional versioning model.

A dataset becomes versioned when it contains either a **horizon column** (a ``LeadTime`` per row) or an **available_at column** (an ``AvailableAt`` timestamp per row). The class detects which scheme is in use automatically:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.types import LeadTime

   index = pd.date_range("2025-01-01", periods=4, freq="15min")
   data = pd.DataFrame(
       {
           "load_mw": [100, 110, 105, 115],
           "horizon": [
               LeadTime(timedelta(hours=1)),
               LeadTime(timedelta(hours=1)),
               LeadTime(timedelta(hours=24)),
               LeadTime(timedelta(hours=24)),
           ],
       },
       index=index,
   )

   versioned = TimeSeriesDataset(
       data,
       sample_interval=timedelta(minutes=15),
       horizon_column="horizon",
   )

   print(versioned.is_versioned)   # True
   print(versioned.horizons)       # [LeadTime('PT1H'), LeadTime('PT24H')]

   # Select only rows for the 1-hour horizon
   h1_view = versioned.select_horizon(LeadTime(timedelta(hours=1)))

The three versioning states are:

- **Unversioned** — plain time series, ``is_versioned`` is ``False``.
- **Horizon-versioned** — each row carries a ``LeadTime``; use ``select_horizon()`` to slice.
- **Availability-versioned** — each row carries an ``AvailableAt``; use ``select_version()`` to obtain the view of data that would have been available at a given point in time.

----

The Domain Type System
-----------------------

``openstef-core`` defines two domain-specific types that appear throughout the library. Both extend ``PydanticStringPrimitive``, meaning they serialise cleanly to strings in configuration files and Parquet metadata.

``LeadTime``
^^^^^^^^^^^^

``LeadTime`` wraps ``timedelta`` and parses ISO 8601 duration strings (e.g. ``"PT1H"``, ``"PT15M"``). It is used wherever a forecast horizon needs to be expressed unambiguously:

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta

   # Construction from timedelta or ISO 8601 string
   h1 = LeadTime(timedelta(hours=1))
   h1_str = LeadTime.from_string("PT1H")

   assert h1 == h1_str
   print(h1.to_hours())   # 1.0

``AvailableAt``
^^^^^^^^^^^^^^^

``AvailableAt`` represents a recurring data-availability offset relative to a reference day, expressed in the compact ``DnTHHMM[tz]`` format. This is particularly useful for modelling when a weather forecast or meter reading becomes available each day:

.. code-block:: python

   from openstef_core.types import AvailableAt
   from datetime import datetime, timezone

   # "D0T0600" means: day 0 (same day) at 06:00
   morning_release = AvailableAt.from_string("D0T0600")

   reference = datetime(2025, 6, 1, tzinfo=timezone.utc)
   print(morning_release.apply(reference))
   # 2025-06-01 06:00:00+00:00

Together, ``LeadTime`` and ``AvailableAt`` give OpenSTEF a precise vocabulary for describing the temporal constraints of real operational forecasting pipelines.

----

The Mixin Hierarchy
--------------------

``openstef-core`` uses a layered mixin architecture to compose behaviour without deep inheritance chains. The ``openstef_core.mixins`` package exports four building blocks:

``Stateful``
^^^^^^^^^^^^

``Stateful`` provides serialisation hooks so that any fitted object (a transform, a model) can be saved and restored. It is the base for all stateful components in the library.

``Transform``
^^^^^^^^^^^^^

``Transform[I, O]`` is a generic abstract base class following the scikit-learn ``fit`` / ``transform`` pattern. The type parameters ``I`` and ``O`` make the input and output contracts explicit at the type-checker level:

.. code-block:: python

   from openstef_core.mixins import Transform
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   class MyScaler(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       def fit(self, data: TimeSeriesDataset) -> None:
           self._mean = data.data.mean()
           self._std = data.data.std()

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           scaled = (data.data - self._mean) / self._std
           return TimeSeriesDataset(scaled, sample_interval=data.sample_interval)

   scaler = MyScaler()
   scaler.fit(dataset)
   scaled_dataset = scaler.transform(dataset)
   print(scaler.is_fitted())   # True

``TransformPipeline``
^^^^^^^^^^^^^^^^^^^^^

``TransformPipeline`` chains multiple ``Transform`` instances, fitting and applying them in sequence. This is the mechanism used by ``openstef-models`` to build preprocessing pipelines — see the :doc:`models` page for concrete examples.

``Predictor`` and ``BatchPredictor``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Predictor`` defines the inference interface that all forecasting models must implement. ``BatchPredictor`` extends it with a ``BatchResult`` return type for scenarios where predictions are generated over many horizons or time windows simultaneously. These abstract classes are what ``openstef-models`` implements; ``openstef-beam`` depends on them for backtesting.

.. note::

   The mixin layer is intentionally thin. ``Transform``, ``Predictor``, and ``Stateful`` define *interfaces*, not implementations. This keeps ``openstef-core`` free of heavy dependencies and makes it straightforward to implement custom components that integrate naturally with the rest of the library.

----

Configuration and Base Models
-------------------------------

``openstef-core`` provides ``BaseModel`` and ``BaseConfig`` — Pydantic-backed classes with built-in YAML serialisation — as the standard way to define configuration objects across the library:

.. code-block:: python

   from pathlib import Path
   from openstef_core.base_model import BaseConfig

   class ForecastConfig(BaseConfig):
       horizon_hours: int = 24
       sample_interval_minutes: int = 15
       feature_set: list[str] = ["temperature", "irradiance"]

   # Write and read back via YAML
   cfg = ForecastConfig(horizon_hours=48)
   cfg.write_yaml(Path("forecast_config.yaml"))

   restored = ForecastConfig.read_yaml(Path("forecast_config.yaml"))
   assert restored.horizon_hours == 48

The module-level helpers ``write_yaml_config`` and ``read_yaml_config`` accept a ``class_type`` argument, making it possible to deserialise configuration objects without knowing their concrete type at the call site — useful for plugin-style model registries.

----

How Core Underpins the Other Packages
---------------------------------------

Every other OpenSTEF package depends on ``openstef-core`` and nothing else from the mono-repo:

- **openstef-models** imports ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, ``Transform``, ``TransformPipeline``, and ``Predictor`` to build its preprocessing pipelines and model wrappers. See :doc:`models` for details.
- **openstef-beam** imports ``Predictor``, ``BatchPredictor``, and ``TimeSeriesDataset`` to run backtests and compute metrics across large datasets. See :doc:`beam` for details.
- **openstef-meta** uses the same ``Predictor`` interface so that ensemble meta-models are interchangeable with single-model predictors.

This strict dependency direction — all arrows point inward to ``openstef-core`` — means the core package can be tested and reasoned about in isolation, and that any component built against its interfaces will compose correctly with the rest of the library.