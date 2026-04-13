Architecture
============

This section describes how OpenSTEF is structured as a modular library, covering the responsibilities of each package, the design patterns that connect them, and how to extend the library for custom use cases.

**Core Package** (:doc:`core`)
   Deep dive into ``openstef-core``: the foundation layer providing data types, base classes, shared interfaces, and the ``TimeSeriesDataset`` structure that all other packages depend on.

**Models Package** (:doc:`models`)
   Deep dive into ``openstef-models``: feature engineering pipelines, energy-specific transforms, forecasting model implementations, explainability, and ready-to-use presets.

**BEAM Package** (:doc:`beam`)
   Deep dive into ``openstef-beam`` (Backtesting, Evaluation, Analysis, Metrics): tools for rigorous model evaluation, regression testing against benchmarks, and answering whether model changes are statistically significant.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
