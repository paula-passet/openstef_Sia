Advanced Customization
======================

This page is for users who have already produced a basic forecast (see :doc:`first_forecast`) and want to move beyond the defaults. It covers the three main extension points in OpenSTEF: customising the feature engineering pipeline, assembling a bespoke ``ForecastingModel``, and wiring everything together with a custom workflow.

.. note::

   All examples on this page assume you have OpenSTEF installed. If not, see :doc:`installation`.


Extension Points at a Glance
-----------------------------

OpenSTEF is built around three composable layers that you can replace or extend independently:

- **Preprocessing / feature engineering** – a ``TransformPipeline`` applied to raw ``TimeSeriesDataset`` objects before the model sees them.
- **Forecaster** – the core estimator (e.g. a gradient-boosted tree, a constant-median baseline, or your own implementation).
- **Postprocessing** – a second ``TransformPipeline`` applied to ``ForecastDataset`` objects after prediction, used for things like quantile calibration or confidence-interval attachment.

These three pieces are assembled into a ``ForecastingModel``, which is then handed to a ``CustomForecastingWorkflow`` that manages training, evaluation, and storage.

.. note:: [DIAGRAM: Three-layer pipeline – TimeSeriesDataset → TransformPipeline (preprocessing) → Forecaster → TransformPipeline (postprocessing) → ForecastDataset]


Custom Feature Engineering
---------------------------

The preprocessing pipeline is a ``TransformPipeline[TimeSeriesDataset]``. Each step in the pipeline is a transform object that implements ``fit`` and ``transform`` (following the familiar scikit-learn convention). OpenSTEF ships a rich set of ready-made transforms under ``openstef_models.transforms``, organised into sub-packages:

- ``openstef_models.transforms.time_domain`` – lag features, rolling statistics, calendar indicators
- ``openstef_models.transforms.weather_domain`` – weather-derived features
- ``openstef_models.transforms.energy_domain`` – domain-specific energy features
- ``openstef_models.transforms.general`` – scaling, imputation, and other general-purpose steps
- ``openstef_models.transforms.validation`` – data quality checks

The example below builds a preprocessing pipeline that adds Dutch public-holiday flags, a set of lag features, and standard scaling:

.. code-block:: python

   from openstef_models.transforms import time_domain, general
   from openstef_models.pipeline import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           time_domain.HolidayFeatures(country="NL"),
           time_domain.LagFeatures(lags=["1d", "2d", "7d"]),
           general.StandardScaler(),
       ]
   )

Because ``TransformPipeline`` is generic, the type checker will catch you if you accidentally mix transforms that operate on different dataset types.

Writing a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^

If the built-in transforms do not cover your needs, subclass the base ``Transform`` class and implement ``fit`` and ``transform``:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.base import Transform

   class PeakHourIndicator(Transform[TimeSeriesDataset]):
       """Adds a binary column that is 1 during morning and evening peak hours."""

       def fit(self, data: TimeSeriesDataset) -> None:
           # Nothing to learn from the data for this stateless transform.
           pass

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           hour = data.data.index.hour
           data.data["is_peak_hour"] = ((hour >= 7) & (hour <= 9)) | (
               (hour >= 17) & (hour <= 19)
           )
           return data

Drop ``PeakHourIndicator()`` into any ``TransformPipeline`` alongside the built-in transforms – no further wiring is required.

.. note::

   Stateful transforms (e.g. a scaler that learns mean and variance) must store their learned parameters in ``fit`` and apply them in ``transform``. The pipeline calls ``fit_transform`` on training data and ``transform`` only on validation and test data, so the split is handled for you.


Assembling a Custom ForecastingModel
--------------------------------------

``ForecastingModel`` is the central object that binds preprocessing, a forecaster, and postprocessing together. You construct it explicitly when the preset workflows do not match your requirements:

.. code-block:: python

   from datetime import timedelta

   from openstef_models.forecasting_model import ForecastingModel
   from openstef_models.pipeline import TransformPipeline
   from openstef_models.transforms import time_domain, general
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       IsotonicQuantileCalibrator,
       QuantileSorter,
   )
   from openstef_models.forecasters import GradientBoostingForecaster

   QUANTILES = [0.05, 0.25, 0.50, 0.75, 0.95]

   preprocessing = TransformPipeline(
       transforms=[
           time_domain.HolidayFeatures(country="NL"),
           time_domain.LagFeatures(lags=["1d", "7d"]),
           general.StandardScaler(),
       ]
   )

   forecaster = GradientBoostingForecaster()

   postprocessing = TransformPipeline(
       transforms=[
           IsotonicQuantileCalibrator(quantiles=QUANTILES),
           QuantileSorter(),
           ConfidenceIntervalApplicator(
               quantiles=QUANTILES,
               add_quantiles_from_std=False,
           ),
       ]
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
       postprocessing=postprocessing,
       target_column="load",
       cutoff_history=timedelta(days=14),
   )

