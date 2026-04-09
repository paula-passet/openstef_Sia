Architecture
============

OpenSTEF 4.0 follows a modular design with three core packages: ``openstef-core`` provides foundational data structures and interfaces, ``openstef-models`` implements forecasting models and feature engineering, and ``openstef-beam`` handles backtesting and evaluation. This section explains how these packages work together and how to extend them.

**Core Package** (:doc:`core`)
   Understand the foundational ``openstef-core`` package, including the TimeSeriesDataset class and shared data structures.

**Models Package** (:doc:`models`)
   Explore the ``openstef-models`` package with its feature engineering transforms and preprocessing pipelines.

**BEAM Package** (:doc:`beam`)
   Learn about the ``openstef-beam`` package for backtesting, metrics, evaluation, and model comparison.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
