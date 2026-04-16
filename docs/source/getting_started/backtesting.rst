Backtesting
===========

Backtesting lets you evaluate how well a forecasting model would have performed on
historical data — without ever touching future observations. Rather than training once
and hoping for the best, you replay the model's decision-making process through time:
train on what was available at each moment, predict forward, and compare those
predictions against what actually happened. This page walks through the full workflow
using OpenSTEF's built-in backtesting machinery.

.. note::

   This tutorial assumes you already have a working forecaster. If you are just
   getting started, see :doc:`first_forecast` first. For custom model configurations,
   see :doc:`advanced_customization`.

How OpenSTEF Backtesting Works
------------------------------

OpenSTEF's backtesting engine simulates the real-time forecasting loop over a
historical window. At each step it:

1. Trains (or retrains) the model using only data available up to that point.
2. Generates predictions for the configured horizon.
3. Advances time by the prediction interval and repeats.

This design prevents data leakage — the model never sees future ground truth during
training — so the resulting metrics reflect realistic operational performance.

The two central classes are ``BacktestConfig``, which controls the timing of training
and prediction events, and ``BacktestRunner``, which drives the simulation and returns
a ``VersionedTimeSeriesDataset`` of all collected predictions.

.. note:: [DIAGRAM: Timeline showing alternating train and predict events advancing
   through a historical window, with ground-truth values shown alongside predictions
   for metric computation.]

Setting Up a Backtest
---------------------

Start by preparing your historical data as ``VersionedTimeSeriesDataset`` objects —
one for the target series (``ground_truth``) and one for the predictor features
(``predictors``). Both must share the same ``DatetimeIndex`` and a consistent
``sample_interval``.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Load your historical data into a DataFrame with a DatetimeIndex
   raw = pd.read_csv("historical_load.csv", index_col="timestamp", parse_dates=True)

   sample_interval = timedelta(minutes=15)

   ground_truth = VersionedTimeSeriesDataset.from_dataframe(
       raw[["load"]],
       sample_interval=sample_interval,
   )

   predictors = VersionedTimeSeriesDataset.from_dataframe(
       raw.drop(columns=["load"]),
       sample_interval=sample_interval,
   )

Next, configure the backtest timing. The three most important parameters are:

- ``prediction_sample_interval`` — must match your forecaster's own
  ``predict_sample_interval``.
- ``predict_interval`` — how often a new forecast is generated (e.g. every hour).
- ``train_interval`` — how often the model is retrained (e.g. every day).

.. code-block:: python

   from datetime import time
   from openstef_core.backtest import BacktestConfig

   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=1),
       train_interval=timedelta(days=1),
       align_time=time(6, 0),   # align daily retrains to 06:00
   )

.. note::

   ``prediction_sample_interval`` in ``BacktestConfig`` **must** equal the
   ``predict_sample_interval`` set on your forecaster. OpenSTEF raises a
   ``ValueError`` at construction time if these values differ, so mismatches are
   caught early.

Running the Simulation
----------------------

With configuration and data in hand, construct a ``BacktestRunner`` and call
``run()``. Pass explicit ``start`` and ``end`` datetimes to restrict the evaluation
window, or leave them as ``None`` to use the full extent of your data.

.. code-block:: python

   from datetime import datetime
   from openstef_core.backtest import BacktestRunner

   runner = BacktestRunner(config=backtest_config, forecaster=my_forecaster)

   predictions = runner.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 6, 30),
       show_progress=True,   # prints a progress bar
   )

``predictions`` is a ``VersionedTimeSeriesDataset`` containing every forecast the
model produced during the simulation, tagged with the timestamp at which each
prediction became available. This versioning is what makes it possible to reconstruct
exactly what the model knew — and predicted — at any point in time.

Computing Evaluation Metrics
-----------------------------

OpenSTEF ships a dedicated metrics module that covers both deterministic and
probabilistic forecast quality. Import from ``openstef_beam.metrics`` (or the
equivalent ``openstef_core`` path in your installation) and compute metrics directly
on the predictions dataset.

The two headline metrics for energy forecasting are:

- **rMAE** (relative Mean Absolute Error) — point forecast accuracy, normalised by
  the mean of the target series so results are comparable across substations or
  load levels.
- **rCRPS** (relative Continuous Ranked Probability Score) — probabilistic forecast
  accuracy; rewards both sharpness and calibration of the predicted distribution.

Lower values are better for both metrics.

