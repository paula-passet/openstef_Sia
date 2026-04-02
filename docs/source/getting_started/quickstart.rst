Quickstart
==========

This page shows you how to train a forecasting model and create predictions in just a few lines of code. If you're new to OpenSTEF, start here.

Installation
------------

Install OpenSTEF using pip::

   pip install openstef

For development installations or optional dependencies, see the full installation guide.

Your First Forecast
-------------------

OpenSTEF works with pandas DataFrames containing historical load data and weather information. Here's a minimal example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Prepare your data: a DataFrame with datetime index
   # Required columns: 'load' (target), weather features (e.g., 'temp', 'windspeed')
   data = pd.DataFrame({
       'load': [...],  # Your historical load measurements
       'temp': [...],  # Temperature observations
       'windspeed': [...],  # Wind speed observations
       # Add other weather features as needed
   }, index=pd.date_range('2023-01-01', periods=8760, freq='15T'))
   
   # Define prediction job configuration
   pj = {
       'id': 307,
       'name': 'My first forecast',
       'model': 'xgb',  # XGBoost model (default)
       'horizon_minutes': 2880,  # Forecast 48 hours ahead
       'resolution_minutes': 15,  # 15-minute resolution
   }
   
   # Train the model
   model_specs = train_model_pipeline(pj, data)
   
   # Create a forecast using the trained model
   forecast = create_forecast_pipeline(
       pj, 
       model_specs,
       input_data=data
   )
   
   # The forecast DataFrame contains predictions with confidence intervals
   print(forecast[['forecast', 'stdev']])

The ``forecast`` DataFrame contains columns for predicted values, standard deviation, and quantiles that represent forecast uncertainty.

What Just Happened?
^^^^^^^^^^^^^^^^^^^

1. **train_model_pipeline** automatically handles feature engineering, model training, and validation
2. **create_forecast_pipeline** generates predictions for the configured horizon with uncertainty quantification
3. Both pipelines use sensible defaults - you only need to specify the essentials

Data Requirements
-----------------

Your input DataFrame must have:

- **Datetime index**: Regular intervals (typically 15 minutes)
- **Load column**: Historical measurements of the quantity you want to forecast
- **Weather features**: At minimum temperature; optionally wind speed, radiation, humidity, etc.

For production use, you'll typically load data from your own database or time-series storage system.

Next Steps
----------

This quickstart gets you a working forecast quickly. To build production-ready forecasting systems:

- **Tutorials**: Work through :doc:`tutorials` for comprehensive examples including backtesting and custom workflows
- **Use Cases**: See :doc:`../guides/use_cases` to identify which forecasting approach fits your needs
- **Deployment**: Check :doc:`../guides/how_to_guides` for orchestration and data integration patterns
- **Concepts**: Read :doc:`../reference/concepts` to understand forecast interpretation and model selection

For questions, see the :doc:`../guides/faq` or reach out to the community via GitHub Discussions.