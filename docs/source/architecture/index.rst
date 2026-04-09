Architecture
============

OpenSTEF 4.0 is built as a modular library with three core packages: ``openstef-core`` provides foundational data structures, ``openstef-models`` handles forecasting and feature engineering, and ``openstef-beam`` delivers backtesting and evaluation tools.

**Core Package** (:doc:`core`)
   Foundational data structures, base classes, and the TimeSeriesDataset class that powers all forecasting workflows.

**Models Package** (:doc:`models`)
   Feature engineering transforms, preprocessing pipelines, and energy-specific data transformations.

**BEAM Package** (:doc:`beam`)
   Backtesting, evaluation, metrics, and analysis tools for assessing forecast quality and model improvements.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
