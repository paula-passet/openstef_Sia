The Models Package
==================

This page covers the ``openstef-models`` package in depth — its three principal layers (transforms, forecasting models, and explainability), how they compose into a complete pipeline, and the design patterns that tie them together. For the shared data types and interfaces that this package builds on, see the :doc:`core` sibling page. For backtesting and evaluation of trained models, see :doc:`beam`.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

Overview
--------

``openstef-models`` is the forecasting engine of OpenSTEF. It is deliberately structured as a *library* of composable pieces rather than a monolithic application: you can use a single transform in isolation, wire several transforms into a ``FeaturePipeline``, wrap that pipeline in a ``ForecastingModel``, and then attach explainability behaviour through mixins — all at the level of granularity that suits your use case.

The package is organised into three cooperating namespaces:

- ``openstef_models.transforms`` — domain-specific feature engineering steps
- ``openstef_models.models`` — forecasting implementations and the pipeline wrapper
- ``openstef_models.explainability`` — tools for understanding what a trained model has learned

The Transforms Layer
--------------------

Feature engineering in ``openstef-models`` is expressed as a collection of *transform* objects, each responsible for a single, well-defined enrichment of the input dataset. Transforms are grouped by domain so that you can import only what is relevant to your problem:

.. code-block:: python

   from openstef_models.transforms import (
       energy_domain,
       general,
       time_domain,
       validation,
       weather_domain,
   )

**Validation transforms** (``transforms.validation``) act as guards at the front of a pipeline. They include ``InputConsistencyChecker``, ``FlatlineChecker``, and ``CompletenessChecker``. Rather than raising exceptions silently inside a model, these transforms make data-quality assumptions explicit and configurable — for instance, ``FlatlineChecker`` accepts a threshold and a flag controlling whether a flatline is a hard error or a warning.

**Time-domain transforms** (``transforms.time_domain``) encode temporal structure that tree-based and linear models cannot infer on their own. ``CyclicFeaturesAdder`` converts hour-of-day, day-of-week, and similar periodic signals into sine/cosine pairs so that the model sees continuity across midnight or the end of the week. ``LagsAdder`` materialises historical values at configurable horizons, and can optionally include a fixed seven-day lag that is particularly useful for capturing weekly seasonality in load profiles.

**Weather-domain transforms** (``transforms.weather_domain``) derive physically meaningful features from raw meteorological inputs. ``AtmosphereDerivedFeaturesAdder`` computes quantities such as dew point and apparent temperature from pressure, relative humidity, and dry-bulb temperature. ``RadiationDerivedFeaturesAdder`` uses the geographic coordinate of the asset together with a radiation column to produce solar-angle-corrected irradiance features.

**Energy-domain transforms** (``transforms.energy_domain``) encode power-system knowledge. The current public surface exposes ``WindPowerFeatureAdder``, which derives aerodynamic features from a wind-speed reference column — a compact way to give a generic gradient-boosting model the benefit of domain physics without hard-coding a wind-power curve.

Composing a Feature Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual transforms become useful at scale when assembled into a ``FeaturePipeline``. The pipeline distinguishes between *aligners* (transforms that shift or align existing columns, such as lag shifters) and *adders* (transforms that append new columns). This separation makes the order of operations unambiguous and allows the pipeline to be serialised and reloaded alongside a trained model.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import LagsAdder, CyclicFeaturesAdder
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.validation import (
       FlatlineChecker,
       CompletenessChecker,
   )
   from openstef_core.types import Coordinate

   # Validation guards run first
   checks = [
       FlatlineChecker(load_column="load", flatliner_threshold=6, error_on_flatliner=False),
       CompletenessChecker(completeness_threshold=0.75),
   ]

   # Feature adders enrich the dataset
   adders = [
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=[timedelta(hours=h) for h in range(1, 25)],
           target_column="load",
       ),
       CyclicFeaturesAdder(),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=Coordinate(lat=52.1, lon=5.1),
           radiation_column="radiation",
       ),
   ]

Each transform in the pipeline implements a consistent ``fit`` / ``transform`` interface, making the whole assembly compatible with scikit-learn conventions and easy to persist with joblib.

The Models Layer
----------------

``openstef_models.models`` contains the forecasting implementations. The central abstraction is the ``ForecastingModel``, a pipeline wrapper that owns a ``FeaturePipeline`` for preprocessing, a concrete forecaster for prediction, and an optional postprocessing stage. This three-stage structure means that swapping the underlying algorithm — say, replacing ``XGBoostForecaster`` with a different estimator — does not require touching the feature engineering or postprocessing code.

Forecasting Implementations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``XGBoostForecaster`` is the primary production-grade estimator. It is built for *probabilistic* forecasting: rather than producing a single point estimate, it outputs a distribution over quantiles, which is essential for grid operators who need to reason about worst-case demand or generation scenarios. The quantile set is configurable and the model internally trains one gradient-boosting tree per quantile.

``ConstantMedianForecaster`` is a lightweight baseline that always predicts the median of the training target. It is useful for sanity-checking pipelines and for establishing a lower bound on forecast quality before investing in more complex models.

