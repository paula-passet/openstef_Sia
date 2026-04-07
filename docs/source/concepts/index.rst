Core Concepts
=============

This section explains the ideas and design decisions behind OpenSTEF. Understanding these concepts will help you make better use of the library—choosing the right models, interpreting probabilistic outputs, and building forecasting pipelines that hold up in production.

OpenSTEF automates many typical machine learning activities for short-term energy forecasting, including data preparation, feature engineering, and single-shot multi-horizon prediction. The pages below unpack how each of these pieces works and why they matter.

:doc:`forecasting_basics` - What short-term energy forecasting is, why the energy sector needs it, and how it differs from long-term planning or simple extrapolation. Start here if you are new to the domain.

:doc:`quantiles_and_confidence` - How OpenSTEF produces probabilistic forecasts rather than single point estimates. Learn what quantiles represent, how to read confidence intervals, and why uncertainty information is essential for grid operations.

:doc:`model_selection` - A guide to the forecasting models available in OpenSTEF and when to use each one. Covers the trade-offs between model types and how the library's automated selection works.

:doc:`feature_engineering` - The predictors that drive accurate forecasts: weather variables, calendar features, lag-based inputs, and more. Explains how OpenSTEF constructs and selects features automatically.

:doc:`reliability_and_fallback` - How to keep forecasts flowing when things go wrong. Covers fallback strategies for model failures, handling missing or delayed input data, and designing pipelines that degrade gracefully.

.. note::

   If you are looking for step-by-step instructions rather than conceptual background, see the :doc:`/user_guides/index` section instead.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
