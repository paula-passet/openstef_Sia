Production Reliability and Fallback Strategies
===============================================

In a live energy forecasting system, things go wrong. Sensors drop out, data
pipelines stall, models trained on last month's weather patterns encounter an
unusual heat wave, and occasionally a model simply fails to load. This page
explains how OpenSTEF is designed to handle these situations gracefully, and
how you can build production systems that degrade predictably rather than fail
catastrophically.

.. note::

   This page focuses on reliability patterns and fallback mechanisms. For an
   introduction to the forecasting pipeline itself, see
   :doc:`forecasting_basics`. For details on how missing features affect
   probabilistic outputs, see :doc:`quantiles_and_confidence`.

.. contents:: On this page
   :local:
   :depth: 2

The Reliability Problem in Energy Forecasting
----------------------------------------------

Short-term energy forecasts are often operationally critical — grid operators
and asset managers make dispatch decisions based on them. A forecast that
silently returns garbage is frequently worse than no forecast at all, because
downstream systems may act on bad numbers without realising they are bad.

OpenSTEF addresses this through several interlocking mechanisms:

- **Explicit data validation** that raises structured exceptions rather than
  producing silently wrong outputs.
- **A ``BaseCaseForecaster``** that provides a simple, robust fallback when
  primary models cannot run.
- **Model staleness detection** via configurable age limits on stored models.
- **Model selection with performance gating** that prevents a degraded
  retrained model from replacing a better existing one.

Understanding these mechanisms lets you design a system where every failure
mode has a defined, predictable outcome.

Data Validation and Missing-Value Handling
------------------------------------------

Real-world meter data is rarely clean. Sensors go offline, communication
failures introduce gaps, and upstream ETL jobs occasionally deliver truncated
time series. OpenSTEF's pipeline validates input data before attempting to
forecast and raises ``InsufficientlyCompleteError`` when the data cannot
support a reliable result.

During training, the pipeline drops rows where the target column contains
``NaN`` values. If *all* target rows are missing after this step, training is
aborted with a clear error rather than fitting a model on an empty dataset:

.. code-block:: python

   from openstef_models.pipelines.forecasting_pipeline import ForecastingPipeline
   from openstef_core.exceptions import InsufficientlyCompleteError

   try:
       pipeline.fit(data=training_data)
   except InsufficientlyCompleteError as exc:
       # Log the failure and fall back to the base-case forecaster
       logger.warning("Training aborted — insufficient target data: %s", exc)
       forecast = base_case_pipeline.predict(data=forecast_input)

A related issue arises with lag-based features. When you configure lag
transforms (for example, a 14-day lag), the first *N* days of a dataset
contain ``NaN`` values because there is no history to look back into. The
pipeline exposes a ``warmup_period`` parameter for exactly this reason — set
it to match your longest lag so those rows are excluded from training:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.pipelines.forecasting_pipeline import ForecastingPipeline

   pipeline = ForecastingPipeline(
       # ... other config ...
       warmup_period=timedelta(days=14),  # matches the longest lag transform
   )

At prediction time, if the input data is missing required lag features
entirely, the model raises a ``ValueError`` listing the missing feature names.
This is intentional: a partial feature set can produce forecasts that look
plausible but are systematically biased, so OpenSTEF surfaces the problem
explicitly rather than silently imputing zeros.

The Base-Case Forecaster: Your Last Line of Defence
----------------------------------------------------

When a primary model cannot run — because training data is unavailable,
because the model file is corrupt, or because the input is too sparse — you
need something that will always produce a reasonable answer. OpenSTEF ships
``BaseCaseForecaster`` for this purpose.

The model implements a simple but surprisingly effective heuristic: energy
load patterns repeat weekly. It takes the last seven days of historical
observations and projects them forward, falling back to 14-day-old data if
the primary week is unavailable. Confidence intervals are derived from hourly
standard deviations computed over the repeated base period.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile

   # Standard configuration — mirrors a typical primary model's quantile set
   base_case = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

The ``BaseCaseForecaster`` is intentionally simple. It has no learned
parameters, requires no training run, and will produce an output as long as
at least 14 days of historical data exist. This makes it suitable as the
terminal fallback in a multi-tier reliability chain.

.. note::

   ``BaseCaseForecaster`` is also useful as a *benchmark baseline* during
   model evaluation. If your primary model cannot consistently beat the
   base case on held-out data, that is a signal worth investigating before
   deploying to production. See :doc:`model_selection` for evaluation
   guidance.

Model Staleness Detection
-------------------------

A model trained six months ago may have been excellent at the time, but energy
systems change: new generation capacity comes online, demand patterns shift
with electrification, and seasonal calibration drifts. OpenSTEF's MLflow
integration includes a ``model_reuse_max_age`` parameter that controls how
long a stored model may be reused before a fresh training run is required.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.integrations.mlflow.mlflow_storage_callback import (
       MLFlowStorageCallback,
   )

   callback = MLFlowStorageCallback(
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),  # force retraining after one week
   )

