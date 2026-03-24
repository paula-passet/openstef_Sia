Architecture Overview
==================

OpenSTEF is designed as a modular Python library that provides the building blocks for creating energy forecasting applications. This page explains the internal structure and design principles that make OpenSTEF flexible, maintainable, and suitable for production use.

.. note::
   OpenSTEF is a **library**, not a deployable application. You integrate OpenSTEF components into your own forecasting system to build custom energy forecasting solutions.

.. [DIAGRAM: Component overview showing relationships between core, models, meta, beam modules and how they integrate into user applications]

Design Principles
=================

Modularity
----------

OpenSTEF follows a layered architecture where each module has clear responsibilities:

- **Core module**: Fundamental data types and interfaces
- **Models module**: Machine learning algorithms and preprocessing
- **Meta module**: Advanced ensemble methods and meta-learning
- **Beam module**: Backtesting, evaluation, and analysis tools

This modular design allows you to use only the components you need. For example, you can use just the core forecasting models without the backtesting infrastructure, or integrate ensemble methods without changing your existing pipeline.

Type Safety
-----------

OpenSTEF uses Python type hints extensively to catch errors at development time and improve code maintainability. Key data structures like ``PredictionJob`` and forecast outputs are strongly typed, making integration safer and more predictable.

Extensibility
-------------

The library provides clear extension points for customization:

- **Custom TargetProvider**: Implement your own data loading logic
- **Custom Models**: Add new machine learning algorithms
- **Custom Features**: Extend the built-in feature engineering
- **Custom Workflows**: Modify training and inference pipelines

Performance
-----------

OpenSTEF is designed for production workloads:

- Efficient data processing using pandas and numpy
- Optimized machine learning models (XGBoost, LightGBM)
- Configurable parallelization for backtesting
- Memory-efficient handling of large time series datasets

Core Components
===============

The OpenSTEF library consists of four main components that work together to provide comprehensive forecasting capabilities.

Core Module (openstef-core)
---------------------------

The foundation layer that defines:

- **Data Schemas**: Standardized formats for input data and forecasts
- **PredictionJob**: Central configuration object that defines forecasting tasks
- **Base Interfaces**: Abstract classes for extending functionality
- **Utility Functions**: Common operations for time series processing

The core module is dependency-light and can be used independently for basic forecasting workflows.

Models Module (openstef-models)
-------------------------------

The machine learning engine that provides:

- **ML Algorithms**: XGBoost, LightGBM, and Linear regression models
- **Feature Engineering**: Automatic creation of lag features, weather variables, and calendar features
- **Preprocessing**: Data cleaning, validation, and transformation
- **Model Explainability**: SHAP integration for understanding feature importance

This module handles the core forecasting logic and is where most users will spend their time when building basic forecasting applications.

Meta Module (openstef-meta)
---------------------------

Advanced forecasting techniques including:

- **Ensemble Methods**: Combining multiple models for improved accuracy
- **Meta-Learning**: Learning from model performance patterns
- **Advanced Feature Selection**: Automated feature importance analysis

The meta module is optional and primarily used for research or when maximum accuracy is required.

Beam Module (openstef-beam)
---------------------------

Evaluation and analysis tools:

- **Backtesting Framework**: Historical model validation
- **Performance Metrics**: Comprehensive evaluation of forecast quality
- **Visualization**: Built-in plotting for forecast analysis
- **Benchmarking**: Comparing different model configurations

The beam module is essential for validating model quality and is typically used during model development and periodic revalidation.

Integration Patterns
====================

OpenSTEF can be integrated into your system in several ways, depending on your needs and infrastructure.

Standalone Usage
----------------

For simple forecasting tasks, you can use OpenSTEF components directly:

.. code-block:: python

   from openstef.models.regressors import XGBOpenstfRegressor
   from openstef.core import PredictionJob
   
   # Configure forecasting job
   job = PredictionJob(...)
   
   # Train model
   model = XGBOpenstfRegressor()
   model.fit(train_data, target)
   
   # Create forecast
   forecast = model.predict(input_data)

This pattern is suitable for experimentation, small-scale deployments, or when you already have your own orchestration infrastructure.

Pipeline Integration
--------------------

For production systems, OpenSTEF provides higher-level pipeline abstractions:

.. code-block:: python

   from openstef.models import train_model, create_forecast
   
   # Higher-level functions handle data preparation and validation
   trained_model = train_model(job, historical_data)
   forecast = create_forecast(job, trained_model, input_data)

This approach handles more of the data processing complexity automatically while still allowing customization through the ``PredictionJob`` configuration.

Custom Combinations
--------------------

You can mix and match OpenSTEF components with your own logic:

.. code-block:: python

   # Use OpenSTEF for feature engineering, your own ML model
   from openstef.core.feature_engineering import apply_feature_engineering
   
   features = apply_feature_engineering(raw_data, job)
   # ... use features with your custom model

This flexibility allows gradual adoption of OpenSTEF in existing systems.

Application Architecture
========================

OpenSTEF fits into a complete forecasting system as the core prediction engine. A typical deployment includes:

.. [DIAGRAM: Typical deployment scenario showing data sources → OpenSTEF library → forecast consumers with orchestration layer]

**Data Layer**: Time series databases, weather APIs, and operational data sources that feed into OpenSTEF.

**OpenSTEF Library**: Handles feature engineering, model training, and forecast generation.

**Orchestration Layer**: Scheduling and workflow management (e.g., Apache Airflow, Dagster, or cron jobs) that coordinates data ingestion, model training, and forecast generation.

**Storage Layer**: Databases or file systems for storing trained models and forecast outputs.

**Consumer Applications**: Downstream systems that use forecasts for operational decisions, visualization, or further analysis.

This architecture separates concerns clearly: OpenSTEF focuses on the forecasting logic while your application handles data integration, scheduling, and business logic.

Next Steps
==========

- See :doc:`repo_structure` for detailed information about the mono-repo organization
- Visit :doc:`../user_guide/tutorials` for hands-on examples of using different components
- Check :doc:`../how_to_guides/index` for specific integration patterns and deployment strategies