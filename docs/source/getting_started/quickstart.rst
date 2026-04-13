Quickstart
==========

This page gets you to a working forecast in the shortest possible time. No theory, no explanations — just copy, paste, and run. If you want to understand *why* things work the way they do, see :doc:`first_forecast`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF must be installed before running the examples below. If you haven't done that yet, see :doc:`installation`.

.. code-block:: python

   pip install openstef-core openstef-models

Minimal Working Example
-----------------------

The following script trains a forecaster on synthetic hourly load data and produces a 24-hour-ahead quantile forecast. Every line is required — nothing here is optional boilerplate.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )

   # ── 1. Load data ──────────────────────────────────────────────────────────
   rng = np.random.default_rng(42)
   n = 24 * 90  # 90 days of hourly readings

   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {
               "load": rng.standard_normal(size=n) * 10 + 50,
               "temperature": rng.standard_normal(size=n) * 5 + 15,
           },
           index=pd.date_range("2025-01-01", periods=n, freq="h"),
       ),
       sample_interval=timedelta(hours=1),
   )

   # ── 2. Create model ───────────────────────────────────────────────────────
   horizons = [LeadTime.from_string("PT24H")]

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       )
   )

   # ── 3. Train ──────────────────────────────────────────────────────────────
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart_model")
   workflow.fit(dataset)

   # ── 4. Forecast ───────────────────────────────────────────────────────────
   forecasts = workflow.predict(dataset)

   # ── 5. Inspect output ─────────────────────────────────────────────────────
   print(forecasts.data.head())

Run this script and you will see a DataFrame printed to stdout with one row per forecast timestamp and one column per quantile (``q0.1``, ``q0.5``, ``q0.9``).

.. note::

   ``ConstantMedianForecaster`` is a baseline model that predicts historical quantile values as constants. It is ideal for getting the pipeline working quickly. Swap it for a gradient-boosting or neural-network forecaster when you are ready — the rest of the code stays the same. See :doc:`first_forecast` for guidance on choosing a production-grade model.

Understanding the Output
------------------------

``forecasts.data`` is a ``pandas.DataFrame`` indexed by timestamp. Each column corresponds to one of the quantiles you requested:

.. code-block:: python

   print(forecasts.data.columns.tolist())
   # ['q0.1', 'q0.5', 'q0.9']

   print(forecasts.data.index[:3])
   # DatetimeIndex(['2025-04-01 00:00:00', '2025-04-01 01:00:00', ...], dtype='datetime64[ns]', freq='h')

The ``q0.5`` column is the median (point) forecast. The ``q0.1`` and ``q0.9`` columns form a prediction interval.

Using Your Own Data
-------------------

Replace the synthetic DataFrame with your own measurements. The only hard requirements are:

- The DataFrame index must be a ``pandas.DatetimeIndex`` with a **uniform frequency**.
- There must be a column named ``load`` (or whichever column you designate as the target).
- Additional columns are treated as exogenous features and passed to the model automatically.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Load from a CSV that has a 'timestamp' column and a 'load' column
   df = pd.read_csv("my_measurements.csv", parse_dates=["timestamp"])
   df = df.set_index("timestamp").sort_index()

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1),  # match your data's actual frequency
   )

.. warning::

   ``TimeSeriesDataset`` validates that the index is uniformly spaced. If your data contains gaps or duplicate timestamps, clean it before constructing the dataset or you will receive a validation error.

Saving and Reloading a Trained Model
-------------------------------------

To persist a trained workflow to disk and reload it later, use ``LocalModelStorage``:

.. code-block:: python

   from pathlib import Path
   from openstef_models.storage.local_model_storage import LocalModelStorage

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save after training
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="quickstart_model",
       storage=storage,
   )
   workflow.fit(dataset)
   # The workflow saves automatically on fit when storage is provided.

   # Reload and predict later
   loaded_workflow = CustomForecastingWorkflow.from_storage(
       model_id="quickstart_model",
       storage=storage,
   )
   forecasts = loaded_workflow.predict(dataset)

Next Steps
----------

You now have a working end-to-end forecast. From here:

- :doc:`first_forecast` — walks through the same pipeline step by step, explaining every decision.
- :doc:`backtesting` — shows how to evaluate forecast quality on historical data.
- :doc:`advanced_customization` — covers custom forecasters, preprocessing pipelines, and feature engineering.