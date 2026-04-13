The ``openstef_models`` Package
================================

This page covers the ``openstef_models`` package in depth: how its transform subpackages
are organised by domain, how forecasting models are implemented on top of the core
interfaces, and how the explainability layer exposes feature importance and per-sample
contributions. For the foundational data types (``TimeSeriesDataset``, base classes)
that everything here builds on, see the :doc:`core` sibling page.

.. note:: [DIAGRAM: Component-level diagram showing three horizontal layers stacked vertically. Bottom layer: ``openstef_core`` (TimeSeriesDataset, Transform, Forecaster interfaces, BaseConfig). Middle layer: ``openstef_models.transforms`` split into five domain columns — validation, general, time_domain, weather_domain, energy_domain — each feeding upward through a TransformPipeline. Top layer: ``openstef_models.models`` (XGBoostForecaster, GBLinearForecaster, MedianForecaster, …) consuming the preprocessed dataset, with ``openstef_models.explainability`` (ExplainableForecaster mixin, ContributionsMixin, FeatureImportancePlotter) attached to the models layer as a side-car. Arrows show data flowing upward through transforms into models, and sideways from models into the explainability tools.]

---

The Transforms Layer
--------------------

Feature engineering in ``openstef_models`` is built around a single abstract base class
defined in ``openstef_core``: ``TimeSeriesTransform``. Every transform follows the
familiar scikit-learn ``fit`` / ``transform`` pattern, operating on
``TimeSeriesDataset`` objects rather than raw NumPy arrays. This keeps the data
contract explicit and type-safe throughout the pipeline.

The top-level ``openstef_models.transforms`` package exposes five domain-specific
subpackages:

.. code-block:: python

    from openstef_models.transforms import (
        energy_domain,
        general,
        time_domain,
        validation,
        weather_domain,
    )

Each subpackage groups transforms by the kind of knowledge they encode, making it easy
to reason about what a pipeline does and to swap individual stages without touching
unrelated logic.

**validation**
  Sanity checks and data-quality guards that should run first — detecting missing
  values, out-of-range readings, and structural inconsistencies before any feature
  engineering takes place.

**general**
  Stateless or lightly stateful utilities that apply across domains. The ``Clipper``
  transform is a representative example: it learns the observed min/max of each
  feature during ``fit`` and clips values to that range during ``transform``, preventing
  extrapolation artefacts from corrupting downstream models.

**time_domain**
  Temporal feature extraction — lag features, rolling statistics, calendar encodings
  (hour-of-day, day-of-week, public holidays), and similar constructs that give models
  access to the periodicity inherent in energy time series.

**weather_domain**
  Transforms that process meteorological inputs such as temperature, irradiance, and
  wind speed into model-ready features, including normalisation and derived quantities
  specific to weather forecasting.

**energy_domain**
  Physics-informed transforms for energy-specific signals. ``WindPowerFeatureAdder``
  is a concrete example: it takes raw wind-speed columns and computes wind-power
  estimates using the standard power-curve relationship, adding them as new features
  to the dataset.

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.general import Clipper

    # Each transform is a Pydantic BaseConfig — configuration is validated at
    # construction time, not at runtime.
    wind_features = WindPowerFeatureAdder(wind_speed_column="wind_speed_100m")
    clipper = Clipper(features=["load", "wind_power"])

    # Stateful fit: learns parameters from training data
    wind_features.fit(train_dataset)
    enriched = wind_features.transform(train_dataset)

    clipper.fit(enriched)
    clipped = clipper.transform(enriched)

Composing Transforms with ``TransformPipeline``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual transforms become useful at scale through ``TransformPipeline``, provided
by ``openstef_core``. A pipeline fits and applies its transforms sequentially, passing
the output of each stage as the input to the next. Because ``is_fitted`` is defined
on the pipeline as a whole (``True`` only when every member transform is fitted), it
integrates cleanly with serialisation and model-storage workflows.

