Advanced Customization
======================

This page is for power users who want to go beyond the defaults and tailor OpenSTEF's behaviour to their specific domain. It covers the three main extension points the library exposes: custom data preparation, custom feature engineering transforms, and custom pipeline and workflow assembly. If you haven't yet run your first forecast, start with :doc:`first_forecast` and return here when the built-in presets no longer meet your needs.

.. note::

   OpenSTEF is a library of composable components. Every layer described here
   can be replaced independently — you are not required to rewrite the whole
   stack to change one piece.

[DIAGRAM: Three-layer customization stack showing data preparation → feature engineering (TransformPipeline) → workflow assembly (CustomForecastingWorkflow), with arrows indicating where each extension point plugs in]


Understanding the Extension Points
-----------------------------------

OpenSTEF's forecasting stack is built from three composable layers:

- **Preprocessing** — a ``TransformPipeline`` of ``TimeSeriesTransform`` steps that turn raw input data into model-ready features.
- **Forecaster** — the core model (XGBoost, LightGBM, median, etc.) that produces quantile predictions.
- **Postprocessing** — a second ``TransformPipeline`` that refines raw model output into a ``ForecastDataset`` (e.g. sorting quantiles, applying confidence intervals).

These three layers are assembled into a ``ForecastingModel``, which is then wrapped by a ``CustomForecastingWorkflow`` that adds lifecycle callbacks, model storage, and run management. You can substitute or extend any of these layers without touching the others.


Custom Feature Engineering
---------------------------

The most common customization is adding domain-specific features to the preprocessing pipeline. OpenSTEF provides ``TimeSeriesTransform`` as the abstract base class for all feature transforms. Implementing it requires three things: an ``is_fitted`` property, a ``fit`` method (stateless transforms can leave this as a no-op), and a ``transform`` method that returns a new ``TimeSeriesDataset``.

The following example adds a rolling-mean smoothing feature to the target column:

.. code-block:: python

   from typing import override
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class RollingMeanAdder(TimeSeriesTransform):
       """Adds a rolling mean of the target column as an additional feature."""

       def __init__(self, window: int = 24, target_column: str = "load"):
           self.window = window
           self.target_column = target_column

       @property
       @override
       def is_fitted(self) -> bool:
           # Stateless transform — always ready
           return True

       @override
       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # Nothing to learn from training data

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           col = f"{self.target_column}_rolling_mean_{self.window}h"
           df[col] = df[self.target_column].rolling(self.window, min_periods=1).mean()
           return TimeSeriesDataset(df, data.sample_interval)

       @override
       def features_added(self) -> list[str]:
           return [f"{self.target_column}_rolling_mean_{self.window}h"]

For transforms that need to learn parameters from training data (e.g. a scaler that stores the training-set maximum), set ``is_fitted`` to return ``False`` until ``fit`` has been called and store the learned state on the instance.

OpenSTEF ships several ready-made transforms you can use directly or combine with your own:

- ``openstef_models.transforms.time_domain.LagsAdder`` — generates lag features for each forecast horizon.
- ``openstef_models.transforms.time_domain.HolidayFeatureAdder`` — adds binary holiday indicators per country.
- ``openstef_models.transforms.time_domain.DatetimeFeaturesAdder`` — encodes hour-of-day, day-of-week, and similar cyclical features.


Assembling a Custom Preprocessing Pipeline
--------------------------------------------

Individual transforms are composed into a ``TransformPipeline``. The pipeline applies transforms in order, fitting each one on the output of the previous step during training and applying the fitted transforms in sequence during prediction.

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   horizons = [timedelta(hours=h) for h in [1, 4, 24, 48]]

   preprocessing = TransformPipeline(
       transforms=[
           # Built-in: lag features for each forecast horizon
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               add_trivial_lags=True,
               target_column="load",
           ),
           # Built-in: public holiday indicators for the Netherlands
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           # Custom: rolling mean defined above
           RollingMeanAdder(window=24, target_column="load"),
       ]
   )

.. note::

   When using lag-based transforms, set ``cutoff_history`` on ``ForecastingModel``
   to match the longest lag window. This prevents rows with incomplete lag features
   from entering the training set.


Assembling a Custom ForecastingModel
--------------------------------------

Once you have a preprocessing pipeline, combine it with a forecaster and a postprocessing pipeline inside a ``ForecastingModel``:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.transforms import TransformPipeline
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.forecasters.xgboost_forecaster import XGBoostForecaster
   from openstef_models.transforms.postprocessing.quantile_sorter import QuantileSorter
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )
   from openstef_core.types import Q

   quantiles = [Q(0.1), Q(0.5), Q(0.9)]
   horizons = [timedelta(hours=h) for h in [1, 4, 24, 48]]

   model = ForecastingModel(
       preprocessing=preprocessing,  # TransformPipeline built above
       forecaster=XGBoostForecaster(
           quantiles=quantiles,
           horizons=horizons,
       ),
       postprocessing=TransformPipeline(
           transforms=[
               QuantileSorter(),
               ConfidenceIntervalApplicator(
                   quantiles=quantiles,
                   add_quantiles_from_std=False,
               ),
           ]
       ),
       target_column="load",
       cutoff_history=timedelta(days=14),  # matches longest lag window
   )

