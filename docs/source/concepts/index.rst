Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library — essential reading before diving into the API.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty bandwidths matter more than point predictions in production.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF uses — weather variables, calendar features, lag features — and how domain knowledge is encoded directly into the library.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles real-world data quality issues: missing measurements, delayed weather forecasts, and automatic fallback strategies that keep production forecasts running.

- **Meta Ensembles** (:doc:`meta_ensembles`)
   Understand the ``openstef-meta`` ensemble approach — why combining multiple models improves robustness and how the library coordinates them without extra configuration.

- **Component Splitting** (:doc:`component_splitting`)
   See how OpenSTEF decomposes aggregate load measurements into energy components (solar, wind, base load), and why this decomposition leads to more accurate and interpretable forecasts.

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
