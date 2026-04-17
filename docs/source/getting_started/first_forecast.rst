Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast using OpenSTEF's
custom pipeline approach. By the end you will have a working pipeline that loads data, engineers
features, trains a model, produces probabilistic forecasts, and visualises the result.

If you just want the shortest possible working example, see :doc:`quickstart` first. This page
goes deeper — it explains *what* each component does and *why* you would configure it the way
you do. For evaluating your model on historical data once it is trained, see :doc:`backtesting`.

.. note::

   [DIAGRAM: Step-by-step flowchart showing the five stages of a custom pipeline:
   (1) Dataset (TimeSeriesDataset) →
   (2) TransformPipeline / preprocessing transforms (HolidayFeatureAdder, LagsAdder, Scaler) →
   (3) ForecastingModel (forecaster + pre/postprocessing) →
   (4) CustomForecastingWorkflow (orchestration + callbacks + storage) →
   (5) fit() / predict() producing a ForecastDataset.
   Show arrows between each stage and label the data type flowing along each arrow.]


Overview
--------

OpenSTEF is a library of composable building blocks. Rather than hiding decisions inside a
black-box application, it lets you assemble a pipeline from explicit, inspectable pieces:

- **Dataset** — a ``TimeSeriesDataset`` or ``VersionedTimeSeriesDataset`` that carries your
  measurements and covariates.
- **Transforms** — stateful objects that learn from data during ``fit`` and apply the same
  transformation during ``transform``. They are chained together in a ``TransformPipeline``.
- **ForecastingModel** — wraps a forecaster with a preprocessing pipeline and a postprocessing
  pipeline into a single trainable unit.
- **CustomForecastingWorkflow** — the top-level orchestrator that drives ``fit`` and ``predict``,
  manages model persistence, and fires lifecycle callbacks.

The sections below build each layer in turn.


Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects time series data in a ``TimeSeriesDataset``. The dataset enforces a consistent
sampling interval and carries both the target column (the load you want to forecast) and any
covariate columns (weather, prices, calendar features you supply yourself).

For this tutorial we use the built-in synthetic dataset generator so you can run the code
without external data:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # Nine months of hourly data with wind and temperature covariates
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       wind_influence=-0.2,
       temp_influence=0.3,
   )

   print(dataset.data.shape)        # (6480, N)
   print(dataset.data.columns.tolist())

The ``create_synthetic_forecasting_dataset`` function returns a ``TimeSeriesDataset`` with a
``"load"`` target column and several covariate columns. In production you would construct the
dataset from your own parquet files:

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   load = VersionedTimeSeriesDataset.read_parquet("load_measurements/my_site.parquet")
   weather = VersionedTimeSeriesDataset.read_parquet("weather_forecasts/my_site.parquet")

   dataset = VersionedTimeSeriesDataset.concat(
       [load, weather], mode="left"
   ).select_version()

``VersionedTimeSeriesDataset`` tracks *when* each data point became available, which is essential
for realistic backtesting. ``select_version()`` materialises the versioned data into a plain
``TimeSeriesDataset`` for training.


Step 2 — Configure the Preprocessing Pipeline
----------------------------------------------

Feature engineering in OpenSTEF is done through a ``TransformPipeline`` — an ordered sequence of
``Transform`` objects. Each transform is fitted on training data and then applied identically at
prediction time, preventing data leakage.

The three transforms used most often for energy forecasting are:

- ``HolidayFeatureAdder`` — adds binary columns for public holidays in a given country.
- ``LagsAdder`` — creates lag features (e.g. load 24 h ago, 48 h ago, 168 h ago) that are
  valid for the forecast horizon you are targeting.
- ``Scaler`` — standardises numeric columns so gradient-boosted models converge faster.

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.transforms.dataset_transforms import TransformPipeline
   from openstef_models.transforms.time_domain import HolidayFeatureAdder, LagsAdder
   from openstef_models.transforms.general import Scaler

   horizons = [timedelta(hours=h) for h in range(1, 49)]   # 1-hour to 48-hour ahead

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               target_column="load",
           ),
           Scaler(),
       ]
   )

.. note::

   ``LagsAdder`` only adds lag features that are *causally valid* for each forecast horizon.
   A 1-hour-ahead forecast cannot use a 1-hour lag of the target, so ``LagsAdder`` omits it
   automatically. This is one of the key correctness guarantees the library provides.

The ``TransformPipeline`` calls each transform's ``fit`` method in sequence, passing the
*output* of the previous transform as input to the next. You never need to manage intermediate
state yourself.


Step 3 — Configure the ForecastingModel
----------------------------------------

A ``ForecastingModel`` bundles three things: a preprocessing pipeline, a forecaster, and a
postprocessing pipeline. It is the unit that gets serialised and loaded for production use.

.. code-block:: python

   from openstef_core.types import Q
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.median_forecaster import MedianForecaster
   from openstef_models.transforms.postprocessing import QuantileSorter, ConfidenceIntervalApplicator

   quantiles = [Q(0.05), Q(0.50), Q(0.95)]

   model = ForecastingModel(
       preprocessing=preprocessing,          # the pipeline from Step 2
       forecaster=MedianForecaster(
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

``MedianForecaster`` is a simple but instructive baseline: it predicts the median of recent
history for each horizon. Swap it for ``LGBMForecaster`` or ``XGBoostForecaster`` when you are
ready for a production-grade model — the rest of the pipeline stays the same.

``QuantileSorter`` enforces monotonicity across quantile predictions (the 5th percentile must
not exceed the 50th). ``ConfidenceIntervalApplicator`` converts raw quantile outputs into the
named columns that downstream consumers expect.


Step 4 — Wrap in a Workflow
----------------------------

``CustomForecastingWorkflow`` is the top-level orchestrator. It owns the model, drives the
``fit`` / ``predict`` lifecycle, and optionally persists the trained model to disk via a
storage backend.

.. code-block:: python

   from pathlib import Path
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.integrations.local import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))

   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_first_forecast",
       storage=storage,
   )

