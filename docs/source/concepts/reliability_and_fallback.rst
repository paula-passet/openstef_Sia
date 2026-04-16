Production Reliability and Fallback Strategies
===============================================

In a production energy forecasting system, things go wrong. Meters stop reporting,
weather feeds arrive late, and models trained weeks ago may no longer reflect current
grid conditions. OpenSTEF is designed as a library with these realities in mind: it
provides built-in tools for detecting bad data, falling back to simpler models when
primary forecasts cannot be produced, and controlling how long a trained model may be
reused before it is considered stale.

This page covers the reliability mechanisms available in OpenSTEF and how to compose
them into a robust forecasting pipeline. For background on what a forecast is and how
the pipeline is structured, see :doc:`forecasting_basics`. For probabilistic output and
confidence intervals, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd


Detecting Bad Input Data
------------------------

Before a model ever runs, the quality of incoming data must be assessed. OpenSTEF
provides three validation transforms in ``openstef_models.transforms.validation`` that
can be inserted into any feature pipeline:

- **CompletenessChecker** — raises an error if the time series contains too many
  missing values to produce a reliable forecast.
- **FlatlineChecker** — detects *flatliner* patterns, where the load signal remains
  constant for an extended period. A flat signal almost always indicates a sensor
  fault or a broken data feed rather than genuine zero-variance consumption.
- **InputConsistencyChecker** — validates that the structure and column set of
  incoming data matches what the fitted pipeline expects.

.. code-block:: python

    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )
    from datetime import timedelta

    # FlatlineChecker can be configured with a minimum duration
    # before a constant signal is considered anomalous.
    flatline_check = FlatlineChecker()

    completeness_check = CompletenessChecker()

    # Apply as part of a transform chain before training or inference
    completeness_check.transform(dataset)
    flatline_check.transform(dataset)

When ``FlatlineChecker`` detects an ongoing flatliner it raises a
``FlatlinerDetectedError``. Catching this exception at the pipeline boundary is the
natural place to trigger a fallback strategy rather than propagating a bad forecast
downstream.

.. note::

   ``FlatlineChecker.detect_ongoing_flatliner`` can also be called directly on a
   ``pd.Series`` if you want to inspect the signal programmatically before deciding
   whether to proceed with the primary model.


The BaseCaseForecaster: A Built-in Fallback Model
-------------------------------------------------

When primary model inference is not possible — because input data is incomplete, a
flatliner has been detected, or the model artefact is unavailable — OpenSTEF provides
``BaseCaseForecaster`` as a ready-made fallback. Rather than returning ``NaN`` or
raising an unhandled exception, the system can degrade gracefully to a naive but
meaningful forecast.

``BaseCaseForecaster`` implements the well-established assumption that energy load
follows a weekly periodic pattern. It takes the last week of historical target data and
repeats it forward to cover the forecast horizon. If that primary window is itself
unavailable, it automatically falls back to data from two weeks ago.

.. code-block:: python

    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    # Default configuration: 7-day primary lag, 14-day fallback lag
    fallback_forecaster = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
    )

    # Custom lag windows if your data has different periodicity
    conservative_fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=21),  # three weeks back
        ),
    )

    fallback_forecaster.fit(training_data)
    fallback_predictions = fallback_forecaster.predict(forecast_data)

The confidence intervals produced by ``BaseCaseForecaster`` are derived from the
hourly standard deviations of the repeated historical window, so downstream consumers
still receive a probabilistic forecast even in degraded mode. This matters for grid
operators who rely on uncertainty bounds to make dispatch decisions.

The two-level lag structure (primary → fallback) means the model is resilient to a
single week of missing or corrupt data. If the most recent week is unavailable, the
forecaster silently promotes the 14-day window rather than failing.


Model Staleness and Controlled Reuse
-------------------------------------

A trained model is a snapshot of historical patterns. As seasons change, new loads
come online, or consumption behaviour shifts, an old model will drift from reality.
OpenSTEF's ``CustomForecastingWorkflow`` exposes explicit controls over how long a
model may be reused before retraining is forced.

The key parameters are:

- ``model_reuse_enable`` — whether to reuse an existing model at all (default: ``True``).
- ``model_reuse_max_age`` — the maximum age of a stored model before it is considered
  stale and a fresh training run is triggered (default: 7 days).
- ``model_selection_enable`` — whether to compare the newly trained model against the
  incumbent and only promote it if it performs better (default: ``True``).
- ``model_selection_metric`` — the quantile, metric name, and direction used for
  comparison (default: median R²).
- ``model_selection_old_model_penalty`` — a multiplier applied to the incumbent's
  metric score to bias selection towards fresher models even when the improvement is
  marginal (default: 1.2).

