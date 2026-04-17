Reliability and Fallback Strategies
====================================

In production energy forecasting, things go wrong. Meters stop reporting, weather
feeds deliver stale data, a model trained weeks ago encounters conditions it has never
seen, or an upstream pipeline simply times out. This page describes how OpenSTEF's
library components help you detect these failure modes early and degrade gracefully
rather than silently producing bad forecasts.

For background on what a forecast actually contains, see
:doc:`forecasting_basics`. For how uncertainty is expressed in the output, see
:doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Data Quality Checks
-------------------

Bad input data is the most common source of forecast failures. OpenSTEF provides
three validation transforms in ``openstef_models.transforms.validation`` that you
can compose into any preprocessing pipeline.

**Completeness checking**

``CompletenessChecker`` measures the fraction of non-missing values across your
input features and raises ``InsufficientlyCompleteError`` if that fraction falls
below a configurable threshold. By default the threshold is 0.5 (50 %), but you
can tighten or loosen it per deployment, and you can assign per-column weights so
that a missing weather temperature column counts more heavily than a missing
secondary sensor.

.. code-block:: python

    from datetime import timedelta
    import numpy as np
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.transforms.validation import CompletenessChecker

    data = pd.DataFrame(
        {
            "load": [100.0, np.nan, 105.0, np.nan],
            "temperature": [12.0, 13.0, np.nan, np.nan],
            "radiation": [np.nan, np.nan, np.nan, np.nan],
        },
        index=pd.date_range("2024-01-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    # Require at least 60 % of values to be present,
    # weighting load more heavily than weather features.
    checker = CompletenessChecker(
        completeness_threshold=0.6,
        weights={"load": 3.0, "temperature": 1.0, "radiation": 1.0},
    )

    try:
        checker.transform(dataset)
    except InsufficientlyCompleteError as exc:
        print(f"Data too sparse to forecast reliably: {exc}")
        # trigger fallback logic here

The weighted completeness score lets you express domain knowledge: a missing load
measurement is far more damaging than a missing secondary weather variable.

**Flatline detection**

A meter that is stuck reporting the same value is arguably worse than a meter that
reports nothing at all, because the data *looks* valid. ``FlatlineChecker`` detects
when a load column has been constant for longer than a configurable duration and
raises ``FlatlinerDetectedError``.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import FlatlineChecker

    data = pd.DataFrame(
        {"load": [200.0, 200.0, 200.0, 200.0, 200.0]},
        index=pd.date_range("2024-01-01", periods=5, freq="1h"),
    )
    dataset = TimeSeriesDataset(data, timedelta(hours=1))

    checker = FlatlineChecker(
        flatliner_threshold=timedelta(hours=3),
        detect_non_zero_flatliner=True,
        relative_tolerance=1e-5,
    )

    # error_on_flatliner=True by default; set False to log-and-continue instead
    checker.fit_transform(dataset)

Setting ``detect_non_zero_flatliner=True`` is important for substations that carry
a constant base load — without it, only zero-value flatlines are caught.

**Input consistency checking**

``InputConsistencyChecker`` ensures that the features present at inference time
match those seen during training. It logs warnings for unexpected extra columns and
raises an error if required columns are absent. This catches the common production
problem where an upstream data source is renamed or removed after a model was
trained.

.. code-block:: python

    from openstef_models.transforms.validation import InputConsistencyChecker

    checker = InputConsistencyChecker()
    checker.fit(training_dataset)   # records expected feature names

    # Later, at inference time:
    checker.transform(live_dataset)  # raises if required columns are missing

Imputing Missing Values
-----------------------

When data is incomplete but still above your completeness threshold, imputation
fills the gaps so that the primary model can run. OpenSTEF's ``Imputer`` transform
supports several strategies, from a simple column mean (``"mean"``) to a fully
iterative Bayesian imputer that uses other features as predictors.

The iterative strategy is more accurate but slower; for real-time inference with
tight latency budgets the ``"mean"`` or ``"median"`` strategies are usually
sufficient. The ``fill_future_values`` parameter controls whether the imputer is
also allowed to fill values in the forecast horizon — by default it does not, to
preserve time-series integrity.

.. note::

   Imputation is a best-effort measure. If a critical feature such as the load
   target itself is missing for the entire training window,
   ``InsufficientlyCompleteError`` will still be raised after the imputer runs,
   because there is nothing meaningful left to train on.

The Base-Case Forecaster as a Fallback
---------------------------------------

When the primary model cannot produce a forecast — because data quality checks
fail, because the model is not yet trained, or because an exception escapes the
pipeline — OpenSTEF provides ``BaseCaseForecaster`` as a principled fallback. It
repeats the most recent weekly pattern from historical data rather than returning
zeros or ``NaN``.

The forecaster uses two configurable lag windows:

- **Primary lag** (default: 7 days) — the most recent week of observations is
  repeated forward.
- **Fallback lag** (default: 14 days) — used automatically when the primary lag
  window contains missing data.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.forecaster import Forecaster
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    fallback_model = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

Because ``BaseCaseForecaster`` requires no trained weights, it can be instantiated
at any time and used immediately. Confidence intervals are derived from the hourly
standard deviation of the repeated base pattern, so the output still carries
meaningful uncertainty bounds — see :doc:`quantiles_and_confidence` for how to
interpret them.

Wiring Fallback Logic Into Your Application
--------------------------------------------

OpenSTEF does not enforce a single fallback architecture — it is a library, and
the orchestration is yours to design. The pattern used in production systems is
straightforward: wrap the primary inference call in a ``try/except`` block that
catches the exceptions OpenSTEF raises, then delegate to the fallback model.

.. code-block:: python

    from openstef_core.exceptions import (
        InsufficientlyCompleteError,
        NotFittedError,
    )

    def produce_forecast(primary_model, fallback_model, dataset):
        """Run primary model with automatic fallback on known failure modes."""
        try:
            return primary_model.predict(dataset)
        except InsufficientlyCompleteError:
            # Input data too sparse for the primary model
            return fallback_model.predict(dataset)
        except NotFittedError:
            # Primary model has not been trained yet (e.g., cold start)
            return fallback_model.predict(dataset)
        except Exception as exc:
            # Unexpected failure — log and fall back rather than crash
            import logging
            logging.getLogger(__name__).error(
                "Primary model failed unexpectedly, using fallback",
                exc_info=exc,
            )
            return fallback_model.predict(dataset)

This pattern keeps the fallback transparent to the caller: the return type is
identical regardless of which model produced the forecast. Downstream consumers
need not know that a fallback occurred, though you should record it in your
observability stack.

Model Staleness
---------------

A model trained on summer data will perform poorly in winter. OpenSTEF does not
automatically retrain models on a schedule — that is the responsibility of your
MLOps infrastructure — but the library gives you the building blocks to detect
staleness and act on it.

The most direct signal is the training cut-off timestamp stored with the fitted
model. Compare it against the current wall-clock time and trigger a retraining
pipeline or switch to the base-case forecaster if the gap exceeds your tolerance:

.. code-block:: python

    from datetime import datetime, timedelta, timezone

    MAX_MODEL_AGE = timedelta(days=7)

    def is_model_stale(model) -> bool:
        """Return True if the model was trained more than MAX_MODEL_AGE ago."""
        trained_at = getattr(model, "trained_at", None)
        if trained_at is None:
            return True  # no training timestamp — treat as stale
        age = datetime.now(tz=timezone.utc) - trained_at
        return age > MAX_MODEL_AGE

    if is_model_stale(primary_model):
        forecast = fallback_model.predict(dataset)
    else:
        forecast = primary_model.predict(dataset)

A complementary approach is to monitor forecast residuals in production. When the
rolling mean absolute error of recent forecasts drifts above a threshold, that is
a strong signal that the model has drifted from reality even if it was trained
recently. This kind of monitoring sits outside OpenSTEF itself but pairs naturally
with the structured exceptions and validation outputs the library provides.

Composing Checks Into a Robust Pipeline
-----------------------------------------

In practice, the validation transforms, imputer, primary model, and fallback model
are composed into a single callable that your scheduler invokes. A minimal but
production-representative structure looks like this:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    def run_forecast_pipeline(raw_dataset, primary_model, fallback_model):
        # 1. Structural validation — are the right columns present?
        consistency_checker = InputConsistencyChecker()
        consistency_checker.fit(primary_model.training_dataset)

        # 2. Quality checks — is the data trustworthy?
        completeness_checker = CompletenessChecker(completeness_threshold=0.5)
        flatline_checker = FlatlineChecker(
            flatliner_threshold=timedelta(hours=24),
            detect_non_zero_flatliner=True,
        )

        try:
            dataset = consistency_checker.transform(raw_dataset)
            dataset = completeness_checker.transform(dataset)
            dataset = flatline_checker.fit_transform(dataset)
            return primary_model.predict(dataset)
        except InsufficientlyCompleteError:
            return fallback_model.predict(raw_dataset)

.. note::

   The ``FlatlineChecker`` accepts ``error_on_flatliner=False`` if you prefer to
   log the anomaly and continue rather than raise. This is useful when the
   flatlining column is a secondary feature rather than the load target itself.

Summary
-------

Reliable production forecasting with OpenSTEF rests on three layers:

- **Detect** bad data early using ``CompletenessChecker``, ``FlatlineChecker``,
  and ``InputConsistencyChecker`` before it reaches the model.
- **Degrade gracefully** by catching ``InsufficientlyCompleteError`` and
  ``NotFittedError`` and routing to ``BaseCaseForecaster``, which always produces
  a physically plausible forecast with uncertainty bounds.
- **Monitor staleness** by tracking model training timestamps and forecast
  residuals, and retraining or switching to the base-case model when drift is
  detected.

Because OpenSTEF is a library, each of these layers is independently composable.
You can adopt only the pieces that fit your existing infrastructure and leave the
orchestration to your own application code.