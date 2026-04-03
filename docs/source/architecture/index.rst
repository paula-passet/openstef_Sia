Architecture
============

OpenSTEF is built on a modular three-package architecture that separates data handling, machine learning, and evaluation concerns. This section explains how ``openstef_core``, ``openstef_models``, and ``openstef_beam`` work together and when to use each package.

.. note::

   [DIAGRAM: Package dependency diagram showing openstef_core at base, openstef_models depending on core, and openstef_beam depending on both. Include data flow arrows showing: raw data → core → features → models → forecasts → beam → evaluation]

The architecture follows a clear dependency hierarchy. ``openstef_core`` provides foundational data structures like ``TimeSeriesDataset`` that are used throughout the library. ``openstef_models`` builds on these structures to implement feature engineering and forecasting models. ``openstef_beam`` sits at the top, consuming outputs from both packages to provide backtesting, metrics, and analysis capabilities.

:doc:`core` - Explore the ``openstef_core`` package, which provides ``TimeSeriesDataset`` and versioned data handling that form the foundation for all forecasting workflows.

:doc:`models` - Learn about the ``openstef_models`` package, including the transforms module for feature engineering, model implementations, and explainability tools.

:doc:`beam` - Understand the ``openstef_beam`` package for backtesting forecasting models, computing performance metrics, and generating evaluation reports.

When building a forecasting system, start with ``openstef_core`` to structure your data, use ``openstef_models`` to train and generate predictions, and apply ``openstef_beam`` to evaluate performance. For production deployments that only need to generate forecasts, you can install just ``openstef-core`` and ``openstef-models``, leaving out the heavier evaluation tools.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
