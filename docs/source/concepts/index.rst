Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library — helping you understand not just *how* to use it, but *why* it works the way it does.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a single-model solution.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty estimates matter more than point predictions alone.

- **Model Selection** (:doc:`model_selection`)
   Compare the forecasting model types available in OpenSTEF and understand the criteria for choosing the right one for your use case.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF uses — weather variables, calendar features, lagged observations — and how domain knowledge is baked into the library's feature pipeline.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Understand how OpenSTEF handles model failures, missing data, and degraded inputs in production to keep forecasts flowing even under adverse conditions.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
