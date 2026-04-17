Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library — essential reading before diving into the API.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty estimates matter more than point predictions alone.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the predictors OpenSTEF builds automatically — weather variables, calendar features, lag features — and why domain-specific inputs improve forecast accuracy.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data, delayed measurements, and model failures in production so forecasts remain available even when inputs are imperfect.

- **Meta Ensembles** (:doc:`meta_ensembles`)
   Understand the ``openstef-meta`` ensemble approach: why combining multiple models produces more robust forecasts and how the meta-learning layer works conceptually.

- **Component Splitting** (:doc:`component_splitting`)
   See how OpenSTEF decomposes aggregate load measurements into energy components (solar, wind, base load) to improve interpretability and model performance.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
   meta_ensembles
   component_splitting
