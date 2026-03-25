OpenSTEF Documentation
======================


Welcome to OpenSTEF
-------------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting on electrical grids. Rather than a standalone application, OpenSTEF serves as a comprehensive toolkit that provides the core components needed to build custom forecasting solutions. The library offers modular pipelines for training models, generating predictions, and evaluating performance, allowing developers to integrate forecasting capabilities into their existing systems and workflows.


- Congestion forecasts for grid capacity planning and load management

- Free space estimation to optimize available grid capacity

- Grid loss forecasts for transmission and distribution efficiency

- Transport forecasts for electric vehicle charging infrastructure

- District heating demand predictions for thermal energy systems

- Medium voltage route management for distribution network optimization


Quick Start
-----------


.. code-block:: python

   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Load your data (load, weather features, etc.)
   data = pd.read_csv('energy_data.csv', index_col='datetime', parse_dates=True)

   # Apply feature engineering
   data_with_features = apply_features(data, horizons=[0.25, 24.0])

   # Train model
   model = train_model_pipeline(
       data_with_features,
       model_type='xgb_quantile',
       horizons=[0.25, 24.0]
   )

   # Create forecast
   forecast = create_forecast_pipeline(
       model=model,
       input_data=data_with_features.tail(48),
       horizons=[0.25, 24.0]
   )

   print(forecast)


For detailed implementation guidance, explore the comprehensive User guides section which covers installation, configuration, and advanced usage patterns. The Architecture, Methodology, and Components section provides essential background on OpenSTEF's machine learning pipeline and forecasting methodology before diving into practical implementation.


Documentation Contents
----------------------


.. toctree::
   :maxdepth: 2
   :caption: Contents


   getting-started/index

   tutorials/index

   how-to-guides/index

   concepts/index

   api-reference/index

   architecture/index

   faq/index


Architecture Overview
---------------------


.. [DIAGRAM: High-level architecture showing OpenSTEF library components and their relationships in the monorepo]


OpenSTEF follows a modular mono-repo architecture with self-contained packages that can be used independently or combined. The core library provides data types and interfaces, while specialized modules handle forecasting models, meta-learning, and evaluation. This unopinionated design allows users to integrate specific components into existing workflows or deploy the complete forecasting stack. Each module maintains clear boundaries while sharing common foundations through the core package.


Community and Support
---------------------


- GitHub Repository: https://github.com/OpenSTEF/openstef

- Issue Tracker: Report bugs and request features on GitHub Issues

- Discussions: Join community conversations on GitHub Discussions

- Contributing Guide: Read CONTRIBUTING.md for development guidelines

- Documentation: Latest docs at https://openstef.readthedocs.io


OpenSTEF thrives on community collaboration and welcomes contributions from developers, researchers, and energy professionals. Join our discussions on GitHub to share ideas, report issues, or contribute code. For technical support or partnership inquiries, contact the development team through our official channels.


