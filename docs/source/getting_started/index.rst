Getting Started
===============

This section walks you through everything you need to go from zero to producing energy forecasts with OpenSTEF. Whether you're evaluating the library for the first time or ready to integrate it into a production pipeline, start here.

The guides below are ordered from basic setup through increasingly hands-on tutorials. If you're new to OpenSTEF, we recommend reading them in order. If you already have the library installed, skip ahead to whichever page matches where you are.

:doc:`installation` --- How to install OpenSTEF, including system requirements (Python 3.12+), the modular package options (``openstef-core``, ``openstef-models``, ``openstef-beam``), and troubleshooting common issues.

:doc:`quickstart` --- The fastest path to your first forecast. A single-page, minimal working example using sample data that you can run in under five minutes.

:doc:`first_forecast` --- A step-by-step tutorial that explains what's happening at each stage. Covers data preparation, model configuration, training, and generating predictions with detailed commentary.

:doc:`backtesting` --- Learn how to evaluate and compare different models against historical data. Essential reading before choosing a model configuration for production use.

:doc:`advanced_customization` --- For power users who want to go beyond the defaults. Shows how to define custom data sources, implement custom models, tune hyperparameters, and extend the library's pipelines.

.. note::

   If you're looking for conceptual background on how OpenSTEF works rather than hands-on tutorials, see the :doc:`/concepts/index` section. For complete API details, see the :doc:`/api/index`.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   :hidden:

   installation
   quickstart
   first_forecast
   backtesting
   advanced_customization
