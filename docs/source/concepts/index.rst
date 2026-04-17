Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read the uncertainty bandwidths OpenSTEF produces, and why a range of predictions is more useful than a single point estimate.

- **Feature Engineering** (:doc:`feature_engineering`)
   Discover which predictors drive forecast accuracy — weather variables, calendar features, lagged load — and how OpenSTEF builds these automatically from raw inputs.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Explore how OpenSTEF handles real-world data problems in production: missing measurements, delayed weather forecasts, and graceful degradation when a model cannot produce a forecast.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