When a prediction is requested and the stored model's age exceeds
``model_reuse_max_age``, the callback treats the model as absent and triggers
a new training run before forecasting. The default of seven days is a
reasonable starting point for most grid-connected assets, but you should tune
this based on how quickly your asset's behaviour changes and how frequently
fresh training data arrives.

If the callback cannot find *any* stored model — whether because none has been
trained yet or because the maximum age has been exceeded and retraining fails —
it raises ``ModelNotFoundError``. Your application code should catch this and
route to the base-case forecaster:

.. code-block:: python

   from openstef_core.exceptions import ModelNotFoundError

   try:
       result = workflow.predict(data=forecast_input)
   except ModelNotFoundError:
       logger.error("No valid model available; using base-case fallback")
       result = base_case.predict(data=forecast_input)

Model Selection and Performance Gating
---------------------------------------

Retraining does not automatically mean improvement. A model retrained on a
short or anomalous data window might perform worse than the model it would
replace. OpenSTEF's ``MLFlowStorageCallback`` includes a model selection step
that compares the newly trained model against the previously stored one before
promoting it.

The comparison is controlled by three parameters:

.. code-block:: python

   callback = MLFlowStorageCallback(
       model_selection_enable=True,
       # Evaluate on median forecast R² — higher is better
       model_selection_metric=("Q0.5", "R2", "higher_is_better"),
       # Require the new model to beat the old one by at least 20%
       # before replacing it (penalty applied to old model score)
       model_selection_old_model_penalty=1.2,
   )

The ``model_selection_old_model_penalty`` is a multiplier applied to the
existing model's metric score before comparison. A value of ``1.2`` means the
new model must score at least 20% better than the incumbent to be promoted.
This asymmetry deliberately biases the system towards stability: in production,
a slightly worse new model is usually less harmful than an unstable one that
oscillates between good and bad performance on successive retraining runs.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Putting It Together: A Layered Fallback Chain
----------------------------------------------

The patterns above compose naturally into a layered reliability architecture.
The following example sketches a production prediction function that degrades
gracefully through three tiers:

.. code-block:: python

   import logging
   from datetime import timedelta

   from openstef_core.exceptions import InsufficientlyCompleteError, ModelNotFoundError
   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile

   logger = logging.getLogger(__name__)

   QUANTILES = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   HORIZONS = [LeadTime(timedelta(hours=h)) for h in range(1, 49)]

   base_case = BaseCaseForecaster(
       quantiles=QUANTILES,
       horizons=HORIZONS,
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )


   def produce_forecast(workflow, forecast_input, historical_data):
       """Attempt primary forecast; fall back through two degraded tiers."""

       # Tier 1: primary ML model via the full workflow
       try:
           return workflow.predict(data=forecast_input)
       except ModelNotFoundError:
           logger.warning("Primary model unavailable; attempting base-case forecast")
       except (InsufficientlyCompleteError, ValueError) as exc:
           logger.warning("Primary forecast failed (%s); attempting base-case", exc)

       # Tier 2: base-case forecaster (weekly pattern repetition)
       try:
           return base_case.predict(data=historical_data)
       except Exception as exc:
           logger.error("Base-case forecast also failed: %s", exc)

       # Tier 3: return None and let the caller decide (e.g., hold last forecast)
       return None

.. warning::

   Tier 3 — returning ``None`` — should be treated as a critical alert in any
   production monitoring system. A ``None`` return means even the simplest
   possible forecast could not be produced, which implies a fundamental data
   availability problem that requires human intervention.

Monitoring Recommendations
---------------------------

Fallback mechanisms are only useful if you know when they are being invoked.
Consider instrumenting the following signals in your production system:

- **Fallback activation rate** — the fraction of forecast cycles that route to
  the base-case forecaster. A sudden increase indicates upstream data quality
  problems.
- **Model age at prediction time** — log the age of the model used for each
  forecast. Consistently old models suggest the retraining pipeline is broken.
- **Feature completeness** — track what fraction of expected features are
  present in each forecast input. Degrading completeness often precedes
  outright failures.
- **Base-case vs. primary model divergence** — when both models run, compare
  their median forecasts. Large divergence is an early warning that the primary
  model may be drifting.

These signals are most valuable when they are tracked over time rather than
checked in isolation. A single fallback activation is unremarkable; a trend
of increasing fallback rate over several days warrants investigation.

For guidance on evaluating whether your primary model's accuracy has degraded
to the point where the base case is competitive, see :doc:`model_selection`.
For understanding how data gaps propagate into probabilistic forecast
uncertainty, see :doc:`quantiles_and_confidence`.