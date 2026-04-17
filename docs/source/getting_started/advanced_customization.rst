Advanced Customization
======================

This page covers the main extension points in OpenSTEF for power users who need to go beyond the defaults. You will learn how to write custom data transforms, assemble bespoke preprocessing and postprocessing pipelines, and hook into the workflow lifecycle with callbacks. If you have not yet run a basic forecast, start with :doc:`first_forecast` first.

.. note::

   OpenSTEF is a library. Every component described here — transforms, pipelines, models, workflows — is a plain Python object you instantiate and compose. There is no configuration file format or CLI to learn; customization is done in code.


Extension Points at a Glance
-----------------------------

OpenSTEF's architecture is built around three composable layers:

- **Transforms** — stateless or stateful operations on a ``TimeSeriesDataset`` (feature engineering, cleaning, scaling, …).
- **Pipelines** — ordered sequences of transforms wrapped in a ``TransformPipeline``, used for preprocessing and postprocessing inside a ``ForecastingModel``.
- **Workflows** — ``CustomForecastingWorkflow`` orchestrates fit/predict and exposes a callback interface for cross-cutting concerns such as logging, model storage, and data export.

The diagram below shows how these layers relate.

.. note:: [DIAGRAM: Data flow from raw TimeSeriesDataset → preprocessing TransformPipeline → Forecaster → postprocessing TransformPipeline → ForecastDataset, all wrapped by CustomForecastingWorkflow with callback hooks at fit/predict boundaries.]

Custom Feature Engineering
--------------------------

The cleanest way to add domain-specific features is to implement ``TimeSeriesTransform``. A transform must:

1. Inherit from ``TimeSeriesTransform`` (and optionally ``BaseConfig`` for Pydantic-based configuration).
2. Implement ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset``.
3. Implement ``features_added() -> list[str]`` to declare the column names it produces.
4. Optionally override ``fit()`` if the transform needs to learn parameters from training data (e.g., computing a mean for imputation). Stateless transforms can skip this — the base class provides a no-op default.

The example below adds a simple rolling-mean feature for the target column:

.. code-block:: python

   from datetime import timedelta
   from typing import override

   import pandas as pd
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform
   from pydantic import Field


   class RollingMeanAdder(BaseConfig, TimeSeriesTransform):
       """Add a rolling mean of the target column as a feature."""

       window: timedelta = Field(default=timedelta(hours=24))
       target_column: str = Field(default="load")

       @override
       def features_added(self) -> list[str]:
           hours = int(self.window.total_seconds() / 3600)
           return [f"{self.target_column}_rolling_mean_{hours}h"]

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           hours = int(self.window.total_seconds() / 3600)
           feature_name = f"{self.target_column}_rolling_mean_{hours}h"
           freq = data.sample_interval
           window_steps = int(self.window / freq)
           rolled = (
               data.data[self.target_column]
               .shift(1)  # avoid look-ahead
               .rolling(window_steps, min_periods=1)
               .mean()
           )
           new_data = data.data.copy()
           new_data[feature_name] = rolled
           return TimeSeriesDataset(new_data, data.sample_interval)

Because ``RollingMeanAdder`` inherits from ``BaseConfig``, its fields are validated by Pydantic and it can be serialised alongside the rest of the model configuration.

OpenSTEF ships a rich set of ready-made transforms you can use directly or as reference implementations:

- ``openstef_models.transforms.time_domain`` — ``HolidayFeatureAdder``, ``LagsAdder``, ``DatetimeFeaturesAdder``
- ``openstef_models.transforms.general`` — ``Scaler``, ``Imputer``, ``NaNDropper``, ``OutlierHandler``, ``Selector``, ``Shifter``
- ``openstef_models.transforms.weather_domain`` and ``openstef_models.transforms.energy_domain`` — domain-specific features

Assembling a Custom Preprocessing Pipeline
-------------------------------------------

Transforms are composed into a ``TransformPipeline`` and passed to ``ForecastingModel`` as its ``preprocessing`` argument. The pipeline calls each transform's ``fit`` and ``transform`` methods in order during training, and only ``transform`` during prediction.

