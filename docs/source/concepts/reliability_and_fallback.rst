Reliability and Fallback Strategies
====================================

In production, forecasting systems face a continuous stream of imperfect conditions: sensors go offline, weather feeds arrive late, models trained on last month's data encounter a grid topology that changed yesterday. This page covers how OpenSTEF is designed to handle these situations gracefully — from structured exception handling and data completeness checks, through built-in fallback models, to recognising when a model has grown stale and should no longer be trusted.

For background on what the forecasts themselves represent, see :doc:`forecasting_basics`. For probabilistic output and confidence intervals, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Decision flow — primary model attempted → data completeness check → fallback to BaseCaseForecaster → NaN propagation if all sources exhausted]

Data Quality and Completeness Checks
--------------------------------------

Before a model ever runs, OpenSTEF validates the incoming data. The ``ForecastInputDataset`` and related validated dataset classes enforce structural invariants at construction time: required columns must be present, timestamps must be sorted, and the sample interval must be consistent. Violations raise typed exceptions — ``MissingColumnsError``, ``TimeSeriesValidationError`` — so calling code can distinguish a schema problem from a runtime error.

Beyond structure, OpenSTEF checks *completeness*: what fraction of expected time steps actually contain values. A dataset that is structurally valid but riddled with gaps may still be unsuitable for training or inference. When completeness falls below an acceptable threshold, an ``InsufficientlyCompleteError`` is raised:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    try:
        forecast = pipeline.predict(dataset)
    except InsufficientlyCompleteError as exc:
        # Log and route to fallback — do not silently discard
        logger.warning("Dataset too incomplete for primary model: %s", exc)
        forecast = fallback_pipeline.predict(dataset)

Catching ``InsufficientlyCompleteError`` at the pipeline boundary is the recommended pattern. It keeps fallback logic explicit and auditable rather than buried inside the model.

Training also guards against empty targets. If every row in the training set has a NaN target after preprocessing, the fit step raises ``InsufficientlyCompleteError`` immediately rather than producing a silently broken model:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError, NotFittedError

    try:
        pipeline.fit(train_data)
    except InsufficientlyCompleteError:
        logger.error("Training aborted: no valid target rows remain after preprocessing.")
        # Retain the previously serialised model rather than overwriting with a broken one

The ``NotFittedError`` exception is raised when ``predict`` is called on a model that has never been fitted, making it straightforward to detect a missing or corrupt model artefact at startup.

The BaseCaseForecaster: A Structured Fallback
----------------------------------------------

When the primary model cannot produce a forecast — because data is too sparse, the model artefact is missing, or inference raises an unrecoverable error — OpenSTEF provides ``BaseCaseForecaster`` as a principled fallback. Rather than returning zeros or raising an exception to the caller, the system can degrade to a model that repeats the most recent weekly pattern.

``BaseCaseForecaster`` works by looking back a configurable number of days (``primary_lag``, default 7 days) and replaying that window as the forecast. If the primary lag window itself contains gaps, it falls back further to a second lag (``fallback_lag``, default 14 days). Confidence intervals are derived from hourly standard deviations computed over the repeated base data, so even the fallback produces probabilistic output compatible with the rest of the pipeline.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )
    from openstef_core.types import LeadTime, Quantile

    fallback_model = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

The two-tier lag design means the fallback itself is resilient: a single week of missing measurements does not silence the system entirely. In practice, the 14-day fallback covers most short outages in upstream data feeds.

.. note::

    ``BaseCaseForecaster`` is intentionally naive. It assumes weekly periodicity, which holds well for most grid loads but poorly for assets with irregular schedules (e.g. industrial sites with variable shift patterns). Monitor fallback activation rates in production; sustained fallback use is a signal that the primary data pipeline needs attention.

Layered Fallback in Practice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A robust production pipeline typically implements fallback in layers:

.. code-block:: python

    from openstef_core.exceptions import (
        InsufficientlyCompleteError,
        ModelNotFoundError,
        PredictError,
    )

    def produce_forecast(dataset, primary_pipeline, fallback_model):
        """Attempt primary forecast; degrade gracefully on failure."""
        try:
            return primary_pipeline.predict(dataset)

        except ModelNotFoundError:
            logger.warning("Primary model artefact not found — using base case fallback.")

        except (InsufficientlyCompleteError, PredictError) as exc:
            logger.warning("Primary forecast failed (%s) — using base case fallback.", exc)

        # Fallback: repeat last week's pattern
        return fallback_model.predict(dataset)

