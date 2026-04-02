Architecture Overview
=====================

OpenSTEF's architecture is designed around modularity and flexibility. As a Python library, it provides building blocks that you can compose into forecasting workflows suited to your specific needs. This page explains how the components fit together at both the repository and library level.

Understanding the architecture helps you make informed decisions about which components to use, how to extend the library for custom use cases, and how the different packages in the OpenSTEF ecosystem interact.


Repository-Level Architecture
------------------------------

The OpenSTEF project is organized as a mono-repository containing multiple related packages. Each package serves a distinct purpose in the forecasting ecosystem:

.. note::
   [DIAGRAM: Sia-style architecture diagram showing mono-repo structure with openstef (core library), openstef-dbc (database connector), openstef-offline (batch processing), openstef-reference (reference implementation), and openstef-meta (orchestration). Show data flow between components and external systems. Reference: FOSDEM 2026 presentation slide.]

**Core Library (openstef)**
   The main Python library providing machine learning models, feature engineering, and forecasting pipelines. This is what most users interact with directly. It contains no assumptions about data storage, orchestration, or deployment - those are left to the user or to companion packages.

**Database Connector (openstef-dbc)**
   Provides standardized interfaces for retrieving and storing forecast data from various backends. Includes adapters for InfluxDB, SQL databases, and file-based storage. Use this when you need pre-built data connectivity.

**Offline Processing (openstef-offline)**
   Batch processing utilities for training models and generating forecasts at scale. Designed for scheduled jobs and backfilling historical forecasts. Useful for production deployments with orchestration tools like Dagster or Airflow.

**Reference Implementation (openstef-reference)**
   Complete working example of an operational forecasting system. Shows how to combine the core library with data connectors and orchestration. Use this as a starting point for your own deployment.

**Orchestration Metadata (openstef-meta)**
   Configuration and metadata management for multi-model forecasting systems. Tracks which models to train, prediction jobs to run, and system health. Particularly relevant for large-scale deployments with hundreds of forecasting models.

These packages are loosely coupled - you can use the core library standalone, or combine it with other packages as needed. The architecture supports both simple single-model workflows and complex multi-model production systems.


Component-Level Architecture
-----------------------------

Within the core OpenSTEF library, functionality is organized into layers that separate concerns and enable customization at each stage of the forecasting process.

.. note::
   [DIAGRAM: Sia-style component diagram for openstef-meta showing orchestration layer, job scheduling, model registry, prediction coordination, and monitoring. Reference: Community meeting presentation on openstef-meta architecture.]


Data Layer
^^^^^^^^^^

The data layer handles input data preparation and validation. It expects time-series data with load measurements and weather features (temperature, wind speed, solar radiation, etc.).

Key responsibilities:

- **Data validation**: Check for missing values, outliers, and data quality issues
- **Time alignment**: Ensure consistent timestamps and handle timezone conversions
- **Feature preparation**: Structure input data for the feature engineering layer

The data layer is intentionally thin - OpenSTEF expects you to provide clean time-series data. For complex data retrieval scenarios, use openstef-dbc or implement your own data connectors.


Feature Engineering Layer
^^^^^^^^^^^^^^^^^^^^^^^^^

This layer transforms raw time-series data into features suitable for machine learning models. It implements domain knowledge about energy forecasting:

- **Temporal features**: Hour of day, day of week, holidays, and seasonal patterns
- **Weather features**: Temperature effects, wind speed, solar radiation, and derived weather variables
- **Lag features**: Historical load values at relevant time offsets
- **Statistical features**: Rolling averages, trends, and variability measures

The feature engineering pipeline is configurable - you can add custom features or modify existing ones. See the advanced customization tutorial for examples of custom feature engineering.


Model Layer
^^^^^^^^^^^

OpenSTEF supports multiple machine learning models optimized for time-series forecasting:

- **XGBoost**: Default model, excellent performance for most use cases
- **LightGBM**: Faster training for very large datasets
- **Linear models**: Interpretable baseline models
- **Quantile regression**: Produces probabilistic forecasts with confidence intervals

Models are trained on historical data with automatic hyperparameter optimization. The library handles cross-validation, model selection, and performance evaluation internally.

