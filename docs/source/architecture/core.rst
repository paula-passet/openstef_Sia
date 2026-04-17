The Core Package
================

The ``openstef_core`` package is the foundation of the OpenSTEF library. Every other package — ``openstef_models``, ``openstef_beam``, and ``openstef_meta`` — depends on it. Rather than containing forecasting logic itself, ``openstef_core`` defines the shared data structures, abstract base classes, type aliases, and utilities that give the rest of the library a consistent vocabulary. This page explains what those building blocks are and how to use them directly.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

Package Layout
--------------

``openstef_core`` is organised into a small number of focused sub-modules:

- **datasets** — ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and validated domain-specific subclasses such as ``ForecastDataset`` and ``ForecastInputDataset``.
- **transforms** — Abstract base classes (``TimeSeriesTransform``, ``VersionedTimeSeriesTransform``) that define the fit/transform contract used throughout the library.
- **mixins** — Protocol classes (``DatasetMixin``, ``TimeSeriesMixin``, ``Transform``) that define shared behaviour without imposing a concrete inheritance hierarchy.
- **types** — Lightweight type aliases (``LeadTime``, ``AvailableAt``) used as a shared type language across packages.
- **utils** — Pandas helpers, ISO-8601 timedelta serialisation, and other small utilities.

The ``TimeSeriesDataset`` Class
--------------------------------

``TimeSeriesDataset`` is the central data structure in OpenSTEF. It wraps a ``pandas.DataFrame`` and enforces a consistent sampling interval, automatic chronological sorting, and optional versioning metadata. Most pipelines in ``openstef_models`` and ``openstef_beam`` accept or return instances of this class.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Build a simple 15-minute load time series
    index = pd.date_range("2024-01-01", periods=96, freq="15min")
    df = pd.DataFrame({"load_mw": [100.0 + i * 0.5 for i in range(96)]}, index=index)

    ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    print(ds.sample_interval)   # 0:15:00
    print(ds.index[:3])         # DatetimeIndex with first three timestamps
    print(ds.feature_names)     # ['load_mw']

Key properties available on every ``TimeSeriesDataset``:

- ``index`` — the ``pd.DatetimeIndex`` of the underlying data.
- ``sample_interval`` — the ``timedelta`` between consecutive observations.
- ``feature_names`` — list of column names, excluding internal bookkeeping columns.
- ``is_versioned`` — ``True`` when the dataset carries availability metadata.
- ``horizons`` — list of forecast lead times present, or ``None`` for plain datasets.

Persistence is built in via the ``DatasetMixin`` protocol. Datasets round-trip cleanly through Parquet, preserving all metadata:

.. code-block:: python

    from pathlib import Path
    from openstef_core.datasets import TimeSeriesDataset

    path = Path("/tmp/load_data.parquet")
    ds.to_parquet(path)

    ds_loaded = TimeSeriesDataset.read_parquet(path)
    assert ds_loaded.sample_interval == ds.sample_interval

The ``pipe`` method, also provided by ``DatasetMixin``, lets you chain transformations in a readable, functional style:

.. code-block:: python

    result = ds.pipe(some_transform_function, extra_arg=42)

Versioned Datasets
------------------

Energy forecasting requires careful handling of *data availability*: a measurement recorded at time *t* may not arrive in a data warehouse until *t + Δ*. Naively ignoring this leads to optimistic backtests that would not reproduce in production.

``VersionedTimeSeriesDataset`` solves this by composing multiple ``TimeSeriesDataset`` parts, each carrying an ``available_at`` timestamp. When you call ``select_version(available_at=t)``, the dataset returns only the data that would have been visible at time *t*, making realistic backtesting straightforward.

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset

    # Two data parts delivered at different times
    idx_early = pd.date_range("2024-01-01", periods=48, freq="15min")
    idx_late  = pd.date_range("2024-01-02", periods=48, freq="15min")

    part_a = TimeSeriesDataset(
        pd.DataFrame({"load_mw": range(48)}, index=idx_early),
        sample_interval=timedelta(minutes=15),
    )
    part_b = TimeSeriesDataset(
        pd.DataFrame({"load_mw": range(48, 96)}, index=idx_late),
        sample_interval=timedelta(minutes=15),
    )

    versioned = VersionedTimeSeriesDataset([part_a, part_b])

    # Simulate what data was available at noon on Jan 2
    snapshot = versioned.select_version(
        available_at=datetime(2024, 1, 2, 12, 0)
    )

``VersionedTimeSeriesDataset`` is the primary input type for backtesting pipelines in ``openstef_beam``. See the :doc:`beam` page for how it is consumed there.

