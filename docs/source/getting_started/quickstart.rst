Quick Start
===========


Installation
------------


OpenSTEF is a Python library designed for short-term energy forecasting in the energy sector. The library provides all components needed for a complete machine learning pipeline to generate accurate energy load forecasts.


.. code-block:: bash

   pip install openstef


Load Sample Data
----------------


.. code-block:: python

   from openstef.data_classes.model_specifications import ForecastInputDataset
   from openstef.tests.unit.models.conftest import sample_forecast_input_dataset

   # Load sample dataset with realistic energy consumption patterns
   dataset = sample_forecast_input_dataset()

   # Access the data
   print(f"Dataset shape: {dataset.data.shape}")
   print(f"Available columns: {list(dataset.data.columns)}")
   print(dataset.data.head())


Train Your First Model
----------------------


.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline_core
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.data_classes.model_specifications import ModelSpecificationDataClass
   import pandas as pd

   # Create prediction job and model specifications
   pj = PredictionJobDataClass(id=1, name="example_job")
   model_specs = ModelSpecificationDataClass()

   # Load your input data
   input_data = pd.read_csv("your_data.csv")

   # Train the model with default settings
   trained_model = train_model_pipeline_core(
       pj=pj,
       model_specs=model_specs,
       input_data=input_data
   )


Create a Forecast
-----------------


.. code-block:: python

   import pandas as pd
   import numpy as np
   from openstef.tasks.create_forecast import create_forecast_task
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   from openstef.tasks.utils.taskcontext import TaskContext

   # Create sample prediction job
   pj = PredictionJobDataClass(
       id=1,
       name="example_forecast",
       lat=52.0,
       lon=4.0,
       resolution_minutes=15,
       horizon_minutes=2880,
       type="load",
       quantiles=[0.1, 0.5, 0.9]
   )

   # Initialize context with your config and database
   context = TaskContext(config=your_config, database=your_database)

   # Generate forecast
   create_forecast_task(pj, context, t_behind_days=14)

   # The forecast is automatically stored in the database
   # Retrieve and display results
   forecast_data = context.database.get_forecast(pj.id)
   print(f"Generated forecast for {pj.name}")
   print(f"Forecast horizon: {pj.horizon_minutes} minutes")
   print(forecast_data.head())


The forecast output contains predicted values with timestamps, typically including quantiles for uncertainty estimation. Results are automatically written to the configured database and can be accessed for further analysis. For production deployments, integrate the forecasting tasks into your scheduling system using the main functions provided by each forecast module.


Next Steps
----------


- Check out the User Guide for detailed tutorials on forecasting workflows

- Explore the API Reference for complete function documentation and parameters

- Visit the Examples section for real-world use cases and code samples

- Read the Configuration Guide to customize OpenSTEF for your specific needs

- Review the Data Requirements section to prepare your input datasets


