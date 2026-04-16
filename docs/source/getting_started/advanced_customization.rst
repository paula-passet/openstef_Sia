Advanced Customization
======================

This page covers the main extension points in OpenSTEF for power users who need to go beyond the defaults. You will learn how to write custom data transforms, assemble a bespoke preprocessing pipeline, plug in your own feature engineering, and hook into the workflow lifecycle with callbacks. The :doc:`quickstart` and :doc:`first_forecast` pages cover the standard path; come back here once you are ready to adapt the library to your own domain.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Understanding the Pipeline Architecture
----------------------------------------

OpenSTEF structures every forecasting run as a three-stage pipeline inside a ``ForecastingModel``:

1. **Preprocessing** — a ``TransformPipeline`` that cleans, validates, and enriches the raw ``TimeSeriesDataset`` before training or inference.
2. **Forecaster** — the model itself (e.g. ``XGBForecaster``, ``ConstantMedianForecaster``).
3. **Postprocessing** — a second ``TransformPipeline`` that operates on the resulting ``ForecastDataset`` (e.g. sorting quantiles, applying confidence intervals).

Each pipeline is just an ordered list of ``Transform`` objects, so you can insert, remove, or replace any step without touching the rest of the system.

Custom Data Transforms
-----------------------

All transforms share the same abstract interface defined in ``openstef_core``. Implement ``fit`` (optional, for stateful transforms) and ``transform``:

.. code-block:: python

   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class CapOutliersTransform(TimeSeriesTransform):
       """Clip extreme values in the target column to [lower, upper] quantiles."""

       def __init__(self, target_column: str, lower: float = 0.01, upper: float = 0.99):
           self.target_column = target_column
           self.lower = lower
           self.upper = upper
           self._lower_val: float | None = None
           self._upper_val: float | None = None

       @property
       def is_fitted(self) -> bool:
           return self._lower_val is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           series = data.data[self.target_column]
           self._lower_val = float(series.quantile(self.lower))
           self._upper_val = float(series.quantile(self.upper))

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           clipped = data.data.copy()
           clipped[self.target_column] = clipped[self.target_column].clip(
               self._lower_val, self._upper_val
           )
           return TimeSeriesDataset(data=clipped)

The ``fit`` / ``transform`` split mirrors the scikit-learn convention: ``fit`` is called once on training data and learns any parameters; ``transform`` is called on both training and inference data using those learned parameters. ``TransformPipeline`` handles the sequencing automatically — it calls ``fit_transform`` on each step during training and only ``transform`` during prediction.

.. note::

   For transforms that need no learned state (e.g. a simple column rename), you can leave ``fit`` as a no-op and set ``is_fitted`` to always return ``True``.

Assembling a Custom Preprocessing Pipeline
-------------------------------------------

Once you have your transforms, compose them into a ``TransformPipeline`` and pass it to ``ForecastingModel``:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_core.transforms.feature_transforms import (
       HolidayFeatureAdder,
       DatetimeFeaturesAdder,
       LagsAdder,
   )
   from openstef_core.transforms.checks import (
       FlatlineChecker,
       CompletenessChecker,
   )
   from openstef_core.types import Q, LeadTime
   from datetime import timedelta

   horizons = [LeadTime(timedelta(hours=h)) for h in range(1, 25)]

   preprocessing = TransformPipeline(
       transforms=[
           # --- data quality checks ---
           FlatlineChecker(load_column="load", flatliner_threshold=6, error_on_flatliner=False),
           CompletenessChecker(completeness_threshold=0.7),
           # --- your custom transform ---
           CapOutliersTransform(target_column="load"),
           # --- built-in feature engineering ---
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(onehot_encode=False),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               add_trivial_lags=True,
               target_column="load",
           ),
       ]
   )

The order matters: quality checks should run before feature adders so that bad data does not propagate into engineered features.

Custom Feature Engineering
---------------------------

OpenSTEF ships several domain-specific feature adders (lags, rolling aggregates, cyclic encodings, radiation-derived features, wind power features, etc.). For domain knowledge that is not covered by the built-ins, subclass ``TimeSeriesTransform`` as shown above and insert it anywhere in the pipeline.

