Quickstart
==========

This page gets you to a working forecast in under five minutes. No background theory — just copy, paste, and run. For explanations of what each step does, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

.. note:: [DIAGRAM: Simple linear workflow — configure preset (ForecastingWorkflowConfig) → create workflow (create_forecasting_workflow) → fit on historical data → predict on new data → TimeSeriesDataset output]

Prerequisites
-------------

OpenSTEF installed and importable. If not, follow :doc:`installation` first.

.. code-block:: python

   import openstef_models
   print(openstef_models.__version__)


Complete Example
----------------

The block below is self-contained. Copy it into a script or notebook and run it.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.datasets.testing import create_synthetic_forecasting_dataset
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # 1. Generate synthetic historical data (nine months, hourly)
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=30 * 9),
       sample_interval=timedelta(hours=1),
   )

   # 2. Configure the preset workflow
   config = ForecastingWorkflowConfig(
       model_id="my-first-forecast",
       model="xgboost",
   )

   # 3. Build the workflow
   workflow = create_forecasting_workflow(config)

   # 4. Fit on historical data
   workflow.fit(dataset)

   # 5. Predict — returns a TimeSeriesDataset with the forecast
   forecast = workflow.predict(dataset)

   print(forecast)

.. note:: [VISUALIZATION: Line chart showing the synthetic load time series alongside the model's point forecast for the final 48 hours, with the horizon on the x-axis and load (MW) on the y-axis]

That's it. ``forecast`` is a :class:`~openstef_core.datasets.timeseries_dataset.TimeSeriesDataset` containing the predicted load values.


Changing the Model
------------------

Swap ``model`` in the config to try a different algorithm. Supported values are ``"xgboost"``, ``"lgbm"``, ``"gblinear"``, ``"lgbmlinear"``, ``"median"``, and ``"flatliner"``.

.. code-block:: python

   config = ForecastingWorkflowConfig(
       model_id="lgbm-forecast",
       model="lgbm",
   )
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)


Adding Probabilistic Quantiles
-------------------------------

Pass a ``quantiles`` list to get prediction intervals alongside the median.

.. code-block:: python

   from openstef_core.types import Q

   config = ForecastingWorkflowConfig(
       model_id="probabilistic-forecast",
       model="xgboost",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

The output dataset will contain columns for each requested quantile (``q0.10``, ``q0.50``, ``q0.90``).

.. note:: [VISUALIZATION: Fan chart showing the p10–p90 prediction interval around the p50 median forecast over a 48-hour horizon]


Setting a Location
------------------

``LocationConfig`` adds geographic context used for holiday and daylight features. It is optional but recommended for real data.

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.presets.forecasting_workflow import LocationConfig

   config = ForecastingWorkflowConfig(
       model_id="amsterdam-forecast",
       model="xgboost",
       location=LocationConfig(
           name="Amsterdam substation",
           country_code="NL",
       ),
   )
   workflow = create_forecasting_workflow(config)
   workflow.fit(dataset)
   forecast = workflow.predict(dataset)


Using Your Own Data
-------------------

Replace ``create_synthetic_forecasting_dataset`` with a :class:`~openstef_core.datasets.timeseries_dataset.TimeSeriesDataset` built from a pandas DataFrame. The only hard requirement is a ``load`` target column and a timezone-aware DatetimeIndex at a fixed frequency.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets.timeseries_dataset import TimeSeriesDataset

   df = pd.read_csv("my_load_data.csv", index_col=0, parse_dates=True)
   # df must have a tz-aware index and a "load" column

   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(hours=1),
   )

   workflow.fit(dataset)
   forecast = workflow.predict(dataset)

.. note::

   ``TimeSeriesDataset`` validates frequency consistency on construction. If your
   index has gaps or mixed frequencies, it will raise immediately rather than
   silently producing wrong forecasts.


Next Steps
----------

- :doc:`first_forecast` — the same workflow with step-by-step explanations of every parameter and design decision.
- :doc:`backtesting` — evaluate forecast accuracy on held-out historical periods before deploying.
- :doc:`advanced_customization` — replace individual transforms, add custom features, or plug in your own model class.