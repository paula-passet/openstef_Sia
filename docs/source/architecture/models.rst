The Models Package
==================

The ``openstef-models`` package is the forecasting engine of OpenSTEF. It provides
everything needed to build, train, and explain energy forecasting models: a library
of domain-aware feature transforms, a set of ready-to-use forecasting model
implementations, and explainability tools that expose what a trained model has
learned. This page covers the architecture of that package and the patterns that
connect its three main layers.

.. note:: [DIAGRAM: Component-level diagram showing three horizontal layers — transforms (time_domain, energy_domain, weather_domain, general, validation), models (Forecaster base → XGBoostForecaster, LGBMForecaster, LGBMLinearForecaster, GBLinearForecaster, MedianForecaster, FlatlinerForecaster), and explainability (ExplainableForecaster mixin, ContributionsMixin, FeatureImportancePlotter) — with arrows showing how models consume transforms and expose explainability interfaces. A TransformPipeline sits between the transforms and models layers.]

For the ``TimeSeriesDataset`` and ``ForecastInputDataset`` types that flow through
this package, see the :doc:`core` page. For backtesting and evaluation of trained
models, see the :doc:`beam` page.

----

The Transforms Layer
--------------------

Feature engineering in OpenSTEF is expressed as *composable, stateful transforms*.
Every transform implements the ``TimeSeriesTransform`` interface from
``openstef-core``, which follows the familiar scikit-learn ``fit`` / ``transform``
pattern but operates on ``TimeSeriesDataset`` objects rather than raw arrays.

.. code-block:: python

    from openstef_core.transforms.dataset_transforms import TimeSeriesTransform
    from openstef_core.datasets import TimeSeriesDataset

    class MyTransform(TimeSeriesTransform):
        def fit(self, data: TimeSeriesDataset) -> None:
            # learn parameters from training data
            ...

        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            # apply learned parameters
            ...

Transforms are grouped into five subpackages, each targeting a distinct domain of
knowledge:

- **``time_domain``** — extracts temporal structure from the datetime index.
  ``DatetimeFeaturesAdder`` adds hour-of-day, day-of-week, and month columns.
  ``CyclicFeaturesAdder`` encodes those as sine/cosine pairs so the model sees
  periodicity directly. ``HolidayFeatureAdder`` marks public holidays.
  ``RollingAggregatesAdder`` and ``LagsAdder`` capture autocorrelation.

- **``energy_domain``** — encodes physical knowledge about energy systems.
  ``WindPowerFeatureAdder`` converts wind speed measurements into estimated wind
  power using a turbine power curve, adding features that a generic ML model
  would otherwise have to infer from scratch.

- **``weather_domain``** — weather-specific preprocessing, such as normalising
  irradiance values or deriving apparent temperature from humidity and wind.

- **``general``** — dataset-agnostic utilities: ``Imputer`` fills missing values,
  ``NaNDropper`` removes rows that cannot be recovered, ``Clipper`` constrains
  features to their observed training range, ``Scaler`` standardises numeric
  columns, ``Selector`` keeps only the features a model was trained on, and
  ``EmptyFeatureRemover`` prunes zero-variance columns before training.

- **``validation``** — guards against data quality problems before a transform
  pipeline runs.

Transforms are assembled into a ``TransformPipeline``, which runs each step
sequentially, passing the output of one transform as the input to the next:

.. code-block:: python

    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        HolidayFeatureAdder,
        LagsAdder,
    )
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
    from openstef_core.transforms.pipeline import TransformPipeline

    pipeline = TransformPipeline(
        transforms=[
            DatetimeFeaturesAdder(),
            CyclicFeaturesAdder(),
            HolidayFeatureAdder(country="NL"),
            LagsAdder(lags=[1, 2, 48]),          # 15-min resolution: 1, 2, 12h lags
            WindPowerFeatureAdder(),
            Imputer(),
            NaNDropper(),
            Scaler(),
        ]
    )

    pipeline.fit(train_dataset)
    prepared = pipeline.transform(inference_dataset)

