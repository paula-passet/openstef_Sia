What is OpenSTEF
================

OpenSTEF is an open-source Python library for short-term energy forecasting. It provides the building blocks for training machine learning models and generating probabilistic forecasts for energy systems.

.. note::
   **OpenSTEF is a library, not an application.** You cannot simply install and run OpenSTEF as a standalone application. Instead, you use OpenSTEF's components to build your own forecasting applications and workflows.

What OpenSTEF Is
-----------------

OpenSTEF is a comprehensive machine learning library that provides:

* **Forecasting Pipeline Components**: Complete machine learning pipeline including data validation, feature engineering, model training, and prediction generation
* **Multiple Model Types**: Support for XGBoost, LightGBM, and linear models optimized for different use cases and aggregation levels
* **Probabilistic Forecasts**: Quantile-based predictions that provide uncertainty estimates alongside point forecasts
* **Energy-Specific Features**: Built-in feature engineering tailored for energy forecasting, including weather dependencies and temporal patterns
* **Backtesting Framework**: Tools for evaluating model performance over historical data
* **Modular Architecture**: Composable components that can be used independently or as part of larger systems

.. [DIAGRAM: Typical deployment scenario with user application using OpenSTEF library]

What OpenSTEF Is NOT
---------------------

To avoid common misconceptions:

* **Not a Deployable Application**: OpenSTEF does not include a user interface, web server, or standalone executable. You must build these components yourself.
* **Not a Pre-trained Model**: OpenSTEF does not come with ready-to-use models. You train your own models using your data.
* **Not a Complete Solution**: OpenSTEF focuses on the machine learning components. You need additional infrastructure for data ingestion, scheduling, monitoring, and result delivery.
* **Not a Real-time System**: OpenSTEF generates forecasts when called, but does not include scheduling, alerting, or automated execution capabilities.

Core Purpose and Design Philosophy
-----------------------------------

OpenSTEF is designed around several key principles:

**Modularity First**
   Components work in isolation and can be easily composed into larger systems. You can use individual pipelines, combine multiple components, or integrate OpenSTEF into existing workflows.

**Type Safety**
   Full type safety throughout the codebase helps catch bugs early and improves maintainability in production environments.

**Extensibility**
   Clear interfaces allow you to add custom models, transforms, and metrics without modifying core OpenSTEF code.

**Energy Domain Expertise**
   Built-in understanding of energy forecasting challenges, including weather dependencies, seasonal patterns, and grid-specific requirements.

Typical Integration Patterns
-----------------------------

OpenSTEF integrates into energy forecasting systems in several common ways:

**Research and Experimentation**
   Use OpenSTEF components in Jupyter notebooks for model development, backtesting, and analysis.

**Small-Scale Deployments**
   Build simple applications using OpenSTEF pipelines with cron jobs or basic orchestration tools.

**Enterprise Integration**
   Integrate OpenSTEF into existing data platforms, workflow orchestrators, and monitoring systems.

.. [DIAGRAM: High-level architecture showing OpenSTEF as library component in user application]

Getting Started
---------------

If you're ready to start using OpenSTEF:

1. **Installation**: Install the library with ``pip install openstef``
2. **Quick Start**: Follow the :doc:`../quick_start` guide for a simple end-to-end example
3. **Tutorials**: Work through the :doc:`../tutorials` for comprehensive learning
4. **Use Cases**: Explore :doc:`../../use_cases/index` to understand real-world applications

For questions about OpenSTEF's capabilities and limitations, see the :doc:`../../faq`.