.. code-block:: python

   import pandas as pd

   # Convert predictions to a horizon-indexed DataFrame for metric computation
   horizon_predictions = predictions.to_horizons(horizons=[1, 4, 8, 16])  # in steps

   # Align with ground truth on the shared index
   actuals = ground_truth.to_dataframe()["load"]
   forecast = horizon_predictions.to_dataframe()["load"]

   aligned = pd.concat([actuals.rename("actual"), forecast.rename("forecast")], axis=1).dropna()

   mae = (aligned["actual"] - aligned["forecast"]).abs().mean()
   rmae = mae / aligned["actual"].mean()

   print(f"rMAE: {rmae:.4f}")

For probabilistic models that output quantile forecasts, use the built-in
``GroupedTargetMetricVisualization`` to compute and plot rCRPS across multiple
targets or time windows without writing metric loops by hand (see the next section).

Visualising Performance
------------------------

OpenSTEF provides interactive HTML visualisations through the analysis module. These
are more informative than static plots for diagnosing where and when a model
struggles.

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from openstef_core.types import Quantile

   analysis_config = AnalysisConfig(
       visualization_providers=[
           # Point forecast accuracy at the median quantile
           GroupedTargetMetricVisualization(
               name="rmae_median",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           # Overall probabilistic performance
           GroupedTargetMetricVisualization(
               name="rcrps_overall",
               metric="rCRPS",
           ),
       ]
   )

The resulting HTML files are interactive: hover over bars to see exact values, and
use the grouping controls to slice results by category (e.g. substation voltage level
or geographic region).

Comparing Two Models
---------------------

The most common use of backtesting is head-to-head model comparison. Run the
simulation independently for each forecaster, then join the metric results on the
shared index.

.. code-block:: python

   from openstef_core.backtest import BacktestRunner

   # Run backtest for model A
   runner_a = BacktestRunner(config=backtest_config, forecaster=forecaster_a)
   preds_a = runner_a.run(ground_truth, predictors, start=start, end=end)

   # Run backtest for model B (same data, same window)
   runner_b = BacktestRunner(config=backtest_config, forecaster=forecaster_b)
   preds_b = runner_b.run(ground_truth, predictors, start=start, end=end)

   # Compute rMAE for each
   def rmae(predictions, actuals):
       fc = predictions.to_dataframe()["load"]
       aligned = pd.concat([actuals, fc], axis=1, keys=["actual", "forecast"]).dropna()
       return (aligned["actual"] - aligned["forecast"]).abs().mean() / aligned["actual"].mean()

   actuals = ground_truth.to_dataframe()["load"]
   print(f"Model A rMAE: {rmae(preds_a, actuals):.4f}")
   print(f"Model B rMAE: {rmae(preds_b, actuals):.4f}")

Keep the ``start`` and ``end`` arguments identical across runs. Comparing models over
different time windows introduces confounding factors (e.g. seasonal difficulty) that
make the comparison meaningless.

.. note::

   If your forecasters have different ``predict_sample_interval`` values you will need
   separate ``BacktestConfig`` instances. The runner validates this at construction
   time and will raise a ``ValueError`` if there is a mismatch.

Interpreting Results
---------------------

A few practical guidelines when reading backtest metrics:

- **rMAE < 0.05** is generally considered strong performance for 15-minute ahead
  load forecasting on a distribution substation. Acceptable thresholds vary with
  horizon and load volatility.
- **Windowed metrics** (e.g. rCRPS computed over rolling 7-day windows) reveal
  seasonal degradation that aggregate numbers hide. Use the ``rCRPS_windowed``
  visualisation to spot periods where the model underperforms.
- **Per-target breakdowns** are more actionable than fleet-wide averages. A single
  poorly-behaved substation can inflate aggregate error without indicating a
  systematic model problem.
- **Retrain frequency matters.** If ``train_interval`` is set too long, the model
  may drift as load patterns change. Experiment with shorter retraining cadences and
  compare the resulting metrics.

.. warning::

   Backtesting on the same data used to select model hyperparameters leads to
   optimistic estimates. Reserve a held-out time window — ideally the most recent
   months — for final evaluation, and use an earlier window for hyperparameter
   search.

Next Steps
----------

- To customise the underlying model or feature engineering pipeline before running a
  backtest, see :doc:`advanced_customization`.
- If you have not yet set up your environment, see :doc:`installation`.
- For a minimal end-to-end example without backtesting, see :doc:`quickstart`.