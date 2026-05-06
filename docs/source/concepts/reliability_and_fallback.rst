Reliability and Fallback Strategies
===================================

In production, forecasting pipelines encounter conditions that no model was trained to handle: sensors go offline, upstream data feeds arrive late, meters flatline for hours, and models trained weeks ago drift away from current reality. This page covers how OpenSTEF addresses these situations — through data validation transforms, a dedicated baseline forecaster, and the design principles that keep a pipeline producing useful output even when things go wrong.

For background on what the forecasts themselves represent, see :doc:`forecasting_basics`. For how uncertainty is expressed in the output, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Why Graceful Degradation Matters
---------------------------------

A forecast that silently fails is worse than no forecast at all. Grid operators and trading desks make decisions based on model output; a stale or corrupted prediction presented as fresh is a liability. The goal of a reliable pipeline is not to prevent all failures — it is to detect them early, communicate them clearly, and substitute a known-quality fallback rather than propagating bad data downstream.

OpenSTEF's approach to this is layered:

- **Validate inputs before inference** — catch bad data before it reaches the model.
- **Raise typed exceptions** — let the calling code distinguish between "data too sparse" and "model not fitted".
- **Fall back to a transparent baseline** — when the primary model cannot run, use a simple, auditable substitute.

Data Validation Before Inference
----------------------------------

The ``openstef_models.transforms.validation`` module provides three transforms that act as gatekeepers. They are designed to be composed into a preprocessing pipeline and raise ``InsufficientlyCompleteError`` when the data does not meet the minimum bar for reliable inference.

**CompletenessChecker** measures the fraction of non-missing values across the relevant columns. If that ratio falls below a configurable threshold, it raises rather than silently forwarding a half-empty dataset to the model:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.validation import CompletenessChecker

   data = pd.DataFrame(
       {
           "load": [100.0, np.nan, np.nan, np.nan],
           "temperature": [20.0, np.nan, 24.0, np.nan],
       },
       index=pd.date_range("2025-01-01", periods=4, freq="15min"),
   )
   dataset = TimeSeriesDataset(data, timedelta(minutes=15))

   checker = CompletenessChecker()
   try:
       checker.transform(dataset)
   except Exception as exc:
       # InsufficientlyCompleteError: The dataset is not sufficiently complete. Completeness: 0.25
       print(exc)

You can restrict the check to specific columns and weight their importance differently — a missing temperature column is less critical than a missing load column, and the checker can reflect that.

**FlatlineChecker** detects long segments where the target series does not change. A meter that reports the same value for 96 consecutive 15-minute intervals (24 hours) is almost certainly stuck, not genuinely flat. Passing that data to a gradient-boosted model produces misleading feature importance and poor predictions. The checker masks those segments so they are excluded from training and flagged during inference.

**InputConsistencyChecker** verifies that the columns present at inference time match those seen during training. A feature that disappears from the upstream feed — a weather provider changing a field name, a sensor being decommissioned — will cause silent degradation if not caught. This transform raises early with a clear message about which columns are missing or unexpected.

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker,
   )

   # Compose into a validation stage
   validators = [
       FlatlineChecker(),
       CompletenessChecker(columns=["load"], threshold=0.8),
       InputConsistencyChecker(),
   ]

   for validator in validators:
       dataset = validator.transform(dataset)

.. note::

   ``InsufficientlyCompleteError`` is a typed exception from ``openstef_core.exceptions``. Catching it specifically — rather than a bare ``Exception`` — lets you route data-quality failures to a different code path than unexpected runtime errors.

The BaseCaseForecaster: A Transparent Fallback
-----------------------------------------------

When the primary model cannot produce a forecast — because validation failed, because the model artefact is absent, or because training data was insufficient — OpenSTEF provides ``BaseCaseForecaster`` as a drop-in substitute. It is intentionally simple: it repeats the most recent week of historical load as the forecast, with a 14-day secondary lag when the primary week is unavailable.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )

   forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

The forecaster uses ``pandas.reindex`` with forward-fill to project the weekly pattern forward, and derives confidence intervals from the hourly standard deviation of that repeated pattern. This means:

- The output is always interpretable — an operator can verify it by looking at last week's actuals.
- The uncertainty bands widen appropriately in hours where historical variance was high (e.g., morning ramp-up periods).
- The fallback itself degrades gracefully: if the primary lag window (7 days ago) has gaps, it automatically uses the secondary lag (14 days ago) to fill them.

.. note:: [VISUALIZATION: Side-by-side plot of a primary ML model forecast vs. BaseCaseForecaster output for the same horizon, showing how the baseline tracks weekly periodicity while the ML model captures shorter-term deviations]

Structuring a Fallback-Aware Pipeline
---------------------------------------

The practical pattern is to wrap primary model inference in a try/except block and substitute the baseline on any data-quality or model-availability failure. The key discipline is to **log which path was taken** so that operators can monitor fallback frequency as a health signal.

.. code-block:: python

   import logging
   from openstef_core.exceptions import InsufficientlyCompleteError

   logger = logging.getLogger(__name__)

   def run_forecast(dataset, primary_model, fallback_model):
       try:
           # Validate and run primary model
           for validator in validators:
               dataset = validator.transform(dataset)
           return primary_model.predict(dataset), "primary"

       except InsufficientlyCompleteError as exc:
           logger.warning(
               "Data quality check failed, switching to base case. Reason: %s", exc
           )
           return fallback_model.predict(dataset), "fallback"

       except Exception as exc:
           logger.error("Unexpected inference failure: %s", exc, exc_info=True)
           return fallback_model.predict(dataset), "fallback"

Returning the source label (``"primary"`` or ``"fallback"``) alongside the forecast lets downstream consumers attach it to the output record. Monitoring the ratio of fallback-to-primary forecasts over time is one of the most useful production health metrics available — a rising fallback rate is an early warning of upstream data degradation long before it becomes visible in accuracy metrics.

Model Staleness
----------------

A model that was accurate when trained can drift as consumption patterns shift — new industrial loads come online, building retrofits change thermal behaviour, EV adoption accelerates. OpenSTEF does not embed a staleness timer in the model artefact itself, but the evaluation pipeline provides the tools to detect drift.

The recommended approach is to run the ``EvaluationPipeline`` from ``openstef_beam.evaluation`` on a rolling window of recent predictions against actuals. When windowed metrics (e.g., CRPS or pinball loss) exceed a threshold relative to the global baseline, that is a signal to trigger retraining rather than continue serving the stale model.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_core.types import LeadTime

   config = EvaluationConfig(
       lead_times=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")],
   )

   report = EvaluationPipeline(config=config, ...).run(
       predictions=recent_predictions,
       ground_truth=actuals,
       target_column="load",
   )

   # Inspect windowed metrics to detect recent degradation
   for subset in report.subsets:
       print(subset.metrics)

A model whose rolling-window error has grown significantly beyond its historical baseline should be retrained before the fallback rate rises. Catching staleness proactively — through evaluation metrics — is preferable to discovering it through operator complaints.

.. note::

   Training data validation uses the same ``InsufficientlyCompleteError`` path. If ``dropna`` on the target column leaves an empty DataFrame, the training pipeline raises immediately rather than fitting a model on no data. This prevents a corrupted model artefact from replacing a good one.

Practical Recommendations
--------------------------

These patterns come from operating OpenSTEF in production environments:

- **Always deploy a fitted** ``BaseCaseForecaster`` **alongside the primary model.** It requires only historical load data — no weather features — so it can run even when the feature pipeline is degraded.
- **Treat fallback rate as a first-class metric.** Alert when it exceeds a few percent over a rolling 24-hour window.
- **Set completeness thresholds conservatively at first**, then tighten them as you learn the normal missingness profile of your data sources. A threshold of 0.8 is a reasonable starting point for most 15-minute load series.
- **Log the completeness score, not just the pass/fail.** A score of 0.79 failing a 0.80 threshold is very different from a score of 0.20 — both trigger the fallback, but the latter warrants immediate investigation.
- **Separate data-quality failures from model failures** in your alerting. ``InsufficientlyCompleteError`` points to an upstream data problem; an unexpected ``RuntimeError`` during inference points to a model or code problem. They have different owners and different remediation paths.

For how features are constructed and which ones matter most for forecast quality, see :doc:`feature_engineering`. For an understanding of the ensemble strategies that sit above individual models, see :doc:`meta_ensembles`.