Each exception type carries a distinct meaning. ``ModelNotFoundError`` points to a deployment or storage problem. ``InsufficientlyCompleteError`` points to a data feed problem. ``PredictError`` covers runtime failures during inference. Logging them separately makes post-incident analysis faster.

.. note:: [DIAGRAM: Layered fallback hierarchy — primary ML model → BaseCaseForecaster (7-day lag) → BaseCaseForecaster (14-day lag) → NaN / alert]

Model Staleness
----------------

A model that was trained six months ago may still load and run without error, yet produce poor forecasts because the underlying load patterns have shifted. This is *model staleness* — the model is technically functional but no longer reliable.

OpenSTEF's ``SkipFitting`` exception provides a mechanism for the training pipeline to signal that a model is *recent enough* and does not need retraining. The inverse — detecting that a model is *too old* — is the responsibility of the orchestration layer. A common pattern is to record the training timestamp alongside the serialised model and compare it against a maximum age threshold before each inference run:

.. code-block:: python

    from datetime import datetime, timedelta, timezone
    from openstef_core.exceptions import ModelNotFoundError

    MAX_MODEL_AGE = timedelta(days=7)

    def load_and_validate_model(model_store, model_id):
        """Load a model and raise if it is too stale to trust."""
        model, metadata = model_store.load(model_id)
        trained_at = metadata.get("trained_at")

        if trained_at is None:
            raise ModelNotFoundError(model_id)

        age = datetime.now(tz=timezone.utc) - trained_at
        if age > MAX_MODEL_AGE:
            raise ValueError(
                f"Model '{model_id}' is {age.days} days old "
                f"(limit: {MAX_MODEL_AGE.days} days). Retraining required."
            )

        return model

When a stale model is detected, the recommended response is to route to the fallback rather than block the forecast entirely. Blocking is appropriate only when the fallback itself is also unavailable.

Handling Missing Features at Inference Time
--------------------------------------------

Even when the model artefact is fresh and the target data is complete, individual *features* may be missing at inference time — a weather API timeout, a sensor that stopped reporting, a lag column that cannot be computed because recent history is absent.

OpenSTEF's autoregressive models check for required lag features before inference and raise a ``ValueError`` listing the missing columns:

.. code-block:: python

    from openstef_core.exceptions import PredictError

    try:
        forecast = model.predict(dataset)
    except ValueError as exc:
        # exc.args[0] contains the list of missing lag features
        logger.error("Missing features at inference: %s", exc)
        # Impute or route to fallback

For lag features specifically, ``BaseCaseForecaster`` handles gaps internally by forward-filling from the available history and falling back to the secondary lag window. For weather features and other external inputs, the recommended approach is to impute at the dataset construction stage — using the most recent available value or a climatological average — before the data reaches the model. This keeps imputation logic centralised and testable.

.. note::

    Frequency mismatches between the input data index and the model's expected frequency are caught early with a descriptive ``ValueError``. Always set an explicit ``freq`` on your ``DatetimeIndex`` before passing data to a model; pandas infers frequency inconsistently on sparse series.

Graceful Degradation Summary
------------------------------

The table below summarises the failure modes covered in this page and the recommended response for each:

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Failure mode
     - Exception raised
     - Recommended response
   * - Model artefact missing or corrupt
     - ``ModelNotFoundError``, ``ModelLoadingError``
     - Route to ``BaseCaseForecaster``
   * - Dataset too incomplete to use
     - ``InsufficientlyCompleteError``
     - Route to ``BaseCaseForecaster``
   * - Runtime inference error
     - ``PredictError``
     - Route to ``BaseCaseForecaster``; alert on-call
   * - Model called before fitting
     - ``NotFittedError``
     - Fail fast at startup; do not serve stale state
   * - Model age exceeds threshold
     - (application-level check)
     - Trigger retraining; serve fallback in the interim
   * - Missing lag or weather features
     - ``ValueError``
     - Impute at dataset stage; log feature availability

.. note::

    Sustained activation of the fallback model is a leading indicator of upstream problems — not a steady state. Set up monitoring on the rate of fallback activations alongside standard forecast accuracy metrics. A spike in fallback rate often precedes a detectable accuracy degradation by several hours.

For the feature engineering decisions that determine which inputs are most critical to protect, see :doc:`feature_engineering`. For how ensemble approaches can themselves provide an additional layer of resilience by combining multiple base models, see :doc:`meta_ensembles`.