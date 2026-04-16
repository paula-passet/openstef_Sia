Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with OpenSTEF from scratch. By the end you will have loaded data, configured a model, trained it, generated predictions, and evaluated the results — with a clear understanding of what each step does and why it matters.

If you just want the shortest possible working example, see :doc:`quickstart` instead. For comparing multiple models against each other, see :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF is a library that gives you composable building blocks for energy forecasting. The central objects you will work with in this tutorial are:

- **TimeSeriesDataset** — a validated wrapper around a ``pandas.DataFrame`` with a fixed sample interval. All data flows through this type.
- **ForecastingWorkflowConfig** — a Pydantic configuration object that fully describes your model: which algorithm to use, which columns carry which signals, feature engineering settings, and location metadata.
- **CustomForecastingWorkflow** — the high-level orchestrator that ties together preprocessing, the forecaster, postprocessing, and optional persistence. You call ``fit()`` and ``predict()`` on this object.

The ``create_forecasting_workflow()`` factory function builds a fully wired ``CustomForecastingWorkflow`` from a ``ForecastingWorkflowConfig``, so you rarely need to assemble the pipeline by hand.

Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects a :class:`~openstef_core.datasets.TimeSeriesDataset`: a regularly sampled time series with a ``pandas.DatetimeIndex`` and at minimum a *target column* (the load or power value you want to forecast). Weather features such as temperature, wind speed, and solar radiation are optional but strongly improve accuracy.

For this tutorial we use the built-in synthetic dataset generator so you can run the code immediately without external data:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # Nine months of hourly data with temperature and radiation influence
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,
   )

   print(dataset.data.shape)          # (6480, N) — rows × features
   print(dataset.data.columns.tolist())

When you bring your own data, wrap it in a ``TimeSeriesDataset`` directly:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.read_csv("my_load_data.csv", index_col="timestamp", parse_dates=True)
   dataset = TimeSeriesDataset(data=df, sample_interval=timedelta(hours=1))

.. note::

   The ``sample_interval`` must match the actual frequency of your data. OpenSTEF validates this on construction and will raise a ``TimeSeriesValidationError`` if rows are missing or duplicated. Fix gaps in your source data before wrapping it.

Step 2 — Configure the Model
-----------------------------

``ForecastingWorkflowConfig`` is the single source of truth for your forecasting setup. It captures the model type, the column names that carry each signal, the forecast horizons, and location metadata used for holiday and solar-angle features.

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
   )
   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="my_first_forecast",
       model="xgboost",                        # xgboost | lgbm | gblinear | median
       sample_interval=timedelta(hours=1),
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],    # median + 80 % prediction interval
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       location=LocationConfig(
           name="Amsterdam",
           country_code=CountryAlpha2("NL"),
       ),
   )

A few configuration choices worth understanding:

- **model** — ``"xgboost"`` is a good default for most energy time series. Use ``"lgbm"`` for faster training on large datasets or ``"median"`` as a simple baseline.
- **quantiles** — requesting multiple quantiles gives you a probabilistic forecast (a prediction interval) rather than a single point estimate. ``Q(0.5)`` alone produces a deterministic median forecast.
- **location** — the country code enables automatic public-holiday features; the coordinates (if provided) enable solar-angle features that improve solar-influenced load forecasts.

Step 3 — Build and Train the Workflow
--------------------------------------

Pass the configuration to ``create_forecasting_workflow()`` to get a fully assembled pipeline, then call ``fit()``:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import create_forecasting_workflow

   workflow = create_forecasting_workflow(config=config)

   # fit() returns a ModelFitResult with train/val/test metrics
   fit_result = workflow.fit(dataset)

   print("Training metrics:", fit_result.metrics_train)
   print("Validation metrics:", fit_result.metrics_val)

What happens inside ``fit()``:

1. The preprocessing pipeline runs ``InputConsistencyChecker``, ``FlatlineChecker``, and ``CompletenessChecker`` to validate the data.
2. Feature engineering transforms — ``LagsAdder``, ``CyclicFeaturesAdder``, weather-derived feature adders — are fitted on the training split and applied to all splits.
3. The data is divided into training, validation, and test subsets.
4. The chosen forecaster (XGBoost in this case) is trained on the training split.
5. In-sample predictions are generated for all splits and scored, producing the ``ModelFitResult``.

