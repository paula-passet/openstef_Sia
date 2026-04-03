Core Concepts
=============

This section explains the fundamental ideas behind short-term energy forecasting and how OpenSTEF approaches the problem. Understanding these concepts will help you make informed decisions about model selection, feature engineering, and production deployment.

What You'll Learn
-----------------

These pages cover the theoretical foundations and practical considerations that inform how you use OpenSTEF. You'll learn why probabilistic forecasts matter, how different models handle uncertainty, and what makes energy forecasting different from other time series problems.

Start with **Forecasting Basics** to understand what short-term forecasting means in the energy sector and why it requires specialized approaches. The **Quantiles and Confidence** page explains how OpenSTEF represents uncertainty through quantile predictions rather than point estimates—a critical concept for interpreting forecast outputs.

When you're ready to choose a model, **Model Selection** compares the available forecasting algorithms and helps you match model characteristics to your specific requirements. **Feature Engineering** dives into the predictors that drive forecast accuracy, from weather variables to temporal patterns and calendar effects.

Finally, **Reliability and Fallback** addresses production concerns: what happens when models fail, how to handle missing data gracefully, and strategies for maintaining service continuity even when primary forecasts aren't available.

These concepts apply across all OpenSTEF workflows, whether you're training models, generating forecasts, or evaluating performance.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
