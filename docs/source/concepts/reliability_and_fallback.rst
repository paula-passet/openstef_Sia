Reliability and Fallback Strategies
===================================

In a live energy forecasting system, models do not always behave as expected.
Sensors go offline, data pipelines stall, weather feeds arrive late, and
occasionally a trained model simply produces nonsense. This page covers how
OpenSTEF handles these situations: how bad or missing data is detected before
it reaches a model, how the library signals that something is wrong, and how
a ``BaseCaseForecaster`` can stand in when the primary model cannot be trusted.

For background on what a forecast is and why it matters, see
:doc:`forecasting_basics`. For probabilistic output and confidence intervals,
see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Data Validation Before Forecasting
-----------------------------------

The first line of defence is rejecting bad input before it ever reaches a
model. OpenSTEF provides three composable validation transforms in
``openstef_models.transforms.validation``:

- ``CompletenessChecker`` — raises ``InsufficientlyCompleteError`` when too
  many values in a time series are missing.
- ``FlatlineChecker`` — detects long runs of identical values, which usually
  indicate a stuck sensor rather than real load.
- ``InputConsistencyChecker`` — verifies that the columns expected by the
  model are actually present in the incoming dataset.

Each transform is a ``TimeSeriesTransform`` that can be inserted into a
preprocessing pipeline. They raise structured exceptions rather than silently
dropping data, so the calling code can decide what to do next.

.. code-block:: python

    from datetime import datetime, timedelta
    import numpy as np
    import pandas as pd

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.exceptions import InsufficientlyCompleteError
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
    )

    # Build a dataset with 25 % of values missing
    index = pd.date_range("2024-01-01", periods=96, freq="15min")
    values = np.random.rand(96)
    values[::4] = np.nan          # every fourth point is missing
    df = pd.DataFrame({"load": values}, index=index)
    dataset = TimeSeriesDataset(data=df)

    checker = CompletenessChecker(
        columns=["load"],
        completeness_threshold=0.5,   # require at least 50 % present
    )

    try:
        checker.transform(dataset)
    except InsufficientlyCompleteError as exc:
        print(f"Data rejected: {exc}")
        # → trigger fallback logic here

The ``completeness_threshold`` is the key tuning parameter. A threshold of
``0.5`` means the pipeline tolerates up to half the values being absent before
refusing to proceed. In practice, thresholds between ``0.7`` and ``0.9`` are
common for training data, while inference pipelines are often more lenient
because a partial forecast is still better than no forecast.

.. note::

   ``FlatlineChecker`` uses a configurable ``window`` (default 96 samples,
   i.e. 24 hours at 15-minute resolution) and a ``threshold`` that controls
   how many consecutive identical values constitute a flatline. Tune both to
   match your meter resolution and expected load variability.

The Fallback Model: ``BaseCaseForecaster``
------------------------------------------

When the primary model cannot run — because training data is insufficient,
because the model artefact is stale, or because validation has rejected the
input — OpenSTEF provides ``BaseCaseForecaster`` as a principled fallback.

The idea is simple: energy load is strongly periodic on a weekly cycle.
If nothing better is available, repeating last week's observed values is a
reasonable approximation. ``BaseCaseForecaster`` does exactly this, with a
secondary fallback to the week before that if the primary lag window contains
gaps.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),    # repeat last week
            fallback_lag=timedelta(days=14),  # or the week before
        ),
    )

The confidence intervals produced by ``BaseCaseForecaster`` are derived from
the hourly standard deviation of the repeated base data, so they widen
automatically when the historical period was itself variable. This means
downstream consumers of probabilistic forecasts (see
:doc:`quantiles_and_confidence`) receive honest uncertainty estimates even
during degraded operation.

.. note:: [VISUALIZATION: Side-by-side plot of primary model forecast vs. BaseCaseForecaster fallback for the same 24-hour window, showing wider confidence bands on the fallback]

Graceful Degradation in Practice
----------------------------------