.. code-block:: python

   from datetime import timedelta

   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.transforms.general.imputer import Imputer
   from openstef_models.transforms.general.scaler import Scaler
   from openstef_models.transforms.general.nan_dropper import NaNDropper
   from openstef_models.transforms.time_domain.holiday_features_adder import (
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_core.pipeline import TransformPipeline

   # Build the preprocessing pipeline
   preprocessing = TransformPipeline(
       transforms=[
           Imputer(),                                    # fill gaps before feature creation
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(lags=[timedelta(hours=24), timedelta(hours=48)]),
           RollingMeanAdder(window=timedelta(hours=24)), # our custom transform
           Scaler(),
           NaNDropper(),                                 # remove rows with NaN after lags
       ]
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=ConstantMedianForecaster(),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=timedelta(days=2),  # exclude rows made NaN by 48-hour lags
   )

.. note::

   Always set ``cutoff_history`` on ``ForecastingModel`` to match the longest lag in your preprocessing pipeline. A 48-hour lag makes the first 48 hours of training data unusable; without ``cutoff_history=timedelta(hours=48)`` those NaN rows will be passed to the forecaster.

The ``cutoff_history`` parameter is your responsibility — OpenSTEF cannot infer it automatically because the relationship between a transform and the rows it invalidates depends on your specific configuration.


Custom Postprocessing
---------------------

Postprocessing transforms operate on a ``ForecastDataset`` (the model's raw output) rather than a ``TimeSeriesDataset``. The pattern is identical: implement ``transform``, declare ``features_added``, and pass a ``TransformPipeline`` as the ``postprocessing`` argument to ``ForecastingModel``.

OpenSTEF provides two commonly needed postprocessors out of the box:

- ``openstef_models.transforms.forecasting.quantile_sorter.QuantileSorter`` — ensures quantile forecasts are monotonically ordered.
- ``openstef_models.transforms.forecasting.confidence_interval_applicator.ConfidenceIntervalApplicator`` — derives confidence intervals from a standard deviation forecast.

For most use cases these two are sufficient. Add custom postprocessors when you need to apply business rules (e.g., clipping negative load values) or convert units after prediction.


Custom Workflow Callbacks
--------------------------

``CustomForecastingWorkflow`` exposes a callback interface that lets you inject logic at four lifecycle points without subclassing the workflow itself:

- ``on_fit_start`` / ``on_fit_end`` — called before and after model training.
- ``on_predict_start`` / ``on_predict_end`` — called before and after generating forecasts.

Implement a callback by subclassing ``ForecastingCallback``:

.. code-block:: python

   from typing import override

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )
   from openstef_models.models.forecasting_model import ModelFitResult
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastDataset
   from openstef_models.mixins.callbacks import WorkflowContext


   class MetricsLoggerCallback(ForecastingCallback):
       """Log training metrics after every fit."""

       @override
       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           result: ModelFitResult,
       ) -> None:
           metrics = result.metrics
           print(f"[{context.workflow.run_name}] fit complete — metrics: {metrics}")

       @override
       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: VersionedTimeSeriesDataset | TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           print(
               f"[{context.workflow.run_name}] forecast generated "
               f"from {result.forecast_start}"
           )

Pass one or more callbacks when constructing the workflow:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage
   from pathlib import Path

   workflow = CustomForecastingWorkflow(
       model=model,                          # ForecastingModel from earlier
       model_id="my_custom_model",
       run_name="production_run",
       callbacks=[MetricsLoggerCallback()],
       model_storage=LocalModelStorage(path=Path("./models")),
   )

   workflow.fit(training_data)
   forecast = workflow.predict(forecast_data)

Callbacks are executed in list order. You can mix built-in callbacks (such as ``MLFlowStorageCallback``) with your own:

.. code-block:: python

   from openstef_models.callbacks.mlflow_storage_callback import MLFlowStorageCallback

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_custom_model",
       callbacks=[
           MetricsLoggerCallback(),
           MLFlowStorageCallback(storage=mlflow_storage),
       ],
   )

Putting It All Together
------------------------

The full customization pattern — custom transform, custom pipeline, custom callback — composes naturally because every piece is a plain Python object:

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.pipeline import TransformPipeline
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.transforms.general.imputer import Imputer
   from openstef_models.transforms.general.nan_dropper import NaNDropper
   from openstef_models.transforms.general.scaler import Scaler
   from openstef_models.transforms.time_domain.holiday_features_adder import (
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.storage.local_model_storage import LocalModelStorage

   # 1. Preprocessing: built-in + custom transforms
   preprocessing = TransformPipeline(
       transforms=[
           Imputer(),
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(lags=[timedelta(hours=24), timedelta(hours=48)]),
           RollingMeanAdder(window=timedelta(hours=24)),
           Scaler(),
           NaNDropper(),
       ]
   )

   # 2. Model
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=ConstantMedianForecaster(),
       postprocessing=TransformPipeline(transforms=[]),
       target_column="load",
       cutoff_history=timedelta(hours=48),
   )

   # 3. Workflow with callback
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="custom_demo",
       run_name="demo",
       callbacks=[MetricsLoggerCallback()],
       model_storage=LocalModelStorage(path=Path("./models")),
   )

   # 4. Train and forecast
   workflow.fit(training_data)
   forecast = workflow.predict(forecast_data)


Next Steps
----------

- :doc:`backtesting` — evaluate your custom pipeline against historical data to measure the impact of your changes.
- :doc:`first_forecast` — revisit the step-by-step tutorial if you want a refresher on how ``TimeSeriesDataset`` and ``ForecastDataset`` are constructed.
- :doc:`quickstart` — a minimal working example useful as a starting template before adding customizations.