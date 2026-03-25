Quick Start Guide
=================


Installation
------------


.. code-block:: bash

   pip install openstef


Prepare Your Data
-----------------


OpenSTEF requires time series data with three essential components: load values representing energy consumption or demand, datetime timestamps for temporal indexing, and weather features for forecasting accuracy. The data should be structured as a pandas DataFrame with datetime index and numeric columns for load and weather variables such as temperature, wind speed, and solar radiation.


.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta

   # Create minimal dataset with required columns
   dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='15T')
   data = pd.DataFrame({
       'datetime': dates,
       'load': 100 + 50 * pd.np.sin(pd.np.arange(len(dates)) * 2 * pd.np.pi / 96),
       'temp': 15 + 10 * pd.np.sin(pd.np.arange(len(dates)) * 2 * pd.np.pi / 96),
       'wind_speed': 5 + 3 * pd.np.random.randn(len(dates))
   })
   data.set_index('datetime', inplace=True)

   # Or load from CSV
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)


Train a Model
-------------


.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   import pandas as pd

   # Create prediction job and model specifications
   pj = PredictionJobDataClass(id=1, name="example_forecast")
   model_specs = ModelSpecificationDataClass()

   # Load your input data (should include load, weather features, etc.)
   input_data = pd.read_csv("your_data.csv")

   # Train the model with default settings
   trained_model = train_model_pipeline_core(
       pj=pj,
       model_specs=model_specs,
       input_data=input_data
   )


Create Your First Forecast
--------------------------


.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features

   # Create sample input data for forecasting
   forecast_index = pd.date_range(start="2023-01-01 00:00:00", freq='15T', periods=96)
   forecast_data = pd.DataFrame(index=forecast_index)
   forecast_data['T-1h'] = 15.0 + 5 * np.sin(forecast_index.hour / 24 * 2 * np.pi)
   forecast_data['radiation'] = np.maximum(0, 800 * np.sin((forecast_index.hour - 6) / 12 * np.pi))
   forecast_data['windspeed_100m'] = 8.0 + 3 * np.random.normal(0, 1, len(forecast_index))

   # Apply feature engineering
   forecast_data = apply_features(forecast_data, horizons=[0.25, 24.0])

   # Make predictions using trained model
   predictions = model.predict(forecast_data)

   # Display forecast results
   print("Forecast Results:")
   print(f"Mean prediction: {predictions.mean():.2f}")
   print(f"Min prediction: {predictions.min():.2f}")
   print(f"Max prediction: {predictions.max():.2f}")

   # Create simple visualization
   import matplotlib.pyplot as plt
   plt.figure(figsize=(12, 6))
   plt.plot(forecast_index, predictions, label='Forecast', linewidth=2)
   plt.xlabel('Time')
   plt.ylabel('Load (MW)')
   plt.title('Energy Load Forecast')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.show()


.. note::

   OpenSTEF is a forecasting library designed for integration into your existing systems. You'll need to implement your own data pipelines, scheduling, and result handling around the core forecasting functions shown above.


Next Steps
----------


- Check out the comprehensive tutorials for step-by-step forecasting workflows

- Explore the API reference documentation for detailed function parameters and examples

- Read the advanced configuration guide for customizing model parameters

- Review the data preparation best practices for optimal forecasting results

- Learn about model validation techniques in the evaluation guide

- Discover integration patterns in the deployment documentation


