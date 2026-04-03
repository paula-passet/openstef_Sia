Core Concepts
=============

This section explains the fundamental ideas behind OpenSTEF and short-term energy forecasting. Understanding these concepts will help you make better decisions when building forecasting pipelines with the library.

You'll learn what makes short-term forecasting different from other prediction tasks, how to interpret probabilistic forecasts, which models work best for different scenarios, and how to build reliable production systems.

What's in this section
----------------------

**Forecasting basics** introduces short-term forecasting: what it is, why energy systems need it, and how it differs from other types of prediction.

**Quantiles and confidence** explains probabilistic forecasts and how to interpret quantile predictions for risk management and decision-making.

**Model selection** compares the forecasting models available in OpenSTEF and helps you choose the right one for your use case.

**Feature engineering** covers the predictors that matter most: weather data, temporal patterns, and domain-specific features that improve forecast accuracy.

**Reliability and fallback** describes strategies for production systems: handling missing data, fallback mechanisms when models fail, and maintaining forecast availability.

Start with forecasting basics if you're new to the domain, or jump directly to the topic most relevant to your current challenge.

.. toctree::
   :maxdepth: 1
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback


.. toctree::
   :maxdepth: 1
   :caption: Contents

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback

