Quick Start
===========

Get up and running with OpenSTEF in under 10 minutes. This guide shows you how to install OpenSTEF, load sample data, train a model, and create your first forecast.

.. note::
   OpenSTEF is a Python library, not a deployable application. You'll be writing Python code to use its forecasting capabilities.

Prerequisites
-------------

- Python 3.8 or higher
- Basic familiarity with pandas DataFrames
- Understanding of time series data concepts

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

Load Sample Data
----------------

OpenSTEF includes built-in sample data to get you started quickly:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Load sample energy load data
   from openstef.data.sample import load_sample_data
   
   # Get sample data with energy load and weather features
   data = load_sample_data()
   print(f"Loaded {len(data)} rows of sample data")
   print(data.head())

The sample data includes typical energy forecasting features like temperature, wind speed, solar irradiance, and historical load patterns.

Train a Model
-------------

Create a prediction job configuration and train a model:

.. code-block:: python

   # Create a prediction job configuration
   prediction_job = PredictionJobDataClass(
       id=1,
       name="quick_start_forecast",
       model="xgb",  # XGBoost model
       horizon_minutes=2880,  # 48-hour forecast horizon
       resolution_minutes=15,  # 15-minute resolution
       train_components=False  # Single model (not component split)
   )
   
   # Train the model
   model_specs = train_model_pipeline(
       prediction_job=prediction_job,
       input_data=data
   )
   
   print(f"Model trained successfully: {model_specs.model_type}")

Create a Forecast
-----------------

Generate a probabilistic forecast using your trained model:

.. code-block:: python

   # Create forecast for the next 48 hours
   forecast = create_forecast_pipeline(
       prediction_job=prediction_job,
       model_specs=model_specs,
       input_data=data
   )
   
   print(f"Generated forecast with {len(forecast)} time steps")
   print(forecast[['forecast', 'quantile_P10', 'quantile_P90']].head())

The forecast includes:
- ``forecast``: Point forecast (P50 quantile)
- ``quantile_P10``: Lower bound (10th percentile)
- ``quantile_P90``: Upper bound (90th percentile)

Visualize Results
-----------------

Plot your forecast results:

.. code-block:: python

   import matplotlib.pyplot as plt
   
   # Plot the last 7 days of actual data and the forecast
   recent_data = data.tail(672)  # Last 7 days (15-min resolution)
   
   plt.figure(figsize=(12, 6))
   plt.plot(recent_data.index, recent_data['load'], label='Historical Load', color='blue')
   plt.plot(forecast.index, forecast['forecast'], label='Forecast', color='red')
   plt.fill_between(forecast.index, forecast['quantile_P10'], forecast['quantile_P90'], 
                    alpha=0.3, color='red', label='Confidence Interval')
   
   plt.xlabel('Time')
   plt.ylabel('Energy Load (MW)')
   plt.title('Energy Load Forecast')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.show()

Next Steps
----------

Now that you have a working forecast, explore these areas:

**Learn More:**
- :doc:`tutorials` - Comprehensive step-by-step guides
- :doc:`../use_cases/index` - Real-world forecasting applications
- :doc:`../concepts/index` - Understanding forecast outputs and model selection

**Customize Your Setup:**
- :doc:`../how_to_guides/index` - Data integration and deployment patterns
- :doc:`../api/index` - Full API reference for advanced usage

**Get Help:**
- :doc:`../faq` - Common questions and troubleshooting
- `GitHub Discussions <https://github.com/OpenSTEF/openstef/discussions>`_ - Community support

.. warning::
   This quick start uses sample data for demonstration. For production use, you'll need to integrate your own historical energy load and weather data following the data schema requirements in the tutorials.