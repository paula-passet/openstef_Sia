Architecture
============

OpenSTEF 4.0 follows a modular architecture with three core packages: ``openstef-core`` provides foundational data structures, ``openstef-models`` implements forecasting algorithms and feature engineering, and ``openstef-beam`` handles evaluation and analysis. This section explains how these packages work together and how to extend them.

**Core Package** (:doc:`core`)
   Foundational data structures including TimeSeriesDataset, base classes, and shared types used across all packages.

**Models Package** (:doc:`models`)
   Feature engineering transforms, preprocessing pipelines, and energy-specific data processing logic.

**BEAM Package** (:doc:`beam`)
   Backtesting framework, evaluation metrics, and tools for assessing model performance and significance.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