A common pattern is to add external signals — for example, a custom temperature-to-heat-demand index:

.. code-block:: python

   import numpy as np
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset
   from openstef_core.transforms.dataset_transforms import TimeSeriesTransform


   class HeatDemandIndexTransform(TimeSeriesTransform):
       """Derive a heat demand proxy from outdoor temperature."""

       def __init__(self, temperature_column: str, base_temp: float = 18.0):
           self.temperature_column = temperature_column
           self.base_temp = base_temp

       @property
       def is_fitted(self) -> bool:
           return True  # stateless transform

       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # nothing to learn

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df["heat_demand_index"] = np.maximum(
               self.base_temp - df[self.temperature_column], 0.0
           )
           return TimeSeriesDataset(data=df)

Drop this into your ``TransformPipeline`` after the completeness check and before the lag adder so that lags of the new feature are also computed.

Building the Full ForecastingModel
------------------------------------

With preprocessing and postprocessing pipelines in hand, wire everything together into a ``ForecastingModel``:

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.forecasters import XGBForecaster
   from openstef_core.transforms import TransformPipeline
   from openstef_core.transforms.postprocessing import QuantileSorter, ConfidenceIntervalApplicator
   from openstef_core.types import Q

   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=preprocessing,          # the pipeline built above
       forecaster=XGBForecaster(
           horizons=horizons,
           quantiles=quantiles,
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
   )

Custom Workflow Callbacks
--------------------------

``CustomForecastingWorkflow`` exposes a callback system that lets you inject logic at key lifecycle points without subclassing the workflow itself. Implement ``ForecastingCallback`` and override whichever hooks you need:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.models.forecasting_model import ModelFitResult
   from openstef_core.datasets.validated_datasets import ForecastDataset
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback
   import logging

   logger = logging.getLogger(__name__)


   class MetricsLoggingCallback(ForecastingCallback):
       """Log evaluation metrics to stdout after every training run."""

       def on_fit_end(
           self,
           context: WorkflowContext,
           result: ModelFitResult,
       ) -> None:
           for metric_name, value in (result.metrics or {}).items():
               logger.info("  %s = %.4f", metric_name, value)

       def on_predict_end(
           self,
           context: WorkflowContext,
           result: ForecastDataset,
       ) -> None:
           logger.info("Forecast produced %d rows", len(result.data))

Attach callbacks when constructing the workflow:

.. code-block:: python

   from openstef_models.storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(base_path=Path("./models"))

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_custom_model",
       run_name="experiment_v1",
       callbacks=[MetricsLoggingCallback()],
   )

   # Train
   fit_result = workflow.fit(train_dataset)

   # Predict
   forecasts = workflow.predict(predict_dataset)

The callback hooks available include ``on_fit_start``, ``on_fit_end``, ``on_predict_start``, and ``on_predict_end``. This makes callbacks the right place for experiment tracking integrations, alerting, or custom validation logic — keeping that code cleanly separated from the model itself.

.. note::

   OpenSTEF ships an ``MLFlowStorageCallback`` that handles MLflow experiment tracking out of the box. Check the API reference before writing your own tracking callback.

Putting It All Together
------------------------

The pattern for a fully custom pipeline is always the same:

1. Define any custom ``TimeSeriesTransform`` subclasses.
2. Compose them with built-in transforms into a ``TransformPipeline``.
3. Pass preprocessing and postprocessing pipelines to ``ForecastingModel``.
4. Wrap the model in a ``CustomForecastingWorkflow``, attaching callbacks as needed.
5. Call ``workflow.fit(train_data)`` and ``workflow.predict(predict_data)``.

This layered design means you can customise any single layer — say, only the feature engineering — while keeping everything else at its default. You are never forced to rewrite the whole pipeline just to add one domain-specific feature.

.. note::

   If you need to compare the performance of your custom pipeline against a baseline, see :doc:`backtesting` for the recommended approach.

Related Pages
--------------

- :doc:`first_forecast` — step-by-step walkthrough of a standard forecast before customising anything.
- :doc:`backtesting` — evaluate whether your custom pipeline actually improves forecast quality.
- :doc:`quickstart` — minimal working example if you need a quick reference for the basic API.