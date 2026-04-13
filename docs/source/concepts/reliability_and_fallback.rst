Production Reliability and Fallback Strategies
===============================================

Energy forecasting systems must keep producing useful outputs even when things go wrong — a model
fails to load, incoming sensor data is corrupted, or a trained model has grown stale. This page
explains how OpenSTEF is designed to support graceful degradation in production, and how you can
build resilience into your own forecasting pipelines using the library's built-in tools.

For background on what forecasts are and why they matter, see :doc:`forecasting_basics`. For
details on the probabilistic outputs these systems produce, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Reliability layers — data validation → model health check → primary forecast → fallback forecast → alert/escalation]

Why Reliability Matters in Production
--------------------------------------

A short-term energy forecast is only useful if it arrives on time and with a reasonable level of
accuracy. Grid operators and energy traders act on these numbers; a silent failure — where a
pipeline produces no output or a subtly wrong one — can be worse than a loudly failing one.
Production forecasting systems therefore need to answer three questions continuously:

- Is the input data good enough to trust?
- Is the trained model still valid?
- If either answer is "no", what should the system do instead?

OpenSTEF addresses all three through validation transforms, model configuration parameters, and
the ``BaseCaseForecaster`` fallback model.

Data Validation Before Forecasting
------------------------------------

Before a forecast is generated, OpenSTEF runs the incoming data through a set of validation
transforms. These are composable ``TimeSeriesTransform`` objects that can be inserted into any
pipeline. Three are provided out of the box:

- **CompletenessChecker** — raises ``InsufficientlyCompleteError`` if too many values are missing.
- **FlatlineChecker** — detects sensors that have frozen (repeated identical readings), which often
  indicates a failed meter or communication fault.
- **InputConsistencyChecker** — ensures the feature columns at inference time match those seen
  during training, catching schema drift early.

The ``EnsembleForecastingWorkflowConfig`` includes these checks by default. You can also use them
directly when building a custom pipeline:

.. code-block:: python

    from datetime import timedelta

    import numpy as np
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
    )

    # Simulate incoming forecast input with gaps
    index = pd.date_range("2025-06-01", periods=96, freq="15min")
    data = pd.DataFrame(
        {
            "load": np.random.normal(100, 10, 96),
            "temperature": np.where(np.arange(96) % 4 == 0, np.nan, 20.0),
        },
        index=index,
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    completeness_check = CompletenessChecker()
    flatline_check = FlatlineChecker(load_column="load", error_on_flatliner=False)

    try:
        dataset = completeness_check.transform(dataset)
        dataset = flatline_check.transform(dataset)
    except InsufficientlyCompleteError as exc:
        # Log and route to fallback — see next section
        print(f"Data quality too low to forecast: {exc}")

Setting ``error_on_flatliner=False`` on ``FlatlineChecker`` means the check logs a warning rather
than raising an exception. This is appropriate when you want to continue forecasting with a
degraded signal rather than halt entirely — a common production trade-off.

.. note::

   ``CompletenessChecker`` accepts a ``columns`` parameter so you can weight critical features
   (such as the load target itself) more heavily than auxiliary weather inputs when calculating
   the completeness score.

The BaseCaseForecaster: A Reliable Fallback
--------------------------------------------

When data quality is too low or a primary model cannot be loaded, you need a fallback that is
simple, robust, and requires minimal input. OpenSTEF provides ``BaseCaseForecaster`` for exactly
this purpose.

The model exploits the strong weekly periodicity of energy load: it takes the last seven days of
historical load data and repeats that pattern across the forecast horizon. If the seven-day window
itself contains gaps, it falls back to the fourteen-day-ago window. Confidence intervals are
derived from the hourly standard deviation of the repeated base case, so the output remains
probabilistic even in fallback mode.

.. code-block:: python

    from datetime import timedelta

    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    # Standard fallback configuration
    fallback_model = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

The ``BaseCaseForecaster`` intentionally has no learned parameters — it cannot be "wrong" in the
model-training sense, which makes it a safe last resort. Its accuracy degrades gracefully around
holidays and unusual demand events, but it will never produce nonsensical negative loads or
unbounded spikes.

A practical pattern is to keep a ``BaseCaseForecaster`` instance alongside every primary model
and invoke it whenever the primary pipeline raises an exception:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    def run_forecast(primary_model, fallback_model, dataset):
        """Run primary forecast with automatic fallback."""
        try:
            forecast = primary_model.predict(dataset)
            return forecast, "primary"
        except InsufficientlyCompleteError:
            # Data too sparse — weekly repeat is more reliable than a partial ML forecast
            forecast = fallback_model.predict(dataset)
            return forecast, "fallback"
        except Exception as exc:
            # Model load failure, schema mismatch, etc.
            import logging
            logging.getLogger(__name__).error(
                "Primary forecast failed, using base case: %s", exc
            )
            forecast = fallback_model.predict(dataset)
            return forecast, "fallback"

Returning the source label alongside the forecast lets downstream consumers (dashboards, trading
systems) distinguish primary from fallback outputs and apply appropriate caution.

Model Staleness and the Reuse Penalty
---------------------------------------

A model trained weeks or months ago may have drifted away from current load patterns — new
industrial consumers, seasonal shifts, or changes in renewable generation can all erode accuracy
silently. OpenSTEF addresses this through the ``model_reuse_enable`` flag and the
``model_selection_old_model_penalty`` parameter in ``EnsembleForecastingWorkflowConfig``.

.. code-block:: python

    from openstef_models.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
    )

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        # Automatically compare new candidate against stored model
        model_reuse_enable=True,
        # Metric used to judge whether the new model is better
        model_selection_enable=True,
        model_selection_metric=("q0.5", "R2", "higher_is_better"),
        # New model must beat old model's R² by at least 1/1.2 ≈ 83%
        # before the old model is replaced — biases toward stability
        model_selection_old_model_penalty=1.2,
    )

