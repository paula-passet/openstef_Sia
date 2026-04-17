Architecture
============

OpenSTEF is organised as a modular mono-repo of four self-contained packages, each with a distinct responsibility — from shared data types up to ensemble meta-models and full backtesting pipelines.

**Package Overview** (:doc:`core`)
   Understand ``openstef-core``: the validated dataset hierarchy, shared interfaces, base classes, and testing utilities that every other package builds on.

**Models** (:doc:`models`)
   Explore ``openstef-models``: domain-organised transforms, forecasting model implementations, explainability features, and ready-to-use presets for common forecasting tasks.

**BEAM Pipelines** (:doc:`beam`)
   Learn how ``openstef-beam`` (Backtesting, Evaluation, Analysis and Metrics) structures backtesting and evaluation pipelines, and how to answer "are my model changes significant?"

**Meta-Learning** (:doc:`meta`)
   See how ``openstef-meta`` implements ``EnsembleForecastingModel`` and ``ForecastCombiner`` to combine predictions from multiple models into a single, more robust forecast.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   core
   models
   beam
   meta
