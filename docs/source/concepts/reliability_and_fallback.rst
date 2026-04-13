Reliability and Fallback Strategies
====================================

In production energy forecasting, things go wrong: meters stop reporting, weather
feeds deliver stale data, trained models drift out of relevance, or upstream systems
fail entirely. OpenSTEF is designed as a library that gives you the building blocks
to handle these situations gracefully, rather than silently producing bad forecasts
or crashing outright. This page covers the practical patterns for keeping your
forecasting pipeline robust: detecting bad or missing data before it reaches a model,
recognising when a model has grown too old to trust, and falling back to simpler
strategies when the primary approach cannot run.

For background on how forecasts are generated in the first place, see
:doc:`forecasting_basics`. For details on probabilistic outputs and confidence
intervals, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Layered fallback chain — primary ML model → base-case forecaster → last-known-good, with data validation gates at each transition]


Data Validation Before Forecasting
------------------------------------

The most common source of forecast failures is not a broken model — it is bad input
data. OpenSTEF provides three validation transforms in
``openstef_models.transforms.validation`` that you can insert into any pipeline to
catch problems early.

**CompletenessChecker** measures what fraction of expected values are actually
present. If the completeness score falls below the configured threshold, it raises
``InsufficientlyCompleteError`` rather than letting a half-empty dataset silently
degrade forecast quality:

.. code-block:: python

    from datetime import timedelta
    import numpy as np
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    data = pd.DataFrame(
        {
            "radiation":    [100, np.nan, np.nan, np.nan],
            "temperature":  [20,  np.nan, 24,     np.nan],
            "wind_speed":   [np.nan, np.nan, np.nan, np.nan],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    checker = CompletenessChecker()
    try:
        checker.transform(dataset)
    except Exception as exc:
        # InsufficientlyCompleteError: The dataset is not sufficiently complete.
        # Completeness: 0.25
        print(f"Data quality gate triggered: {exc}")
        # → route to fallback here

**FlatlineChecker** detects *flatliner* patterns — runs of identical consecutive
values that typically indicate a stuck sensor or a feed that has stopped updating.
Unlike a gap in the data, a flatline looks superficially complete but carries no
real information. The checker exposes a ``detect_ongoing_flatliner`` method you can
call on a live series to decide whether the most recent measurements are trustworthy
before committing to a forecast:

.. code-block:: python

    from openstef_models.transforms.validation import FlatlineChecker

    checker = FlatlineChecker(
        load_column="load",
        flatliner_threshold=6,       # consecutive identical readings to trigger
        detect_non_zero_flatliner=True,
        error_on_flatliner=False,    # warn rather than raise, so pipeline continues
    )

**InputConsistencyChecker** guards against a subtler failure mode: the feature set
available at inference time no longer matches what the model was trained on. It fits
on the training feature schema and then validates every subsequent dataset against
that schema, logging warnings and removing unexpected columns rather than letting
mismatched inputs corrupt predictions silently.

These three transforms compose naturally. The ``EnsembleForecastingWorkflowConfig``
wires them together automatically in its internal preprocessing chain, but you can
also use them individually in custom pipelines.


The Base-Case Forecaster as a Fallback
----------------------------------------

When the primary ML model cannot run — because data quality checks fail, because
the model has not yet been trained, or because an upstream dependency is
unavailable — you need something to fill the gap. OpenSTEF ships a
``BaseCaseForecaster`` for exactly this purpose.

The base-case model is deliberately simple: it repeats the most recent week of
historical load data, using weekly periodicity as its sole assumption. This is a
well-known property of energy consumption, and it produces forecasts that are
wrong in detail but credible in shape. The model also computes confidence intervals
from hourly standard deviations of the repeated pattern, so downstream consumers
still receive probabilistic output rather than a bare point forecast.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),   # use last week
            fallback_lag=timedelta(days=14), # fall back to two weeks ago
        ),
    )

The ``primary_lag`` / ``fallback_lag`` design means the base-case forecaster has its
own internal fallback: if the most recent seven days of history are unavailable, it
reaches back fourteen days instead. This two-level design is intentional — a single
point of failure in the historical feed should not prevent the fallback from
functioning.

