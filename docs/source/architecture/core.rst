The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. It defines the shared data structures, abstract interfaces, type system, and persistence utilities that every other package — ``openstef-models``, ``openstef-beam``, and ``openstef-meta`` — depends on. If you are extending OpenSTEF with custom transforms, models, or pipelines, understanding ``openstef-core`` is essential.

This page covers the internal structure of the package: the dataset classes, the mixin-based protocol system, the type primitives, and the base configuration utilities.

.. mermaid:: diagrams/architecture/core_diagram_1.mmd

Dataset Classes
---------------

The heart of ``openstef-core`` is its dataset abstraction. Rather than passing raw ``pandas.DataFrame`` objects between pipeline stages, OpenSTEF wraps time series data in structured containers that enforce consistency guarantees and carry temporal metadata.

``TimeSeriesDataset``
^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the primary data container. It holds a ``pandas.DataFrame`` indexed by a ``DatetimeIndex`` named ``timestamp``, and it guarantees that:

- rows are sorted in ascending temporal order,
- a fixed ``sample_interval`` (a ``timedelta``) describes the spacing between consecutive observations, and
- feature names are tracked separately from internal bookkeeping columns such as ``horizon`` or ``available_at``.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

    # Build a simple 15-minute time series
    data = pd.DataFrame(
        {
            "temperature": [20.1, 22.3, 21.5, 19.8],
            "load": [100.0, 120.0, 110.0, 105.0],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="15min", name="timestamp"),
    )

    dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

    print(dataset.feature_names)      # ['temperature', 'load']
    print(dataset.sample_interval)    # 0:15:00
    print(dataset.is_versioned)       # False
    print(dataset.calculate_time_coverage())  # 0:45:00

The class also supports *versioned* datasets, where each row carries information about when the data became available. This is important for realistic backtesting: weather forecasts and meter readings are not instantly available, so a model trained or evaluated without accounting for data latency will be overly optimistic.

Versioning is detected automatically from the DataFrame columns:

- If a ``horizon`` column is present, the dataset is versioned by forecast horizon (a ``timedelta`` per row).
- If an ``available_at`` column is present, the dataset is versioned by wall-clock availability time.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

    data_versioned = pd.DataFrame(
        {
            "load": [100.0, 120.0],
            "horizon": pd.to_timedelta(["1h", "2h"]),
        },
        index=pd.date_range("2025-01-01", periods=2, freq="1h", name="timestamp"),
    )

    dataset = TimeSeriesDataset(data_versioned, sample_interval=timedelta(hours=1))

    print(dataset.is_versioned)   # True
    print(dataset.horizons)       # [LeadTime('PT1H'), LeadTime('PT2H')]

