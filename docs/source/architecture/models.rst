The Models Package
==================

The ``openstef-models`` package is the forecasting engine of OpenSTEF. It provides
everything needed to go from raw time series data to a trained, explainable probabilistic
forecast: domain-aware feature engineering transforms, gradient-boosting forecasting
models, and built-in explainability tools. This page covers the internal design of each
layer and how they compose together.

For the foundational data types and interfaces that ``openstef-models`` builds on —
``TimeSeriesDataset``, ``ForecastInputDataset``, and the ``TimeSeriesTransform`` base
class — see the :doc:`core` page. For backtesting and evaluation tooling, see
:doc:`beam`.

.. mermaid:: diagrams/architecture/models_diagram_1.mmd

Package Structure
-----------------

The package is organised into three cooperating sub-packages::

    openstef_models/
    ├── transforms/          # Feature engineering, domain-grouped
    │   ├── time_domain/
    │   ├── weather_domain/
    │   ├── energy_domain/
    │   ├── general/
    │   └── validation/
    ├── models/
    │   └── forecasting/     # Concrete forecaster implementations
    └── explainability/
        ├── mixins.py        # ExplainableForecaster, ContributionsMixin
        └── plotters/        # Built-in interactive visualisations

Each sub-package is independently importable, so you can use the transforms without
instantiating a full forecaster, or attach the explainability mixins to a custom model
you bring yourself.

The Transforms Layer
--------------------

Feature engineering in OpenSTEF is expressed as a collection of stateful
``TimeSeriesTransform`` objects — each one a small, composable unit that follows the
familiar scikit-learn ``fit`` / ``transform`` pattern but operates on
``TimeSeriesDataset`` instances rather than bare NumPy arrays.

Transforms are grouped by domain, which makes it easy to pick exactly the features
relevant to a given forecasting problem:

- **``time_domain``** — calendar and lag features: hour-of-day, day-of-week, public
  holidays, rolling statistics.
- **``weather_domain``** — meteorological derived features such as apparent temperature,
  humidity corrections, and irradiance decomposition.
- **``energy_domain``** — physics-informed features for the power system, including wind
  power conversion (``WindPowerFeatureAdder``).
- **``general``** — domain-agnostic utilities such as ``Clipper``, which constrains
  feature values to the range observed during training to prevent out-of-distribution
  extrapolation.
- **``validation``** — transforms that enforce data quality constraints before features
  are passed to a model.

Composing a Pipeline
^^^^^^^^^^^^^^^^^^^^

Individual transforms are assembled into a ``TransformPipeline``, which applies them
sequentially and propagates the fitted state through the chain:

.. code-block:: python

    from openstef_models.transforms import time_domain, energy_domain, general
    from openstef_core.transforms.pipeline import TransformPipeline

    pipeline = TransformPipeline(
        transforms=[
            time_domain.CalendarFeatureAdder(),
            time_domain.LagFeatureAdder(lags=[1, 2, 3, 24, 48]),
            energy_domain.WindPowerFeatureAdder(),
            general.Clipper(),
        ]
    )

    # Fit on training data — each transform learns its parameters in turn
    pipeline.fit(train_dataset)

    # Apply the same learned parameters to new data
    features = pipeline.transform(forecast_dataset)

The pipeline's ``fit`` method calls ``fit_transform`` on each transform in order,
threading the output of one step directly into the input of the next. This means later
transforms (such as ``Clipper``) see the features produced by earlier ones and can
learn their clipping bounds from the fully-engineered training set.

Writing a Custom Transform
^^^^^^^^^^^^^^^^^^^^^^^^^^

Because every transform shares the ``TimeSeriesTransform`` interface from
``openstef-core``, you can drop a custom transform anywhere in the pipeline without
touching the surrounding code:

.. code-block:: python

    from openstef_core.transforms import TimeSeriesTransform
    from openstef_core.datasets import TimeSeriesDataset


    class NormalisedLoad(TimeSeriesTransform):
        """Divide load by installed capacity, learned from training data."""

        def fit(self, data: TimeSeriesDataset) -> None:
            self._capacity = data.features["load"].max()

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            data.features["load_norm"] = data.features["load"] / self._capacity
            return data

        @property
        def is_fitted(self) -> bool:
            return hasattr(self, "_capacity")

The ``features_added`` convention used by built-in transforms (e.g.
``WindPowerFeatureAdder.features_added()``) is a useful pattern to adopt in custom
transforms: it lets downstream code introspect which columns a transform will produce
without running it.

The Models Layer
----------------

Concrete forecasters live in ``openstef_models.models.forecasting``. The current
library ships two production-ready implementations:

- **``LGBMForecaster``** — multi-quantile gradient boosting using LightGBM tree
  learners. The default choice for most energy forecasting tasks.
- **``LGBMLinearForecaster``** — LightGBM with linear tree leaves, useful when the
  target relationship is closer to linear and interpretability of individual splits
  matters.

Both forecasters are configured through a paired ``HyperParams`` dataclass
(``LGBMHyperParams``, ``LGBMLinearHyperParams``). This keeps model construction
explicit and serialisable:

.. code-block:: python

    from openstef_models.models.forecasting.lgbm_forecaster import (
        LGBMForecaster,
        LGBMHyperParams,
    )

    hparams = LGBMHyperParams(
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=63,
    )

    # HyperParams knows how to instantiate its paired forecaster
    forecaster: LGBMForecaster = hparams.forecaster_class()

    forecaster.fit(train_data, data_val=val_data)
    forecast = forecaster.predict(forecast_input)

