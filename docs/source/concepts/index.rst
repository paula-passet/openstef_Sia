Concepts
========

This section explains the core ideas behind OpenSTEF — from how short-term energy forecasting works to the design decisions that shape the library's behaviour in production.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid management, and how OpenSTEF approaches multi-horizon prediction.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn how OpenSTEF produces probabilistic forecasts rather than single-point predictions, and how to interpret uncertainty bandwidths in practice.

- **Model Selection** (:doc:`model_selection`)
   Compare the available model types in OpenSTEF and understand which to choose based on your data characteristics and forecasting goals.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF provides — weather variables, time features, and domain-specific transformations like solar radiation to PV generation estimates.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data and model failures in production, including the fallback strategies that keep forecasts available under adverse conditions.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
