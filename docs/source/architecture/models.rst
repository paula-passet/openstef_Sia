The Models Package
==================

The ``openstef-models`` package is the forecasting engine of OpenSTEF. It provides everything needed to go from raw time series data to calibrated probabilistic forecasts: a domain-aware feature engineering layer, a set of ready-to-use forecasting model implementations, and built-in explainability tools. This page describes how these three layers are designed, how they relate to each other, and how to compose them in practice.

For the foundational data types (``TimeSeriesDataset``, ``ForecastInputDataset``) that all of these components operate on, see the :doc:`core` page. For backtesting and evaluation of trained models, see the :doc:`beam` page.

.. mermaid:: /diagrams/architecture/models_diagram_1.mmd

---

The Transforms Layer
--------------------

The ``openstef_models.transforms`` package organises feature engineering into five domain-specific subpackages. Each transform implements the same ``TimeSeriesTransform`` interface — ``fit(data)``, ``transform(data)``, and ``features_added()`` — so they can be composed freely into preprocessing pipelines without any special glue code.

The five subpackages reflect the natural structure of energy forecasting problems:

- **``validation``** — sanity checks that run before any feature engineering: ``CompletenessChecker``, ``FlatlineChecker``, and ``InputConsistencyChecker`` raise early errors rather than letting bad data silently corrupt a model.
- **``time_domain``** — temporal features that capture periodicity and recency: ``DatetimeFeaturesAdder``, ``CyclicFeaturesAdder``, ``HolidayFeatureAdder``, ``LagsAdder``, and ``RollingAggregatesAdder``.
- **``weather_domain``** — derived meteorological features: ``RadiationDerivedFeaturesAdder``, ``AtmosphereDerivedFeaturesAdder``, and ``DaylightFeatureAdder``.
- **``energy_domain``** — physics-informed features specific to power systems, such as ``WindPowerFeatureAdder``, which converts wind speed measurements into an estimated power curve.
- **``general``** — data hygiene transforms applied regardless of domain: ``Imputer``, ``NaNDropper``, ``Clipper``, ``Scaler``, ``Selector``, ``EmptyFeatureRemover``, and ``SampleWeighter``.

A sixth subpackage, **``postprocessing``**, operates on the model's output rather than its input. ``ConfidenceIntervalApplicator`` adds learned uncertainty bands to point forecasts, and ``QuantileSorter`` enforces monotonicity across quantile outputs.

The ``features_added()`` method on every transform is worth highlighting: it lets a pipeline introspect exactly which columns each step introduces, making it straightforward to audit the full feature set without running any data through the pipeline.

Composing a Feature Pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Transforms are assembled into a ``FeaturePipeline`` that is passed to a ``ForecastingModel``. The pipeline runs each transform in sequence during both training and inference, ensuring that the same feature engineering logic is applied consistently.

.. code-block:: python

    from openstef_models.transforms.validation import CompletenessChecker
    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        HolidayFeatureAdder,
        LagsAdder,
    )
    from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.general import Imputer, Scaler, NaNDropper

    preprocessing_steps = [
        CompletenessChecker(),
        DatetimeFeaturesAdder(),
        CyclicFeaturesAdder(),
        HolidayFeatureAdder(country="NL"),
        LagsAdder(lags=[1, 2, 3, 24, 48]),
        RadiationDerivedFeaturesAdder(),
        WindPowerFeatureAdder(),
        Imputer(),
        Scaler(),
        NaNDropper(),
    ]

Each step receives a ``TimeSeriesDataset`` and returns one, so the pipeline is a pure data transformation chain. Validation steps at the front of the list act as a guard: if the input data fails a completeness or flatline check, the pipeline raises immediately rather than producing a silently degraded forecast.

---

The Models Layer
----------------

The ``openstef_models.models`` subpackage provides concrete forecasting implementations. All of them extend the ``Forecaster`` base class from ``openstef-core``, which defines the ``fit`` / ``predict`` contract. The available implementations cover the range of practical needs:

- **``XGBoostForecaster``** — gradient-boosted trees via XGBoost, with multi-quantile output and magnitude-weighted pinball loss. The default choice for most energy forecasting tasks.
- **``LGBMForecaster``** — the same gradient-boosting approach using LightGBM, often faster to train on large datasets.
- **``GBLinearForecaster``** / **``LGBMLinearForecaster``** — linear models wrapped in the XGBoost and LightGBM boosting frameworks respectively, useful when interpretability or regularisation is a priority.
- **``MedianForecaster``** — a simple lag-based median model that serves as a strong baseline and as a fallback when training data is scarce.
- **``FlatlinerForecaster``** — a degenerate model that predicts a constant value, useful for detecting and handling flatline measurement periods.

