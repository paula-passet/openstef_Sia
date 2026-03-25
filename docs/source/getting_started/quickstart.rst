Quick Start
===========


Installation
------------


OpenSTEF is a Python library for forecasting energy loads on the energy grid using machine learning. The library provides tasks and pipelines for training models, generating forecasts, and performing evaluations with confidence estimates.

.. code-block:: bash

    pip install openstef


.. code-block:: bash

   pip install openstef


Load Sample Data
----------------


OpenSTEF includes built-in sample datasets to help you get started quickly. These samples contain realistic input data and pre-prepared features that demonstrate the library's forecasting capabilities. The sample data allows you to explore OpenSTEF's single-shot, multi-horizon forecasting methodology without needing to prepare your own datasets first.


.. code-block:: python

   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Load sample prediction job configuration
   prediction_job = PredictionJob(
       id=307,
       name="sample_wind_farm",
       model="xgb",
       resolution_minutes=15,
       forecast_type="wind",
       train_components=0.95
   )

   # Train model with sample data
   model_specs = train_model_pipeline(prediction_job, input_data)

   # Create forecast
   forecast = create_forecast_pipeline(prediction_job, model_specs, input_data)


Train Your First Model
----------------------


Model training in OpenSTEF combines input data preparation with feature engineering to create forecasting models. The library uses pipelines that handle data validation, feature selection, and machine learning model training based on your prediction job configuration. This single-shot approach enables multi-horizon forecasting with confidence estimates.


.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   import pandas as pd

   # Create prediction job with default settings
   pj = PredictionJobDataClass(
       id=1,
       name="example_forecast",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15
   )

   # Load your training data
   train_data = pd.read_csv("your_training_data.csv")
   train_data["datetime"] = pd.to_datetime(train_data["datetime"])

   # Train the model
   model, report, modelspecs = train_model_pipeline_core(pj, train_data)


Create a Forecast
-----------------


Once your model is trained, generate forecasts by calling the predict method on your forecaster instance with input data. The OpenSTEF library returns predictions as a ForecastDataset containing forecast values, confidence intervals, and timestamps for the specified prediction horizon.


.. code-block:: python

   from openstef.model.forecaster import create_forecaster
   from openstef.data.weather import WeatherDataLoader
   import pandas as pd

   # Load training data
   train_data = pd.read_csv('energy_data.csv', parse_dates=['datetime'])
   train_data.set_index('datetime', inplace=True)

   # Create and train forecaster
   forecaster = create_forecaster('xgb')
   forecaster.fit(train_data)

   # Generate forecast
   forecast_input = train_data.tail(48)  # Last 48 hours
   forecast = forecaster.predict(forecast_input, horizon_hours=24)

   # Display results
   print("Forecast Results:")
   print(forecast[['forecast', 'forecast_upper', 'forecast_lower']].head(10))
   print(f"\nForecast period: {forecast.index[0]} to {forecast.index[-1]}")


Next Steps
----------


Now that you've completed the basic setup, explore the comprehensive tutorials and guides in our documentation. The user guide covers advanced forecasting techniques, model customization, and integration patterns. API reference documentation provides detailed information about all OpenSTEF library functions and classes.


- Read the User Guide for comprehensive tutorials and examples

- Explore the API Reference for detailed function documentation

- Check the Configuration Guide for advanced setup options

- Visit the Examples section for real-world use cases

- Review the Developer Guide for contributing to OpenSTEF


