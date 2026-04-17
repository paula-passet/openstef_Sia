Architecture
============

This section documents the internal structure of the OpenSTEF library, covering how its four packages are organised, how they depend on one another, and how to extend or integrate them into your own systems.

- **Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the ``TimeSeriesDataset`` class, shared data structures, base classes, and the foundational interfaces that all other packages build upon.

- **Models Package** (:doc:`models`)
   Internals of ``openstef-models``: the transforms module, feature engineering pipelines, forecasting model implementations, explainability utilities, and ready-to-use presets.

- **BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam`` (Backtesting, Evaluation, Analysis and Metrics): how to run backtests, interpret evaluation metrics, and use the analysis and visualisation tools to assess model quality.

- **Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: ensemble model architectures, meta-learning strategies, and advanced model configurations for production-grade forecasting.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
