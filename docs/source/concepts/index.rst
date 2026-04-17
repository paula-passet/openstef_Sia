Core Concepts
=============

This section explains the ideas behind OpenSTEF's design — from how short-term energy forecasting works to why the library is built the way it is.

**Forecasting Basics** (:doc:`forecasting_basics`)
   Start here to understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem.

**Quantiles and Confidence** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are and how to interpret the uncertainty bandwidths OpenSTEF produces alongside every prediction.

**Feature Engineering** (:doc:`feature_engineering`)
   Understand which predictors drive forecast accuracy — weather variables, calendar features, lagged load — and how OpenSTEF constructs them automatically.

**Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Read about how OpenSTEF handles missing data, model failures, and degraded inputs to keep forecasts running in production.

**Meta Ensembles** (:doc:`meta_ensembles`)
   Explore the rationale for combining multiple trained models into a single ensemble and when this approach improves forecast quality.

**Component Splitting** (:doc:`component_splitting`)
   See how OpenSTEF decomposes aggregate load measurements into energy components (solar, wind, base load) to improve interpretability and accuracy.

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