The pipeline's ``fit`` method walks the list in order, calling ``fit_transform``
on each step so that later transforms see already-processed data. At inference
time, ``transform`` replays the fitted steps without re-learning anything.

.. note::

   ``Clipper`` is particularly important for production deployments. It prevents
   out-of-distribution feature values — a sensor spike, for instance — from
   silently extrapolating a model far outside its training distribution.

----

The Models Layer
----------------

The ``openstef_models.models`` subpackage provides concrete forecasting model
implementations. All of them inherit from ``Forecaster``, a base class that
defines a consistent ``fit`` / ``predict`` interface and wires together the
transform pipeline with the underlying ML algorithm.

OpenSTEF ships the following forecasters out of the box:

- **``XGBoostForecaster``** — gradient-boosted trees via XGBoost, the default
  choice for most grid-connected load and generation forecasting tasks.
- **``LGBMForecaster``** — LightGBM equivalent; typically faster to train on
  large datasets and more memory-efficient.
- **``LGBMLinearForecaster``** — combines LightGBM leaf embeddings with a linear
  head, useful when interpretability of the final layer matters.
- **``GBLinearForecaster``** — gradient-boosted linear model for datasets where
  tree splits are not appropriate.
- **``MedianForecaster``** — a simple historical-median baseline. Use it to
  establish a lower bound on forecast quality before investing in more complex
  models.
- **``FlatlinerForecaster``** — detects and handles "flatliner" assets whose
  output is near-constant, preventing gradient boosting models from overfitting
  to noise.

All tree-based forecasters support **multi-quantile regression** natively. Rather
than predicting a single point estimate, they produce a full predictive
distribution across configurable quantiles (e.g. P10, P50, P90), which is
essential for uncertainty-aware grid planning.

Hyperparameters are expressed as typed Pydantic models (e.g.
``LGBMHyperParams``, ``XGBoostHyperParams``), which means they are validated at
construction time and can be serialised to JSON for experiment tracking:

.. code-block:: python

    from openstef_models.models.forecasting.lgbm_forecaster import (
        LGBMForecaster,
        LGBMHyperParams,
    )
    from openstef_core.types import Q

    hyperparams = LGBMHyperParams(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        reg_alpha=0.1,
        reg_lambda=1.0,
    )

    model = LGBMForecaster(hyperparams=hyperparams, quantiles=[Q(0.1), Q(0.5), Q(0.9)])
    model.fit(train_dataset)

    forecast = model.predict(forecast_input_dataset)

The ``forecast`` object is a ``ForecastDataset`` (defined in ``openstef-core``)
containing one column per requested quantile.

Compositional Design
^^^^^^^^^^^^^^^^^^^^

The key architectural decision in ``openstef-models`` is that *transforms and
models are separate concerns*. A ``Forecaster`` does not hard-code its feature
engineering; it receives a fitted ``TransformPipeline`` as a collaborator. This
means you can swap the model algorithm without changing the feature engineering
logic, or extend the pipeline with a new domain-specific transform without
touching the model code.

.. code-block:: python

    from openstef_models.transforms.general import (
        Imputer, NaNDropper, Selector, EmptyFeatureRemover,
    )
    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder, LagsAdder,
    )
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_core.transforms.pipeline import TransformPipeline

    # Build the pipeline independently of the model
    feature_pipeline = TransformPipeline(
        transforms=[
            DatetimeFeaturesAdder(),
            LagsAdder(lags=[1, 2, 4, 48, 96]),
            EmptyFeatureRemover(),
            Imputer(),
            NaNDropper(),
            Selector(),
        ]
    )

    # Attach it to whichever model you want to evaluate
    model = XGBoostForecaster(transform_pipeline=feature_pipeline)
    model.fit(train_dataset)

----

Explainability Tools
--------------------

