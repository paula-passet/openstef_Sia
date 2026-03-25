OpenSTEF Documentation
======================


What is OpenSTEF?
-----------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting. As a software package, it provides complete pipelines for data preprocessing, feature engineering, model training, and probabilistic forecasting. OpenSTEF is not a standalone application but rather a library that requires integration with additional components like data fetchers, APIs, and schedulers to create a full forecasting system.


- Congestion forecasts to predict grid overload and enable proactive load management

- Free space estimation to determine available grid capacity for new connections

- Grid loss forecasts to optimize energy distribution efficiency

- Transport forecasts for energy flow predictions across transmission networks

- District heating load forecasts for thermal energy distribution systems


Quick Example
-------------


Getting started with OpenSTEF is straightforward. This Python library provides simple interfaces for energy forecasting tasks. The following example demonstrates how to train a model and generate forecasts with just a few lines of code, showcasing the library's ease of use for machine learning-based energy load predictions.


.. code-block:: python

   import pandas as pd
   from openstef.tasks import create_forecast_task, train_model_task
   from openstef.model.regressors import XGBQuantileOpenstfRegressor

   # Load your data
   input_data = pd.read_csv('energy_data.csv', index_col=0, parse_dates=True)

   # Define prediction job configuration
   pj = {
       'id': 307,
       'name': 'wind_solar_forecast',
       'model': 'xgb',
       'horizon_minutes': 2880,
       'resolution_minutes': 15
   }

   # Train a model
   model = train_model_task.main(pj, input_data)

   # Create forecast
   forecast = create_forecast_task.main(pj, input_data, model)

   print(f"Forecast shape: {forecast.shape}")
   print(forecast.head())


Documentation Structure
-----------------------


- Getting Started - Quick installation and basic setup to begin using the OpenSTEF library

- Tutorials - Step-by-step guides for common forecasting workflows and model training

- How-to Guides - Practical solutions for specific tasks and integration scenarios

- API Reference - Complete documentation of classes, functions, and parameters

- Architecture - Technical overview of OpenSTEF's design and core components

- Use Cases - Real-world applications and implementation examples

- Concepts - Fundamental principles of short-term energy forecasting

- FAQ - Frequently asked questions and troubleshooting tips


Installation
------------


.. code-block:: bash

   pip install openstef

   # For development installation with additional dependencies
   pip install openstef[dev]

   # Install from source
   git clone https://github.com/OpenSTEF/openstef.git
   cd openstef
   pip install -e .


.. note::

   For advanced installation options including database setup, containerization, and deployment configurations, see the detailed installation guide in the OpenSTEF documentation.


Community and Support
---------------------


Welcome to the OpenSTEF community! We provide multiple support channels to help you succeed with this forecasting library. For technical questions and discussions, visit our GitHub repository where you can open issues, browse documentation, and connect with other users. Our community is here to support your implementation and answer questions about forecasting workflows.


- GitHub Repository: https://github.com/OpenSTEF/openstef

- Issue Tracker: Report bugs and request features on GitHub Issues

- Discussions: Join community discussions on GitHub Discussions

- Documentation: Complete guides and API reference at openstef.readthedocs.io

- Contact: Reach the development team via GitHub or project maintainers


