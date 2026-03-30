Quickstart
==========

Get up and running with OpenSTEF in minutes. This guide shows you how to train your first forecasting model and create a forecast using minimal code.

Installation
------------

Install OpenSTEF with pip::

   pip install openstef

For the complete installation with all features::

   pip install "openstef[all]"

Your First Forecast
-------------------

Here's how to train a model and create a forecast in just a few steps:

.. code-block:: python

   import pandas as pd
   from openstef_models.forecasting import train_model_pipeline, create_forecast_pipeline
   from openstef_core.base_model import PredictionJobDataClass

   # Configure your forecasting job
   pj = PredictionJobDataClass(
       id=287,
       model='xgb',  # XGBoost model
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],  # Confidence intervals
       horizon_minutes=48*60,  # Forecast 48 hours ahead
       resolution_minutes=15,  # 15-minute intervals
       lat=52.1,  # Latitude
       lon=5.2,   # Longitude
       forecast_type="demand",
       name='MyFirstForecast'
   )

   # Load your data (CSV with datetime index)
   # Required columns: 'load' (target), weather data, timestamps
   input_data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)

   # Split data for training and testing
   train_data = input_data.iloc[:-192]  # All but last 8 days
   test_data = input_data.iloc[-192:]   # Last 8 days for testing

   # Train the model
   model = train_model_pipeline(pj, train_data)

   # Create forecast
   forecast = create_forecast_pipeline(pj, test_data, model)

   # View results
   print(forecast[['forecast', 'quantile_P10', 'quantile_P90']].head())

Data Requirements
-----------------

Your input data should be a pandas DataFrame with:

- **DateTime index**: Timestamps at regular intervals (typically 15 minutes)
- **Target column**: The load/demand you want to forecast (column name: 'load')
- **Weather features**: Temperature, wind speed, solar radiation, etc.
- **Optional features**: Day-ahead prices, calendar features

Example data structure:

.. code-block:: python

   #                     load  temperature  windspeed  radiation
   # 2023-01-01 00:00:00  45.2         8.1        3.2        0.0
   # 2023-01-01 00:15:00  44.8         8.0        3.1        0.0
   # 2023-01-01 00:30:00  44.1         7.9        3.0        0.0

Understanding Results
---------------------

The forecast DataFrame contains:

- **forecast**: The main prediction (P50 quantile)
- **quantile_P10** to **quantile_P90**: Confidence intervals
- **horizon**: Hours ahead for each prediction
- **available_at**: When the forecast was made

.. code-block:: python

   # Visualize your forecast
   import matplotlib.pyplot as plt
   
   plt.figure(figsize=(12, 6))
   plt.plot(forecast.index, forecast['forecast'], label='Forecast', linewidth=2)
   plt.fill_between(forecast.index, 
                    forecast['quantile_P10'], 
                    forecast['quantile_P90'], 
                    alpha=0.3, label='80% Confidence')
   plt.legend()
   plt.title('Energy Demand Forecast')
   plt.show()

Model Options
-------------

OpenSTEF supports multiple model types. Simply change the `model` parameter:

.. code-block:: python

   # XGBoost (default, good for complex patterns)
   pj = PredictionJobDataClass(model='xgb', ...)
   
   # Linear Quantile Regression (better for extreme values)
   pj = PredictionJobDataClass(model='linear_quantile', ...)
   
   # Random Forest
   pj = PredictionJobDataClass(model='random_forest', ...)

Next Steps
----------

Now that you have your first forecast working:

- **Learn more**: Check out our :doc:`../getting_started/tutorials` for comprehensive examples
- **Explore use cases**: See :doc:`../guides/use_cases` to find the best approach for your needs  
- **Production deployment**: Read :doc:`../guides/how_to_guides` for deployment strategies
- **Understand concepts**: Visit :doc:`../reference/concepts` to learn about forecasting fundamentals

Need help? Visit our :doc:`../guides/faq` or check the :doc:`../reference/api/index` for detailed documentation.