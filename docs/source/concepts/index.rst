Concepts
========

This section explains the ideas behind OpenSTEF's design — from how short-term energy forecasting works to the architectural choices that make the library reliable in production.

**Forecasting Basics** (:doc:`forecasting_basics`)
   Start here to understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

**Quantiles and Confidence** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are and how to read the uncertainty bandwidths that OpenSTEF produces instead of single-point predictions.

**Feature Engineering** (:doc:`feature_engineering`)
   Understand which predictors drive forecast accuracy — weather variables, calendar features, lagged load — and how OpenSTEF builds them automatically from raw inputs.

**Reliability and Fallback** (:doc:`reliability_and_fallback`)
   See how OpenSTEF handles missing data, stale inputs, and model failures in production so that a forecast is always available even when something goes wrong.

**Meta Ensembles** (:doc:`meta_ensembles`)
   Understand why combining multiple models improves robustness and how OpenSTEF's meta-ensemble layer selects and weights constituent models at runtime.

**Component Splitting** (:doc:`component_splitting`)
   Learn how OpenSTEF decomposes an aggregate load measurement into its energy components — solar, wind, base load — to improve both interpretability and forecast accuracy.

.. toctree::
   :maxdepth: 1
   :caption: Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
   meta_ensembles
   component_splitting
