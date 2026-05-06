Advanced Customization
======================

This page is for users who have already run their first forecast (see :doc:`first_forecast`) and want to go beyond the defaults. It covers the three main extension points in OpenSTEF: writing custom transforms for feature engineering, assembling those transforms into a preprocessing pipeline, and wiring everything together into a custom forecasting workflow.

.. note::

   If you are new to OpenSTEF, start with :doc:`quickstart` before reading this page. The patterns here assume familiarity with the core concepts introduced in :doc:`first_forecast`.

Extension Points Overview
--------------------------

OpenSTEF is built around three composable layers that you can replace or extend independently:

- **Transforms** — stateless or stateful operations on a ``TimeSeriesDataset`` (feature engineering, scaling, outlier handling, lag creation, …).
- **TransformPipeline** — an ordered sequence of transforms applied during ``fit`` and ``predict``.
- **CustomForecastingWorkflow** — the top-level object that ties together a model, a preprocessing pipeline, model storage, and the train/predict loop.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Custom Feature Transforms
--------------------------

Every built-in transform in OpenSTEF (``WindPowerFeatureAdder``, ``OutlierHandler``, ``SampleWeighter``, etc.) implements the same ``TimeSeriesTransform`` interface from ``openstef_core``. You can write your own by subclassing it.

The contract is minimal:

- ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` — required; applies the transformation.
- ``fit(data: TimeSeriesDataset) -> None`` — optional; learns parameters from training data. The default implementation is a no-op, so stateless transforms only need ``transform``.
- ``is_fitted -> bool`` — property; returns ``True`` by default for stateless transforms.
- ``features_added() -> list[str]`` — returns the names of any new columns added to the dataset.

Stateless transform example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A transform that adds a ``load_per_mw`` normalisation column requires no fitting:

.. code-block:: python

   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class LoadNormaliser(TimeSeriesTransform):
       """Normalise load by installed capacity."""

       def __init__(self, capacity_mw: float) -> None:
           self.capacity_mw = capacity_mw

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df["load_per_mw"] = df["load"] / self.capacity_mw
           return TimeSeriesDataset(df, data.sample_interval)

       def features_added(self) -> list[str]:
           return ["load_per_mw"]

Stateful transform example
^^^^^^^^^^^^^^^^^^^^^^^^^^^

A transform that clips outliers to a range learned from training data needs ``fit``:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class PercentileClipper(TimeSeriesTransform):
       """Clip a column to the [low_pct, high_pct] percentile range seen during fit."""

       def __init__(self, column: str, low_pct: float = 1.0, high_pct: float = 99.0) -> None:
           self.column = column
           self.low_pct = low_pct
           self.high_pct = high_pct
           self._lower: float | None = None
           self._upper: float | None = None

       @property
       def is_fitted(self) -> bool:
           return self._lower is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           series = data.data[self.column]
           self._lower = series.quantile(self.low_pct / 100)
           self._upper = series.quantile(self.high_pct / 100)

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df[self.column] = df[self.column].clip(self._lower, self._upper)
           return TimeSeriesDataset(df, data.sample_interval)

       def features_added(self) -> list[str]:
           return []

.. note::

   ``fit`` is called only during training. During inference, ``transform`` is called directly on the fitted instance. OpenSTEF serialises fitted transforms alongside the model, so learned parameters survive across restarts.

Assembling a Custom Preprocessing Pipeline
-------------------------------------------

A ``TransformPipeline`` chains transforms in order. Each transform receives the output of the previous one. During ``fit``, each transform is fitted and then immediately applied before the next transform is fitted — so later transforms see already-processed data.

.. code-block:: python

   from openstef_models.transforms.general.nan_dropper import NaNDropper
   from openstef_models.transforms.general.outlier_handler import OutlierHandler
   from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder
   from openstef_core.transforms.transform_pipeline import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           NaNDropper(),
           PercentileClipper(column="wind_speed", low_pct=0.5, high_pct=99.5),
           WindPowerFeatureAdder(),
           LoadNormaliser(capacity_mw=150.0),
       ]
   )

The pipeline exposes the same ``fit`` / ``transform`` / ``fit_transform`` interface as individual transforms, so it can be dropped in anywhere a single transform is expected.

Custom Forecasting Workflow
----------------------------

The ``CustomForecastingWorkflow`` is the top-level orchestrator. It wraps a ``ForecastingModel`` (which itself contains a preprocessing pipeline, a predictor, and a postprocessing pipeline) together with model storage and the train/predict loop.

The quickest way to build a custom workflow is through ``ForecastingWorkflowConfig`` and ``create_forecasting_workflow``, which accept your custom pipeline objects:

.. code-block:: python

   from pathlib import Path
   from datetime import timedelta

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_models.transforms.general.holiday_feature_adder import HolidayFeatureAdder
   from openstef_models.transforms.general.lag_feature_adder import LagFeatureAdder
   from openstef_core.transforms.transform_pipeline import TransformPipeline
   from openstef_models.model.local_model_storage import LocalModelStorage

   preprocessing = TransformPipeline(
       transforms=[
           NaNDropper(),
           PercentileClipper(column="load", low_pct=1.0, high_pct=99.0),
           HolidayFeatureAdder(country="NL"),
           LagFeatureAdder(lags=[timedelta(hours=1), timedelta(days=1), timedelta(days=7)]),
       ]
   )

   config = ForecastingWorkflowConfig(
       location=LocationConfig(name="substation_42", region="NL"),
       preprocessing=preprocessing,
       model_dir=Path("/models/substation_42"),
   )

   workflow = create_forecasting_workflow(config)

Once you have a workflow, the train and predict calls are identical to the preset examples shown in :doc:`first_forecast`:

.. code-block:: python

   # Training
   workflow.train(training_data)

   # Inference
   forecast = workflow.predict(forecast_data)

.. note:: [VISUALIZATION: Side-by-side plots of raw load signal and the same signal after the custom PercentileClipper and LagFeatureAdder transforms, showing the effect of each preprocessing step]

Custom Data Preparation
------------------------

OpenSTEF expects data as a ``TimeSeriesDataset`` (or ``VersionedTimeSeriesDataset`` for backtesting). If your source data arrives in a different shape — a database query result, a CSV with irregular timestamps, or a multi-site DataFrame — you need to prepare it before handing it to the workflow.

The recommended pattern is to write a thin adapter function that produces a ``TimeSeriesDataset``:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from datetime import timedelta


   def load_from_csv(path: str, resample_interval: timedelta = timedelta(minutes=15)) -> TimeSeriesDataset:
       df = pd.read_csv(path, parse_dates=["timestamp"], index_col="timestamp")

       # Enforce a uniform frequency — required by TimeSeriesDataset
       df = df.resample(resample_interval).mean()

       # Rename site-specific columns to the names your transforms expect
       df = df.rename(columns={"P_measured_kW": "load", "ws_10m": "wind_speed"})

       return TimeSeriesDataset(df, sample_interval=resample_interval)

Keep data preparation logic outside your transforms. Transforms should assume they receive a well-formed ``TimeSeriesDataset``; adapters handle the messiness of real-world sources.

Postprocessing
---------------

The same ``TransformPipeline`` pattern applies to postprocessing. A postprocessing pipeline receives the model's raw output (a ``ForecastDataset``) and can apply corrections such as clipping negative values, re-scaling to physical units, or smoothing:

.. code-block:: python

   from openstef_models.transforms.postprocessing.non_negative_clipper import NonNegativeClipper
   from openstef_core.transforms.transform_pipeline import TransformPipeline

   postprocessing = TransformPipeline(
       transforms=[
           NonNegativeClipper(),   # generation assets cannot produce negative power
       ]
   )

Pass ``postprocessing`` alongside ``preprocessing`` when constructing ``ForecastingWorkflowConfig``.

Putting It All Together
------------------------

A complete custom setup — data adapter, preprocessing pipeline, postprocessing pipeline, and workflow — looks like this:

.. code-block:: python

   from pathlib import Path
   from datetime import timedelta

   from openstef_core.transforms.transform_pipeline import TransformPipeline
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_models.transforms.general.nan_dropper import NaNDropper
   from openstef_models.transforms.general.holiday_feature_adder import HolidayFeatureAdder
   from openstef_models.transforms.general.lag_feature_adder import LagFeatureAdder
   from openstef_models.transforms.postprocessing.non_negative_clipper import NonNegativeClipper

   # --- Data ---
   training_data = load_from_csv("data/substation_42_train.csv")
   forecast_data = load_from_csv("data/substation_42_forecast.csv")

   # --- Preprocessing ---
   preprocessing = TransformPipeline(
       transforms=[
           NaNDropper(),
           PercentileClipper(column="load", low_pct=1.0, high_pct=99.0),
           HolidayFeatureAdder(country="NL"),
           LagFeatureAdder(lags=[timedelta(hours=1), timedelta(days=1), timedelta(days=7)]),
           LoadNormaliser(capacity_mw=150.0),
       ]
   )

   # --- Postprocessing ---
   postprocessing = TransformPipeline(transforms=[NonNegativeClipper()])

   # --- Workflow ---
   config = ForecastingWorkflowConfig(
       location=LocationConfig(name="substation_42", region="NL"),
       preprocessing=preprocessing,
       postprocessing=postprocessing,
       model_dir=Path("/models/substation_42"),
   )
   workflow = create_forecasting_workflow(config)

   # --- Train and predict ---
   workflow.train(training_data)
   forecast = workflow.predict(forecast_data)

.. note::

   Once trained, the workflow (including all fitted transform parameters) can be persisted and reloaded via the ``LocalModelStorage`` configured in ``ForecastingWorkflowConfig``. See :doc:`first_forecast` for details on model storage.

Next Steps
-----------

- To evaluate your custom workflow on historical data, see :doc:`backtesting`.
- For installation of optional dependencies (e.g. GPU-accelerated models), see :doc:`installation`.
- Built-in transforms are documented in the API reference under ``openstef_models.transforms``.