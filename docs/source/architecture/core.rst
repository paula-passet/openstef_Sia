The ``openstef_core`` Package
=============================

The ``openstef_core`` package is the foundation of the OpenSTEF library. It defines the validated data structures, domain types, and composable base classes that every other package builds on. Understanding ``openstef_core`` means understanding the shared language that flows through training pipelines, model definitions, and beam-based batch jobs alike.

This page covers the dataset hierarchy, the mixin system, and the domain types that give OpenSTEF its type-safety guarantees. For how models consume these structures, see :doc:`models`. For how pipelines orchestrate them at scale, see :doc:`beam`.

.. note:: [DIAGRAM: Class hierarchy showing TimeSeriesMixin and DatasetMixin as shared bases; TimeSeriesDataset and VersionedTimeSeriesDataset as siblings both inheriting from those mixins; ForecastInputDataset, ForecastDataset, EnergyComponentDataset, and EnsembleForecastDataset as subclasses of TimeSeriesDataset]

----

The Dataset Hierarchy
---------------------

All datasets in OpenSTEF descend from ``TimeSeriesDataset``, a validated wrapper around a ``pandas.DataFrame`` that enforces a sorted ``DatetimeIndex``, a consistent ``sample_interval``, and optional ``horizon`` and ``available_at`` columns. Rather than working with raw DataFrames throughout a pipeline, you work with objects that carry invariants — if construction succeeds, the data is already known to be well-formed.

``VersionedTimeSeriesDataset`` sits alongside ``TimeSeriesDataset`` as a sibling class. It represents *lazy* versioned data: each row carries an ``available_at`` timestamp recording when that value became known. This is the key primitive for realistic backtesting, where you must never allow a model to see data that would not yet have been available at the time of the forecast. Calling ``.select_version()`` on a ``VersionedTimeSeriesDataset`` materialises it into a concrete ``TimeSeriesDataset`` by selecting the most recent value available at each timestamp.

The four specialised datasets — ``ForecastInputDataset``, ``ForecastDataset``, ``EnergyComponentDataset``, and ``EnsembleForecastDataset`` — all extend ``TimeSeriesDataset`` and add domain-specific column validation. They represent distinct stages of the forecasting pipeline, and passing the wrong type to a function is caught at construction time rather than silently producing bad output.

TimeSeriesDataset
^^^^^^^^^^^^^^^^^

``TimeSeriesDataset`` is the everyday container for feature data and measurements. It accepts a DataFrame, validates the index, and exposes convenience properties such as ``feature_names``, ``horizons``, and ``is_versioned``.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   data = pd.DataFrame(
       {"load": [100.0, 120.0, 115.0, 130.0]},
       index=pd.date_range("2025-01-01", periods=4, freq="1h", name="timestamp"),
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))

   print(dataset.feature_names)   # ['load']
   print(dataset.is_versioned)    # False

VersionedTimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^

``VersionedTimeSeriesDataset`` is used wherever data arrives with a publication delay — weather forecasts, market prices, or metered load values that are only confirmed after settlement. Loading from Parquet and joining multiple sources is the typical entry point:

.. code-block:: python

   from pathlib import Path
   from openstef_core.datasets import VersionedTimeSeriesDataset

   local_dir = Path("data")
   target = "substation_A"

   load_ds = VersionedTimeSeriesDataset.read_parquet(
       local_dir / f"load_measurements/{target}.parquet"
   )
   weather_ds = VersionedTimeSeriesDataset.read_parquet(
       local_dir / f"weather_forecasts_versioned/{target}.parquet"
   )
   epex_ds = VersionedTimeSeriesDataset.read_parquet(local_dir / "EPEX.parquet")

   # Left join: keep all load timestamps, attach features where available
   combined = VersionedTimeSeriesDataset.concat(
       [load_ds, weather_ds, epex_ds],
       mode="left",
   )

   # Materialise into a concrete TimeSeriesDataset
   dataset = combined.select_version()
   print(f"Shape: {dataset.data.shape}")

The ``filter_by_available_before`` method lets you slice the versioned dataset to a specific point in time, which is how backtesting pipelines reconstruct the information set that existed at each historical forecast moment.

