Architecture
============

This section describes how OpenSTEF is structured as a modular library of four cooperating packages, covering their responsibilities, dependencies, design patterns, and extension points.

**Core Package** (:doc:`core`)
   Understand ``openstef-core``: the validated dataset hierarchy, shared interfaces, base classes, and utilities that every other package builds on.

**Models Package** (:doc:`models`)
   Explore ``openstef-models``: domain-organised transforms, forecasting model implementations, explainability features, and ready-to-use presets for common forecasting tasks.

**BEAM Package** (:doc:`beam`)
   Learn how ``openstef-beam`` (Backtesting, Evaluation, Analysis and Metrics) provides pipelines for rigorous model evaluation, regression testing, and performance measurement.

**Meta Package** (:doc:`meta`)
   Discover ``openstef-meta``: ensemble forecasting with ``EnsembleForecastingModel`` and ``ForecastCombiner``, enabling advanced multi-model architectures built on top of the other packages.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