Understanding *why* a model makes a particular forecast is as important as the
forecast itself. The ``openstef_models.explainability`` subpackage provides two
mixin classes that any ``Forecaster`` can inherit from:

- **``ExplainableForecaster``** — exposes a ``feature_importances`` property
  returning a ``pd.DataFrame`` with feature names as the index and quantiles as
  columns. It also provides ``plot_feature_importances()``, which renders an
  interactive Plotly treemap — no external plotting setup required.

- **``ContributionsMixin``** — adds ``predict_contributions()``, which returns a
  ``TimeSeriesDataset`` where each column is the per-sample contribution of one
  feature to the final prediction. This is the SHAP-style decomposition that
  lets you trace an individual forecast back to its driving inputs.

All built-in tree-based forecasters (``XGBoostForecaster``, ``LGBMForecaster``,
etc.) implement both mixins, so explainability is available by default:

.. code-block:: python

    # After fitting a model that implements ExplainableForecaster
    importances = model.feature_importances          # pd.DataFrame
    print(importances.sort_values(Q(0.5), ascending=False).head(10))

    # Interactive treemap — opens in a browser or Jupyter cell
    fig = model.plot_feature_importances(quantile=Q(0.5))
    fig.show()

    # Per-sample SHAP-style contributions
    contributions = model.predict_contributions(forecast_input_dataset)
    # contributions is a TimeSeriesDataset; each column is one feature's contribution
    print(contributions.dataframe.head())

The ``FeatureImportancePlotter`` that backs ``plot_feature_importances()`` is
also available directly if you want to render importance scores computed outside
a model object:

.. code-block:: python

    from openstef_models.explainability.plotters.feature_importance_plotter import (
        FeatureImportancePlotter,
    )
    from openstef_core.types import Q

    plotter = FeatureImportancePlotter()
    fig = plotter.plot(scores=importances, quantile=Q(0.5))
    fig.write_html("feature_importances.html")

.. note::

   The mixin design means explainability is opt-in for custom model
   implementations. If you write a new ``Forecaster`` subclass and inherit from
   ``ExplainableForecaster``, you only need to implement the ``feature_importances``
   property; the ``plot_feature_importances`` method is provided for free.

----

Putting It Together
-------------------

A complete training workflow in ``openstef-models`` follows a consistent
three-step pattern: build a transform pipeline, attach it to a model, train, and
then inspect what the model learned.

.. code-block:: python

    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        HolidayFeatureAdder,
        LagsAdder,
    )
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.general import (
        Imputer, NaNDropper, Clipper, EmptyFeatureRemover, Selector,
    )
    from openstef_models.models.forecasting.lgbm_forecaster import (
        LGBMForecaster,
        LGBMHyperParams,
    )
    from openstef_core.transforms.pipeline import TransformPipeline
    from openstef_core.types import Q

    pipeline = TransformPipeline(
        transforms=[
            DatetimeFeaturesAdder(),
            CyclicFeaturesAdder(),
            HolidayFeatureAdder(country="NL"),
            LagsAdder(lags=[1, 2, 48]),
            WindPowerFeatureAdder(),
            EmptyFeatureRemover(),
            Imputer(),
            Clipper(),
            NaNDropper(),
            Selector(),
        ]
    )

    model = LGBMForecaster(
        hyperparams=LGBMHyperParams(n_estimators=200, max_depth=7),
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        transform_pipeline=pipeline,
    )

    model.fit(train_dataset)

    # Forecast
    forecast = model.predict(forecast_input_dataset)

    # Explain
    fig = model.plot_feature_importances(quantile=Q(0.5))
    fig.show()

    contributions = model.predict_contributions(forecast_input_dataset)

This pattern — composable transforms, swappable model backends, and built-in
explainability — is the central design philosophy of the ``openstef-models``
package. It keeps each concern isolated and testable while making it
straightforward to extend the library with new transforms or model algorithms.