ForecastInputDataset
^^^^^^^^^^^^^^^^^^^^

``ForecastInputDataset`` wraps training and prediction data where a named target column must be present. It records ``target_column``, an optional ``sample_weight_column``, and a ``forecast_start`` timestamp. Validation at construction time ensures the target column exists before any model ever sees the data.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import timedelta, datetime
   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   data = pd.DataFrame(
       {
           "load": [100.0, 120.0, np.nan, 130.0],
           "temperature": [15.0, 14.5, 14.0, 13.5],
           "wind_speed": [3.2, 4.1, 5.0, 4.7],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="1h", name="timestamp"),
   )

   input_ds = ForecastInputDataset(
       data,
       sample_interval=timedelta(hours=1),
       target_column="load",
       forecast_start=datetime(2025, 1, 1, 2),
   )

   print(input_ds.target_column)   # 'load'
   print(input_ds.target_series)   # pd.Series of the load column

ForecastDataset
^^^^^^^^^^^^^^^

``ForecastDataset`` holds the output of a probabilistic forecaster. Its columns follow the quantile naming convention (e.g., ``quantile_P10``, ``quantile_P50``, ``quantile_P90``), and the class validates that all non-target columns conform to this pattern. It exposes ``quantiles``, ``median_series``, ``standard_deviation_series``, and ``quantiles_data`` as first-class properties.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import timedelta
   from openstef_core.datasets.validated_datasets import ForecastDataset

   forecast_data = pd.DataFrame(
       {
           "load": [100.0, np.nan],
           "quantile_P10": [90.0, 95.0],
           "quantile_P50": [100.0, 110.0],
           "quantile_P90": [115.0, 125.0],
       },
       index=pd.date_range("2025-01-01", periods=2, freq="1h", name="timestamp"),
   )

   forecast_ds = ForecastDataset(forecast_data, sample_interval=timedelta(hours=1))

   print(forecast_ds.quantiles)        # [0.1, 0.5, 0.9]
   print(forecast_ds.median_series)    # pd.Series of quantile_P50

.. note::
   [VISUALIZATION: Example forecast plot showing quantile_P10, quantile_P50, quantile_P90 bands over a 48-hour horizon with actuals overlaid]

EnsembleForecastDataset
^^^^^^^^^^^^^^^^^^^^^^^

``EnsembleForecastDataset`` is the intermediate format produced by the first stage of an ensemble model. Each base forecaster contributes columns named ``<forecaster_name>__<quantile>`` (the ``__`` separator is ``ENSEMBLE_COLUMN_SEP``). The ``get_learner_and_quantile`` class method parses these column names back into structured lists, and ``select_quantile`` projects the dataset into a ``ForecastInputDataset`` ready for the stacking layer.

EnergyComponentDataset
^^^^^^^^^^^^^^^^^^^^^^

``EnergyComponentDataset`` validates that all columns required by ``EnergyComponentType`` are present. This makes it the right container for decomposed generation data (solar, wind, load, etc.) where downstream consumers depend on a fixed schema.

----

Domain Types
------------

The ``openstef_core.types`` module provides typed wrappers for the primitive concepts that appear throughout the forecasting pipeline. Using these types instead of raw floats or strings means that serialisation, validation, and comparison behaviour is consistent everywhere.

LeadTime
^^^^^^^^

``LeadTime`` is a ``timedelta`` subclass with a canonical ``DnTHHMM[tz]`` string representation. It supports Pydantic serialisation and can be applied to a ``datetime`` or a ``DatetimeIndex`` to compute the corresponding availability timestamps.

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import datetime

   horizon = LeadTime.from_string("D0T1200")
   reference = datetime(2025, 6, 1, 0, 0)

   print(horizon.apply(reference))   # 2025-06-01 12:00:00

Quantile
^^^^^^^^

``Quantile`` is a ``float`` subclass constrained to ``[0, 1]``. It provides ``format()`` (producing strings like ``quantile_P50``), ``parse()``, ``from_percentile()``, and ``complementary()``. The ``ForecastDataset`` and ``EnsembleForecastDataset`` classes use ``Quantile`` throughout their column-naming logic.

