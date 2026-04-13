Quickstart
==========

Get your first OpenSTEF forecast running in under five minutes. This page gives you a single, copy-paste-ready script — no background theory, no deep-dives. Once it runs, head to :doc:`first_forecast` for a step-by-step walkthrough of what each piece does.

.. note:: [DIAGRAM: Linear workflow — (1) Create synthetic data → (2) Define ForecastingModel → (3) Wrap in CustomForecastingWorkflow → (4) Call workflow.fit() → (5) Call workflow.predict() → (6) Inspect ForecastDataset output]

Prerequisites
-------------

Make sure OpenSTEF is installed before running the example below. See :doc:`installation` if you haven't done this yet.

.. code-block:: python

   pip install openstef

Minimal Working Example
-----------------------

The script below trains a median-based forecaster on synthetic hourly load data and produces a 24-hour-ahead probabilistic forecast. Copy it into a file or notebook and run it as-is.

.. code-block:: python

   # SPDX-FileCopyrightText: 2025 Contributors to the OpenSTEF project
   # SPDX-License-Identifier: MPL-2.0

   from datetime import timedelta

   import numpy as np
   import pandas as pd

   from openstef_models.data.time_series_dataset import TimeSeriesDataset
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow,
   )
   from openstef_models.types import LeadTime, Q

   # ------------------------------------------------------------------
   # 1. Create synthetic time series data
   # ------------------------------------------------------------------
   rng = np.random.default_rng(42)
   n_samples = 24 * 90  # 90 days of hourly observations

   timestamps = pd.date_range("2025-01-01", periods=n_samples, freq="h")

   temp = rng.standard_normal(size=n_samples)
   wind = rng.standard_normal(size=n_samples)

   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {
               "load": wind * -10 + temp * -3 + rng.standard_normal(size=n_samples) * 2,
               "temperature": temp,
               "wind": wind,
           },
           index=timestamps,
       ),
       sample_interval=timedelta(hours=1),
   )

   # ------------------------------------------------------------------
   # 2. Define the forecasting model
   # ------------------------------------------------------------------
   horizons = [LeadTime.from_string("PT24H")]

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       ),
       target_column="load",
   )

   # ------------------------------------------------------------------
   # 3. Create a workflow and train
   # ------------------------------------------------------------------
   workflow = CustomForecastingWorkflow(model=model, model_id="quickstart_model")

   fit_result = workflow.fit(dataset)
   print("Training complete:", fit_result)

   # ------------------------------------------------------------------
   # 4. Generate forecasts
   # ------------------------------------------------------------------
   forecasts = workflow.predict(dataset)

   # ------------------------------------------------------------------
   # 5. Inspect the output
   # ------------------------------------------------------------------
   print(forecasts.data.head())

Running the script produces a ``ForecastDataset`` whose ``.data`` attribute is a ``DataFrame`` indexed by forecast timestamp. Each row contains the predicted quantiles — ``quantile_P10``, ``quantile_P50``, and ``quantile_P90`` — for the 24-hour-ahead horizon.

Expected Output
---------------

After a successful run you should see output similar to the following:

.. code-block:: text

   Training complete: ModelFitResult(...)

                        quantile_P10  quantile_P50  quantile_P90
   2025-04-01 00:00:00     -18.34        -9.87         -1.42
   2025-04-01 01:00:00     -17.91       -10.12         -2.03
   2025-04-01 02:00:00     -19.05        -9.55         -1.88
   2025-04-01 03:00:00     -18.62       -10.34         -2.17
   2025-04-01 04:00:00     -17.78        -9.71         -1.55

The three quantile columns represent the lower bound, median, and upper bound of the probabilistic forecast respectively.

.. note::

   ``ConstantMedianForecaster`` is a lightweight baseline model — it predicts the historical median for each horizon. It is ideal for verifying your setup. For production-grade forecasts, replace it with a gradient-boosted or neural-network forecaster. See :doc:`first_forecast` for guidance on choosing a model.

What Just Happened
------------------

In five steps the script exercised the core OpenSTEF library pattern:

- **Data** — ``TimeSeriesDataset`` wraps a ``pandas.DataFrame`` together with a ``sample_interval``, giving the library the context it needs to compute lag features and horizon offsets correctly.
- **Model** — ``ForecastingModel`` is a pipeline that combines a preprocessing stage with a ``forecaster``. Here no explicit preprocessing is configured, so the data passes through unchanged.
- **Workflow** — ``CustomForecastingWorkflow`` orchestrates ``fit`` and ``predict`` calls, manages model identity via ``model_id``, and provides hooks for callbacks such as logging and storage.
- **Output** — ``workflow.predict()`` returns a ``ForecastDataset``. Access the underlying ``DataFrame`` via ``.data``.

Next Steps
----------

Now that the library is working on your machine, the following pages take you deeper:

- :doc:`first_forecast` — the same workflow explained step by step, with real data loading, feature engineering, and model selection.
- :doc:`backtesting` — evaluate forecast accuracy over a historical period before deploying a model.
- :doc:`advanced_customization` — swap in custom forecasters, write your own preprocessing transforms, and configure model storage backends.