Advanced Customization
======================

OpenSTEF is designed to be extended. While the built-in presets and configuration-driven workflows cover the majority of use cases, the library exposes a set of well-defined extension points that let you plug in custom logic at every stage of the forecasting pipeline — from data preparation and feature engineering through to post-prediction callbacks. This page walks through the three main customization patterns: building custom transforms, assembling custom pipelines, and hooking into workflow lifecycle events.

If you haven't yet run a basic forecast, start with :doc:`first_forecast` before reading this page. For comparing customized models against baselines, see :doc:`backtesting`.

.. note::
   .. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd


Custom Transforms and Feature Engineering
------------------------------------------

The fundamental building block for data preparation in OpenSTEF is the ``Transform`` abstract class. Any object that implements ``fit`` and ``transform`` can participate in a pipeline. This makes it straightforward to add domain-specific features — for example, a custom lag feature derived from a SCADA system, or a weather-derived variable not covered by the built-in adders.

To create a custom transform, subclass ``Transform`` from ``openstef_core`` and implement the two required methods:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms import Transform


   class PeakHourIndicator(Transform[TimeSeriesDataset, TimeSeriesDataset]):
       """Adds a binary column indicating morning and evening peak hours."""

       _is_fitted: bool = False

       @property
       def is_fitted(self) -> bool:
           return self._is_fitted

       def fit(self, data: TimeSeriesDataset) -> None:
           # This transform has no learnable parameters, so fit is a no-op.
           self._is_fitted = True

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           hour = df.index.hour
           df["is_peak_hour"] = ((hour >= 7) & (hour <= 9)) | (
               (hour >= 17) & (hour <= 19)
           )
           return data.with_data(df)

A few conventions to keep in mind:

- ``fit`` should learn any parameters from the training data (e.g., mean values for normalisation). For stateless transforms, it simply sets ``_is_fitted = True``.
- ``transform`` must return a new dataset instance rather than mutating the input in place. Use the dataset's ``with_data`` helper to wrap a modified DataFrame.
- Both methods receive a ``TimeSeriesDataset``, not a raw ``pandas.DataFrame``. Access the underlying frame via ``data.data``.


Assembling a Custom TransformPipeline
---------------------------------------

Individual transforms become useful when composed into a ``TransformPipeline``. The pipeline applies transforms sequentially, passing the output of each step as the input to the next. It also handles fitting correctly: each transform is fitted on the intermediate output of all preceding transforms, so normalisation steps see already-cleaned data.

.. code-block:: python

   from openstef_models.transforms import TransformPipeline
   from openstef_models.transforms import (
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )

   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           PeakHourIndicator(),                          # custom transform from above
           HolidayFeatureAdder(country_code="NL"),       # built-in holiday flags
           DatetimeFeaturesAdder(onehot_encode=False),   # built-in datetime features
       ]
   )

   # Fit on training data, then transform held-out data
   preprocessing.fit(train_dataset)
   transformed_train = preprocessing.transform(train_dataset)
   transformed_val = preprocessing.transform(val_dataset)

The pipeline is serialisable via pickle, which means it can be stored alongside a trained model and reloaded for inference without re-fitting.

.. note::
   The order of transforms matters. Place data-quality checks and outlier removal before feature adders, and feature adders before any normalisation or selection steps. This mirrors the ordering used in the built-in ``create_forecasting_workflow`` preset.


Building a Custom Forecasting Workflow
----------------------------------------

For full control over the training and prediction process, you can construct a ``CustomForecastingWorkflow`` directly rather than using the configuration-driven ``create_forecasting_workflow`` preset. This is the right approach when you need a non-standard pipeline structure — for example, different preprocessing for different model components, or a custom combiner in an ensemble.

The workflow object ties together a ``ForecastingModel`` (or ``EnsembleForecastingModel``) with optional callbacks and a run name for experiment tracking:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig
   from datetime import timedelta

   # Build a workflow from a config as a starting point, then customise
   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model="xgboost",
       sample_interval=timedelta(minutes=15),
   )
   workflow = create_forecasting_workflow(config)

   # Swap the preprocessing pipeline for one that includes your custom transform
   from openstef_models.transforms import TransformPipeline
   workflow.model.preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           PeakHourIndicator(),
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(onehot_encode=False),
       ]
   )

   # Train and predict as normal
   workflow.fit(train_dataset, data_val=val_dataset)
   forecasts = workflow.predict(predict_dataset)

