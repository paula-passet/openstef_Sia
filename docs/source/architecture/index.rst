Architecture
============

OpenSTEF is structured as a modular mono-repo of four self-contained packages, each with a distinct responsibility — from shared data types and base classes through to ensemble models and full backtesting pipelines.

**Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the validated dataset hierarchy, shared interfaces, base classes, and testing utilities that every other package depends on.

**Models Package** (:doc:`models`)
   Internals of ``openstef-models``: domain-organised transforms, forecasting model implementations, explainability features, and ready-to-use presets.

**BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam``: backtesting pipelines, evaluation metrics, and analysis tooling for answering "are my model changes statistically significant?"

**Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: ``EnsembleForecastingModel``, ``ForecastCombiner``, and the meta-learning layer that combines outputs from multiple base models.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
