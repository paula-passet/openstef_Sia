The Models Package
==================

The ``openstef-models`` package is the forecasting engine of OpenSTEF. It provides the
feature engineering pipelines, forecasting model implementations, and explainability
tools that turn raw time series data into calibrated probabilistic forecasts. This page
explains how those three layers are structured and how they compose together.

.. mermaid:: diagrams/architecture/models_diagram_1.mmd

For the data types (``TimeSeriesDataset``, ``ForecastInputDataset``) that flow through
these layers, see the :doc:`core` sibling page. For backtesting and evaluation of
trained models, see :doc:`beam`.

----

The Transforms Layer
--------------------

Feature engineering in OpenSTEF is expressed as a collection of stateful
``TimeSeriesTransform`` objects, each responsible for a single, well-scoped
transformation. Transforms are grouped into five domain subpackages, all exported from
``openstef_models.transforms``:

- **validation** — data quality checks (completeness, flatlines, input consistency)
- **general** — domain-agnostic utilities (imputation, clipping, scaling, feature selection, sample weighting)
- **time_domain** — calendar and lag features (datetime components, cyclic encoding, holidays, rolling aggregates, lag windows)
- **weather_domain** — meteorological derivations (radiation-derived features, atmospheric features, daylight duration)
- **energy_domain** — power-system-specific features (e.g. wind power from wind speed)

Every transform follows the same contract: it accepts a ``TimeSeriesDataset``, returns
a ``TimeSeriesDataset``, and can be fitted on training data before being applied to
unseen data. This uniformity means transforms are interchangeable and composable — a
``ForecastingModel`` simply holds an ordered list of them as its preprocessing pipeline.

Domain subpackages
^^^^^^^^^^^^^^^^^^

**Validation transforms** run at the pipeline boundary and raise structured exceptions
when data quality falls below acceptable thresholds. ``CompletenessChecker`` verifies
that enough non-null observations are present; ``FlatlineChecker`` detects stuck sensors;
``InputConsistencyChecker`` ensures that feature columns expected by the model are
actually present.

**General transforms** handle the mechanics of preparing a feature matrix.
``Imputer`` fills missing values, ``Scaler`` normalises numeric columns,
``Clipper`` constrains values to the range observed during training (preventing
extrapolation artefacts), ``Selector`` retains only the columns needed by the
downstream model, and ``NaNDropper`` removes rows that cannot be recovered. The
``SampleWeighter`` / ``SampleWeightConfig`` pair lets you emphasise recent observations
or specific time windows during training.

**Time-domain transforms** are where most of the predictive signal for energy
forecasting is created. ``LagsAdder`` appends lagged copies of the target and
selected features; ``RollingAggregatesAdder`` computes rolling statistics with
configurable ``AggregationFunction`` values; ``DatetimeFeaturesAdder`` extracts
hour-of-day, day-of-week, and month; ``CyclicFeaturesAdder`` encodes those integers
as sine/cosine pairs so that the model sees temporal continuity; and
``HolidayFeatureAdder`` injects a binary holiday indicator.

**Weather-domain transforms** derive physically meaningful quantities from raw
meteorological inputs. ``RadiationDerivedFeaturesAdder`` computes clear-sky indices and
other radiation ratios; ``AtmosphereDerivedFeaturesAdder`` adds humidity and pressure
combinations; ``DaylightFeatureAdder`` calculates sunrise/sunset-based daylight
duration, which is a strong proxy for solar generation.

**Energy-domain transforms** encode knowledge specific to power systems.
``WindPowerFeatureAdder`` applies a wind-power curve to raw wind-speed measurements,
producing a feature that is directly proportional to turbine output rather than the
raw meteorological variable.

Building a preprocessing pipeline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because every transform shares the same interface, assembling a pipeline is
straightforward:

.. code-block:: python

    from openstef_models.transforms.validation import CompletenessChecker
    from openstef_models.transforms.general import Imputer, Scaler, NaNDropper
    from openstef_models.transforms.time_domain import (
        LagsAdder,
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        HolidayFeatureAdder,
    )
    from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    preprocessing = [
        CompletenessChecker(),
        WindPowerFeatureAdder(),
        RadiationDerivedFeaturesAdder(),
        DatetimeFeaturesAdder(),
        CyclicFeaturesAdder(),
        HolidayFeatureAdder(country="NL"),
        LagsAdder(lags=[1, 2, 3, 24, 48]),
        Imputer(),
        NaNDropper(),
        Scaler(),
    ]

This list is passed directly to ``ForecastingModel`` as its ``preprocessing`` argument.
The order matters: domain-specific feature adders should run before lag and rolling
transforms so that the derived features also get their own lag columns.

----

The Models Layer
----------------

``openstef-models`` ships several concrete forecaster implementations, all built on a
common ``Forecaster`` base class defined in
``openstef_models.models.forecasting.forecaster``. The available models are:

- ``XGBoostForecaster`` — gradient-boosted trees via XGBoost, with quantile regression support
- ``LGBMForecaster`` — LightGBM equivalent, often faster on large feature sets
- ``GBLinearForecaster`` — XGBoost with a linear booster, useful as a regularised baseline
- ``LGBMLinearForecaster`` — LightGBM with a linear booster
- ``MedianForecaster`` — predicts the historical median; a robust naive baseline
- ``FlatlinerForecaster`` — predicts a constant; useful for detecting degenerate cases

Each model exposes paired hyperparameter classes (e.g. ``XGBoostHyperParams``,
``LGBMHyperParams``) that are Pydantic models, giving you validation, serialisation,
and IDE autocompletion for free.

