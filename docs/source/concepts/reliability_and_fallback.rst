Reliability and Fallback Strategies
====================================

In production energy forecasting, models don't always behave perfectly. Input data
arrives late or with gaps, sensors flatline, and trained models grow stale as grid
conditions evolve. This page describes how OpenSTEF handles these situations — what
checks it performs automatically, what exceptions it raises when things go wrong, and
how you can build a graceful degradation strategy around the library's built-in tools.

For background on what OpenSTEF forecasts and why, see :doc:`forecasting_basics`. For
details on probabilistic outputs, see :doc:`quantiles_and_confidence`.

.. mermaid:: diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Data Quality: The First Line of Defence
-----------------------------------------

Bad forecasts usually start with bad data. OpenSTEF's validation layer catches the
most common input problems before they silently corrupt a model or produce nonsensical
output. Three transforms in ``openstef_models.transforms.validation`` do this work:

**CompletenessChecker** computes the fraction of non-null values across the dataset
and raises ``InsufficientlyCompleteError`` if it falls below a configurable threshold.
This is the most common failure mode in practice: a data pipeline stalls and the
forecast window fills up with ``NaN``.

**FlatlineChecker** detects when the target signal stops varying — a classic sign of
a stuck sensor or a broken data feed. It can be configured to log a warning or to
block the pipeline entirely via ``error_on_flatliner``.

**InputConsistencyChecker** ensures that the features present at inference time match
those seen during training. If a weather provider drops a column or renames a field,
this checker catches the mismatch before the model silently receives a zero-filled
substitute.

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
    )

    # Simulate a partially missing input window
    data = pd.DataFrame(
        {
            "load": [100.0, np.nan, np.nan, np.nan],
            "temperature": [15.0, np.nan, 16.0, np.nan],
            "wind_speed": [np.nan, np.nan, np.nan, np.nan],
        },
        index=pd.date_range("2025-06-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    try:
        CompletenessChecker().transform(dataset)
    except InsufficientlyCompleteError as exc:
        # Completeness: 0.25 — too many gaps to trust the forecast
        print(f"Data rejected: {exc}")

These transforms are applied automatically when you use the ensemble workflow, but
you can also compose them manually into any preprocessing pipeline if you are building
a custom workflow.

.. note::

   ``InsufficientlyCompleteError`` is the canonical signal that a forecast attempt
   should be abandoned and a fallback should be triggered. Catch it at the top of
   your forecasting loop rather than letting it propagate to an unhandled exception.

The BaseCaseForecaster: A Reliable Fallback
--------------------------------------------

When the primary model cannot produce a forecast — because data is too sparse, the
model has not yet been trained, or validation fails — OpenSTEF provides
``BaseCaseForecaster`` as a drop-in fallback. It makes no statistical assumptions
beyond weekly periodicity: it takes the most recent full week of historical load data
and repeats it forward, filling any gaps from the week before that.

This is intentionally simple. A naive weekly-repeat forecast is almost always better
than returning zeros or raising an unhandled exception, and it degrades gracefully
even when only partial history is available.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    # Standard fallback: repeat last 7 days, fill gaps from 14 days ago
    fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
    )

    # If primary data is unusually sparse, extend the lookback window
    conservative_fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

The fallback also produces confidence intervals by computing hourly standard
deviations from the repeated base data, so downstream consumers that expect
probabilistic output continue to receive it even during degraded operation.

Model Staleness and Reuse
--------------------------

A model trained six months ago on summer load patterns may perform poorly in winter.
OpenSTEF's ``EnsembleForecastingWorkflowConfig`` exposes ``model_max_age`` to set a
hard upper bound on how old a persisted model can be before it is retrained rather
than reused.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.workflows.ensemble_forecasting_workflow import (
        EnsembleForecastingWorkflowConfig,
    )

    config = EnsembleForecastingWorkflowConfig(
        model_id="substation_42",
        base_models=["lgbm", "gblinear"],
        horizons=[...],
        quantiles=[...],
        # Reject any persisted model older than 30 days
        model_max_age=timedelta(days=30),
        # When reusing, penalise the old model's metric to favour retraining
        model_selection_old_model_penalty=1.2,
        model_reuse_enable=True,
    )

The ``model_selection_old_model_penalty`` parameter biases the comparison metric
against the older model. A value of ``1.2`` means the old model's score is divided
by 1.2 before being compared to the newly trained candidate — so the new model only
needs to be 83% as good to win. This prevents unnecessary retraining churn while
still replacing genuinely degraded models.

If ``model_reuse_enable`` is ``False``, the workflow always retrains from scratch,
which is appropriate for scheduled nightly retraining jobs where compute cost is not
a concern.

Graceful Degradation in Practice
----------------------------------

The pattern that emerges from production deployments is a three-tier hierarchy:

1. **Primary model** — the trained ensemble, used when data is complete and the model
   is fresh.
2. **Degraded primary** — the same model, used with a warning when data completeness
   is marginal but above a minimum threshold.
3. **BaseCaseForecaster** — used when data quality fails validation entirely or no
   trained model is available.

The following sketch shows how to wire these tiers together using OpenSTEF's
exception types:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError, NotFittedError

    def produce_forecast(workflow, dataset):
        """Attempt primary forecast with automatic fallback."""
        try:
            return workflow.predict(dataset)

        except InsufficientlyCompleteError:
            # Data too sparse — fall back to weekly repeat
            import logging
            logging.warning(
                "Input data failed completeness check; using BaseCaseForecaster."
            )
            return fallback.predict(dataset)

        except NotFittedError:
            # No trained model exists yet (e.g., first deployment)
            logging.warning(
                "No trained model found; using BaseCaseForecaster."
            )
            return fallback.predict(dataset)

.. warning::

   Do not silently swallow ``InsufficientlyCompleteError`` and proceed with the
   primary model. The validation transforms raise this exception precisely because
   the model's predictions would be unreliable. Always route to a fallback or
   surface the error to an alerting system.

Monitoring and Alerting Hooks
------------------------------

OpenSTEF does not prescribe a monitoring framework, but several natural integration
points exist:

- **Completeness ratio** — ``CompletenessChecker`` raises with the completeness score
  in the exception message. Parse this value and emit it as a metric to your
  observability platform.
- **Fallback activation rate** — track how often ``produce_forecast`` falls through
  to the ``BaseCaseForecaster`` tier. A sustained increase signals a degrading data
  pipeline upstream.
- **Model age** — log the age of the model used for each forecast run. If
  ``model_max_age`` is never triggered, the threshold may be set too conservatively.
- **Flatline events** — ``FlatlineChecker`` can log warnings without blocking the
  pipeline (``error_on_flatliner=False``). Aggregate these warnings to detect
  systematic sensor failures.

These hooks are intentionally lightweight: because OpenSTEF is a library, it does not
impose a metrics backend. You instrument the points that matter for your deployment
and send data wherever your organisation already collects it.

Summary
--------

OpenSTEF's reliability story rests on three complementary mechanisms: validation
transforms that reject bad data early, a ``BaseCaseForecaster`` that provides a
meaningful fallback when the primary model cannot run, and workflow configuration
options that prevent stale models from silently degrading forecast quality. Together
they allow you to build a forecasting service that fails loudly at the right
boundaries and degrades gracefully everywhere else.

For guidance on selecting and configuring the primary model that sits above these
fallbacks, see :doc:`model_selection`. For details on the feature inputs that the
validation transforms protect, see :doc:`feature_engineering`.