``VersionedTimeSeriesDataset``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` is a higher-level container that groups multiple ``TimeSeriesDataset`` parts — each representing data as it was available at a different point in time. It exposes the same filtering interface as ``TimeSeriesDataset`` and adds a ``to_horizons()`` method that materialises multi-horizon training data by selecting the appropriate version for each lead time.

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef_core.datasets import VersionedTimeSeriesDataset

    data = pd.DataFrame(
        {
            "load": [100.0, 120.0],
            "temperature": [20.0, 22.0],
        },
        index=pd.DatetimeIndex(
            [
                datetime.fromisoformat("2025-01-01T10:00:00"),
                datetime.fromisoformat("2025-01-01T10:15:00"),
            ],
            name="timestamp",
        ),
    )

    versioned = VersionedTimeSeriesDataset.from_dataframe(
        data, sample_interval=timedelta(minutes=15)
    )

    print(versioned.feature_names)  # ['load', 'temperature']

The ``from_dataframe`` convenience constructor wraps a plain DataFrame in a single-part ``VersionedTimeSeriesDataset``, which is the most common starting point when loading historical data.

Mixin-Based Protocol System
----------------------------

``openstef-core`` uses Python ``Protocol`` classes (structural subtyping) rather than abstract base classes with inheritance. This design means you can integrate your own dataset types into OpenSTEF pipelines without subclassing any OpenSTEF class, as long as your type satisfies the protocol interface.

Two protocols are defined in ``openstef_core.datasets.mixins``:

- **``TimeSeriesMixin``** — defines the temporal interface: ``index``, ``sample_interval``, ``feature_names``, ``is_versioned``, and a family of filtering methods (``filter_by_range``, ``filter_by_available_before``, ``filter_by_available_at``, ``filter_by_lead_time``, ``select_version``, ``calculate_time_coverage``).
- **``DatasetMixin``** — defines the persistence interface: ``to_parquet``, ``read_parquet``, and a ``pipe`` method for chaining transformations in a readable style.

``TimeSeriesDataset`` composes both mixins, so it satisfies both protocols simultaneously.

The ``pipe`` method deserves special mention. It mirrors the ``pandas.DataFrame.pipe`` pattern, allowing you to chain dataset transformations without deeply nested function calls:

.. code-block:: python

    from datetime import datetime

    result = (
        dataset
        .pipe(lambda ds: ds.filter_by_range(
            start=datetime(2025, 1, 1, 0, 0),
            end=datetime(2025, 1, 1, 12, 0),
        ))
        .pipe(lambda ds: ds.filter_by_lead_time(lead_time="PT1H"))
    )

Type Primitives
---------------

``openstef_core.types`` defines two domain-specific scalar types that appear throughout the library's API:

``LeadTime``
^^^^^^^^^^^^

``LeadTime`` represents a forecast horizon as a ``timedelta``, but with ISO 8601 duration string serialisation (e.g., ``"PT1H"`` for one hour, ``"P1D"`` for one day). It is Pydantic-compatible and validates inputs from ``str``, ``timedelta``, or another ``LeadTime``.

.. code-block:: python

    from openstef_core.types import LeadTime

    lt = LeadTime.from_string("PT4H")
    print(lt.to_hours())   # 4.0

    # Pydantic validates these automatically in model fields
    lt2 = LeadTime.validate(timedelta(hours=24))
    print(lt2.to_hours())  # 24.0

``AvailableAt``
^^^^^^^^^^^^^^^

``AvailableAt`` encodes a recurring daily availability offset in the compact ``DnTHHMM[tz]`` format. It answers the question: "On any given day, at what time does this data source become available?" Calling ``apply(date)`` resolves the offset against a concrete reference date to produce an absolute ``datetime``.

.. code-block:: python

    from datetime import date
    from openstef_core.types import AvailableAt

    # Data available at 08:00 UTC on the day itself
    availability = AvailableAt.from_string("D0T0800UTC")
    print(availability.apply(date(2025, 6, 15)))
    # 2025-06-15 08:00:00+00:00

These types flow through dataset filtering (``filter_by_available_at``, ``filter_by_lead_time``) and into the transform layer, ensuring that data availability constraints are expressed consistently across the entire library.

Transform Base Classes
----------------------

``openstef_core.transforms.dataset_transforms`` provides the abstract base classes for all data transformations in OpenSTEF. They follow the scikit-learn ``fit`` / ``transform`` pattern and are typed against the dataset classes described above.

- **``TimeSeriesTransform``** — operates on ``TimeSeriesDataset`` in, ``TimeSeriesDataset`` out. Subclasses must implement ``transform`` and may override ``fit`` for stateful transformations.
- **``VersionedTimeSeriesTransform``** — same contract, but for ``VersionedTimeSeriesDataset``.

Both inherit from the lower-level ``Transform`` mixin defined in ``openstef_core.mixins``, which provides the ``is_fitted`` property and enforces the two-phase lifecycle.

.. code-block:: python

    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

    class ScaleLoadTransform(TimeSeriesTransform):
        """Scales the 'load' column by a fixed factor learned during fit."""

        def __init__(self, column: str = "load") -> None:
            self.column = column
            self._scale: float | None = None

        def fit(self, data: TimeSeriesDataset) -> None:
            self._scale = float(data.data[self.column].max())

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            scaled = data.data.copy()
            scaled[self.column] = scaled[self.column] / self._scale
            return TimeSeriesDataset(scaled, sample_interval=data.sample_interval)

        @property
        def features_added(self) -> list[str]:
            return []

Custom transforms written against these base classes are automatically compatible with the pipeline infrastructure in ``openstef-models``. See the :doc:`models` page for how transforms are composed into full training pipelines.

Configuration Utilities
-----------------------

``openstef_core.base_model`` provides two Pydantic-based building blocks used throughout the library for structured configuration:

- **``BaseModel``** — extends Pydantic's ``BaseModel`` with no additional behaviour; serves as the common root so that all OpenSTEF data classes share a consistent validation and serialisation strategy.
- **``BaseConfig``** — adds ``read_yaml`` and ``write_yaml`` class/instance methods, making it straightforward to load pipeline configuration from YAML files and round-trip it back to disk.

.. code-block:: python

    from pathlib import Path
    from openstef_core.base_model import BaseConfig

    class ForecastConfig(BaseConfig):
        horizon_hours: int = 48
        sample_interval_minutes: int = 15
        target_column: str = "load"

    # Persist and reload configuration
    config = ForecastConfig(horizon_hours=24, target_column="net_load")
    config.write_yaml(Path("forecast_config.yaml"))

    reloaded = ForecastConfig.read_yaml(Path("forecast_config.yaml"))
    print(reloaded.horizon_hours)  # 24

Persistence
-----------

Both ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` implement Parquet-based persistence through the ``DatasetMixin`` protocol. Metadata such as ``sample_interval``, ``horizon_column``, and ``available_at_column`` is preserved alongside the data, so a round-tripped dataset is identical to the original.

.. code-block:: python

    from pathlib import Path

    # Save
    dataset.to_parquet(Path("my_dataset.parquet"))

    # Load — metadata is restored automatically
    restored = TimeSeriesDataset.read_parquet(Path("my_dataset.parquet"))
    print(restored.sample_interval)  # 0:15:00
    print(restored.feature_names)    # ['temperature', 'load']

.. note::

   Parquet is the recommended format for persisting datasets between pipeline stages, particularly in distributed workflows built with ``openstef-beam``. See the :doc:`beam` page for how datasets are serialised and passed between Beam transforms.

How Core Provides the Foundation
---------------------------------

Every other OpenSTEF package depends on ``openstef-core`` and only on ``openstef-core`` for its data contracts:

- **``openstef-models``** receives ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` as inputs to its preprocessing pipelines and training routines, and returns ``TimeSeriesDataset`` as forecast output. Its transform classes subclass ``TimeSeriesTransform`` and ``VersionedTimeSeriesTransform`` directly. See the :doc:`models` page for details.
- **``openstef-beam``** uses ``VersionedTimeSeriesDataset`` as the unit of work flowing through backtesting pipelines, and relies on ``LeadTime`` and ``AvailableAt`` to enforce data availability constraints during evaluation. See the :doc:`beam` page for how these are used in practice.
- **``openstef-meta``** builds ensemble and meta-learning models on top of the same dataset and transform interfaces, requiring no changes to the core contracts.

This layering means that improvements to the core data structures — better validation, new filtering methods, additional persistence formats — propagate automatically to all higher-level packages without requiring coordinated changes across the codebase.