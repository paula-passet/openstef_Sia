Quick Start
===========

Get started with OpenSTEF in minutes. This guide shows you how to train your first forecasting model and create a forecast using the OpenSTEF Python library.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: python

   pip install openstef

For development or advanced features, see the complete :doc:`installation guide <../user_guide/installation>`.

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from openstef_models.data_classes.prediction_job import PredictionJobDataClass
   from openstef_models.pipeline.train_model import train_model_pipeline
   from openstef_models.pipeline.create_forecast import create_forecast_pipeline

   # Define your forecasting task
   prediction_job = PredictionJobDataClass(
       id=307,
       name="Example Substation",
       model="xgb",
       forecast_type="demand",
       horizon_minutes=2880,  # 48 hours
       resolution_minutes=15,
       lat=52.1,
       lon=5.2
   )

   # Load your data (CSV with datetime index, 'load' column, and weather data)
   data = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)
   
   # Train the model
   model_specs = train_model_pipeline(
       pj=prediction_job,
       input_data=data,
       mlflow_tracking_uri="file:///tmp/mlflow"
   )
   
   # Create a forecast
   forecast = create_forecast_pipeline(
       pj=prediction_job,
       input_data=data,
       mlflow_tracking_uri="file:///tmp/mlflow"
   )
   
   print(f"Forecast created with {len(forecast)} predictions")
   print(forecast.head())

Data Requirements
-----------------

Your input data should be a pandas DataFrame with:

- **Datetime index**: Regular 15-minute intervals
- **load column**: Your target variable (energy demand/generation)
- **Weather columns**: At minimum `radiation` and `windspeed_100m`

Example data structure:

.. code-block:: python

   #                     load  radiation  windspeed_100m  temperature
   # 2023-01-01 00:00:00  150.2      0.0            8.5         2.1
   # 2023-01-01 00:15:00  148.7      0.0            8.2         2.0
   # 2023-01-01 00:30:00  147.1      0.0            7.9         1.9

Key Parameters
--------------

The most important parameters to configure:

- **model**: Choose from `"xgb"` (XGBoost), `"lgb"` (LightGBM), or `"linear_quantile"`
- **forecast_type**: `"demand"` for load forecasting, `"solar"` for solar generation
- **horizon_minutes**: How far ahead to forecast (e.g., 2880 = 48 hours)
- **resolution_minutes**: Data frequency (typically 15 minutes)

Next Steps
----------

Now that you have your first forecast working:

1. **Learn more**: Read the comprehensive :doc:`tutorials <tutorials>` for detailed examples
2. **Explore use cases**: Check out :doc:`../guides/use_cases` to find patterns matching your needs  
3. **Customize models**: See :doc:`../guides/how_to_guides` for advanced configuration
4. **Understand concepts**: Visit :doc:`../reference/concepts` to learn about forecasting fundamentals

.. note::
   
   This quickstart uses default settings optimized for common use cases. For production deployments, you'll want to customize data preprocessing, model parameters, and evaluation metrics based on your specific requirements.