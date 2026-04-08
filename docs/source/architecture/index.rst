Architecture
============

OpenSTEF is built as a modular library with three core packages: ``openstef-core`` provides foundational data structures, ``openstef-models`` implements forecasting algorithms and feature engineering, and ``openstef-beam`` handles backtesting and evaluation. This section explains how these packages work together and how to extend the library.

**Core Package** (:doc:`core`)
   Foundational data structures including TimeSeriesDataset, shared types, and base classes used across all packages.

**Models Package** (:doc:`models`)
   Forecasting models, feature engineering transforms, and energy-specific preprocessing pipelines.

**BEAM Package** (:doc:`beam`)
   Backtesting, evaluation, analysis, and metrics for comparing model performance and detecting regressions.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
