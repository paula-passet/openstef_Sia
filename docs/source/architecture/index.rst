Architecture
============

OpenSTEF is structured as a modular mono-repo of four focused packages — ``openstef-core``, ``openstef-models``, ``openstef-meta``, and ``openstef-beam`` — each with a distinct responsibility, from shared data types and base classes through to ensemble forecasting and backtesting pipelines.

**Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the validated dataset hierarchy, base model interfaces, shared exceptions, and the building blocks every other package depends on.

**Models Package** (:doc:`models`)
   Internals of ``openstef-models``: domain-organised transforms, forecasting model implementations, explainability features, and ready-to-use presets for common forecasting tasks.

**BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam``: backtesting pipelines, evaluation metrics, and regression-testing utilities for answering "are my model changes statistically significant?"

**Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: the ``EnsembleForecastingModel``, ``ForecastCombiner``, and the meta-learning layer that combines outputs from multiple base models.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   core
   models
   beam
   meta
