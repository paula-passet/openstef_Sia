Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the responsibilities of each package, the design patterns they follow, and how to extend the framework for custom use cases.

- **Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the foundational data structures, ``TimeSeriesDataset``, base classes, and shared interfaces that every other package depends on.

- **Models Package** (:doc:`models`)
   Internals of ``openstef-models``: how the transforms module handles feature engineering, how preprocessing pipelines are composed, and how explainability is built into the forecasting layer.

- **BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam`` (Backtesting, Evaluation, Analysis and Metrics): how backtesting pipelines are structured, how models are evaluated against benchmarks, and how scoring and analysis utilities are organized.

- **Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: ensemble model architectures, meta-learning strategies, and the advanced model patterns that build on top of ``openstef-core`` and ``openstef-models``.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
