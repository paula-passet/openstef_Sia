Quick Start
===========

Get up and running with OpenSTEF in minutes. This guide shows you how to train your first model and create a forecast using the OpenSTEF Python library.

Installation
------------

Install OpenSTEF from PyPI::

   pip install openstef

Train a Model and Create a Forecast
-----------------------------------

Here's a complete example that trains a model and generates a forecast::

   import pandas as pd
   import numpy as np
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core

   # Create sample data (replace with your actual data)
   dates = pd.date_range('2023-01-01', periods=2000, freq='15T')
   data = pd.DataFrame({
       'load': np.sin(dates.hour / 24 * np.pi) * 100 + np.random.normal(0, 10, len(dates)),
       'temperature': np.sin(dates.hour / 24 * np.pi) * 20 + np.random.normal(0, 5, len(dates)),
       'radiation': np.maximum(0, np.sin(dates.hour / 24 * np.pi) * 500 + np.random.normal(0, 50, len(dates)))
   }, index=dates)

   # Split data for training and forecasting
   train_data = data[:-96]  # All but last 24 hours
   forecast_data = data[-96:]  # Last 24 hours

   # Create prediction job configuration
   pj = PredictionJobDataClass(
       id=1,
       name="example_forecast",
       model="xgb",
       lat=52.0,
       lon=5.0,
       forecast_type="demand"
   )

   # Create model specifications
   model_specs = ModelSpecificationDataClass(
       id=1,
       model_config={}
   )

   # Train the model
   trained_model = train_model_pipeline_core(
       pj=pj,
       model_specs=model_specs,
       input_data=train_data
   )

   # Create forecast
   forecast = create_forecast_pipeline_core(
       pj=pj,
       input_data=forecast_data,
       model=trained_model,
       model_specs=model_specs
   )

   print("Forecast created!")
   print(forecast.head())

What Happens Here
-----------------

1. **Data Preparation**: We create sample time series data with load, temperature, and radiation columns
2. **Configuration**: We define a prediction job that specifies the model type and location
3. **Training**: The ``train_model_pipeline_core`` function trains an XGBoost model on historical data
4. **Forecasting**: The ``create_forecast_pipeline_core`` function generates predictions with confidence intervals

Your forecast DataFrame will contain columns for predicted values and confidence intervals for multiple horizons.

Next Steps
----------

This minimal example gets you started quickly. For production use, you'll want to:

- Use real historical load and weather data
- Explore different model types and hyperparameters
- Set up proper data validation and error handling
- Consider the comprehensive tutorials for detailed workflows

For specific use cases like congestion forecasting or grid loss prediction, see the use cases guide.