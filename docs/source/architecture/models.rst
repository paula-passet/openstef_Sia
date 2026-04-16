The ``openstef_models`` Package
================================

This page provides a deep dive into the ``openstef_models`` package — the part of the OpenSTEF library
responsible for feature engineering, forecasting model implementations, and explainability tooling.
If you are looking for the foundational data types and interfaces that ``openstef_models`` builds on,
see the :doc:`core` page. For ensemble and meta-learning models, see :doc:`meta`.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

The package is organised around three cooperating concerns: **transforms** that encode domain
knowledge as composable feature-engineering steps, **models** that wire those transforms into
end-to-end forecasting pipelines, and **explainability** utilities that let you interrogate what
a trained model has learned. Understanding how these three layers relate to each other is the key
to using ``openstef_models`` effectively.


Transforms: Domain-Organised Feature Engineering
-------------------------------------------------

The ``openstef_models.transforms`` package groups feature-engineering logic by the domain it
belongs to rather than by implementation detail. This keeps energy-specific knowledge (wind power
curves, solar radiation geometry) separate from generic time-series utilities (lag creation,
cyclic encoding) and from data-quality checks (completeness, flatline detection).

The five sub-packages are:

- **``validation``** — input-quality checks such as ``CompletenessChecker``, ``FlatlineChecker``,
  and ``InputConsistencyChecker``. These are typically placed at the head of a preprocessing
  pipeline so that downstream transforms receive clean data.
- **``general``** — model-agnostic utilities including ``DimensionalityReducer``, ``Imputer``,
  ``NaNDropper``, and ``Selector``. These handle structural data preparation that is not specific
  to any physical domain.
- **``time_domain``** — temporal feature constructors: ``LagsAdder``, ``CyclicFeaturesAdder``,
  ``DatetimeFeaturesAdder``, and ``HolidayFeatureAdder``. These encode the periodicity and
  calendar structure that is central to load forecasting.
- **``weather_domain``** — derived meteorological features: ``RadiationDerivedFeaturesAdder``
  and ``AtmosphereDerivedFeaturesAdder``. These translate raw weather measurements into
  physically meaningful quantities such as clear-sky irradiance.
- **``energy_domain``** — power-system-specific transforms, currently anchored by
  ``WindPowerFeatureAdder``, which applies a wind power curve to convert wind speed into an
  estimated generation signal.

Every transform follows the same interface — ``fit``, ``transform``, and ``features_added`` — so
they compose uniformly inside a ``TransformPipeline`` (defined in ``openstef_core``). The
``features_added`` method is particularly useful: it lets a pipeline introspect which columns a
transform will introduce, enabling downstream ``Selector`` steps to include or exclude them by
name without hard-coding column lists.

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.time_domain import LagsAdder, HolidayFeatureAdder
   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   from openstef_models.transforms.validation import CompletenessChecker

   # Each transform declares what it adds — useful for building Selector steps
   wind = WindPowerFeatureAdder(windspeed_reference_column="wind_speed")
   print(wind.features_added())  # e.g. ['wind_power']

   holiday = HolidayFeatureAdder(country_code="NL")
   print(holiday.features_added())  # e.g. ['is_holiday']


Models: The ``ForecastingModel`` Pipeline
-----------------------------------------

The central abstraction in ``openstef_models.models`` is ``ForecastingModel``. It is a
single-forecaster pipeline that composes three stages:

1. **Preprocessing** — a ``TransformPipeline`` of transforms from the ``transforms`` package.
2. **Forecaster** — the statistical or machine-learning model that produces quantile predictions.
3. **Postprocessing** — a second ``TransformPipeline`` that sorts quantiles, applies confidence
   intervals, and performs any output-side corrections.

This three-stage structure means that the forecaster itself stays narrow in responsibility: it
receives a clean, fully-featured ``ForecastInputDataset`` and returns raw quantile predictions.
All data-quality enforcement and output formatting live in the surrounding pipeline stages.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import Q
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )
   from openstef_models.transforms.time_domain import LagsAdder, HolidayFeatureAdder
   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_core.mixins import TransformPipeline

   horizons = [timedelta(hours=h) for h in range(1, 49)]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   preprocessing = TransformPipeline([
       CompletenessChecker(completeness_threshold=0.7),
       HolidayFeatureAdder(country_code="NL"),
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=False,
           target_column="load",
           custom_lags=[timedelta(days=7)],
       ),
   ])

   forecaster = GBLinearForecaster(
       quantiles=quantiles,
       horizons=horizons,
       hyperparams=GBLinearHyperParams(),
   )

   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
       postprocessing=TransformPipeline([]),
       target_column="load",
       cutoff_history=timedelta(days=14),  # exclude rows made NaN by lag transforms
   )

.. note::

   The ``cutoff_history`` parameter deserves attention. Lag-based transforms introduce NaN values
   at the start of the training window — a 14-day lag means the first 14 days of data are
   incomplete. Setting ``cutoff_history`` to match the longest lag prevents the model from
   training on those incomplete rows. This must be configured manually because the pipeline
   cannot automatically infer lag depths from arbitrary transform objects.

``ForecastingModel.fit`` orchestrates the full sequence: it fits the preprocessing pipeline,
transforms the training data, fits the forecaster, then fits the postprocessing pipeline on the
resulting predictions. ``predict`` applies the already-fitted transforms in order. The ``score``
method evaluates the model on a held-out dataset and returns a ``SubsetMetric`` object.


Available Forecasters
^^^^^^^^^^^^^^^^^^^^^

