The ``openstef_models`` Package
================================

This page is a deep dive into ``openstef_models``, the package that provides everything needed to go from raw time series data to a trained, explainable forecasting model. It covers three tightly related layers: the **transforms** module for feature engineering, the **models** module for forecasting implementations, and the **explainability** tools that make model behaviour transparent. For the foundational data types these layers operate on, see the :doc:`core` page. For ensemble architectures built on top of these primitives, see :doc:`meta`.

.. note:: [DIAGRAM: Component-level diagram showing three horizontal layers stacked vertically. Bottom layer: ``openstef_core`` (TimeSeriesDataset, TransformPipeline, base interfaces). Middle layer: ``openstef_models.transforms`` (five subpackages: validation, general, time_domain, weather_domain, energy_domain), each feeding into a central FeaturePipeline arrow. Top layer: ``openstef_models.models`` (ForecastingModel wrapping a Forecaster) and ``openstef_models.explainability`` (ExplainableForecaster, ContributionsMixin) shown as a side-channel attached to the models layer. Arrows flow upward, with ``openstef_models.presets`` shown as a shortcut that wires all three layers together.]

---

Compositional Design
--------------------

The central design idea in ``openstef_models`` is **composition over inheritance**. A ``ForecastingModel`` is not a monolithic class — it is a thin orchestrator that holds a preprocessing ``TransformPipeline``, a ``Forecaster``, and a postprocessing ``TransformPipeline``. Each of these pieces is independently replaceable. The transforms module supplies the building blocks for those pipelines; the models module supplies the forecasters; and the explainability module attaches to any forecaster that opts in.

This means you can mix and match: swap a GBLinear forecaster for XGBoost, add a domain-specific weather transform without touching the model, or attach a custom postprocessor — all without subclassing anything.

---

The Transforms Module
---------------------

``openstef_models.transforms`` is organised into five domain-aware subpackages, each exposing stateless or stateful transforms that implement the ``TimeSeriesTransform`` interface from ``openstef_core``:

- **``validation``** — data quality checks and cleaning steps applied before any feature engineering.
- **``general``** — domain-agnostic utilities such as ``DimensionalityReducer`` for pruning correlated features.
- **``time_domain``** — temporal feature generators: ``HolidayFeatureAdder``, ``LagsAdder``, and ``VersionedLagsAdder``.
- **``weather_domain``** — meteorological enrichment: ``AtmosphereDerivedFeaturesAdder``, ``DaylightFeatureAdder``, and related transforms.
- **``energy_domain``** — power-system-specific features, currently anchored by ``WindPowerFeatureAdder``.

