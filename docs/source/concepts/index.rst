Core Concepts
=============

This section explains the foundational ideas behind OpenSTEF and short-term energy forecasting. Understanding these concepts will help you make better decisions when building forecasting pipelines and interpreting results.

:doc:`forecasting_basics` explains what short-term forecasting is, why it matters for energy systems, and how it differs from other types of prediction. Start here if you're new to energy forecasting.

:doc:`quantiles_and_confidence` covers probabilistic forecasts and how to interpret quantile predictions. This is essential for understanding uncertainty in your forecasts and making risk-aware decisions.

:doc:`model_selection` helps you choose the right forecasting model for your use case. It compares available model types and explains when to use each one based on data characteristics and requirements.

:doc:`feature_engineering` describes the most important predictors for energy forecasting, including weather features, temporal patterns, and domain-specific variables. Learn how to prepare input data for better forecast accuracy.

:doc:`reliability_and_fallback` addresses production concerns like fallback strategies when models fail, handling missing or invalid data, and ensuring your forecasting pipeline runs reliably in operational environments.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
