The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. Every other package — ``openstef-models``, ``openstef-beam``, and ``openstef-meta`` — depends on it. Rather than containing forecasting logic itself, ``openstef-core`` defines the shared data structures, abstract interfaces, and type primitives that give the rest of the library a consistent vocabulary. This page explains what lives in ``openstef-core``, how its pieces relate to each other, and how you work with them directly.

.. note:: [DIAGRAM: Component-level diagram of the openstef-core package showing four internal layers: (1) types module (LeadTime, AvailableAt, PydanticStringPrimitive), (2) datasets layer (TimeSeriesMixin, DatasetMixin protocols → TimeSeriesDataset → VersionedTimeSeriesDataset), (3) transforms layer (Transform mixin → TimeSeriesTransform → VersionedTimeSeriesTransform), and (4) utilities layer (base_model, config I/O, pandas helpers, validation). Arrows indicate dependency direction flowing upward from types through datasets and transforms to utilities.]

Package Structure
-----------------

``openstef-core`` is organised into four cohesive areas:

- **Types** — domain-specific primitives (``LeadTime``, ``AvailableAt``) that carry semantic meaning beyond a plain ``timedelta`` or ``str``.
- **Datasets** — the ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` classes, built on protocol mixins that define the expected interface for any time series data object.
- **Transforms** — abstract base classes (``TimeSeriesTransform``, ``VersionedTimeSeriesTransform``) that define the scikit-learn-style fit/transform contract used throughout the library.
- **Utilities** — configuration I/O helpers (``BaseModel``, ``BaseConfig``), pandas utilities, and validation routines shared across packages.

The design is deliberately lean. ``openstef-core`` avoids pulling in heavy ML dependencies; it only requires ``pandas`` and ``pydantic``, which keeps it fast to import and easy to depend on.

Domain Types
------------

Two custom types appear throughout the OpenSTEF API and deserve attention before looking at the dataset classes.

``LeadTime`` wraps a ``timedelta`` and adds ISO 8601 duration parsing and a ``to_hours()`` convenience method. Wherever a forecast horizon is expected, you will see ``LeadTime`` rather than a raw ``timedelta``.

``AvailableAt`` encodes *when during the day* a particular data source becomes available — for example, a weather forecast published at 06:00 UTC each day. Its ``DnTHHMM[tz]`` string format captures both a day offset and a time-of-day. Calling ``apply(date)`` resolves it against a concrete reference date, and ``apply_index(index)`` vectorises that operation over a ``DatetimeIndex``.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, AvailableAt

    # LeadTime from an ISO 8601 duration string
    horizon = LeadTime.from_string("PT4H")
    print(horizon.to_hours())   # 4.0

    # AvailableAt: data available at 06:00 on the same day (D0T0600)
    availability = AvailableAt.from_string("D0T0600")
    from datetime import datetime
    resolved = availability.apply(datetime(2025, 6, 1))
    print(resolved)  # 2025-06-01 06:00:00

Both types are Pydantic-compatible through ``PydanticStringPrimitive``, so they round-trip cleanly through YAML configuration files and JSON serialisation.

The TimeSeriesDataset
---------------------

``TimeSeriesDataset`` is the central data structure in OpenSTEF. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` and enforces a fixed ``sample_interval``. All transforms, models, and evaluation routines in the library accept and return ``TimeSeriesDataset`` instances, so understanding this class is essential.

**Creating a dataset**

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
    data.index.name = "timestamp"

    dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

    print(dataset.feature_names)    # ['temperature', 'load']
    print(dataset.sample_interval)  # 0:15:00
    print(dataset.is_versioned)     # False

The constructor sorts data by timestamp automatically, so you do not need to pre-sort your DataFrame. Pass ``is_sorted=True`` only when you are certain the data is already ordered and want to skip the sort for performance.

**Versioned datasets**

A dataset becomes *versioned* when it tracks not just *what* the data values are, but *when* they were available. This matters in real forecasting pipelines where measurements arrive with a delay. ``TimeSeriesDataset`` supports two versioning modes:

- **Horizon-based**: a ``horizon`` column (``timedelta`` dtype) records how far ahead each row was forecast.
- **Availability-based**: an ``available_at`` column (``datetime`` dtype) records when each measurement became available.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

    data = pd.DataFrame(
        {
            "load": [100.0, 120.0, 110.0],
            "horizon": pd.to_timedelta(["1h", "2h", "4h"]),
        },
        index=pd.date_range("2025-01-01", periods=3, freq="1h"),
    )
    data.index.name = "timestamp"

    versioned = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))
    print(versioned.is_versioned)   # True
    print(versioned.horizons)       # [LeadTime('PT1H'), LeadTime('PT2H'), LeadTime('PT4H')]

**Filtering**

The ``TimeSeriesMixin`` protocol defines a rich set of filtering methods that all dataset classes implement:

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef_core.types import LeadTime

    # Filter by time range
    subset = dataset.filter_by_range(
        start=datetime(2025, 1, 1, 0, 0),
        end=datetime(2025, 1, 1, 0, 30),
    )

    # On a versioned dataset: keep only rows available before a cutoff
    cutoff = datetime(2025, 1, 1, 2, 0)
    available_subset = versioned.filter_by_available_before(cutoff)

    # Keep only rows at or beyond a specific lead time
    long_horizon = versioned.filter_by_lead_time(LeadTime.from_string("PT2H"))

