Concepts
========

This section explains the core ideas behind OpenSTEF — what short-term energy forecasting is, how the library approaches it, and why it is designed the way it is.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF's multi-horizon pipeline works end to end.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn how OpenSTEF produces probabilistic forecasts with uncertainty bandwidths, and how to interpret quantile outputs in practice.

- **Model Selection** (:doc:`model_selection`)
   Compare the available model types in OpenSTEF and understand which to choose based on your data characteristics and forecasting goals.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF provides — weather variables, time features, lag features, and domain-specific signals like PV generation estimates.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data, model failures, and degraded inputs to keep forecasts running reliably in production.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
