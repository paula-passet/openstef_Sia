Quickstart
==========

This page gets you from zero to a working energy forecast in under five minutes. No explanations — just copy, paste, and run. For the reasoning behind each step, see :doc:`first_forecast`.

.. note::

   **Prerequisites:** OpenSTEF installed in your environment. If not, see :doc:`installation` first.

.. note:: [DIAGRAM: Simple linear workflow — configure preset (ForecastingWorkflowConfig) → create workflow (create_forecasting_workflow) → fit (workflow.fit) → predict (workflow.predict) → output (ForecastDataset / HTML plot)]

----

Step 1: Generate synthetic data
--------------------------------

OpenSTEF ships a built-in utility for creating realistic synthetic load data. No external files needed.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=90),
       sample_interval=timedelta(hours=1),
       wind_influence=-10.0,
       temp_influence=5.0,
       radiation_influence=-7.0,
       stochastic_influence=2.0,
   )

   print(dataset.data.head())

The returned ``TimeSeriesDataset`` contains an hourly ``load`` column alongside weather features (temperature, wind speed, radiation) that the model will use as predictors.

----

Step 2: Configure and create the workflow
------------------------------------------

The ``ForecastingWorkflowConfig`` / ``create_forecasting_workflow`` preset wires together feature engineering, model training, and prediction in one call.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="my_first_forecast_v1",
           model="lgbm",                          # xgboost | lgbm | gblinear | lgbmlinear
           horizons=[LeadTime.from_string("PT36H")],   # forecast up to 36 h ahead
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],    # median + 80 % prediction interval
           mlflow_storage=None,                    # disable experiment tracking for now
       )
   )

.. note::

   ``mlflow_storage=None`` skips MLflow logging. To persist runs, see :doc:`first_forecast`.

----

Step 3: Train the model
------------------------

.. code-block:: python

   result = workflow.fit(dataset)

   if result is not None:
       print(result.metrics_full.to_dataframe())

Training on 90 days of hourly data typically completes in a few seconds. ``result.metrics_full`` contains cross-validation scores for every horizon.

----

Step 4: Generate a forecast
-----------------------------

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   forecast: ForecastDataset = workflow.predict(dataset)

   print(forecast.data.tail())

``forecast.data`` is a ``DataFrame`` indexed by timestamp and horizon, with one column per quantile.

----

Step 5: Visualise the result
------------------------------

OpenSTEF includes an interactive plotter — no matplotlib required.

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(dataset.select_version().data["load"])
       .add_model(
           model_name="lgbm",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot(title="My First OpenSTEF Forecast")
   )

   fig.write_html("forecast_plot.html")

Open ``forecast_plot.html`` in any browser to explore the interactive chart.

**[VISUALIZATION: Interactive forecast plot showing measured load (solid line) overlaid with the median forecast and shaded 10–90 % quantile band across a 36-hour horizon]**

----

Complete script
----------------

Everything above in one copy-paste block:

.. code-block:: python

   from datetime import timedelta

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter
   from openstef_core.datasets import ForecastDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # 1. Synthetic data
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=90),
       sample_interval=timedelta(hours=1),
       wind_influence=-10.0,
       temp_influence=5.0,
       radiation_influence=-7.0,
       stochastic_influence=2.0,
   )

   # 2. Configure workflow
   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="my_first_forecast_v1",
           model="lgbm",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           mlflow_storage=None,
       )
   )

   # 3. Train
   result = workflow.fit(dataset)
   if result is not None:
       print(result.metrics_full.to_dataframe())

   # 4. Predict
   forecast: ForecastDataset = workflow.predict(dataset)
   print(forecast.data.tail())

   # 5. Plot
   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(dataset.select_version().data["load"])
       .add_model(
           model_name="lgbm",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot(title="My First OpenSTEF Forecast")
   )
   fig.write_html("forecast_plot.html")
   print("Forecast written to forecast_plot.html")

----

What's next?
-------------

- :doc:`first_forecast` — the same workflow with step-by-step explanations of every parameter and design decision.
- :doc:`backtesting` — evaluate your model on historical data before deploying it.
- :doc:`advanced_customization` — swap in custom feature transforms, model architectures, and callbacks.