ForecastingModel: the compositional wrapper
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The key design insight is that a raw ``Forecaster`` is never used directly in
production code. Instead, it is wrapped inside a ``ForecastingModel``, which
orchestrates the full pipeline:

1. Apply preprocessing transforms (fitted on training data)
2. Delegate to the inner ``Forecaster`` for ``fit`` / ``predict``
3. Apply postprocessing transforms (``QuantileSorter``, ``ConfidenceIntervalApplicator``)

This separation keeps the ``Forecaster`` implementations small and focused — they only
need to handle the model mathematics — while ``ForecastingModel`` handles all the
data-wrangling concerns.

.. code-block:: python

    from openstef_models.models import ForecastingModel
    from openstef_models.models.forecasting.lgbm_forecaster import (
        LGBMForecaster,
        LGBMHyperParams,
    )
    from openstef_models.transforms.general import Imputer, NaNDropper, Scaler
    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        LagsAdder,
    )
    from openstef_models.transforms.postprocessing import QuantileSorter

    hyperparams = LGBMHyperParams(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
    )

    model = ForecastingModel(
        forecaster=LGBMForecaster(hyperparams=hyperparams),
        preprocessing=[
            DatetimeFeaturesAdder(),
            CyclicFeaturesAdder(),
            LagsAdder(lags=[1, 2, 24, 48]),
            Imputer(),
            NaNDropper(),
            Scaler(),
        ],
        postprocessing=[QuantileSorter()],
        # Exclude the first 48 rows from training because LagsAdder
        # introduces NaNs for the lag-48 window.
        cutoff_history=48,
    )

    model.fit(train_dataset)
    forecast = model.predict(input_dataset)

.. note::

   The ``cutoff_history`` parameter is important when using lag-based transforms.
   A ``LagsAdder`` with ``lags=[48]`` leaves the first 48 rows of the training
   dataset with NaN lag values. Setting ``cutoff_history=48`` tells
   ``ForecastingModel`` to exclude those rows from the training matrix so the
   model never sees incomplete lag windows.

Hyperparameters as Pydantic models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because hyperparameter classes inherit from Pydantic's ``BaseModel`` (via
``openstef_core.mixins.HyperParams``), they can be serialised to and from JSON
without any extra code:

.. code-block:: python

    import json
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostHyperParams

    params = XGBoostHyperParams(n_estimators=500, max_depth=7, learning_rate=0.03)

    # Serialise for storage alongside a trained model artefact
    params_json = params.model_dump_json()

    # Reconstruct from stored JSON
    restored = XGBoostHyperParams.model_validate(json.loads(params_json))

----

The Explainability Layer
------------------------

Understanding *why* a model made a particular forecast is as important as the forecast
itself, especially in regulated energy markets. ``openstef-models`` provides two
complementary mixin classes in ``openstef_models.explainability.mixins``:

``ExplainableForecaster``
    Adds a ``feature_importances`` property that returns a ``pd.DataFrame`` indexed by
    feature name, with quantiles as columns. It also provides a
    ``plot_feature_importances()`` method that delegates to the built-in
    ``FeatureImportancePlotter`` to produce an interactive Plotly treemap — no
    external visualisation library required.

``ContributionsMixin``
    Adds a ``predict_contributions()`` method that returns a ``TimeSeriesDataset``
    containing per-sample, per-feature contribution scores (SHAP values or equivalent,
    depending on the underlying model). This lets you answer not just "which features
    matter overall?" but "which features drove *this specific* forecast point?"

Both ``XGBoostForecaster`` and ``LGBMForecaster`` implement both mixins, so they
support the full explainability surface out of the box.

Accessing feature importances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # After fitting a ForecastingModel that wraps an ExplainableForecaster:
    importances = model.forecaster.feature_importances
    # Returns a DataFrame: index = feature names, columns = quantiles (e.g. Q50)
    print(importances.sort_values("Q50", ascending=False).head(10))

    # Interactive treemap — returns a plotly Figure, display in a notebook or save
    fig = model.forecaster.plot_feature_importances()
    fig.show()

Per-sample contributions
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Requires a forecaster that implements ContributionsMixin (e.g. LGBMForecaster)
    contributions = model.forecaster.predict_contributions(input_dataset)
    # contributions is a TimeSeriesDataset; each column is a feature,
    # each row is a forecast timestamp, values are SHAP contributions.
    contributions_df = contributions.select_version().data
    print(contributions_df.head())

The ``predict_contributions`` path is also surfaced at the ``ForecastingModel`` level,
so you do not need to reach into the inner forecaster manually:

.. code-block:: python

    contributions = model.predict_contributions(input_dataset)

.. note::

   ``predict_contributions`` raises ``NotImplementedError`` for forecasters that do
   not implement ``ContributionsMixin`` (e.g. ``MedianForecaster``). Check
   ``isinstance(model.forecaster, ContributionsMixin)`` before calling it if you are
   writing generic code that works with multiple model types.

----

Compositional Design Summary
-----------------------------

The three layers form a clean dependency hierarchy:

- **Transforms** depend only on ``openstef-core`` data types — they are pure
  data-processing components with no model knowledge.
- **Forecasters** depend on transforms (for input preparation) and on
  ``openstef-core`` interfaces — they implement the statistical learning.
- **Explainability mixins** are orthogonal to the forecaster hierarchy; they are
  composed in via multiple inheritance, so any forecaster can opt in without changing
  its core logic.

This design means you can swap a ``LGBMForecaster`` for an ``XGBoostForecaster``
without touching the preprocessing pipeline, add a new domain transform without
modifying any model code, and add explainability to a custom forecaster by simply
inheriting from the appropriate mixin.

For backtesting a trained ``ForecastingModel`` at scale, see :doc:`beam`, which
provides the evaluation harness built around these model objects.