Architecture
============

This section documents the internal structure of the OpenSTEF library, covering how its packages are organised, the design patterns they follow, and how to extend them for custom use cases.

- **Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the ``TimeSeriesDataset`` class, shared data structures, base interfaces, and the foundational types that all other packages depend on.

- **Models Package** (:doc:`models`)
   Internals of ``openstef-models``: feature engineering transforms, the model-agnostic forecasting pipeline, explainability utilities, and built-in presets for common forecasting scenarios.

- **Beam Package** (:doc:`beam`)
   Internals of ``openstef-beam``: backtesting workflows, metrics, evaluation pipelines, and regression testing tools for assessing whether model changes are statistically significant.

- **Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: ensemble model architectures and advanced meta-learning approaches built on top of the core and models packages.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
