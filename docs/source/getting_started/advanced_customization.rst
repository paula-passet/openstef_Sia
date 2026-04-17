Advanced Customization
======================

This page is for power users who want to go beyond the defaults and tailor OpenSTEF to their specific forecasting problem. It covers the three main extension points the library exposes: custom data preparation, custom feature engineering transforms, and custom pipeline workflows. If you are new to OpenSTEF, work through :doc:`first_forecast` first — the concepts here build on that foundation.

**[DIAGRAM: Extension points in OpenSTEF — data preparation feeds into TransformPipeline (preprocessing), which feeds into ForecastingModel, which is orchestrated by CustomForecastingWorkflow with optional callbacks for storage and monitoring]**

.. note::

   All customization in OpenSTEF is done by composing library-provided building blocks or by subclassing well-defined abstract base classes. You never need to fork or monkey-patch the library itself.

Overview of Extension Points
-----------------------------

OpenSTEF structures a forecasting system in three composable layers:

- **Transforms** — stateless or stateful operations on a ``TimeSeriesDataset``. They are the atomic unit of feature engineering and data preparation.
- **TransformPipeline** — an ordered sequence of transforms applied as preprocessing or postprocessing inside a ``ForecastingModel``.
- **CustomForecastingWorkflow** — the top-level orchestrator that wraps a ``ForecastingModel``, manages model identity, and fires lifecycle callbacks for storage, logging, and monitoring.

Each layer can be customised independently. You can swap a single transform in an otherwise standard pipeline, or build an entirely bespoke workflow from scratch.

Custom Data Preparation
-----------------------

Data preparation in OpenSTEF is handled by the same ``TransformPipeline`` mechanism as feature engineering. The library ships several ready-made cleaning transforms in ``openstef_models.transforms.general``:

.. code-block:: python

   from openstef_models.transforms.general import (
       Imputer,
       OutlierHandler,
       NaNDropper,
       Scaler,
       Selector,
   )

A typical preprocessing pipeline that cleans raw input before any feature engineering looks like this:

.. code-block:: python

   from openstef_core.transforms import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           Selector(selection=["load", "temperature", "wind_speed"]),
           OutlierHandler(),
           Imputer(),
           Scaler(),
       ]
   )

``Selector`` restricts the dataset to only the columns your model needs. ``OutlierHandler`` clips extreme values, ``Imputer`` fills gaps, and ``Scaler`` normalises the range. These can be reordered or replaced as your data demands.

Writing a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^

When the built-in transforms do not cover your use case, you can implement your own by subclassing ``TimeSeriesTransform`` from ``openstef_core.transforms``. The interface mirrors scikit-learn: implement ``fit`` (optional, for stateful transforms) and ``transform`` (required). You must also implement ``features_added`` to declare which column names your transform introduces.

.. code-block:: python

   from typing import override
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform


   class PeakHourFlagTransform(BaseConfig, TimeSeriesTransform):
       """Adds a binary feature that flags morning and evening peak hours."""

       morning_start: int = 7
       morning_end: int = 9
       evening_start: int = 17
       evening_end: int = 20

       @override
       def features_added(self) -> list[str]:
           return ["is_peak_hour"]

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           hour = data.data.index.hour
           is_peak = (
               (hour >= self.morning_start) & (hour < self.morning_end)
               | (hour >= self.evening_start) & (hour < self.evening_end)
           ).astype(int)
           new_data = data.data.copy()
           new_data["is_peak_hour"] = is_peak
           return TimeSeriesDataset(new_data, data.sample_interval)

A few things to note:

- Inheriting from both ``BaseConfig`` and ``TimeSeriesTransform`` gives you Pydantic validation on constructor arguments for free.
- Stateless transforms (like this one) do not need to override ``fit`` — the base class provides a no-op implementation.
- For stateful transforms (e.g., a custom scaler that learns parameters from training data), override ``fit`` and store learned state as instance attributes.

Custom Feature Engineering
--------------------------

OpenSTEF provides a rich set of domain-specific feature adders out of the box. The most commonly used ones live in ``openstef_models.transforms.time_domain``:

.. code-block:: python

   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.time_domain.datetime_features_adder import DatetimeFeaturesAdder

``HolidayFeatureAdder`` adds binary columns for public holidays per country. ``LagsAdder`` generates lag features aligned to your forecast horizons. ``DatetimeFeaturesAdder`` extracts weekday, weekend, and other calendar features.

You compose these into a preprocessing pipeline that is passed directly to ``ForecastingModel``:

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.time_domain.datetime_features_adder import DatetimeFeaturesAdder

   feature_pipeline = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           DatetimeFeaturesAdder(onehot_encode=False),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=[timedelta(hours=h) for h in range(1, 25)],
               target_column="load",
           ),
       ]
   )

Your custom transforms slot into the same pipeline without any special registration:

