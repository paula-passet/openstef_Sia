Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the responsibilities of each package, the design patterns they follow, and how to extend or integrate them into your own systems.

**Core Package** (:doc:`core`)
   Explore ``openstef_core``: the foundational layer providing shared data structures, base classes, configuration utilities, and the ``TimeSeriesDataset`` abstraction that all other packages build upon.

**Models Package** (:doc:`models`)
   Explore ``openstef_models``: forecasting models, feature engineering transforms, preprocessing pipelines, energy-specific transformations, explainability features, and ready-to-use presets.

**BEAM Package** (:doc:`beam`)
   Explore ``openstef_beam`` (Backtesting, Evaluation, Analysis and Metrics): the framework for rigorously evaluating model changes, running regression tests against benchmarks, and producing scoring and analysis artefacts.

**Meta Package** (:doc:`meta`)
   Explore ``openstef_meta``: advanced ensemble models and meta-learning architectures that compose the lower-level packages into higher-capacity forecasting solutions.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
