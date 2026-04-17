Reliability and Fallback Strategies
===================================

In production energy forecasting, models occasionally fail — training data arrives incomplete, a sensor goes offline, or a model trained weeks ago no longer reflects current grid behaviour. This page explains how OpenSTEF handles these situations: what exceptions signal trouble, how the ``BaseCaseForecaster`` provides a principled fallback, and how to build a graceful degradation strategy in your own pipeline.

For background on what forecasts represent and how uncertainty is expressed, see :doc:`quantiles_and_confidence`. For details on the features that feed these models, see :doc:`feature_engineering`.

Why Reliability Matters in Forecasting
---------------------------------------

A forecast that silently returns ``NaN`` — or worse, a confidently wrong number — is more dangerous than one that raises an explicit error. Production energy systems use forecasts to schedule balancing capacity, trigger demand-response actions, and settle imbalance costs. A missing or stale forecast at the wrong moment has real financial and operational consequences.

OpenSTEF addresses this through three complementary mechanisms:

- **Structured exceptions** that make failure modes explicit and catchable.
- **A ``BaseCaseForecaster``** that provides a statistically grounded fallback when the primary model cannot run.
- **Dataset validation** that catches data quality problems before they silently corrupt a forecast.

Structured Exceptions
----------------------

OpenSTEF defines a set of domain-specific exceptions in ``openstef_core.exceptions``. Catching these lets you distinguish between different failure modes and respond appropriately rather than swallowing a generic ``Exception``.

.. code-block:: python

    from openstef_core.exceptions import (
        InsufficientlyCompleteError,
        PredictError,
        ModelLoadingError,
        ModelNotFoundError,
        NotFittedError,
    )

The most important ones for reliability work are:

- ``InsufficientlyCompleteError`` — raised when a dataset does not meet the minimum completeness threshold required for training or prediction. This prevents a model from being trained on a dataset that is mostly gaps.
- ``PredictError`` — raised when the forecasting step itself fails, for example because required lag features are absent from the input.
- ``ModelLoadingError`` / ``ModelNotFoundError`` — raised when a persisted model cannot be retrieved from storage, signalling that no trained model is available for a given prediction unit.
- ``NotFittedError`` — raised when ``predict`` is called on a model that has never been fitted.
- ``SkipFitting`` — not an error, but a signal that re-training was evaluated and deliberately skipped (for example, because the existing model is recent enough).

Wrapping your pipeline calls in targeted ``except`` blocks lets you route each failure to the right recovery path:

.. code-block:: python

    from openstef_core.exceptions import (
        InsufficientlyCompleteError,
        ModelNotFoundError,
        PredictError,
    )
    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    def run_forecast_with_fallback(primary_pipeline, forecast_dataset):
        try:
            return primary_pipeline.predict(forecast_dataset)

        except (ModelNotFoundError, NotFittedError):
            # No trained model exists yet — use the base case
            print("No trained model available; falling back to BaseCaseForecaster.")
            return run_base_case(forecast_dataset)

        except InsufficientlyCompleteError as exc:
            # Input data is too sparse to trust
            print(f"Input data too incomplete for primary model: {exc}")
            return run_base_case(forecast_dataset)

        except PredictError as exc:
            # Model exists but prediction failed (e.g. missing features)
            print(f"Prediction failed: {exc}. Falling back.")
            return run_base_case(forecast_dataset)

    def run_base_case(forecast_dataset):
        forecaster = BaseCaseForecaster(
            quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
            horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
        )
        forecaster.fit(forecast_dataset)
        return forecaster.predict(forecast_dataset)

The Base Case Forecaster
-------------------------

``BaseCaseForecaster`` is OpenSTEF's built-in fallback model. It does not use a trained machine learning model at all — instead it repeats the most recent weekly pattern from historical data, which is a surprisingly robust baseline for energy load because load profiles are strongly periodic.

The logic is straightforward:

1. Take the last ``primary_lag`` days of historical target data (default: 7 days).
2. Repeat that window forward to cover the forecast horizon.
3. If the primary lag window contains gaps, fall back to ``fallback_lag`` (default: 14 days).
4. Compute per-hour standard deviations from the repeated window to produce confidence intervals.

.. note:: [DIAGRAM: Data flow showing historical load window → weekly repetition → forecast horizon, with primary_lag and fallback_lag annotated]

Because it only needs a recent slice of historical measurements, the ``BaseCaseForecaster`` can produce a forecast even when weather data, grid topology features, or other engineered features are unavailable. This makes it suitable as a last-resort fallback when the feature pipeline itself is degraded.

You can tune the lag windows if your load has a different dominant periodicity:

.. code-block:: python

    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    # For a site with strong daily (not weekly) periodicity
    daily_base_case = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=1),
            fallback_lag=timedelta(days=2),
        ),
    )

.. note::

   The ``BaseCaseForecaster`` is intentionally simple. Its value is not accuracy — it is *availability*. A forecast that is always present and roughly correct is more useful operationally than one that is sometimes perfect and sometimes absent.

Handling Missing and Bad Data
------------------------------

OpenSTEF validates datasets before they reach a model. The ``ForecastInputDataset`` and related classes enforce invariants such as sorted timestamps, consistent sampling intervals, and the presence of required columns. Violations raise ``TimeSeriesValidationError`` or ``MissingColumnsError`` early, before any computation occurs.

For completeness checking, the ``InsufficientlyCompleteError`` is raised when the fraction of non-null values in the target column falls below a configured threshold. This prevents training on a dataset that is mostly gaps, which would produce a model that has learned from imputed or interpolated values rather than real measurements.

