The openstef_core Package
=========================

The ``openstef_core`` package is the shared foundation of the OpenSTEF library. It defines the validated dataset hierarchy, domain types, and mixin interfaces that every other package—``openstef_models``, ``openstef_beam``, and ``openstef_meta``—builds upon. This page covers the data structures and abstractions you will encounter most often when working with OpenSTEF at any level.

.. note:: [DIAGRAM: Class hierarchy showing TimeSeriesMixin and DatasetMixin as shared protocol bases on the left; TimeSeriesDataset (inherits both mixins) and VersionedTimeSeriesDataset (inherits both mixins) as sibling concrete classes; ForecastInputDataset, ForecastDataset, EnergyComponentDataset, and EnsembleForecastDataset as subclasses of TimeSeriesDataset on the right]

Dataset Hierarchy
-----------------

All dataset types in OpenSTEF share two protocol bases: ``TimeSeriesMixin`` and ``DatasetMixin``. Together they enforce that every dataset can be persisted to and from Parquet, piped through transformation functions, and queried for its temporal properties (index, sample interval, feature names). Concrete classes then add domain-specific invariants on top.

The Mixin Bases
^^^^^^^^^^^^^^^

``TimeSeriesMixin`` guarantees that a dataset holds a ``pd.DatetimeIndex`` with a consistent ``sample_interval``, exposes ``feature_names``, and provides ``horizons`` and ``available_at_series`` for datasets that carry forecast metadata.

``DatasetMixin`` is a persistence protocol: any class that implements it can be round-tripped through ``to_parquet`` / ``read_parquet`` and composed with arbitrary transformation functions via ``pipe``.

Because both are structural protocols rather than abstract base classes, you can satisfy them in your own classes without inheriting from OpenSTEF types—useful when integrating external data sources.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the primary concrete class. It wraps a ``pd.DataFrame`` and validates that the index is a monotonically increasing ``DatetimeIndex`` with a uniform sample interval.

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset

    df = pd.DataFrame(
        {"load": [1.0, 2.0, 3.0], "temperature": [10.0, 11.0, 12.0]},
        index=pd.date_range("2024-01-01", periods=3, freq="15min", tz="UTC"),
    )
    ds = TimeSeriesDataset(data=df)

    print(ds.sample_interval)   # 0:15:00
    print(ds.feature_names)     # ['load', 'temperature']

Datasets can be saved and reloaded without losing metadata:

.. code-block:: python

    ds.to_parquet("my_dataset.parquet")
    ds_loaded = TimeSeriesDataset.read_parquet("my_dataset.parquet")

The ``pipe`` method lets you chain transformations cleanly:

