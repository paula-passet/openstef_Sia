Quickstart
==========

Get up and running with OpenSTEF in minutes. This page shows you how to train a model and create your first forecast with minimal setup.

What You'll Need
----------------

- Python 3.8 or higher
- A CSV file with historical load and weather data
- 5 minutes of your time

.. note::
   This quickstart uses sample data and default settings. For production use, see the :doc:`tutorials` page for comprehensive guidance.

Install OpenSTEF
----------------

.. code-block:: bash

   pip install openstef

Create Your First Forecast
---------------------------

Here's a complete example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Define your forecasting job
   pj = PredictionJobDataClass(
       id=1,
       name="QuickstartForecast",
       model="xgb",
       horizon_minutes=48 * 60,  # 48 hours ahead
       resolution_minutes=15,    # 15-minute intervals
       quantiles=[0.1, 0.5, 0.9],  # 10%, 50%, 90% confidence levels
       lat=52.1,
       lon=5.2,
       forecast_type="demand"
   )

   # Load your data (must include 'load', 'radiation', 'windspeed_100m' columns)
   data = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)

   # Split data for training and forecasting
   train_data = data.iloc[:-192]  # All but last 8 days for training
   forecast_data = data.iloc[-192:]  # Last 8 days for forecasting

   # Train the model
   mlflow_tracking_uri = "./mlflow_models"
   trained_model = train_model_pipeline(
       pj=pj,
       input_data=train_data,
       mlflow_tracking_uri=mlflow_tracking_uri
   )

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=forecast_data,
       mlflow_tracking_uri=mlflow_tracking_uri
   )

   # View results
   print(forecast.head())

Understanding the Results
-------------------------

Your forecast DataFrame contains:

- **forecast**: The median (50th percentile) prediction
- **quantile_X**: Confidence intervals (e.g., quantile_0.1 for 10th percentile)
- **stdev**: Standard deviation of the prediction
- **pid**: Prediction job identifier

.. code-block:: python

   # Plot your forecast vs actual values
   import matplotlib.pyplot as plt

   plt.figure(figsize=(12, 6))
   plt.plot(forecast.index, forecast['forecast'], label='Forecast', color='blue')
   plt.plot(forecast.index, forecast_data['load'], label='Actual', color='red')
   plt.fill_between(
       forecast.index,
       forecast['quantile_0.1'],
       forecast['quantile_0.9'],
       alpha=0.3,
       color='blue',
       label='80% Confidence Interval'
   )
   plt.legend()
   plt.title('Energy Forecast vs Actual Load')
   plt.show()

Data Requirements
-----------------

Your CSV file needs these columns:

- **load**: Historical energy consumption/demand values
- **radiation**: Solar radiation data
- **windspeed_100m**: Wind speed at 100 meters height
- **datetime index**: Timestamps for all measurements

.. note::
   OpenSTEF automatically creates additional features from weather data, handles missing values, and applies data preprocessing. No manual feature engineering required for basic forecasting.

Next Steps
----------

- Try the comprehensive :doc:`tutorials` for production-ready workflows
- Explore different :doc:`../guides/use_cases` for your specific application
- Check the :doc:`../guides/faq` for common questions
- Learn about OpenSTEF's :doc:`../reference/concepts` and forecasting approach