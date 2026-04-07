Core Concepts
=============

This section explains the foundational ideas behind OpenSTEF and short-term energy forecasting. Understanding these concepts will help you make better decisions when building forecasting systems with the library.

If you're new to energy forecasting, start with :doc:`forecasting_basics` to understand what short-term forecasting is, why it matters for grid operations, and how it differs from other types of prediction. This page provides essential context for working with OpenSTEF.

For users building production systems, :doc:`quantiles_and_confidence` explains how OpenSTEF produces probabilistic forecasts rather than single point predictions. You'll learn what quantiles represent, how to interpret confidence intervals, and why this approach is valuable for operational decision-making.

Choosing the right algorithm is critical for forecast quality. :doc:`model_selection` compares the model types available in OpenSTEF—including gradient boosting, linear models, and ensemble approaches—and helps you understand when to use each one based on your data characteristics and requirements.

Good features are the foundation of accurate forecasts. :doc:`feature_engineering` covers the most important predictors for energy forecasting, including weather data, temporal patterns, and lagged values. This page shows you how OpenSTEF handles feature creation and what to consider when preparing your input data.

Finally, :doc:`reliability_and_fallback` addresses production concerns: what happens when models fail, how to handle missing input data, and strategies for maintaining forecast availability even when components break. These patterns are essential for deploying OpenSTEF in operational environments.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
