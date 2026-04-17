Quickstart
==========

This page gets you to a working forecast in under five minutes. No background theory — just copy, paste, and run. For step-by-step explanations see :doc:`first_forecast`, and for customising the workflow see :doc:`advanced_customization`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF must be installed before running the examples below. See :doc:`installation` if you have not done this yet.

.. code-block:: python

   pip install openstef-models

Minimal Working Example
-----------------------

The following script generates synthetic load data, trains a model, and produces a 24-hour ahead forecast. Every line is required — nothing is optional here.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   # ── 1. Build synthetic training data ────────────────────────────────────────
   rng = np.random.default_rng(42)
   train_index = pd.date_range("2024-01-01", periods=8 * 24 * 7, freq="15min")  # 7 days

   train_df = pd.DataFrame(
       {
           "load": 200 + 50 * np.sin(2 * np.pi * train_index.hour / 24)
                   + rng.normal(0, 5, len(train_index)),
           "temperature": 10 + 5 * np.sin(2 * np.pi * train_index.dayofyear / 365)
                          + rng.normal(0, 1, len(train_index)),
       },
       index=train_index,
   )

   train_dataset = TimeSeriesDataset(
       data=train_df,
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

   # ── 2. Configure the preset workflow ────────────────────────────────────────
   config = ForecastingWorkflowConfig(
       model_id="quickstart-demo",
       model="xgboost",
       sample_interval=timedelta(minutes=15),
       quantiles=[0.1, 0.5, 0.9],
   )

   workflow = create_forecasting_workflow(config)

   # ── 3. Fit ───────────────────────────────────────────────────────────────────
   workflow.fit(train_dataset)

   # ── 4. Predict ───────────────────────────────────────────────────────────────
   forecast_start = train_index[-1] + timedelta(minutes=15)
   predict_index = pd.date_range(forecast_start, periods=96, freq="15min")  # 24 h

   predict_df = pd.DataFrame(
       {
           "load": np.nan,  # target is unknown at forecast time
           "temperature": 10 + rng.normal(0, 1, len(predict_index)),
       },
       index=predict_index,
   )

   predict_dataset = TimeSeriesDataset(
       data=predict_df,
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

   forecast = workflow.predict(predict_dataset)
   print(forecast.data.head())

.. note:: [VISUALIZATION: Line chart showing the synthetic training load series followed by the 24-hour probabilistic forecast band (p10, p50, p90 quantiles)]

The ``forecast`` object is a ``ForecastDataset``. Its ``.data`` attribute is a ``pandas.DataFrame`` with one column per requested quantile.

Key Parameters
--------------

The two objects you always configure are ``ForecastingWorkflowConfig`` and ``TimeSeriesDataset``.

**ForecastingWorkflowConfig**

- ``model_id`` — a string that uniquely identifies this workflow; used for logging and model storage.
- ``model`` — the underlying estimator. Choices: ``"xgboost"``, ``"lgbm"``, ``"gblinear"``, ``"lgbmlinear"``, ``"median"``, ``"flatliner"``.
- ``sample_interval`` — the cadence of your time series as a ``timedelta``. Must match the actual data frequency.
- ``quantiles`` — list of quantile levels to forecast. Use ``[0.5]`` for a point forecast only.

**TimeSeriesDataset**

- ``data`` — a ``pandas.DataFrame`` with a ``DatetimeIndex``.
- ``sample_interval`` — must match the config value.
- ``target_column`` — name of the column to forecast (default ``"load"``).

.. note::

   ``sample_interval`` must be identical in both the config and every dataset you pass to the workflow. A mismatch raises a validation error at fit time.

Switching the Model
-------------------

Swap ``"xgboost"`` for any supported estimator without changing anything else:

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model_id="quickstart-lgbm",
       model="lgbm",
       sample_interval=timedelta(minutes=15),
       quantiles=[0.1, 0.5, 0.9],
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(train_dataset)
   forecast = workflow.predict(predict_dataset)

Adding Location Metadata
------------------------

If your features include holiday indicators or location-aware transforms, attach a ``LocationConfig``:

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import LocationConfig, ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="quickstart-nl",
       model="xgboost",
       sample_interval=timedelta(minutes=15),
       quantiles=[0.5],
       location=LocationConfig(
           name="Amsterdam",
           country_code="NL",
       ),
   )

Holiday features are then generated automatically during fit and predict.

What's Next
-----------

- :doc:`first_forecast` — the same workflow explained step by step, with commentary on each decision.
- :doc:`backtesting` — evaluate your model on historical data before deploying it.
- :doc:`advanced_customization` — replace or extend individual transforms, add custom features, and tune hyperparameters.