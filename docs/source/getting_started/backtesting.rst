Backtesting Models with Historical Data
=======================================

Backtesting is the process of evaluating a forecasting model's performance by
replaying it against historical data as if it were operating in real time. Rather
than simply fitting a model to a held-out test set, a proper backtest respects the
temporal constraints that exist in production: the model only sees data that would
have been available at each prediction moment, and it retrains on the schedule it
would follow operationally.

This page walks through the full backtesting workflow in OpenSTEF — configuring the
pipeline, running it against historical data, computing evaluation metrics, and
comparing multiple models side by side.

If you haven't yet produced your first forecast, start with :doc:`first_forecast`
before continuing here. For information on customising the underlying forecaster,
see :doc:`advanced_customization`.


How OpenSTEF Backtesting Works
-------------------------------

OpenSTEF's backtesting machinery is built around two classes:

- **BacktestConfig** — declares the operational cadence: how often predictions are
  generated, how often the model is retrained, and what the prediction sample
  interval is.
- **BacktestPipeline** — orchestrates the simulation. It walks forward through time,
  fires training and prediction events on schedule, and collects every forecast into
  a single ``TimeSeriesDataset`` for later analysis.

The pipeline is deliberately strict about data leakage. At every prediction event it
constructs a point-in-time view of both the ground truth and the predictor features,
ensuring that no future information bleeds into the model. This makes backtest
results a faithful proxy for live performance.

.. note:: [DIAGRAM: Timeline showing alternating train and predict events stepping
   forward through a historical window, with the available-data horizon advancing
   at each step.]


Setting Up the Backtest Configuration
--------------------------------------

``BacktestConfig`` controls three timing parameters:

- ``prediction_sample_interval`` — the resolution of individual forecast samples
  (default: 15 minutes). **Must match** the forecaster's own
  ``predict_sample_interval``.
- ``predict_interval`` — how often a new forecast is generated during the backtest
  window (default: 6 hours).
- ``train_interval`` — how often the model is retrained from scratch (default: 7
  days).

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting import BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
        align_time=time.fromisoformat("00:00+00"),
    )

Choose ``predict_interval`` to match your operational cadence. For a day-ahead
forecasting system that publishes a new forecast every six hours, the default is
appropriate. For intra-day systems you might reduce it to one or two hours.

``train_interval`` governs how stale the model is allowed to become. A weekly
retraining cycle is a reasonable starting point; you can tune this based on the
performance-over-time analysis described later in this page.

.. warning::

   ``BacktestConfig.prediction_sample_interval`` must equal
   ``forecaster.config.predict_sample_interval``. The pipeline raises a
   ``ValueError`` at construction time if these values differ, so mismatches are
   caught early.


Preparing Historical Data
--------------------------

The pipeline expects two ``VersionedTimeSeriesDataset`` objects:

- **ground_truth** — the historical target values (e.g. measured load in MW).
- **predictors** — all feature data (weather forecasts, calendar features, etc.).

``VersionedTimeSeriesDataset`` tracks *when* each data point became available, which
is what enables the point-in-time reconstruction described above. The simplest way
to construct one from a ``pandas.DataFrame`` is ``from_dataframe``:

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef_core.datasets import VersionedTimeSeriesDataset

    # Load your historical target series
    target_df = pd.read_csv("load_history.csv", index_col="timestamp", parse_dates=True)

    ground_truth = VersionedTimeSeriesDataset.from_dataframe(
        target_df,
        sample_interval=timedelta(minutes=15),
    )

    # Load predictor features (weather, calendar, etc.)
    features_df = pd.read_csv("features_history.csv", index_col="timestamp", parse_dates=True)

    predictors = VersionedTimeSeriesDataset.from_dataframe(
        features_df,
        sample_interval=timedelta(minutes=15),
    )

Both datasets should span the same period and have a ``DatetimeIndex`` named
``timestamp``. Gaps are tolerated — the pipeline enforces minimum coverage
thresholds defined on the forecaster config rather than requiring perfectly dense
data.


Running the Backtest
---------------------

With config and data in hand, construct a ``BacktestPipeline`` and call ``run``:

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_beam.backtesting import BacktestPipeline

    pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

    predictions = pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 30, tzinfo=timezone.utc),
        show_progress=True,
    )

``run`` returns a ``TimeSeriesDataset`` containing every forecast generated during
the window. Each row carries both the predicted value and an ``available_at``
timestamp recording when that prediction was made, so you can later slice by lead
time or analyse forecast freshness.

Setting ``start`` and ``end`` to ``None`` uses the full extent of the provided
datasets, which is convenient during exploratory analysis.


Computing Evaluation Metrics
-----------------------------

Once you have the predictions dataset, align it with ground truth to compute error
metrics. The key step is matching each predicted value to the corresponding observed
value at the same timestamp:

.. code-block:: python

    import pandas as pd
    import numpy as np

    # Convert to DataFrames for metric computation
    pred_df = predictions.data.rename(columns={"value": "forecast"})
    obs_df = target_df.rename(columns={"load": "observed"})

    # Align on timestamp
    results = pred_df.join(obs_df, how="inner")
    results["error"] = results["forecast"] - results["observed"]
    results["abs_error"] = results["error"].abs()
    results["sq_error"] = results["error"] ** 2

    mae  = results["abs_error"].mean()
    rmse = np.sqrt(results["sq_error"].mean())
    mape = (results["abs_error"] / results["observed"].abs()).mean() * 100

    print(f"MAE:  {mae:.3f} MW")
    print(f"RMSE: {rmse:.3f} MW")
    print(f"MAPE: {mape:.2f} %")

**MAE** (Mean Absolute Error) is the most interpretable metric for energy
forecasting — it carries the same unit as the target and is not disproportionately
influenced by outliers. **RMSE** penalises large errors more heavily, making it
useful when peak-load accuracy is critical. **MAPE** expresses error as a
percentage, which aids comparison across substations or time periods with different
load magnitudes.


Analysing Performance Over Time
---------------------------------

A single aggregate metric hides important structure. Plotting error over a rolling
window reveals seasonal degradation, the impact of retraining events, and periods
where the model struggles:

.. code-block:: python

    # Rolling 7-day MAE
    rolling_mae = (
        results["abs_error"]
        .resample("D")
        .mean()
        .rolling(7, min_periods=1)
        .mean()
    )

    rolling_mae.plot(
        title="Rolling 7-day MAE",
        ylabel="MAE (MW)",
        xlabel="Date",
        figsize=(12, 4),
    )

Look for:

- **Upward trends** between retraining events — a sign that ``train_interval``
  should be shortened.
- **Seasonal spikes** around holidays or weather extremes — these may warrant
  dedicated feature engineering.
- **Step improvements** after a retraining event — confirmation that the model
  benefits from fresh data.

OpenSTEF also provides ``WindowedMetricVisualization`` for richer interactive
analysis of windowed metrics across multiple runs. See the API reference for
details.


Comparing Two Models
---------------------

The most common use of backtesting is head-to-head model comparison. Run the same
pipeline with two different forecasters and collect the results:

.. code-block:: python

    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    # Both forecasters share the same config
    pipeline_a = BacktestPipeline(config=config, forecaster=forecaster_a)
    pipeline_b = BacktestPipeline(config=config, forecaster=forecaster_b)

    preds_a = pipeline_a.run(ground_truth, predictors, start=start, end=end)
    preds_b = pipeline_b.run(ground_truth, predictors, start=start, end=end)

    # Build a comparison table
    def summarise(preds, obs, label):
        df = preds.data.rename(columns={"value": "forecast"}).join(obs, how="inner")
        err = (df["forecast"] - df["observed"]).abs()
        return {"model": label, "MAE": err.mean(), "RMSE": np.sqrt((err**2).mean())}

    comparison = pd.DataFrame([
        summarise(preds_a, obs_df["observed"], "Model A"),
        summarise(preds_b, obs_df["observed"], "Model B"),
    ]).set_index("model")

    print(comparison.round(3))

.. note::

   For a fair comparison, both pipelines must use identical ``start``/``end``
   boundaries and the same ``ground_truth`` and ``predictors`` datasets. Any
   difference in data availability will skew the results.

Beyond aggregate metrics, compare the rolling MAE curves side by side. A model with
a slightly higher overall MAE but a flatter rolling curve may be preferable in
production because its errors are more predictable and it degrades less between
retraining cycles.


Avoiding Common Pitfalls
-------------------------

**Data leakage**
   Always use ``VersionedTimeSeriesDataset`` with accurate ``available_at``
   timestamps. If you construct the dataset from a flat DataFrame without
   availability metadata, the pipeline assumes all data was available at the
   earliest timestamp — which is optimistic and will inflate apparent performance.

**Insufficient warm-up data**
   The first training event requires ``training_context_length`` of history before
   ``start``. If your dataset begins exactly at ``start``, the first training window
   will be empty and the pipeline will skip it. Provide data that extends at least
   ``training_context_length`` before your intended backtest start date.

**Mismatched sample intervals**
   ``BacktestConfig.prediction_sample_interval`` must match the forecaster's
   ``predict_sample_interval``. The pipeline validates this at construction and
   raises ``ValueError`` if they differ.

**Comparing models on different data subsets**
   If one model requires longer context than another, the effective evaluation
   window may differ. Pin both ``start`` and ``end`` explicitly rather than relying
   on ``None`` defaults when comparing models.


Next Steps
-----------

- :doc:`advanced_customization` — learn how to build a custom forecaster that
  implements ``BacktestForecasterMixin`` so you can plug any model into the
  backtesting pipeline.
- :doc:`first_forecast` — if you need a refresher on constructing a forecaster
  before running a backtest.
- :doc:`quickstart` — the minimal end-to-end example if you want a working script
  to adapt.