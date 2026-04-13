Backtesting
===========

Backtesting lets you evaluate how well a forecasting model would have performed
on historical data — before committing it to production. Rather than training
once and predicting forward, you simulate the operational reality: the model
is retrained periodically, predictions are generated at fixed intervals, and
results are compared against what actually happened. This page walks through
the full backtesting workflow in OpenSTEF, from configuring the pipeline to
comparing multiple models side by side.

If you haven't yet produced your first forecast, start with :doc:`first_forecast`
before continuing here.

.. mermaid:: diagrams/getting_started/backtesting_diagram_1.mmd

Why Backtesting Matters
-----------------------

A model that scores well on a held-out test set is not the same as a model
that performs well in operation. In production, models are retrained on a
rolling basis, predictions are made at specific times of day, and only data
available at that moment can be used. OpenSTEF's ``BacktestPipeline`` enforces
these constraints explicitly, preventing data leakage and faithfully
reproducing the operational environment. The result is an honest estimate of
real-world forecast quality.

The Core Concepts
-----------------

Three objects drive every backtest in OpenSTEF:

- **BacktestConfig** — defines *when* predictions are generated
  (``prediction_sample_interval``) and how often the model is retrained
  (``train_interval``).
- **BacktestPipeline** — orchestrates the simulation, stepping through time
  chronologically and calling your forecaster for training and prediction.
- **VersionedTimeSeriesDataset** — the return type of ``BacktestPipeline.run()``,
  containing every prediction together with the timestamp at which it was made
  (``available_at``). This versioning is what makes downstream evaluation
  meaningful.

.. note::

   ``BacktestConfig.prediction_sample_interval`` must match the forecaster's
   own ``predict_sample_interval``. OpenSTEF raises a ``ValueError`` at
   construction time if they differ, so mismatches are caught early.

Running a Backtest
------------------

The example below runs a backtest over a two-month window. Swap in any
forecaster that implements ``BacktestForecasterMixin`` — the pipeline API
stays the same regardless of the underlying model.

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef.backtest import BacktestConfig, BacktestPipeline

   # --- Configure the simulation ---
   config = BacktestConfig(
       prediction_sample_interval=timedelta(hours=1),   # generate a forecast every hour
       train_interval=timedelta(days=7),                # retrain weekly
   )

   # --- Attach your forecaster ---
   # Any forecaster implementing BacktestForecasterMixin works here.
   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   # --- Run over a historical window ---
   predictions = pipeline.run(
       ground_truth=ground_truth_dataset,   # VersionedTimeSeriesDataset
       predictors=predictor_dataset,        # VersionedTimeSeriesDataset
       start=datetime(2024, 1, 1),
       end=datetime(2024, 2, 28),
       show_progress=True,                  # progress bar in notebooks / terminals
   )

``predictions`` is a ``VersionedTimeSeriesDataset``. Each row carries both the
predicted value and the ``available_at`` timestamp — the moment at which that
forecast was produced. This makes it straightforward to slice results by lead
time or by the time of day the forecast was issued.

Evaluating Forecast Quality
---------------------------

OpenSTEF provides ``EvaluationPipeline`` and ``EvaluationConfig`` for computing
metrics across multiple dimensions simultaneously: lead time, availability
time, and rolling windows.

.. code-block:: python

   from openstef.evaluation import EvaluationConfig, EvaluationPipeline
   from openstef.evaluation.metrics import MAEProvider, RMSEProvider, MAPEProvider
   from datetime import timedelta

   # Define the evaluation dimensions
   eval_config = EvaluationConfig(
       available_ats=["D-1T06:00"],          # forecasts issued at 06:00 the day before
       lead_times=["PT12H", "PT24H", "PT36H"],  # evaluate at 12 h, 24 h, and 36 h ahead
   )

   # Choose which metrics to compute
   metrics = [MAEProvider(), RMSEProvider(), MAPEProvider()]

   pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[0.1, 0.5, 0.9],           # 0.5 (median) is required
       window_metric_providers=metrics,
       global_metric_providers=metrics,
   )

   report = pipeline.run(
       predictions=predictions,
       ground_truth=ground_truth_dataset,
       target_column="load_mw",
   )

The returned ``EvaluationReport`` contains both global metrics (aggregated over
the entire evaluation period) and windowed metrics (computed over rolling
21-day windows by default). You can inspect either:

.. code-block:: python

   # Global summary
   global_metrics = report.get_global_metric()
   print(global_metrics.metrics)

   # Per-window breakdown
   for window_metric in report.get_window_metrics():
       print(window_metric.window, window_metric.metrics)

.. note::

   ``EvaluationPipeline`` always appends an ``ObservedProbabilityProvider``
   to global metrics automatically. This calibration metric checks whether
   your probabilistic intervals contain the true value at the stated frequency
   — a critical check for probabilistic forecasts.

Visualising Results
-------------------

OpenSTEF ships ``ForecastTimeSeriesPlotter`` for interactive comparison of
forecasts against measurements. It produces Plotly figures with shaded
uncertainty bands, colour-coded model traces, and capacity limit lines — no
external plotting library required.

.. code-block:: python

   import pandas as pd
   from openstef_core.visualization import ForecastTimeSeriesPlotter

   # Extract median forecast series from the backtest results
   median_forecast = predictions.to_series(quantile=0.5)
   actuals = ground_truth_dataset.to_series()

   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(actuals)
   plotter.add_model("XGBoost", forecast=median_forecast)

   fig = plotter.plot(title="Backtest: XGBoost vs Actuals (Jan–Feb 2024)")
   fig.show()

The resulting figure lets you:

- Scroll and zoom across the full evaluation period
- Hover over any point to see exact values and timestamps
- Inspect where uncertainty bands fail to contain the actual measurement

Comparing Multiple Models
-------------------------

The real power of backtesting is head-to-head model comparison. Run the same
``BacktestPipeline.run()`` call for each candidate forecaster, then overlay
them in a single plot:

.. code-block:: python

   from openstef.backtest import BacktestConfig, BacktestPipeline
   from openstef_core.visualization import ForecastTimeSeriesPlotter

   config = BacktestConfig(
       prediction_sample_interval=timedelta(hours=1),
       train_interval=timedelta(days=7),
   )

   results = {}
   for name, forecaster in {
       "XGBoost": xgboost_forecaster,
       "LightGBM": lgbm_forecaster,
       "LinearRegression": lr_forecaster,
   }.items():
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       results[name] = pipeline.run(
           ground_truth=ground_truth_dataset,
           predictors=predictor_dataset,
           start=datetime(2024, 1, 1),
           end=datetime(2024, 2, 28),
       )

   # Overlay all models on a single interactive chart
   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(actuals)
   for name, preds in results.items():
       plotter.add_model(name, forecast=preds.to_series(quantile=0.5))

   fig = plotter.plot(title="Model Comparison: Jan–Feb 2024")
   fig.show()

For a quantitative summary, run ``EvaluationPipeline`` on each result set and
collect the global metrics into a DataFrame:

.. code-block:: python

   import pandas as pd

   summary_rows = []
   for name, preds in results.items():
       report = pipeline_eval.run(
           predictions=preds,
           ground_truth=ground_truth_dataset,
           target_column="load_mw",
       )
       row = report.get_global_metric().metrics
       row["model"] = name
       summary_rows.append(row)

   summary = pd.DataFrame(summary_rows).set_index("model")
   print(summary)

This gives you a clean table of MAE, RMSE, MAPE, and calibration scores per
model, ready for reporting or further analysis.

Avoiding Common Pitfalls
------------------------

**Data leakage.** ``BacktestPipeline`` prevents leakage by construction —
each training call only receives data with a timestamp earlier than the
current simulation time. If you pre-process features outside the pipeline,
make sure any transformations (e.g. scaling, lag computation) are fitted only
on the training slice, not the full dataset.

**Mismatched sample intervals.** The ``prediction_sample_interval`` in
``BacktestConfig`` must equal the forecaster's ``predict_sample_interval``.
Set both consistently when configuring your objects.

**Sparse evaluation periods.** If your ``start``/``end`` window is shorter
than one ``train_interval``, the model may never retrain during the backtest.
Use at least two to three training cycles for meaningful results.

**Probabilistic vs deterministic metrics.** RMSE and MAE measure the median
forecast. If you are using a probabilistic model, also check the calibration
metric (``ObservedProbabilityProvider``) to verify that your intervals are
reliable.

Next Steps
----------

- :doc:`advanced_customization` — learn how to plug in custom forecasters,
  feature engineering pipelines, and metric providers.
- :doc:`first_forecast` — if you need a refresher on the basic forecasting
  workflow before extending it with backtesting.
- :doc:`quickstart` — the minimal working example if you want a fast
  reference to the core API.