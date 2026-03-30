Quickstart
==========

This guide shows you how to train a forecasting model and create your first forecast with OpenSTEF in just a few minutes. If you need more detailed explanations or want to explore advanced features, see the :doc:`tutorials` page.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

This installs the core forecasting functionality. For additional components like backtesting tools, see the full installation guide.

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast. This example uses a simple XGBoost model with default settings.

.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Define the forecasting task
   pj = PredictionJobDataClass(
       id=1,
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],  # 10th, 50th, 90th percentiles
       horizon_minutes=24 * 60,     # 24-hour ahead forecast
       forecast_type="demand",
       lat=52.0,
       lon=5.0,
       resolution_minutes=15,
       name="QuickstartExample",
   )

   # Load your data (CSV with datetime index)
   # Required columns: 'load' (target) + weather features
   input_data = pd.read_csv(
       "your_data.csv",
       parse_dates=True,
       index_col=0
   )

   # Train the model
   train_model_pipeline(
       pj=pj,
       input_data=input_data,
       mlflow_tracking_uri="./mlflow_models"
   )

   # Create a forecast
   # Set recent 'load' values to NaN for the forecast period
   forecast_data = input_data.copy()
   forecast_data.loc[forecast_data.index[-96:], "load"] = np.nan

   # Generate forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=forecast_data,
       mlflow_tracking_uri="./mlflow_models"
   )

   print(forecast.head())

Understanding the Code
^^^^^^^^^^^^^^^^^^^^^^

**PredictionJobDataClass**: Defines your forecasting task. Key parameters:

- ``model``: Machine learning model type (``"xgb"`` for XGBoost, ``"lgb"`` for LightGBM, ``"linear"`` for linear regression)
- ``quantiles``: Confidence intervals for the forecast (0.5 = median prediction)
- ``horizon_minutes``: How far ahead to forecast
- ``resolution_minutes``: Time resolution of your data (typically 15 minutes for energy systems)

**Input Data**: A pandas DataFrame with:

- Datetime index
- ``load`` column: Historical measurements (your target variable)
- Weather features: Temperature, wind speed, radiation, etc.

**Training**: ``train_model_pipeline()`` trains the model and saves it to MLflow for later use.

**Forecasting**: ``create_forecast_pipeline()`` loads the trained model and generates predictions. Set ``load`` to ``NaN`` for periods you want to forecast.

Input Data Format
-----------------

OpenSTEF expects a pandas DataFrame with a datetime index and specific columns:

.. code-block:: python

   # Example data structure
   data = pd.DataFrame({
       "load": [120.5, 135.2, 142.8, ...],           # Target variable (required)
       "temp": [15.2, 16.1, 15.8, ...],              # Temperature (recommended)
       "windspeed_100m": [5.2, 6.1, 4.8, ...],       # Wind speed (recommended)
       "radiation": [200, 350, 450, ...],            # Solar radiation (recommended)
   }, index=pd.date_range("2024-01-01", periods=1000, freq="15min"))

The ``load`` column is required. Weather features are optional but significantly improve forecast accuracy. OpenSTEF automatically generates additional features like hour-of-day, day-of-week, and lagged values.

Quick Evaluation
----------------

Visualize your forecast results:

.. code-block:: python

   import matplotlib.pyplot as plt

   # Compare forecast to actual values
   plt.figure(figsize=(12, 6))
   plt.plot(forecast.index, forecast["forecast"], label="Forecast (median)")
   plt.fill_between(
       forecast.index,
       forecast["quantile_P10"],
       forecast["quantile_P90"],
       alpha=0.3,
       label="80% confidence interval"
   )
   plt.plot(forecast.index, forecast["load"], label="Actual", alpha=0.7)
   plt.legend()
   plt.xlabel("Time")
   plt.ylabel("Load (MW)")
   plt.title("24-Hour Forecast")
   plt.show()

For more sophisticated evaluation including metrics and backtesting, see the :doc:`tutorials` page.

Common Parameters
-----------------

Adjust these parameters in ``PredictionJobDataClass`` to customize your forecast:

- ``model``: Choose ``"xgb"`` (default, best for most cases), ``"lgb"`` (faster training), or ``"linear"`` (interpretable)
- ``quantiles``: Add more quantiles for detailed uncertainty estimates, e.g., ``[0.05, 0.1, 0.5, 0.9, 0.95]``
- ``horizon_minutes``: Forecast horizon (common values: 2880 for 48 hours, 10080 for 7 days)
- ``resolution_minutes``: Match your data's time resolution (typically 15 or 60 minutes)

Next Steps
----------

Now that you've created your first forecast, explore:

- :doc:`tutorials` - Comprehensive examples including backtesting and advanced customization
- :doc:`../guides/use_cases` - Find the right approach for your specific forecasting problem
- :doc:`../reference/concepts` - Understand forecasting concepts like quantiles and model selection
- :doc:`../guides/how_to_guides` - Set up production deployment with orchestration tools

For questions about OpenSTEF's capabilities, check the :doc:`../guides/faq`.