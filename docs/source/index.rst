OpenSTEF Documentation
======================


Welcome to OpenSTEF
-------------------


OpenSTEF is a Python machine learning library designed for short-term energy forecasting. As a software package, it provides the core components needed to build forecasting pipelines but is not a standalone application. To deploy OpenSTEF as a complete forecasting system, you must integrate it with additional components like data fetchers, APIs, and scheduling systems.


OpenSTEF is a Python library designed specifically for short-term energy grid forecasting. The library provides a complete machine learning pipeline with modular components for data preparation, feature engineering, model training, and prediction. Its extensible architecture allows users to integrate custom components while leveraging built-in functionality for single-shot, multi-horizon forecasting with confidence estimates.


Key Features & Capabilities
---------------------------


- Automated feature engineering with configurable lag features and time-based transformations

- Multiple machine learning algorithms including XGBoost, LightGBM, and linear models

- Quantile forecasting for uncertainty estimation and confidence intervals

- Single-shot multi-horizon forecasting up to 47 hours ahead

- Built-in data validation to detect flatliners and data quality issues

- Comprehensive backtesting and model evaluation capabilities

- Flexible pipeline architecture supporting both tasks and direct pipeline usage

- Two methods for forecast confidence estimation with usage recommendations


- Energy grid congestion forecasting for transmission system operators

- Distribution network load prediction for grid operators

- Renewable energy output forecasting for wind and solar farms

- Electric vehicle charging demand prediction

- Industrial energy consumption forecasting

- Residential and commercial load forecasting

- Grid loss prediction and optimization

- Peak demand forecasting for capacity planning

- Energy trading and market price forecasting support

- Smart grid optimization and demand response planning


Getting Started
---------------


New to OpenSTEF? Start with our quickstart guide to get hands-on experience with the library. You'll learn to load data, create forecasting models, and generate predictions in just a few steps.


For comprehensive learning, explore our tutorials which walk through complete forecasting workflows. To identify relevant applications for your specific needs, consult the use cases guide which demonstrates OpenSTEF's capabilities across different forecasting scenarios and data types.


Documentation Structure
-----------------------


.. toctree::
   :maxdepth: 1
   :caption: Contents


   getting_started/quickstart

   getting_started/tutorials

   guides/use_cases

   guides/how_to_guides

   guides/faq

   reference/architecture

   reference/concepts

   reference/changelog

   api/index


- Getting Started - Installation, quickstart guide, and basic configuration to begin using OpenSTEF

- User Guides - Step-by-step tutorials for common forecasting workflows and advanced features

- API Reference - Complete documentation of classes, functions, and parameters for developers

- Examples - Practical code samples and use cases demonstrating OpenSTEF capabilities

- Contributing - Guidelines for contributing code, reporting issues, and development setup


New users should start with the Getting Started guide and basic tutorials. Experienced ML practitioners can jump to the API Reference and advanced modeling techniques. System integrators should focus on the Installation guide, Configuration sections, and deployment examples to understand how OpenSTEF integrates with existing infrastructure.


Community & Support
-------------------


The OpenSTEF library is developed openly on GitHub at OpenSTEF/, where you can find the main package and related repositories. Join community discussions and get support through our Teams channel or community meetings held every four weeks. Report bugs or request features by opening issues on GitHub, and check our roadmap for upcoming developments.


For technical support and questions, visit our community support page or post in the OpenSTEF Teams channel. Contributors should review our contributing guidelines before submitting code. Bug reports and feature requests can be submitted through our GitHub issues page.


