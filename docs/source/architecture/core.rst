The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. It defines the shared data structures, abstract base classes, type definitions, and utilities that every other OpenSTEF package builds upon. If you are extending OpenSTEF—writing a custom transform, integrating a new model, or building a pipeline—you will interact with ``openstef-core`` directly.

This page covers the internal structure of ``openstef-core``: the ``TimeSeriesDataset`` class and its versioned counterpart, the mixin and transform base classes, the domain-specific type system, and the configuration utilities. For how these pieces are assembled into full forecasting pipelines, see the :doc:`models` page. For backtesting and evaluation workflows built on top of these structures, see the :doc:`beam` page.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

----

Dataset Layer
-------------

The central abstraction in ``openstef-core`` is ``TimeSeriesDataset``. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and attaches the metadata that energy forecasting pipelines require: a fixed ``sample_interval``, optional versioning columns, and validated feature lists.

Basic Construction
^^^^^^^^^^^^^^^^^^

At minimum, a ``TimeSeriesDataset`` needs a ``DataFrame`` with a ``DatetimeIndex`` and a ``sample_interval``:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   data = pd.DataFrame(
       {
           "temperature": [20.1, 22.3, 21.5, 19.8],
           "load": [100.0, 120.0, 110.0, 105.0],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

   print(dataset.feature_names)   # ['temperature', 'load']
   print(dataset.is_versioned)    # False
   print(dataset.sample_interval) # 0:15:00

The class enforces that the index is a ``DatetimeIndex`` and automatically sorts rows by timestamp. The ``feature_names`` property returns all columns that are not internal versioning columns, making it straightforward to pass the right column names to downstream model training code.

Versioned Datasets
^^^^^^^^^^^^^^^^^^

Many real-world forecasting scenarios involve data that is not available instantaneously. A weather forecast issued at 06:00 for the next 48 hours carries a different information value than one issued at 18:00 for the same period. ``TimeSeriesDataset`` supports two versioning strategies to model this:

- **Horizon versioning** — a ``horizon`` column stores ``timedelta`` values indicating how far ahead each row was predicted.
- **Availability versioning** — an ``available_at`` column stores the ``datetime`` at which each row's data became available.

``TimeSeriesDataset`` detects which strategy applies automatically based on which column is present:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   # Versioned by forecast horizon
   data_versioned = pd.DataFrame(
       {
           "load": [100.0, 120.0, 100.0, 118.0],
           "horizon": pd.to_timedelta(["1h", "2h", "1h", "2h"]),
       },
       index=pd.date_range("2025-01-01", periods=4, freq="1h"),
   )

   dataset = TimeSeriesDataset(data_versioned, sample_interval=timedelta(hours=1))

   print(dataset.is_versioned)  # True
   print(dataset.horizons)      # [Timedelta('0 days 01:00:00'), Timedelta('0 days 02:00:00')]

Once a dataset is versioned, you can select a specific horizon slice for model training or evaluation without copying data manually:

.. code-block:: python

   # Select only the 1-hour-ahead rows
   horizon_1h = dataset.select_lead_time(timedelta(hours=1))

Persistence
^^^^^^^^^^^

``TimeSeriesDataset`` implements ``DatasetMixin``, which provides Parquet-based persistence. Metadata such as the ``sample_interval`` and versioning column names is preserved across serialization:

.. code-block:: python

   from pathlib import Path

   dataset.to_parquet(Path("my_dataset.parquet"))
   reloaded = TimeSeriesDataset.read_parquet(Path("my_dataset.parquet"))

The ``pipe`` method (also from ``DatasetMixin``) allows functional chaining of arbitrary transformations without breaking the dataset abstraction:

.. code-block:: python

   def add_rolling_mean(ds: TimeSeriesDataset) -> TimeSeriesDataset:
       ds.data["load_rolling"] = ds.data["load"].rolling(4).mean()
       return ds

   dataset = dataset.pipe(add_rolling_mean)

----

Type System
-----------

``openstef-core`` defines two domain-specific types in ``openstef_core.types`` that appear throughout the library wherever time relationships matter.

``LeadTime``
^^^^^^^^^^^^

``LeadTime`` is a ``timedelta`` subtype that also accepts ISO 8601 duration strings. It is used to represent forecast horizons in a way that is both human-readable and serializable:

.. code-block:: python

   from openstef_core.types import LeadTime

   lt = LeadTime.from_string("PT1H30M")  # 1 hour 30 minutes
   print(lt.to_hours())                  # 1.5

   # LeadTime validates multiple input forms
   lt2 = LeadTime.validate(timedelta(hours=6))
   print(lt2.to_hours())  # 6.0

``AvailableAt``
^^^^^^^^^^^^^^^

``AvailableAt`` represents a recurring availability offset relative to a reference day—for example, "day-ahead data available at 14:00 UTC". It uses a compact ``DnTHHMM[tz]`` string format:

.. code-block:: python

   from datetime import datetime
   from openstef_core.types import AvailableAt

   # Data available the same day at 14:00 UTC
   avail = AvailableAt.from_string("D0T1400UTC")

   reference = datetime(2025, 6, 15)
   print(avail.apply(reference))  # 2025-06-15 14:00:00+00:00

``AvailableAt.apply_index`` applies the offset to an entire ``DatetimeIndex`` at once, which is how pipeline code filters training data to respect realistic data availability constraints.

----

Transform Interfaces
--------------------

Transforms in OpenSTEF follow the scikit-learn ``fit`` / ``transform`` pattern, but operate on ``TimeSeriesDataset`` objects rather than raw arrays. The abstract base classes live in ``openstef_core.transforms.dataset_transforms``:

- ``TimeSeriesTransform`` — for transforms that consume and produce ``TimeSeriesDataset``.
- ``VersionedTimeSeriesTransform`` — for transforms that operate on versioned datasets.

Both inherit from the lower-level ``Transform`` mixin defined in ``openstef_core.mixins``.

.. code-block:: python

   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   class NormalisedLoad(TimeSeriesTransform):
       """Normalise the load column to zero mean and unit variance."""

       def fit(self, data: TimeSeriesDataset) -> None:
           self._mean = data.data["load"].mean()
           self._std = data.data["load"].std()

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           data.data["load_norm"] = (data.data["load"] - self._mean) / self._std
           return data

       @property
       def features_added(self) -> list[str]:
           return ["load_norm"]

The ``features_added`` property is important: downstream components use it to track which columns were introduced by each transform, enabling clean feature bookkeeping across a multi-step pipeline. The ``is_fitted`` property guards against calling ``transform`` before ``fit``.

.. note::

   The ``openstef-models`` package ships a collection of ready-made transforms for energy-specific feature engineering (solar irradiance estimates, calendar features, lag features). You rarely need to implement ``TimeSeriesTransform`` from scratch unless you are adding genuinely novel domain knowledge.

----

Configuration Utilities
-----------------------

``openstef-core`` provides a thin configuration layer built on Pydantic. ``BaseConfig`` is the recommended base class for any configuration object in the OpenSTEF ecosystem:

.. code-block:: python

   from pathlib import Path
   from openstef_core.base_model import BaseConfig

   class ForecastConfig(BaseConfig):
       location_id: str
       sample_interval_minutes: int = 15
       forecast_horizon_hours: int = 48

   # Round-trip through YAML
   config = ForecastConfig(location_id="substation_42", forecast_horizon_hours=24)
   config.write_yaml(Path("forecast_config.yaml"))

   reloaded = ForecastConfig.read_yaml(Path("forecast_config.yaml"))
   print(reloaded.location_id)  # substation_42

The ``read_yaml_config`` / ``write_yaml_config`` module-level functions provide the same functionality when you need to handle multiple config types dynamically. ``PydanticStringPrimitive`` is the base class used by ``LeadTime`` and ``AvailableAt`` to add string-serializable domain types that integrate cleanly with Pydantic models.

----

How Core Provides the Foundation
---------------------------------

The relationship between ``openstef-core`` and the rest of the library is straightforward: ``openstef-core`` defines *what data looks like* and *what operations on data look like*, while other packages define *specific implementations* of those operations.

- ``openstef-models`` imports ``TimeSeriesDataset``, ``TimeSeriesTransform``, and ``VersionedTimeSeriesTransform`` to build its preprocessing pipelines and model wrappers. All energy-specific feature engineering is implemented as concrete ``TimeSeriesTransform`` subclasses—see the :doc:`models` page for details.
- ``openstef-beam`` imports ``TimeSeriesDataset`` and the ``AvailableAt`` / ``LeadTime`` types to construct backtesting scenarios that respect realistic data availability windows—see the :doc:`beam` page for details.

This layering means that ``openstef-core`` itself has no dependency on any forecasting model or evaluation framework. You can use ``TimeSeriesDataset`` and the transform interfaces in your own code without pulling in the full OpenSTEF stack.

.. note::

   ``openstef-core`` is intentionally unopinionated. It does not assume a particular model type, training strategy, or deployment environment. The design goal is to provide stable, well-typed contracts so that the higher-level packages—and your own extensions—can evolve independently.