A practical pattern is to check completeness explicitly before attempting to train, so you can log a meaningful diagnostic rather than catching an exception after the fact:

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset
    from openstef_core.exceptions import InsufficientlyCompleteError

    def assess_data_quality(df: pd.DataFrame, target_column: str) -> dict:
        """Return a simple quality report before committing to training."""
        total = len(df)
        non_null = df[target_column].notna().sum()
        completeness = non_null / total if total > 0 else 0.0

        gaps = df[target_column].isna()
        longest_gap = gaps.groupby((~gaps).cumsum()).sum().max() if gaps.any() else 0

        return {
            "completeness": completeness,
            "longest_gap_samples": int(longest_gap),
            "total_samples": total,
        }

    quality = assess_data_quality(raw_df, target_column="load_mw")
    print(f"Completeness: {quality['completeness']:.1%}, "
          f"longest gap: {quality['longest_gap_samples']} samples")

    if quality["completeness"] < 0.85:
        print("Data too sparse — skipping training, using base case.")
    else:
        # Proceed with normal training pipeline
        ...

.. note:: [VISUALIZATION: Bar chart showing completeness percentage per prediction unit, with a threshold line at 85%]

Model Staleness
----------------

A model that was accurate when trained can become stale as load patterns shift — new large consumers connect, seasonal behaviour changes, or the grid topology is reconfigured. OpenSTEF signals this through the ``SkipFitting`` exception, which is raised (not as an error, but as a control-flow signal) when the training pipeline determines that the current model is recent enough and re-training should be skipped.

In your own pipeline, you can implement a staleness check by tracking the model's training timestamp and comparing it against a maximum age threshold:

.. code-block:: python

    from datetime import datetime, timedelta, timezone
    from openstef_core.exceptions import SkipFitting

    MAX_MODEL_AGE = timedelta(days=7)

    def check_model_freshness(model_metadata: dict) -> None:
        """Raise SkipFitting if the model is recent enough, otherwise allow re-training."""
        trained_at = model_metadata.get("trained_at")
        if trained_at is None:
            return  # No metadata — always re-train

        age = datetime.now(tz=timezone.utc) - trained_at
        if age < MAX_MODEL_AGE:
            raise SkipFitting(
                f"Model trained {age.days}d {age.seconds // 3600}h ago, "
                f"within the {MAX_MODEL_AGE.days}-day threshold."
            )

    try:
        check_model_freshness(loaded_metadata)
        # Re-train
        pipeline.fit(training_dataset)
    except SkipFitting as reason:
        print(f"Re-training skipped: {reason}")
        # Use the existing model as-is

The inverse problem — a model that is *too old* and has not been caught by the above check — should be handled by your monitoring layer. A reasonable heuristic is to treat any model older than a configurable threshold as equivalent to ``ModelNotFoundError`` and route it to the base case fallback.

Graceful Degradation in Practice
----------------------------------

Putting the pieces together, a production-grade forecast pipeline typically implements a degradation ladder: each rung is tried in order, and the system falls back to the next rung only when the current one fails.

.. note:: [DIAGRAM: Degradation ladder showing: Primary ML model → Base case forecaster → Last known good forecast → Alert / manual intervention, with exception types annotated at each transition]

A concrete implementation of this pattern:

.. code-block:: python

    from openstef_core.exceptions import (
        InsufficientlyCompleteError,
        ModelLoadingError,
        ModelNotFoundError,
        NotFittedError,
        PredictError,
    )

    RECOVERABLE = (
        InsufficientlyCompleteError,
        ModelLoadingError,
        ModelNotFoundError,
        NotFittedError,
        PredictError,
    )

    def forecast_with_degradation(
        primary_pipeline,
        base_case_forecaster,
        forecast_dataset,
        last_known_good: dict | None = None,
    ):
        # Rung 1: primary ML model
        try:
            result = primary_pipeline.predict(forecast_dataset)
            return result, "primary"
        except RECOVERABLE as exc:
            print(f"[WARN] Primary model failed ({type(exc).__name__}): {exc}")

        # Rung 2: base case (weekly repetition)
        try:
            base_case_forecaster.fit(forecast_dataset)
            result = base_case_forecaster.predict(forecast_dataset)
            return result, "base_case"
        except Exception as exc:
            print(f"[WARN] Base case forecaster failed: {exc}")

        # Rung 3: last known good forecast
        if last_known_good is not None:
            print("[WARN] Returning last known good forecast.")
            return last_known_good, "last_known_good"

        # Rung 4: unrecoverable — alert and raise
        raise RuntimeError(
            "All forecast fallbacks exhausted. Manual intervention required."
        )

.. warning::

   Always log which rung of the degradation ladder was used, and expose this as a metric in your monitoring system. A base-case forecast that silently persists for days is a sign that the primary model pipeline needs attention.

Key Takeaways
--------------

- Use OpenSTEF's structured exceptions (``InsufficientlyCompleteError``, ``PredictError``, ``ModelNotFoundError``) to distinguish failure modes and route them to appropriate recovery paths.
- ``BaseCaseForecaster`` provides a statistically grounded fallback that requires only recent historical load data — no trained model, no weather features.
- Validate data completeness *before* training, not only by catching exceptions after the fact.
- Implement a degradation ladder with explicit rungs and log which rung is active at all times.
- Treat model staleness as a first-class concern: track training timestamps and enforce maximum model age thresholds.

For probabilistic aspects of fallback forecasts — including how the ``BaseCaseForecaster`` derives its confidence intervals from historical variance — see :doc:`quantiles_and_confidence`. For the feature pipeline that feeds the primary model, and what happens when individual features are missing, see :doc:`feature_engineering`.