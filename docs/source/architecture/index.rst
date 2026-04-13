Architecture
============

OpenSTEF is structured as a modular library across three focused packages, each with a distinct responsibility in the short-term energy forecasting workflow.

- **Package Structure and Dependencies** (:doc:`core`)
   Understand the ``openstef-core`` package — the foundation layer providing ``TimeSeriesDataset``, shared data structures, base classes, and types that all other packages build on.

- **Models and Feature Engineering** (:doc:`models`)
   Explore the ``openstef-models`` package — forecasting models, the transforms module for feature engineering, preprocessing pipelines, and energy-specific data processing.

- **Backtesting, Evaluation, and Metrics** (:doc:`beam`)
   Learn how the ``openstef-beam`` package (Backtesting, Evaluation, Analysis, Metrics) enables rigorous model evaluation, regression testing against benchmarks, and statistical significance testing for model changes.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
