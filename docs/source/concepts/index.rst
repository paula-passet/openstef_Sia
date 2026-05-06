Core Concepts
=============

This section explains the ideas behind OpenSTEF — from how short-term energy forecasting works to the design decisions that shape the library's behaviour in production.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty estimates matter more than point predictions alone.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF uses — weather variables, calendar features, lagged load — and how domain knowledge is baked into the pipeline.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data, delayed measurements, and model failures so forecasts remain available in production.

- **Meta Ensembles** (:doc:`meta_ensembles`)
   See why combining multiple models through the ``openstef-meta`` ensemble approach improves accuracy and robustness over any single model.

- **Component Splitting** (:doc:`component_splitting`)
   Understand how aggregate load measurements are decomposed into energy components (solar, wind, base load) to improve forecast interpretability and accuracy.

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
