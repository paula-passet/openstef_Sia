Quick Start Guide
=================

This guide shows you how to train your first OpenSTEF model and create a forecast in just a few steps. OpenSTEF is a Python machine learning library designed specifically for short-term energy forecasting, and you can have a working forecast in under 10 minutes.

What You'll Learn
-----------------

- How to set up a basic prediction job
- How to train a forecasting model
- How to create forecasts with your trained model
- How to evaluate forecast results

Prerequisites
-------------

You'll need:

- Python 3.8 or higher
- OpenSTEF installed (``pip install openstef``)
- A CSV file with time series data including load measurements and weather features

Basic Example
-------------

Here's a complete example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Set up pandas plotting
   pd.options.plotting.backend = 'plotly'

Step 1: Define Your Prediction Job
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The prediction job contains all the configuration for your forecast:

.. code-block:: python

   # Create prediction job with basic settings
   pj = PredictionJobDataClass(
       id=1,
       model='xgb',  # XGBoost model
       quantiles=[0.10, 0.50, 0.90],  # Confidence intervals
       horizon_minutes=48*60,  # Forecast 48 hours ahead
       resolution_minutes=15,  # 15-minute intervals
       lat=52.0,  # Latitude for weather data
       lon=5.0,   # Longitude for weather data
       forecast_type="demand",
       name="MyFirstForecast"
   )

Step 2: Load Your Data
^^^^^^^^^^^^^^^^^^^^^^

Your data should include timestamps, load measurements, and weather features:

.. code-block:: python

   # Load time series data
   input_data = pd.read_csv('your_data.csv', 
                           index_col='timestamp', 
                           parse_dates=True)
   
   # Data should contain columns like:
   # - load: energy measurements
   # - radiation: solar radiation
   # - windspeed_100m: wind speed at 100m
   # - temperature: air temperature

Step 3: Train Your Model
^^^^^^^^^^^^^^^^^^^^^^^^

Train a forecasting model using historical data:

.. code-block:: python

   # Train the model
   model, model_specs, report = train_model_pipeline(
       pj=pj,
       input_data=input_data,
       mlflow_tracking_uri="./mlflow_models"  # Where to save the model
   )
   
   print("Model training completed!")
   print(f"Model type: {model_specs.model_type}")

Step 4: Create a Forecast
^^^^^^^^^^^^^^^^^^^^^^^^^

Use your trained model to create forecasts:

.. code-block:: python

   # Create forecast for the next 48 hours
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=input_data,
       mlflow_tracking_uri="./mlflow_models"
   )
   
   # View your forecast
   print(forecast.head())

Step 5: Visualize Results
^^^^^^^^^^^^^^^^^^^^^^^^^

Plot your forecast to see the results:

.. code-block:: python

   # Plot forecast with confidence intervals
   fig = forecast[['forecast', 'quantile_P10', 'quantile_P90']].plot()
   fig.update_layout(
       title="Energy Forecast",
       xaxis_title="Time",
       yaxis_title="Load (MW)"
   )
   fig.show()

Understanding the Output
------------------------

Your forecast DataFrame contains:

- ``forecast``: The main prediction (median/P50 quantile)
- ``quantile_P10``: Lower confidence bound (10th percentile)
- ``quantile_P90``: Upper confidence bound (90th percentile)
- Additional quantiles if specified in your prediction job

The forecast represents expected energy demand at 15-minute intervals for the next 48 hours.

Common Data Requirements
------------------------

Your input data should include:

**Required columns:**
- ``load``: Historical energy measurements
- ``radiation``: Solar radiation data
- ``windspeed_100m``: Wind speed at 100 meters
- ``temperature``: Air temperature

**Data format:**
- DateTime index with regular intervals (e.g., 15 minutes)
- At least several weeks of historical data for training
- Recent data for making forecasts

.. note::
   OpenSTEF automatically handles missing data and feature engineering. The library creates additional features like day-of-week, hour-of-day, and lag features from your input data.

Next Steps
----------

Now that you have a working forecast, explore these resources:

- :doc:`../getting_started/tutorials` - Comprehensive tutorials with advanced features
- :doc:`../guides/use_cases` - Find the right approach for your specific use case
- :doc:`../reference/concepts` - Understand forecasting concepts and model behavior

For production deployments, see :doc:`../guides/how_to_guides` for integration patterns with orchestration tools and data systems.

Troubleshooting
---------------

**Model training fails:** Ensure your data has sufficient history (at least 4 weeks) and contains the required weather columns.

**Poor forecast accuracy:** Check data quality, consider adjusting the forecast horizon, or explore different model types in the tutorials.

**Missing predictions:** Verify your input data covers the forecast period and has recent weather data.