Concepts
========

This section explains the core ideas behind OpenSTEF — from how short-term energy forecasting works to the design decisions that shape the library's behaviour in production.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read the quantile outputs OpenSTEF produces, and why uncertainty estimates matter for operational decisions.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the predictors OpenSTEF builds automatically — weather variables, calendar features, lag terms, and domain-specific signals like PV generation estimates.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data, model failures, and degraded inputs so that forecasts remain available in production even when things go wrong.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