Each forecaster is configured through a paired ``HyperParams`` class (e.g. ``XGBoostHyperParams``, ``LGBMHyperParams``) that uses Pydantic validation. This means hyperparameter errors are caught at construction time, not at training time.

Assembling a Complete Forecasting Model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A ``ForecastingModel`` binds a forecaster together with its preprocessing pipeline. The following example builds a complete model from scratch:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import Quantile as Q, LeadTime
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )
    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        LagsAdder,
    )
    from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
    from openstef_models.transforms.validation import CompletenessChecker

    # Configure the forecaster
    forecaster = XGBoostForecaster(
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=XGBoostHyperParams(n_estimators=200, max_depth=6),
    )

    # Assemble preprocessing steps
    preprocessing_steps = [
        CompletenessChecker(),
        DatetimeFeaturesAdder(),
        HolidayFeatureAdder(country="NL"),
        LagsAdder(lags=[1, 2, 3, 24, 48]),
        Imputer(),
        Scaler(),
        NaNDropper(),
    ]

    # Fit on a ForecastInputDataset (see openstef-core docs)
    forecaster.fit(training_data)

    # Predict returns a ForecastDataset with one column per quantile
    forecast = forecaster.predict(test_data)

.. note::

   XGBoost and LightGBM are optional dependencies. Install them with
   ``pip install openstef-models[xgboost]`` or ``pip install openstef-models[lgbm]``
   respectively.

The compositional design means you can swap the forecaster without touching the preprocessing pipeline, or extend the pipeline with domain-specific transforms without modifying the model. The ``ForecastingModel`` wrapper handles the sequencing.

---

The Explainability Layer
------------------------

Explainability in ``openstef-models`` is delivered through two mixins that forecasters opt into by inheritance, rather than through a separate tool that operates on models from the outside.

``ExplainableForecaster``
  Adds a ``feature_importances`` property that returns a ``pd.DataFrame`` indexed by feature name, with one column per quantile. It also provides ``plot_feature_importances()``, which produces an interactive Plotly treemap — no external visualisation library required.

``ContributionsMixin``
  Adds ``predict_contributions(data)``, which returns a ``TimeSeriesDataset`` of per-sample SHAP values. This lets you answer not just *which features matter overall* but *why the model made a specific prediction at a specific time*.

Both ``XGBoostForecaster`` and ``LGBMForecaster`` implement both mixins. The simpler models (``MedianForecaster``, ``FlatlinerForecaster``) implement ``ContributionsMixin`` with uniform or trivial contributions, so calling code does not need to branch on model type.

Using the Explainability Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # After fitting an XGBoostForecaster (see above)

    # --- Feature importances ---
    importances = forecaster.feature_importances  # pd.DataFrame
    print(importances.head())

    # Interactive treemap (returns a plotly Figure)
    fig = forecaster.plot_feature_importances(quantile=Q(0.5))
    fig.show()

    # --- Per-sample SHAP contributions ---
    contributions = forecaster.predict_contributions(test_data)
    # contributions is a TimeSeriesDataset; each column is one feature's
    # contribution to the prediction at that timestamp
    contributions_df = contributions.data
    print(contributions_df.head())

Because ``plot_feature_importances`` is built into the mixin and backed by ``FeatureImportancePlotter``, the visualisation is consistent across all model types that implement ``ExplainableForecaster`` — you do not need to wire up a separate SHAP plotting library.

---

How the Layers Compose
-----------------------

The three layers are deliberately loosely coupled. Transforms know nothing about models; models know nothing about explainability plotters; the explainability mixins know nothing about which transforms were used. The only shared contract is the ``TimeSeriesDataset`` / ``ForecastInputDataset`` / ``ForecastDataset`` type hierarchy defined in ``openstef-core``.

This means the library is open to extension at every layer:

- Add a new domain transform by implementing ``TimeSeriesTransform`` and dropping it into any pipeline.
- Add a new forecaster by extending ``Forecaster`` and, optionally, mixing in ``ExplainableForecaster`` and ``ContributionsMixin``.
- Add a new explainability visualisation by implementing a plotter that consumes the ``pd.DataFrame`` returned by ``feature_importances``.

None of these extensions require modifying existing code, which keeps the library composable as forecasting requirements evolve.

.. note::

   For high-level workflow orchestration — training, validation, and prediction in a single call — see the ``CustomForecastingWorkflow`` and preset configurations in ``openstef_models.presets``. These build on the same transforms and models described here, but handle the end-to-end sequencing for common use cases.