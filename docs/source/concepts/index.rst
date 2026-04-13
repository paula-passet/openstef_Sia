Concepts
========

This section explains the core ideas behind OpenSTEF — a model-agnostic Python library for short-term energy forecasting — so you understand not just *how* to use it, but *why* it works the way it does.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term energy forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty estimates are a first-class feature of OpenSTEF rather than an afterthought.

- **Model Selection** (:doc:`model_selection`)
   Compare the model types available in OpenSTEF and understand the trade-offs that should guide your choice for a given forecasting task.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF provides — weather variables, calendar features, lag features, and domain-specific signals like PV generation estimates — and how to extend them.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data, model failures, and degraded inputs in production, and what fallback strategies are available to keep forecasts running.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
