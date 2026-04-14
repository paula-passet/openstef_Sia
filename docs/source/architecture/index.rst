Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the three core packages, their responsibilities, and how they fit together.

**Core Package** (:doc:`core`)
   Explore ``openstef-core``: the foundation layer providing shared data structures, base classes, and interfaces that all other packages build upon.

**Models Package** (:doc:`models`)
   Explore ``openstef-models``: the feature engineering pipeline, forecasting model implementations, energy-specific transforms, and presets for common use cases.

**BEAM Package** (:doc:`beam`)
   Explore ``openstef-beam``: the Backtesting, Evaluation, Analysis, and Metrics package for assessing model quality and validating changes against benchmarks.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
