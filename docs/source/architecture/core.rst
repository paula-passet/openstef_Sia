The Core Package
================

The ``openstef_core`` package is the foundation on which every other OpenSTEF package is built. It defines the canonical data structures for time series data, the abstract base classes that govern how transforms and models behave, shared type aliases, validation helpers, and pandas utilities. Understanding ``openstef_core`` is the key to understanding how the rest of the library fits together.

This page focuses exclusively on the internals of ``openstef_core``. For the transforms that ``openstef_models`` builds on top of these structures, see :doc:`models`. For backtesting pipelines that consume them, see :doc:`beam`. For ensemble models, see :doc:`meta`.

.. mermaid:: /diagrams/architecture/core_diagram_1.mmd

Package Layout
--------------

``openstef_core`` is intentionally narrow in scope. It ships no forecasting models and no training pipelines. Its job is to provide stable, well-validated abstractions that the rest of the library can rely on without re-implementing them. The main sub-modules are:

- ``openstef_core.datasets`` — dataset classes and validated domain subtypes
- ``openstef_core.transforms`` — abstract base classes for stateful data transforms
- ``openstef_core.mixins`` — the generic ``Transform`` protocol
- ``openstef_core.types`` — type aliases such as ``LeadTime`` and ``AvailableAt``
- ``openstef_core.utils`` — pandas helpers and ISO-8601 timedelta serialisation
- ``openstef_core.exceptions`` — shared exception hierarchy

The Dataset Hierarchy
---------------------

The central abstraction in ``openstef_core`` is the dataset. All dataset classes share two mixins:

- **``DatasetMixin``** — a ``Protocol`` that mandates ``to_parquet``, ``read_parquet``, and ``pipe`` so every dataset can be persisted and composed with arbitrary functions.
- **``TimeSeriesMixin``** — adds temporal metadata: a ``DatetimeIndex``, a ``sample_interval``, and helpers for slicing by time range.

These mixins are combined in two concrete classes.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the workhorse of the library. It wraps a ``pandas.DataFrame`` whose index is a sorted ``DatetimeIndex`` with a fixed ``sample_interval``. Construction validates the index automatically, so downstream code can always assume regularity.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset

    # Build a simple 15-minute dataset
    index = pd.date_range("2024-01-01", periods=96, freq="15min")
    df = pd.DataFrame({"load_mw": range(96)}, index=index)

    ds = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

    print(ds.sample_interval)   # 0:15:00
    print(ds.feature_names)     # ['load_mw']
    print(ds.calculate_time_coverage())  # 23:45:00

The class also supports *versioned* data — situations where each row carries information about when it became available (via an ``available_at`` column or a ``horizon`` column). This is essential for realistic backtesting, where you must never use data that would not yet have been available at forecast time.

.. code-block:: python

    # Inspect versioning metadata
    print(ds.is_versioned)      # False for a plain dataset

    # Persist and reload, preserving all metadata
    ds.to_parquet("load_data.parquet")
    ds_reloaded = TimeSeriesDataset.read_parquet("load_data.parquet")

    # Functional composition via pipe
    def add_rolling_mean(dataset: TimeSeriesDataset) -> TimeSeriesDataset:
        df = dataset.data.copy()
        df["rolling_mean"] = df["load_mw"].rolling(4).mean()
        return TimeSeriesDataset(df.dropna(), dataset.sample_interval)

    ds_enriched = ds.pipe(add_rolling_mean)

Key properties at a glance:

- ``index`` — the underlying ``pd.DatetimeIndex``
- ``sample_interval`` — ``timedelta`` between consecutive samples
- ``feature_names`` — list of non-metadata column names
- ``is_versioned`` — whether the dataset carries availability metadata
- ``horizons`` — list of ``LeadTime`` values when present
- ``calculate_time_coverage()`` — total span as a ``timedelta``

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` composes *multiple* ``TimeSeriesDataset`` parts into a single unified view that tracks data availability over time. Each part represents data as it was known at a particular point in history. The class validates that parts share the same ``sample_interval`` and that their feature columns do not overlap.

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Combine two data parts (e.g., actuals and a revision)
    versioned = VersionedTimeSeriesDataset([part_a, part_b])

    # Select the view of the data available at a specific moment
    snapshot = versioned.select_version(available_at=some_datetime)

This design is what makes OpenSTEF's backtesting honest: the ``openstef_beam`` package uses ``VersionedTimeSeriesDataset`` to replay history without leaking future information.

Validated Domain Datasets
^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_core.datasets`` also exports several validated subclasses that encode domain knowledge as type constraints:

- **``ForecastInputDataset``** — validated input features for a forecast run
- **``ForecastDataset``** — validated forecast output with horizon columns
- **``EnergyComponentDataset``** — energy decomposition (e.g., solar, wind, load components)
- **``EnsembleForecastDataset``** — multi-model ensemble outputs

Using these types rather than raw ``TimeSeriesDataset`` instances lets the library catch domain errors at the boundary rather than deep inside a pipeline.

The Transform Abstraction
--------------------------

``openstef_core.mixins`` defines a generic ``Transform[InputT, OutputT]`` protocol modelled on the scikit-learn ``fit`` / ``transform`` pattern. Two concrete abstract base classes in ``openstef_core.transforms`` specialise this for forecasting:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform

    class NormalisationTransform(TimeSeriesTransform):
        """Normalise all features to [0, 1] using training-set min/max."""

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
            return []   # no new columns, existing ones are modified in-place

The ``features_added`` property is a contract that lets pipeline builders inspect what columns a transform introduces without running it. ``VersionedTimeSeriesTransform`` provides the same interface for versioned datasets, enabling transforms that are aware of data availability.

.. note::

   Stateless transforms can skip overriding ``fit`` — the base class default is a no-op and ``is_fitted`` returns ``True`` unconditionally.

Types and Utilities
-------------------

``openstef_core.types`` defines two important aliases used throughout the library:

- ``LeadTime`` — a ``timedelta`` representing how far ahead a forecast looks
- ``AvailableAt`` — a ``datetime`` representing when a data point became available

These aliases make function signatures self-documenting and allow type checkers to catch misuse early.

``openstef_core.utils`` provides two categories of helpers:

**Timedelta serialisation** — ``timedelta_to_isoformat`` and ``timedelta_from_isoformat`` convert Python ``timedelta`` objects to and from ISO-8601 duration strings (e.g., ``"PT15M"``). This is used internally when persisting dataset metadata to Parquet.

.. code-block:: python

    from openstef_core.utils import timedelta_to_isoformat, timedelta_from_isoformat
    from datetime import timedelta

    iso = timedelta_to_isoformat(timedelta(minutes=15))
    print(iso)  # 'PT15M'

    td = timedelta_from_isoformat("PT1H")
    print(td)   # 1:00:00

**Pandas helpers** — ``openstef_core.utils.pandas`` exposes low-level functions such as ``unsafe_sorted_range_slice_idxs`` and ``combine_timeseries_indexes`` that are used internally for efficient slicing and merging of time-indexed DataFrames. These are considered internal API; prefer the dataset methods over calling them directly.

How Other Packages Depend on Core
-----------------------------------

Every other OpenSTEF package takes ``openstef_core`` as a direct dependency and builds on it without re-implementing its abstractions:

- **openstef_models** implements concrete ``TimeSeriesTransform`` subclasses (feature engineering, lag creation, calendar features) and wraps scikit-learn-compatible estimators that accept ``TimeSeriesDataset`` inputs. See :doc:`models`.
- **openstef_beam** defines training and backtesting pipelines that consume ``VersionedTimeSeriesDataset`` and produce ``ForecastDataset`` outputs. It also uses ``EnergyComponentDataset`` for component-level evaluation. See :doc:`beam`.
- **openstef_meta** builds ensemble models on top of the ``ForecastDataset`` and ``EnsembleForecastDataset`` types. See :doc:`meta`.

This layering means that a custom transform or model written against ``openstef_core`` types will work anywhere in the stack — in a standalone script, inside an ``openstef_beam`` pipeline, or as a component of an ``openstef_meta`` ensemble.

.. note::

   ``openstef_core`` has a deliberately small dependency footprint: ``pandas``, ``numpy``, ``pyarrow``, ``pydantic``, and ``joblib``. This makes it safe to install in environments where the heavier ML dependencies of ``openstef_models`` are not available.