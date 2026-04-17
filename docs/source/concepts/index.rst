Concepts
========

This section explains the ideas and design decisions behind OpenSTEF, helping you understand *why* the library works the way it does before diving into the API.

- **Forecasting Basics** (:doc:`forecasting_basics`)
   What short-term energy forecasting is, why it matters for grid operations, and how OpenSTEF approaches it as a model-agnostic ML library.

- **Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   How to read and use OpenSTEF's probabilistic forecasts, which express uncertainty as quantile bands rather than single-point predictions.

- **Feature Engineering** (:doc:`feature_engineering`)
   The key predictors OpenSTEF builds automatically — weather variables, calendar features, and energy-domain transformations like PV generation estimates.

- **Reliability and Fallback** (:doc:`reliability_and_fallback`)
   How OpenSTEF handles missing data and model failures in production, and what fallback strategies are available to keep forecasts running.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