.. code-block:: python

    from openstef_core.mixins import TransformPipeline
    from openstef_models.transforms.validation import OutlierValidator
    from openstef_models.transforms.time_domain import LagFeatureAdder, HolidayFeatureAdder
    from openstef_models.transforms.general import Clipper

    preprocessing = TransformPipeline(
        transforms=[
            OutlierValidator(),
            HolidayFeatureAdder(country="NL"),
            LagFeatureAdder(lags=[1, 2, 3, 24, 48]),
            Clipper(),
        ]
    )

    # Fit once on training data; the fitted state is preserved for inference
    preprocessing.fit(train_dataset)
    train_ready = preprocessing.transform(train_dataset)
    inference_ready = preprocessing.transform(live_dataset)

The pipeline is serialisable via the standard model-storage mechanism, so the fitted
transform state travels with the model artefact — no separate preprocessing artefact
management is needed.

---

The Models Layer
----------------

``openstef_models.models`` contains the forecasting implementations. All forecasters
extend the abstract ``Forecaster`` base class from ``openstef_core``, which mandates
``fit`` and ``predict`` methods operating on ``ForecastInputDataset`` and returning a
``ForecastDataset``. This shared interface means that any forecaster can be dropped
into a ``ForecastingModel`` pipeline without changes to surrounding code.

The library ships several production-ready implementations:

- **XGBoostForecaster** — gradient-boosted trees with multi-quantile output, configurable
  loss functions, and SHAP-based explainability.
- **GBLinearForecaster** — a linear booster variant suited to smoother load profiles.
- **MedianForecaster** — a lag-based constant forecaster useful as a baseline and for
  diagnosing data issues.

Each forecaster exposes its hyperparameters through a companion ``HyperParams`` class
(itself a ``BaseConfig`` / Pydantic model), so configuration is validated before
training begins and can be serialised to JSON for experiment tracking.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    hparams = XGBoostHyperParams(
        max_depth=6,
        learning_rate=0.05,
        n_estimators=400,
        quantiles=[0.1, 0.5, 0.9],
    )

    forecaster = XGBoostForecaster(hparams=hparams)
    forecaster.fit(train_input_dataset, data_val=val_input_dataset)
    forecast = forecaster.predict(live_input_dataset)

The ``ForecastingModel`` Wrapper
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In practice you rarely instantiate a bare forecaster. ``ForecastingModel`` is the
higher-level container that wires together a preprocessing ``TransformPipeline``, one
or more forecasters, and an optional postprocessing pipeline into a single, coherent
object. During ``fit``, the model first fits and applies the shared preprocessing
pipeline, then fits each forecaster on the transformed data. During ``predict``, the
same preprocessing is applied to live data before it reaches the forecasters.

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_core.mixins import TransformPipeline
    from openstef_models.transforms.time_domain import LagFeatureAdder, HolidayFeatureAdder
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    model = ForecastingModel(
        preprocessing=TransformPipeline(
            transforms=[
                HolidayFeatureAdder(country="NL"),
                LagFeatureAdder(lags=[1, 2, 3, 24, 48]),
            ]
        ),
        forecasters={
            "xgb": XGBoostForecaster(
                hparams=XGBoostHyperParams(quantiles=[0.1, 0.5, 0.9])
            )
        },
    )

    model.fit(train_versioned_dataset)
    forecast_dataset = model.predict(live_versioned_dataset)

This compositional design is intentional: the transforms layer and the models layer
are independently testable and replaceable. You can swap the preprocessing pipeline
without touching the forecaster, or benchmark multiple forecasters against the same
preprocessing by adding them to the ``forecasters`` dictionary.

Presets
^^^^^^^

For common configurations, ``openstef_models.presets`` provides factory functions
that construct fully wired ``ForecastingModel`` instances with sensible defaults for
XGBoost, GBLinear, and baseline workflows. Presets are the fastest path to a working
forecast and serve as a reference for building custom configurations.

.. code-block:: python

    from openstef_models.presets import get_xgboost_forecasting_model

    # Returns a ready-to-fit ForecastingModel with standard preprocessing
    model = get_xgboost_forecasting_model(country="NL", quantiles=[0.1, 0.5, 0.9])
    model.fit(train_versioned_dataset)

