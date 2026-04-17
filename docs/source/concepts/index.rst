Core Concepts
=============

This section explains the ideas behind OpenSTEF's design — from how short-term energy forecasting works to why the library is built the way it is. Read these pages to understand the *why* before diving into the how-to guides.

**Forecasting Basics** (:doc:`forecasting_basics`)
   Start here to understand what short-term energy forecasting is, why it matters for grid operations, and how OpenSTEF approaches the problem differently from a standalone model.

**Quantiles and Confidence Intervals** (:doc:`quantiles_and_confidence`)
   Learn what probabilistic forecasts are, how to read quantile outputs, and why uncertainty estimates matter more than single-point predictions in operational settings.

**Feature Engineering** (:doc:`feature_engineering`)
   Understand which predictors drive forecast accuracy — weather signals, calendar features, lagged load — and how OpenSTEF builds them automatically from raw inputs.

**Reliability and Fallback** (:doc:`reliability_and_fallback`)
   Covers how OpenSTEF handles missing data, degraded inputs, and model failures in production so forecasts remain available even when conditions are imperfect.

**Meta-Ensembles** (:doc:`meta_ensembles`)
   Explains the ensemble approach used to combine multiple base models, when it helps, and the trade-offs involved in stacking forecasters.

**Component Splitting** (:doc:`component_splitting`)
   Describes how aggregate load measurements are decomposed into energy components (solar, wind, base load) and why this improves both accuracy and interpretability.

.. toctree::
   :maxdepth: 1
   :caption: Contents
   :hidden:

   forecasting_basics
   quantiles_and_confidence
   feature_engineering
   reliability_and_fallback
   meta_ensembles
   component_splitting
