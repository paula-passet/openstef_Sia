Architecture
============

OpenSTEF is organized as a modular mono-repo of four self-contained packages — ``openstef-core``, ``openstef-models``, ``openstef-beam``, and ``openstef-meta`` — each with a distinct responsibility, layered so that higher-level packages depend on lower-level ones but not the reverse.

**Core Package** (:doc:`core`)
   Internals of ``openstef-core``: the validated dataset hierarchy, base classes, shared interfaces, and the foundation every other package builds on.

**Models Package** (:doc:`models`)
   Internals of ``openstef-models``: domain-organized transforms, forecasting model implementations, explainability utilities, and ready-to-use presets.

**BEAM Package** (:doc:`beam`)
   Internals of ``openstef-beam``: the backtesting, metrics, and evaluation pipelines that answer whether model changes are statistically significant.

**Meta Package** (:doc:`meta`)
   Internals of ``openstef-meta``: the ``EnsembleForecastingModel``, ``ForecastCombiner``, and other advanced model architectures that sit at the top of the dependency stack.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   core
   models
   beam
   meta
