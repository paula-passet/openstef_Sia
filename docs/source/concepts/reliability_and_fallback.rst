Reliability and Fallback Strategies
====================================

In production, energy forecasting systems face a continuous stream of imperfect conditions: sensors go offline, upstream data pipelines deliver late or corrupted measurements, and models trained weeks ago may no longer reflect current grid behaviour. This page explains how OpenSTEF is designed to handle these situations gracefully, covering the built-in mechanisms for data validation, fallback forecasting, and detecting when a model has grown stale.

For background on what a forecast represents and how uncertainty is quantified, see :doc:`quantiles_and_confidence`. For details on the features that feed into a model, see :doc:`feature_engineering`.

.. note::

   Reliability is a property of the *system* you build around OpenSTEF, not just the library itself. OpenSTEF provides the building blocks — validated datasets, structured exceptions, and a purpose-built fallback forecaster — but the orchestration logic that decides *when* to invoke each layer is yours to implement.

[DIAGRAM: Layered fallback decision tree showing: primary ML model → data completeness check → BaseCaseForecaster (7-day lag) → BaseCaseForecaster (14-day fallback lag) → hard failure with structured exception]

---

Data Quality and Completeness Checks
--------------------------------------

Before a forecast is ever computed, OpenSTEF validates the incoming data through its typed dataset classes. ``ForecastInputDataset`` and ``ForecastDataset`` (from ``openstef_core.datasets.validated_datasets``) enforce structural invariants at construction time: required columns must be present, timestamps must be sorted, and the sample interval must be consistent throughout the series.

When these invariants are violated, OpenSTEF raises structured exceptions rather than silently producing garbage output. The most important of these is ``InsufficientlyCompleteError``, raised when the fraction of valid (non-NaN) target values falls below a configurable threshold. This makes it straightforward to distinguish a *data problem* from a *model problem* in your monitoring stack.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets.validated_datasets import ForecastInputDataset
   from openstef_core.exceptions import InsufficientlyCompleteError

   # Build a dataset from your incoming DataFrame.
   # Structural validation runs at construction time.
   try:
       dataset = ForecastInputDataset(
           data=raw_df,
           sample_interval=timedelta(minutes=15),
       )
   except (ValueError, InsufficientlyCompleteError) as exc:
       # Log, alert, and route to fallback — do not re-raise blindly.
       print(f"Input data rejected: {exc}")
       dataset = None

A second common failure mode is a frequency mismatch: the index of the incoming DataFrame carries a different cadence than the model was trained on. OpenSTEF's ``MedianForecaster`` and related models check this explicitly and raise a ``ValueError`` with a descriptive message, so you can detect clock-drift or resampling bugs in upstream pipelines early.

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastInputDataset
   from openstef_core.exceptions import InsufficientlyCompleteError

   def validate_or_none(raw_df: pd.DataFrame) -> ForecastInputDataset | None:
       """Return a validated dataset, or None if the data is unusable."""
       try:
           return ForecastInputDataset(data=raw_df, sample_interval=timedelta(minutes=15))
       except (ValueError, InsufficientlyCompleteError):
           return None

---

The BaseCaseForecaster: A Built-In Fallback
--------------------------------------------

When the primary ML model cannot produce a forecast — because input data is too sparse, the model artefact is unavailable, or an unexpected exception occurs — OpenSTEF provides ``BaseCaseForecaster`` as a first-class fallback. Rather than returning zeros or raising an unhandled error, you can route the request to this model and still deliver a useful, explainable forecast to downstream consumers.

``BaseCaseForecaster`` (from ``openstef_models.models.forecasting.base_case_forecaster``) implements a weekly-periodicity assumption: it repeats the load pattern observed exactly one week ago (the *primary lag*, default 7 days). If that window is itself missing data, it automatically falls back to a second historical window (the *fallback lag*, default 14 days). Confidence intervals are derived from the hourly standard deviation of the repeated pattern, so the output is still a valid probabilistic forecast with quantiles.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case_forecaster import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   # Configure the fallback forecaster.
   # primary_lag: look back 7 days; fallback_lag: look back 14 days.
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

   # Fit once on historical data; re-fit periodically as new data arrives.
   fallback_forecaster.fit(training_dataset)

The fallback forecaster is intentionally simple. Its value in production is not accuracy — it is *availability*. A forecast that says "load will look like last Tuesday" is almost always more useful to grid operators than no forecast at all, and it degrades gracefully even when recent data is patchy.

.. note::

   You can extend the fallback lag beyond 14 days for assets with strong seasonal patterns or when recent history is unreliable. A 21-day lag, for example, captures three full weekly cycles and can be more robust for industrial loads with fortnightly maintenance schedules.

---

Implementing a Fallback Chain
------------------------------

The recommended pattern in production is a *try-primary, catch-fallback* chain. The exact structure depends on your orchestration framework, but the logic is always the same: attempt the primary forecast, catch any exception that indicates a recoverable failure, and invoke the fallback.

