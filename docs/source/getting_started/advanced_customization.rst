Advanced Customization
======================

OpenSTEF is designed around composable building blocks—transforms, pipelines, forecasters, and callbacks—that you can extend and recombine to fit your specific forecasting needs. This page walks through the main extension points and shows how to build custom data preparation steps, feature engineering transforms, and complete pipeline workflows.

If you haven't yet run a basic forecast, start with the :doc:`quickstart` or :doc:`first_forecast` tutorials before diving into customization.

.. contents:: On this page
   :local:
   :depth: 2


The Transform Interface
-----------------------

The ``Transform`` class is the fundamental building block for all data processing in OpenSTEF. Every preprocessing step, feature engineering operation, and postprocessing step implements the same interface:

.. code-block:: python

   from openstef_core.transforms import Transform

   class Transform[I, O]:
       def fit(self, data: I) -> None:
           """Learn parameters from data."""
           ...

       def transform(self, data: I) -> O:
           """Apply the transformation."""
           ...

       def fit_transform(self, data: I) -> O:
           """Fit and transform in one step."""
           ...

       @property
       def is_fitted(self) -> bool:
           """Whether this transform has been fitted."""
           ...

This consistent interface means that every custom component you write plugs directly into OpenSTEF's pipelines without any adapter code.


Writing a Custom Transform
--------------------------

To create your own feature engineering step, subclass ``BaseConfig`` (for Pydantic configuration support) and the appropriate transform type. For time series data, use ``TimeSeriesTransform``:

.. code-block:: python

   from typing import override
   from pydantic import Field
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform


   class TemperatureSquaredAdder(BaseConfig, TimeSeriesTransform):
       """Adds a squared temperature feature to capture non-linear effects."""

       source_column: str = Field(default="temperature")
       output_column: str = Field(default="temperature_squared")

       @property
       @override
       def is_fitted(self) -> bool:
           return True  # Stateless transform, always ready

       @override
       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # Nothing to learn

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           df[self.output_column] = df[self.source_column] ** 2
           return TimeSeriesDataset(
               data=df,
               sample_interval=data.sample_interval,
           )

Key points:

- Stateless transforms (like adding a derived column) can return ``True`` from ``is_fitted`` immediately.
- Stateful transforms (like a scaler that learns mean/std) should track their fitted state and raise ``NotFittedError`` if ``transform`` is called before ``fit``.
- Always return a **new** dataset instance rather than mutating the input.


Composing Transforms with TransformPipeline
--------------------------------------------

Individual transforms are composed into a ``TransformPipeline``, which applies them sequentially. Each transform receives the output of the previous one:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   preprocessing = TransformPipeline[TimeSeriesDataset](
       transforms=[
           LagsAdder(
               source_column="load",
               trivial_lags=True,
           ),
           TemperatureSquaredAdder(
               source_column="temperature",
           ),
       ]
   )

   # Fit and transform training data
   processed_train = preprocessing.fit_transform(data=train_data)

   # Transform validation data (using learned parameters)
   processed_val = preprocessing.transform(data=val_data)

The pipeline handles fitting correctly: during ``fit``, each transform is fitted on the intermediate output of all preceding transforms, ensuring that downstream transforms see the data shape they'll encounter at prediction time.

An empty pipeline (``transforms=[]``) acts as a no-op, passing data through unchanged.


Building a Custom Forecasting Pipeline
---------------------------------------

The ``ForecastingModel`` class ties together preprocessing, a forecaster, and postprocessing into a complete pipeline:

.. code-block:: python

   from openstef_models.models.forecasting import ForecastingModel
   from openstef_core.transforms import TransformPipeline
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   model = ForecastingModel(
       preprocessing=TransformPipeline[TimeSeriesDataset](
           transforms=[
               LagsAdder(source_column="load", trivial_lags=True),
               TemperatureSquaredAdder(),
           ]
       ),
       forecaster=my_forecaster,
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=14,  # Days to discard due to lag NaNs
   )

.. warning::

   The ``cutoff_history`` parameter is critical when using lag-based features. For example, a 14-day lag transform creates NaN values for the first 14 days of data. You must set ``cutoff_history`` manually to exclude these incomplete rows from training, since lags cannot be automatically inferred from the transforms.


Workflow Orchestration with Callbacks
-------------------------------------

For production use, wrap your ``ForecastingModel`` in a ``CustomForecastingWorkflow`` to add lifecycle callbacks for logging, model storage, and experiment tracking:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )
   from openstef_models.mixins.callbacks import WorkflowContext


   class MetricsLogger(ForecastingCallback):
       """Custom callback that logs training metrics."""

       def on_fit_end(self, context: WorkflowContext, result) -> None:
           print(f"Training complete. Metrics: {result.metrics}")

       def on_predict_start(self, context: WorkflowContext, data) -> None:
           print(f"Starting prediction on {len(data.data)} rows")


   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_custom_model",
       callbacks=[MetricsLogger()],
   )

   # Train
   result = workflow.fit(data=train_dataset, data_val=val_dataset)

   # Predict
   forecasts = workflow.predict(data=test_dataset)

The callback interface provides four hooks:

- ``on_fit_start`` — called before model training begins
- ``on_fit_end`` — called after training completes successfully
- ``on_predict_start`` — called before prediction generation
- ``on_predict_end`` — called after predictions are generated

OpenSTEF includes a built-in ``MLFlowStorageCallback`` that handles model versioning, selection, and reuse through MLflow. You can combine it with your own callbacks:

.. code-block:: python

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="production_solar_v2",
       callbacks=[
           MLFlowStorageCallback(
               storage=my_mlflow_storage,
               model_reuse_enable=True,
               model_selection_enable=True,
               model_selection_metric="mae",
           ),
           MetricsLogger(),
       ],
   )


Built-in Transforms
--------------------

OpenSTEF ships with several transform families you can use directly or as reference for your own:

**Time-domain transforms:**

- ``LagsAdder`` — creates lagged features from the target variable using trivial lags, custom lags, or autocorrelation-based lag selection
- ``VersionedLagsAdder`` — lag features that respect data availability constraints in versioned datasets

**Validation transforms:**

- ``CompletenessChecker`` — validates that input data meets minimum completeness thresholds before processing

**Postprocessing transforms:**

- ``ConfidenceIntervalApplicator`` — adds quantile-based confidence intervals to forecasts

These transforms all follow the same ``Transform`` interface, so you can freely mix built-in and custom transforms in any pipeline.


Extension Patterns Summary
--------------------------

.. note:: [DIAGRAM: Extension points in the OpenSTEF pipeline — showing Transform, TransformPipeline, ForecastingModel (with preprocessing/forecaster/postprocessing slots), and CustomForecastingWorkflow (with callback hooks)]

The main extension points, from most to least common:

1. **Custom transforms** — add new feature engineering or data validation steps by implementing the ``Transform`` interface
2. **Custom pipelines** — compose transforms into preprocessing and postprocessing pipelines via ``TransformPipeline``
3. **Custom callbacks** — add logging, storage, or monitoring by implementing ``ForecastingCallback``
4. **Custom forecasters** — implement a new forecasting algorithm (see the API reference for the forecaster interface)

Each layer builds on the one below it, so you can customize at exactly the level you need without rewriting the rest of the stack.


Next Steps
----------

- :doc:`backtesting` — learn how to systematically compare different model configurations
- :doc:`first_forecast` — review the basics if any concepts here were unfamiliar