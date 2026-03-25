OpenSTEF Documentation
======================


What is OpenSTEF?
-----------------


OpenSTEF is a Python machine learning library designed for short-term energy system forecasting. As a software package, it provides complete pipelines for data preprocessing, feature engineering, model training, and probabilistic forecasting. OpenSTEF is not a standalone application but requires integration with additional components like data fetchers, APIs, and scheduling systems to function as a complete forecasting solution.


.. code-block:: python

   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Load your energy load data
   load_data = pd.read_csv('energy_loads.csv', parse_dates=['datetime'])

   # Train a forecasting model
   model_config = {
       'model': 'xgb_quantile',
       'quantiles': [0.1, 0.5, 0.9],
       'horizon_minutes': 2880  # 48 hours ahead
   }

   trained_model = train_model_pipeline(
       pj=load_data,
       model_type='xgb_quantile',
       quantiles=[0.1, 0.5, 0.9]
   )

   # Create probabilistic forecasts
   forecast = create_forecast_pipeline(
       pj=load_data,
       model=trained_model,
       horizon_minutes=2880
   )

   print(f"Forecast shape: {forecast.shape}")
   print(f"Confidence intervals: {forecast.columns.tolist()}")


Key Capabilities
----------------


- Congestion management and peak load forecasting

- Grid loss prediction and optimization

- Transport system energy demand forecasting

- District heating load prediction

- EV charging capacity estimation

- Free space estimation for grid planning

- MV route congestion analysis with topology-aware forecasting


.. image:: _static/images/placeholder_example_forecast_visualization_showing_multiple_prediction_types.png
   :alt: Example forecast visualization showing multiple prediction types
   :align: center


Quick Start
-----------


.. code-block:: bash

   pip install openstef

   import pandas as pd
   from openstef.pipeline.train_model import TrainModelPipeline
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor

   # Load your data
   data = pd.read_csv('energy_data.csv')

   # Configure prediction job
   config = {
       'id': 123,
       'name': 'solar_forecast',
       'model': 'xgb',
       'quantiles': [0.1, 0.5, 0.9],
       'horizon_minutes': 2880
   }

   # Initialize and run training pipeline
   pipeline = TrainModelPipeline(config)
   model = pipeline.run(data)


For a comprehensive introduction to using the OpenSTEF library, including detailed installation instructions, basic usage examples, and step-by-step tutorials, visit our Getting Started guide in the tutorials section. This guide covers everything from initial setup to running your first forecasting pipeline.


Documentation Structure
-----------------------


- Tutorials - Step-by-step guides for getting started with OpenSTEF forecasting workflows

- How-to Guides - Practical solutions for specific forecasting tasks and common use cases

- API Reference - Complete documentation of OpenSTEF classes, functions, and parameters

- Concepts - Understanding forecasting principles, model types, and OpenSTEF architecture


.. [DIAGRAM: Documentation organization flowchart showing user journey from beginner to advanced]


Community & Support
-------------------


The OpenSTEF community welcomes contributions and provides multiple support channels. Find the main repository and related projects at GitHub.com/OpenSTEF/. Join four-weekly community meetings to discuss progress and collaboration opportunities. For bugs or feature requests, open issues on GitHub. Get support through the OpenSTEF Teams channel or community support page. Review contributing guidelines before submitting code contributions.


.. note::

   OpenSTEF is an open source library that welcomes contributions in all forms. Whether you want to contribute code, report bugs, or request features, the community encourages participation from developers and users alike.