.. code-block:: python

   from openstef_core.types import Quantile

   q = Quantile(0.9)
   print(q.format())           # 'quantile_P90'
   print(q.complementary())    # 0.1
   print(q.to_percentile())    # 90.0

AvailableAt
^^^^^^^^^^^

``AvailableAt`` encodes the offset between a reference timestamp and when a data value becomes available. It drives the ``filter_by_available_before`` logic in ``VersionedTimeSeriesDataset`` and is the type-safe way to express publication delays in pipeline configuration.

EnergyComponentType
^^^^^^^^^^^^^^^^^^^

``EnergyComponentType`` is a ``StrEnum`` that enumerates the recognised energy component column names. ``EnergyComponentDataset`` validates against this enum, ensuring that any code expecting decomposed generation data can rely on a stable schema.

----

The Mixin System
----------------

``openstef_core.mixins`` provides three composable abstractions that the rest of the library builds on. They are deliberately thin — they define *interfaces* and *patterns*, not implementations.

Stateful
^^^^^^^^

``Stateful`` is the base for any object that needs to serialise and restore its internal state. It defines a ``VersionedState`` protocol and is the foundation for both ``Transform`` and ``Predictor``. The ``openstef_models`` package uses ``Stateful`` to persist trained model weights; see :doc:`models` for details.

Transform and TransformPipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Transform`` is an abstract base for data preprocessing steps. It follows the familiar ``fit`` / ``transform`` / ``fit_transform`` pattern and is typed over input and output types. ``TransformPipeline`` composes a sequence of ``Transform`` instances, fitting and applying them in order. Because ``Transform`` extends ``Stateful``, a fitted pipeline can be serialised and reloaded without re-fitting.

.. code-block:: python

   from openstef_core.mixins import Transform, TransformPipeline

   # Concrete transforms are defined in openstef_models — see the models page.
   # TransformPipeline wires them together:
   #
   #   pipeline = TransformPipeline(transforms=[scaler, imputer, feature_selector])
   #   pipeline.fit(train_dataset)
   #   clean_dataset = pipeline.transform(raw_dataset)

Predictor and BatchPredictor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Predictor`` is the abstract interface for any model that can be fitted and used to generate predictions. It is generic over its input type ``I`` and output type ``O``, which in practice are ``ForecastInputDataset`` and ``ForecastDataset`` respectively. ``BatchPredictor`` extends this with a ``predict_batch`` method for processing lists of inputs — the interface that ``openstef_beam`` pipelines target when distributing work across workers.

``HyperParams`` is a Pydantic ``BaseModel`` subclass intended as the base for all model configuration objects, giving hyperparameter sets automatic validation and serialisation.

.. code-block:: python

   from openstef_core.mixins import Predictor, HyperParams

   class MyHyperParams(HyperParams):
       n_estimators: int = 100
       learning_rate: float = 0.05

   # Concrete Predictor implementations live in openstef_models.
   # The interface contract is:
   #   predictor.fit(train_data)          -> fitted state
   #   predictor.predict(input_data)      -> ForecastDataset
   #   predictor.fit_predict(train_data)  -> ForecastDataset

----

How Core Underpins the Rest of OpenSTEF
----------------------------------------

Every other package in OpenSTEF is a consumer of ``openstef_core`` abstractions:

- **openstef_models** implements ``Predictor`` and ``Transform`` to build concrete forecasting models and preprocessing pipelines. It relies on ``ForecastInputDataset`` as the training contract and returns ``ForecastDataset`` as output. See :doc:`models`.

- **openstef_beam** constructs Apache Beam pipelines that call ``BatchPredictor.predict_batch``, read ``VersionedTimeSeriesDataset`` from storage, and write ``ForecastDataset`` results. The domain types (``LeadTime``, ``Quantile``) appear in pipeline configuration throughout. See :doc:`beam`.

- **openstef_meta** builds ensemble forecasting on top of ``EnsembleForecastDataset`` and ``ForecastDataset``, using the ``ENSEMBLE_COLUMN_SEP`` convention to track which base forecaster produced each column. See :doc:`meta`.

This layering means that a change to column-naming conventions in ``Quantile.format()`` propagates consistently to model outputs, ensemble intermediates, and pipeline I/O without any package needing to re-implement the logic.