---

The Explainability Layer
------------------------

Understanding *why* a model produces a particular forecast is as important as the
forecast itself, especially in regulated energy markets. ``openstef_models.explainability``
provides this capability through two mixins that forecasters can adopt:

**ExplainableForecaster**
  Adds a ``feature_importances`` property returning a ``pd.DataFrame`` indexed by
  feature name with quantile columns. This gives an aggregate view of which features
  the model relies on most across its quantile estimators.

**ContributionsMixin**
  Adds ``predict_contributions``, which returns a ``TimeSeriesDataset`` where each
  column is a feature and each row is a timestep, with values representing that
  feature's contribution to the prediction at that point. For ``XGBoostForecaster``
  this is backed by SHAP values computed directly from the XGBoost booster.

``XGBoostForecaster`` implements both mixins, making it the primary choice when
interpretability is a requirement.

.. code-block:: python

    # After fitting, inspect aggregate feature importances
    importances = forecaster.feature_importances  # pd.DataFrame
    print(importances.sort_values("0.5", ascending=False).head(10))

    # Per-sample contributions for a specific forecast window
    contributions = forecaster.predict_contributions(live_input_dataset)
    # contributions is a TimeSeriesDataset — one column per feature

Visualising Feature Importance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``openstef_models`` ships its own interactive visualisation tooling so you do not need
to reach for external plotting libraries. ``FeatureImportancePlotter`` generates an
interactive Plotly treemap from a feature-importance DataFrame, and
``ExplainableForecaster`` exposes this directly through ``plot_feature_importances``:

.. code-block:: python

    from openstef_core.types import Q

    # Returns a plotly.graph_objects.Figure — display in a notebook or export to HTML
    fig = forecaster.plot_feature_importances(quantile=Q(0.5))
    fig.show()

    # Or use the plotter directly with a custom DataFrame
    from openstef_models.explainability.plotters import FeatureImportancePlotter

    plotter = FeatureImportancePlotter()
    fig = plotter.plot(scores=importances, quantile=Q(0.5))

The treemap groups features hierarchically, making it straightforward to see whether
the model is leaning on lag features, weather inputs, or calendar signals — a practical
first step when diagnosing unexpected forecast behaviour.

.. note::

   ``ContributionsMixin.predict_contributions`` returns a ``TimeSeriesDataset``, not
   a raw DataFrame. This keeps the result consistent with the rest of the data model
   and allows it to be passed directly into downstream analysis tools in
   ``openstef_beam``. See the :doc:`beam` page for how contributions feed into
   backtesting and regression analysis.

---

Design Principles
-----------------

Several patterns run consistently through ``openstef_models``:

- **Configuration as data.** Every configurable object — transforms, hyperparameters,
  pipelines — is a Pydantic ``BaseConfig``. This means configuration is validated at
  construction time, serialisable to JSON, and self-documenting through type annotations.

- **Separation of concerns.** Transforms know nothing about models; models know nothing
  about storage or evaluation. Each layer has a single responsibility and communicates
  through the ``TimeSeriesDataset`` / ``ForecastDataset`` contract defined in
  ``openstef_core``.

- **Composability over inheritance.** Explainability is added to forecasters via mixins
  rather than a deep class hierarchy. A forecaster that does not support SHAP simply
  does not implement ``ContributionsMixin``, and calling code can check with
  ``isinstance`` before attempting to use it.

- **Domain knowledge as first-class code.** Physics-informed transforms like
  ``WindPowerFeatureAdder`` live alongside generic utilities. Energy-domain expertise
  is encoded in the library itself, not left to each user to re-implement.

---

Related Pages
-------------

- :doc:`core` — ``TimeSeriesDataset``, ``Transform``, and the base interfaces that
  ``openstef_models`` builds on.
- :doc:`beam` — backtesting, metrics, and regression testing that consume the
  forecasts and contributions produced by the models described here.