If you need to build the workflow entirely from scratch — for instance, to wire up a custom model class — pass the model and any callbacks directly to the constructor:

.. code-block:: python

   workflow = CustomForecastingWorkflow(
       model=my_custom_model,
       callbacks=[my_logging_callback],
       run_name="experiment-peak-hour-v1",
   )

The ``with_run_name`` method returns a deep copy of a workflow with a new run name, which is convenient when running multiple experiments from the same base configuration without risk of shared state:

.. code-block:: python

   baseline_workflow = create_forecasting_workflow(config)
   experiment_workflow = baseline_workflow.with_run_name("peak-hour-features")


Lifecycle Callbacks
--------------------

Callbacks are the cleanest way to add cross-cutting concerns — logging, metrics, model persistence, alerting — without modifying the core workflow logic. ``CustomForecastingWorkflow`` accepts a list of ``ForecastingCallback`` instances and calls them at four points in the lifecycle:

- ``on_fit_start`` — before training begins
- ``on_fit_end`` — after training completes, receives the ``ModelFitResult``
- ``on_predict_start`` — before prediction begins
- ``on_predict_end`` — after prediction completes, receives the ``ForecastDataset``

All hook methods have default no-op implementations, so you only override the events you care about:

.. code-block:: python

   import logging
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.workflows.custom_forecasting_workflow import ForecastingCallback
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_core.datasets import TimeSeriesDataset, ForecastDataset
   from openstef_models.models import ModelFitResult

   logger = logging.getLogger(__name__)


   class MetricsLoggingCallback(ForecastingCallback):
       """Logs training metrics and forecast statistics after each lifecycle event."""

       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           logger.info(
               "Training complete for run '%s'. Metrics: %s",
               context.workflow.run_name,
               result.metrics,
           )

       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           n_rows = len(result.data)
           logger.info("Generated %d forecast rows.", n_rows)


   # Attach the callback when constructing the workflow
   workflow = CustomForecastingWorkflow(
       model=my_model,
       callbacks=[MetricsLoggingCallback()],
   )

You can attach multiple callbacks; they are called in list order. A common pattern is to have one callback for logging, one for writing forecasts to a database, and one for sending alerts when prediction quality falls below a threshold.

.. note::
   The ``ComponentSplitCallback`` class provides the same four hooks for ``CustomComponentSplitWorkflow``, which handles the decomposition of total load into energy components (e.g., solar, wind, residual). The pattern is identical — subclass, override the hooks you need, and pass an instance to the workflow constructor.


Putting It All Together
------------------------

A realistic customisation typically combines all three patterns: a custom transform, a tailored pipeline, and a callback for observability. The sketch below shows how these pieces connect:

.. code-block:: python

   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_models.transforms import TransformPipeline
   from openstef_models.transforms import HolidayFeatureAdder, DatetimeFeaturesAdder
   from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig
   from datetime import timedelta

   # 1. Define custom transform
   peak_indicator = PeakHourIndicator()

   # 2. Build preprocessing pipeline
   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           peak_indicator,
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(onehot_encode=False),
       ]
   )

   # 3. Create workflow from config and inject custom pipeline
   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model="lgbm",
       sample_interval=timedelta(minutes=15),
   )
   workflow = create_forecasting_workflow(config)
   workflow.model.preprocessing = preprocessing

   # 4. Attach observability callback
   workflow = CustomForecastingWorkflow(
       model=workflow.model,
       callbacks=[MetricsLoggingCallback()],
       run_name="lgbm-peak-hour-features",
   )

   # 5. Train and forecast
   fit_result = workflow.fit(train_dataset, data_val=val_dataset)
   forecasts = workflow.predict(predict_dataset)

Once you have a customised workflow, use the backtesting utilities described in :doc:`backtesting` to measure whether your changes actually improve forecast quality before deploying them to production.