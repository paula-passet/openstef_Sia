Reliability and Fallback Strategies
====================================

In a production energy forecasting system, things go wrong: sensors flatline, upstream
data feeds arrive late, models grow stale, or training simply fails due to insufficient
data. OpenSTEF is designed with these realities in mind. Rather than crashing silently
or producing garbage forecasts, the library provides a layered set of mechanisms —
input validation, automatic staleness detection, and a dedicated baseline forecaster —
that together give your system a path to graceful degradation instead of hard failure.

This page explains each layer, when it activates, and how to configure it for your
deployment. For background on the forecasting pipeline itself, see
:doc:`forecasting_basics`. For details on the probabilistic outputs that these
mechanisms preserve, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Three-layer reliability stack — Input Validation → Model Staleness Check → Baseline Fallback — with arrows showing the path a forecast request takes through each gate]

---

Input Validation: Catching Bad Data Before It Reaches the Model
----------------------------------------------------------------

The first line of defence is a set of transform-based validators that run on every
dataset before it is passed to a model. These are not optional quality checks you wire
up yourself — they are built into the standard workflow pipelines and execute
automatically.

**FlatlineChecker**

A *flatliner* is a stretch of measurements where the load value stays suspiciously
constant, almost always indicating a stuck sensor, a broken data pipeline, or a
transmission error. ``FlatlineChecker`` scans the target column and raises
``FlatlinerDetectedError`` when it detects such a pattern.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import FlatlineChecker

    # Build a dataset where the load is stuck at 110 for three hours
    data = pd.DataFrame(
        {"load": [100, 110, 110, 110]},
        index=pd.date_range("2025-01-01", periods=4, freq="1h"),
    )
    dataset = TimeSeriesDataset(data, timedelta(hours=1))

    checker = FlatlineChecker(
        flatliner_threshold=timedelta(hours=2),
        detect_non_zero_flatliner=True,  # catch non-zero flatlines too
        relative_tolerance=1e-5,
    )

    try:
        checker.fit_transform(dataset)
    except FlatlinerDetectedError as e:
        # Log the anomaly and route to the fallback path
        print(f"Flatliner detected: {e}")

By default the workflow pipelines set ``error_on_flatliner=False``, meaning the checker
logs a warning rather than raising an exception. You can tighten this to ``True`` in
environments where a stuck sensor should halt the forecast entirely and trigger an
alert.

**InputConsistencyChecker**

``InputConsistencyChecker`` validates that the feature columns present at prediction
time match those seen during training. Schema drift — a column renamed in an upstream
ETL job, a weather provider changing its API — is one of the most common silent failure
modes in production ML. This checker surfaces the mismatch immediately rather than
letting the model produce a forecast with an incomplete feature set.

**InsufficientlyCompleteError**

During training, if dropping rows with ``NaN`` targets leaves an empty dataset, the
library raises ``InsufficientlyCompleteError``. Catching this exception in your
orchestration layer is the correct place to decide whether to skip retraining and keep
the existing model, or to escalate to an alert.

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    try:
        workflow.fit(dataset)
    except InsufficientlyCompleteError:
        # Retraining skipped — existing model remains in service
        print("Insufficient training data; retaining current model.")

---

Model Staleness Detection
--------------------------

Even a perfectly trained model degrades over time. Energy consumption patterns shift
with seasons, new loads come online, and the statistical relationship between features
and target drifts. OpenSTEF's workflow layer tracks model age and can automatically
skip reuse of models that have grown too old.

The relevant configuration lives in the ``MLFlowStorageCallback`` (and the equivalent
ensemble workflow config):

.. code-block:: python

    from datetime import timedelta
    from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig

    config = ForecastingWorkflowConfig(
        model_id="substation_42",
        # Reuse the stored model only if it was trained within the last 7 days
        model_reuse_enable=True,
        model_reuse_max_age=timedelta(days=7),
        # When a new model is trained, only replace the stored one if it
        # outperforms the old model (after applying a penalty to bias toward
        # newer models)
        model_selection_enable=True,
        model_selection_metric=("Q0.5", "R2", "higher_is_better"),
        model_selection_old_model_penalty=1.2,
        # ... other config fields
    )

When ``model_reuse_enable=True`` and the stored model's age exceeds
``model_reuse_max_age``, the workflow triggers a full retraining cycle on the next
``fit()`` call rather than loading the stale artifact. The
``model_selection_old_model_penalty`` parameter is worth understanding: a value of
``1.2`` means the new model's metric must be at least 20 % better than the old model's
metric before the old model is replaced. This prevents noisy training runs from
accidentally degrading a well-performing production model.

