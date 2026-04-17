Advanced Customization
======================

This page is for power users who want to go beyond the defaults and tailor OpenSTEF's behaviour to their specific domain. It covers the three main extension points the library exposes: custom data preparation through transforms, custom feature engineering pipelines, and custom workflow orchestration through callbacks. If you haven't yet run your first forecast, start with :doc:`first_forecast` before reading this page.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Overview of Extension Points
-----------------------------

OpenSTEF is built around a small set of composable abstractions. Understanding them makes customisation straightforward:

- **Transform / TransformPipeline** — stateful, chainable data transformations that handle everything from validation to feature engineering. You can write your own and slot them into any pipeline.
- **ForecastingModel** — combines a preprocessing ``TransformPipeline``, a forecaster, and a postprocessing ``TransformPipeline`` into a single trainable unit.
- **CustomForecastingWorkflow** — wraps a ``ForecastingModel`` with lifecycle callbacks, model storage, and run management. This is the top-level object you interact with in production.

Each layer is independently replaceable. You can swap only the feature engineering while keeping the rest of the stack intact, or you can attach callbacks for monitoring without touching the model at all.

Writing a Custom Transform
---------------------------

Every transform in OpenSTEF implements the ``Transform`` abstract base class from ``openstef_core``. The contract is minimal: implement ``is_fitted``, ``fit``, and ``transform``. The ``fit_transform`` convenience method is provided for free.

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import Transform

   class PeakNormaliser(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Normalise every column by the peak value seen during fitting."""

       def __init__(self) -> None:
           self._peak: float | None = None

       @property
       def is_fitted(self) -> bool:
           return self._peak is not None

       def fit(self, data: TimeSeriesDataset) -> None:
           self._peak = float(data.data.max().max())

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           if not self.is_fitted:
               raise RuntimeError("Call fit() before transform().")
           scaled = data.data / self._peak
           return TimeSeriesDataset(scaled, data.sample_interval)

A few conventions to keep in mind:

- ``fit`` must be idempotent with respect to the ``is_fitted`` flag — once fitted, calling ``fit`` again should not corrupt learned state.
- ``transform`` must return a *new* dataset object rather than mutating the input; the pipeline relies on this for correct sequential chaining.
- If your transform has no learnable parameters (e.g. a pure column selector), set ``is_fitted`` to always return ``True`` and leave ``fit`` as a no-op.

Composing Transforms into a Pipeline
--------------------------------------

``TransformPipeline`` applies a sequence of transforms in order, passing the output of each step as the input to the next. It is itself a ``Transform``, so pipelines can be nested.

.. code-block:: python

   from datetime import timedelta

   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=[timedelta(hours=h) for h in range(1, 25)],
               add_trivial_lags=True,
               target_column="load",
           ),
           PeakNormaliser(),   # the custom transform from above
       ]
   )

The pipeline is fitted once on training data and then applied to any number of prediction datasets without re-fitting:

.. code-block:: python

   # During training
   train_features = preprocessing.fit_transform(data=train_dataset)

   # During inference — uses the peak learned from training
   predict_features = preprocessing.transform(data=predict_dataset)

OpenSTEF ships a rich set of built-in transforms under ``openstef_models.transforms``, organised into sub-packages:

- ``openstef_models.transforms.time_domain`` — lag features, holiday indicators, datetime cyclical encodings
- ``openstef_models.transforms.weather_domain`` — radiation-derived features, wind power features, atmosphere-derived features
- ``openstef_models.transforms.energy_domain`` — energy-specific transformations
- ``openstef_models.transforms.general`` — generic utilities such as imputation, column selection, completeness checking, and flatliner detection

Browse these before writing a custom transform — the feature you need may already exist.

Assembling a Custom ForecastingModel
--------------------------------------

``ForecastingModel`` is the central object that ties preprocessing, a forecaster, and postprocessing together. You construct it explicitly when the built-in presets don't match your requirements.

.. code-block:: python

   from datetime import timedelta

   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_core.types import Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.general.quantile_sorter import QuantileSorter
   from openstef_models.forecasters.xgboost_forecaster import XGBoostForecaster

   horizons = [timedelta(hours=h) for h in range(1, 25)]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               add_trivial_lags=True,
               target_column="load",
           ),
       ]
   )

   postprocessing = TransformPipeline(
       transforms=[QuantileSorter()]
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=XGBoostForecaster(
           quantiles=quantiles,
           horizons=horizons,
       ),
       postprocessing=postprocessing,
       target_column="load",
   )

The separation of preprocessing and postprocessing is intentional. Preprocessing runs on the raw ``TimeSeriesDataset`` before the forecaster sees it; postprocessing runs on the raw ``ForecastDataset`` the forecaster produces. This keeps each stage focused and independently testable.

.. note::

   When you call ``model.fit()``, the preprocessing pipeline is fitted on the training data and then frozen. The same fitted pipeline is used at prediction time, so any statistics learned during training (e.g. scaling factors, imputation fill values) are automatically applied consistently.

Custom Workflow Orchestration with Callbacks
---------------------------------------------

``CustomForecastingWorkflow`` wraps a ``ForecastingModel`` and fires lifecycle hooks at four points: ``on_fit_start``, ``on_fit_end``, ``on_predict_start``, and ``on_predict_end``. Subclass ``ForecastingCallback`` and override only the hooks you care about — all methods have no-op defaults.

.. code-block:: python

   import logging

   from openstef_core.datasets import ForecastDataset, TimeSeriesDataset
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_models.models.forecasting_model import ModelFitResult
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )

   logger = logging.getLogger(__name__)

   class AuditCallback(ForecastingCallback):
       """Log training and prediction events for audit purposes."""

       def on_fit_start(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
       ) -> None:
           logger.info(
               "Training started — %d samples, columns: %s",
               len(data.data),
               list(data.data.columns),
           )

       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           logger.info("Training complete.")

       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           logger.info("Forecast generated — %d rows.", len(result.data))

Attach one or more callbacks when constructing the workflow:

.. code-block:: python

   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[AuditCallback()],
   )

   workflow.fit(data=train_dataset)
   forecast = workflow.predict(data=predict_dataset)

Multiple callbacks are executed in list order. You can mix built-in callbacks (such as ``MLFlowStorageCallback`` for experiment tracking) with your own:

.. code-block:: python

   from openstef_models.callbacks.mlflow_storage_callback import MLFlowStorageCallback

   workflow = CustomForecastingWorkflow(
       model=model,
       callbacks=[
           AuditCallback(),
           MLFlowStorageCallback(storage=mlflow_storage),
       ],
   )

Callbacks are the recommended way to add cross-cutting concerns — logging, alerting, metrics export, forecast persistence — without coupling that logic into the model itself.

Putting It All Together
------------------------

The pattern for a fully customised pipeline is always the same three steps:

1. Build a ``TransformPipeline`` for preprocessing (and optionally postprocessing).
2. Wrap it with a forecaster inside a ``ForecastingModel``.
3. Attach callbacks and hand the model to ``CustomForecastingWorkflow``.

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(
       model=ForecastingModel(
           preprocessing=preprocessing,
           forecaster=XGBoostForecaster(quantiles=quantiles, horizons=horizons),
           postprocessing=postprocessing,
           target_column="load",
       ),
       callbacks=[AuditCallback()],
   )

   # Train
   workflow.fit(data=train_dataset, data_val=val_dataset)

   # Predict
   forecast = workflow.predict(data=predict_dataset)

Because every component is a plain Python object, you can unit-test each layer in isolation — fit a ``TransformPipeline`` on a small synthetic dataset, assert on the output columns, and never involve the forecaster at all. This composability is one of the main design goals of the library.

.. note::

   For a working end-to-end example including synthetic data generation and model storage, see the ``configuring_model_pipeline_example`` in the ``examples/`` directory of the repository.

Next Steps
-----------

- :doc:`backtesting` — once you have a custom pipeline, use backtesting to measure whether your changes actually improve forecast accuracy.
- :doc:`first_forecast` — revisit the step-by-step tutorial if you want a refresher on the core data structures used above.
- :doc:`quickstart` — the minimal working example is a useful reference for the simplest possible pipeline configuration.