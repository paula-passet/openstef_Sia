Quickstart
==========

This page gets you to a working forecast in the shortest possible time. Copy the code below, run it, and you will have probabilistic energy load predictions as output. For explanations of what each step does and why, see :doc:`first_forecast`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF must be installed before running the example below. If you have not done this yet, see :doc:`installation`.

.. code-block:: python

   pip install openstef-models openstef-core

Minimal Working Example
-----------------------

The following script is self-contained. It generates synthetic load data, configures a gradient-boosted linear forecasting workflow, trains it, and produces a probabilistic forecast.

.. code-block:: python

   # SPDX-License-Identifier: MPL-2.0
   from datetime import timedelta

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.presets.forecasting_workflow import GBLinearForecaster

   # ── 1. Load data ──────────────────────────────────────────────────────────────
   # create_synthetic_forecasting_dataset returns a TimeSeriesDataset with
   # realistic load, weather, and price columns — no external files needed.
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=90),
       sample_interval=timedelta(hours=1),
       include_atmosphere=True,
   )

   # Split into train / forecast windows
   split_point = dataset.data.index[-48]  # hold out last 48 hours
   train_data = dataset.slice(end=split_point)
   forecast_data = dataset.slice(start=split_point)

   # ── 2. Create the model ───────────────────────────────────────────────────────
   # ForecastingWorkflowConfig declares what to predict and how.
   # create_forecasting_workflow assembles the full pipeline from that config.
   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="quickstart_model",
           model="gblinear",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           target_column="load",
           temperature_column="temperature_2m",
           relative_humidity_column="relative_humidity_2m",
           wind_speed_column="wind_speed_10m",
           radiation_column="shortwave_radiation",
           pressure_column="surface_pressure",
           mlflow_storage=None,  # disable experiment tracking for now
           gblinear_hyperparams=GBLinearForecaster.HyperParams(n_steps=50),
       )
   )

   # ── 3. Train ──────────────────────────────────────────────────────────────────
   result = workflow.fit(train_data)
   print("Training metrics:")
   print(result.metrics_full.to_dataframe())

   # ── 4. Forecast ───────────────────────────────────────────────────────────────
   forecast: ForecastDataset = workflow.predict(forecast_data)

   # ── 5. Inspect output ─────────────────────────────────────────────────────────
   print(forecast.data.head())
   # Columns: quantile_P10  quantile_P50  quantile_P90
   # Index:   DatetimeIndex (hourly)

Run it with:

.. code-block:: bash

   python quickstart.py

Understanding the Output
------------------------

``workflow.predict()`` returns a :class:`~openstef_core.datasets.ForecastDataset`. Its ``.data`` attribute is a ``pandas.DataFrame`` with one column per requested quantile:

- ``quantile_P10`` — lower bound of the 80 % prediction interval
- ``quantile_P50`` — median (point forecast)
- ``quantile_P90`` — upper bound of the 80 % prediction interval

The index is a ``DatetimeIndex`` aligned to the ``sample_interval`` you configured.

.. note::

   The synthetic dataset used here is provided by ``openstef_core.testing`` specifically for examples and tests. When working with real data, replace ``create_synthetic_forecasting_dataset`` with a ``TimeSeriesDataset`` built from your own ``pandas.DataFrame``. See :doc:`first_forecast` for details on data preparation.

Visualising the Forecast
------------------------

OpenSTEF ships with built-in plotting utilities so you do not need to reach for matplotlib directly:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(forecast)
   fig.show()

``ForecastTimeSeriesPlotter`` renders the quantile bands and the observed load on a single interactive chart.

What to Do Next
---------------

This example uses the ``gblinear`` preset with default settings. OpenSTEF is a library — every component shown above is replaceable:

- **Understand each step** — :doc:`first_forecast` walks through the same workflow with full explanations of data preparation, feature engineering, and model configuration.
- **Try different models** — swap ``model="gblinear"`` for ``"xgboost"``, ``"lgbm"``, or ``"median"`` in :class:`~openstef_models.presets.ForecastingWorkflowConfig` without changing anything else.
- **Measure model quality** — :doc:`backtesting` shows how to replay historical data to get unbiased performance estimates.
- **Customise the pipeline** — :doc:`advanced_customization` covers replacing the built-in preprocessors, adding your own feature transforms, and wiring in custom callbacks.