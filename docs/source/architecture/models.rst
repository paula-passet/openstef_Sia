The ``openstef_models`` Package
================================

This page covers the ``openstef_models`` package in depth — the part of OpenSTEF responsible
for feature engineering, forecasting model implementations, and model explainability. If you
are looking for the foundational data types and interfaces that this package builds on, see the
:doc:`core` page. For backtesting and evaluation tooling, see the :doc:`beam` page.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

The three layers are deliberately decoupled. Transforms know nothing about models; models
compose transforms through a standard pipeline interface; and explainability is added to
forecasters through mixins rather than inheritance hierarchies. This compositional design
makes it straightforward to swap out individual pieces — a different feature engineering
step, a new base learner, or a custom explainability back-end — without touching the rest
of the stack.

Transforms: Domain-Specific Feature Engineering
-------------------------------------------------

The ``openstef_models.transforms`` package organises feature engineering into five
sub-packages, each targeting a distinct domain:

- ``validation`` — data quality checks and anomaly flagging before features are computed
- ``general`` — domain-agnostic transforms such as ``Clipper`` (clips values to observed min/max ranges)
- ``time_domain`` — temporal features: lag features, rolling statistics, calendar encodings
- ``weather_domain`` — meteorological features derived from raw weather inputs
- ``energy_domain`` — power-system-specific features, including wind power estimation

Every transform in the library implements the ``TimeSeriesTransform`` interface from
``openstef_core``. The interface is intentionally minimal:

.. code-block:: python

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms import time_domain

    # Each transform exposes fit(), transform(), and features_added()
    lag_transform = time_domain.LagFeatureAdder(lags=[1, 2, 24, 48])

    lag_transform.fit(train_data)          # learns any stateful parameters
    enriched = lag_transform.transform(train_data)

    print(lag_transform.features_added())  # ['lag_1', 'lag_2', 'lag_24', 'lag_48']

Stateless transforms (those that derive features purely from the current row, with no
learned parameters) override ``is_fitted`` to return ``True`` immediately, so calling
``fit`` on them is a no-op. Stateful transforms — such as ``Clipper``, which records
observed value ranges — must be fitted on training data before they can transform
unseen data.

The ``WindPowerFeatureAdder`` in ``energy_domain`` is a good example of a domain-specific
stateless transform. It converts raw wind speed columns into estimated wind power output
using a physical power-curve model, requiring no training data:

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    wind_features = WindPowerFeatureAdder()
    dataset_with_wind = wind_features.transform(raw_dataset)
    # Adds columns such as 'wind_power_relative' derived from wind speed inputs

Composing Transforms into Pipelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual transforms become useful at scale when composed into a ``TransformPipeline``.
The pipeline applies transforms in order, feeding the output of each step as the input to
the next. Fitting the pipeline fits each stateful transform sequentially on the
intermediate outputs, so downstream transforms always see already-processed data:

.. code-block:: python

    from openstef_core.pipelines import TransformPipeline
    from openstef_models.transforms.validation import OutlierClipper
    from openstef_models.transforms.time_domain import LagFeatureAdder, CalendarFeatureAdder
    from openstef_models.transforms.weather_domain import WeatherFeatureAdder

    pipeline = TransformPipeline(transforms=[
        OutlierClipper(),
        CalendarFeatureAdder(),
        LagFeatureAdder(lags=[1, 2, 24, 48]),
        WeatherFeatureAdder(),
    ])

    pipeline.fit(train_dataset)
    train_features = pipeline.transform(train_dataset)
    test_features  = pipeline.transform(test_dataset)

The pipeline is itself serialisable (it supports pickling), which means a fitted pipeline
can be saved alongside a trained model and reloaded for inference without any extra
bookkeeping.

.. note::

   ``TransformPipeline`` is generic over the dataset type (``TransformPipeline[TimeSeriesDataset]``).
   The component-splitting models in ``openstef_models`` use a second pipeline typed over
   ``EnergyComponentDataset`` for post-processing, demonstrating that the same abstraction
   works across different dataset shapes.

Models: Forecasting Implementations
-------------------------------------

The ``openstef_models.models`` sub-package contains two levels of abstraction: low-level
*forecasters* that wrap a single ML algorithm, and high-level *forecasting models* that
orchestrate the full prediction pipeline.

Base Forecasters
^^^^^^^^^^^^^^^^^

Concrete forecasters — ``XGBoostForecaster``, ``LGBMForecaster``, and
``LGBMLinearForecaster`` — each wrap a gradient-boosting back-end and produce
probabilistic (multi-quantile) forecasts. They share a common interface defined by
``BaseForecastingModel``:

- ``quantiles`` — the quantile levels the model produces (e.g. ``[0.05, 0.5, 0.95]``)
- ``max_horizon`` — the furthest lead time the model supports
- ``hyperparams`` — a typed ``HyperParams`` object rather than a raw dictionary
- ``fit(data, data_val)`` / ``predict(data)`` — standard fit/predict contract

Because each forecaster is a Pydantic ``BaseModel``, hyperparameters are validated at
construction time and the entire model state can be serialised to JSON for experiment
tracking.

The ``ForecastingModel`` Orchestrator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ForecastingModel`` is the high-level class most application code interacts with. It
owns a ``TransformPipeline`` for preprocessing, a base forecaster, and optionally a
postprocessing pipeline. Calling ``fit`` runs the full sequence — preprocessing, training,
postprocessing fit — and returns a ``ModelFitResult`` that bundles training metrics,
validation metrics, and per-split results:

