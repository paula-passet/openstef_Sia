Quick Start Guide
=================


Installation
------------


.. code-block:: bash

   # Install OpenSTEF
   pip install openstef
   # Verify installation


Load Sample Data
----------------


OpenSTEF requires time series data with a datetime index containing load measurements and weather features. The data should be structured as a pandas DataFrame with columns for load values and relevant weather variables like temperature, wind speed, and solar irradiation for accurate forecasting.


.. code-block:: python

   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   from openstef.model.regressors.regressor import OpenstfRegressor
   import pandas as pd
   import numpy as np

   # Create sample energy consumption dataset
   index = pd.date_range(start="2023-01-01 00:00:00", freq="15T", periods=2000)
   load_data = np.sin(index.hour/24*np.pi) * 100 + np.random.normal(0, 10, 2000)
   sample_data = pd.DataFrame(index=index, data={"load": load_data})

   # Add weather features
   sample_data["T-1d"] = 15 + 10 * np.sin((index.dayofyear-80)/365*2*np.pi) + np.random.normal(0, 2, 2000)
   sample_data["radiation"] = np.maximum(0, 800 * np.sin(index.hour/12*np.pi) + np.random.normal(0, 100, 2000))
   sample_data["windspeed"] = np.maximum(0, 5 + np.random.exponential(3, 2000))

   print(f"Sample dataset shape: {sample_data.shape}")
   print(sample_data.head())


Train Your First Model
----------------------


.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   import pandas as pd

   # Create prediction job with minimal configuration
   pj = PredictionJobDataClass(
       id=1,
       name="my_first_model",
       model="xgb",
       resolution_minutes=15
   )

   # Create model specifications with defaults
   model_specs = ModelSpecificationDataClass()

   # Load your training data (replace with actual data)
   input_data = pd.DataFrame({
       'load': [100, 120, 110, 130],
       'datetime': pd.date_range('2024-01-01', periods=4, freq='15T')
   }).set_index('datetime')

   # Train the model
   trained_model = train_model_pipeline_core(
       pj=pj,
       model_specs=model_specs,
       input_data=input_data
   )


Create a Forecast
-----------------


.. code-block:: python

   import pandas as pd
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.tasks.utils.task_context import TaskContext

   # Define prediction job for 24-hour forecast
   pj = PredictionJobDataClass(
       id=123,
       lat=52.1326,
       lon=5.2913,
       resolution_minutes=15,
       horizon_minutes=1440,  # 24 hours
       type="load",
       name="example_forecast",
       quantiles=[0.1, 0.5, 0.9]
   )

   # Create task context
   context = TaskContext()

   # Generate forecast
   create_forecast_task(pj, context, t_behind_days=14)

   # Display results with confidence intervals
   forecast_data = context.database.get_forecast(pj.id)
   print(f"Forecast for next 24 hours:")
   print(f"P10: {forecast_data['quantile_P10'].iloc[-96:].mean():.2f}")
   print(f"P50: {forecast_data['quantile_P50'].iloc[-96:].mean():.2f}")
   print(f"P90: {forecast_data['quantile_P90'].iloc[-96:].mean():.2f}")


.. note::

   This demonstrates a complete working forecast pipeline in OpenSTEF with just a few lines of code. The library handles all the complexity of data retrieval, feature engineering, model loading, and prediction generation automatically.


Next Steps
----------


- Explore the tutorials section for step-by-step guides on advanced forecasting techniques

- Browse the API reference documentation for detailed function and class descriptions

- Check out example notebooks and scripts in the examples directory

- Visit the GitHub repository for source code, issues, and contributions

- Join the community discussions for support and best practices sharing


