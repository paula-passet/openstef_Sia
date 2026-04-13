Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the responsibilities of each package and the design decisions that make the library flexible and extensible.

- **Package Overview** (:doc:`core`)
     Internals of the ``openstef-core`` package: the ``TimeSeriesDataset`` class, shared data structures, base interfaces, and the foundational types that all other packages depend on.

- **Models and Feature Engineering** (:doc:`models`)
     Internals of the ``openstef-models`` package: how transforms and feature engineering pipelines are structured, how forecasting models are implemented, and how to extend the library with custom models or preprocessing steps.

- **Backtesting, Evaluation, and Metrics** (:doc:`beam`)
     Internals of the ``openstef-beam`` package: how backtesting is orchestrated, how model performance is measured and compared, and how to use the evaluation and analysis tools to validate model changes.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