.. code-block:: python

   import logging
   from openstef_core.exceptions import InsufficientlyCompleteError

   logger = logging.getLogger(__name__)

   def produce_forecast(primary_model, fallback_model, dataset):
       """Attempt primary forecast; fall back gracefully on failure."""
       if dataset is None:
           logger.warning("No valid dataset available; using fallback forecaster.")
           return fallback_model.predict(fallback_dataset)

       try:
           return primary_model.predict(dataset)
       except InsufficientlyCompleteError as exc:
           logger.warning("Primary forecast failed (incomplete data): %s", exc)
           return fallback_model.predict(fallback_dataset)
       except AttributeError as exc:
           # Model not fitted — likely a cold-start or deployment issue.
           logger.error("Primary model not fitted: %s", exc)
           return fallback_model.predict(fallback_dataset)
       except Exception as exc:
           # Broad catch only at the outermost layer; always log the original.
           logger.exception("Unexpected error in primary forecast: %s", exc)
           return fallback_model.predict(fallback_dataset)

[DIAGRAM: Sequence diagram showing orchestrator calling primary model, receiving InsufficientlyCompleteError, logging the event, then calling BaseCaseForecaster and returning its output to the downstream consumer]

A few practical notes on this pattern:

- **Always log the original exception** before routing to fallback. Silent fallbacks make post-incident analysis very difficult.
- **Tag fallback forecasts** in your output schema (e.g., with a ``forecast_source`` field). Downstream consumers and monitoring dashboards need to know which forecasts came from the primary model and which did not.
- **Alert on sustained fallback usage.** A single fallback event is normal; ten consecutive ones indicate a systemic problem that needs human attention.

---

Model Staleness Detection
--------------------------

A model that was accurate when trained can silently degrade as the underlying load patterns shift — new large consumers connect, distributed generation capacity changes, or seasonal baselines drift. OpenSTEF does not automatically detect staleness, but it provides the evaluation infrastructure to measure it continuously.

The ``EvaluationPipeline`` (from ``openstef_beam.evaluation.evaluation_pipeline``) segments forecast performance across multiple dimensions: availability times, lead times, and rolling time windows. By running this pipeline regularly against recent actuals, you can track whether model skill is declining over a sliding window.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import AvailableAt, LeadTime, Quantile
   from openstef_beam.evaluation.evaluation_pipeline import (
       EvaluationConfig,
       EvaluationPipeline,
   )
   from openstef_beam.evaluation.models import Window

   config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       # Evaluate over a rolling 21-day window to detect gradual drift.
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

   pipeline = EvaluationPipeline(
       config=config,
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       window_metric_providers=my_window_metrics,
       global_metric_providers=my_global_metrics,
   )

   report = pipeline.run(forecast_dataset)

A practical staleness policy might look like this:

- **Green:** rolling skill score within 10 % of the baseline established at training time.
- **Amber:** skill score degraded by 10–25 %; schedule a retraining run.
- **Red:** skill score degraded by more than 25 %, or the model has not been retrained in more than *N* days; trigger immediate retraining and route to fallback until the new model is validated.

The specific thresholds depend on your asset type and the cost of forecast errors. For assets where forecast error directly affects balancing costs, tighter thresholds are warranted.

.. note::

   Staleness is not the same as a bad forecast on a single day. Weather-driven anomalies (heat waves, storms) will always produce temporarily worse forecasts. Look for *sustained* degradation over the rolling window, not individual spikes.

---

Handling Missing Features at Inference Time
--------------------------------------------

Even when the primary model is healthy and recent data is available, individual feature columns can be missing at inference time — a weather provider API times out, a sensor is offline, or a new feature was added to the pipeline but not yet backfilled. OpenSTEF's models raise a ``ValueError`` with a precise list of missing features when this occurs:

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastInputDataset

   try:
       forecast = primary_model.predict(inference_dataset)
   except ValueError as exc:
       if "missing the following lag features" in str(exc):
           logger.warning("Feature gap detected, routing to fallback: %s", exc)
           forecast = fallback_model.predict(fallback_dataset)
       else:
           raise

This explicit error message makes it possible to distinguish a *feature pipeline* failure from a *model* failure in your alerting system, and to route them to different on-call teams if needed.

---

Summary
--------

OpenSTEF provides several interlocking mechanisms for production reliability:

- **Validated dataset types** (``ForecastInputDataset``, ``ForecastDataset``) catch structural data problems at construction time, before any model code runs.
- **``InsufficientlyCompleteError``** signals that data is too sparse to train or forecast reliably, giving you a clean hook for fallback routing.
- **``BaseCaseForecaster``** is a purpose-built fallback that repeats weekly load patterns with a two-level lag hierarchy (7-day primary, 14-day secondary), always producing a valid probabilistic output.
- **``EvaluationPipeline``** with rolling time windows gives you the continuous skill monitoring needed to detect model staleness before it becomes a production incident.

The library handles the mechanics; the policy — thresholds, alert routing, retraining schedules — is yours to define based on the operational requirements of your grid.

For related topics, see :doc:`quantiles_and_confidence` for how uncertainty is represented in forecast outputs, and :doc:`meta_ensembles` for how ensemble approaches can themselves improve robustness by combining multiple base models.