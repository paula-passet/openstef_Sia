Concepts
========

This section explains the ideas and design principles behind OpenSTEF, giving you the context to use the library more effectively and understand the reasoning behind its key decisions.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   What short-term energy forecasting is, why it matters for grid operations, and how OpenSTEF approaches it differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   How OpenSTEF produces probabilistic forecasts with uncertainty bandwidths, and how to interpret and use quantile outputs in practice.

- **Feature Engineering** (:doc:`feature_engineering`)
   The predictors OpenSTEF builds automatically — weather variables, time features, and domain-specific transformations like solar radiation to PV generation estimates.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   How the library handles degraded conditions in production: fallback strategies when models fail, missing data, and delayed measurements or weather forecasts.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
