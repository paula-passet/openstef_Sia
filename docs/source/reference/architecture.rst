Architecture Overview
=====================


Repository Architecture
-----------------------


OpenSTEF is a modular machine learning library structured as a mono-repo containing multiple self-contained packages. The architecture includes core modules for data types and interfaces, specialized packages for forecasting models and meta-learning, and evaluation tools for backtesting and analysis. This modular design enables flexible integration while maintaining focus on forecasting functionality.


.. [DIAGRAM: Repository-level Sia-style diagram showing openstef-core, openstef-meta, openstef-reference, openstef-dazls packages and their relationships (based on FOSDEM 2026 slide)]


Core Library Components
-----------------------


The openstef-core library is organized into several key modules that handle different aspects of the forecasting workflow. The pipeline module provides high-level functionality through components like train_model, create_forecast, and optimize_hyperparameters that orchestrate the entire forecasting process. The feature_engineering module contains specialized components for data preparation, weather features, lag features, and holiday features that transform raw input data into model-ready features.

The model module handles machine learning model implementations and training logic, while the data_classes module defines structured data containers like PredictionJobDataClass that standardize data flow between components. The metrics module provides performance evaluation capabilities, and the logging module ensures comprehensive tracking throughout the forecasting pipeline. These modules work together to create a cohesive data flow from raw input through feature engineering to model training and forecast generation.


.. [DIAGRAM: Component-level Sia-style diagram of openstef-core showing data pipeline, feature engineering, model training, and prediction modules with data flow arrows]


Meta Package Architecture
-------------------------


The openstef-meta package serves as the production orchestration layer that coordinates OpenSTEF library components into complete forecasting workflows. It manages the execution of training pipelines, forecast generation, and model evaluation tasks while handling data dependencies and scheduling constraints in enterprise environments.


.. [DIAGRAM: Sia-style diagram of openstef-meta showing workflow orchestration, scheduling, and integration with external systems (similar to community meeting presentations)]


Package Interactions
--------------------


OpenSTEF's modular architecture enables flexible integration patterns. Use openstef-core as the foundation with openstef-models for standard forecasting workflows. Add openstef-meta for advanced ensemble techniques and openstef-beam for rigorous model evaluation. The openstef-reference package provides a complete deployment example, while openstef-offline-example offers Jupyter notebooks for experimentation. Each package complements others - core provides shared interfaces, models handles preprocessing and forecasting, meta adds sophisticated architectures, and beam ensures model quality through comprehensive testing and benchmarking.


- Use openstef-core for building custom integrations and extending OpenSTEF with your own components

- Use openstef-models for standard forecasting tasks with built-in preprocessing and energy-specific transformations

- Use openstef-meta for advanced ensemble models and modern architectures requiring meta-learning capabilities

- Use openstef-beam for model evaluation, backtesting, and regression testing against benchmarks

- Use openstef-reference for complete stack deployment including databases, datamodels, and UI components

- Use openstef-dbc for enterprise environments requiring custom database connectors and company-specific integrations

- Use openstef-offline-example for learning and prototyping with Jupyter notebooks and sample datasets