.. code-block:: python

    from openstef_beam.workflows.custom_forecasting_workflow import (
        CustomForecastingWorkflow,
    )
    from datetime import timedelta
    from openstef_core.types import Q

    workflow = CustomForecastingWorkflow(
        # Force retraining if the stored model is older than 3 days
        model_reuse_max_age=timedelta(days=3),
        # Require a 20 % improvement before promoting a new model
        model_selection_old_model_penalty=1.2,
        model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
    )

Setting ``model_reuse_max_age`` to a value shorter than your retraining cadence
guarantees that a model is never silently reused beyond its intended lifetime. The
penalty factor prevents unnecessary churn: a newly trained model must beat the
incumbent by a meaningful margin before it replaces it, which avoids promoting a model
that happens to score slightly higher on a single evaluation window due to noise.

.. note::

   Model age is tracked through the versioned storage backend (MLflow by default).
   The workflow reads the ``trained_at`` timestamp from the stored run and compares it
   against the current wall-clock time. No external scheduler or cron job is needed to
   enforce the age limit — the check happens automatically at the start of each
   training workflow invocation.


Composing a Resilient Pipeline
--------------------------------

The individual mechanisms described above are most powerful when composed into a
coherent strategy. A typical production pattern looks like this:

1. **Validate inputs** using ``CompletenessChecker`` and ``FlatlineChecker`` before
   attempting primary model inference.
2. **Catch validation exceptions** at the pipeline boundary and route to the fallback
   forecaster rather than propagating the error.
3. **Tag fallback forecasts** in your output so that downstream consumers and
   monitoring dashboards can distinguish degraded output from primary output.
4. **Enforce model age limits** via ``model_reuse_max_age`` so that stale models are
   retrained automatically rather than silently accumulating drift.

.. code-block:: python

    from openstef_core.exceptions import FlatlinerDetectedError
    from openstef_models.transforms.validation import CompletenessChecker, FlatlineChecker
    from openstef_models.models.forecasting.base_case_forecaster import BaseCaseForecaster
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    completeness_check = CompletenessChecker()
    flatline_check = FlatlineChecker()

    fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
    )
    fallback.fit(training_dataset)

    def produce_forecast(primary_model, dataset, training_dataset):
        """Attempt primary forecast; fall back gracefully on data quality issues."""
        try:
            completeness_check.transform(dataset)
            flatline_check.transform(dataset)
            forecast = primary_model.predict(dataset)
            forecast["source"] = "primary"
        except (FlatlinerDetectedError, ValueError) as exc:
            # Log the reason so operators can investigate
            import logging
            logging.getLogger(__name__).warning(
                "Primary forecast failed (%s); using base-case fallback.", exc
            )
            forecast = fallback.predict(dataset)
            forecast["source"] = "fallback"
        return forecast

The ``source`` column is a simple convention, but it is invaluable in practice: it
lets you filter monitoring metrics by forecast type, alert when the fallback rate
exceeds a threshold, and audit historical periods where degraded forecasts were used.


Monitoring and Alerting Considerations
----------------------------------------

OpenSTEF provides the forecasting logic; the surrounding observability infrastructure
is the operator's responsibility. A few patterns that work well in practice:

- **Track fallback rate over time.** If ``source == "fallback"`` appears for more than
  a few consecutive intervals, it almost always indicates a persistent upstream data
  problem rather than a transient glitch.
- **Monitor model age independently of the retraining workflow.** Even with
  ``model_reuse_max_age`` set, a retraining job can fail silently. Querying the
  MLflow storage for the ``trained_at`` timestamp and alerting when it exceeds your
  threshold provides a second line of defence.
- **Compare fallback forecasts against actuals retrospectively.** Because
  ``BaseCaseForecaster`` produces confidence intervals, you can evaluate its coverage
  after the fact and tune ``primary_lag`` / ``fallback_lag`` to match the actual
  periodicity of your load profile.

.. note::

   For sites with strong weekly periodicity (residential, commercial office loads),
   the default 7-day lag is usually appropriate. For industrial loads with irregular
   shift patterns, consider extending ``primary_lag`` to 14 days and ``fallback_lag``
   to 28 days so the fallback window captures a more representative operating cycle.


Summary
-------

OpenSTEF's reliability mechanisms are composable library primitives rather than
opinionated application behaviour. The key building blocks are:

- ``CompletenessChecker``, ``FlatlineChecker``, and ``InputConsistencyChecker`` for
  catching bad data before it reaches the model.
- ``BaseCaseForecaster`` as a statistically grounded fallback that degrades gracefully
  to weekly-pattern repetition with uncertainty estimates.
- ``model_reuse_max_age`` and ``model_selection_old_model_penalty`` in
  ``CustomForecastingWorkflow`` for controlling model staleness and preventing silent
  drift.

Together these tools let you build a forecasting service that continues to produce
useful output — and clearly signals when it is doing so in degraded mode — even when
the primary data pipeline or model is unavailable.