.. note::

   The ``cutoff_history`` parameter on ``ForecastingWorkflowConfig`` controls how many leading rows are excluded from training to avoid NaN values introduced by lag features. If you add a 14-day lag, set ``cutoff_history=timedelta(days=14)``. The default is conservative but you may need to adjust it for custom lag configurations.

Step 4 — Generate a Forecast
------------------------------

Once the workflow is fitted, call ``predict()`` with the data window that covers the forecast context. OpenSTEF needs enough historical context to compute lag features:

.. code-block:: python

   from datetime import datetime, timezone

   # Use the last portion of the dataset as the prediction context
   forecast_start = datetime(2025, 9, 1, tzinfo=timezone.utc)
   forecasts = workflow.predict(dataset, forecast_start=forecast_start)

   # forecasts is a ForecastDataset — access the underlying DataFrame
   print(forecasts.data.head())

The returned ``ForecastDataset`` contains one column per requested quantile (e.g. ``forecast_0.1``, ``forecast_0.5``, ``forecast_0.9``) alongside the original features. The ``forecast_start`` argument pins the prediction window; if omitted, OpenSTEF uses the latest available timestamp in the data.

Step 5 — Evaluate the Results
-------------------------------

The workflow's ``score()`` method computes evaluation metrics by comparing predictions against the ground truth in the dataset:

.. code-block:: python

   metrics = workflow.model.score(dataset)
   print(metrics.metrics)   # dict of metric name → value

For a visual inspection, use the built-in ``ForecastTimeSeriesPlotter``:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecasts=forecasts, title="My First Forecast")
   fig.show()

The plot overlays the median forecast and the prediction interval bands against the actual load values, making it easy to spot systematic bias or periods of high uncertainty.

.. note::

   ``score()`` evaluates at the model's maximum horizon. For a breakdown of accuracy across multiple lead times — for example, how accuracy degrades from 1 hour ahead to 48 hours ahead — see :doc:`backtesting`, which covers the full backtesting workflow.

Persisting the Model
---------------------

In production you will want to save a trained workflow and reload it later without retraining. Use ``LocalModelStorage``:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save after training
   storage.save(model_id=config.model_id, model=workflow.model)

   # Reload in a separate process
   loaded_workflow = workflow.from_storage(
       model_id=config.model_id,
       storage=storage,
   )
   forecasts = loaded_workflow.predict(dataset)

Putting It All Together
------------------------

Here is the complete, self-contained script combining every step above:

.. code-block:: python

   import logging
   from datetime import datetime, timedelta, timezone
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import Q
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_models.storage import LocalModelStorage
   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   logging.basicConfig(level=logging.INFO)

   # 1. Data
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,
   )

   # 2. Configuration
   config = ForecastingWorkflowConfig(
       model_id="my_first_forecast",
       model="xgboost",
       sample_interval=timedelta(hours=1),
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       location=LocationConfig(
           name="Amsterdam",
           country_code=CountryAlpha2("NL"),
       ),
   )

   # 3. Build and train
   workflow = create_forecasting_workflow(config=config)
   fit_result = workflow.fit(dataset)
   print("Validation metrics:", fit_result.metrics_val)

   # 4. Forecast
   forecast_start = datetime(2025, 9, 1, tzinfo=timezone.utc)
   forecasts = workflow.predict(dataset, forecast_start=forecast_start)

   # 5. Evaluate
   metrics = workflow.model.score(dataset)
   print("Evaluation metrics:", metrics.metrics)

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecasts=forecasts, title="My First Forecast")
   fig.show()

   # Persist
   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model_id=config.model_id, model=workflow.model)

Next Steps
----------

Now that you have a working forecast, consider:

- :doc:`backtesting` — rigorously evaluate your model across a historical period and compare it against alternative configurations.
- :doc:`advanced_customization` — replace built-in components with custom preprocessors, forecasters, or postprocessors to match your specific use case.
- :doc:`installation` — if you are setting up a new environment, this page covers optional dependency groups for different backends.