.. code-block:: python

    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
    from openstef_core.pipelines import TransformPipeline
    from openstef_models.transforms.time_domain import LagFeatureAdder, CalendarFeatureAdder

    forecaster = LGBMForecaster(quantiles=[0.1, 0.5, 0.9])

    model = ForecastingModel(
        preprocessing=TransformPipeline(transforms=[
            CalendarFeatureAdder(),
            LagFeatureAdder(lags=[1, 2, 24, 48]),
        ]),
        forecaster=forecaster,
    )

    fit_result = model.fit(train_dataset, data_val=val_dataset)

    # Inspect training metrics across quantiles
    print(fit_result.metrics_to_flat_dict())

    # Generate probabilistic forecasts
    forecast: ForecastDataset = model.predict(test_dataset)

The separation between ``ForecastingModel`` and the underlying forecaster is intentional:
you can swap ``LGBMForecaster`` for ``XGBoostForecaster`` without changing the pipeline
configuration, or reuse the same forecaster inside different pipeline configurations for
different grid locations.

Explainability
---------------

The ``openstef_models.explainability`` package provides two complementary views of model
behaviour: aggregate feature importance across the training set, and per-sample feature
contributions for individual predictions.

ExplainableForecaster and Feature Importance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forecasters that implement the ``ExplainableForecaster`` mixin expose a
``feature_importances`` property returning a ``pd.DataFrame`` indexed by feature name,
with one column per quantile. The values are normalised importance scores (summing to 1.0
across features for each quantile).

The mixin also provides ``plot_feature_importances``, which delegates to
``FeatureImportancePlotter`` and returns an interactive Plotly treemap — no external
visualisation library required:

.. code-block:: python

    from openstef_models.explainability import ExplainableForecaster

    # Assuming `model.forecaster` implements ExplainableForecaster
    explainable = model.forecaster

    # Tabular importance scores
    importance_df = explainable.feature_importances
    print(importance_df.head())

    # Interactive treemap (returns a plotly Figure)
    fig = explainable.plot_feature_importances(quantile=0.5)
    fig.show()

Per-Sample Contributions with ContributionsMixin
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``ContributionsMixin`` goes further than aggregate importance by decomposing each
individual prediction into additive feature contributions. For tree-based models this
corresponds to SHAP TreeExplainer values; for linear GBM models it is the
coefficient-times-feature-value decomposition; for ensembles it shows each base model's
contribution weight.

The result is a ``TimeSeriesDataset`` whose columns are feature names and whose rows
align with the input time index — making it straightforward to plot how a specific
feature drove a forecast spike at a particular timestamp:

.. code-block:: python

    from openstef_models.explainability import ContributionsMixin

    # predict_contributions is available on the high-level ForecastingModel
    # when the underlying forecaster implements ContributionsMixin
    contributions: TimeSeriesDataset = model.predict_contributions(
        data=test_dataset,
        forecast_start=forecast_start,
    )

    # contributions.data is a DataFrame: rows = timestamps, columns = features
    top_contributors = contributions.data.abs().mean().nlargest(5)
    print("Most influential features on average:", top_contributors)

.. note::

   ``predict_contributions`` raises ``NotImplementedError`` if the underlying forecaster
   does not implement ``ContributionsMixin``. Check ``model.get_explainable_components()``
   to discover which components of an ensemble support contributions.

Compositional Design in Practice
----------------------------------

The three layers — transforms, models, and explainability — are connected through
composition rather than deep inheritance. A ``ForecastingModel`` *has* a
``TransformPipeline``; a forecaster *implements* ``ExplainableForecaster`` as a mixin;
``FeatureImportancePlotter`` is injected into the mixin rather than subclassed.

This means you can build custom forecasting pipelines by assembling these pieces without
subclassing any of the high-level classes:

.. code-block:: python

    from openstef_core.pipelines import TransformPipeline
    from openstef_models.models.forecasting_model import ForecastingModel
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.general import Clipper
    from openstef_models.transforms.time_domain import LagFeatureAdder

    wind_model = ForecastingModel(
        preprocessing=TransformPipeline(transforms=[
            WindPowerFeatureAdder(),       # energy-domain feature
            LagFeatureAdder(lags=[1, 24]), # temporal context
            Clipper(),                     # guard against out-of-range values
        ]),
        forecaster=XGBoostForecaster(quantiles=[0.1, 0.5, 0.9]),
    )

    fit_result = wind_model.fit(train_data, data_val=val_data)
    forecast   = wind_model.predict(future_data)

    # Explainability comes for free because XGBoostForecaster implements both mixins
    fig = wind_model.forecaster.plot_feature_importances()

The ``ModelFitResult`` returned by ``fit`` carries per-component metrics via
``component_fit_results()``, which is particularly useful when working with ensemble
models where you want to inspect each base learner independently.

.. note::

   For presets that bundle a recommended transform pipeline and forecaster for common
   energy forecasting scenarios, see the ``openstef_models.presets`` module. Presets are
   the fastest way to get a working model without hand-assembling the pipeline.

Related Pages
--------------

- :doc:`core` — ``TimeSeriesDataset``, ``TransformPipeline``, and the base interfaces
  that ``openstef_models`` builds on
- :doc:`beam` — backtesting, metrics, and statistical significance testing for evaluating
  the models described on this page