The ``cutoff_history`` parameter controls how much historical data is retained when the model is serialised – useful for keeping storage footprints small in production.

Choosing a Postprocessing Stack
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The three postprocessing transforms shown above are the standard production stack:

- ``IsotonicQuantileCalibrator`` – corrects systematic quantile bias using isotonic regression.
- ``QuantileSorter`` – enforces monotonicity across quantile levels (prevents quantile crossing).
- ``ConfidenceIntervalApplicator`` – attaches named confidence-interval columns to the output ``ForecastDataset``.

You can omit any of these or add your own postprocessing transform following the same pattern as the custom preprocessing transform above, but targeting ``ForecastDataset`` instead of ``TimeSeriesDataset``.


Custom Workflow Orchestration
------------------------------

``CustomForecastingWorkflow`` wraps a ``ForecastingModel`` and handles the train/predict lifecycle, model versioning, and optional callbacks (e.g. MLflow logging). Constructing one directly gives you full control:

.. code-block:: python

   from pathlib import Path

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.storage import LocalModelStorage

   # --- Data ---
   dataset: VersionedTimeSeriesDataset = create_synthetic_forecasting_dataset()

   # --- Storage ---
   storage = LocalModelStorage(base_path=Path("./models"))

   # --- Workflow ---
   workflow = CustomForecastingWorkflow(
       model=model,          # the ForecastingModel assembled above
       model_id="my_substation",
       run_name="experiment_01",
   )

   # Train
   workflow.train(data=dataset, model_storage=storage)

   # Forecast
   forecast = workflow.predict(data=dataset, model_storage=storage)

.. note:: [VISUALIZATION: Forecast output plot showing point forecast and confidence interval bands over a 48-hour horizon]

The workflow stores a versioned snapshot of the model after each successful training run. On the next call to ``predict``, it loads the latest version automatically. See :doc:`backtesting` for how to evaluate multiple historical versions of a model systematically.

Adding Callbacks
^^^^^^^^^^^^^^^^

Callbacks let you hook into the workflow without subclassing it. The most common use case is shipping metrics and artefacts to MLflow:

.. code-block:: python

   from openstef_models.callbacks import MLFlowStorageCallback
   from openstef_models.storage import MLFlowModelStorage

   mlflow_storage = MLFlowModelStorage(tracking_uri="http://localhost:5000")

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_substation",
       run_name="experiment_01",
       callbacks=[
           MLFlowStorageCallback(
               storage=mlflow_storage,
               model_reuse_enable=True,
               model_reuse_max_age=timedelta(days=7),
               model_selection_enable=True,
               model_selection_metric="mae",
           )
       ],
   )

When ``model_reuse_enable=True`` the workflow will skip retraining and reuse the stored model if it was trained within ``model_reuse_max_age`` and its evaluation metric has not degraded beyond the selection threshold.

.. note::

   Callbacks are purely additive – removing them does not change the model or forecast output, only what gets persisted or logged externally.


Putting It All Together
------------------------

The pattern for a fully customised pipeline is always the same three steps:

1. Build a ``TransformPipeline`` for preprocessing (and optionally postprocessing).
2. Wrap them with a forecaster into a ``ForecastingModel``.
3. Hand the model to a ``CustomForecastingWorkflow`` and call ``train`` / ``predict``.

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.forecasters import GradientBoostingForecaster
   from openstef_models.forecasting_model import ForecastingModel
   from openstef_models.pipeline import TransformPipeline
   from openstef_models.storage import LocalModelStorage
   from openstef_models.transforms import time_domain, general
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       IsotonicQuantileCalibrator,
       QuantileSorter,
   )
   from openstef_models.workflows import CustomForecastingWorkflow

   QUANTILES = [0.05, 0.25, 0.50, 0.75, 0.95]

   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=[
           time_domain.HolidayFeatures(country="NL"),
           time_domain.LagFeatures(lags=["1d", "7d"]),
           general.StandardScaler(),
       ]),
       forecaster=GradientBoostingForecaster(),
       postprocessing=TransformPipeline(transforms=[
           IsotonicQuantileCalibrator(quantiles=QUANTILES),
           QuantileSorter(),
           ConfidenceIntervalApplicator(quantiles=QUANTILES, add_quantiles_from_std=False),
       ]),
       target_column="load",
       cutoff_history=timedelta(days=14),
   )

   dataset: VersionedTimeSeriesDataset = create_synthetic_forecasting_dataset()
   storage = LocalModelStorage(base_path=Path("./models"))

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_substation",
       run_name="custom_run",
   )
   workflow.train(data=dataset, model_storage=storage)
   forecast = workflow.predict(data=dataset, model_storage=storage)
   print(forecast.data.head())

This is the same pattern used internally by the preset workflows – the presets simply fill in sensible defaults for common configurations. If a preset almost fits your use case, inspect its source to see which transforms and forecaster it selects, then copy and modify that configuration rather than starting from scratch.

For the next step, see :doc:`backtesting` to learn how to measure whether your customised pipeline actually improves forecast quality on historical data.