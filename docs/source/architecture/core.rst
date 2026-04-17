The openstef_core Package
=========================

The ``openstef_core`` package is the shared foundation of the OpenSTEF library. It defines the dataset hierarchy, domain types, and base classes that every other package — ``openstef_models``, ``openstef_beam``, and ``openstef_meta`` — builds on. This page covers the core data structures in depth: what they enforce, how they relate to each other, and how to use them in practice.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

---

The Mixin System
----------------

Two mixins form the structural backbone of every dataset in OpenSTEF:

- **``TimeSeriesMixin``** — enforces that the underlying data has a monotonically sorted datetime index and a consistent ``sample_interval``. Any class that carries this mixin guarantees temporal regularity.
- **``DatasetMixin``** — provides the persistence interface (``read_parquet`` / ``to_parquet``), the ``pipe_pandas`` escape hatch for arbitrary DataFrame transformations, and ``copy_with`` for creating modified copies while preserving metadata.

Neither mixin is instantiated directly. They exist so that ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` can share the same contract without one inheriting from the other.

.. code-block:: python

   from openstef_core.datasets.mixins import DatasetMixin, TimeSeriesMixin

   # Both concrete dataset roots inherit both mixins
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

   assert issubclass(TimeSeriesDataset, TimeSeriesMixin)
   assert issubclass(TimeSeriesDataset, DatasetMixin)
   assert issubclass(VersionedTimeSeriesDataset, TimeSeriesMixin)
   assert issubclass(VersionedTimeSeriesDataset, DatasetMixin)

The separation matters when writing generic utilities: a function that only needs persistence can type-hint ``DatasetMixin``; one that needs temporal guarantees can type-hint ``TimeSeriesMixin``.

---

TimeSeriesDataset
-----------------

``TimeSeriesDataset`` is the workhorse class. It wraps a ``pd.DataFrame`` whose index is a sorted ``DatetimeIndex`` with a uniform ``sample_interval``. Construction validates both properties and raises ``TimeSeriesValidationError`` on violation.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   index = pd.date_range("2024-01-01", periods=96, freq="15min", tz="UTC")
   df = pd.DataFrame({"load": range(96), "temperature": range(96)}, index=index)

   ds = TimeSeriesDataset(data=df, sample_interval=timedelta(minutes=15))

   print(ds.data.shape)          # (96, 2)
   print(ds.sample_interval)     # 0:15:00

Key operations available on every ``TimeSeriesDataset``:

- ``select_features(["load"])`` — returns a new dataset with only the named columns.
- ``pipe_pandas(func, *args)`` — applies any ``DataFrame → DataFrame`` function and wraps the result back into a dataset.
- ``copy_with(new_df)`` — replaces the underlying data while keeping ``sample_interval`` and other metadata.
- ``to_parquet`` / ``read_parquet`` — round-trip serialisation that preserves the ``sample_interval`` in Parquet metadata.

.. code-block:: python

   # Normalise a feature column without leaving the dataset abstraction
   normalised = ds.pipe_pandas(
       lambda df: df.assign(load=lambda d: (d["load"] - d["load"].mean()) / d["load"].std())
   )

---

VersionedTimeSeriesDataset
--------------------------

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts, each tagged with an ``available_at`` timestamp. This models the real-world situation where different data sources (measurements, weather forecasts, market prices) arrive at different times. The class is the key enabler of realistic backtesting: by calling ``select_version(as_of=t)``, you materialise only the data that would have been available at time ``t``.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   load = VersionedTimeSeriesDataset.read_parquet("load_measurements.parquet")
   weather = VersionedTimeSeriesDataset.read_parquet("weather_forecasts_versioned.parquet")
   epex = VersionedTimeSeriesDataset.read_parquet("EPEX.parquet")

   # Combine with a left join — keeps all load timestamps
   combined = VersionedTimeSeriesDataset.concat(
       [load, weather, epex],
       mode="left",
   )

   # Materialise into a plain TimeSeriesDataset as of "now"
   dataset = combined.select_version()

The ``mode`` parameter mirrors pandas join semantics: ``"left"``, ``"inner"``, and ``"outer"`` are all supported. ``select_version`` returns a ``TimeSeriesDataset``, so all downstream code that accepts the base class works without modification.

.. mermaid:: /diagrams/architecture/core_diagram_2.mmd

---

Validated Datasets
------------------

The four validated dataset classes inherit from ``TimeSeriesDataset`` and add domain-specific column constraints. They are the types that flow between pipeline stages in ``openstef_beam`` and ``openstef_meta``.

ForecastInputDataset
^^^^^^^^^^^^^^^^^^^^

Requires a designated *target column* (default ``"load"``). Provides convenience properties and methods used during model training and inference.

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset, TimeSeriesDataset

   # Promote a generic dataset to a ForecastInputDataset
   forecast_input = ForecastInputDataset.from_timeseries(
       dataset,
       target_column="load",
       forecast_start=pd.Timestamp("2024-03-01 00:00", tz="UTC"),
   )

   target = forecast_input.target_series          # pd.Series of the load column
   features = forecast_input.input_data()         # DataFrame without the target column
   horizon_index = forecast_input.create_forecast_range(horizon=LeadTime("PT24H"))

ForecastDataset
^^^^^^^^^^^^^^^

Holds probabilistic forecasts: one column per ``Quantile`` plus an optional actuals column. The ``median_series`` property extracts the ``q0.50`` column directly.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastDataset

   # Typically produced by a model's predict() call, not constructed manually
   median = forecast_ds.median_series
   p10 = forecast_ds.quantile_series(Quantile(0.10))

EnsembleForecastDataset
^^^^^^^^^^^^^^^^^^^^^^^

Extends ``ForecastDataset`` to hold forecasts from multiple ensemble members. Member columns are separated by the ``"__"`` delimiter (``ENSEMBLE_COLUMN_SEP``), so a column named ``model_a__q0.50`` belongs to member ``model_a`` at quantile ``0.50``. The class provides methods to extract per-member sub-datasets.

EnergyComponentDataset
^^^^^^^^^^^^^^^^^^^^^^

Holds the output of component-splitting models. Each column corresponds to an ``EnergyComponentType`` (e.g. solar, wind, residual load). The dataset validates that all declared components are present as columns.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import EnergyComponentDataset
   from openstef_core.types import EnergyComponentType

   # Inspect which components are present
   print(EnergyComponentType.__members__)
   # e.g. {'solar': 'solar', 'wind': 'wind', ...}

---

Domain Types
------------

``openstef_core.types`` provides typed wrappers for the primitive values that appear throughout the forecasting pipeline. Using these types instead of raw ``float`` or ``timedelta`` values gives you validated serialisation and a self-documenting API.

LeadTime
^^^^^^^^

A ``timedelta`` subclass serialised as ISO 8601 duration strings (e.g. ``"PT15M"``, ``"PT24H"``). Pydantic models that use ``LeadTime`` fields accept both ``timedelta`` objects and ISO strings.

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta

   lt = LeadTime(timedelta(hours=24))
   print(str(lt))          # "PT24H"

   lt2 = LeadTime.from_string("PT15M")
   print(lt2.total_seconds())  # 900.0

Quantile
^^^^^^^^

A ``float`` subclass constrained to ``[0, 1]``. Provides string formatting consistent with ForecastDataset column naming.

.. code-block:: python

   from openstef_core.types import Quantile

   q = Quantile(0.9)
   print(q.format())               # "q0.90"
   print(q.complementary())        # Quantile(0.1)
   print(Quantile.from_percentile(10))  # Quantile(0.1)

AvailableAt
^^^^^^^^^^^

Encodes the offset between a reference timestamp and when data becomes available. Used by ``VersionedTimeSeriesDataset`` to tag data parts and by backtesting pipelines to simulate realistic data availability.

.. code-block:: python

   from openstef_core.types import AvailableAt
   import pandas as pd

   offset = AvailableAt.from_string("D1T0800UTC")  # available next day at 08:00 UTC
   reference = pd.Timestamp("2024-03-01 00:00", tz="UTC")
   print(offset.apply(reference))   # 2024-03-02 08:00:00+00:00

   # Vectorised version for full indexes
   shifted_index = offset.apply_index(some_datetime_index)

EnergyComponentType
^^^^^^^^^^^^^^^^^^^

A ``StrEnum`` enumerating the energy components that ``EnergyComponentDataset`` and component-splitting models work with. Using the enum rather than raw strings prevents typos and makes column names consistent across packages.

.. code-block:: python

   from openstef_core.types import EnergyComponentType

   for component in EnergyComponentType:
       print(component)   # solar, wind, ...

---

Base Classes and Configuration
-------------------------------

``openstef_core`` also exports ``BaseConfig`` (a Pydantic ``BaseModel`` subclass) and the ``Predictor`` generic base class used by ``openstef_models``. These are covered in the :doc:`models` page, which describes how ``ComponentSplitter`` and the forecasting models build on them.

The ``openstef_core.exceptions`` module defines ``TimeSeriesValidationError`` and ``MissingColumnsError`` — the two exceptions you are most likely to encounter when constructing datasets with invalid data.

.. code-block:: python

   from openstef_core.exceptions import TimeSeriesValidationError, MissingColumnsError

   try:
       bad_ds = ForecastInputDataset.from_timeseries(dataset, target_column="nonexistent")
   except MissingColumnsError as exc:
       print(exc)   # descriptive message listing the missing columns

---

How Core Underpins Other Packages
----------------------------------

Every OpenSTEF package imports from ``openstef_core`` rather than defining its own data structures:

- **``openstef_models``** — model ``predict()`` methods accept ``ForecastInputDataset`` and return ``ForecastDataset`` or ``EnergyComponentDataset``. See :doc:`models` for details.
- **``openstef_beam``** — pipeline stages are typed with the validated dataset classes; ``VersionedTimeSeriesDataset`` is the standard input format for backtesting pipelines. See :doc:`beam` for details.
- **``openstef_meta``** — the ensemble forecasting model aggregates ``EnsembleForecastDataset`` instances produced by member models. See :doc:`meta` for details.

This single-source-of-truth design means that a ``ForecastDataset`` produced by a model in ``openstef_models`` can be passed directly to an aggregation step in ``openstef_meta`` without any conversion layer.

.. note::

   All dataset classes are immutable by convention: mutating methods return a new instance rather than modifying in place. This makes it safe to pass datasets across pipeline stages without defensive copying.