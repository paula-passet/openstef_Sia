Architecture
============

OpenSTEF is organized as a modular mono-repo of four self-contained packages, each with a distinct responsibility — from shared data types and base classes through to ensemble models and full backtesting pipelines.

**Core Package** (:doc:`core`)
   Understand the foundation of the framework: validated dataset types, shared interfaces, base classes, and the dependency contract that all other packages build on.

**Models Package** (:doc:`models`)
   Explore the forecasting model layer: domain-organized transforms, model-agnostic forecasting pipelines, explainability utilities, and ready-to-use presets.

**BEAM Package** (:doc:`beam`)
   Learn how the Backtesting, Evaluation, Analysis and Metrics package works: pipeline structure, scoring rules, baseline comparisons, and how to assess whether model changes are statistically significant.

**Meta Package** (:doc:`meta`)
   Discover the meta-learning layer: ``EnsembleForecastingModel``, ``ForecastCombiner``, and the advanced model architectures that combine outputs from the models package.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   core
   models
   beam
   meta
