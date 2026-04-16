Quickstart
==========

Get from zero to a working energy forecast in under five minutes. This page gives you a single, copy-paste-ready script — no background theory, no configuration deep-dives. If you want explanations of *why* each step works, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF and its core packages must be installed before running the example below. If you have not done this yet, follow :doc:`installation` first, then come back here.

The Minimal Example
-------------------

The script below uses OpenSTEF's built-in synthetic dataset generator so you do not need any external data files. It trains a gradient-boosted linear forecaster on nine months of synthetic hourly load data and produces a probabilistic forecast with 10th, 50th, and 90th percentile outputs.

.. code-block:: python

    # SPDX-License-Identifier: MPL-2.0
    import logging
    from datetime import timedelta

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    # ── 1. Load data ──────────────────────────────────────────────────────────────
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=270),          # ~9 months of hourly data
        sample_interval=timedelta(hours=1),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
    )

    # ── 2. Create the forecasting workflow ────────────────────────────────────────
    workflow = create_forecasting_workflow(
        config=ForecastingWorkflowConfig(
            model_id="my_first_forecast",
            model="gblinear",                # gradient-boosted linear model
            horizons=[LeadTime.from_string("PT36H")],   # 36-hour ahead forecast
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],         # 10th / median / 90th
            mlflow_storage=None,             # disable experiment tracking for now
        )
    )

    # ── 3. Train ──────────────────────────────────────────────────────────────────
    result = workflow.fit(dataset)

    if result is not None:
        print("\n── Training metrics ──")
        print(result.metrics_full.to_dataframe())

    # ── 4. Forecast ───────────────────────────────────────────────────────────────
    forecast = workflow.predict(dataset)

    # ── 5. Inspect output ─────────────────────────────────────────────────────────
    print("\n── Forecast (last 5 rows) ──")
    print(forecast.data.tail())

    print("\n── Median series (last 5 rows) ──")
    print(forecast.median_series.tail())

Run it with:

.. code-block:: bash

    python quickstart.py

You should see training metrics printed to the console followed by a table of probabilistic forecast values.

Understanding the Output
------------------------

The ``forecast`` object is a ``ForecastDataset``. Its most useful attributes are:

- ``forecast.data`` — a ``pandas.DataFrame`` with one column per requested quantile (e.g. ``quantile_P10``, ``quantile_P50``, ``quantile_P90``).
- ``forecast.median_series`` — a convenience ``pandas.Series`` for the P50 (median) prediction.
- ``forecast.quantiles_data`` — a dictionary mapping each quantile to its corresponding series.

Visualising the Forecast
------------------------

OpenSTEF ships a built-in plotter that produces an interactive HTML chart. Add these lines after the ``workflow.predict`` call:

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
    print("Chart saved to forecast_plot.html")

Open ``forecast_plot.html`` in any browser to see the measured load overlaid with the forecast band.

.. note::

   ``mlflow_storage=None`` disables experiment tracking, which keeps this example self-contained. When you move to production you will want to pass a real ``MLFlowStorage`` instance so that trained models are persisted and can be reloaded for prediction without retraining. See :doc:`first_forecast` for a full walkthrough of that setup.

What Just Happened
------------------

In roughly 30 lines of code the library:

- Generated a synthetic hourly load time series with weather influences.
- Configured a full preprocessing → forecasting → postprocessing pipeline.
- Trained a gradient-boosted linear model with automatic feature engineering (lag features, holiday indicators, data scaling).
- Produced a 36-hour probabilistic forecast at three quantile levels.

Next Steps
----------

- :doc:`first_forecast` — the same workflow explained step by step, with real data loading, MLflow tracking, and model persistence.
- :doc:`backtesting` — evaluate forecast accuracy by replaying the model over historical periods.
- :doc:`advanced_customization` — swap in custom forecasters, feature pipelines, and postprocessing transforms.