Concepts
========

This section explains the core ideas behind short-term energy forecasting and the design decisions that shape how OpenSTEF works as a library — giving you the context to use it more effectively.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand what short-term load forecasting is, why it matters for grid operations, and how OpenSTEF's multi-horizon pipeline approaches the problem.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn how OpenSTEF produces probabilistic forecasts with uncertainty bandwidths, and how to interpret quantile outputs in practice.

- **Model Selection** (:doc:`model_selection`)
   Compare the available model types in OpenSTEF, understand their trade-offs, and find guidance on choosing the right one for your use case.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF provides — weather data, time features, lag features, and domain-specific signals like PV generation estimates.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Understand how OpenSTEF handles missing data and model failures in production, including the fallback strategies that keep forecasts running.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
