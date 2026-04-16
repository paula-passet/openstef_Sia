Reliability and Fallback Strategies
====================================

Production energy forecasting systems must keep running even when things go wrong. Models become stale, input data arrives late or corrupted, and sensors flatline without warning. This page covers the reliability mechanisms built into OpenSTEF — data validation transforms, the ``BaseCaseForecaster`` fallback model, and the patterns used in real deployments to degrade gracefully rather than fail silently.

For background on what forecasts represent and how probabilistic outputs are structured, see :doc:`quantiles_and_confidence`. For details on the input features that feed these pipelines, see :doc:`feature_engineering`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Why Reliability Matters in Energy Forecasting
----------------------------------------------

A short-term load forecast that silently returns zeros, stale values, or ``NaN`` is often worse than no forecast at all. Grid operators and trading desks act on these numbers; a bad forecast that *looks* valid causes real operational harm. OpenSTEF addresses this at two levels:

- **Input validation** — detect and reject bad data before it reaches a model.
- **Graceful degradation** — when the primary model cannot produce a reliable forecast, fall back to a simpler but trustworthy baseline rather than propagating an error.

These two layers are complementary. Validation prevents garbage-in/garbage-out; fallback ensures the system keeps producing *something* useful even when validation catches a problem.

Data Validation Transforms
---------------------------

OpenSTEF ships three validation transforms in ``openstef_models.transforms.validation``. Each implements the ``TimeSeriesTransform`` interface, so they compose naturally into any pipeline.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

