Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library — helping you understand not just *how* to use it, but *why* it works the way it does.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF's multi-horizon pipeline differs from a simple model wrapper.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how OpenSTEF expresses uncertainty through quantiles, and how to interpret confidence bandwidths in practice.

- **Model Selection** (:doc:`model_selection`)
   Compare the forecasting model types available in OpenSTEF and understand the trade-offs that should guide your choice for a given use case.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF provides — weather variables, time features, lag features, and domain-specific signals like PV generation estimates — and how to extend them.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Understand how OpenSTEF handles missing data, model failures, and degraded inputs in production, and what fallback strategies are available to keep forecasts running.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