Assembling a Complete Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following example wires together a ``FeaturePipeline`` and a ``ForecastingModel``, trains on synthetic data, and produces a forecast:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta
   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.models.pipeline import ForecastingModel, FeaturePipeline
   from openstef_models.transforms.time_domain import LagsAdder, CyclicFeaturesAdder
   from openstef_models.transforms.validation import CompletenessChecker

   # --- Data ---
   train_dataset, forecast_dataset = create_synthetic_forecasting_dataset()

   # --- Feature pipeline ---
   feature_pipeline = FeaturePipeline(
       checks=[CompletenessChecker(completeness_threshold=0.5)],
       feature_adders=[
           LagsAdder(
               history_available=timedelta(days=7),
               horizons=[timedelta(hours=h) for h in range(1, 25)],
               target_column="load",
           ),
           CyclicFeaturesAdder(),
       ],
   )

   # --- Forecasting model ---
   model = ForecastingModel(
       feature_pipeline=feature_pipeline,
       forecaster=XGBoostForecaster(),
   )

   model.fit(train_dataset)
   forecast: TimeSeriesDataset = model.predict(forecast_dataset)

.. note::

   ``ForecastingModel.predict`` returns a ``TimeSeriesDataset`` (defined in ``openstef-core``) rather than a plain ``DataFrame``. This preserves metadata such as the forecast horizon and quantile labels, which downstream consumers — including the evaluation tools in ``openstef-beam`` — rely on. See the :doc:`core` page for details on ``TimeSeriesDataset``.

Presets
^^^^^^^

For common configurations, ``openstef_models.presets`` provides factory functions that assemble a ``ForecastingModel`` from a configuration object. This is the recommended entry point when you want a production-ready setup without manually specifying every transform:

.. code-block:: python

   from openstef_models.presets import build_forecasting_workflow_from_config

   workflow = build_forecasting_workflow_from_config(config)
   workflow.train(train_dataset)
   forecast = workflow.predict(forecast_dataset)

Under the hood, ``build_forecasting_workflow_from_config`` selects the appropriate forecaster based on ``config.model``, populates ``LagsAdder`` from ``config.horizons`` and ``config.predict_history``, conditionally adds ``WindPowerFeatureAdder`` and radiation features based on the columns present in the configuration, and wires in the validation checks. The preset is a convenience layer, not a constraint — you can always construct the same pipeline manually for full control.

The Explainability Layer
------------------------

Understanding *why* a model produces a particular forecast is as important as the forecast itself, especially in regulated energy markets. ``openstef_models.explainability`` provides this capability through two mixins and a built-in plotter.

Mixins and the Decorator Pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ExplainableForecaster`` is an abstract mixin that any forecaster can implement to expose feature importance scores:

.. code-block:: python

   from openstef_models.explainability.mixins import ExplainableForecaster

   # XGBoostForecaster already implements ExplainableForecaster
   scores: pd.DataFrame = model.forecaster.feature_importances

``ContributionsMixin`` goes further: it exposes ``predict_contributions``, which returns per-sample feature contributions for a given input dataset. This is the SHAP-style decomposition that allows you to attribute each individual forecast value to specific input features.

.. code-block:: python

   from openstef_models.explainability.mixins import ContributionsMixin

   contributions: TimeSeriesDataset = model.forecaster.predict_contributions(forecast_dataset)

The mixin design means that explainability is an *opt-in capability* rather than a mandatory overhead. A lightweight forecaster that does not support SHAP simply does not implement ``ContributionsMixin``, and calling code can check with ``isinstance`` before attempting to use it.

Visualising Feature Importance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_models.explainability.plotters`` provides ``FeatureImportancePlotter``, which renders an interactive treemap using Plotly. The treemap groups features by their domain prefix (lag features, weather features, cyclic features, and so on), making it easy to see at a glance which categories of information the model relies on most.

.. code-block:: python

   from openstef_models.explainability.plotters import FeatureImportancePlotter
   from openstef_core.types import Q

   plotter = FeatureImportancePlotter()

   # plot() accepts the DataFrame returned by feature_importances
   fig = plotter.plot(scores=model.forecaster.feature_importances, quantile=Q(0.5))
   fig.show()

Alternatively, if the forecaster implements ``ExplainableForecaster``, the convenience method ``plot_feature_importances`` is available directly on the forecaster object:

.. code-block:: python

   fig = model.forecaster.plot_feature_importances(quantile=Q(0.5))
   fig.show()

Both paths produce the same interactive Plotly figure. The ``quantile`` argument selects which quantile's importance scores to display, which is relevant for multi-quantile models where different quantiles may weight features differently.

Design Patterns and Relationships
----------------------------------

The three layers described above follow a consistent set of design principles that are worth making explicit:

**Composition over inheritance.** ``ForecastingModel`` does not subclass ``XGBoostForecaster``; it *contains* a forecaster. Similarly, explainability is added through mixins rather than a deep class hierarchy. This makes it straightforward to combine any forecaster with any set of transforms.

**Separation of concerns.** Transforms know nothing about the forecaster; the forecaster knows nothing about explainability. Each layer has a single responsibility, which makes individual components testable in isolation.

**scikit-learn compatibility.** All transforms and forecasters implement ``fit`` / ``transform`` or ``fit`` / ``predict`` interfaces. This means the entire pipeline can be serialised with joblib (via the ``openstef_models.integrations.joblib`` integration), and individual components can be used inside scikit-learn ``Pipeline`` objects if needed.

**Domain knowledge as first-class code.** Rather than encoding energy-domain knowledge in ad-hoc preprocessing scripts, ``openstef-models`` packages it as reusable, versioned transform objects. ``WindPowerFeatureAdder`` and ``RadiationDerivedFeaturesAdder`` are the library's way of saying: this physics matters, and it should be applied consistently across every model that uses wind or solar inputs.

Further Reading
---------------

- :doc:`core` — ``TimeSeriesDataset``, ``ForecastDataset``, and the base interfaces that transforms and models build on.
- :doc:`beam` — Backtesting, metrics, and regression testing for evaluating trained ``ForecastingModel`` instances.