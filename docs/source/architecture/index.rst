Architecture
============

OpenSTEF is organized as a modular mono-repo of four focused packages — ``openstef-core``, ``openstef-models``, ``openstef-meta``, and ``openstef-beam`` — each with a distinct responsibility, layered so that higher-level packages depend on lower-level ones but not the reverse.

**Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the validated dataset hierarchy, base classes, shared interfaces, and the foundational types that every other package builds on.

**Models Package** (:doc:`models`)
   Internals of ``openstef-models``: domain-organized transforms, forecasting model implementations, explainability utilities, and ready-to-use presets for common forecasting tasks.

**BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam``: backtesting pipelines, evaluation metrics, and analysis tooling that answers whether model changes produce statistically meaningful improvements.

**Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: the ``EnsembleForecastingModel``, ``ForecastCombiner``, and other advanced model architectures that compose lower-level models into production-grade ensembles.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   core
   models
   beam
   meta
