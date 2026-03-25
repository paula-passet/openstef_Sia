Architecture Overview
=====================


Repository Architecture
-----------------------


OpenSTEF is organized as a modular mono-repo containing multiple self-contained packages that work together to provide comprehensive forecasting capabilities. The repository includes the core OpenSTEF library for machine learning-based forecasting, database connectors for enterprise integration, reference implementations for complete stack deployment, and offline examples with Jupyter notebooks demonstrating practical usage scenarios.


.. [DIAGRAM: Repository-level architecture showing core packages (openstef), example implementations, and supporting tools]


Core Library Architecture
-------------------------


The OpenSTEF library is organized into several core modules that handle distinct aspects of energy forecasting. The `openstef.pipeline` module provides high-level functionality through pipelines for training models, creating forecasts, and optimizing hyperparameters. The `openstef.feature_engineering` module contains specialized components for data preparation, weather features, lag features, and missing value handling. The `openstef.model` module manages machine learning models, including basecase models, confidence intervals, and metamodels. Supporting modules include `openstef.data_classes` for data structures, `openstef.metrics` for evaluation, and `openstef.logging` for structured logging capabilities.


.. [DIAGRAM: Core library architecture showing model, pipeline, feature engineering, and data handling components]


Data Flow and Processing Pipeline
---------------------------------


OpenSTEF processes data through a structured pipeline workflow that transforms raw input data into accurate forecasts. The process begins with data ingestion, where historical load data and weather features are collected and prepared. Feature engineering then creates additional predictive variables such as lagged values and temporal features based on the prediction job configuration. The prepared dataset flows through model training using algorithms like XGBoost, with automatic train-validation-test splitting. Finally, the trained model generates forecasts through the create_forecast pipeline, with optional post-processing to combine results with configuration metadata or decompose forecasts into component predictions.


.. [DIAGRAM: Data flow diagram showing input data → feature engineering → model training/prediction → forecast output]


Component Integration Patterns
------------------------------


OpenSTEF integrates with enterprise systems through modular deployment patterns that accommodate diverse infrastructure requirements. The library supports three primary integration approaches: standalone deployment using openstef-offline-example for isolated environments, database-connected deployment via openstef-dbc for enterprise data sources, and full-stack deployment through openstef-reference for complete forecasting solutions.

The modular mono-repo architecture enables flexible integration strategies where organizations can adopt individual packages based on their specific needs. Core modules provide foundational forecasting capabilities while specialized packages like openstef-beam offer backtesting and evaluation features. This design allows seamless integration with existing MLOps pipelines, custom APIs, and enterprise data platforms without compromising the library's performance or model quality.


.. [DIAGRAM: Integration architecture showing OpenSTEF library connected to data sources, schedulers, and output systems]