You can also implement custom models by extending the base model interface. This allows integration of deep learning models or domain-specific algorithms while maintaining compatibility with the rest of the pipeline.


Prediction Layer
^^^^^^^^^^^^^^^^

The prediction layer generates forecasts using trained models. It handles:

- **Forecast horizon**: Generate predictions from 15 minutes to several days ahead
- **Quantile forecasts**: Produce confidence intervals alongside point forecasts
- **Fallback strategies**: Use alternative models or historical patterns when primary models fail
- **Energy split decomposition**: Break down forecasts into components (e.g., solar, wind, base load)

Predictions are returned as pandas DataFrames with timestamps, forecast values, and confidence bounds. This makes it easy to integrate forecasts into downstream systems.


Workflow Orchestration
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides workflow primitives for common forecasting tasks:

- **Training workflow**: Load data → engineer features → train model → evaluate performance
- **Prediction workflow**: Load model → prepare input data → generate forecast → post-process results
- **Backtesting workflow**: Iterate over historical periods → train → predict → evaluate accuracy

These workflows are composable building blocks. You can use them as-is for simple scenarios, or customize them for complex production requirements. The openstef-offline package provides higher-level orchestration for batch processing.


Data Flow
---------

A typical forecasting workflow follows this data flow:

1. **Input data** arrives as time-series measurements (load, weather, etc.)
2. **Feature engineering** transforms raw data into model-ready features
3. **Model training** learns patterns from historical data (periodic, e.g., daily or weekly)
4. **Model storage** persists trained models for reuse
5. **Prediction** applies trained models to recent data with weather forecasts
6. **Output forecasts** are delivered to downstream systems (grid operators, optimization tools, etc.)

.. note::
   [DIAGRAM: Sia-style data flow diagram showing the journey from raw input data through feature engineering, model training/storage, prediction, and output delivery. Include feedback loops for model retraining and performance monitoring.]

The architecture separates model training (which happens periodically on historical data) from prediction (which happens frequently with fresh data). This separation enables efficient resource usage - training can run on powerful batch systems while prediction runs on lightweight services.


Extension Points
----------------

OpenSTEF is designed for customization at multiple levels:

**Custom Features**
   Implement your own feature engineering logic by extending the feature pipeline. Useful for domain-specific predictors or proprietary data sources.

**Custom Models**
   Integrate new machine learning models by implementing the model interface. This allows you to use deep learning, ensemble methods, or specialized algorithms while leveraging OpenSTEF's feature engineering and evaluation tools.

**Custom Workflows**
   Build specialized workflows for unique use cases. For example, you might create a workflow that trains separate models for different weather conditions, or one that combines multiple forecasting approaches.

**Custom Data Connectors**
   Implement adapters for your data storage systems. The library is agnostic about where data comes from - you control the data retrieval and storage logic.

See the advanced customization tutorial for concrete examples of extending OpenSTEF.


Deployment Patterns
-------------------

The modular architecture supports various deployment patterns:

**Single-Model Deployment**
   Use the core library directly in a Python script or Jupyter notebook. Train one model, generate forecasts, and integrate results into your systems. Suitable for proof-of-concept work or small-scale deployments.

**Batch Processing**
   Combine openstef-offline with a scheduler (cron, Dagster, Airflow) for automated training and prediction. Train models periodically (e.g., weekly) and generate forecasts frequently (e.g., every 15 minutes).

**Multi-Model System**
   Use openstef-meta to orchestrate hundreds of forecasting models. Centralized configuration tracks which models to train, manages prediction schedules, and monitors system health. Suitable for grid operators forecasting many grid points.

**Microservices**
   Deploy prediction as a REST API service. Train models offline, load them into a prediction service, and serve forecasts on demand. Separates training infrastructure from operational systems.

The architecture doesn't prescribe a deployment pattern - choose what fits your operational requirements and infrastructure.


Related Documentation
---------------------

- :doc:`../getting_started/quickstart` - See the architecture in action with a minimal example
- :doc:`../getting_started/tutorials` - Learn how to customize workflows and extend components
- :doc:`../guides/how_to_guides` - Practical deployment patterns and integration examples
- :doc:`concepts` - Understand the forecasting concepts that inform the architecture