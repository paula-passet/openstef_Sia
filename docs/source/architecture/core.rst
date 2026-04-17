The ``openstef_core`` Package
==============================

The ``openstef_core`` package is the foundational layer of the OpenSTEF library. Every other package — ``openstef_models``, ``openstef_beam``, and ``openstef_meta`` — builds on top of it. This page covers the three pillars that ``openstef_core`` provides: a validated dataset hierarchy for representing time series data at every stage of the forecasting pipeline, a set of domain types that enforce correctness at the type level, and a mixin system that defines reusable behavioural contracts for models and transforms.

.. note::

   [DIAGRAM: Class hierarchy showing TimeSeriesMixin and DatasetMixin as shared protocol base interfaces; TimeSeriesDataset and VersionedTimeSeriesDataset as siblings both implementing those protocols; ForecastInputDataset, ForecastDataset, EnergyComponentDataset, and EnsembleForecastDataset as concrete subclasses of TimeSeriesDataset]


Dataset Hierarchy
-----------------

The dataset hierarchy is designed around a single principle: data quality problems should be caught as early as possible, at the boundary where data enters a pipeline stage. Rather than passing raw ``pd.DataFrame`` objects between components, OpenSTEF wraps them in typed dataset classes that validate structure and invariants on construction.

All dataset classes share two protocol interfaces defined in ``openstef_core.datasets.mixins``:

- **TimeSeriesMixin** — guarantees that a dataset exposes a sorted, consistently-sampled ``DatetimeIndex``, provides access to feature metadata, and supports temporal filtering and horizon restriction.
- **DatasetMixin** — guarantees persistence operations: ``read_parquet`` and ``to_parquet``.

These protocols are not base classes in the inheritance sense; they are ``Protocol`` definitions used for static type checking. The concrete inheritance tree starts at ``TimeSeriesDataset``.


TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the root concrete class. It wraps a ``pd.DataFrame`` with a ``DatetimeIndex``, enforces a consistent ``sample_interval``, and exposes utilities for feature selection, horizon restriction, and pandas interoperability.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.DataFrame(
       {"load": [100.0, 102.0, 98.0, 105.0]},
       index=pd.date_range("2024-01-01", periods=4, freq="15min"),
   )

   dataset = TimeSeriesDataset(df, sample_interval=timedelta(minutes=15))

   print(dataset.feature_names)   # Index(['load'], dtype='object')
   print(dataset.sample_interval) # 0:15:00

The ``pipe_pandas`` method lets you apply arbitrary DataFrame transformations while keeping the result wrapped in the same dataset type — a pattern that avoids accidentally dropping the validated wrapper mid-pipeline:

.. code-block:: python

   cleaned = dataset.pipe_pandas(lambda df: df.dropna())


VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` is a sibling of ``TimeSeriesDataset`` (both implement the shared protocols) rather than a subclass. It models the reality that in operational forecasting, different data sources become available at different times. Each row carries an ``available_at`` timestamp recording when that observation was actually accessible.

This makes ``VersionedTimeSeriesDataset`` the correct structure for realistic backtesting: you can materialise a view of the data as it would have looked at any historical point in time by calling ``select_version()``.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   load_ds = VersionedTimeSeriesDataset.read_parquet("load_measurements/site_a.parquet")
   weather_ds = VersionedTimeSeriesDataset.read_parquet("weather_forecasts/site_a.parquet")

   # Combine sources with a left join on the load timestamps
   combined = VersionedTimeSeriesDataset.concat(
       [load_ds, weather_ds],
       mode="left",
   )

   # Materialise the dataset as seen at a specific point in time
   snapshot = combined.select_version()

   print(snapshot.data.shape)

The ``select_version()`` call converts the lazy versioned representation into a concrete ``TimeSeriesDataset``, which can then be passed to any downstream component that expects that type.

.. note::

   ``VersionedTimeSeriesDataset`` is the recommended input format when constructing training datasets for backtesting pipelines. See the :doc:`beam` page for how the pipeline layer uses versioned datasets to drive realistic training runs.


Validated Specialisations
^^^^^^^^^^^^^^^^^^^^^^^^^

Four classes extend ``TimeSeriesDataset`` with domain-specific column validation. They are all importable from ``openstef_core.datasets``.

**ForecastInputDataset** represents data entering the forecasting stage. It requires a designated target column and optionally records a ``forecast_start`` timestamp. Convenience properties ``target_series`` and ``input_data()`` cleanly separate the label from the features.

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset, TimeSeriesDataset

   # Promote a generic dataset to a ForecastInputDataset
   forecast_input = ForecastInputDataset.from_timeseries(
       snapshot,
       target_column="load",
       forecast_start=pd.Timestamp("2024-03-01"),
   )

   features = forecast_input.input_data()   # DataFrame without the target column
   target   = forecast_input.target_series  # pd.Series of the load column

**ForecastDataset** represents the output of a single probabilistic forecaster. It stores quantile estimates as columns and exposes ``median_series``, ``quantiles_data``, and ``filter_quantiles()`` for downstream consumers.

**EnsembleForecastDataset** is the intermediate format produced when multiple base forecasters have each generated a ``ForecastDataset``. The column naming convention encodes both the forecaster name and the quantile, separated by ``__``. The class method ``from_forecast_datasets()`` assembles this structure from a dictionary of named ``ForecastDataset`` objects.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import EnsembleForecastDataset

   # datasets is a dict[str, ForecastDataset] keyed by forecaster name
   ensemble_ds = EnsembleForecastDataset.from_forecast_datasets(
       datasets,
       target_series=forecast_input.target_series,
   )

   learner_names, quantiles = ensemble_ds.get_learner_and_quantile(
       ensemble_ds.data.columns
   )

**EnergyComponentDataset** validates that all columns required by ``EnergyComponentType`` (wind, solar, other) are present. It is the output type of component-splitting models in ``openstef_models``.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.validated_datasets import EnergyComponentDataset

   component_df = pd.DataFrame(
       {
           "wind":  [50.0, 60.0],
           "solar": [30.0, 40.0],
           "other": [20.0, 25.0],
       },
       index=pd.date_range("2024-01-01", periods=2, freq="h"),
   )

   energy_ds = EnergyComponentDataset(component_df, timedelta(hours=1))
   print(energy_ds.feature_names)  # Index(['wind', 'solar', 'other'], ...)


Domain Types
------------

``openstef_core.types`` provides typed wrappers for the primitive values that appear throughout the forecasting domain. Using these types instead of bare ``float`` or ``timedelta`` values means that serialisation, validation, and comparison behaviour is consistent everywhere in the library.

**LeadTime** wraps ``timedelta`` and serialises to ISO 8601 duration strings. It supports Pydantic schema generation, making it safe to use in configuration classes.

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta

   horizon = LeadTime(timedelta(hours=24))
   print(str(horizon))          # e.g. "P0DT24H0M0S"

   parsed = LeadTime.from_string("P0DT48H0M0S")
   print(parsed.total_seconds() / 3600)  # 48.0

**Quantile** is a ``float`` subclass constrained to ``[0, 1]``. It provides ``format()``, ``parse()``, ``from_percentile()``, and ``complementary()`` helpers, and integrates with Pydantic validation.

.. code-block:: python

   from openstef_core.types import Quantile

   q = Quantile(0.9)
   print(q.complementary())          # Quantile(0.1)
   print(q.to_percentile())          # 90.0
   print(Quantile.from_percentile(50.0))  # Quantile(0.5)

**AvailableAt** encodes the availability offset of a data source — the delay between when a measurement is taken and when it becomes accessible. It serialises to a compact ``DnTHHMM[tz]`` string format and can be applied to a ``datetime`` or a whole ``DatetimeIndex``.

.. code-block:: python

   from openstef_core.types import AvailableAt
   from datetime import datetime, timezone

   offset = AvailableAt.from_string("D0T0015")
   reference = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)
   print(offset.apply(reference))  # 2024-03-01 12:15:00+00:00

**EnergyComponentType** is a ``StrEnum`` enumerating the recognised energy generation components (``wind``, ``solar``, ``other``). It is used both as a column validator in ``EnergyComponentDataset`` and as a configuration field in component-splitting models.

.. code-block:: python

   from openstef_core.types import EnergyComponentType

   for component in EnergyComponentType:
       print(component.value)
   # wind
   # solar
   # other


The Mixin System
----------------

``openstef_core.mixins`` defines the behavioural contracts that model classes across the library implement. These are abstract base classes (not protocols), so they participate in the inheritance tree and enforce method signatures at class definition time.

The four exports from ``openstef_core.mixins`` are:

- **Stateful** — base for any object that has a fitted/unfitted lifecycle. Exposes ``is_fitted``.
- **Predictor[I, O]** — extends ``Stateful`` with ``fit(data: I)``, ``predict(data: I) -> O``, and the convenience ``fit_predict()``. The generic parameters bind the input and output dataset types, making the contract explicit in the type system.
- **BatchPredictor[I, O]** — extends ``Predictor`` with ``predict_batch(data: list[I]) -> BatchResult[O]`` for vectorised inference over multiple inputs.
- **Transform** and **TransformPipeline** — for composable, stateless data transformations.

The ``Predictor`` generic is the key integration point between ``openstef_core`` and the rest of the library. For example, a component-splitting model in ``openstef_models`` is typed as ``Predictor[TimeSeriesDataset, EnergyComponentDataset]``, making the data flow self-documenting:

.. code-block:: python

   from openstef_core.mixins import Predictor
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.datasets.validated_datasets import EnergyComponentDataset

   class MyComponentSplitter(Predictor[TimeSeriesDataset, EnergyComponentDataset]):
       def fit(self, data: TimeSeriesDataset, data_val=None):
           # training logic
           ...

       def predict(self, data: TimeSeriesDataset) -> EnergyComponentDataset:
           # inference logic
           ...

``HyperParams`` (also in ``openstef_core.mixins``) is a Pydantic ``BaseModel`` subclass intended as the base for all model configuration classes. Pairing a ``Predictor`` subclass with a ``HyperParams`` subclass is the standard pattern used throughout ``openstef_models``.

.. note::

   The mixin system is intentionally minimal. ``openstef_core`` defines the contracts; ``openstef_models`` provides the concrete implementations. See :doc:`models` for the full catalogue of available model classes.


How Core Underpins the Rest of the Library
------------------------------------------

The dependency graph flows in one direction: ``openstef_core`` has no dependencies on other OpenSTEF packages. Everything else depends on it.

- **openstef_models** imports ``Predictor``, ``Transform``, ``HyperParams``, and all dataset types to implement concrete forecasting and component-splitting models.
- **openstef_beam** imports the dataset types as the inputs and outputs of its Apache Beam pipeline stages, and uses ``VersionedTimeSeriesDataset`` to drive backtesting. See :doc:`beam` for details.
- **openstef_meta** imports ``EnsembleForecastDataset`` as the exchange format between base learners and the meta-learner. See :doc:`meta` for how ensemble stacking is implemented on top of these types.

This layering means that any code written against the ``openstef_core`` types and mixins is automatically compatible with the full pipeline stack, without needing to import the higher-level packages.