The ``predict`` method returns a ``ForecastDataset`` containing one column per
quantile, giving probabilistic forecasts out of the box without any additional
post-processing.

.. note::

   ``ForecastInputDataset`` and ``ForecastDataset`` are defined in ``openstef-core``
   and carry the metadata (resolution, horizon, location) that the forecaster needs
   alongside the feature matrix. See :doc:`core` for their full specification.

Compositional Design
^^^^^^^^^^^^^^^^^^^^

Forecasters do not embed feature engineering internally. The expected pattern is to
run a ``TransformPipeline`` first, then pass the enriched ``ForecastInputDataset`` to
the forecaster. This separation keeps each layer independently testable and lets you
swap out the transform pipeline without retraining the model, or vice versa.

.. code-block:: python

    # 1. Build and fit the feature pipeline on training data
    pipeline = TransformPipeline(
        transforms=[
            time_domain.CalendarFeatureAdder(),
            time_domain.LagFeatureAdder(lags=[1, 2, 3, 24, 48]),
            general.Clipper(),
        ]
    )
    pipeline.fit(train_dataset)
    enriched_train = pipeline.transform(train_dataset)

    # 2. Train the forecaster on the enriched data
    forecaster = LGBMHyperParams().forecaster_class()
    forecaster.fit(enriched_train)

    # 3. At inference time, apply the same fitted pipeline first
    enriched_input = pipeline.transform(live_input_dataset)
    forecast = forecaster.predict(enriched_input)

The Explainability Layer
------------------------

Explainability in OpenSTEF is delivered through two mixins defined in
``openstef_models.explainability.mixins``:

- **``ExplainableForecaster``** — exposes a ``feature_importances`` property that
  returns a ``pd.DataFrame`` indexed by feature name, with one column per quantile.
  Also provides ``plot_feature_importances()``, which returns an interactive Plotly
  treemap without requiring any additional imports.
- **``ContributionsMixin``** — adds ``predict_contributions()``, which computes
  per-sample SHAP values and returns them as a ``TimeSeriesDataset``. This lets you
  see not just which features matter globally, but how much each feature contributed
  to each individual forecast point.

Both ``LGBMForecaster`` and ``LGBMLinearForecaster`` implement both mixins, so
explainability is available on every built-in model with no extra setup:

.. code-block:: python

    # Feature importances as a DataFrame
    importances = forecaster.feature_importances
    print(importances.head())
    #                         Q0.1   Q0.5   Q0.9
    # lag_1                  0.312  0.298  0.287
    # hour_of_day            0.201  0.215  0.198
    # wind_power             0.143  0.151  0.162
    # ...

    # Interactive treemap — returns a plotly Figure, display in a notebook or save
    fig = forecaster.plot_feature_importances(quantile=Q(0.5))
    fig.show()

    # Per-sample SHAP contributions
    contributions: TimeSeriesDataset = forecaster.predict_contributions(enriched_input)

The ``FeatureImportancePlotter`` that backs ``plot_feature_importances`` is also
accessible directly from ``openstef_models.explainability.plotters`` if you want to
render importance scores that were computed separately or stored from a previous run:

.. code-block:: python

    from openstef_models.explainability.plotters.feature_importance_plotter import (
        FeatureImportancePlotter,
    )
    from openstef_core.types import Q

    plotter = FeatureImportancePlotter()
    fig = plotter.plot(scores=importances, quantile=Q(0.5))

Adding Explainability to a Custom Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because explainability is delivered as mixins rather than baked into a base class, you
can add it to any forecaster that computes compatible importance scores:

.. code-block:: python

    import pandas as pd
    from openstef_models.explainability.mixins import ExplainableForecaster
    from openstef_core.types import Q, Quantile


    class MyForecaster(ExplainableForecaster):
        @property
        def feature_importances(self) -> pd.DataFrame:
            # Return a DataFrame indexed by feature name, columns = quantiles
            return pd.DataFrame(
                self._importance_scores,
                columns=[Q(0.1), Q(0.5), Q(0.9)],
            )

The mixin's ``plot_feature_importances`` method will then work automatically using
your ``feature_importances`` implementation.

.. warning::

   ``ContributionsMixin`` requires that the underlying model supports SHAP value
   computation. For tree-based models this is handled automatically via the
   ``shap.TreeExplainer`` integration inside the built-in forecasters. Custom models
   must implement ``predict_contributions`` themselves.

Design Principles
-----------------

Three design decisions shape the whole package and are worth keeping in mind when
extending it:

1. **Separation of feature engineering and modelling.** Transforms and forecasters are
   independent objects. Neither knows about the other's internals, and they communicate
   only through the ``TimeSeriesDataset`` / ``ForecastInputDataset`` contract defined
   in ``openstef-core``.

2. **Explainability as a first-class concern.** Rather than being an optional add-on,
   feature importance and SHAP contributions are part of the standard forecaster
   interface. Every built-in model implements both mixins.

3. **Configuration as data.** ``HyperParams`` dataclasses carry both the model
   configuration and the knowledge of which forecaster class to instantiate. This makes
   serialisation, hyperparameter search, and experiment tracking straightforward.