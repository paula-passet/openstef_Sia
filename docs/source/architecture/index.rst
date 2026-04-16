Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the three core packages, their dependencies, design patterns, and how to extend the library for custom use cases.

**Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the foundational data structures, interfaces, and base classes that all other packages depend on.

**Models Package** (:doc:`models`)
   Internals of ``openstef-models``: feature engineering transforms, forecasting model implementations, preprocessing pipelines, and explainability features.

**Beam Package** (:doc:`beam`)
   Internals of ``openstef-beam``: backtesting infrastructure, metrics, evaluation workflows, and regression testing against benchmarks.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
