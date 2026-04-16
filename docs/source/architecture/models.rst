The ``openstef_models`` Package
================================

The ``openstef_models`` package is the forecasting engine of OpenSTEF. It provides
everything needed to go from raw time series data to a calibrated probabilistic
forecast: domain-specific feature transforms, a suite of forecasting model
implementations, and explainability tools for inspecting what a trained model has
learned. This page explores the internal design of the package, the relationships
between its three main layers, and how you compose them into a working pipeline.

For ensemble and meta-learning models that build on top of these primitives, see
:doc:`meta`. For backtesting and evaluation utilities, see :doc:`beam`.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

Package Structure
-----------------

The package is organised into four top-level namespaces::

    openstef_models/
    ├── transforms/          # Feature engineering, validation, postprocessing
    │   ├── time_domain/     # Temporal and calendar features
    │   ├── energy_domain/   # Physics-informed energy features
    │   ├── weather_domain/  # Meteorological features
    │   ├── general/         # Imputation, scaling, selection, outlier handling
    │   └── validation/      # Data quality checks
    ├── models/              # Forecasting model implementations
    ├── explainability/      # Feature importance and contribution tools
    └── presets/             # Pre-wired workflow configurations

The design is deliberately compositional: transforms are stateless or stateful
sklearn-style objects, models wrap a forecaster with a pipeline of transforms, and
explainability is added through mixins rather than baked into any single class.
This means you can swap any layer independently.

The Transforms Layer
--------------------

Transforms are the feature engineering backbone of ``openstef_models``. Rather than
a single monolithic preprocessing step, they are grouped by domain so that each
sub-package captures a coherent body of knowledge.

**Time-domain transforms** derive features from the timestamp index itself. This
includes cyclic encodings of hour-of-day and day-of-week (``CyclicFeaturesAdder``),
one-hot or ordinal datetime decompositions (``DatetimeFeaturesAdder``), country-aware
public holiday flags (``HolidayFeatureAdder``), rolling aggregates
(``RollingAggregatesAdder``), and lag features (``LagsAdder``). These are the most
universally applicable transforms and appear in almost every preset.

**Energy-domain transforms** encode physical knowledge about the power system.
``WindPowerFeatureAdder``, for example, derives wind-power-curve features from raw
wind speed measurements — a non-linear relationship that a tree model would otherwise
need to learn from scratch.

**General transforms** handle data hygiene: ``Imputer`` fills missing values,
``NaNDropper`` removes rows that cannot be imputed, ``OutlierHandler`` clips or
removes statistical outliers, ``Scaler`` standardises features, and ``Selector``
includes or excludes named columns. ``SampleWeighter`` assigns per-sample training
weights, which is important for giving recent observations more influence.

All transforms implement the ``TransformPipeline`` interface from ``openstef_core``,
so they compose naturally into ordered pipelines.

.. code-block:: python

    from openstef_models.transforms.time_domain import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
        LagsAdder,
    )
    from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
    from openstef_core.mixins import TransformPipeline
    from pydantic_extra_types.country import CountryAlpha2

    # Build a reusable preprocessing pipeline from individual transforms
    preprocessing = TransformPipeline(
        steps=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagsAdder(lags=[timedelta(hours=1), timedelta(hours=24), timedelta(days=7)]),
            Imputer(imputation_strategy="mean"),
            NaNDropper(),
            Scaler(),
        ]
    )

Each transform exposes a ``fit`` / ``transform`` interface. Calling
``preprocessing.fit(data)`` fits any stateful transforms (e.g. ``Scaler`` learns
mean and variance), and ``preprocessing.transform(data)`` applies the full sequence.
The fitted pipeline is serialised together with the model when you persist it, so
inference always uses the same statistics as training.

The Models Layer
----------------

The ``models`` sub-package provides the forecasting implementations. OpenSTEF ships
several forecasters out of the box:

- **GBLinearForecaster** — gradient-boosted linear model; the default choice for
  most energy forecasting tasks because it combines interpretability with strong
  performance on tabular data.
- **XGBoostForecaster** — XGBoost-based model suited to datasets with complex
  non-linear patterns.
- **LGBMForecaster** / **LGBMLinearForecaster** — LightGBM variants offering faster
  training on large datasets.
- **MedianForecaster** / **FlatlinerForecaster** — simple baselines used for
  sanity-checking and handling degenerate inputs.

All forecasters are wrapped by ``ForecastingModel``, which is the object you
actually train and deploy. ``ForecastingModel`` owns three things: a ``forecaster``
instance, a preprocessing ``FeaturePipeline``, and an optional postprocessing
pipeline. This separation means the forecaster itself only ever sees clean,
fully-engineered features — it has no knowledge of raw timestamps or missing values.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import Q
    from openstef_models.models import ForecastingModel
    from openstef_models.models.forecasting.gblinear_forecaster import (
        GBLinearForecaster,
        GBLinearHyperParams,
    )
    from openstef_models.transforms.time_domain import (
        HolidayFeatureAdder,
        DatetimeFeaturesAdder,
        LagsAdder,
    )
    from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
    from openstef_core.mixins import TransformPipeline
    from pydantic_extra_types.country import CountryAlpha2

    quantiles = [Q(0.1), Q(0.5), Q(0.9)]
    horizons = [timedelta(hours=h) for h in range(1, 25)]

    forecaster = GBLinearForecaster(
        hyperparams=GBLinearHyperParams(),
        quantiles=quantiles,
        horizons=horizons,
    )

    preprocessing = TransformPipeline(
        steps=[
            HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
            DatetimeFeaturesAdder(onehot_encode=False),
            LagsAdder(lags=[timedelta(hours=1), timedelta(hours=24)]),
            Imputer(imputation_strategy="mean"),
            NaNDropper(),
            Scaler(),
        ]
    )

    model = ForecastingModel(
        forecaster=forecaster,
        preprocessing=preprocessing,
    )

