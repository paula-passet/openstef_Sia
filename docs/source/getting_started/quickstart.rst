Quickstart
==========

Get started with OpenSTEF in minutes. This guide shows you how to train a forecasting model and create your first forecast with minimal setup.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

For the complete toolkit including evaluation tools:

.. code-block:: bash

   pip install "openstef[all]"

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast in just a few steps:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Load your data (CSV with datetime index and 'load' column)
   data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)
   
   # Define prediction job - this configures your forecasting model
   pj = PredictionJobDataClass(
       id=1,
       name="My First Forecast",
       model='xgb',  # XGBoost model
       forecast_type="demand",
       lat=52.0,  # Location coordinates
       lon=5.0,
       resolution_minutes=15,  # 15-minute intervals
       horizon_minutes=1440,   # 24-hour forecast horizon
       quantiles=[0.5]  # Median forecast
   )
   
   # Split data for training and testing
   train_data = data.iloc[:-96]  # All but last 24 hours
   test_data = data.iloc[-96:]   # Last 24 hours for forecasting
   
   # Train the model
   model, model_specs, _ = train_model_pipeline(pj, train_data)
   
   # Create forecast
   forecast = create_forecast_pipeline(pj, test_data)
   
   # View results
   print(forecast[['forecast', 'load']].head())

Data Requirements
-----------------

Your input data should be a pandas DataFrame with:

- **DateTime index**: Timestamps for your time series
- **Target column**: Named 'load' containing the values to forecast (e.g., energy consumption in MW)
- **Weather features**: Optional columns like 'temperature', 'windspeed', 'radiation'
- **Regular intervals**: Consistent time spacing (e.g., 15-minute intervals)

Example data structure:

.. code-block:: python

   # Example of properly formatted data
   data = pd.DataFrame({
       'load': [120.5, 125.2, 118.9, 122.1],
       'temperature': [15.2, 16.1, 14.8, 15.9],
       'windspeed': [5.2, 6.1, 4.8, 5.5]
   }, index=pd.date_range('2024-01-01', periods=4, freq='15min'))

Key Configuration Options
-------------------------

The ``PredictionJobDataClass`` controls your forecasting setup:

.. code-block:: python

   pj = PredictionJobDataClass(
       id=1,                      # Unique identifier
       name="Energy Forecast",    # Descriptive name
       model='xgb',              # Model type: 'xgb', 'lgb', 'linear'
       forecast_type="demand",    # Type of forecast
       lat=52.0, lon=5.0,        # Location for weather data
       resolution_minutes=15,     # Data interval
       horizon_minutes=1440,      # How far ahead to forecast (24h)
       quantiles=[0.1, 0.5, 0.9] # Confidence intervals
   )

Common model options:
- ``'xgb'``: XGBoost (recommended for most cases)
- ``'lgb'``: LightGBM (faster training)
- ``'linear'``: Linear regression (simple baseline)

Understanding Results
--------------------

The forecast returns a DataFrame with these key columns:

- ``forecast``: Main prediction values
- ``quantile_P10``, ``quantile_P90``: Confidence intervals (if requested)
- ``load``: Actual values (for comparison during evaluation)

.. code-block:: python

   # Visualize your forecast
   import matplotlib.pyplot as plt
   
   forecast[['forecast', 'load']].plot(figsize=(12, 6))
   plt.title('Energy Forecast vs Actual')
   plt.ylabel('Load (MW)')
   plt.show()

Next Steps
----------

Now that you have your first forecast working:

1. **Learn more**: Check out the :doc:`../getting_started/tutorials` for comprehensive examples
2. **Explore use cases**: See :doc:`../guides/use_cases` to find the right approach for your application  
3. **Customize**: Read :doc:`../guides/how_to_guides` for specific implementation tasks
4. **Understand concepts**: Visit :doc:`../reference/concepts` to learn about forecasting fundamentals

.. note::
   This quickstart uses default settings optimized for energy demand forecasting. OpenSTEF supports many other use cases including congestion forecasting, renewable generation, and district heating. See the use cases guide to explore other applications.