The penalty factor deliberately biases the selection toward keeping the existing model unless the
new candidate is meaningfully better. This prevents noisy retraining runs from replacing a
well-performing model with a marginally different one. Increase the penalty (e.g., ``1.5``) in
stable grids where retraining should be conservative; lower it (e.g., ``1.05``) in grids with
rapidly changing load profiles.

When ``model_reuse_enable=False``, the workflow always retrains from scratch and deploys the
result — appropriate for scheduled nightly retraining jobs where you want a fresh model regardless
of the comparison outcome.

Handling Missing Input Features at Inference
---------------------------------------------

Feature availability at inference time is rarely guaranteed. Weather forecast APIs go down,
upstream data pipelines stall, and new substations may lack historical data for lag features.
``InputConsistencyChecker`` catches column mismatches, but you also need a strategy for what to
do when expected columns arrive with ``NaN`` values.

The recommended approach is to let the feature engineering pipeline handle imputation before
validation, and to configure ``CompletenessChecker`` with column weights that reflect which
features are truly load-bearing:

.. code-block:: python

    from openstef_models.transforms.validation import CompletenessChecker

    # Only the load column is mandatory; weather features are weighted lower
    checker = CompletenessChecker(
        columns=["load", "temperature", "wind_speed"],
        # Default weights treat all columns equally — override if needed
    )

For features derived from weather forecasts (see :doc:`feature_engineering` for details on which
features matter most), a common production pattern is to substitute climatological averages when
live forecast data is unavailable. This keeps the ML model operating rather than triggering a
fallback, at the cost of slightly wider prediction intervals.

Designing a Layered Reliability Strategy
------------------------------------------

Drawing these pieces together, a robust production pipeline typically has three layers:

1. **Validate first.** Run ``CompletenessChecker``, ``FlatlineChecker``, and
   ``InputConsistencyChecker`` on every incoming dataset before attempting inference. Catch
   ``InsufficientlyCompleteError`` and route to the fallback immediately.

2. **Monitor model age.** Use ``model_reuse_enable`` and ``model_selection_old_model_penalty``
   to control when retraining replaces the live model. Log the model's training timestamp
   alongside every forecast so you can alert when a model exceeds your staleness threshold.

3. **Always have a fallback.** Keep a ``BaseCaseForecaster`` configured and ready. It requires
   only recent historical load — no weather data, no trained weights — and will produce a
   reasonable probabilistic forecast even when everything else has failed.

.. note::

   Emit a structured log or metric whenever the fallback is invoked. A sudden increase in
   fallback rate is an early warning of upstream data quality problems or model drift, and is
   often the first signal that something needs attention in production.

.. warning::

   The ``BaseCaseForecaster`` assumes weekly periodicity holds. During public holidays, grid
   events, or extreme weather, the base case may be significantly off. Consider flagging
   fallback forecasts explicitly in your output schema so consumers can apply manual overrides
   when needed.

Related Topics
---------------

- :doc:`forecasting_basics` — introduction to short-term forecasting and what OpenSTEF produces
- :doc:`feature_engineering` — which input features matter most and how to handle missing ones
- :doc:`quantiles_and_confidence` — understanding the probabilistic outputs that fallback models
  also produce
- :doc:`model_selection` — choosing and comparing models, including the ensemble workflow
  configuration discussed above