Training and prediction follow a consistent interface regardless of which forecaster
is underneath:

.. code-block:: python

    from openstef_core.testing import create_synthetic_forecasting_dataset

    # create_synthetic_forecasting_dataset returns a VersionedTimeSeriesDataset
    dataset = create_synthetic_forecasting_dataset()

    fit_result = model.fit(dataset.train)
    forecast = model.predict(dataset.forecast_input)

The ``fit`` call fits the preprocessing pipeline first, transforms the training data,
then fits the forecaster on the result. ``predict`` applies the already-fitted
preprocessing and returns a ``ForecastDataset`` containing point forecasts and
quantile intervals.

Using Presets
^^^^^^^^^^^^^

Assembling a ``ForecastingModel`` by hand is useful when you need fine-grained
control. For common scenarios, the ``presets`` module provides pre-wired
configurations that encode best-practice choices for each model type:

.. code-block:: python

    from openstef_core.testing import create_synthetic_forecasting_dataset
    from openstef_core.types import Q, LeadTime
    from openstef_models.presets import ForecastingWorkflowConfig, CustomForecastingWorkflow

    config = ForecastingWorkflowConfig(
        model_type="gblinear",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime(hours=h) for h in range(1, 25)],
    )

    dataset = create_synthetic_forecasting_dataset()
    workflow = CustomForecastingWorkflow(config=config)
    workflow.train(dataset)
    forecast = workflow.predict(dataset.forecast_input)

The preset wires together the correct transforms, hyperparameter defaults, and
postprocessing steps (such as ``ConfidenceIntervalApplicator`` and
``QuantileSorter``) so that the output is always a well-formed probabilistic
forecast.

The Explainability Layer
------------------------

Understanding *why* a model produces a particular forecast is as important as the
forecast itself. The ``explainability`` sub-package provides two complementary
interfaces, both implemented as mixins so they can be attached to any compatible
forecaster.

``ExplainableForecaster`` exposes global feature importance:

- ``feature_importances`` — a ``pd.DataFrame`` of importance scores, one row per
  feature.
- ``plot_feature_importances(quantile)`` — an interactive Plotly treemap where box
  area is proportional to importance. Larger boxes immediately draw attention to the
  features that matter most.

``ContributionsMixin`` exposes local, per-sample contributions:

- ``predict_contributions(data)`` — returns a ``TimeSeriesDataset`` where each
  column is the additive contribution of one feature to each individual prediction.
  This is the SHAP-style decomposition that lets you answer "why did the model
  predict a spike at 18:00 on this particular day?"

``GBLinearForecaster`` implements both mixins. The following snippet shows how to
access them after training:

.. code-block:: python

    from typing import cast
    from openstef_models.explainability import ExplainableForecaster, ContributionsMixin

    # Cast to the explainability interface — safe when using GBLinearForecaster
    explainable = cast(ExplainableForecaster, workflow.model.forecaster)

    # Global feature importance as a treemap
    fig = explainable.plot_feature_importances(quantile=Q(0.5))
    fig.show()

    # Per-sample feature contributions
    contributions_model = cast(ContributionsMixin, workflow.model.forecaster)
    contributions = contributions_model.predict_contributions(dataset.forecast_input)

.. note::

   ``plot_feature_importances`` returns a ``plotly.graph_objects.Figure``. No
   external visualisation library is needed — Plotly is a first-class dependency of
   ``openstef_models``.

Compositional Design
--------------------

The three layers are loosely coupled by design. The key relationships are:

- **Transforms know nothing about models.** A ``LagsAdder`` or ``HolidayFeatureAdder``
  operates purely on a ``TimeSeriesDataset`` and has no dependency on any forecaster.
  This makes transforms reusable across model types and easy to unit-test in
  isolation.

- **Models know nothing about explainability.** Explainability is added through
  mixins rather than inheritance, so a forecaster that does not support SHAP
  decomposition simply does not implement ``ContributionsMixin``. Calling code can
  check at runtime with ``isinstance`` rather than relying on a class hierarchy.

- **Presets span all three layers.** The ``presets`` module is the only place where
  all three layers are wired together into a concrete, opinionated configuration.
  This keeps the lower layers general and the higher-level convenience separate.

This architecture means you can, for example, add a new domain-specific transform
without touching any model code, or swap ``GBLinearForecaster`` for
``XGBoostForecaster`` without changing the preprocessing pipeline.

.. note::

   For ensemble models that combine multiple ``ForecastingModel`` instances — each
   potentially with its own preprocessing pipeline — see :doc:`meta`. The ensemble
   layer follows the same compositional pattern, fitting a shared preprocessing step
   first and then per-forecaster steps on the common output.

Related Pages
-------------

- :doc:`core` — ``TimeSeriesDataset``, ``ForecastDataset``, and the base interfaces
  that ``openstef_models`` builds on.
- :doc:`meta` — ensemble models and advanced architectures that compose multiple
  ``ForecastingModel`` instances.
- :doc:`beam` — backtesting and evaluation tools for measuring forecast quality.