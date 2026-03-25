OpenSTEF Documentation
======================


What is OpenSTEF?
-----------------


OpenSTEF is a Python library for short-term energy forecasting, not a standalone application. It provides a complete machine learning toolkit for predicting energy loads hours to days ahead, including data preprocessing, feature engineering, model training, and probabilistic forecasting capabilities with uncertainty estimates.


OpenSTEF is a machine learning library specifically designed for energy grid forecasting. It provides complete pipelines for data preprocessing, feature engineering, model training, and forecasting to predict electrical load hours to days ahead. The library generates probabilistic forecasts with uncertainty estimates rather than single-point predictions, incorporating domain-specific knowledge for energy systems.


Documentation Contents
----------------------


.. toctree::
   :maxdepth: 2
   :caption: Contents


   api/index


Key Features
------------


- Automated feature engineering with weather, holiday, lag, and rolling features

- Multiple machine learning models including XGBoost, LightGBM, and linear regression

- Quantile forecasting with confidence interval estimation

- Multi-horizon forecasting in a single prediction run

- Comprehensive backtesting and model validation capabilities

- Missing value handling and data preparation pipelines

- Flexible model specifications and hyperparameter optimization

- Built-in metrics and performance reporting tools


Common Use Cases
----------------


- Congestion forecasts for proactive grid management and demand response

- Free space estimation to optimize grid capacity utilization

- Grid loss forecasts for accurate energy distribution planning

- Transport forecasts for mobility and logistics optimization

- District heating demand prediction for community energy systems


These use cases enable grid operators and energy companies to proactively manage their infrastructure and operations. By accurately forecasting energy demand and generation patterns, operators can prevent costly equipment overloads, optimize grid capacity utilization, and implement targeted demand response programs. This translates to reduced operational costs, improved grid reliability, and enhanced customer service through proactive communication and compensation programs.


Getting Started
---------------


New to OpenSTEF? The Quick Start guide provides step-by-step instructions to get you up and running with the library quickly. Follow along with practical examples to create your first forecasting models and understand core functionality.


For comprehensive learning, explore the tutorials section which provides step-by-step guides for common OpenSTEF workflows. For detailed technical specifications and function signatures, consult the API reference documentation.


Community and Support
---------------------


The OpenSTEF community provides multiple support channels. Visit the GitHub repository at OpenSTEF/ for source code and issue tracking. Join four-weekly community meetings open to all interested participants, with details and meeting links available on the community page. For questions and discussions, use the OpenSTEF Teams channel or explore community support options through the official support resources.


OpenSTEF welcomes contributions in all forms. Code contributors should review the contributing guidelines on GitHub. Community members can participate in four-weekly meetings to discuss progress, refine issues, and explore collaboration opportunities. Bug reports and feature requests can be submitted through GitHub issues, and support is available through the OpenSTEF Teams channel.


