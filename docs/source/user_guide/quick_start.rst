Quick Start
===========

Get up and running with OpenSTEF in under 10 minutes. This guide will walk you through creating your first energy forecast using the OpenSTEF library.

.. note::
   OpenSTEF is a Python library for building forecasting applications. You'll write Python code to train models and generate forecasts - it's not a pre-built application you can run directly.

Prerequisites
=============

- Python 3.8 or higher
- Basic familiarity with pandas and time series data
- Understanding of energy forecasting concepts (load, weather dependency)

Installation
============

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

This installs all core components needed for forecasting.

Your First Forecast
===================

Let's create a complete forecasting workflow in just a few steps.

Step 1: Load Sample Data
------------------------

OpenSTEF includes sample data to get you started:

.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd
   
   # Load built-in sample data (15-minute resolution energy data with weather)
   from openstef.data.sample import load_sample_data
   data = load_sample_data()
   
   print(f"Loaded {len(data)} data points from {data.index.min()} to {data.index.max()}")

Step 2: Configure a Prediction Job
----------------------------------

A PredictionJob defines what you want to forecast and how:

.. code-block:: python

   # Create a prediction job configuration
   pj = PredictionJobDataClass(
       id=1,
       name="my_first_forecast",
       model="xgb",  # Use XGBoost regressor
       horizon_minutes=2880,  # 48-hour forecast horizon
       resolution_minutes=15,  # 15-minute resolution
       train_components=0.95,  # Use 95% of data for training
   )

Step 3: Train a Model
---------------------

Train a forecasting model using your data:

.. code-block:: python

   # Train the model with automatic feature engineering
   model_specs = train_model_pipeline(
       pj=pj,
       input_data=data,
       check_old_model_age=False  # Skip age check for this example
   )
   
   print(f"Model trained successfully: {model_specs.name}")
   print(f"Model type: {type(model_specs.trained_model)}")

Step 4: Create a Forecast
-------------------------

Generate probabilistic forecasts for the next 48 hours:

.. code-block:: python

   # Create forecast for the latest available datetime
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=data,
       model_specs=model_specs
   )
   
   print(f"Generated forecast with {len(forecast)} time points")
   print(f"Forecast columns: {list(forecast.columns)}")

Step 5: Examine Results
-----------------------

OpenSTEF generates probabilistic forecasts with confidence intervals:

.. code-block:: python

   # Display forecast summary
   print("\nForecast Preview:")
   print(forecast[['forecast', 'quantile_P10', 'quantile_P90']].head(10))
   
   # Plot the results (requires matplotlib)
   import matplotlib.pyplot as plt
   
   # Plot recent historical data and forecast
   recent_data = data.tail(96)  # Last 24 hours of actual data
   
   plt.figure(figsize=(12, 6))
   plt.plot(recent_data.index, recent_data['load'], 'b-', label='Historical Load', linewidth=2)
   plt.plot(forecast.index, forecast['forecast'], 'r-', label='Forecast', linewidth=2)
   plt.fill_between(forecast.index, forecast['quantile_P10'], forecast['quantile_P90'], 
                    alpha=0.3, color='red', label='P10-P90 Confidence Band')
   
   plt.title('Energy Load Forecast')
   plt.xlabel('Time')
   plt.ylabel('Load (MW)')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.tight_layout()
   plt.show()

Understanding Your Results
==========================

Your forecast contains several important columns:

- **forecast**: The most likely predicted value (P50 quantile)
- **quantile_P10**: Lower bound (10% chance actual will be below this)
- **quantile_P90**: Upper bound (10% chance actual will be above this)
- **quantile_P50**: Median prediction (same as 'forecast')

The P10-P90 band gives you an 80% confidence interval for your predictions.

What Just Happened?
===================

In those few lines of code, OpenSTEF automatically:

1. **Analyzed your data** to understand patterns and seasonality
2. **Engineered features** including weather correlations, lag features, and calendar effects
3. **Selected optimal hyperparameters** for the XGBoost model
4. **Trained a probabilistic model** that predicts not just point estimates but confidence intervals
5. **Generated a 48-hour forecast** with 15-minute resolution

Next Steps
==========

Now that you have a working forecast, explore these topics:

- **Use Your Own Data**: Replace the sample data with your energy measurements
- **Try Different Models**: Experiment with 'lgb' (LightGBM) or 'linear' models
- **Evaluate Performance**: Learn about backtesting to test model quality
- **Customize Features**: Add domain-specific predictors for your use case

Continue to the :doc:`tutorials` for in-depth guidance on these topics.

Troubleshooting
===============

**"No module named 'openstef'"**
   Make sure you installed with ``pip install openstef`` and are using the correct Python environment.

**"Insufficient data for training"**
   The sample data should work out of the box. If using your own data, ensure you have at least several weeks of 15-minute resolution data.

**Forecast looks unrealistic**
   This is normal with sample data. Models perform better when trained on data similar to what you want to predict.

Need Help?
==========

- Check the :doc:`../faq` for common questions
- Visit our `GitHub Discussions <https://github.com/OpenSTEF/openstef/discussions>`_ for community support
- Review the :doc:`tutorials` for more detailed examples