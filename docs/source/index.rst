OpenSTEF Documentation
======================


What is OpenSTEF?
-----------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting, predicting loads hours to days ahead. As a software package rather than a standalone application, OpenSTEF provides a comprehensive toolkit of machine learning pipelines for data preprocessing, feature engineering, model training, and probabilistic forecasting. The library serves as a foundation for building custom forecasting solutions that can be integrated into larger energy management systems.


.. code-block:: python

   from openstef.model.regressors import XGBOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   import pandas as pd

   # Load your data
   data = pd.read_csv('energy_data.csv', parse_dates=['datetime'])

   # Train a model
   model_specs = {
       'id': 307,
       'model': 'xgb',
       'horizon_minutes': 2880,  # 48 hours
   }

   trained_model = train_model_pipeline(
       pj=model_specs,
       input_data=data,
       mlflow_tracking_uri=None
   )

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=model_specs,
       input_data=data,
       model=trained_model
   )

   print(forecast[['forecast', 'forecast_upper', 'forecast_lower']].head())


Key Features & Use Cases
------------------------


- Quantile forecasting for uncertainty estimation and risk assessment

- Multiple machine learning model types including XGBoost and linear models

- Automated feature engineering with weather data integration

- Modular architecture supporting custom models and transformations

- Backtesting framework for model validation and performance evaluation

- Flexible data preprocessing with configurable input formats

- Type-safe implementation for production reliability

- Extensible design for adding custom metrics and transforms


- Congestion management through accurate peak demand forecasting and proactive demand response

- Grid loss prediction for optimizing electricity distribution efficiency

- Transport system forecasting for capacity planning and resource allocation

- District heating demand forecasting for community energy systems

- EV charging capacity estimation for infrastructure planning

- Free space estimation in energy networks

- MV route congestion analysis with topology-aware forecasting capabilities


Getting Started
---------------


OpenSTEF is a Python library for energy load forecasting using machine learning. Install it via pip with ``pip install openstef``. The library provides tasks for complete workflows including data handling, or pipelines for direct use with your own data management. For detailed setup instructions and hands-on examples, see the Quick Start Guide and explore our comprehensive tutorials to get started with forecasting.


.. note::

   OpenSTEF requires properly prepared time series data as input. Before getting started, review the data requirements and feature engineering documentation to ensure your data is compatible with the library's expected format and structure.


Documentation Structure
-----------------------


- Getting Started - Installation, quick start guide, and basic tutorials for new users

- How-to Guides - Step-by-step instructions for specific forecasting tasks and workflows

- API Reference - Complete technical documentation of OpenSTEF library functions and classes

- Concepts - Theoretical background, forecasting principles, and architectural explanations


Community & Support
-------------------


For support and contributions, visit our `GitHub repository <https://github.com/OpenSTEF/openstef>`_ to report issues or submit pull requests. Join discussions in our community channels or contact the maintainers directly through GitHub. The OpenSTEF team actively monitors these platforms and welcomes feedback from users and contributors.