All filter methods return a new dataset of the same type, so they chain naturally.

**Persistence**

``DatasetMixin`` adds ``to_parquet`` and ``read_parquet`` so datasets serialise without losing metadata:

.. code-block:: python

    from pathlib import Path

    path = Path("/tmp/my_dataset.parquet")
    dataset.to_parquet(path)

    loaded = TimeSeriesDataset.read_parquet(path)
    print(loaded.sample_interval)  # 0:15:00 — metadata preserved

The ``pipe`` method on ``DatasetMixin`` lets you apply arbitrary functions in a fluent style, which is useful when composing transformation steps without nesting function calls.

VersionedTimeSeriesDataset
--------------------------

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts — each representing data as it was available at a different point in time — into a single object. This is the structure used when you need to simulate historical forecasting conditions faithfully, for example in backtesting.

The ``from_dataframe`` class method is the most convenient entry point:

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    data = pd.DataFrame(
        {
            "load": [100.0, 120.0],
            "temperature": [20.0, 22.0],
        },
        index=pd.DatetimeIndex(
            [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 10, 15)],
            name="timestamp",
        ),
    )

    versioned_ds = VersionedTimeSeriesDataset.from_dataframe(
        data, timedelta(minutes=15)
    )

To convert a ``VersionedTimeSeriesDataset`` into a flat, horizon-indexed ``TimeSeriesDataset`` suitable for model training, use ``to_horizons``:

.. code-block:: python

    from openstef_core.types import LeadTime

    horizons = [LeadTime.from_string("PT1H"), LeadTime.from_string("PT4H")]
    flat = versioned_ds.to_horizons(horizons)
    # flat is a TimeSeriesDataset with a 'horizon' column

Transform Base Classes
----------------------

``openstef-core`` defines the abstract interfaces that all data transformations in the library must implement. The hierarchy is:

- ``Transform`` (generic mixin) — declares ``fit(data)`` and ``transform(data)`` with an ``is_fitted`` property.
- ``TimeSeriesTransform`` — specialises ``Transform`` for ``TimeSeriesDataset`` inputs and outputs; adds ``features_added`` to declare which columns a transform produces.
- ``VersionedTimeSeriesTransform`` — the same contract for ``VersionedTimeSeriesDataset``.

These abstract classes live in ``openstef_core.transforms.dataset_transforms`` and are what ``openstef-models`` builds on when implementing concrete feature engineering steps. If you are writing a custom transform, subclass the appropriate base:

.. code-block:: python

    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


    class SquaredLoadTransform(TimeSeriesTransform):
        """Adds a squared load feature."""

        @property
        def features_added(self) -> list[str]:
            return ["load_squared"]

        def fit(self, data: TimeSeriesDataset) -> None:
            # No parameters to learn for this simple transform
            pass

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            import pandas as pd
            from datetime import timedelta

            new_col = data.data["load"] ** 2
            new_data = data.data.copy()
            new_data["load_squared"] = new_col
            return TimeSeriesDataset(new_data, sample_interval=data.sample_interval)

The ``is_fitted`` property is automatically managed by the mixin; it becomes ``True`` after ``fit`` has been called.

Configuration Utilities
-----------------------

``openstef-core`` provides ``BaseModel`` and ``BaseConfig`` — thin Pydantic wrappers with YAML serialisation baked in. These are used throughout the library for pipeline configuration and are the recommended way to define configuration objects in any OpenSTEF-based project:

.. code-block:: python

    from pathlib import Path
    from openstef_core.base_model import BaseConfig


    class MyPipelineConfig(BaseConfig):
        sample_interval_minutes: int = 15
        forecast_horizons: list[str] = ["PT1H", "PT4H", "PT24H"]


    config = MyPipelineConfig(sample_interval_minutes=15)
    config.write_yaml(Path("pipeline_config.yaml"))

    loaded = MyPipelineConfig.read_yaml(Path("pipeline_config.yaml"))
    print(loaded.forecast_horizons)  # ['PT1H', 'PT4H', 'PT24H']

The ``read_yaml_config`` and ``write_yaml_config`` free functions accept a ``class_type`` argument, which is useful when the concrete type is determined at runtime.

How Core Underpins the Library
------------------------------

The relationship between ``openstef-core`` and the other packages is one of strict dependency: ``openstef-models``, ``openstef-beam``, and ``openstef-meta`` all import from ``openstef-core`` but ``openstef-core`` imports from none of them. This means:

- You can use ``TimeSeriesDataset`` and the type primitives in your own code without pulling in the full ML stack.
- Custom transforms written against the ``TimeSeriesTransform`` interface are automatically compatible with any pipeline in ``openstef-models``.
- Backtesting infrastructure in ``openstef-beam`` operates on the same ``VersionedTimeSeriesDataset`` objects you construct here.

.. note::

   ``openstef-core`` is intentionally dependency-light. Its only runtime requirements are ``pandas`` and ``pydantic``. If you are building tooling that needs to inspect or manipulate OpenSTEF data structures without running models, installing only ``openstef-core`` is sufficient.

For the concrete feature engineering transforms built on top of these base classes, see the :doc:`models` sibling page. For how ``VersionedTimeSeriesDataset`` is used in backtesting and evaluation pipelines, see the :doc:`beam` sibling page.