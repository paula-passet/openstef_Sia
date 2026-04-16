Quickstart
==========

Get a forecast running in under five minutes. This page gives you a single, self-contained script you can copy, paste, and run immediately. No data files required — OpenSTEF includes a built-in synthetic dataset generator.

For a line-by-line explanation of what each step does, see :doc:`first_forecast`. For backtesting and model comparison, see :doc:`backtesting`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF must be installed before running the example below. If you haven't done that yet, see :doc:`installation`.

.. code-block:: python

   pip install openstef-core openstef-beam

The Complete Example
--------------------

The script below loads synthetic energy time series data, builds a forecasting pipeline, trains it, and produces a forecast — all in one go.

.. code-block:: python

   # SPDX-FileCopyrightText: 2025 Contributors to the OpenSTEF project
   # SPDX-License-Identifier: MPL-2.0

   from datetime import timedelta
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.models.forecasting_model import ForecastingModel
   from openstef_core.models.preprocessing import FeaturePipeline
   from openstef_core.models.preprocessing.transforms import (
       HolidayFeatures,
       LagTransform,
       StandardScaler,
   )
   from openstef_core.models.forecasters import ConstantMedianForecaster
   from openstef_core.storage import LocalModelStorage

   # ── 1. Load data ──────────────────────────────────────────────────────────────
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),   # ~9 months of hourly data
       sample_interval=timedelta(hours=1),
   )

   # Split into train and forecast windows
   split = dataset.data.index[-48]          # hold out last 48 hours
   data_train = dataset.slice_time(end=split)
   data_forecast = dataset.slice_time(start=split)

   # ── 2. Build the model ────────────────────────────────────────────────────────
   preprocessing = FeaturePipeline(
       transforms=[
           HolidayFeatures(country=CountryAlpha2("NL")),
           LagTransform(horizons=[timedelta(hours=h) for h in [1, 24, 168]]),
           StandardScaler(),
       ]
   )

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(),
       preprocessing=preprocessing,
   )

   # ── 3. Train ──────────────────────────────────────────────────────────────────
   fit_result = model.fit(data=data_train)
   print("Training metrics:", fit_result.metrics_train)

   # ── 4. Forecast ───────────────────────────────────────────────────────────────
   forecast = model.predict(data=data_forecast)
   print(forecast.data.head())

   # ── 5. (Optional) Persist the model ──────────────────────────────────────────
   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model, model_id="my_first_model")

Run it with:

.. code-block:: bash

   python quickstart.py

You should see training metrics printed to the console followed by the first few rows of the forecast ``DataFrame``.

What You Just Did
-----------------

Each numbered step in the script maps to a core OpenSTEF concept:

- **Step 1 — Data** ``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` with a realistic hourly load profile. Swap this call for your own data loader when you're ready.
- **Step 2 — Model** ``ForecastingModel`` is a pipeline that chains preprocessing, a forecaster, and optional postprocessing. ``ConstantMedianForecaster`` is a fast, dependency-free baseline.
- **Step 3 — Train** ``model.fit()`` runs the full pipeline and returns a ``ModelFitResult`` containing train/validation metrics.
- **Step 4 — Forecast** ``model.predict()`` returns a ``ForecastDataset`` whose ``.data`` attribute is a standard ``pandas.DataFrame``.
- **Step 5 — Persist** ``LocalModelStorage`` saves a versioned snapshot to disk so the model can be reloaded later.

.. note::

   ``ConstantMedianForecaster`` is intentionally simple — it predicts the historical median for each horizon. It is a useful sanity-check baseline, not a production forecaster. See :doc:`first_forecast` for guidance on choosing a more capable model.

Visualising the Forecast
------------------------

OpenSTEF ships with an interactive plotter in ``openstef-beam``. Add the following lines after Step 4:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   fig = plotter.plot(
       forecast=forecast,
       measurements=data_forecast,
       model_name="ConstantMedian baseline",
   )
   fig.show()   # opens an interactive Plotly chart in your browser

The chart overlays the forecast against the actual measurements and renders uncertainty bands when quantile predictions are available.

Next Steps
----------

Now that you have a working forecast, the natural next steps are:

- :doc:`first_forecast` — the same workflow explained step by step, including how to bring in real data and choose a production-grade forecaster.
- :doc:`backtesting` — evaluate your model rigorously by replaying it over historical data.
- :doc:`advanced_customization` — build custom preprocessors, forecasters, and postprocessors to fit your specific use case.