Validated Domain Datasets
--------------------------

``openstef_core`` ships several ``TimeSeriesDataset`` subclasses that add domain-specific column validation. These are the types that flow between pipeline stages in higher-level packages:

- ``ForecastInputDataset`` — validated input features ready for model inference.
- ``ForecastDataset`` — model output containing point forecasts and optional quantiles.
- ``EnergyComponentDataset`` — decomposed energy components (solar, wind, load, etc.).
- ``EnsembleForecastDataset`` — forecasts from multiple models before aggregation.

Using these types rather than plain ``TimeSeriesDataset`` instances means that structural errors (missing required columns, wrong dtypes) are caught at construction time rather than silently propagating through a pipeline.

.. code-block:: python

    from openstef_core.datasets import ForecastDataset

    # ForecastDataset validates that required forecast columns are present
    forecast_ds = ForecastDataset(forecast_df, sample_interval=timedelta(minutes=15))

Abstract Transform Base Classes
---------------------------------

The ``openstef_core.transforms`` module defines the contract that all data transformations in the library must follow. The design mirrors scikit-learn's ``fit``/``transform`` pattern but operates on ``TimeSeriesDataset`` objects rather than NumPy arrays.

.. code-block:: python

    from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


    class NormalisationTransform(TimeSeriesTransform):
        """Normalise all features to the range [0, 1]."""

        def __init__(self):
            self._min = None
            self._max = None

        @property
        def is_fitted(self) -> bool:
            return self._min is not None

        def fit(self, data: TimeSeriesDataset) -> None:
            self._min = data.data.min()
            self._max = data.data.max()

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            normalised = (data.data - self._min) / (self._max - self._min)
            return TimeSeriesDataset(normalised, data.sample_interval)

        @property
        def features_added(self) -> list[str]:
            return []  # no new columns, existing ones are modified in-place

The parallel ``VersionedTimeSeriesTransform`` base class follows the same interface but operates on ``VersionedTimeSeriesDataset`` inputs, allowing transforms to be applied across the full versioned history. The ``openstef_models`` package provides concrete implementations of both base classes — see the :doc:`models` page for details.

.. note::

   Transforms are stateful by design. Always call ``fit`` on training data before calling ``transform`` on held-out or production data. The ``is_fitted`` property lets you guard against accidental use of an unfitted transform.

Types and Utilities
--------------------

Two type aliases from ``openstef_core.types`` appear throughout the library's public API:

- ``LeadTime`` — a ``timedelta`` representing a forecast horizon (e.g., ``timedelta(hours=24)``).
- ``AvailableAt`` — a ``datetime`` marking when a data version became available.

Using these aliases rather than bare ``timedelta`` and ``datetime`` makes function signatures self-documenting and allows type checkers to catch misuse.

The ``openstef_core.utils`` module provides helpers that are used internally but are also available to library users:

.. code-block:: python

    from openstef_core.utils import timedelta_from_isoformat, timedelta_to_isoformat

    # Serialise a timedelta to an ISO 8601 duration string
    iso = timedelta_to_isoformat(timedelta(minutes=15))  # "PT15M"

    # Round-trip back to a timedelta
    td = timedelta_from_isoformat("PT15M")
    assert td == timedelta(minutes=15)

These utilities are used internally when persisting dataset metadata to Parquet, ensuring that ``sample_interval`` survives serialisation without loss of precision.

How Other Packages Build on Core
----------------------------------

The dependency graph is strictly one-directional: ``openstef_core`` has no knowledge of the packages above it.

- **openstef_models** imports ``TimeSeriesDataset``, ``ForecastInputDataset``, ``ForecastDataset``, and the transform base classes to implement concrete feature engineering and model wrappers. See :doc:`models`.
- **openstef_beam** imports ``VersionedTimeSeriesDataset`` and ``ForecastDataset`` to drive backtesting pipelines and compute evaluation metrics. See :doc:`beam`.
- **openstef_meta** builds ensemble models on top of ``EnsembleForecastDataset`` and the validated dataset types. See :doc:`meta`.

This layering means you can use ``openstef_core`` in isolation — for example, to build a custom data ingestion pipeline or a bespoke transform — without pulling in the heavier model or backtesting dependencies.

.. note::

   ``openstef_core`` is intentionally kept lightweight. Its only non-standard dependencies are ``pandas``, ``numpy``, ``pyarrow``, ``pydantic``, and ``joblib``. If you are building tooling that needs to read or write OpenSTEF datasets without running forecasts, installing ``openstef-core`` alone is sufficient.