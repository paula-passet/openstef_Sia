Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn how OpenSTEF produces probabilistic forecasts with uncertainty bandwidths, and how to interpret quantile outputs in practice.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF uses — weather variables, calendar features, and energy-domain transformations — and how to extend them for your own use case.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles real-world data issues in production: missing measurements, delayed inputs, and automatic fallback strategies when a model cannot produce a forecast.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