.. code-block:: python

    def add_lag(dataset: TimeSeriesDataset, col: str) -> TimeSeriesDataset:
        df = dataset.data.copy()
        df[f"{col}_lag1"] = df[col].shift(1)
        return TimeSeriesDataset(data=df)

    ds_with_lag = ds.pipe(add_lag, col="load")

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` tracks *when* each data point became available. This is essential for realistic backtesting: weather forecasts issued on Monday should not be visible to a model that is simulating a run from Sunday.

The class is composed from multiple ``TimeSeriesDataset`` parts and materialised into a concrete ``TimeSeriesDataset`` by calling ``select_version``, which filters each part to only the rows that were available at the requested point in time.

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeriesDataset

    load_ds = VersionedTimeSeriesDataset.read_parquet("load_measurements/grid_a.parquet")
    weather_ds = VersionedTimeSeriesDataset.read_parquet("weather_forecasts/grid_a.parquet")
    epex_ds = VersionedTimeSeriesDataset.read_parquet("EPEX.parquet")

    # Combine with a left join so all load timestamps are retained
    combined = VersionedTimeSeriesDataset.concat(
        [load_ds, weather_ds, epex_ds],
        mode="left",
    )

    # Materialise: only data available at the current wall-clock time
    snapshot: TimeSeriesDataset = combined.select_version()

    print(snapshot.data.shape)

The ``mode`` argument mirrors pandas join semantics: ``"left"`` keeps all timestamps from the first dataset, ``"inner"`` keeps only the intersection, and ``"outer"`` keeps the union.

.. note::

    ``VersionedTimeSeriesDataset`` is the recommended input format for backtesting pipelines in ``openstef_beam``. See the :doc:`beam` page for how it is consumed there.

Validated Datasets
^^^^^^^^^^^^^^^^^^

Four specialised subclasses of ``TimeSeriesDataset`` add domain-specific invariants. They are used as typed contracts between pipeline stages so that errors surface at dataset construction rather than deep inside a model.

**ForecastInputDataset** requires a named target column and optionally a ``forecast_start`` timestamp. It exposes ``target_series``, ``input_data`` (features without the target), and ``create_forecast_range`` for building the prediction index.

.. code-block:: python

    from openstef_core.datasets import ForecastInputDataset

    # Promote a generic dataset to a typed input dataset
    input_ds = ForecastInputDataset.from_timeseries(
        snapshot,
        target_column="load",
        forecast_start=pd.Timestamp("2024-06-01 00:00", tz="UTC"),
    )

    features = input_ds.input_data()          # DataFrame without 'load'
    target   = input_ds.target_series         # pd.Series of 'load'

**ForecastDataset** holds probabilistic forecasts. Columns are named after ``Quantile`` values (see `Domain Types`_ below), and the dataset validates that a median column is present. It exposes ``median_series`` and ``target_series`` (when actuals are included alongside forecasts).

**EnergyComponentDataset** constrains columns to valid ``EnergyComponentType`` members (solar, wind, etc.) and is the output type of component-splitting models in ``openstef_models``.

**EnsembleForecastDataset** stores forecasts from multiple ensemble members. Member columns are separated by the ``__`` delimiter and the class provides utilities for aggregating across members.

Domain Types
------------

``openstef_core.types`` provides typed wrappers for the primitive values that appear throughout the forecasting pipeline. Using these types instead of raw floats or strings makes serialisation, validation, and comparison consistent across packages.

LeadTime
^^^^^^^^

``LeadTime`` is a ``timedelta`` subclass that serialises to and from ISO 8601 duration strings (e.g. ``"PT1H"`` for one hour). It is used wherever a forecast horizon is expressed.

.. code-block:: python

    from openstef_core.types import LeadTime
    from datetime import timedelta

    h1 = LeadTime(timedelta(hours=1))
    h24 = LeadTime.from_string("PT24H")

    print(h1 < h24)          # True
    print(str(h1))            # PT1H

Quantile
^^^^^^^^

``Quantile`` is a ``float`` subclass restricted to ``[0, 1]``. It formats itself as a string for use in column names and can round-trip through ``parse``.

.. code-block:: python

    from openstef_core.types import Quantile

    q = Quantile(0.5)
    print(q.format())                    # "0.50"
    print(q.complementary())             # Quantile(0.5)  — symmetric around 0.5

    q10 = Quantile.from_percentile(10)
    print(q10.complementary().format())  # "0.90"

AvailableAt
^^^^^^^^^^^

``AvailableAt`` represents a data-availability offset in ``DnTHHMM[tz]`` format. It encodes the delay between when a measurement is taken and when it appears in a data feed—for example, ``"D0T0600"`` means the data for a given day is available at 06:00 on the same day. Calling ``apply`` or ``apply_index`` shifts a reference timestamp by the encoded offset.

.. code-block:: python

    from openstef_core.types import AvailableAt
    from datetime import datetime, timezone

    offset = AvailableAt.from_string("D0T0600")
    ref = datetime(2024, 6, 1, tzinfo=timezone.utc)
    print(offset.apply(ref))   # 2024-06-01 06:00:00+00:00

EnergyComponentType
^^^^^^^^^^^^^^^^^^^

``EnergyComponentType`` is a ``StrEnum`` whose members name the energy components that OpenSTEF can model (solar, wind, and so on). It is used as the column namespace in ``EnergyComponentDataset`` and as configuration in component-splitting models.

.. code-block:: python

    from openstef_core.types import EnergyComponentType

    print(list(EnergyComponentType))   # [<EnergyComponentType.solar: 'solar'>, ...]

Base Classes and Interfaces
---------------------------

Beyond datasets, ``openstef_core`` defines the abstract interfaces that models and pipelines implement. The ``openstef_core.mixins`` module provides ``Predictor`` and ``TransformPipeline``, which are generic over their input and output dataset types. ``ComponentSplitter`` in ``openstef_models``, for instance, is declared as ``Predictor[TimeSeriesDataset, EnergyComponentDataset]``, making the contract explicit at the type level.

``openstef_core.base_model`` provides ``BaseModel`` and ``BaseConfig``—thin Pydantic wrappers that all configuration and result objects in OpenSTEF inherit from. This ensures that every configuration class can be serialised to JSON and validated on construction.

How Core Underpins the Other Packages
--------------------------------------

Every OpenSTEF package imports from ``openstef_core`` but never the reverse. The dependency flows in one direction:

- **openstef_models** implements ``Predictor`` and ``TransformPipeline`` using ``ForecastInputDataset`` → ``ForecastDataset`` as its typed interface. See :doc:`models` for details.
- **openstef_beam** consumes ``VersionedTimeSeriesDataset`` for backtesting and produces ``ForecastDataset`` results. See :doc:`beam` for the pipeline architecture.
- **openstef_meta** orchestrates ensemble models whose outputs are typed as ``EnsembleForecastDataset``. See :doc:`meta` for how ensemble forecasting is structured.

This layering means that any code written against ``openstef_core`` types is automatically compatible with all higher-level packages. If you are building a custom model or data connector, implementing the ``TimeSeriesMixin`` / ``DatasetMixin`` protocols and returning the appropriate validated dataset type is all that is needed to plug into the rest of the library.