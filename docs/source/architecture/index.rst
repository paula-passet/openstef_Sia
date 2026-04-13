Architecture
============

OpenSTEF is structured as a modular library across three focused packages — ``openstef-core``, ``openstef-models``, and ``openstef-beam`` — each with a distinct responsibility in the forecasting workflow. This section explains how those packages fit together, the design patterns they follow, and how to extend the library for your own use cases.

- **Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the ``TimeSeriesDataset`` class, shared data structures, base model interfaces, and the foundational types that the rest of the library builds on.

- **Models Package** (:doc:`models`)
   Internals of ``openstef-models``: the transforms module for feature engineering, forecasting model implementations, preprocessing pipelines, and energy-specific data processing patterns.

- **BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam`` (Backtesting, Evaluation, Analysis, Metrics): how to run backtests, interpret evaluation results, and use the analysis and metrics tooling to validate model changes.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