A practical integration pattern wraps the primary forecast call in a try/except and
routes to the base-case forecaster on any ``InsufficientlyCompleteError``:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    def forecast_with_fallback(primary_model, fallback_model, dataset):
        """Attempt primary forecast; degrade to base-case on data quality failure."""
        try:
            return primary_model.predict(dataset)
        except InsufficientlyCompleteError as exc:
            import logging
            logging.warning(
                "Primary forecast aborted due to incomplete data (%s). "
                "Falling back to base-case forecaster.",
                exc,
            )
            return fallback_model.predict(dataset)

.. note::

   The base-case forecaster is not a substitute for a well-trained model — it is a
   safety net. Monitor how often your pipeline activates it; a rising fallback rate
   is an early warning of a data feed problem or a model that needs retraining.


Model Staleness and the Reuse Policy
--------------------------------------

A trained model that was accurate six months ago may no longer be appropriate today.
Seasonal shifts, changes in the grid, new generation assets, or demand-side
interventions can all cause a model to drift. OpenSTEF addresses this through the
``model_max_age`` parameter in ``EnsembleForecastingWorkflowConfig``, which sets an
upper bound on how old a stored model can be before it is considered stale and
retraining is forced:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
    )

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        horizons=[...],
        quantiles=[...],
        # Reject any stored model older than 30 days
        model_max_age=timedelta(days=30),
        # Allow reuse of a recent model if it still performs well
        model_reuse_enable=True,
        # Penalise the old model's metric to bias selection toward fresh models
        model_selection_old_model_penalty=1.2,
        model_selection_metric=("q0.5", "R2", "higher_is_better"),
    )

The ``model_selection_old_model_penalty`` parameter is worth understanding: when
comparing a freshly trained model against a stored one, the stored model's
performance metric is divided by this factor before comparison. A value of ``1.2``
means the old model must outperform the new one by at least 20 % to be retained.
This deliberately biases the system toward retraining, accepting a small performance
cost in exchange for models that stay current.

When ``model_reuse_enable=False`` the workflow always retrains from scratch,
which is appropriate for batch pipelines where compute cost is not a concern and
freshness is paramount.


Handling Gaps in Training Data
--------------------------------

Data gaps are inevitable in long-running production systems. OpenSTEF's training
pipeline handles them defensively: rows with ``NaN`` target values are dropped
before fitting, and if *all* target rows are ``NaN`` after this step, training raises
``InsufficientlyCompleteError`` rather than fitting a model on empty data:

.. code-block:: python

    # The pipeline raises InsufficientlyCompleteError rather than
    # fitting a model with no valid targets.
    #
    # In your orchestration layer, catch this and either:
    #   1. Extend the training window to find more data, or
    #   2. Skip retraining and retain the previous model version.

    from openstef_core.exceptions import InsufficientlyCompleteError

    try:
        workflow.fit(training_data)
    except InsufficientlyCompleteError:
        logging.error(
            "Training aborted: no valid target values in the supplied window. "
            "Retaining previous model version."
        )
        # continue using the previously stored model

For feature columns (as opposed to the target), gaps are handled differently.
Missing feature values are imputed during preprocessing rather than causing an
outright failure, because a forecast with imputed weather data is almost always
preferable to no forecast at all. The ``InputConsistencyChecker`` ensures that
imputation does not introduce columns the model has never seen.


Putting It Together: A Layered Reliability Strategy
------------------------------------------------------

Production experience with energy forecasting systems suggests a three-layer
reliability architecture:

1. **Validate inputs early.** Run ``CompletenessChecker``, ``FlatlineChecker``, and
   ``InputConsistencyChecker`` at the boundary where data enters your pipeline.
   Fail fast with a clear error rather than propagating bad data into a model.

2. **Degrade gracefully.** Catch ``InsufficientlyCompleteError`` and route to the
   ``BaseCaseForecaster``. Emit a structured log event so that operations teams
   can distinguish a planned fallback from an unexpected failure.

3. **Enforce model freshness.** Set ``model_max_age`` to match your domain's rate
   of change. For substations with stable load profiles, 30–90 days is common.
   For assets with rapidly changing behaviour (e.g., substations serving new EV
   charging infrastructure), shorter windows are appropriate.

.. note::

   Instrument your fallback rate as an operational metric. If the base-case
   forecaster activates more than a few percent of the time in normal operation,
   investigate the root cause rather than treating fallback as a steady state.

The validation transforms and the base-case forecaster are independent library
components — you do not need to use the full ensemble workflow to benefit from them.
They can be composed into any custom pipeline built on OpenSTEF's core abstractions.

For guidance on the features that feed into these models and how missing weather
data is handled upstream, see :doc:`feature_engineering`.