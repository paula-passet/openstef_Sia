Quickstart
==========

This page shows you how to create your first energy forecast with OpenSTEF in just a few lines of code. OpenSTEF is a Python library for short-term energy forecasting that provides complete machine learning pipelines for training models and generating forecasts.

Installation
------------

Install OpenSTEF from PyPI:

.. code-block:: python

   pip install openstef

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast using OpenSTEF's built-in pipelines:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.pipeline.create_forecast import create_forecast_pipeline_core

   # Create sample training data
   dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='15T')
   training_data = pd.DataFrame({
       'datetime': dates,
       'load': 100 + 20 * pd.np.sin(2 * pd.np.pi * dates.hour / 24) + pd.np.random.normal(0, 5, len(dates)),
       'temperature': 15 + 10 * pd.np.sin(2 * pd.np.pi * (dates.dayofyear - 80) / 365) + pd.np.random.normal(0, 2, len(dates))
   }).set_index('datetime')

   # Configure prediction job
   prediction_job = PredictionJobDataClass(
       id=1,
       name="demo_forecast",
       model="xgb",
       forecast_type="demand",
       resolution_minutes=15,
       horizon_minutes=2880,  # 48 hours
       lat=52.0,
       lon=5.0
   )

   # Train model
   model, model_specs, _ = train_model_pipeline_core(
       pj=prediction_job,
       input_data=training_data
   )

   # Create forecast input data (recent data for prediction)
   forecast_start = datetime(2024, 1, 1)
   forecast_input = training_data.loc[forecast_start - timedelta(days=7):forecast_start]

   # Generate forecast
   forecast = create_forecast_pipeline_core(
       pj=prediction_job,
       input_data=forecast_input,
       model=model,
       model_specs=model_specs
   )

   print(f"Forecast created with {len(forecast)} predictions")
   print(forecast.head())

This example demonstrates OpenSTEF's core workflow: configure a prediction job, train a model with historical data, and generate forecasts. The forecast includes confidence intervals and covers the full horizon specified in your prediction job.

Next Steps
----------

- Explore comprehensive examples in our `tutorials <tutorials.html>`_ section
- Learn about different `use cases <../guides/use_cases.html>`_ OpenSTEF supports
- Check out the `FAQ <../guides/faq.html>`_ for common questions
- Browse the complete `API reference <../reference/api.html>`_ for advanced usage