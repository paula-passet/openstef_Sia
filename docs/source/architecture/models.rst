The ``openstef_models`` Package
================================

This page is a deep dive into the ``openstef_models`` package — the layer of OpenSTEF that turns raw time series data into trained, explainable forecasting models. It covers three tightly coupled subsystems: the **transforms** module for domain-aware feature engineering, the **models** module that orchestrates the full prediction pipeline, and the **explainability** tools that expose what a trained model has learned.

For the foundational data types (``TimeSeriesDataset``, ``ForecastDataset``) that these components consume and produce, see the :doc:`core` page. For ensemble architectures built on top of the single-model primitives described here, see :doc:`meta`.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

----

The Transforms Module
---------------------

Feature engineering in ``openstef_models`` is organised into five domain subpackages, all importable from ``openstef_models.transforms``:

.. code-block:: python

   from openstef_models.transforms import (
       energy_domain,
       general,
       time_domain,
       validation,
       weather_domain,
   )

Every individual transform is a lightweight, composable object that implements the ``TimeSeriesTransform`` interface from ``openstef_core``. Each transform exposes a ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` method and a ``features_added()`` property that declares which columns it contributes. This makes pipelines self-documenting: you can always ask a pipeline what features it will produce before fitting it.

**Validation** transforms act as guards at the start of a pipeline — checking for required columns, detecting flatliners, and raising structured errors before any computation begins. Placing these first is a deliberate convention: fail fast with a clear message rather than propagate NaNs silently.

**Time-domain** transforms encode calendar knowledge. ``HolidayFeatureAdder`` uses a country code (ISO 3166-1 alpha-2) to inject binary holiday indicator columns, one per named holiday in that country's calendar. ``LagsAdder`` is the most nuanced transform in this group: rather than a simple ``shift()``, it respects data-availability constraints in ``VersionedTimeSeriesDataset``. For each configured lag, it shifts timestamps forward so that a lag feature at horizon *h* only uses data that would genuinely have been available at prediction time. This prevents the subtle data-leakage that plagues naive lag implementations.

**Weather-domain** transforms derive meteorological features from raw weather inputs. ``AtmosphereDerivedFeaturesAdder`` computes quantities such as dew point and absolute humidity from temperature and relative humidity. ``DaylightFeatureAdder`` adds solar-position and daylight-duration features, which are strong predictors for solar generation and air-conditioning load.

**Energy-domain** transforms encode power-system knowledge. Currently this includes ``WindPowerFeatureAdder``, which derives wind-power proxy features from wind speed using a turbine power-curve approximation.

**General** transforms cover cross-domain utilities: imputation, scaling, datetime encoding, and quantile sorting.

Composing Transforms into a Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are assembled into a ``TransformPipeline`` (from ``openstef_core.mixins``) before being handed to a model. The pipeline calls each transform in sequence, passing the output of one as the input of the next, and handles ``fit``/``transform`` separation correctly for stateful transforms like scalers.

.. code-block:: python

   from datetime import timedelta

   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.mixins import TransformPipeline
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.general import DatetimeFeaturesAdder, Imputer

   preprocessing = TransformPipeline([
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
       DatetimeFeaturesAdder(onehot_encode=False),
       LagsAdder(lags=[timedelta(hours=24), timedelta(hours=48)]),
       Imputer(),
   ])

The pipeline is not tied to any particular model — you can fit and apply it independently, inspect the features it adds, or swap individual steps without touching the rest of the configuration.

----

The Models Module
-----------------

``openstef_models.models`` provides the orchestration layer that wraps a raw forecaster (XGBoost, GBLinear, a constant-median baseline, etc.) inside a structured pipeline:

.. code-block:: text

   preprocessing (TransformPipeline)
         ↓
     forecaster  (Forecaster interface)
         ↓
   postprocessing (TransformPipeline)

The abstract base ``BaseForecastingModel`` defines the contract shared by all implementations:

- ``fit(data, data_val, data_test)`` — trains preprocessing and forecaster together, returning a ``ModelFitResult``
- ``predict(data, forecast_start)`` — applies preprocessing then generates a ``ForecastDataset``
- ``prepare_input(data, forecast_start)`` — runs only the preprocessing step, useful for inspection
- ``score(data)`` — evaluates the model and returns a ``SubsetMetric``
- ``get_explainable_components()`` — returns named sub-components that support feature-importance queries

``ForecastingModel`` is the concrete single-forecaster implementation. It wires together one preprocessing pipeline, one forecaster, and one postprocessing pipeline, and handles the bookkeeping differences between single-horizon and multi-horizon forecasters automatically.

.. note::

   The ``cutoff_history`` parameter on ``ForecastingModel`` is important when your preprocessing includes lag transforms. A 14-day lag, for example, produces NaN rows for the first 14 days of training data. Set ``cutoff_history`` to exclude those rows; the library cannot infer this automatically because it depends on your specific pipeline configuration.

Building a ``ForecastingModel`` from Scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following example constructs a complete single-forecaster pipeline with a GBLinear model:

.. code-block:: python

   from datetime import timedelta

   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.mixins import TransformPipeline
   from openstef_core.types import Q
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.general import DatetimeFeaturesAdder, Imputer, QuantileSorter

   quantiles = [Q(0.05), Q(0.5), Q(0.95)]
   horizon = timedelta(days=1)

   model = ForecastingModel(
       preprocessing=TransformPipeline([
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           DatetimeFeaturesAdder(onehot_encode=False),
           LagsAdder(lags=[timedelta(hours=24), timedelta(hours=48)]),
           Imputer(),
       ]),
       forecaster=GBLinearForecaster(
           quantiles=quantiles,
           horizons=[horizon],
           hyperparams=GBLinearHyperParams(),
       ),
       postprocessing=TransformPipeline([QuantileSorter()]),
       cutoff_history=timedelta(days=2),
   )

   # Train
   fit_result = model.fit(data=train_dataset, data_val=val_dataset)

   # Predict
   forecast = model.predict(data=test_dataset)

Using Presets
^^^^^^^^^^^^^

For common configurations, ``openstef_models.presets`` provides factory functions that assemble the full pipeline — preprocessing, forecaster, and postprocessing — from a single configuration object. This is the fastest path to a working model and the recommended starting point for new use cases.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       build_forecasting_workflow,
   )
   from openstef_core.types import Q
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model="gblinear",
       quantiles=[Q(0.05), Q(0.5), Q(0.95)],
       horizons=[timedelta(days=1)],
   )

   workflow = build_forecasting_workflow(config)

Presets cover ``xgboost``, ``gblinear``, ``lgbm``, ``lgbmlinear``, and ``flatliner`` (a constant-median baseline useful for sanity-checking). Each preset selects an appropriate set of preprocessing transforms for that model family — for example, GBLinear receives an ``Imputer`` and feature standardisation because the underlying linear booster is sensitive to feature scale, whereas tree-based XGBoost does not require standardisation.

----

Explainability
--------------

Explainability in ``openstef_models`` is expressed through two mixins that forecaster implementations can opt into:

- **``ExplainableForecaster``** (from ``openstef_models.explainability.mixins``) — provides ``feature_importances`` (a ``pd.DataFrame``) and ``plot_feature_importances()``, which returns an interactive Plotly treemap where box area is proportional to importance.
- **``ContributionsMixin``** — provides ``predict_contributions(data)``, which returns per-sample feature contribution values (SHAP-style additive decomposition).

Both are accessed through the model's ``get_explainable_components()`` method, which returns a dictionary of named components that implement ``ExplainableForecaster``. This indirection means the same calling code works for a ``ForecastingModel`` (one component) and an ``EnsembleForecastingModel`` (one component per base forecaster).

.. code-block:: python

   from typing import cast
   from openstef_models.explainability.mixins import ExplainableForecaster

   # Retrieve the explainable component from a trained model
   explainable_components = model.get_explainable_components()
   explainable = cast(ExplainableForecaster, explainable_components["forecaster"])

   # Tabular feature importances
   importances_df = explainable.feature_importances
   print(importances_df.sort_values("importance", ascending=False).head(10))

   # Interactive treemap — larger boxes indicate more important features
   fig = explainable.plot_feature_importances(quantile=Q(0.5))
   fig.show()

.. note::

   Not all forecasters implement both mixins. ``GBLinearForecaster`` and ``XGBoostForecaster`` implement ``ExplainableForecaster``; ``ContributionsMixin`` support depends on whether the underlying model exposes SHAP values. Check ``get_explainable_components()`` at runtime — an empty dict means the model does not support explainability queries.

The ``ContributionsMixin`` is also surfaced at the ``ForecastingModel`` level via ``predict_contributions()``, which internally calls ``prepare_input()`` to apply preprocessing before delegating to the forecaster. This means contribution values are expressed in terms of the *engineered* features (lag columns, holiday indicators, etc.), not the raw inputs — which is usually what you want when debugging a model's behaviour on a specific day.

----

Compositional Design
--------------------

The key architectural insight of ``openstef_models`` is that **models are assembled, not subclassed**. Rather than a deep inheritance hierarchy where each model variant overrides methods, the library uses composition: a ``ForecastingModel`` holds a preprocessing pipeline, a forecaster, and a postprocessing pipeline as first-class fields. Swapping the forecaster from ``GBLinearForecaster`` to ``XGBoostForecaster`` requires changing one field; the rest of the pipeline is unchanged.

This design also makes serialisation straightforward. Because all components are Pydantic models, a complete ``ForecastingModel`` — including its fitted state — can be serialised and restored via ``LocalModelStorage`` or the MLflow integration in ``openstef_models.integrations.mlflow``.

For ensemble architectures that compose multiple ``ForecastingModel`` instances with a shared preprocessing stage, see :doc:`meta`. For backtesting and evaluation of trained models, see :doc:`beam`.