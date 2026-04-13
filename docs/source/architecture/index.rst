Architecture
============

This section describes how OpenSTEF is structured as a modular forecasting library, covering the responsibilities of each package, the design patterns that connect them, and how to extend the library for custom use cases.

**Core Package** (:doc:`core`)
   Explore ``openstef-core``: the foundational layer providing data structures, shared types, base classes, and interfaces that all other packages depend on.

**Models Package** (:doc:`models`)
   Explore ``openstef-models``: the machine learning layer covering feature engineering transforms, forecasting model implementations, preprocessing pipelines, and explainability.

**BEAM Package** (:doc:`beam`)
   Explore ``openstef-beam``: the Backtesting, Evaluation, Analysis, and Metrics layer used to assess model quality, run regression tests, and compare model changes.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