[DIAGRAM: ForecastingModel internal data flow: TimeSeriesDataset → preprocessing TransformPipeline → XGBoostForecaster → postprocessing TransformPipeline → ForecastDataset]

Swap ``XGBoostForecaster`` for any other forecaster (``LGBMForecaster``, ``MedianForecaster``, etc.) without changing anything else. The preprocessing and postprocessing pipelines are forecaster-agnostic.


Custom Workflow Assembly
-------------------------

``ForecastingModel`` handles the mathematical pipeline. ``CustomForecastingWorkflow`` wraps it with operational concerns: model persistence, lifecycle callbacks, and run naming. You construct a workflow by passing your model and any callbacks you need:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my-custom-forecast",
       run_name="experiment-rolling-mean",
   )

   # Training
   workflow.fit(training_dataset)

   # Prediction
   forecast = workflow.predict(prediction_dataset)

The workflow exposes ``fit`` and ``predict`` as its public API. Internally it delegates to ``ForecastingModel`` and fires any registered callbacks at the start and end of each phase.


Adding Lifecycle Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks let you inject logic at key points in the workflow without subclassing or modifying the core pipeline. Common uses include logging metrics, saving intermediate data for debugging, and integrating with experiment trackers.

Implement ``ForecastingCallback`` and override whichever hooks you need:

.. code-block:: python

   from typing import override
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_models.models.forecasting_model import ModelFitResult
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastDataset

   class MetricsLoggerCallback(ForecastingCallback):
       """Logs training metrics after each fit."""

       @override
       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           print(f"[{context.workflow.run_name}] fit complete — metrics: {result}")

       @override
       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: VersionedTimeSeriesDataset | TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           print(f"[{context.workflow.run_name}] forecast shape: {result.data.shape}")

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my-custom-forecast",
       run_name="experiment-rolling-mean",
       callbacks=[MetricsLoggerCallback()],
   )

Multiple callbacks can be registered simultaneously and are executed in list order. OpenSTEF ships a ``DataSaveCallback`` (from ``openstef_models.workflows``) that persists prepared training data and forecasts to Parquet files — useful for debugging feature pipelines without writing your own callback.


Custom Data Preparation
------------------------

Before data reaches the preprocessing pipeline it must be in a ``TimeSeriesDataset``. If your raw data comes from a non-standard source (a REST API, a proprietary historian, a CSV with irregular timestamps), you need to prepare it yourself before handing it to the workflow.

The key requirements for a valid ``TimeSeriesDataset`` are:

- A ``pd.DataFrame`` with a timezone-aware ``DatetimeIndex``.
- A consistent ``sample_interval`` (e.g. ``timedelta(minutes=15)``).
- A column matching ``target_column`` (default ``"load"``).

.. code-block:: python

   import pandas as pd
   from datetime import timedelta, timezone
   from openstef_core.datasets import TimeSeriesDataset

   # Load from any source — here a CSV is used as a stand-in
   raw = pd.read_csv("my_data.csv", index_col="timestamp", parse_dates=True)
   raw.index = raw.index.tz_localize(timezone.utc)

   # Resample to a uniform 15-minute grid, forward-filling short gaps
   raw = raw.resample("15min").mean().ffill(limit=4)

   dataset = TimeSeriesDataset(
       data=raw,
       sample_interval=timedelta(minutes=15),
   )

For production pipelines where data arrives in versioned snapshots (i.e. each row has a known availability timestamp), use ``VersionedTimeSeriesDataset`` instead. This enables realistic backtesting that respects data latency — see :doc:`backtesting` for details.

.. warning::

   Gaps longer than ``limit=4`` samples (one hour at 15-minute resolution) should
   be handled explicitly before creating the dataset. The ``Imputer`` transform
   inside the preprocessing pipeline is designed for small residual gaps only.


Putting It All Together
------------------------

The pattern for a fully custom pipeline is always the same sequence:

1. Prepare a ``TimeSeriesDataset`` from your data source.
2. Build a ``TransformPipeline`` from built-in and custom ``TimeSeriesTransform`` steps.
3. Combine it with a forecaster and postprocessing pipeline in a ``ForecastingModel``.
4. Wrap the model in a ``CustomForecastingWorkflow``, attaching any callbacks.
5. Call ``workflow.fit(training_data)`` and ``workflow.predict(prediction_data)``.

[DIAGRAM: End-to-end custom pipeline sequence: raw data source → TimeSeriesDataset → TransformPipeline (custom + built-in transforms) → ForecastingModel → CustomForecastingWorkflow (with callbacks) → ForecastDataset]

Each step is independently testable. You can call ``preprocessing.fit_transform(dataset)`` directly to inspect the features your pipeline produces before committing to a full training run. Similarly, you can call ``model.prepare_input(dataset)`` to see the exact DataFrame that reaches the forecaster.

For the next step — evaluating your custom pipeline on historical data — see :doc:`backtesting`.