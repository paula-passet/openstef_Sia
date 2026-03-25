OpenSTEF Documentation
======================


What is OpenSTEF?
-----------------


OpenSTEF is a Python machine learning library designed specifically for short-term energy forecasting in the energy sector. As a comprehensive software package, it provides all the essential components needed to build a complete machine learning pipeline for forecasting energy loads on the electrical grid. The library enables users to create accurate, multi-horizon forecasts with confidence estimates, making it a powerful tool for energy system operators, utilities, and researchers who need reliable predictions for grid management and planning.


.. note::

   OpenSTEF is a Python library, not a standalone application. To use OpenSTEF as a complete forecasting solution, you need to integrate it with additional components such as data fetchers, APIs, and schedulers. For a ready-to-use implementation, see the OpenSTEF-reference repository which provides a complete stack deployment.


Short-term energy forecasting is the process of predicting energy demand and supply patterns over relatively brief time horizons, typically ranging from minutes to several days ahead. In the energy sector, accurate short-term forecasts are critical for maintaining grid stability, optimizing energy trading decisions, managing renewable energy integration, and ensuring efficient resource allocation. These forecasts enable energy operators to anticipate load fluctuations, balance supply and demand in real-time, and make informed decisions about energy dispatch and storage. As energy grids become increasingly complex with the integration of renewable sources and distributed generation, the ability to predict short-term energy patterns has become essential for reliable and cost-effective grid operations.


Key Features
------------


- Multiple machine learning algorithms with automated pipeline selection

- Quantile forecasting for probabilistic predictions and risk-based decision making

- Automated feature engineering from weather data and historical load patterns

- Multi-horizon forecasting with single-shot prediction capability

- Resilient forecasting with multiple fallback strategies to ensure forecast availability

- Component-based forecasting to separate wind, solar, and conventional energy sources

- Cloud-native and platform-agnostic containerized deployment

- Confidence estimation methods for forecast reliability assessment


OpenSTEF supports flexible forecast horizons and update frequencies to meet diverse operational needs in the energy sector. The library's single-shot, multi-horizon forecasting capability allows users to generate predictions spanning from minutes ahead to several days, with typical implementations running forecasts every 15 minutes to hourly intervals. This frequent updating ensures that forecasts remain current with changing weather conditions and grid dynamics, while the multi-horizon approach provides both short-term operational guidance and longer-term planning insights in a single model run.


Common Use Cases
----------------


- Congestion forecasts for proactive grid management and demand response to prevent overloads

- Free space estimation to determine available capacity on electrical infrastructure

- Grid loss forecasts to predict energy losses in transmission and distribution networks

- Transport forecasts for energy demand prediction in transportation systems

- District heating forecasts for community heating system optimization


OpenSTEF serves a wide range of energy forecasting applications, from traditional grid congestion management to emerging use cases like EV charging capacity estimation and district heating. The library has been successfully deployed for transport forecasts, grid loss predictions, and topology-aware MV route congestion analysis. Whether you're a researcher working in Jupyter notebooks, managing small-scale deployments, or building enterprise-level forecasting systems, OpenSTEF's flexible architecture can be adapted to your specific needs. For detailed examples and implementation guidance across these various applications, see our comprehensive use cases documentation.


Quick Example
-------------


This example demonstrates the core functionality of the OpenSTEF library for creating short-term energy forecasts. OpenSTEF combines input data preparation, feature engineering, and machine learning to enable single-shot, multi-horizon forecasting with confidence estimates. The following code shows how to train a model and generate predictions using the library's main components.


.. code-block:: python

   ```python
   import pandas as pd
   from openstef.model.regressors import XGBOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Load your data (example structure)
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)

   # Define prediction job configuration
   pj = {
       'id': 123,
       'name': 'solar_forecast',
       'model': 'xgb',
       'horizon_minutes': 2880,  # 48 hours
       'resolution_minutes': 15,
       'feature_names': ['radiation', 'temperature', 'wind_speed']
   }

   # Train the model
   model_specs = train_model_pipeline(
       pj=pj,
       input_data=data,
       check_hyper_params=True
   )

   # Create forecast
   forecast = create_forecast_pipeline(
       pj=pj,
       input_data=data,
       model_specs=model_specs
   )

   print(f"Forecast shape: {forecast.shape}")
   print(f"Forecast columns: {forecast.columns.tolist()}")
   ```


For a comprehensive guide on getting started with OpenSTEF, including detailed installation instructions, data preparation, and step-by-step tutorials, visit the User guides section. If you're new to OpenSTEF, we also recommend reading the Architecture, Methodology, and Components section to understand the library's core concepts and design principles.


