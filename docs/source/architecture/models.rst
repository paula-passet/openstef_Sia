The ``openstef_models`` Package
================================

This page is a deep dive into ``openstef_models``, the package that provides
OpenSTEF's feature engineering pipelines, concrete forecasting model
implementations, and explainability tools. Together these three layers form
the core modelling surface of the library. For the data structures that feed
into these models see the :doc:`core` page; for ensemble and meta-learning
architectures built on top of them see the :doc:`meta` page.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

Compositional Design
--------------------

The central design idea in ``openstef_models`` is *composition over
inheritance*. Rather than encoding feature engineering logic inside a model
class, the library separates concerns into three independent layers that are
wired together at configuration time:

- **Transforms** — stateless or stateful sklearn-style transformers, grouped
  by domain, that convert a ``TimeSeriesDataset`` into a richer one.
- **Models** — forecaster implementations that consume a transformed dataset
  and emit a ``ForecastDataset``. They know nothing about feature engineering.
- **Explainability** — mixins and plotters that can be attached to any
  compatible forecaster to expose feature importance and per-sample
  contributions without changing the forecaster's core logic.

The glue between these layers is ``TransformPipeline``, a typed container
that chains transforms and exposes a single ``fit_transform`` / ``transform``
interface. ``ForecastingModel`` holds two pipelines — one for preprocessing
and one for postprocessing — plus a single forecaster in the middle.

The Transforms Module
---------------------

``openstef_models.transforms`` is organised into five sub-packages, each
targeting a distinct concern:

- ``time_domain`` — cyclic encodings, datetime features, holiday indicators,
  lag features, rolling aggregates.
- ``weather_domain`` — derived meteorological features such as daylight
  duration, atmosphere-derived variables, and radiation-derived solar
  irradiance.
- ``energy_domain`` — power-system-specific transforms, currently including
  ``WindPowerFeatureAdder`` for converting wind-speed measurements into
  estimated wind-power features.
- ``general`` — domain-agnostic utilities: outlier handling, scaling,
  imputation, NaN dropping, sample weighting, and empty-feature removal.
- ``validation`` — data-quality checks that run at the head of a pipeline
  and raise early if required columns are missing or data is malformed.