A robust production pipeline wraps the primary forecast attempt in a
try/except block and falls back explicitly rather than propagating an
exception to the caller. The pattern below illustrates the structure:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    def run_forecast(primary_model, fallback_model, dataset):
        """Run primary model; fall back gracefully on known failure modes."""
        try:
            # Validation transforms run inside prepare_input;
            # they raise InsufficientlyCompleteError on bad data.
            return primary_model.predict(dataset), "primary"

        except InsufficientlyCompleteError as exc:
            # Input data is too sparse — use the periodic baseline.
            import warnings
            warnings.warn(
                f"Primary forecast skipped due to data quality: {exc}. "
                "Falling back to BaseCaseForecaster.",
                RuntimeWarning,
                stacklevel=2,
            )
            return fallback_model.predict(dataset), "fallback"

        except Exception as exc:
            # Unexpected model failure — still prefer a degraded forecast
            # over raising to the caller.
            import warnings
            warnings.warn(
                f"Primary forecast failed unexpectedly: {exc}. "
                "Falling back to BaseCaseForecaster.",
                RuntimeWarning,
                stacklevel=2,
            )
            return fallback_model.predict(dataset), "fallback"

Returning the source label (``"primary"`` or ``"fallback"``) alongside the
forecast is important: it lets monitoring systems track how often the fallback
is activated and alert operators when the rate climbs above a baseline.

Model Staleness
----------------

A model that was trained months ago on a different load regime can be worse
than the periodic baseline. Staleness manifests in two ways:

**Concept drift** — the underlying load pattern has shifted (new large
consumers, changed operating hours, seasonal baseline shift) so the model's
learned weights no longer reflect reality.

**Feature drift** — the distribution of input features has changed, for
example because a weather provider changed its units or a sensor was replaced
with one that has a different calibration.

OpenSTEF's evaluation pipeline (``openstef_beam.evaluation``) is designed to
be run continuously against live data. The ``EvaluationPipeline`` computes
metrics across rolling time windows, which makes it straightforward to detect
when performance has degraded beyond an acceptable threshold:

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.evaluation.evaluation_pipeline import (
        EvaluationConfig,
        EvaluationPipeline,
    )
    from openstef_core.types import LeadTime, Quantile, Window, AvailableAt

    config = EvaluationConfig(
        lead_times=[LeadTime.from_string("PT24H")],
        windows=[
            Window(lag=timedelta(hours=0), size=timedelta(days=7)),   # last week
            Window(lag=timedelta(days=7),  size=timedelta(days=7)),   # week before
        ],
    )

    # Run evaluation; compare the two windows to detect drift.
    # If the recent window is significantly worse, trigger retraining.

A simple staleness heuristic is to compare the median absolute error (MAE)
of the most recent rolling window against a long-term baseline. If the ratio
exceeds a threshold (e.g. 1.5×), the model should be retrained or replaced
with the fallback until a fresh model is available.

.. note::

   There is no universal staleness threshold. A model serving a stable
   industrial load can remain valid for months; a model for a mixed
   residential/commercial feeder may drift within weeks after a public
   holiday period or a seasonal transition. Calibrate thresholds using
   historical evaluation runs before deploying automated retraining triggers.

Handling Missing Features at Inference Time
--------------------------------------------

Even when the target load series is complete, individual features may be
absent at inference time — a weather API may be slow, or a derived feature
may fail to compute. The ``InputConsistencyChecker`` catches the case where
expected columns are entirely absent. For partially missing feature values,
the preprocessing pipeline applies forward-fill and interpolation before the
model sees the data.

If a critical feature (such as temperature) is missing for the entire forecast
horizon, the safest response is to fall back to ``BaseCaseForecaster``, which
requires only the historical target series and no external features at all.
This makes it a robust last resort regardless of which upstream dependency
has failed.

.. code-block:: python

    from openstef_models.transforms.validation import InputConsistencyChecker
    from openstef_core.exceptions import InsufficientlyCompleteError

    checker = InputConsistencyChecker(required_columns=["temperature", "irradiance"])

    try:
        checker.transform(inference_dataset)
    except InsufficientlyCompleteError:
        # Critical features absent — skip primary model entirely
        forecast, source = fallback_model.predict(inference_dataset), "fallback"

Summary
--------

Reliable production forecasting in OpenSTEF rests on three practices:

- **Validate early.** Use ``CompletenessChecker``, ``FlatlineChecker``, and
  ``InputConsistencyChecker`` to reject bad data before it reaches the model,
  and handle ``InsufficientlyCompleteError`` explicitly.
- **Fall back intentionally.** ``BaseCaseForecaster`` provides a principled
  periodic baseline that requires only historical load data. Wire it in as an
  explicit fallback rather than letting exceptions propagate.
- **Monitor continuously.** Use rolling evaluation windows to detect concept
  drift and trigger retraining before model staleness degrades forecast
  quality below the baseline.

For the feature engineering decisions that affect what can go wrong at
inference time, see :doc:`feature_engineering`. For how ensemble approaches
can themselves improve robustness by combining multiple models, see
:doc:`meta_ensembles`.