Documentation Structure
-----------------------


This documentation is organized to serve different types of users and use cases. Whether you're a data scientist looking to implement forecasting models, a developer integrating OpenSTEF into your applications, or a system administrator deploying the library, you'll find dedicated sections tailored to your needs. The structure progresses from basic concepts and installation through practical tutorials, comprehensive API reference, and advanced deployment scenarios.


- **Getting Started** - Quick installation guide and basic usage examples to get you up and running with OpenSTEF

- **User Guide** - Comprehensive tutorials and workflows for forecasting, validation, and model optimization

- **API Reference** - Complete documentation of all classes, functions, and modules in the OpenSTEF library

- **Examples** - Real-world use cases and code samples demonstrating OpenSTEF capabilities

- **Contributing** - Guidelines for developers who want to contribute to the OpenSTEF project

- **Release Notes** - Latest updates, new features, and breaking changes across OpenSTEF versions


Getting Started Paths
---------------------


OpenSTEF offers multiple learning paths depending on your background and goals. If you're new to forecasting, start with the Concepts section to understand the fundamentals of short-term energy forecasting and how OpenSTEF approaches common challenges. For hands-on learners, jump directly to the Quick Start guide to get a basic forecast running in minutes. Developers integrating OpenSTEF into existing systems should begin with the API Reference to understand the library's interface and capabilities. Data scientists and researchers may prefer starting with the Advanced Usage section to explore customization options and model tuning. Each path eventually converges on the comprehensive User Guide, which covers all aspects of using OpenSTEF effectively in production environments.


- **Beginners**: Start with the :doc:`quickstart` guide to understand OpenSTEF's core concepts and run your first forecast

- **Experienced ML practitioners**: Jump to :doc:`tutorials/index` for hands-on examples and explore the :doc:`reference/api` for advanced customization

- **System integrators**: Review :doc:`installation` requirements and :doc:`reference/configuration` for deployment considerations


Community and Support
---------------------


The OpenSTEF community offers multiple channels for support, collaboration, and engagement. Whether you're looking for technical assistance, want to contribute to the project, or need help implementing OpenSTEF in your environment, our active community provides various resources to help you succeed. The project maintains regular community meetings every four weeks where participants discuss progress, refine open issues, and explore collaboration opportunities - these meetings are open to anyone interested in the project. For direct support, you can reach out through the OpenSTEF Teams channel or explore the comprehensive support options available through our community channels. The project is governed by a Technical Steering Committee that guides the overall direction and development, ensuring OpenSTEF continues to evolve to meet the needs of its users and contributors.


- GitHub Issues - Report bugs or request features at https://github.com/OpenSTEF/openstef/issues

- Community Forums - Join discussions in the OpenSTEF Teams channel for questions and support

- Four-weekly Community Meetings - Open meetings to discuss progress, issues, and collaboration opportunities

- Technical Steering Committee - Contact the TSC for project governance and strategic direction matters


OpenSTEF welcomes contributions in all forms from the community! Whether you're interested in contributing code, reporting bugs, requesting features, or participating in discussions, there are many ways to get involved. The project maintains contributing guidelines to help you get started with code contributions, and you can open issues on GitHub for bug reports or feature requests. The community holds four-weekly meetings that are open to anyone interested in discussing progress, refining open issues, and exploring collaboration possibilities. For support and questions, you can engage through the community support channels or join the OpenSTEF Teams channel. The Technical Steering Committee provides governance and direction for the project, ensuring that community input helps shape the future development of this open-source forecasting library.


License and Attribution
-----------------------


OpenSTEF is licensed under the Mozilla Public License, version 2.0 (MPL-2.0), making it freely available for use, modification, and distribution. As an open source Python library, OpenSTEF can be integrated into both commercial and non-commercial projects while maintaining the copyleft requirements of the MPL-2.0 license. Users are free to use OpenSTEF for forecasting energy loads, modify the source code to suit their specific needs, and distribute their modifications, provided they comply with the license terms which require that any modifications to OpenSTEF source files be made available under the same license.


OpenSTEF is developed and maintained by a collaborative community of contributors. The project is supported by various organizations in the energy sector who contribute to its development and provide valuable feedback. Special recognition goes to the teams and individuals who have contributed code, documentation, testing, and domain expertise to make OpenSTEF a robust forecasting library. The project benefits from contributions across multiple repositories including the core OpenSTEF package, database connectors, reference implementations, and educational materials, all of which can be found on the OpenSTEF GitHub organization page.


