Reliability and Fallback Strategies
===================================

In production, forecasting pipelines encounter conditions that no model was trained to handle: sensors go offline, communication links drop, upstream data feeds arrive late, and models trained weeks ago drift away from current reality. This page covers how OpenSTEF is designed to degrade gracefully under these conditions — and how you can build robust pipelines around its reliability primitives.

For background on what the forecasts themselves represent, see :doc:`forecasting_basics`. For probabilistic output and confidence intervals, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Why Forecasts Fail in Production
---------------------------------

Short-term energy forecasting pipelines run continuously, often every 15 minutes. Over a long operational lifetime, failures accumulate from several distinct sources:

- **Missing input data** — weather feeds, smart meter readings, or SCADA measurements arrive late or not at all.
- **Bad data** — sensors report physically impossible values (flatliners, spikes, sign errors) that corrupt feature engineering.
- **Stale models** — a model trained on summer data is still running in winter; its accuracy has silently degraded.
- **Unfitted models** — a model artefact is present in storage but was never successfully trained, or its serialisation is corrupt.
- **Structural breaks** — a new solar installation, grid topology change, or metering reconfiguration shifts the underlying distribution.

OpenSTEF addresses each of these with a layered defence: structured exceptions signal *what* went wrong, data validators catch bad inputs early, and the ``BaseCaseForecaster`` provides a last-resort fallback that always produces a valid forecast.

OpenSTEF's Exception Hierarchy
--------------------------------

OpenSTEF uses a typed exception hierarchy (from ``openstef_core.exceptions``) so that calling code can respond differently to different failure modes rather than catching a generic ``Exception``.

.. code-block:: python

   from openstef_core.exceptions import (
       InsufficientlyCompleteError,
       FlatlinerDetectedError,
       ModelLoadingError,
       ModelNotFoundError,
       NotFittedError,
       PredictError,
   )

The most important exceptions for reliability engineering are:

- ``InsufficientlyCompleteError`` — raised when a dataset falls below the minimum completeness threshold required for training or inference. The exception message includes the measured completeness ratio so you can log it.
- ``FlatlinerDetectedError`` — raised when a time series is detected to be a flatliner (constant value), which typically indicates a stuck sensor rather than genuine zero load.
- ``ModelLoadingError`` — raised when a model artefact exists in storage but cannot be deserialised correctly.
- ``ModelNotFoundError`` — raised when no model artefact exists at all for a given model identifier.
- ``NotFittedError`` — raised when ``predict`` is called on a model that has not been fitted.
- ``PredictError`` — raised for errors that occur during the inference step itself.
- ``SkipFitting`` — not an error; raised internally to signal that a model is recent enough and retraining should be skipped.

Handling Missing and Bad Data
------------------------------

Data completeness is checked before any model sees the input. The ``InsufficientlyCompleteError`` is the primary signal that you should either wait for more data or fall back to a simpler strategy.

.. code-block:: python

   from openstef_core.exceptions import (
       InsufficientlyCompleteError,
       FlatlinerDetectedError,
       PredictError,
   )
   from openstef_models.models.forecasting.base_case import BaseCaseForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   horizons = [LeadTime(timedelta(hours=h)) for h in range(1, 49)]

   def run_forecast(primary_model, dataset):
       try:
           return primary_model.predict(dataset)
       except InsufficientlyCompleteError as exc:
           # Log completeness ratio from the exception message, then fall back
           print(f"Data too sparse for primary model: {exc}")
           return run_base_case_fallback(dataset)
       except FlatlinerDetectedError:
           # Stuck sensor — base case is safer than a model trained on real variation
           print("Flatliner detected in input data, using base case")
           return run_base_case_fallback(dataset)
       except PredictError as exc:
           print(f"Primary model prediction failed: {exc}")
           return run_base_case_fallback(dataset)

   def run_base_case_fallback(dataset):
       forecaster = BaseCaseForecaster(
           quantiles=quantiles,
           horizons=horizons,
       )
       # BaseCaseForecaster does not require fitting — it repeats the last week
       return forecaster.predict(dataset)

.. note::

   ``BaseCaseForecaster`` requires no prior training. It repeats the most recent 7-day window of historical load as its forecast, falling back to the 14-day window if the 7-day window contains gaps. This makes it robust to exactly the conditions that break trained models.

The Base-Case Forecaster as a Safety Net
-----------------------------------------

The ``BaseCaseForecaster`` implements the assumption that energy load follows a weekly periodic pattern. It is intentionally simple: no gradient boosting, no feature engineering, no hyperparameter tuning. Its value in production is precisely that simplicity — it will produce a forecast as long as *any* historical data is available.

.. code-block:: python

   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   # Default: 7-day primary lag, 14-day fallback lag
   fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
   )

   # Custom lag windows — useful for assets with non-weekly periodicity
   industrial_fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14),
       ),
   )

Confidence intervals from the base-case forecaster are derived from the hourly standard deviation of the repeated historical window, so they widen appropriately when the historical pattern itself was variable.

.. note:: [VISUALIZATION: Side-by-side plot of primary model forecast vs. base-case fallback forecast for a 48-hour horizon, showing how the base case captures the weekly shape but misses short-term deviations]

Model Staleness Detection
--------------------------

A model that was accurate when trained can become unreliable as the underlying load pattern drifts. OpenSTEF signals this through the ``SkipFitting`` exception, which is raised internally when the pipeline determines a model is recent enough to skip retraining. The inverse — detecting that a model is *too old* — is your responsibility as the pipeline operator.

