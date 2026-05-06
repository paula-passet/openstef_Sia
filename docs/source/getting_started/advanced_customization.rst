Advanced Customization
======================

This page is for users who have already run their first forecast — if you haven't, start with :doc:`first_forecast` — and want to go beyond the defaults. It covers the three main extension points in OpenSTEF: custom data preparation, custom feature engineering, and assembling bespoke pipeline workflows.

.. note::

   All examples on this page assume OpenSTEF V4 and a working installation. See :doc:`installation` for setup instructions.

Extension Points Overview
-------------------------

OpenSTEF is built around a small set of composable abstractions. Every customisation you make plugs into one of these three layers:

- **Transforms** — stateless or stateful operations that accept and return a ``TimeSeriesDataset``. They are the atoms of feature engineering and data preparation.
- **TransformPipeline** — an ordered sequence of transforms applied in series. Preprocessing and postprocessing are both pipelines.
- **ForecastingModel / CustomForecastingWorkflow** — the top-level objects that wire a pipeline, a model, and storage together into a runnable workflow.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_1.mmd

Writing a Custom Transform
--------------------------

Every built-in transform in ``openstef_models`` (lag adders, holiday features, wind power features, dimensionality reducers) implements the same two-class mixin pattern: ``BaseConfig`` for Pydantic-based configuration and ``TimeSeriesTransform`` for the transform contract. Your custom transforms follow exactly the same pattern.

The ``TimeSeriesTransform`` interface requires three methods:

- ``is_fitted`` — a property returning ``True`` when the transform is ready to call ``transform()``.
- ``fit(data)`` — learn any parameters from training data; for stateless transforms this is a no-op.
- ``transform(data)`` — apply the transform and return a new ``TimeSeriesDataset``.

Here is a minimal example that adds a rolling-mean smoothing feature:

.. code-block:: python

   from datetime import timedelta
   from typing import override

   import pandas as pd
   from pydantic import Field

   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform


   class RollingMeanAdder(BaseConfig, TimeSeriesTransform):
       """Add a rolling-mean feature over a configurable window."""

       feature: str = Field(description="Column to smooth.")
       window: timedelta = Field(
           default=timedelta(hours=24),
           description="Rolling window width.",
       )

       @property
       @override
       def is_fitted(self) -> bool:
           return True  # Stateless — no fitting required.

       @override
       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # Nothing to learn.

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           window_steps = int(self.window / data.resolution)
           smoothed = (
               data.data[self.feature]
               .rolling(window=window_steps, min_periods=1)
               .mean()
               .rename(f"{self.feature}_rolling_mean_{self.window}")
           )
           new_df = data.data.copy()
           new_df[smoothed.name] = smoothed
           return data.model_copy(update={"data": new_df})

A stateful transform — one that learns parameters during ``fit()`` — looks the same but stores learned values as private Pydantic fields (``PrivateAttr``) and sets ``is_fitted`` based on whether those fields have been populated. The built-in ``LagsAdder`` and ``DimensionalityReducer`` are good references for this pattern.

.. note::

   Transforms are Pydantic models. All configuration is declared as ``Field(...)`` attributes, which means they are automatically serialisable and can be stored alongside a saved model.

Composing a Feature Pipeline
-----------------------------

Once you have individual transforms, you assemble them into a ``TransformPipeline``. The pipeline calls ``fit_transform`` on each step in order during training and ``transform`` on each step during inference.

The example below combines the built-in ``HolidayFeatureAdder`` and ``LagsAdder`` with the custom ``RollingMeanAdder`` defined above:

.. code-block:: python

   from datetime import timedelta

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.transforms import TransformPipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   feature_pipeline = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country=CountryAlpha2("NL")),
           LagsAdder(
               feature="load",
               lags=[
                   timedelta(hours=-1),
                   timedelta(hours=-24),
                   timedelta(days=-7),
               ],
           ),
           RollingMeanAdder(feature="load", window=timedelta(hours=48)),
       ]
   )

``TransformPipeline`` is itself generic over the dataset type (``TransformPipeline[TimeSeriesDataset]``), so the same pattern applies to postprocessing pipelines that operate on ``EnergyComponentDataset`` or any other dataset type you introduce.

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_2.mmd

Customising the Forecasting Model
----------------------------------

A ``ForecastingModel`` wraps a preprocessing pipeline, a core estimator, and a postprocessing pipeline into a single serialisable object. You can supply your own pipeline at construction time:

.. code-block:: python

   from openstef_models.model.forecasting import ForecastingModel
   from openstef_models.model.estimators import ConstantMedianForecaster

   model = ForecastingModel(
       preprocessing=feature_pipeline,   # your custom TransformPipeline
       estimator=ConstantMedianForecaster(),
       # postprocessing defaults to an empty pipeline
   )

