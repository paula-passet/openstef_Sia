Quickstart
==========

Get started with OpenSTEF in minutes. This guide shows you how to train a model and create your first forecast using minimal code.

Installation
------------

Install OpenSTEF with pip:

.. code-block:: bash

   pip install openstef

For the complete experience including evaluation tools:

.. code-block:: bash

   pip install "openstef[all]"

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # Define forecast specifications
   pj = PredictionJobDataClass(
       id=1,
       model='xgb',  # XGBoost model
       quantiles=[0.10, 0.50, 0.90],  # 10%, 50%, 90% confidence intervals
       horizon_minutes=48*60,  # Forecast 48 hours ahead
       resolution_minutes=15,  # 15-minute intervals
       lat=52.0,
       lon=5.0,
       forecast_type="demand",
       name="QuickStart"
   )

   # Load your data (CSV with datetime index and 'load' column)
   # Data should include: load, temperature, radiation, windspeed columns
   input_data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)

   # Train the model
   model, modelspecs, train_data = train_model_pipeline(
       pj=pj,
       input_data=input_data
   )

   # Create forecast
   forecast = create_forecast_pipeline_core(
       pj=pj,
       input_data=input_data,
       model=model,
       model_specs=modelspecs
   )

   print(f"Forecast created with {len(forecast)} predictions")
   print(forecast.head())

What You Get
------------

The forecast DataFrame contains:

- **forecast**: Point predictions (50th quantile)
- **quantile_X**: Confidence intervals (e.g., quantile_10, quantile_90)
- **horizon**: Hours ahead for each prediction
- **datetime**: Timestamp for each forecast point

.. code-block:: python

   # View forecast structure
   print(forecast.columns)
   # Output: ['forecast', 'quantile_10', 'quantile_90', 'horizon', ...]

   # Plot your forecast
   forecast['forecast'].plot(title='Energy Forecast')

Data Requirements
-----------------

Your CSV file needs these columns:

- **load**: Historical energy consumption/generation (target variable)
- **temperature**: Weather temperature
- **radiation**: Solar radiation (for solar generation)
- **windspeed**: Wind speed (for wind generation)
- **datetime index**: Timestamp column set as pandas index

.. note::
   OpenSTEF includes sample datasets. See :doc:`../guides/tutorials` for examples using built-in data.

Model Options
-------------

Change the model type by updating the prediction job:

.. code-block:: python

   # Linear quantile regression (faster, good for peaks)
   pj = PredictionJobDataClass(
       model='linear_quantile',
       # ... other parameters
   )

   # XGBoost (default, handles complex patterns)
   pj = PredictionJobDataClass(
       model='xgb',
       # ... other parameters
   )

Quick Evaluation
----------------

Evaluate your forecast quality:

.. code-block:: python

   from openstef.metrics import metrics

   # If you have actual values for comparison
   if 'realised' in forecast.columns:
       mae = metrics.mean_absolute_error(
           forecast['realised'], 
           forecast['forecast']
       )
       print(f"Mean Absolute Error: {mae:.2f}")

Next Steps
----------

- **Learn more**: Read the comprehensive :doc:`../guides/tutorials` 
- **Production setup**: See :doc:`../guides/how_to_guides` for deployment
- **Understand concepts**: Explore :doc:`../reference/concepts`
- **Find your use case**: Check :doc:`../guides/use_cases`

This quickstart gets you forecasting immediately. The tutorials provide deeper examples with real data, evaluation techniques, and advanced customization options.