.. note::

   Setting ``model_reuse_max_age`` too aggressively (e.g., ``timedelta(hours=6)``)
   means retraining happens very frequently, which is expensive. Setting it too
   loosely means the model may be operating on outdated patterns. A value of 1–7 days
   is typical for substations with stable load profiles; volatile or rapidly changing
   loads may warrant shorter windows.

---

The Baseline Fallback: ``BaseCaseForecaster``
----------------------------------------------

When a trained ML model is genuinely unavailable — the training pipeline has not yet
run, the stored artifact is corrupted, or the model age check has invalidated it and
retraining has not yet succeeded — you still need to produce a forecast. The
``BaseCaseForecaster`` is OpenSTEF's answer to this problem.

It implements a simple but surprisingly robust heuristic: energy load patterns are
weekly-periodic, so the best naive guess for next Tuesday at 14:00 is what happened
last Tuesday at 14:00. The forecaster repeats the last week of historical data
(``primary_lag``, default 7 days) and fills any gaps in that window from two weeks ago
(``fallback_lag``, default 14 days). Confidence intervals are derived from the hourly
standard deviation of the repeated base case.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    import numpy as np
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case_forecaster import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )
    from openstef_core.datasets import TimeSeriesDataset

    # Simulate two weeks of historical load at 15-minute resolution
    index = pd.date_range("2025-01-01", periods=2 * 7 * 96, freq="15min")
    rng = np.random.default_rng(0)
    load = 200 + 50 * np.sin(np.linspace(0, 4 * np.pi, len(index))) + rng.normal(0, 5, len(index))
    history = TimeSeriesDataset(
        pd.DataFrame({"load": load}, index=index),
        timedelta(minutes=15),
    )

    forecaster = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 49)],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

    forecaster.fit(history)
    forecast = forecaster.predict(history)

The ``BaseCaseForecaster`` is intentionally simple. It will not outperform a
well-trained gradient boosting model, but it will produce a *reasonable* forecast under
any data conditions, which is exactly what you need from a fallback. In operational
terms, it acts as the floor of your reliability stack.

A common pattern is to wrap your primary workflow call in a try/except and fall back to
the base case forecaster when the primary path raises:

.. code-block:: python

    from openstef_core.exceptions import NotFittedError, InsufficientlyCompleteError

    def get_forecast(workflow, base_case_forecaster, dataset):
        """Return a forecast, falling back to the base case on primary failure."""
        try:
            return workflow.predict(dataset)
        except (NotFittedError, InsufficientlyCompleteError) as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Primary model unavailable (%s); using base case fallback.", exc
            )
            return base_case_forecaster.predict(dataset)

---

Putting It Together: A Layered Reliability Strategy
-----------------------------------------------------

The three mechanisms described above are not mutually exclusive — they form a stack:

- **Layer 1 — Input validation** (``FlatlineChecker``, ``InputConsistencyChecker``):
  Catches bad or schema-drifted data before it corrupts a forecast or a training run.
  Configure ``error_on_flatliner`` and handle ``InsufficientlyCompleteError`` in your
  orchestration layer.

- **Layer 2 — Staleness management** (``model_reuse_max_age``,
  ``model_selection_enable``): Ensures the model in service is not too old and that
  retraining only replaces a model when the replacement is genuinely better.

- **Layer 3 — Baseline fallback** (``BaseCaseForecaster``): Provides a always-available
  forecast of last resort based purely on historical weekly patterns, requiring no
  trained ML artifact.

Deploying all three layers means your system can tolerate sensor anomalies, ETL
failures, and training pipeline outages without producing silent errors or missing
forecast windows entirely.

.. note::

   The validators and staleness checks are already wired into the standard
   ``EnsembleForecastingWorkflowConfig`` pipeline. You do not need to assemble them
   manually unless you are building a custom workflow. See the
   :doc:`model_selection` page for guidance on choosing and configuring the primary
   model that sits above this fallback stack.

---

Configuration Reference
------------------------

The table below summarises the key reliability-related configuration fields and their
defaults.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Field
     - Default
     - Purpose
   * - ``model_reuse_enable``
     - ``True``
     - Whether to attempt loading a stored model before retraining.
   * - ``model_reuse_max_age``
     - ``timedelta(days=7)``
     - Maximum age of a stored model before it is considered stale.
   * - ``model_selection_enable``
     - ``True``
     - Whether to compare new and old model metrics before replacing.
   * - ``model_selection_old_model_penalty``
     - ``1.2``
     - Multiplicative penalty applied to the old model's metric; new model must exceed this threshold to replace it.
   * - ``flatliner_threshold``
     - *(workflow-specific)*
     - Duration of constant load that triggers a flatliner detection.
   * - ``detect_non_zero_flatliner``
     - ``False``
     - Whether to flag non-zero constant stretches (not just zero-load flatlines).
   * - ``error_on_flatliner``
     - ``False``
     - Whether to raise ``FlatlinerDetectedError`` or log a warning.