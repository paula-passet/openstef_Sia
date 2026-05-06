Core Concepts
=============

This section explains the ideas and design decisions behind OpenSTEF — from how short-term energy forecasting works to why the library is built the way it is.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term energy forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem end-to-end.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty estimation matters more than single-point predictions.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the predictors OpenSTEF uses by default — weather signals, calendar features, lagged load — and how domain knowledge is baked into the pipeline.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Understand how OpenSTEF handles model failures, missing data, and degraded inputs in production so forecasts remain available under adverse conditions.

- **Meta Ensembles** (:doc:`meta_ensembles`)
   Discover why combining multiple models often outperforms any single model, and how OpenSTEF's meta-ensemble layer works conceptually.

- **Component Splitting** (:doc:`component_splitting`)
   See how aggregate load measurements can be decomposed into energy components (solar, wind, base load) and why this improves forecast accuracy.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
   meta_ensembles
   component_splitting
