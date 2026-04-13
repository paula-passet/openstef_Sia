The Core Package
================

The ``openstef-core`` package is the foundation of the OpenSTEF library. It defines the data structures, type system, abstract interfaces, and shared utilities that every other package depends on. If you are building a custom transform, integrating OpenSTEF into a larger pipeline, or simply want to understand how data flows through the library, this page is the right starting point.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

For details on how the models package builds on these foundations, see :doc:`models`. For backtesting and evaluation utilities, see :doc:`beam`.

----

The Type System
---------------

``openstef-core`` defines a small but carefully designed set of domain types in ``openstef_core.types``. Rather than passing raw ``timedelta`` or ``datetime`` objects through the entire codebase, OpenSTEF wraps these in Pydantic-compatible primitives that carry domain semantics and validate their own inputs.

**LeadTime** represents a forecast horizon as a ``timedelta``. It accepts ISO 8601 duration strings (``"PT1H"``, ``"P1D"``), plain ``timedelta`` objects, or existing ``LeadTime`` instances. The ``.to_hours()`` method provides a convenient float representation for numerical operations.

**AvailableAt** encodes a recurring daily availability offset in the format ``DnTHHMM[tz]`` — for example, ``D0T0600`` means "available at 06:00 on the same day". Calling ``.apply(date)`` resolves the offset against a concrete reference date, and ``.apply_index(index)`` vectorises this over a ``DatetimeIndex``. This type is central to the library's ability to model realistic data-availability constraints, where measurements or weather forecasts are only known with a delay.

Both types extend ``PydanticStringPrimitive``, which means they serialise cleanly to strings in Pydantic models, YAML configuration files, and Parquet metadata.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, AvailableAt

    # LeadTime accepts ISO 8601 strings or timedelta objects
    horizon = LeadTime.from_string("PT4H")
    print(horizon.to_hours())   # 4.0
    assert horizon == LeadTime.validate(timedelta(hours=4))

    # AvailableAt models when data becomes available each day
    availability = AvailableAt.from_string("D0T0800")  # available at 08:00 same day
    from datetime import datetime
    resolved = availability.apply(datetime(2025, 6, 1))
    print(resolved)  # 2025-06-01 08:00:00

----

Datasets
--------

The dataset layer is the most heavily used part of ``openstef-core``. It provides two concrete classes — ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset`` — built on top of two protocol mixins that define the shared interface.

Protocols: TimeSeriesMixin and DatasetMixin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``TimeSeriesMixin`` is a ``Protocol`` that specifies the interface any time series object must satisfy. It declares properties such as ``index``, ``sample_interval``, ``feature_names``, and ``is_versioned``, together with a family of filtering methods:

- ``filter_by_range(start, end)`` — restrict to a time window
- ``filter_by_available_before(available_before)`` — keep only data whose availability timestamp precedes a given moment
- ``filter_by_available_at(available_at)`` — apply a recurring ``AvailableAt`` constraint
- ``filter_by_lead_time(lead_time)`` — keep only rows whose horizon is at least as long as the specified lead time
- ``select_version()`` — collapse a versioned dataset to a single ``TimeSeriesDataset``
- ``calculate_time_coverage()`` — return the total ``timedelta`` spanned by the dataset

``DatasetMixin`` adds persistence and pipeline operations: ``to_parquet``, ``read_parquet``, and ``pipe``. The ``pipe`` method follows the pandas convention — it applies an arbitrary callable to the dataset and returns the result, enabling clean method-chaining without subclassing.

Because both are ``Protocol`` classes, your own dataset implementations are structurally compatible with OpenSTEF transforms and pipelines as long as they satisfy the interface, without requiring inheritance.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the primary data container in OpenSTEF. It wraps a ``pandas.DataFrame`` with a ``DatetimeIndex`` named ``"timestamp"`` and enforces a fixed ``sample_interval``. On construction the data is automatically sorted by timestamp, ensuring downstream code can rely on monotonic ordering.

The class supports two versioning modes, detected automatically from the column names present in the DataFrame:

- **Horizon versioning** — a column (default name ``"horizon"``) holds ``timedelta`` values representing how far ahead each row was forecast.
- **Availability versioning** — a column (default name ``"available_at"``) holds ``datetime`` values recording when each measurement became known.

If neither column is present, ``is_versioned`` returns ``False`` and the dataset behaves as a plain time series.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

    # Plain time series — no versioning
    data = pd.DataFrame(
        {"temperature": [20.1, 22.3, 21.5], "load": [100, 120, 110]},
        index=pd.date_range("2025-01-01", periods=3, freq="15min", name="timestamp"),
    )
    ds = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

    print(ds.feature_names)    # ['temperature', 'load']
    print(ds.is_versioned)     # False
    print(ds.sample_interval)  # 0:15:00

    # Restrict to a time window
    subset = ds.filter_by_range(
        start=pd.Timestamp("2025-01-01 00:00"),
        end=pd.Timestamp("2025-01-01 00:15"),
    )

    # Persist and reload
    ds.to_parquet("my_dataset.parquet")
    reloaded = TimeSeriesDataset.read_parquet("my_dataset.parquet")

