Core Concepts
=============

This section explains the fundamental ideas behind OpenSTEF and short-term energy forecasting. Understanding these concepts helps you make better decisions about model selection, feature engineering, and production deployment. Whether you're new to forecasting or experienced with machine learning, these pages provide the context for using OpenSTEF effectively.

:doc:`forecasting_basics` - What short-term energy forecasting is, why it matters for grid management, and how OpenSTEF's multi-horizon approach differs from traditional time series methods.

:doc:`quantiles_and_confidence` - How probabilistic forecasts work in OpenSTEF, what quantiles represent, and why uncertainty estimates are essential for operational decisions like congestion management.

:doc:`model_selection` - Guidance on choosing between XGBoost, gradient boosted linear models, and other forecasters based on your data characteristics, extrapolation needs, and interpretability requirements.

:doc:`feature_engineering` - The predictors that drive forecast accuracy, including weather data, temporal patterns, and domain-specific features like solar radiation transformations that OpenSTEF provides.

:doc:`reliability_and_fallback` - Production reliability strategies for handling model failures, missing data, and edge cases to ensure your forecasting pipeline remains operational.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
