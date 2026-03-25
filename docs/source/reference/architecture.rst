Architecture Overview
=====================


Repository Architecture
-----------------------


OpenSTEF is a Python library built as a monorepo containing multiple interconnected packages that work together to provide comprehensive short-term forecasting capabilities. The core openstef package includes specialized modules for data processing, feature engineering, machine learning models, and evaluation metrics. Additional companion packages like OpenSTEF-dbc provide database connectivity, while OpenSTEF-reference offers a complete reference implementation. These components integrate through high-level pipelines that orchestrate model training, forecasting, and evaluation workflows.


.. [DIAGRAM: Repository-level architecture showing core packages (openstef, openstef-dbc, openstef-reference) and their relationships]


Core Library Architecture
-------------------------


The OpenSTEF library is organized into five core modules that handle distinct aspects of forecasting workflows. The data_classes module defines structured data containers for prediction jobs, model specifications, and data preparation configurations. The feature_engineering module provides comprehensive tools for creating time-series features including weather data, lag variables, rolling statistics, and holiday indicators. The model module contains machine learning components including base models, metamodels, confidence intervals, and fallback mechanisms. The pipeline module offers high-level workflows for training models, creating forecasts, hyperparameter optimization, and backtesting. The metrics module handles performance evaluation through statistical metrics, visualization tools, and reporting functionality.


.. [DIAGRAM: Core library architecture showing modules like data_classes, feature_engineering, model, pipeline, and their interactions]


Forecasting Pipeline Flow
-------------------------


The OpenSTEF forecasting pipeline processes data through four sequential steps. Feature engineering selects and creates required features based on prediction job configuration, such as historical load data from previous days or weeks. Machine learning performs model training or forecasting using algorithms like XGBoost quantile models. Model storage handles trained model persistence and retrieval through MLFlow integration. Post processing combines forecast results with configuration metadata and can split aggregate forecasts into component predictions for solar, wind, and energy usage.


.. [DIAGRAM: Pipeline flow diagram showing data ingestion → feature engineering → model training/prediction → forecast output]


Component Integration Points
----------------------------


OpenSTEF provides multiple integration patterns for custom implementations. The library integrates with external systems through database connectors like OpenSTEF-dbc, which provides interfaces for reading and writing data. Custom data fetchers can be implemented to pull input data from various sources and write to databases. Extension points include custom forecaster components that fetch configuration and data to run OpenSTEF tasks, and data APIs that provide standardized access to forecasts and input data for downstream applications.


.. [DIAGRAM: Integration architecture showing how external data sources, schedulers, and storage systems connect to OpenSTEF components]


