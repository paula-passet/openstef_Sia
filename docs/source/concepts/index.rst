Concepts
========

This section explains the core ideas behind OpenSTEF — what it does, how it works, and why it is designed the way it is — giving you the foundation to use the library effectively.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   Understand short-term energy forecasting: what it means to predict load hours to days ahead, and why it matters for congestion management and grid operations.

- **Quantiles and Confidence** (:doc:`quantiles_and_confidence`)
   Learn how OpenSTEF produces probabilistic forecasts with uncertainty bandwidths, and how to interpret quantile outputs in practice.

- **Model Selection** (:doc:`model_selection`)
   Compare the available model types in OpenSTEF and understand which to choose based on your data, use case, and accuracy requirements.

- **Feature Engineering** (:doc:`feature_engineering`)
   Explore the built-in predictors OpenSTEF provides — weather variables, time features, and domain-specific signals like PV generation estimates — and how to extend them.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Discover how OpenSTEF handles missing data and model failures in production, including the fallback strategies that keep forecasts running under adverse conditions.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
