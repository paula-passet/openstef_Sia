Now I'll create the quickstart documentation page based on the information I've gathered:

Quickstart
==========

Get up and running with OpenSTEF in minutes. This guide shows you how to train your first forecasting model and create a forecast using the OpenSTEF Python library.

Installation
------------

Install OpenSTEF from PyPI:

.. code-block:: python

   pip install openstef

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast. This example uses the built-in pipeline functions that handle all the complexity for you:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Create a prediction job configuration
   prediction_job = PredictionJobDataClass(
       id="quickstart_example",
       name="My First Forecast",
       model="xgb",  # XGBoost model
       lat=52.1326,  # Amsterdam coordinates
       lon=5.2913,
       forecast_type="demand"
   )

   # Load your data (must include 'load' column and datetime index)
   # This example assumes you have historical load data
   training_data = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)
   
   # Train the model
   trained_model, model_specs, report = train_model_pipeline(
       pj=prediction_job,
       input_data=training_data
   )
   
   # Create a forecast for the next 48 hours
   forecast = create_forecast_pipeline_core(
       pj=prediction_job,
       input_data=training_data,  # Recent data for context
       model=trained_model,
       model_specs=model_specs
   )
   
   print(forecast.head())

The forecast DataFrame contains:

- **forecast**: Point predictions
- **quantile_P10** to **quantile_P90**: Confidence intervals
- **stdev**: Standard deviation of predictions

.. note::
   OpenSTEF is a Python library, not a standalone application. You integrate it into your own systems and workflows.

What You Need
^^^^^^^^^^^^^

Your input data must include:

- A **load** column with historical energy measurements
- A **datetime index** with regular intervals (typically 15-minute resolution)
- At least several weeks of historical data for training

OpenSTEF automatically handles:

- Weather data integration (using coordinates from your prediction job)
- Feature engineering (time-based features, weather correlations)
- Model training and validation
- Probabilistic forecast generation

Next Steps
----------

This quickstart gets you forecasting quickly with default settings. For production use and advanced customization:

- Follow the comprehensive :doc:`tutorials <tutorials>` to understand the full workflow
- Explore different :doc:`use cases </guides/use_cases>` to find the best approach for your needs  
- Check the :doc:`how-to guides </guides/how_to_guides>` for deployment and integration patterns

Ready to dive deeper? The tutorials will walk you through data preparation, model evaluation, and backtesting with real examples.