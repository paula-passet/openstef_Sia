Reliability and Fallback Strategies
===================================

In production, forecasting pipelines encounter conditions that no model was trained to handle: sensors go dark, upstream data feeds stall, meters flatline, and trained models grow stale as load patterns shift. This page explains how OpenSTEF addresses these situations — through structured data validation, a built-in baseline fallback model, and the exception types that signal when graceful degradation should kick in.

For background on what the forecasts themselves represent, see :doc:`forecasting_basics`. For how uncertainty is expressed in the output, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/reliability_and_fallback_diagram_1.mmd

Data Validation Before Inference
---------------------------------

Bad input data is the most common source of silent forecast failures. A model will produce a number regardless of whether its inputs are meaningful — which is why OpenSTEF applies explicit validation transforms before any model sees the data.

Three validators ship in ``openstef_models.transforms.validation``:

- **CompletenessChecker** — measures the ratio of non-missing values across selected columns and raises ``InsufficientlyCompleteError`` if the dataset falls below a configurable threshold.
- **FlatlineChecker** — detects long segments where a sensor has stopped updating and is simply repeating the same value, a common failure mode for smart meters and weather feeds.
- **InputConsistencyChecker** — verifies that the columns present at inference time match what the model was trained on.

A typical validation setup looks like this:

.. code-block:: python

    import numpy as np
    import pandas as pd
    from datetime import timedelta

    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.validation import (
        CompletenessChecker,
        FlatlineChecker,
        InputConsistencyChecker,
    )

    # Build a dataset with some missing values
    data = pd.DataFrame(
        {
            "load": [100.0, np.nan, 102.0, np.nan],
            "temperature": [15.0, 15.2, np.nan, 15.5],
            "radiation": [0.0, 0.0, 0.0, 0.0],  # potential flatline
        },
        index=pd.date_range("2025-06-01", periods=4, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    # Completeness check — raises InsufficientlyCompleteError if too many NaNs
    completeness_check = CompletenessChecker(columns=["load", "temperature"])
    completeness_check.transform(dataset)

    # Flatline check — raises if a column is stuck for too long
    flatline_check = FlatlineChecker()
    flatline_check.transform(dataset)

These transforms are designed to be composed into a preprocessing pipeline. When one raises, the calling code can catch the exception and route to a fallback rather than letting a degraded forecast propagate downstream.

.. note::

   ``CompletenessChecker`` accepts a ``columns`` argument to focus on the features that matter most for a given model. Weighting individual columns is also supported for cases where some inputs are more critical than others.

Handling Insufficient Training Data
-------------------------------------

During model training, OpenSTEF raises ``InsufficientlyCompleteError`` when the target column contains too many missing values to fit a reliable model. This is intentional: fitting on a sparse target produces a model that will underperform in ways that are hard to detect later.

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    try:
        pipeline.fit(training_data)
    except InsufficientlyCompleteError as exc:
        # Log and skip retraining; keep the previously trained model
        logger.warning("Skipping model retraining: %s", exc)

The same exception surfaces at inference time when the input dataset is too sparse to produce a trustworthy forecast. Catching it at the pipeline boundary is the recommended pattern for deciding whether to fall back.

The BaseCaseForecaster: A Principled Fallback
----------------------------------------------

When a primary model cannot run — because validation failed, training data was insufficient, or the model artefact is unavailable — OpenSTEF provides ``BaseCaseForecaster`` as a drop-in fallback. Rather than returning zeros or propagating an error, it repeats the most recent weekly pattern from historical data, which is a reasonable approximation for most grid-connected loads.

The forecaster uses two configurable lags:

- **primary_lag** (default: 7 days) — the most recent week of actuals to repeat.
- **fallback_lag** (default: 14 days) — used when the primary lag window itself contains gaps.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.base_case import (
        BaseCaseForecaster,
        BaseCaseForecasterHyperParams,
    )

    # Standard fallback: repeat last week, fall back to two weeks ago
    fallback = BaseCaseForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=1))],
    )

    # Tighter fallback window for assets with less stable weekly patterns
    fallback_custom = BaseCaseForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=1))],
        hyperparams=BaseCaseForecasterHyperParams(
            primary_lag=timedelta(days=7),
            fallback_lag=timedelta(days=14),
        ),
    )

Confidence intervals for the base case are derived from the hourly standard deviation of the repeated historical window, so the output remains probabilistic and compatible with downstream consumers that expect quantile forecasts. See :doc:`quantiles_and_confidence` for how these intervals are interpreted.

.. note:: [VISUALIZATION: Side-by-side plot of a primary model forecast vs. BaseCaseForecaster output for the same horizon, showing how the fallback tracks the weekly pattern with wider confidence bands]

Graceful Degradation in Practice
----------------------------------

The recommended production pattern is a try/except chain that attempts the primary model first and falls back progressively:

.. code-block:: python

    from openstef_core.exceptions import InsufficientlyCompleteError

    def produce_forecast(dataset, primary_model, fallback_model):
        """Attempt primary forecast; degrade to base case on failure."""
        try:
            # Validate inputs before inference
            completeness_check.transform(dataset)
            flatline_check.transform(dataset)
            return primary_model.predict(dataset)

        except InsufficientlyCompleteError as exc:
            logger.warning(
                "Input data insufficient for primary model (%s). "
                "Using base case fallback.",
                exc,
            )
            # BaseCaseForecaster only needs the target history,
            # so it is robust to missing feature columns
            return fallback_model.predict(dataset)

        except Exception as exc:
            logger.error("Unexpected forecasting failure: %s", exc, exc_info=True)
            raise

A few principles worth noting from production experience:

- **Fail loudly at training, quietly at inference.** Raising during training prevents a bad model from being deployed. At inference time, returning a base-case forecast is almost always preferable to returning nothing, provided the degradation is logged and monitored.
- **Log which path was taken.** Downstream systems consuming forecasts rarely know whether they received a primary or fallback forecast. Tagging the output with a ``forecast_source`` field (e.g., ``"primary"`` vs. ``"base_case"``) makes it possible to track fallback frequency in dashboards.
- **Monitor fallback rate as a health signal.** A rising fallback rate is an early warning of data feed degradation or model staleness — often before any explicit alert fires.

Model Staleness
----------------

A model trained weeks or months ago may have been accurate when deployed but can drift as load patterns shift — due to new industrial consumers, seasonal changes, or grid topology updates. OpenSTEF does not currently provide an automated staleness detector, but the ``EvaluationPipeline`` in ``openstef_beam`` can be run periodically against recent actuals to surface performance degradation before it becomes operationally significant.

.. code-block:: python

    from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
    from openstef_core.types import Quantile
    from datetime import timedelta

    config = EvaluationConfig()  # uses default lead times and windows
    evaluator = EvaluationPipeline(
        config=config,
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        window_metric_providers=[...],
        global_metric_providers=[...],
    )

    report = evaluator.run(
        predictions=recent_predictions,
        ground_truth=recent_actuals,
        target_column="load",
    )

A practical staleness heuristic: if the rolling skill score of the primary model approaches that of the ``BaseCaseForecaster`` over a sustained window (e.g., two weeks), the model should be retrained. Comparing primary model metrics against the base case gives a meaningful, interpretable threshold rather than an arbitrary absolute error cutoff.

.. note::

   Retraining frequency depends on how quickly load patterns change at a given location. Substations serving rapidly growing areas or sites with intermittent large consumers typically need more frequent retraining than stable residential feeders.

Summary
--------

OpenSTEF's reliability layer rests on three interlocking mechanisms:

- **Validation transforms** (``CompletenessChecker``, ``FlatlineChecker``, ``InputConsistencyChecker``) catch bad data before it reaches the model.
- **``InsufficientlyCompleteError``** provides a typed signal that calling code can catch to trigger fallback logic.
- **``BaseCaseForecaster``** delivers a probabilistic, weekly-pattern-based forecast when the primary model cannot run, ensuring the pipeline always produces output.

Together these allow a production system to degrade gracefully under data feed failures, model artefact issues, or training data gaps, while maintaining observability through structured logging and periodic evaluation.

For related topics, see :doc:`feature_engineering` for how input features are constructed and validated, and :doc:`meta_ensembles` for how ensemble approaches can themselves improve robustness by combining multiple model signals.