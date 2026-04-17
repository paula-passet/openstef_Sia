Architecture
============

OpenSTEF is structured as a modular mono-repo of four self-contained packages, each with a distinct responsibility — from shared data types and base classes through to ensemble meta-learning and full backtesting pipelines.

- **Package Overview** (:doc:`core`)
   Understand ``openstef-core``: the validated dataset hierarchy, shared interfaces, base classes, and testing utilities that every other package builds on.

- **Models & Transforms** (:doc:`models`)
   Explore ``openstef-models``: domain-organised transforms, forecasting model implementations, explainability features, and presets for common energy-forecasting use cases.

- **BEAM Pipelines** (:doc:`beam`)
   Learn how ``openstef-beam`` (Backtesting, Evaluation, Analysis and Metrics) orchestrates backtesting runs, computes scoring metrics, and answers "are my model changes significant?"

- **Meta-Learning & Ensembles** (:doc:`meta`)
   See how ``openstef-meta`` layers ``EnsembleForecastingModel`` and ``ForecastCombiner`` on top of the core and models packages to deliver advanced ensemble forecasting architectures.

.. toctree::
   :maxdepth: 1
   :caption: Architecture
   :hidden:

   core
   models
   beam
   meta
