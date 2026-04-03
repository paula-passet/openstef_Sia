Quickstart
==========

This page shows the fastest path to generating your first forecast with OpenSTEF. Copy and paste the code below to get a working forecast in minutes. For detailed explanations of each step, see :doc:`first_forecast`.

Prerequisites
-------------

Install OpenSTEF:

.. code-block:: bash

   pip install openstef

Create Sample Data
------------------

OpenSTEF works with time series data in pandas DataFrames with a DatetimeIndex. Here's a minimal dataset:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   
   # Create 30 days of hourly load data
   dates = pd.date_range(
       start=datetime(2024, 1, 1),
       end=datetime(2024, 1, 31),
       freq='h'
   )
   
   # Simulate load pattern with daily cycle
   hours = np.arange(len(dates))
   load = 100 + 20 * np.sin(2 * np.pi * hours / 24) + np.random.normal(0, 5, len(dates))
   
   # Create DataFrame
   data = pd.DataFrame({
       'load': load,
       'temperature': 15 + 5 * np.sin(2 * np.pi * hours / 24) + np.random.normal(0, 2, len(dates))
   }, index=dates)

Wrap in Dataset
---------------

Convert the DataFrame to OpenSTEF's dataset format:

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset
   
   dataset = ForecastInputDataset(
       data=data,
       sample_interval=timedelta(hours=1),
       target_column='load'
   )

Train and Predict
-----------------

Use the default forecasting model to train and generate predictions:

.. code-block:: python

   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Split data: train on first 80%, predict on last 20%
   split_point = int(len(data) * 0.8)
   train_data = data.iloc[:split_point]
   forecast_start = data.index[split_point]
   
   # Train model
   model, _ = train_model_pipeline(
       pj={'id': 'quickstart', 'name': 'Quickstart Forecast'},
       input_data=train_data,
       model_type='xgb'
   )
   
   # Generate forecast
   forecast = create_forecast_pipeline(
       pj={'id': 'quickstart', 'name': 'Quickstart Forecast'},
       input_data=data,
       model=model,
       forecast_start=forecast_start
   )

View Results
------------

The forecast is returned as a pandas DataFrame:

.. code-block:: python

   print(forecast[['forecast', 'load']].head())
   
   # Plot results
   import matplotlib.pyplot as plt
   
   plt.figure(figsize=(12, 6))
   plt.plot(forecast.index, forecast['load'], label='Actual', alpha=0.7)
   plt.plot(forecast.index, forecast['forecast'], label='Forecast', alpha=0.7)
   plt.legend()
   plt.xlabel('Time')
   plt.ylabel('Load')
   plt.title('OpenSTEF Quickstart Forecast')
   plt.show()

Complete Example
----------------

Here's the full working code in one block:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Create sample data
   dates = pd.date_range(start=datetime(2024, 1, 1), end=datetime(2024, 1, 31), freq='h')
   hours = np.arange(len(dates))
   data = pd.DataFrame({
       'load': 100 + 20 * np.sin(2 * np.pi * hours / 24) + np.random.normal(0, 5, len(dates)),
       'temperature': 15 + 5 * np.sin(2 * np.pi * hours / 24) + np.random.normal(0, 2, len(dates))
   }, index=dates)
   
   # Split data
   split_point = int(len(data) * 0.8)
   train_data = data.iloc[:split_point]
   forecast_start = data.index[split_point]
   
   # Train and forecast
   pj = {'id': 'quickstart', 'name': 'Quickstart Forecast'}
   model, _ = train_model_pipeline(pj, train_data, model_type='xgb')
   forecast = create_forecast_pipeline(pj, data, model, forecast_start)
   
   # View results
   print(forecast[['forecast', 'load']].tail(10))

Next Steps
----------

This quickstart uses default settings. To understand what's happening and customize your forecasts:

- :doc:`first_forecast` - Detailed walkthrough with explanations
- :doc:`installation` - System requirements and installation options
- :doc:`backtesting` - Compare model performance over time
- :doc:`advanced_customization` - Configure feature engineering and model parameters