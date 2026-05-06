Quickstart
==========

This page gets you to a working forecast in under five minutes. No background theory, no configuration deep-dives — just copy, paste, and run. If you want explanations of what each step does, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. mermaid:: /diagrams/getting_started/quickstart_diagram_1.mmd

Prerequisites
-------------

OpenSTEF installed and importable. If not, follow :doc:`installation` first, then come back here.

.. code-block:: python

   import openstef_models  # should import without error

The Minimal Example
-------------------

The following block is self-contained. It generates synthetic load data, trains a model, and produces a forecast.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.datasets.testing import create_synthetic_forecasting_dataset
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )

   # 1. Generate synthetic training data (nine months, hourly resolution)
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),
       sample_interval=timedelta(hours=1),
   )

   # 2. Configure the preset workflow
   config = ForecastingWorkflowConfig(
       model_id="quickstart-model",
       model="lgbm",
       sample_interval=timedelta(hours=1),
   )

   # 3. Build the workflow
   workflow = create_forecasting_workflow(config)

   # 4. Fit on the dataset
   workflow.fit(dataset)

   # 5. Predict — returns a TimeSeriesDataset containing the forecast
   forecast = workflow.predict(dataset)

   print(forecast)

.. note:: [VISUALIZATION: Example forecast output — a time series plot showing observed load values alongside the predicted median and uncertainty bands for the forecast horizon]

That's it. ``forecast`` is a ``TimeSeriesDataset`` containing the predicted load values for the configured horizons.

Choosing a Model
----------------

Swap the ``model`` field to try a different algorithm. All options accept the same ``fit`` / ``predict`` interface:

.. code-block:: python

   # LightGBM (default recommendation)
   config = ForecastingWorkflowConfig(model_id="my-model", model="lgbm", ...)

   # XGBoost
   config = ForecastingWorkflowConfig(model_id="my-model", model="xgboost", ...)

   # Linear gradient boosting — useful as a fast baseline
   config = ForecastingWorkflowConfig(model_id="my-model", model="gblinear", ...)

Adding Probabilistic Forecasts
-------------------------------

Pass a list of quantiles to get prediction intervals alongside the median:

.. code-block:: python

   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="quickstart-model",
       model="lgbm",
       sample_interval=timedelta(hours=1),
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

The output dataset will contain columns for each requested quantile.

Using Real Data
---------------

Replace ``create_synthetic_forecasting_dataset`` with your own ``TimeSeriesDataset``. The only requirement is that the dataset contains a target load column and a datetime index at the resolution you configured in ``sample_interval``:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   df = pd.read_csv("my_load_data.csv", index_col="timestamp", parse_dates=True)

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1),
   )

   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

.. note::

   The column name for the load target defaults to ``"load"``. If your data uses a different column name, set ``target_column`` in ``ForecastingWorkflowConfig``.

What's Next
-----------

- :doc:`first_forecast` — the same workflow with step-by-step explanations of every decision.
- :doc:`backtesting` — evaluate your model on historical data before deploying it.
- :doc:`advanced_customization` — replace or extend individual pipeline components.