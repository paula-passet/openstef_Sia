Quickstart
==========

Get a forecast running in under five minutes. This page gives you a single, copy-paste script that trains a model on synthetic data and produces a forecast. There are no explanations of the underlying mechanics — see :doc:`first_forecast` for that.

.. note:: [DIAGRAM: Simple linear workflow: Configure ForecastingWorkflowConfig → create_forecasting_workflow() → workflow.fit(dataset) → workflow.predict(dataset) → ForecastDataset output]

Prerequisites
-------------

OpenSTEF must be installed before running the code below. If you have not done that yet, see :doc:`installation`.

.. code-block:: python

   pip install openstef-models

The Minimal Script
------------------

The following script is self-contained. It generates synthetic load data, trains an XGBoost forecasting model, and prints the resulting forecast.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.datasets.synthetic import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # 1. Generate synthetic training data (9 months, hourly resolution)
   dataset = create_synthetic_forecasting_dataset(
       sample_interval=timedelta(hours=1),
   )

   # 2. Configure the preset workflow
   config = ForecastingWorkflowConfig(
       model_id="quickstart-model",
       model="xgboost",
       sample_interval=timedelta(hours=1),
       horizons=[LeadTime.from_string("PT24H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   # 3. Create the workflow from config
   workflow = create_forecasting_workflow(config)

   # 4. Fit the model
   workflow.fit(dataset)

   # 5. Predict
   forecast = workflow.predict(dataset)

   print(forecast)

Run it with:

.. code-block:: bash

   python quickstart.py

You should see a ``ForecastDataset`` printed to the terminal containing quantile columns (``q0.1``, ``q0.5``, ``q0.9``) indexed by timestamp.

.. note:: [VISUALIZATION: Example terminal output showing a ForecastDataset DataFrame with datetime index and three quantile columns of numeric load values]

What Each Step Does
-------------------

The script follows four fixed steps that every OpenSTEF workflow uses:

- **Configure** — ``ForecastingWorkflowConfig`` holds every setting: model type, forecast horizon, quantiles, and sample resolution. The ``model_id`` is a free-form string you use to identify the model later.
- **Create** — ``create_forecasting_workflow()`` assembles the full pipeline (feature engineering, model, post-processing) from the config.
- **Fit** — ``workflow.fit()`` trains the model on the ``TimeSeriesDataset`` you pass in.
- **Predict** — ``workflow.predict()`` returns a ``ForecastDataset`` with one column per quantile for the configured horizon.

Changing the Model
------------------

Swap ``model="xgboost"`` for any of the built-in options:

.. code-block:: python

   # Available: "xgboost", "lgbm", "gblinear", "lgbmlinear", "median", "flatliner"
   config = ForecastingWorkflowConfig(
       model_id="quickstart-lgbm",
       model="lgbm",
       sample_interval=timedelta(hours=1),
       horizons=[LeadTime.from_string("PT24H")],
       quantiles=[Q(0.5)],
   )

``"median"`` and ``"flatliner"`` require no training and are useful as baselines.

Changing the Horizon
--------------------

``horizons`` accepts any ISO 8601 duration string:

.. code-block:: python

   horizons=[LeadTime.from_string("PT48H")]   # 48-hour ahead forecast
   horizons=[LeadTime.from_string("PT1H")]    # 1-hour ahead forecast

.. note::

   Each entry in ``horizons`` produces a separate set of predictions. The list currently accepts exactly one horizon per workflow. To forecast multiple horizons, create one workflow per horizon.

Adding a Location
-----------------

Holiday features and other location-aware transforms are enabled by providing a ``LocationConfig``:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_models.workflows.custom_forecasting_workflow import LocationConfig

   config = ForecastingWorkflowConfig(
       model_id="quickstart-nl",
       model="xgboost",
       sample_interval=timedelta(hours=1),
       horizons=[LeadTime.from_string("PT24H")],
       quantiles=[Q(0.5)],
       location=LocationConfig(
           name="Amsterdam",
           country_code="NL",
       ),
   )

The default location is already set to the Netherlands (``NL``), so this step is optional for the quickstart.

Using Your Own Data
-------------------

Replace ``create_synthetic_forecasting_dataset()`` with a ``TimeSeriesDataset`` built from your own ``pandas.DataFrame``:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset

   df = pd.read_csv("load.csv", index_col=0, parse_dates=True)
   # DataFrame must have a DatetimeIndex and at least one numeric column (the target)

   dataset = TimeSeriesDataset(data=df, target_column="load_mw")

The target column is the series the model will learn to forecast. All other columns are treated as features.

.. note::

   Your ``DataFrame`` index must be timezone-aware. Add a timezone if it is not:

   .. code-block:: python

      df.index = df.index.tz_localize("UTC")

Next Steps
----------

This page covered the shortest possible path to a working forecast. When you are ready to go further:

- :doc:`first_forecast` — walks through the same workflow step by step, explaining each decision.
- :doc:`backtesting` — evaluate your trained model on historical data before deploying it.
- :doc:`advanced_customization` — replace built-in transforms, add callbacks, or plug in a custom model.