Swap ``ConstantMedianForecaster`` for any scikit-learn–compatible estimator. The preprocessing pipeline you pass in replaces the default feature engineering entirely, so you have full control over what the estimator sees.

Building a Custom Workflow
--------------------------

The ``CustomForecastingWorkflow`` ties a ``ForecastingModel`` to model storage and exposes ``train()`` and ``predict()`` methods. The quickest way to create one is through the ``create_forecasting_workflow`` factory, but you can also instantiate it directly when you need finer control.

.. code-block:: python

   from pathlib import Path

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )

   config = ForecastingWorkflowConfig(
       location=LocationConfig(country="NL", region="amsterdam"),
       horizon_hours=24,
   )

   workflow = create_forecasting_workflow(config)

For cases where the preset does not fit — for example, you want to inject a custom model or a non-standard storage backend — construct the workflow manually:

.. code-block:: python

   from openstef_models.workflows.forecasting import CustomForecastingWorkflow
   from openstef_models.storage import LocalModelStorage

   storage = LocalModelStorage(path=Path("./models"))

   workflow = CustomForecastingWorkflow(
       model=model,          # ForecastingModel built above
       storage=storage,
   )

   # Training
   workflow.train(train_data=train_dataset, validation_data=val_dataset)

   # Inference
   forecast = workflow.predict(forecast_data=forecast_dataset)

.. mermaid:: /diagrams/getting_started/advanced_customization_diagram_3.mmd

Custom Data Preparation
-----------------------

Data preparation — cleaning, resampling, aligning external features — happens *before* data enters the pipeline. OpenSTEF expects a ``TimeSeriesDataset`` (or ``VersionedTimeSeriesDataset`` for multi-horizon setups) as input. The cleanest approach is to write a preparation function that returns one of these types, keeping your raw-data logic entirely separate from the pipeline.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset


   def prepare_dataset(raw_df: pd.DataFrame, resolution_minutes: int = 15) -> TimeSeriesDataset:
       """Clean and resample raw meter data into an OpenSTEF dataset."""
       df = (
           raw_df
           .dropna(subset=["load"])
           .resample(f"{resolution_minutes}min")
           .mean()
           .interpolate(method="time", limit=4)  # fill short gaps only
       )
       return TimeSeriesDataset(data=df)


   train_dataset = prepare_dataset(raw_train_df)
   forecast_dataset = prepare_dataset(raw_forecast_df)

Keep preparation functions pure and side-effect free. This makes them easy to test in isolation and straightforward to swap out when your data source changes.

.. note::

   If your preparation logic is complex — multiple sources, schema validation, unit conversion — consider placing it in a dedicated module and testing it independently of the pipeline. The pipeline itself should receive clean, correctly typed data.

Putting It All Together
-----------------------

The following sketch shows how the pieces above combine into a complete custom setup:

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   import pandas as pd
   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TransformPipeline
   from openstef_models.model.forecasting import ForecastingModel
   from openstef_models.model.estimators import ConstantMedianForecaster
   from openstef_models.storage import LocalModelStorage
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.workflows.forecasting import CustomForecastingWorkflow

   # 1. Prepare data
   train_dataset = prepare_dataset(raw_train_df)
   forecast_dataset = prepare_dataset(raw_forecast_df)

   # 2. Build feature pipeline
   pipeline = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country=CountryAlpha2("NL")),
           LagsAdder(feature="load", lags=[timedelta(hours=-1), timedelta(days=-1)]),
           RollingMeanAdder(feature="load", window=timedelta(hours=48)),
       ]
   )

   # 3. Assemble model
   model = ForecastingModel(
       preprocessing=pipeline,
       estimator=ConstantMedianForecaster(),
   )

   # 4. Create workflow and run
   workflow = CustomForecastingWorkflow(
       model=model,
       storage=LocalModelStorage(path=Path("./models")),
   )
   workflow.train(train_data=train_dataset)
   forecast = workflow.predict(forecast_data=forecast_dataset)

.. note::

   Once trained, ``LocalModelStorage`` serialises the entire ``ForecastingModel`` — including your custom pipeline configuration — to disk. Reloading it restores the fitted state without any extra steps.

Next Steps
----------

- To evaluate your custom model on historical data, see :doc:`backtesting`.
- For the minimal working example that precedes this page, see :doc:`quickstart`.
- For wind-power-specific feature transforms (``WindPowerFeatureAdder``) and dimensionality reduction (``DimensionalityReducer``), browse the ``openstef_models.transforms`` package directly — both follow the same ``BaseConfig + TimeSeriesTransform`` pattern shown here.