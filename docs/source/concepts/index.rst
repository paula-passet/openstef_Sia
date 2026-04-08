Core Concepts
=============

This section explains the fundamentals of short-term energy forecasting and the design philosophy behind OpenSTEF. Start here to understand the 'why' before diving into code.

**Forecasting Basics** (:doc:`forecasting_basics`)
   What short-term forecasting is, why it matters for grid management, and how OpenSTEF approaches the problem.

**Quantiles and Confidence** (:doc:`quantiles_and_confidence`)
   How probabilistic forecasts work and why uncertainty estimates are critical for operational decisions.

**Model Selection** (:doc:`model_selection`)
   Compare available model types and understand when to use each based on your data and requirements.

**Feature Engineering** (:doc:`feature_engineering`)
   Key predictors for energy forecasting including weather data, time features, and domain-specific transformations.

**Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Production-ready strategies for handling model failures, missing data, and maintaining forecast availability.

.. toctree::
   :maxdepth: 1
   :caption: Core Concepts
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   model_selection
   feature_engineering
   reliability_and_fallback
