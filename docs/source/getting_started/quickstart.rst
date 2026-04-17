Quickstart
==========

Get your first OpenSTEF forecast running in under five minutes. This page gives you a single, copy-paste-ready script — no explanations, no detours. If you want to understand *why* each step works, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. note::

   [DIAGRAM: Simple linear workflow — configure ForecastingWorkflowConfig → call create_forecasting_workflow → workflow.fit(dataset) → workflow.predict(dataset) → ForecastDataset output]

Prerequisites
-------------

OpenSTEF installed and ready. If not::

   pip install openstef-models

The Complete Script
-------------------

Copy the block below, run it, and you will have a trained model and a printed forecast table.

.. code-block:: python

   import logging
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.integrations.mlflow import MLFlowStorage

   logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

   # 1. Synthetic data — 90 days of hourly load with weather influences
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=90),
       wind_influence=-10.0,
       temp_influence=5.0,
       radiation_influence=-7.0,
       stochastic_influence=2.0,
       sample_interval=timedelta(hours=1),
   )

   # 2. Configure the preset workflow
   workspace = Path("./openstef_quickstart")
   workspace.mkdir(exist_ok=True)

   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="quickstart_model_v1",
           model="gblinear",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           mlflow_storage=MLFlowStorage(
               tracking_uri=str(workspace / "mlflow_tracking"),
               local_artifacts_path=workspace / "mlflow_artifacts",
           ),
       )
   )

   # 3. Train
   result = workflow.fit(dataset)
   if result is not None:
       print(result.metrics_full.to_dataframe())

   # 4. Predict
   forecast = workflow.predict(dataset)
   print(forecast.data.tail())

What You Get
------------

Running the script produces:

- A printed metrics table from ``result.metrics_full`` showing training performance.
- A ``forecast.data`` DataFrame with point forecasts and quantile columns (P10, P50, P90) for a 36-hour horizon.
- A persisted model stored under ``./openstef_quickstart/mlflow_tracking``, ready to reload.

Visualising the Forecast
------------------------

OpenSTEF ships a built-in plotter. Add these lines after ``workflow.predict``:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=dataset.select_version().data["load"])
       .add_model(
           model_name="gblinear",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.write_html("forecast_plot.html")

Open ``forecast_plot.html`` in any browser to see the forecast overlaid on the training data.

[VISUALIZATION: Screenshot of the interactive forecast plot showing measured load, median forecast line, and shaded P10–P90 quantile band over a 36-hour horizon]

Key Parameters at a Glance
---------------------------

The two objects that control everything in the preset workflow are ``ForecastingWorkflowConfig`` and the dataset factory. The most commonly adjusted settings are:

- ``model`` — the underlying estimator (``"gblinear"``, ``"xgb"``, ``"lgbm"``, and others).
- ``horizons`` — list of :class:`LeadTime` values defining how far ahead to forecast.
- ``quantiles`` — probabilistic output bands; ``Q(0.5)`` alone gives a point forecast.
- ``length`` in ``create_synthetic_forecasting_dataset`` — controls how much history the model trains on.

.. note::

   ``create_synthetic_forecasting_dataset`` is a convenience helper from ``openstef_core.testing``.
   Replace it with your own :class:`~openstef_core.datasets.TimeSeriesDataset` when moving to real data.
   See :doc:`first_forecast` for a guided walkthrough of loading real data.

Next Steps
----------

- :doc:`first_forecast` — the same workflow explained step by step, with real data loading and feature engineering details.
- :doc:`backtesting` — evaluate your model on historical data before deploying it.
- :doc:`advanced_customization` — swap in custom transforms, forecasters, and callbacks.