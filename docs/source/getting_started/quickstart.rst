Quick Start
===========


Quick Start
===========


This page will get you up and running with OpenSTEF in just a few minutes. OpenSTEF is a Python library that provides all the components needed for the machine learning pipeline to create short-term energy forecasts. Whether you're new to forecasting or an experienced data scientist, this quick start guide demonstrates the fastest path to generating your first forecasts using the OpenSTEF library's core functionality.


Prerequisites
-------------


- Python 3.8 or higher

- pip install openstef


.. code-block:: bash

   pip install openstef


30-Second Forecast
------------------


Here's a complete example that demonstrates the entire OpenSTEF workflow from data preparation to forecasting in just a few lines of code. This example shows how to train a model and generate predictions using the library's pipeline functionality:

```python
import pandas as pd
from openstef.pipeline.train_model import train_model_pipeline
from openstef.pipeline.create_forecast import create_forecast_pipeline

# Load your energy load and weather data
load_data = pd.read_csv('energy_loads.csv', index_col=0, parse_dates=True)
weather_data = pd.read_csv('weather_data.csv', index_col=0, parse_dates=True)

# Combine datasets
input_data = pd.concat([load_data, weather_data], axis=1)

# Define prediction job configuration
pj = {
    'id': 123,
    'name': 'solar_forecast_example',
    'model': 'xgb',
    'horizon_minutes': 2880,  # 48 hours
    'resolution_minutes': 15,
    'feature_names': ['load', 'temp', 'windspeed_100m', 'radiation']
}

# Train the model
trained_model = train_model_pipeline(pj, input_data)

# Create forecast
forecast = create_forecast_pipeline(pj, input_data, trained_model)
```

This example demonstrates OpenSTEF's core capability: combining input data preparation, feature engineering, model training, and multi-horizon forecasting in a streamlined workflow that produces both point predictions and confidence intervals.


.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import TrainModelPipeline
   from openstef.pipeline.create_forecast import CreateForecastPipeline
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Create sample training data
   train_data = pd.DataFrame({
       'load': [100, 120, 110, 130, 140, 125, 135],
       'temp': [15, 18, 16, 20, 22, 19, 21],
       'humidity': [60, 65, 62, 70, 68, 66, 72],
       'wind_speed': [5, 8, 6, 10, 12, 9, 11]
   }, index=pd.date_range('2024-01-01', periods=7, freq='H'))

   # Create prediction job configuration
   pj = PredictionJobDataClass(
       id=1,
       name="sample_forecast",
       model="xgb",
       horizon_minutes=60,
       resolution_minutes=15,
       train_components=0.95,
       feature_names=["temp", "humidity", "wind_speed"]
   )

   # Train the model
   train_pipeline = TrainModelPipeline()
   model = train_pipeline.run(pj, train_data)

   # Create forecast data (next hour)
   forecast_data = pd.DataFrame({
       'temp': [23],
       'humidity': [70],
       'wind_speed': [8]
   }, index=pd.date_range('2024-01-01 07:00', periods=1, freq='H'))

   # Generate forecast
   forecast_pipeline = CreateForecastPipeline()
   forecast = forecast_pipeline.run(pj, forecast_data, model)

   print("Forecast:")
   print(forecast)


You just created a complete machine learning forecast using OpenSTEF's pipeline system. The library automatically handled feature engineering (creating relevant input features from your data), trained an XGBoost model optimized for energy forecasting, and generated predictions with confidence intervals. OpenSTEF's single-shot, multi-horizon approach means you got forecasts for multiple time steps ahead in one operation, while the built-in data validation ensured your input data met quality standards before processing.


Understanding the Output
------------------------


OpenSTEF forecast functions return pandas DataFrames with datetime indices and forecast values. The output typically includes multiple columns representing different quantile predictions (e.g., 0.1, 0.5, 0.9) that capture forecast uncertainty, where the 0.5 quantile represents the median prediction. When quantile predictions are enabled, you'll receive a DataFrame where each column corresponds to a specific quantile level, allowing you to assess both the expected forecast value and the prediction intervals. The structure follows a standard format with datetime as the index and forecast values organized by quantile, making it easy to visualize uncertainty bands and analyze forecast reliability across different confidence levels.


.. code-block:: python

   # Access forecast results from a prediction
   forecast_result = forecast_pipeline.predict(input_data)

   # The forecast returns a pandas DataFrame with datetime index
   print("Forecast shape:", forecast_result.shape)
   print("Forecast columns:", forecast_result.columns.tolist())

   # Access the main forecast values (median prediction)
   main_forecast = forecast_result['forecast']
   print("Next 24 hours forecast:")
   print(main_forecast.head(96))  # 96 = 24 hours * 4 (15-min intervals)

   # Access quantile predictions if available
   if 'quantile_0.1' in forecast_result.columns:
       lower_bound = forecast_result['quantile_0.1']
       upper_bound = forecast_result['quantile_0.9']
       print("Uncertainty bands:")
       print(f"Lower bound (10%): {lower_bound.iloc[0]:.2f}")
       print(f"Upper bound (90%): {upper_bound.iloc[0]:.2f}")

   # Get forecast for specific datetime
   specific_time = pd.Timestamp('2024-01-01 12:00:00')
   if specific_time in forecast_result.index:
       forecast_value = forecast_result.loc[specific_time, 'forecast']
       print(f"Forecast for {specific_time}: {forecast_value:.2f}")


Next Steps
----------


This quickstart guide provided a minimal example to get you started with OpenSTEF. For more comprehensive coverage of the library's capabilities, including advanced forecasting techniques, model optimization, feature engineering, and production deployment patterns, explore our detailed tutorials and guides in the following sections. These resources will help you build robust forecasting pipelines tailored to your specific energy forecasting needs.


- Follow the :doc:`../tutorials/first_use` tutorial for a step-by-step walkthrough of creating your first forecast

- Learn about :doc:`../data_preparation/index` to understand how to structure and prepare your data for OpenSTEF

- Explore :doc:`../evaluation/index` to discover methods for evaluating and improving your forecast models