The recommended pattern is to record the training timestamp alongside every model artefact and enforce a maximum age policy before each inference run:

.. code-block:: python

   from datetime import datetime, timedelta, timezone
   from openstef_core.exceptions import ModelNotFoundError, ModelLoadingError

   MAX_MODEL_AGE = timedelta(days=7)

   def load_and_validate_model(model_store, model_id):
       """Load a model and raise if it is too stale to trust."""
       try:
           model, metadata = model_store.load(model_id)
       except ModelNotFoundError:
           raise RuntimeError(f"No model found for {model_id!r} — cannot forecast")
       except ModelLoadingError as exc:
           raise RuntimeError(f"Model artefact for {model_id!r} is corrupt: {exc}")

       trained_at = metadata.get("trained_at")
       if trained_at is None:
           raise RuntimeError("Model metadata missing 'trained_at' timestamp")

       age = datetime.now(tz=timezone.utc) - trained_at
       if age > MAX_MODEL_AGE:
           raise RuntimeError(
               f"Model {model_id!r} is {age.days} days old (limit: {MAX_MODEL_AGE.days}). "
               "Trigger retraining before forecasting."
           )

       return model

The ``SkipFitting`` exception is used internally by training pipelines to avoid unnecessary retraining when a model was recently fitted. If you are building a custom training loop, you can catch it to implement the same behaviour:

.. code-block:: python

   from openstef_core.exceptions import SkipFitting

   try:
       model.fit(training_dataset)
   except SkipFitting as reason:
       print(f"Retraining skipped: {reason}")
       # Continue using the existing model artefact

Graceful Degradation in Practice
----------------------------------

A production-grade pipeline typically implements a tiered fallback chain rather than a binary primary/fallback split. The tiers below reflect lessons from real deployments:

**Tier 1 — Primary model**
   The trained ML model (gradient boosting, neural network, or ensemble). Requires complete feature data and a model artefact younger than the staleness threshold.

**Tier 2 — Degraded-feature model**
   The same model, but with missing weather or exogenous features imputed from climatological averages. Useful when a weather feed is temporarily unavailable but the model artefact is healthy.

**Tier 3 — Base-case forecaster**
   ``BaseCaseForecaster`` with the 7-day lag. No feature engineering required — only historical load observations.

**Tier 4 — Extended base case**
   ``BaseCaseForecaster`` with the 14-day fallback lag. Used when even the most recent week of history is incomplete.

.. code-block:: python

   from openstef_core.exceptions import (
       InsufficientlyCompleteError,
       FlatlinerDetectedError,
       ModelLoadingError,
       ModelNotFoundError,
       PredictError,
   )

   def tiered_forecast(model_store, model_id, dataset, dataset_minimal):
       """Attempt forecast through a tiered fallback chain."""

       # Tier 1: primary model with full features
       try:
           model = load_and_validate_model(model_store, model_id)
           return model.predict(dataset), "primary"
       except (RuntimeError, PredictError, InsufficientlyCompleteError) as exc:
           print(f"Tier 1 failed: {exc}")

       # Tier 3: base case — 7-day lag
       try:
           fallback = BaseCaseForecaster(
               quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
               horizons=[LeadTime(timedelta(hours=1))],
           )
           return fallback.predict(dataset_minimal), "base_case_7d"
       except InsufficientlyCompleteError as exc:
           print(f"Tier 3 failed: {exc}")

       # Tier 4: base case — 14-day lag
       fallback_14d = BaseCaseForecaster(
           quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
           horizons=[LeadTime(timedelta(hours=1))],
           hyperparams=BaseCaseForecasterHyperParams(
               primary_lag=timedelta(days=14),
               fallback_lag=timedelta(days=14),
           ),
       )
       return fallback_14d.predict(dataset_minimal), "base_case_14d"

Always record which tier was used alongside the forecast output. This makes it straightforward to audit forecast quality retrospectively and to trigger alerts when the system spends too much time below Tier 1.

Monitoring and Alerting
------------------------

Reliability is not only about what happens when things go wrong — it is about knowing *when* things are going wrong. The evaluation pipeline (``openstef_beam.evaluation``) can be run continuously against recent forecasts to detect accuracy degradation before it becomes operationally significant.

Key signals to monitor in production:

- **Tier distribution** — what fraction of forecasts are being served from each fallback tier. A rising Tier 3/4 fraction indicates a data pipeline problem.
- **Model age** — days since last successful retraining per asset. Alert when this exceeds your staleness threshold.
- **Completeness ratio** — logged by ``InsufficientlyCompleteError``. A sustained drop indicates a sensor or feed outage.
- **Flatliner rate** — frequency of ``FlatlinerDetectedError`` per asset. Sudden spikes indicate sensor faults.

.. note::

   The ``EvaluationPipeline`` in ``openstef_beam.evaluation`` segments forecast accuracy by lead time and availability time, making it straightforward to detect whether degradation is concentrated in specific horizons — a common symptom of stale models that have drifted on seasonal patterns.

Related Topics
---------------

- :doc:`forecasting_basics` — what short-term forecasts represent and how the primary model pipeline works.
- :doc:`quantiles_and_confidence` — how confidence intervals are constructed, including by the base-case fallback.
- :doc:`feature_engineering` — which features are most sensitive to data quality issues and how missing values propagate.
- :doc:`meta_ensembles` — how ensemble approaches can themselves improve robustness by averaging over multiple model predictions.