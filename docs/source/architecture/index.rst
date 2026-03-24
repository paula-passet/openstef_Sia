Architecture Overview
=====================

OpenSTEF is designed as a modular Python library that provides the building blocks for energy forecasting applications. Understanding its architecture will help you effectively integrate OpenSTEF into your systems and customize it for your specific use cases.

.. note::
   OpenSTEF is a **library**, not a deployable application. You use OpenSTEF components to build your own forecasting applications and workflows.

Core Architecture Principles
-----------------------------

OpenSTEF follows several key architectural principles:

**Modularity First**
   Components work in isolation and can be easily composed into larger systems.

**Type Safety**
   Full type safety throughout the codebase to catch bugs early and improve maintainability.

**Extensibility**
   Clear interfaces for adding custom models, transforms, and metrics without modifying core code.

**Performance**
   Efficient implementations optimized for production use cases.

High-Level Components
---------------------

OpenSTEF consists of several main components that work together:

**Prediction Jobs**
   Input configuration for tasks and pipelines (e.g., train an XGB model for a specific location).

**Tasks**
   High-level operations that handle data fetching, processing, and storage. Tasks use pipelines internally and include database interactions and exception handling.

**Pipelines**
   Core processing logic for training, forecasting, and evaluation. Pipelines work with data you provide directly.

**Data Validation**
   Validates input data quality and detects issues like flatliners or missing values.

**Feature Engineering**
   Selects and creates features for training and forecasting based on prediction job configuration.

**Machine Learning**
   Performs model training, forecasting, and evaluation using various algorithms like XGBoost and LightGBM.

Available Pipelines
-------------------

OpenSTEF provides several pre-built pipelines for common forecasting workflows:

- ``openstef.pipeline.train_model`` - Train machine learning models
- ``openstef.pipeline.create_forecast`` - Generate forecasts from trained models  
- ``openstef.pipeline.optimize_hyperparameters`` - Tune model parameters
- ``openstef.pipeline.create_component_forecast`` - Create component-specific forecasts
- ``openstef.pipeline.create_basecase_forecast`` - Generate baseline forecasts
- ``openstef.pipeline.train_create_forecast_backtest`` - Combined training and backtesting

Tasks vs Pipelines
-------------------

OpenSTEF offers two levels of abstraction:

**Tasks** (Higher Level)
   - Handle data fetching from databases
   - Manage data writing and storage
   - Include error handling and logging
   - Best for operational deployments

**Pipelines** (Lower Level)  
   - Work with data you provide directly
   - Focus purely on ML operations
   - More flexible for custom workflows
   - Best for research and experimentation

Choose tasks when you want OpenSTEF to handle data management, or use pipelines directly when you need full control over data flow.

Application Integration
-----------------------

To deploy OpenSTEF as a complete forecasting application, you typically need additional components:

**Data Fetcher**
   Software to collect input data (weather, load measurements) and store it in a database.

**Data API**
   REST API or similar interface to provide data to applications and users.

**Forecaster**
   Scheduled jobs (e.g., cron, Kubernetes) that run OpenSTEF tasks and pipelines.

**OpenSTEF Library**
   The core machine learning components for training models and generating forecasts.

Forecasting Methodology
------------------------

OpenSTEF supports single-shot, multi-horizon forecasting with confidence estimates. The library provides two methods for confidence estimation and includes comprehensive feature engineering capabilities.

For detailed information about the forecasting methodology, see :doc:`../user_guide/intro/methodology_train_predict`.

Next Steps
----------

- :doc:`../user_guide/quick_start` - Get started with OpenSTEF in minutes
- :doc:`../user_guide/tutorials` - Step-by-step guides for common tasks
- :doc:`../api/index` - Complete API reference
- :doc:`../examples` - Jupyter notebook examples with sample data

.. toctree::
   :maxdepth: 1
   :hidden:
   
   Repository Structure <repo_structure>