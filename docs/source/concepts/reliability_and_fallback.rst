Reliability and Fallback Strategies
====================================

In production energy forecasting, things go wrong. Sensors fail, upstream data
pipelines stall, models encounter inputs they were never trained on, and
historical data arrives late or corrupted. A forecasting system that simply
crashes or returns ``NaN`` in these situations is not production-ready.

This page covers the reliability patterns built into OpenSTEF and the
strategies you should adopt when integrating the library into a production
system: how to detect bad or missing data before it reaches a model, how to
fall back gracefully when a primary model cannot produce a forecast, and how to
recognise when a model has grown stale and needs retraining.

.. note::

   This page focuses on reliability mechanics. For background on what
   OpenSTEF forecasts and why they are probabilistic, see
   :doc:`forecasting_basics` and :doc:`quantiles_and_confidence`.

**[DIAGRAM: Reliability decision flow — data arrives → validation checks (completeness, flatline, consistency) → pass: primary model forecast → fail: fallback to BaseCaseForecaster → staleness check runs in parallel → triggers retraining if model age exceeds threshold]**

----

Data Validation Before Forecasting
------------------------------------

The most common source of production failures is not a broken model — it is
bad input data reaching a model that was never designed to handle it. OpenSTEF
provides three composable validation transforms in
``openstef_models.transforms.validation`` that you should apply as the first
stage of any inference pipeline.

**Completeness checking**

``CompletenessChecker`` calculates a weighted completeness score across the
columns of a ``TimeSeriesDataset`` and raises
``InsufficientlyCompleteError`` if the score falls below a configurable
threshold. The default threshold is 0.5 (50 % of values must be non-null),
but you can tighten or loosen this per deployment:

.. code-block:: python

   from datetime import timedelta
   import numpy as np
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_core.exceptions import InsufficientlyCompleteError

   data = pd.DataFrame(
       {
           "load": [100.0, np.nan, 105.0, np.nan],
           "temperature": [12.0, 13.0, np.nan, 14.0],
       },
       index=pd.date_range("2024-01-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   # Require at least 70 % completeness, weight load more heavily
   checker = CompletenessChecker(
       completeness_threshold=0.7,
       weights={"load": 2.0, "temperature": 1.0},
   )

   try:
       checker.transform(dataset)
   except InsufficientlyCompleteError as exc:
       print(f"Data too sparse to forecast reliably: {exc}")
       # → trigger fallback here

The ``weights`` parameter lets you express domain knowledge: a missing load
measurement is more damaging than a missing weather feature, so you can penalise
it more heavily in the completeness score.

**Flatline detection**

A sensor that is stuck reporting the same value is arguably worse than a sensor
reporting ``NaN``, because the data *looks* valid. ``FlatlineChecker`` detects
runs of identical values exceeding a configurable duration and raises
``FlatlinerDetectedError``:

.. code-block:: python

   from openstef_models.transforms.validation import FlatlineChecker
   from openstef_core.exceptions import FlatlinerDetectedError

   flatline_check = FlatlineChecker(
       flatliner_threshold=timedelta(hours=2),
       detect_non_zero_flatliner=True,
       relative_tolerance=1e-5,
   )

   try:
       flatline_check.fit_transform(dataset)
   except FlatlinerDetectedError as exc:
       print(f"Sensor appears stuck: {exc}")

Setting ``detect_non_zero_flatliner=True`` catches the common case where a
meter is frozen at a non-zero reading — a failure mode that zero-only detection
misses entirely.

**Input consistency checking**

When a model is trained on a fixed feature set, inference data must match that
set exactly. ``InputConsistencyChecker`` is fitted during training and then
applied at inference time to verify that all expected columns are present and
that no unexpected columns silently alter downstream behaviour:

.. code-block:: python

   from openstef_models.transforms.validation import InputConsistencyChecker

   consistency_check = InputConsistencyChecker()
   consistency_check.fit(training_dataset)

   # At inference time — logs warnings for extra columns, raises on missing ones
   validated = consistency_check.transform(inference_dataset)

This is particularly valuable when feature engineering pipelines evolve over
time and a model serialised months ago is still serving live traffic.

----

The BaseCaseForecaster: Your Safety Net
-----------------------------------------

When validation fails or a primary model raises an exception, you need
something to fill the gap. OpenSTEF ships ``BaseCaseForecaster`` — a
deliberately simple model that repeats the most recent weekly pattern — as a
production-grade fallback. It requires no training beyond the historical target
series and produces calibrated confidence intervals from hourly standard
deviations of that same history.

The forecaster uses a two-level lag strategy: it first tries to use data from
``primary_lag`` (default: 7 days ago) and falls back to ``fallback_lag``
(default: 14 days ago) when the primary window is unavailable. This means it
degrades gracefully even when recent history is itself incomplete.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   fallback_model = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

   fallback_model.fit(training_data)  # only needs the target column
   fallback_forecast = fallback_model.predict(forecast_data)

**[VISUALIZATION: Side-by-side comparison of a primary ML model forecast vs. BaseCaseForecaster fallback for the same 24-hour window, showing the fallback's wider confidence intervals and smoother weekly-repeat shape]**

The ``BaseCaseForecaster`` is intentionally not as accurate as a trained
gradient-boosted or neural model. Its value is *reliability*: it will always
produce a forecast as long as two weeks of historical data exist, and its
outputs are interpretable enough that operators can immediately understand what
they are looking at.

.. note::

   The ``BaseCaseForecaster`` also serves as a useful benchmark. If your
   primary model cannot consistently beat it, that is a signal to revisit
   feature engineering (see :doc:`feature_engineering`) or model selection.

----

Structuring a Fallback Pipeline
---------------------------------

The pattern used in production is straightforward: wrap primary model inference
in a try/except block, catch the exceptions that OpenSTEF's validation layer
raises, and delegate to the fallback. Logging the reason for each fallback is
essential for monitoring — silent fallbacks are invisible failures.

.. code-block:: python

   import logging
   from openstef_core.exceptions import (
       InsufficientlyCompleteError,
       FlatlinerDetectedError,
   )

   logger = logging.getLogger(__name__)

   def produce_forecast(primary_model, fallback_model, dataset, forecast_dataset):
       """Attempt primary forecast, fall back to base case on data quality failure."""
       try:
           # Run validation transforms first
           checker = CompletenessChecker(completeness_threshold=0.6)
           flatline = FlatlineChecker(flatliner_threshold=timedelta(hours=2))
           validated = checker.transform(dataset)
           validated = flatline.fit_transform(validated)

           return primary_model.predict(forecast_dataset), "primary"

       except (InsufficientlyCompleteError, FlatlinerDetectedError) as exc:
           logger.warning(
               "Falling back to base case forecaster. Reason: %s", exc
           )
           return fallback_model.predict(forecast_dataset), "fallback"

       except Exception as exc:
           logger.error(
               "Primary model raised unexpected error, using fallback. Error: %s",
               exc,
               exc_info=True,
           )
           return fallback_model.predict(forecast_dataset), "fallback"

The return value of ``"primary"`` or ``"fallback"`` should be recorded
alongside the forecast itself. Over time, the ratio of fallback forecasts to
primary forecasts is one of the most informative health metrics for a
production forecasting system.

**[DIAGRAM: Fallback pipeline sequence — validate dataset → CompletenessChecker → FlatlineChecker → InputConsistencyChecker → primary model predict → on exception: log reason + BaseCaseForecaster predict → emit forecast + source tag]**

----

Model Staleness Detection
---------------------------

A model trained six months ago on summer data will behave poorly in winter.
Unlike a crashed model, a stale model fails silently — it produces forecasts
that look plausible but are systematically wrong. Detecting staleness requires
comparing live forecast errors against a baseline.

OpenSTEF does not prescribe a single staleness metric, but the following
pattern is widely used in production deployments:

**Track rolling forecast error against the base case.** If your primary model's
mean absolute error over the last *N* days approaches or exceeds the
``BaseCaseForecaster``'s error over the same window, the primary model has
effectively stopped adding value and retraining should be triggered.

.. code-block:: python

   import pandas as pd

   def is_model_stale(
       primary_errors: pd.Series,
       fallback_errors: pd.Series,
       staleness_ratio: float = 1.2,
       window_days: int = 7,
   ) -> bool:
       """Return True if the primary model is performing close to the base case.

       Args:
           primary_errors: Absolute forecast errors from the primary model.
           fallback_errors: Absolute forecast errors from BaseCaseForecaster.
           staleness_ratio: Trigger retraining if primary MAE exceeds
               fallback MAE by less than this factor (default: 1.2 means
               primary must be at least ~17 % better than fallback).
           window_days: Rolling window over which to compute MAE.
       """
       cutoff = pd.Timestamp.now() - pd.Timedelta(days=window_days)
       recent_primary_mae = primary_errors[primary_errors.index >= cutoff].mean()
       recent_fallback_mae = fallback_errors[fallback_errors.index >= cutoff].mean()

       if recent_fallback_mae == 0:
           return False  # Cannot compute ratio

       ratio = recent_primary_mae / recent_fallback_mae
       return ratio > (1 / staleness_ratio)

   # Example usage
   if is_model_stale(primary_errors, fallback_errors):
       logger.warning("Primary model appears stale — scheduling retraining.")
       # trigger_retraining(model_id)

A complementary check is **model age**: if a model has not been retrained
within a configurable maximum age (e.g., 30 days), flag it for retraining
regardless of current error metrics. Concept drift in energy data — driven by
new solar installations, EV uptake, or building retrofits — can accumulate
gradually enough that error-based detection lags behind reality.

.. code-block:: python

   from datetime import datetime, timedelta, timezone

   def model_age_exceeds_limit(
       trained_at: datetime,
       max_age: timedelta = timedelta(days=30),
   ) -> bool:
       """Check whether a model has exceeded its maximum permitted age."""
       age = datetime.now(tz=timezone.utc) - trained_at
       return age > max_age

----

Handling Missing Features at Inference Time
---------------------------------------------

Even when the target load series is complete, individual feature columns —
weather forecasts, calendar flags, grid topology signals — may arrive late or
not at all. The ``InputConsistencyChecker`` will raise on missing required
columns, but you often want to impute rather than fall back entirely.

A practical hierarchy for missing feature handling:

- **Weather features**: Use the most recent available observation as a
  persistence forecast, or substitute climatological normals for the time of
  year. See :doc:`feature_engineering` for which weather features matter most.
- **Lag features**: The ``BaseCaseForecaster``'s two-level lag strategy
  (primary → fallback) is a direct implementation of this principle. If 7-day
  lag data is missing, use 14-day lag data.
- **Structural features** (e.g., grid capacity, connection type): These change
  rarely. Carry forward the last known value with a staleness warning rather
  than blocking the forecast.

The key principle is to be explicit: log every imputation, tag the forecast
with a data quality indicator, and never silently substitute zeros for missing
values in energy data (zero load is a physically meaningful state, not a
neutral fill value).

----

Summary
--------

Reliable production forecasting with OpenSTEF rests on three practices:

- **Validate early.** Use ``CompletenessChecker``, ``FlatlineChecker``, and
  ``InputConsistencyChecker`` as the first stage of every inference pipeline,
  before data reaches any model.
- **Always have a fallback.** Keep a fitted ``BaseCaseForecaster`` ready. It
  is not as accurate as a trained model, but it is always available and its
  outputs are interpretable.
- **Monitor for staleness.** Track rolling forecast error relative to the base
  case, enforce a maximum model age, and automate retraining triggers. Silent
  degradation is harder to recover from than an explicit failure.

For related topics, see :doc:`forecasting_basics` for an introduction to what
OpenSTEF forecasts, :doc:`quantiles_and_confidence` for how uncertainty is
expressed in fallback forecasts, and :doc:`meta_ensembles` for ensemble
approaches that can themselves improve resilience by combining multiple model
signals.