Every transform implements the ``TimeSeriesTransform`` protocol: a
``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` method and a
``features_added() -> list[str]`` property that declares which columns it
introduces. This contract makes transforms introspectable and composable
without coupling them to any particular model.

.. code-block:: python

   from openstef_models.transforms import (
       energy_domain,
       time_domain,
       weather_domain,
       general,
   )
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.general import (
       Imputer,
       NaNDropper,
       OutlierHandler,
       Scaler,
       SampleWeighter,
       EmptyFeatureRemover,
   )

   # Inspect what columns a transform will add before fitting
   daylight = DaylightFeatureAdder(coordinate=(52.37, 4.90))
   print(daylight.features_added())

Because each transform declares its outputs, a pipeline can be validated
structurally — you can verify that every feature a forecaster expects is
produced by some upstream transform before any data is loaded.

Building a Feature Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are assembled into a ``TransformPipeline`` that is passed to
``ForecastingModel``. The ordering matters: validation checks should run
first, domain-specific feature adders next, and normalisation/imputation
last so that scaling is applied to the full feature set.

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
   )
   from openstef_models.transforms.general import Scaler, NaNDropper
   from openstef_core.types import Q
   # TransformPipeline is a typed container — import from models package
   from openstef_models.models.forecasting_model import ForecastingModel

   # A representative preprocessing stack for a load-forecasting use case
   preprocessing_transforms = [
       # 1. Temporal features
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code="NL"),
       # 2. Weather-derived features
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       DaylightFeatureAdder(coordinate=(52.37, 4.90)),
       # 3. Lag features (set cutoff_history on ForecastingModel accordingly)
       LagsAdder(
           history_available=14,
           horizons=[Q(1), Q(24), Q(48)],
           target_column="load",
       ),
       # 4. Normalisation
       NaNDropper(),
       Scaler(method="standard"),
   ]

.. note::

   When using ``LagsAdder``, set ``cutoff_history`` on ``ForecastingModel``
   to match the longest lag window. Lag transforms introduce NaN rows at the
   start of the training set; ``cutoff_history`` tells the model to discard
   those rows rather than training on incomplete samples.

The Models Module
-----------------

``openstef_models.models`` contains the forecaster implementations and the
``ForecastingModel`` orchestrator that wraps them.

ForecastingModel
^^^^^^^^^^^^^^^^

``ForecastingModel`` is the primary entry point for single-forecaster
workflows. It holds:

- ``preprocessing`` — a ``TransformPipeline`` that runs before training and
  prediction.
- ``forecaster`` — any object implementing the forecaster protocol
  (``fit``, ``predict``).
- ``postprocessing`` — a ``TransformPipeline`` applied to the raw forecast
  output (e.g. sorting quantiles, applying confidence intervals).

During ``fit``, the preprocessing pipeline is fitted and transformed on the
training data, then the forecaster is trained on the result. During
``predict``, only ``transform`` (not ``fit_transform``) is called, ensuring
that scaling statistics learned on training data are applied consistently to
new inputs.

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearForecaster
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       LagsAdder,
   )
   from openstef_models.transforms.general import Scaler, NaNDropper, Imputer
   from openstef_models.transforms.postprocessing import (
       QuantileSorter,
       ConfidenceIntervalApplicator,
   )
   from openstef_core.types import Q

   horizons = [Q(1), Q(24)]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       preprocessing=TransformPipeline(transforms=[
           CyclicFeaturesAdder(),
           DatetimeFeaturesAdder(onehot_encode=False),
           LagsAdder(history_available=7, horizons=horizons, target_column="load"),
           Imputer(imputation_strategy="mean"),
           NaNDropper(),
           Scaler(method="standard"),
       ]),
       forecaster=GBLinearForecaster(
           quantiles=quantiles,
           horizons=horizons,
       ),
       postprocessing=TransformPipeline(transforms=[
           QuantileSorter(),
           ConfidenceIntervalApplicator(quantiles=quantiles),
       ]),
       target_column="load",
       cutoff_history=7,   # discard first 7 days of lag-NaN rows
   )

Available Forecasters
^^^^^^^^^^^^^^^^^^^^^

The library ships several forecaster implementations, each suited to
different data regimes:

- **GBLinearForecaster** — gradient-boosted linear model; fast, interpretable,
  and the default choice for most load-forecasting tasks. Implements
  ``ExplainableForecaster``.
- **XGBoostForecaster** — XGBoost-backed forecaster for capturing non-linear
  patterns in complex feature spaces.
- **MedianForecaster** — lag-based median baseline; useful as a sanity-check
  benchmark.
- **ConstantMedianForecaster** — predicts the historical median regardless of
  input; the simplest possible baseline.
- **FlatlinerForecaster** — detects and handles flat-line (zero-load) periods
  explicitly.

All forecasters share the same protocol, so they are interchangeable inside
``ForecastingModel`` without changing the surrounding pipeline.

Using Presets
^^^^^^^^^^^^^

For common configurations, ``openstef_models`` exposes preset factory
functions that assemble a fully-configured ``ForecastingModel`` (wrapped in a
``CustomForecastingWorkflow``) from a single configuration object. This is the
fastest path from data to a working model:

.. code-block:: python

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   config = ForecastingWorkflowConfig(
       model="gblinear",
       target_column="load",
       horizons=[1, 24, 48],
       quantiles=[0.1, 0.5, 0.9],
   )

   workflow = create_forecasting_workflow(config)

   dataset = create_synthetic_forecasting_dataset()
   workflow.train(dataset)
   forecast = workflow.predict(dataset)

Internally, ``create_forecasting_workflow`` builds exactly the kind of
``TransformPipeline`` + forecaster + postprocessing stack shown in the manual
example above. Presets are a good starting point; the manual approach gives
full control when you need to customise individual transforms.

The Explainability Module
-------------------------

``openstef_models.explainability`` provides two mixins and a plotter that
can be used independently of any particular forecaster implementation.

ExplainableForecaster
^^^^^^^^^^^^^^^^^^^^^

``ExplainableForecaster`` is an abstract mixin. Forecasters that implement it
expose:

- ``feature_importances`` — a ``pd.DataFrame`` of importance scores, one row
  per feature.
- ``plot_feature_importances(quantile)`` — an interactive Plotly treemap where
  box area is proportional to importance. Larger boxes indicate features that
  contribute more to the model's predictions.

``GBLinearForecaster`` implements this mixin, making it the natural choice
when interpretability is a requirement.

.. code-block:: python

   from typing import cast
   from openstef_models.explainability import ExplainableForecaster

   # After training, cast to the mixin type to access explainability methods
   explainable = cast(ExplainableForecaster, workflow.model.forecaster)

   # Tabular importance scores
   importances = explainable.feature_importances
   print(importances.head(10))

   # Interactive treemap — works in Jupyter or any Plotly-compatible environment
   fig = explainable.plot_feature_importances()
   fig.show()

ContributionsMixin
^^^^^^^^^^^^^^^^^^

``ContributionsMixin`` goes one level deeper: rather than global feature
importance, it computes *per-sample* feature contributions — how much each
feature pushed a specific prediction up or down relative to the baseline.

.. code-block:: python

   from openstef_models.explainability import ContributionsMixin
   from typing import cast

   contributive = cast(ContributionsMixin, workflow.model.forecaster)

   # Returns a TimeSeriesDataset where each column is a feature contribution
   contributions = contributive.predict_contributions(forecast_input)
   print(contributions.data.head())

Per-sample contributions are particularly useful for debugging unexpected
forecast spikes: you can immediately see which feature (e.g. an anomalous
temperature reading or a missing lag value) drove the outlier prediction.

FeatureImportancePlotter
^^^^^^^^^^^^^^^^^^^^^^^^

``FeatureImportancePlotter`` is a standalone plotter that can be used outside
the mixin hierarchy — for example, to compare importance profiles across two
separately trained models:

.. code-block:: python

   from openstef_models.explainability import FeatureImportancePlotter

   plotter = FeatureImportancePlotter()
   fig = plotter.plot(importances_df)
   fig.show()

How the Layers Interact
-----------------------

The three modules are deliberately decoupled. A transform does not know which
forecaster will consume its output; a forecaster does not know which
postprocessing step will refine its predictions; an explainability mixin does
not know which pipeline assembled the model. This means you can:

- Swap a forecaster without touching the feature pipeline.
- Add a new transform domain (e.g. ``market_domain``) without modifying any
  model code.
- Attach explainability to a third-party forecaster by implementing the mixin
  interface.

The ``ForecastingModel`` class is the only place where these layers are
composed, and it does so through constructor injection — making the
composition explicit and testable.

For ensemble architectures that compose *multiple* ``ForecastingModel``
instances, see the :doc:`meta` page. For backtesting and evaluating the
quality of a trained model, see the :doc:`beam` page.