.. code-block:: python

   feature_pipeline = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           DatetimeFeaturesAdder(onehot_encode=False),
           PeakHourFlagTransform(morning_start=7, evening_start=17),  # custom
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=[timedelta(hours=h) for h in range(1, 25)],
               target_column="load",
           ),
       ]
   )

Custom Pipeline Workflows
--------------------------

The ``CustomForecastingWorkflow`` class is the top-level orchestrator. It wraps a ``ForecastingModel`` (which itself contains your preprocessing and postprocessing pipelines) and adds model identity management and a callback system for lifecycle events.

Assembling a Full Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following example wires together all the pieces — custom preprocessing, feature engineering, a forecaster, and postprocessing — into a single runnable workflow:

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   import numpy as np
   import pandas as pd
   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.transforms.general import Imputer, NaNDropper, Scaler, Selector
   from openstef_models.transforms.time_domain.datetime_features_adder import DatetimeFeaturesAdder
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   logger = logging.getLogger(__name__)

   # --- Preprocessing: cleaning + feature engineering ---
   preprocessing = TransformPipeline(
       transforms=[
           Imputer(),
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           DatetimeFeaturesAdder(onehot_encode=False),
           PeakHourFlagTransform(),          # your custom transform
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=[timedelta(hours=h) for h in range(1, 25)],
               target_column="load",
           ),
           NaNDropper(),
       ]
   )

   # --- Postprocessing ---
   from openstef_models.transforms.general import Selector as PostSelector
   postprocessing = TransformPipeline(transforms=[])

   # --- Assemble the model ---
   from openstef_models.forecasters.constant_median import ConstantMedianForecaster

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=ConstantMedianForecaster(),
       postprocessing=postprocessing,
       target_column="load",
   )

   # --- Wrap in a workflow ---
   workflow = CustomForecastingWorkflow(
       model_id="my_custom_forecaster_v1",
       model=model,
   )

   # --- Train and predict ---
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

**[VISUALIZATION: Example forecast output showing predicted load curve with confidence intervals over a 24-hour horizon]**

Adding Lifecycle Callbacks
^^^^^^^^^^^^^^^^^^^^^^^^^^

Callbacks let you hook into the workflow at key stages — after fitting, before prediction, after prediction — without modifying the workflow itself. This is the recommended pattern for adding model persistence, experiment tracking, or custom validation.

The ``ForecastingCallback`` base class from ``openstef_models.workflows.custom_forecasting_workflow`` defines the interface:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
       ForecastingCallback,
   )
   from openstef_models.mixins.callbacks import WorkflowContext
   from openstef_core.datasets import TimeSeriesDataset, VersionedTimeSeriesDataset
   from openstef_core.datasets.validated_datasets import ForecastDataset
   from openstef_models.models.forecasting_model import ModelFitResult


   class MetricsLoggerCallback(ForecastingCallback):
       """Logs evaluation metrics to stdout after every fit."""

       def on_fit_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: VersionedTimeSeriesDataset | TimeSeriesDataset,
           result: ModelFitResult,
       ) -> None:
           if result is not None and result.metrics_test is not None:
               logger.info("Test metrics:\n%s", result.metrics_test.to_dataframe())

       def on_predict_end(
           self,
           context: WorkflowContext[CustomForecastingWorkflow],
           data: VersionedTimeSeriesDataset | TimeSeriesDataset,
           result: ForecastDataset,
       ) -> None:
           logger.info("Forecast produced %d rows", len(result.data))


   workflow = CustomForecastingWorkflow(
       model_id="my_custom_forecaster_v1",
       model=model,
       callbacks=[MetricsLoggerCallback()],
   )

For production use cases, OpenSTEF ships an ``MLFlowStorageCallback`` that handles model versioning and artifact storage automatically — see the ``openstef_models.workflows`` module for details.

.. note::

   Multiple callbacks can be registered simultaneously. They are executed in list order, so you can chain logging, validation, and storage callbacks without any of them being aware of the others.

Putting It All Together
-----------------------

The pattern for advanced customization in OpenSTEF is always the same:

- **Extend** ``TimeSeriesTransform`` to add new features or cleaning steps.
- **Compose** transforms into a ``TransformPipeline`` for preprocessing and postprocessing.
- **Assemble** a ``ForecastingModel`` from those pipelines and a forecaster.
- **Orchestrate** with ``CustomForecastingWorkflow``, attaching callbacks for any cross-cutting concerns.

**[DIAGRAM: Layered composition — TimeSeriesTransform instances compose into TransformPipeline, TransformPipeline composes into ForecastingModel (preprocessing + forecaster + postprocessing), ForecastingModel composes into CustomForecastingWorkflow with callbacks attached]**

This compositional design means you can unit-test each transform in isolation, swap forecasters without touching feature engineering, and add monitoring callbacks without modifying model code.

For evaluating how well your custom pipeline generalises to unseen data, see :doc:`backtesting`. If you are still setting up your environment, refer to :doc:`installation`.