Versioned datasets arise naturally when working with forecast archives or delayed-measurement pipelines. Adding a ``"horizon"`` column is all that is needed:

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
    from openstef_core.types import LeadTime

    data = pd.DataFrame(
        {
            "load": [100, 120, 115, 130],
            "horizon": pd.to_timedelta(["1h", "2h", "1h", "2h"]),
        },
        index=pd.date_range("2025-01-01", periods=4, freq="1h", name="timestamp"),
    )
    ds = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))

    print(ds.is_versioned)   # True
    print(ds.horizons)       # [LeadTime('PT1H'), LeadTime('PT2H')]

    # Keep only rows with at least a 2-hour lead time
    long_horizon = ds.filter_by_lead_time(LeadTime.from_string("PT2H"))

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` composes multiple ``TimeSeriesDataset`` parts — each representing data as it was known at a particular point in time — into a single object. The ``from_dataframe`` class method is the most convenient entry point when you already have a flat DataFrame with an ``available_at`` column:

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    data = pd.DataFrame(
        {
            "load": [100, 120],
            "temperature": [20.0, 22.0],
            "available_at": [
                datetime(2025, 1, 1, 8, 0),
                datetime(2025, 1, 1, 8, 0),
            ],
        },
        index=pd.DatetimeIndex(
            [datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 10, 15)],
            name="timestamp",
        ),
    )
    vds = VersionedTimeSeriesDataset.from_dataframe(data, timedelta(minutes=15))

    # Convert to a horizon-based TimeSeriesDataset for model training
    from openstef_core.types import LeadTime
    horizon_ds = vds.to_horizons([LeadTime.from_string("PT2H"), LeadTime.from_string("PT4H")])

The ``to_horizons`` method is particularly important: it bridges the gap between the versioned representation used during data collection and the horizon-indexed format that forecasting models expect during training.

----

Transform Base Classes
----------------------

``openstef-core`` defines the abstract base classes for all data transformations in ``openstef_core.transforms.dataset_transforms``. These follow the scikit-learn ``fit`` / ``transform`` pattern, extended to work with ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``.

- **TimeSeriesTransform** — operates on ``TimeSeriesDataset`` → ``TimeSeriesDataset``. Implement ``transform(data)`` and optionally ``fit(data)``. The ``features_added`` property declares which column names the transform introduces, enabling downstream components to introspect the pipeline.
- **VersionedTimeSeriesTransform** — the same contract for ``VersionedTimeSeriesDataset`` → ``VersionedTimeSeriesDataset``.

Both inherit from the generic ``Transform`` mixin defined in ``openstef_core.mixins``, which provides the ``is_fitted`` guard and enforces that ``transform`` is only called after ``fit``.

The ``openstef-models`` package provides concrete implementations of these base classes — see :doc:`models` for examples of energy-specific feature transforms built on this interface.

.. code-block:: python

    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform

    class NormalisationTransform(TimeSeriesTransform):
        """Subtract the mean learned during fit."""

        def fit(self, data: TimeSeriesDataset) -> None:
            self._means = data.data[data.feature_names].mean()

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            normalised = data.data.copy()
            normalised[data.feature_names] -= self._means
            return TimeSeriesDataset(normalised, sample_interval=data.sample_interval)

        @property
        def features_added(self) -> list[str]:
            return []  # no new columns, only modifies existing ones

----

Configuration and Persistence Utilities
----------------------------------------

``openstef_core.base_model`` provides ``BaseModel`` and ``BaseConfig``, thin wrappers around Pydantic's ``BaseModel`` that add YAML serialisation:

.. code-block:: python

    from pathlib import Path
    from openstef_core.base_model import BaseConfig

    class ForecastConfig(BaseConfig):
        horizon_hours: int = 24
        sample_interval_minutes: int = 15
        target_column: str = "load"

    config = ForecastConfig(horizon_hours=48)
    config.write_yaml(Path("forecast_config.yaml"))

    reloaded = ForecastConfig.read_yaml(Path("forecast_config.yaml"))
    print(reloaded.horizon_hours)  # 48

The module-level helpers ``write_yaml_config`` and ``read_yaml_config`` accept a ``class_type`` argument, which is useful when the concrete type is only known at runtime.

``openstef_core.utils`` also exposes ``timedelta_from_isoformat`` and ``timedelta_to_isoformat`` for round-tripping ``timedelta`` values through YAML and Parquet metadata, and ``openstef_core.utils.pandas.unsafe_sorted_range_slice_idxs`` for high-performance temporal slicing of sorted indexes used internally by the dataset classes.

----

How Core Underpins the Rest of OpenSTEF
-----------------------------------------

Every other package in the library imports from ``openstef-core`` but never the reverse. This strict dependency direction means:

- **openstef-models** imports ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, ``TimeSeriesTransform``, and the type primitives to build its preprocessing pipelines and model wrappers. See :doc:`models` for details.
- **openstef-beam** imports the same dataset types to define its backtesting and evaluation interfaces. See :doc:`beam` for details.
- Your own code can depend on ``openstef-core`` alone if you only need the data structures and transform contracts, without pulling in the heavier model or evaluation dependencies.

.. note::

   ``openstef-core`` is intentionally kept lightweight. It has no dependency on machine learning frameworks such as scikit-learn, XGBoost, or LightGBM. This makes it safe to use as a shared dependency in environments where those libraries are not available or where version pinning is strict.