Every transform exposes a ``features_added()`` method so downstream code can introspect which columns it will produce, and a ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` method that does the work.

Temporal Features
^^^^^^^^^^^^^^^^^

Lag features are the backbone of short-term energy forecasting. ``LagsAdder`` handles standard datasets, while ``VersionedLagsAdder`` is designed for ``VersionedTimeSeriesDataset`` — the versioned structure that tracks when each measurement became available. The versioned variant is critical in production: it ensures a lag feature only uses data that would have been available at prediction time, preventing look-ahead leakage.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder

   # Add 24h and 48h lags of the load column
   lags = LagsAdder(
       feature="load",
       lags=[timedelta(hours=-24), timedelta(hours=-48)],
   )

   # Add country-specific public holiday indicators
   holidays = HolidayFeatureAdder(country="NL")

   # Both transforms are stateless — no fit() call needed
   enriched = lags.transform(dataset)
   enriched = holidays.transform(enriched)

Weather and Energy Domain Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Weather transforms derive higher-level meteorological signals from raw forecast columns. ``AtmosphereDerivedFeaturesAdder`` computes quantities such as dew point and apparent temperature from humidity and pressure. ``DaylightFeatureAdder`` adds sunrise/sunset-relative features that are strongly predictive for solar generation. On the energy side, ``WindPowerFeatureAdder`` converts wind speed into an estimated power curve output, encoding physical domain knowledge directly into the feature space.

.. code-block:: python

   from openstef_models.transforms.weather_domain.atmosphere_derived_features_adder import (
       AtmosphereDerivedFeaturesAdder,
   )
   from openstef_models.transforms.weather_domain.daylight_feature_adder import DaylightFeatureAdder
   from openstef_models.transforms.energy_domain.wind_power_feature_adder import WindPowerFeatureAdder

   atmo = AtmosphereDerivedFeaturesAdder()
   daylight = DaylightFeatureAdder()
   wind_power = WindPowerFeatureAdder()

   # Each transform is independently applicable and composable
   dataset = atmo.transform(dataset)
   dataset = daylight.transform(dataset)
   dataset = wind_power.transform(dataset)

   # Inspect what was added
   print(wind_power.features_added())

Assembling a Pipeline
^^^^^^^^^^^^^^^^^^^^^

Transforms are composed into a ``TransformPipeline`` (from ``openstef_core``) that applies them in sequence. This pipeline is then passed directly into a ``ForecastingModel``.

.. code-block:: python

   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.weather_domain.daylight_feature_adder import DaylightFeatureAdder
   from datetime import timedelta

   preprocessing = TransformPipeline(
       transforms=[
           DaylightFeatureAdder(),
           HolidayFeatureAdder(country="NL"),
           LagsAdder(
               feature="load",
               lags=[timedelta(hours=-24), timedelta(hours=-48), timedelta(hours=-168)],
           ),
       ]
   )

---

The Models Module
-----------------

``openstef_models.models`` provides two main model types: ``ForecastingModel`` for single-forecaster pipelines and ``ComponentSplittingModel`` for decomposing a total load signal into constituent energy components. Both follow the same pattern: a preprocessing pipeline, a core algorithm, and an optional postprocessing pipeline.

``ForecastingModel`` and ``BaseForecastingModel``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``BaseForecastingModel`` is the abstract base shared by ``ForecastingModel`` (single forecaster) and ``EnsembleForecastingModel`` in ``openstef_meta``. It defines the ``fit`` / ``predict`` contract and ensures that preprocessing and postprocessing are always applied consistently around the core forecaster.

``ForecastingModel`` wraps any ``Forecaster`` implementation — including the built-in ``GBLinearForecaster``, ``XGBoostForecaster``, and ``FlatlinerForecaster`` — together with the preprocessing pipeline assembled from transforms:

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )
   from openstef_core.mixins import TransformPipeline
   from openstef_core.types import Q

   forecaster = GBLinearForecaster(
       hyperparams=GBLinearHyperParams(),
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=preprocessing,   # TransformPipeline from the previous section
   )

   model.fit(training_dataset)
   forecast = model.predict(input_dataset)

Component Splitting
^^^^^^^^^^^^^^^^^^^

``ComponentSplittingModel`` addresses a different problem: given a total load measurement, decompose it into labelled energy components (e.g. solar, wind, residual). It follows the same preprocessing/algorithm/postprocessing structure, but the core algorithm is a ``ComponentSplitter`` rather than a forecaster. The ``ConstantComponentSplitter`` provides a simple ratio-based baseline:

.. code-block:: python

   from openstef_models.models.component_splitting.constant_component_splitter import (
       ConstantComponentSplitter,
       ConstantComponentSplitterConfig,
   )
   from openstef_models.models.component_splitting.component_splitting_model import (
       ComponentSplittingModel,
   )
   from openstef_core.mixins import TransformPipeline
   from openstef_core.types import EnergyComponentType

   splitter = ConstantComponentSplitter(
       ConstantComponentSplitterConfig(
           source_column="total_load",
           components=[EnergyComponentType.SOLAR, EnergyComponentType.WIND],
           component_ratios={
               EnergyComponentType.SOLAR: 0.6,
               EnergyComponentType.WIND: 0.4,
           },
       )
   )

   splitting_model = ComponentSplittingModel(
       component_splitter=splitter,
       preprocessing=TransformPipeline(),
       source_column="total_load",
   )

   splitting_model.fit(training_data)
   components = splitting_model.predict(new_data)

---

Explainability
--------------

Explainability in ``openstef_models`` is implemented as **opt-in mixins** rather than a separate framework. A forecaster that can explain itself implements one or both of:

- ``ExplainableForecaster`` — exposes ``feature_importances`` (a ``pd.DataFrame``) and ``plot_feature_importances()``, which returns an interactive Plotly treemap where box size encodes importance.
- ``ContributionsMixin`` — exposes ``predict_contributions()``, which returns per-sample feature contribution scores as a ``TimeSeriesDataset``.

``GBLinearForecaster`` implements both. This design means explainability is a capability of the forecaster, not a post-hoc wrapper, so it is always consistent with the model that was actually trained.

.. code-block:: python

   from typing import cast
   from openstef_models.explainability import ExplainableForecaster

   # Cast to the explainability interface — valid when using GBLinearForecaster
   explainable = cast(ExplainableForecaster, model.forecaster)

   # Tabular feature importances
   importances = explainable.feature_importances
   print(importances.head(10))

   # Interactive treemap — larger boxes indicate more influential features
   fig = explainable.plot_feature_importances(quantile=Q(0.5))
   fig.show()

.. note::

   ``plot_feature_importances`` returns a ``plotly.graph_objects.Figure``. No external visualisation library is required — the method is part of the ``ExplainableForecaster`` interface provided directly by ``openstef_models``.

---

Presets: Wiring It All Together
--------------------------------

Assembling transforms, a forecaster, and a workflow by hand is straightforward but repetitive for common configurations. The ``openstef_models.presets`` subpackage provides ``ForecastingWorkflowConfig`` and the ``create_forecasting_workflow()`` factory, which wire up a complete pipeline — including MLflow storage, evaluation metrics, and sensible defaults for lag windows and weather columns — from a single configuration object.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Q
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="my_substation_001",
       forecaster_type="gblinear",
       location=LocationConfig(
           country="NL",
       ),
       horizons=[timedelta(hours=h) for h in range(1, 25)],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

   workflow = create_forecasting_workflow(config)

   workflow.train(training_dataset)
   forecast = workflow.predict(input_dataset)

Presets are the recommended starting point for new projects. Once you need to deviate — custom transforms, a non-standard forecaster, or a bespoke postprocessor — you can drop down to the lower-level ``ForecastingModel`` API shown in the sections above.

.. note::

   For ensemble presets that combine multiple base forecasters, see the :doc:`meta` page, which describes ``EnsembleForecastingWorkflowConfig`` and the combiner models available in ``openstef_meta``.

---

How the Layers Relate
---------------------

The three layers form a clean dependency graph:

- **Transforms** depend only on ``openstef_core`` data types. They are pure feature engineering and carry no model state beyond what is needed for stateful transforms (e.g. a fitted scaler).
- **Models** depend on transforms (via ``TransformPipeline``) and on ``openstef_core`` interfaces. They own the fit/predict lifecycle.
- **Explainability** is a side-channel: it depends on the models layer but does not affect the prediction path. A forecaster that does not implement the mixins simply does not expose those methods.

This separation means you can unit-test transforms in isolation, swap forecasters without touching feature engineering, and add explainability to a custom forecaster by implementing two methods.

For backtesting and statistical evaluation of models built with these components, see the :doc:`beam` page.