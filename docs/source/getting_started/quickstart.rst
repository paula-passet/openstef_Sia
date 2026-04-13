Quickstart
==========

Get your first forecast running in under five minutes. This page is a single, copy-paste-ready script — no explanations of the underlying concepts. For the full walkthrough, see :doc:`first_forecast`.

.. note:: [DIAGRAM: Simple linear workflow — Data Loading → Model Creation → Training → Forecasting → Output (forecasts DataFrame)]

Prerequisites
-------------

OpenSTEF must be installed before running the code below. See :doc:`installation` if you have not done this yet.

.. code-block:: python

   pip install openstef-models

The Complete Script
-------------------

Copy the block below into a file (e.g. ``my_first_forecast.py``) and run it with ``python my_first_forecast.py``.

.. code-block:: python

   # SPDX-License-Identifier: MPL-2.0
   from datetime import timedelta

   import numpy as np
   import pandas as pd

   from openstef_core.types import LeadTime, Q
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.workflows import CustomForecastingWorkflow
   from openstef_core.datasets import TimeSeriesDataset

   # ── 1. Create sample data ──────────────────────────────────────────────────
   rng = np.random.default_rng(42)
   n_samples = 24 * 90  # 90 days of hourly readings

   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h")
   load = (
       rng.standard_normal(n_samples) * 5        # noise
       + np.sin(np.arange(n_samples) * 2 * np.pi / 24) * 10  # daily cycle
       + 50                                       # baseline
   )

   dataset = TimeSeriesDataset(
       data=pd.DataFrame({"load": load}, index=timestamps),
       sample_interval=timedelta(hours=1),
   )

   # ── 2. Create the model ────────────────────────────────────────────────────
   horizon = LeadTime.from_string("PT24H")   # forecast 24 hours ahead

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=[horizon],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # 10th / median / 90th percentile
       ),
       target_column="load",
   )

   # ── 3. Train ───────────────────────────────────────────────────────────────
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart")
   workflow.fit(dataset)

   # ── 4. Forecast ────────────────────────────────────────────────────────────
   forecasts = workflow.predict(dataset)

   # ── 5. Inspect the output ──────────────────────────────────────────────────
   print(forecasts.data.head())

Running the script prints a DataFrame with one row per forecast timestamp and one column per quantile:

.. code-block:: text

   timestamp            q0.1       q0.5       q0.9
   2025-04-01 00:00:00  44.83      50.01      55.19
   2025-04-01 01:00:00  44.83      50.01      55.19
   ...

What Each Step Does (in brief)
-------------------------------

- **TimeSeriesDataset** — wraps a ``pandas.DataFrame`` with a datetime index and a ``sample_interval`` so OpenSTEF knows the data resolution.
- **LeadTime** — specifies how far ahead to forecast (ISO 8601 duration string, e.g. ``"PT24H"`` = 24 hours).
- **Q** — declares a quantile level. ``Q(0.5)`` is the median; ``Q(0.1)`` / ``Q(0.9)`` give a prediction interval.
- **ForecastingModel** — the pipeline object that owns preprocessing, a forecaster, and postprocessing.
- **ConstantMedianForecaster** — a simple, always-fitted baseline forecaster; ideal for smoke-testing your setup.
- **CustomForecastingWorkflow** — orchestrates ``fit`` and ``predict`` calls against a named model.

.. note::

   ``ConstantMedianForecaster`` is intentionally trivial — it predicts the historical median for each quantile. Swap it for ``GBLinearForecaster`` or ``XGBForecaster`` once your pipeline is working. See :doc:`first_forecast` for guidance on choosing a forecaster.

Switching to a Real Forecaster
-------------------------------

Replace the ``ConstantMedianForecaster`` block with a gradient-boosted model and add feature preprocessing:

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_core.transforms import Scaler
   from openstef_models.models.forecasting.gb_linear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(method="standard"),
           ]
       ),
       forecaster=GBLinearForecaster(
           horizons=[LeadTime.from_string("PT24H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=GBLinearHyperParams(n_steps=500, learning_rate=0.1),
       ),
       target_column="load",
   )

Everything else in the script stays the same — ``CustomForecastingWorkflow.fit`` and ``predict`` have an identical interface regardless of which forecaster is inside the model.

.. note::

   Training a gradient-boosted model on 90 days of hourly data takes a few seconds on a modern laptop. For production use you will want more history and additional weather features. See :doc:`first_forecast` for a data-preparation guide.

Next Steps
----------

- :doc:`first_forecast` — the same workflow explained step-by-step, with real weather features and data validation.
- :doc:`backtesting` — evaluate forecast accuracy against held-out history before deploying.
- :doc:`advanced_customization` — write custom forecasters, transforms, and callbacks.