The preset system (discussed below) reveals the forecasters that ship with ``openstef_models``:

- **``XGBoostForecaster``** — gradient-boosted trees via XGBoost; the default choice for
  complex non-linear patterns. Supports CPU and GPU computation.
- **``GBLinearForecaster``** — a linear model trained with the XGBoost ``gblinear`` booster;
  faster to train and more interpretable, well-suited to sites where load follows a near-linear
  relationship with weather and calendar features.
- **``LGBMForecaster``** and **``LGBMLinearForecaster``** — LightGBM equivalents of the above.
- **``MedianForecaster``** — a simple lag-based median model; useful as a baseline.
- **``FlatlinerForecaster``** — a specialised model for grid points that exhibit persistent
  zero or near-zero load (flatliners), where standard models would otherwise over-fit to noise.

Each forecaster accepts ``quantiles`` and ``horizons`` at construction time, so the pipeline
knows from the outset what outputs to produce.


Presets: Batteries-Included Configurations
-------------------------------------------

Building a preprocessing pipeline by hand is powerful but verbose. The
``openstef_models.presets`` sub-package provides ``ForecastingWorkflowConfig``, a Pydantic
configuration object that encodes sensible defaults for each model type and constructs the full
``ForecastingModel`` for you.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import ForecastingWorkflowConfig
   from openstef_core.types import Q, LeadTime
   from pydantic_extra_types.coordinate import Latitude, Longitude
   from pydantic_extra_types.country import CountryAlpha2

   config = ForecastingWorkflowConfig(
       model="gblinear",
       target_column="load",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       location=dict(
           latitude=Latitude(52.37),
           longitude=Longitude(4.90),
           country_code=CountryAlpha2("NL"),
       ),
   )

   # Build the fully-configured ForecastingModel from the config
   workflow = config.build()

The preset assembles the correct combination of validation checks, lag adders, weather-derived
feature adders, holiday encoders, imputers, and postprocessors for the chosen model type. For
example, the ``gblinear`` preset adds only a 7-day lag (rather than the full lag matrix used by
tree-based models) and includes an ``Imputer`` and ``NaNDropper`` because the linear booster
cannot handle missing values natively. These model-specific decisions are encoded once in the
preset and reused consistently across all users of the library.

Presets are the recommended starting point. Once you understand what a preset builds, you can
deviate from it selectively — swap the forecaster, add a domain-specific transform, or tighten
the completeness threshold — without rewriting the entire pipeline from scratch.


Explainability
--------------

Understanding *why* a model makes a particular prediction is as important as the prediction
itself, especially in operational settings where forecasts drive grid management decisions.
``openstef_models.explainability`` provides two mixin interfaces and a plotter that forecasters
can implement.

``ExplainableForecaster`` exposes:

- **``feature_importances``** (property) — a ``pd.DataFrame`` of global importance scores
  aggregated across the training set.
- **``plot_feature_importances``** — an interactive Plotly treemap where box area encodes
  relative importance, making it easy to see which feature groups dominate.

``ContributionsMixin`` exposes:

- **``predict_contributions``** — per-sample feature contributions for a given input dataset,
  returned as a ``TimeSeriesDataset``. This enables local explanations: for any individual
  forecast, you can see how much each feature pushed the prediction up or down.

``ForecastingModel.predict_contributions`` delegates to the underlying forecaster if it
implements ``ContributionsMixin``, and raises ``NotImplementedError`` otherwise. This means
you can write code that conditionally uses contributions without needing to know the forecaster
type at call time.

.. code-block:: python

   from typing import cast
   from openstef_models.explainability import ExplainableForecaster, FeatureImportancePlotter

   # GBLinearForecaster implements ExplainableForecaster
   explainable = cast(ExplainableForecaster, model.forecaster)

   # Global feature importance as a DataFrame
   importances = explainable.feature_importances
   print(importances.head())

   # Interactive treemap — larger boxes indicate more influential features
   fig = explainable.plot_feature_importances()
   fig.show()

   # Per-sample contributions (requires ContributionsMixin)
   from openstef_models.explainability import ContributionsMixin
   if isinstance(model.forecaster, ContributionsMixin):
       contributions = model.predict_contributions(data=dataset)

The ``FeatureImportancePlotter`` class in ``openstef_models.explainability.plotters`` provides
additional plotting utilities when you need more control over the visualisation than the mixin
methods offer directly.


Compositional Design
--------------------

The design of ``openstef_models`` is deliberately compositional rather than inheritance-based.
A ``ForecastingModel`` does not subclass a forecaster — it *contains* one. A preprocessing
pipeline does not extend a base class with overridable hooks — it *sequences* independent
transform objects. This means:

- **Transforms are reusable across models.** The same ``LagsAdder`` instance can appear in
  the preprocessing pipeline of an XGBoost model and a GBLinear model.
- **Forecasters are swappable without touching the pipeline.** Changing from ``XGBoostForecaster``
  to ``GBLinearForecaster`` requires only replacing the forecaster argument; the surrounding
  transforms remain unchanged.
- **Explainability is opt-in.** A forecaster that does not implement ``ExplainableForecaster``
  still works perfectly inside ``ForecastingModel``; the explainability methods simply become
  unavailable.

This composability is what makes the preset system tractable: each preset is just a function
that selects and wires together the right components for a given model type, using the same
building blocks that you would assemble by hand.

For ensemble models that combine multiple forecasters — each with its own preprocessing branch —
see the :doc:`meta` page, which describes how ``openstef_meta`` extends this compositional
pattern to multi-model architectures.