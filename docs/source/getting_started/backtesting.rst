Backtesting
===========

Backtesting lets you evaluate how well a forecasting model would have performed on
historical data, simulating the real-time operational environment as faithfully as
possible. Rather than simply fitting a model to a held-out test set, OpenSTEF's
backtesting machinery replays the past: it generates predictions at regular intervals,
retrains the model on a rolling schedule, and — critically — never lets the model see
data it would not have had access to at prediction time. This page walks you through
setting up a backtest, interpreting the results, and comparing multiple models against
each other.

If you have not yet produced your first forecast, start with :doc:`first_forecast`
before continuing here. For customising the underlying forecaster itself, see
:doc:`advanced_customization`.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd


How OpenSTEF Backtesting Works
-------------------------------

The central class is ``BacktestPipeline``. It takes a ``BacktestConfig`` and a
forecaster object, then walks forward through your historical dataset emitting
*train* and *predict* events in chronological order. Three intervals govern the
simulation:

- **prediction_sample_interval** — the temporal resolution of each forecast output
  (e.g. 15 minutes). This must match the forecaster's own ``predict_sample_interval``.
- **predict_interval** — how often a new forecast is generated (e.g. every 6 hours).
- **train_interval** — how often the model is retrained from scratch on the data
  available up to that point (e.g. every 7 days).

Because the pipeline enforces a *restricted horizon* on the input data at every step,
there is no data leakage: the model at time *t* can only see observations with
timestamps strictly before *t*.


Configuring a Backtest
-----------------------

Start by importing the relevant classes and constructing a ``BacktestConfig``:

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting.pipeline import BacktestPipeline
    from openstef_beam.backtesting.pipeline import BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),  # output resolution
        predict_interval=timedelta(hours=6),               # how often to forecast
        train_interval=timedelta(days=7),                  # how often to retrain
        align_time=time.fromisoformat("00:00+00"),         # schedule anchor
    )

The defaults shown above are sensible starting points for a 15-minute energy
forecasting use case. Increase ``train_interval`` if retraining is expensive; decrease
``predict_interval`` if you need more frequent forecast updates.


Running the Pipeline
---------------------

``BacktestPipeline`` expects your forecaster to implement ``BacktestForecasterMixin``
(or ``BacktestBatchForecasterMixin`` for vectorised batch prediction). Pass your
configured forecaster together with the config, then call ``.run()``:

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_beam.backtesting.pipeline import BacktestPipeline

    # Assume `my_forecaster` already implements BacktestForecasterMixin
    pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

    predictions = pipeline.run(
        ground_truth=ground_truth_dataset,   # VersionedTimeSeriesDataset
        predictors=predictors_dataset,       # VersionedTimeSeriesDataset
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 30, tzinfo=timezone.utc),
        show_progress=True,
    )

``run()`` returns a ``VersionedTimeSeriesDataset`` containing every forecast produced
during the simulation window, annotated with the timestamp at which each forecast was
made and the data-availability horizon that was in effect at that moment. Passing
``start=None`` or ``end=None`` causes the pipeline to use the earliest or latest
timestamp present in the input data respectively.

.. note::

   The ``prediction_sample_interval`` in ``BacktestConfig`` must match the
   ``predict_sample_interval`` declared in your forecaster's own config. A
   ``ValueError`` is raised immediately on construction if they differ, so you will
   catch misconfiguration before any expensive computation begins.


Implementing the Forecaster Interface
--------------------------------------

Any class that implements ``BacktestForecasterMixin`` can be plugged into the pipeline.
The interface requires two things: a ``quantiles`` property and a ``predict`` method
that accepts a ``RestrictedHorizonVersionedTimeSeries``. The library ships a
``DummyForecaster`` that satisfies the interface without real prediction logic — useful
for smoke-testing your data pipeline before wiring in a real model:

.. code-block:: python

    from openstef_beam.backtesting.backtest_forecaster.dummy_forecaster import DummyForecaster
    from openstef_beam.backtesting.backtest_forecaster.mixins import BacktestForecasterConfig
    from datetime import timedelta

    dummy_config = BacktestForecasterConfig(
        predict_sample_interval=timedelta(minutes=15),
    )
    dummy = DummyForecaster(config=dummy_config)

    # Verify the pipeline wires up correctly before swapping in your real model
    pipeline = BacktestPipeline(config=config, forecaster=dummy)

For a production forecaster, subclass ``BacktestForecasterMixin``, implement
``predict()``, and optionally override the ``train()`` hook that the pipeline calls on
each retraining event.


Evaluating Forecast Accuracy
------------------------------

OpenSTEF provides a dedicated metrics module covering both deterministic and
probabilistic forecasts. The key deterministic metrics are:

- **MAE** (Mean Absolute Error) — interpretable in the same units as the load signal.
- **RMAE** (Relative MAE) — MAE normalised by the mean of the target, useful for
  comparing across substations with different load scales.
- **Completeness** — fraction of non-missing predictions, important when the model
  occasionally fails to produce output.

For probabilistic forecasts (quantile outputs), the module adds reliability and
sharpness metrics that assess whether confidence intervals are well-calibrated.

.. code-block:: python

    import numpy as np
    from openstef_beam.metrics.metrics_deterministic import mae, rmae, completeness

    # `predictions` and `actuals` are numpy arrays of the same shape
    y_true = np.array([100.0, 110.0, 105.0, 98.0, 102.0])
    y_pred = np.array([ 98.0, 113.0, 104.0, 99.0, 101.0])

    print(f"MAE:          {mae(y_true, y_pred):.2f} MW")
    print(f"RMAE:         {rmae(y_true, y_pred):.4f}")
    print(f"Completeness: {completeness(y_pred):.2%}")

The ``EvaluationPipeline`` class (used internally by the forecaster's ``score()``
method) can segment these metrics by forecast lead time and by sliding time window,
giving you a richer picture than a single aggregate number:

.. code-block:: python

    from openstef_beam.metrics.evaluation_pipeline import EvaluationPipeline, EvaluationConfig
    from datetime import timedelta

    eval_config = EvaluationConfig(
        available_ats=[],                           # evaluate all availability timestamps
        lead_times=[timedelta(hours=h) for h in [1, 6, 12, 24]],
    )

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=my_forecaster.quantiles,
        window_metric_providers=[],
        global_metric_providers=my_forecaster.evaluation_metrics,
    )

    result = eval_pipeline.run_for_subset(
        filtering=timedelta(hours=24),
        predictions=predictions,
    )
    global_metrics = result.get_global_metric()
    print(global_metrics)


Comparing Multiple Models
--------------------------

The recommended pattern for model comparison is to run ``BacktestPipeline`` once per
candidate model over the same historical window and the same input datasets, then
aggregate the per-model metrics into a summary table. Because every run uses identical
data and identical scheduling, differences in the numbers reflect genuine differences in
model quality rather than artefacts of different train/test splits.

.. code-block:: python

    import pandas as pd
    from openstef_beam.metrics.metrics_deterministic import mae, rmae

    models = {
        "xgboost": xgboost_forecaster,
        "linear":  linear_forecaster,
        "prophet": prophet_forecaster,
    }

    results = {}
    for name, forecaster in models.items():
        pipeline = BacktestPipeline(config=config, forecaster=forecaster)
        preds = pipeline.run(
            ground_truth=ground_truth_dataset,
            predictors=predictors_dataset,
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 6, 30, tzinfo=timezone.utc),
            show_progress=False,
        )
        # Align predictions with ground truth for scoring
        y_true, y_pred = align_predictions(preds, ground_truth_dataset)
        results[name] = {
            "MAE":          mae(y_true, y_pred),
            "RMAE":         rmae(y_true, y_pred),
            "Completeness": completeness(y_pred),
        }

    summary = pd.DataFrame(results).T.sort_values("MAE")
    print(summary)

.. note::

   Keep ``train_interval`` and ``predict_interval`` identical across all runs. Changing
   these between models introduces a confound: a model that trains more frequently will
   typically score better regardless of its intrinsic quality.


Visualising Backtest Results
-----------------------------

Once you have the predictions dataset from ``pipeline.run()``, you can plot forecast
vs. actuals for any sub-period to inspect where the model struggles. The
``VersionedTimeSeriesDataset`` returned by the pipeline can be converted to a pandas
``DataFrame`` for plotting:

.. code-block:: python

    import matplotlib.pyplot as plt

    # Select a representative week for visual inspection
    week_preds = predictions.to_pandas().loc["2024-03-04":"2024-03-10"]
    week_truth = ground_truth_dataset.to_pandas().loc["2024-03-04":"2024-03-10"]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(week_truth.index, week_truth["load"], label="Actual", color="black")
    ax.plot(week_preds.index, week_preds["forecast"], label="Forecast", color="steelblue")
    ax.set_ylabel("Load (MW)")
    ax.set_title("Backtest: forecast vs. actual (sample week)")
    ax.legend()
    plt.tight_layout()
    plt.show()

For lead-time breakdowns — showing how accuracy degrades as the horizon grows —
iterate over the ``lead_times`` you passed to ``EvaluationConfig`` and plot the
resulting MAE series:

.. code-block:: python

    lead_hours = [1, 6, 12, 24, 48]
    mae_by_lead = []

    for h in lead_hours:
        result = eval_pipeline.run_for_subset(
            filtering=timedelta(hours=h),
            predictions=predictions,
        )
        metric = result.get_global_metric()
        mae_by_lead.append(metric.metrics.get("mae", float("nan")))

    fig, ax = plt.subplots()
    ax.plot(lead_hours, mae_by_lead, marker="o")
    ax.set_xlabel("Forecast horizon (hours)")
    ax.set_ylabel("MAE (MW)")
    ax.set_title("Accuracy vs. forecast horizon")
    plt.tight_layout()
    plt.show()


Common Pitfalls
----------------

**Mismatched sample intervals**
  The most frequent error when setting up a backtest is a mismatch between
  ``BacktestConfig.prediction_sample_interval`` and the forecaster's own
  ``predict_sample_interval``. The pipeline raises a ``ValueError`` on construction,
  so fix this before calling ``.run()``.

**Insufficient historical depth**
  If your ``train_interval`` is 7 days but your dataset only covers 10 days, the first
  retraining event will have very little data. Aim for at least 3–4× the
  ``train_interval`` of historical data before the backtest start date.

**Comparing models with different predict intervals**
  A model that generates forecasts every hour will accumulate more predictions than one
  that forecasts every 6 hours. When computing aggregate metrics, make sure you are
  comparing the same set of forecast timestamps across models.

**Ignoring completeness**
  A model with a low MAE but a completeness of 0.7 is missing 30 % of its predictions
  — a serious operational problem. Always report completeness alongside accuracy
  metrics.


Next Steps
-----------

- :doc:`advanced_customization` — plug in custom feature engineering, model
  architectures, and training callbacks.
- :doc:`first_forecast` — revisit the end-to-end single-forecast workflow if you need
  a refresher on data preparation.
- :doc:`quickstart` — the minimal working example if you want a fast sanity check
  before running a full backtest.