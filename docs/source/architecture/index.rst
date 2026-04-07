Architecture
============

OpenSTEF is built with a modular three-package architecture that separates concerns and allows you to install only what you need. The ``openstef_core`` package provides foundational data structures and utilities, ``openstef_models`` implements machine learning models and feature engineering, and ``openstef_beam`` delivers backtesting and evaluation tools. This section explains how these packages work together and when to use each one.

.. note::
   [DIAGRAM: Package dependency diagram showing openstef_core at the base, openstef_models depending on core, and openstef_beam depending on both. Include data flow arrows showing TimeSeriesDataset flowing from core through models to beam for evaluation.]

Understanding the three-package structure helps you make informed decisions about dependencies and integration points. Whether you're building custom models, integrating OpenSTEF into existing systems, or evaluating forecast performance, knowing which package provides which functionality is essential.

:doc:`core` - Explore the ``openstef_core`` package, including the ``TimeSeriesDataset`` class, versioned datasets, data validation, and shared type definitions that form the foundation for all OpenSTEF components.

:doc:`models` - Learn about the ``openstef_models`` package, which provides the transforms module for feature engineering, machine learning model implementations, and data processing pipelines that generate forecasts.

:doc:`beam` - Discover the ``openstef_beam`` package for backtesting workflows, performance metrics, forecast evaluation, and analysis tools that help you understand model behavior over time.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
