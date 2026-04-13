Architecture
============

OpenSTEF is structured as a modular library across three focused packages, each with a distinct responsibility in the forecasting workflow.

- **Package Structure & Dependencies** (:doc:`core`)
   Understand the ``openstef-core`` package: the ``TimeSeriesDataset`` class, shared data structures, base model interfaces, and the foundational types that the rest of the library builds on.

- **Models & Feature Engineering** (:doc:`models`)
   Explore the ``openstef-models`` package: how transforms and feature engineering pipelines are composed, how forecasting models are implemented, and the design patterns used to keep models interchangeable.

- **Backtesting, Evaluation & Metrics** (:doc:`beam`)
   Learn how the ``openstef-beam`` package provides rigorous model evaluation — covering backtesting workflows, metrics, and analysis tools for answering whether model changes are statistically meaningful.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