``LocalModelStorage`` serialises the fitted workflow to a directory on disk. When you call
``workflow.fit(dataset)`` the trained model is saved automatically, and a subsequent call to
``CustomForecastingWorkflow.from_storage(model_id="my_first_forecast", storage=storage)``
reloads it without retraining.

For production deployments you can swap ``LocalModelStorage`` for ``MLFlowStorageCallback``
to track experiments in MLflow — see :doc:`advanced_customization` for details.


Step 5 — Train the Model
------------------------

With the workflow assembled, training is a single call:

.. code-block:: python

   import logging
   logging.basicConfig(level=logging.INFO)

   fit_result = workflow.fit(dataset)

   print(fit_result)

During ``fit``, the workflow:

1. Calls ``preprocessing.fit(dataset)`` to learn scaler statistics, lag offsets, and holiday
   calendars from the training data.
2. Passes the transformed data to the forecaster's own ``fit`` method.
3. Runs postprocessing on the in-sample predictions to validate the output shape.
4. Serialises the fitted workflow to the configured storage backend.

The returned ``ModelFitResult`` contains in-sample metrics and, if a validation split was
configured, out-of-sample metrics too.


Step 6 — Generate Forecasts
----------------------------

Once the workflow is fitted, call ``predict`` with a dataset that covers the forecast horizon:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # A short window of recent data that the model uses as context
   forecast_input = create_synthetic_forecasting_dataset(
       length=timedelta(days=14),
       sample_interval=timedelta(hours=1),
   )

   forecasts = workflow.predict(forecast_input)

   print(type(forecasts))           # ForecastDataset
   print(forecasts.data.columns.tolist())

The result is a ``ForecastDataset`` with one column per quantile (e.g. ``quantile_P05``,
``quantile_P50``, ``quantile_P95``) indexed by timestamp. The preprocessing pipeline applies
the *same* fitted transforms that were used during training — no re-fitting occurs.


Step 7 — Evaluate and Visualise
--------------------------------

OpenSTEF ships with a built-in time series plotter so you can inspect your forecasts without
reaching for an external plotting library:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecasts=forecasts, actuals=forecast_input)
   fig.show()

[VISUALIZATION: Side-by-side plot of actual load vs. forecast median with shaded 5th–95th
percentile confidence band, x-axis showing timestamps over a 48-hour window.]

For a more rigorous evaluation across many historical periods, see :doc:`backtesting`. The
backtesting tutorial shows how to replay your pipeline day-by-day over months of history and
compute aggregate metrics such as MAE, RMSE, and skill scores.


Putting It All Together
-----------------------

Here is the complete script combining every step above:

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.transforms.dataset_transforms import TransformPipeline
   from openstef_core.types import Q

   from openstef_models.integrations.local import LocalModelStorage
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.median_forecaster import MedianForecaster
   from openstef_models.transforms.general import Scaler
   from openstef_models.transforms.postprocessing import (
       ConfidenceIntervalApplicator,
       QuantileSorter,
   )
   from openstef_models.transforms.time_domain import HolidayFeatureAdder, LagsAdder
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   logging.basicConfig(level=logging.INFO)

   # --- Data ---
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
   )

   # --- Transforms ---
   horizons = [timedelta(hours=h) for h in range(1, 49)]
   quantiles = [Q(0.05), Q(0.50), Q(0.95)]

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           LagsAdder(
               history_available=timedelta(days=14),
               horizons=horizons,
               target_column="load",
           ),
           Scaler(),
       ]
   )

   # --- Model ---
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=MedianForecaster(horizons=horizons, quantiles=quantiles),
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

   # --- Workflow ---
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="my_first_forecast",
       storage=LocalModelStorage(base_path=Path("./models")),
   )

   # --- Train ---
   fit_result = workflow.fit(dataset)

   # --- Predict ---
   forecast_input = create_synthetic_forecasting_dataset(
       length=timedelta(days=14),
       sample_interval=timedelta(hours=1),
   )
   forecasts = workflow.predict(forecast_input)

   # --- Visualise ---
   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecasts=forecasts, actuals=forecast_input)
   fig.show()


Next Steps
----------

Now that you have a working pipeline, consider:

- **Swap the forecaster** — replace ``MedianForecaster`` with ``LGBMForecaster`` or
  ``XGBoostForecaster`` for gradient-boosted models that learn from the engineered features.
- **Add more transforms** — ``DatetimeFeaturesAdder``, ``CyclicFeaturesAdder``, and
  ``WindPowerFeatureAdder`` are all drop-in additions to the ``TransformPipeline``.
- **Evaluate rigorously** — the :doc:`backtesting` tutorial shows how to replay your pipeline
  over historical data to measure real-world accuracy.
- **Customise deeply** — :doc:`advanced_customization` covers writing your own transforms,
  forecasters, and callbacks.