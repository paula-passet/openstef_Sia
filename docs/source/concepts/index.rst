Core Concepts
=============

This section explains the fundamental ideas behind short-term energy forecasting and how OpenSTEF approaches these challenges. Understanding these concepts will help you make informed decisions when building forecasting pipelines with the library.

You'll learn about probabilistic forecasting, model selection trade-offs, feature engineering strategies, and how to build reliable production systems. These pages focus on the "why" behind OpenSTEF's design, not just the "how."

What's in this section
----------------------

:doc:`forecasting_basics`
   What short-term forecasting is, why energy systems need it, and how it differs from other prediction tasks.

:doc:`quantiles_and_confidence`
   How to interpret probabilistic forecasts and why quantile predictions matter for decision-making.

:doc:`model_selection`
   Guidance on choosing between XGBoost, linear models, and other forecasters based on your data and requirements.

:doc:`feature_engineering`
   Which predictors matter most for energy forecasting, including weather data, temporal features, and domain-specific variables.

:doc:`reliability_and_fallback`
   Strategies for handling failures gracefully in production, including fallback mechanisms and missing data handling.

:doc:`architecture`
   How OpenSTEF's components fit together, with diagrams showing the library's internal structure.

Start with :doc:`forecasting_basics` if you're new to energy forecasting, or jump to :doc:`model_selection` if you want to compare available algorithms.

.. toctree::
   :hidden:
   :maxdepth: 1

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
   architecture


.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
   architecture

