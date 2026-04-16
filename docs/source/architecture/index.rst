Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the responsibilities of each package, the design patterns they follow, and how to extend the framework for custom use cases.

**Core Package** (:doc:`core`)
   Explore ``openstef-core``: the foundational layer providing data structures, base classes, shared interfaces, and configuration utilities that all other packages depend on.

**Models Package** (:doc:`models`)
   Explore ``openstef-models``: forecasting models, feature engineering transforms, preprocessing pipelines, explainability features, and presets for common energy forecasting scenarios.

**BEAM Package** (:doc:`beam`)
   Explore ``openstef-beam``: the Backtesting, Evaluation, Analysis, and Metrics framework — use this to answer whether model changes are statistically significant and to run regression tests against benchmarks.

**Meta Package** (:doc:`meta`)
   Explore ``openstef-meta``: advanced ensemble models and meta-learning architectures that build on top of the core and models packages for higher-accuracy forecasting.

.. note::

   OpenSTEF follows an **unopinionated, modular design** — packages can be used independently or together. Install only what you need, or use the ``openstef`` meta-package to pull in the full framework.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
