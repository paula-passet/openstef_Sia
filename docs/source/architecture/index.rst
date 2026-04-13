Architecture
============

OpenSTEF is structured as a modular library across three focused packages — ``openstef-core``, ``openstef-models``, and ``openstef-beam`` — each with a distinct responsibility in the forecasting workflow.

- **Core Package** (:doc:`core`)
   Covers the ``openstef-core`` package: the ``TimeSeriesDataset`` class, shared data structures, base model interfaces, and the foundational types used across the entire library.

- **Models Package** (:doc:`models`)
   Covers the ``openstef-models`` package: feature engineering pipelines, data transforms, forecasting model implementations, and presets for common use cases.

- **BEAM Package** (:doc:`beam`)
   Covers the ``openstef-beam`` package: backtesting workflows, metrics, model evaluation, and analysis tools for assessing forecast quality and model changes.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