**CompletenessChecker** measures what fraction of expected values are actually present across the input columns. If the weighted completeness score falls below a configurable threshold (default 0.5), it raises ``InsufficientlyCompleteError``. You can weight columns differently to reflect their importance — for example, giving the target load column a higher weight than an auxiliary weather feature.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets.validated_datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import CompletenessChecker

    data = pd.DataFrame(
        {
            "load": [100.0, 102.0, np.nan, 105.0],
            "temperature": [15.0, np.nan, np.nan, 16.0],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    # Raise the threshold and weight load more heavily
    checker = CompletenessChecker(
        weights={"load": 2.0, "temperature": 1.0},
        completeness_threshold=0.7,
    )
    checker.transform(dataset)  # raises InsufficientlyCompleteError if too sparse

The ``columns`` parameter lets you restrict the check to a subset of columns, which is useful when some features are optional enrichments rather than hard requirements.

**FlatlineChecker** detects the common sensor failure mode where a measurement stream stops updating and repeats the same value indefinitely. This is distinct from missing data — the values are present, but they carry no information. The ``detect_ongoing_flatliner`` method inspects the tail of a series and returns ``True`` if the pattern is detected.

.. code-block:: python

    from openstef_models.transforms.validation import FlatlineChecker

    flatline_checker = FlatlineChecker()
    # Used as a transform in a pipeline; raises or flags on detection
    flatline_checker.transform(dataset)

In practice, a flatlined load signal is one of the most dangerous inputs for a forecasting model because it produces confident-looking but completely wrong predictions. Catching it early, before training or inference, prevents those predictions from reaching downstream consumers.

**InputConsistencyChecker** validates that the structure and feature set of incoming data matches what the model was fitted on. This guards against schema drift — situations where a data pipeline change silently drops or renames a column that the model depends on.

.. code-block:: python

    from openstef_models.transforms.validation import InputConsistencyChecker

    consistency_checker = InputConsistencyChecker()
    consistency_checker.fit(training_dataset)   # record expected schema at train time
    consistency_checker.transform(live_dataset) # validate at inference time

Fitting the checker on the training dataset and then calling ``transform`` on live data is the standard pattern. Any mismatch raises an error before the model ever sees the inconsistent input.

The BaseCaseForecaster: A Trustworthy Fallback
-----------------------------------------------

When validation fails, or when a primary model is unavailable (not yet trained, too old, or producing out-of-range outputs), OpenSTEF provides ``BaseCaseForecaster`` as a principled fallback. Rather than returning zeros or raising an unhandled exception, the system can switch to this model and continue operating.

``BaseCaseForecaster`` implements a weekly-periodicity assumption: energy load tends to repeat on a seven-day cycle, so last week's actuals are a reasonable proxy for this week's forecast. The model uses two lag windows:

- **Primary lag** (default: 7 days) — the main source of predictions.
- **Fallback lag** (default: 14 days) — used when primary lag data is unavailable, for example during the first week after a new meter is commissioned.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    # Standard configuration — mirrors a 7-day weekly pattern
    fallback_model = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
    )

    # If the primary lag window is shorter (e.g., sparse history),
    # adjust both lags accordingly
    fallback_model_custom = BaseCaseForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

Confidence intervals are derived from the hourly standard deviation of the repeated base-case data, so the model produces calibrated uncertainty estimates even in fallback mode. This means downstream consumers receive a full probabilistic forecast — not just a point estimate — regardless of which model is active.

.. note::

   ``BaseCaseForecaster`` is intentionally simple. Its value is not accuracy but *reliability*: it will always produce a forecast as long as at least two weeks of historical data exist, and its outputs are interpretable and auditable.

Model Staleness and When to Fall Back
--------------------------------------

A model trained weeks or months ago on a different load regime can be more dangerous than the naive baseline. OpenSTEF's production patterns treat model age as a first-class concern. The general rule applied in real deployments is:

- Track the training timestamp alongside every deployed model artifact.
- Define a maximum acceptable model age for each forecasting horizon (shorter horizons typically tolerate less staleness).
- At inference time, compare the current timestamp against the training timestamp and route to ``BaseCaseForecaster`` if the model is too old.

A minimal staleness guard looks like this:

.. code-block:: python

    from datetime import datetime, timedelta, timezone

    MAX_MODEL_AGE = timedelta(days=30)

    def get_forecaster(primary_model, training_timestamp):
        """Return primary model if fresh, otherwise fall back to base case."""
        model_age = datetime.now(tz=timezone.utc) - training_timestamp
        if model_age > MAX_MODEL_AGE:
            return BaseCaseForecaster(
                quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
                horizons=[LeadTime(timedelta(hours=1))],
            )
        return primary_model

This pattern keeps the fallback decision explicit and auditable. Logging which model was used for each forecast run makes it straightforward to diagnose periods of degraded accuracy in retrospect.

Putting It Together: A Defensive Inference Pattern
----------------------------------------------------

The following sketch combines validation and fallback into a single inference function. It is intentionally simplified — real deployments will integrate with a model registry and a structured logging framework — but it illustrates the layered approach:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    def run_forecast(dataset, primary_model, training_timestamp):
        """
        Run a forecast with validation and automatic fallback.

        Returns a forecast dataset and a flag indicating whether
        the fallback model was used.
        """
        used_fallback = False

        # Layer 1: validate input data
        try:
            CompletenessChecker(completeness_threshold=0.6).transform(dataset)
            FlatlineChecker().transform(dataset)
            InputConsistencyChecker().transform(dataset)
        except InsufficientlyCompleteError as exc:
            # Log and proceed to fallback; do not re-raise
            print(f"Input validation failed: {exc}. Switching to base case.")
            used_fallback = True

        # Layer 2: check model freshness
        model = get_forecaster(primary_model, training_timestamp)
        if model is not primary_model:
            used_fallback = True

        # Layer 3: produce forecast
        forecast = model.predict(dataset)
        return forecast, used_fallback

.. warning::

   Never suppress validation errors without logging them. Silent fallback is a reliability feature; silent failure is a reliability hazard. Always emit a structured log entry or metric when the fallback path is taken so that operations teams can investigate the root cause.

Lessons from Production
------------------------

A few patterns that emerge consistently from real deployments:

**Separate validation from imputation.** It is tempting to fill missing values automatically and continue. This works for occasional gaps (a few missing intervals in an otherwise complete series) but masks systematic problems like a broken data pipeline. Use ``CompletenessChecker`` to enforce a hard floor, and only impute within that floor.

**Make fallback observable.** The most useful operational metric is not forecast accuracy in isolation but the *fraction of forecasts served by the fallback model*. A sudden spike in fallback usage is an early warning of upstream data problems, even before accuracy degrades visibly.

**Test the fallback path explicitly.** In integration tests, deliberately inject incomplete or flatlined data and assert that the system returns a valid ``BaseCaseForecaster`` output rather than an exception. Fallback paths that are never exercised in tests tend to be broken when they are needed most.

**Align lag windows with your retraining cadence.** If models are retrained weekly, a 30-day staleness threshold means a model could be used for up to four weeks after training. Ensure the ``BaseCaseForecaster`` lag windows cover at least that span of history so the fallback always has data to work with.

Related Topics
--------------

- :doc:`forecasting_basics` — how the primary forecasting pipeline works before any of these fallback mechanisms are needed.
- :doc:`quantiles_and_confidence` — understanding the probabilistic outputs that both the primary model and ``BaseCaseForecaster`` produce.
- :doc:`feature_engineering` — the input features whose quality the validation transforms are protecting.