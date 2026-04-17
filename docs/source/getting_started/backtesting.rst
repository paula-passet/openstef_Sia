Backtesting
===========

Backtesting lets you measure how well a forecasting model would have performed if it had been deployed in the past. Rather than evaluating on a held-out test set in one shot, OpenSTEF's ``BacktestPipeline`` replays history in operational conditions: the model only ever sees data that would have been available at each point in time, it retrains on a schedule, and it generates predictions at the same cadence it would in production. The result is an honest estimate of real-world accuracy.

This page walks through configuring and running a backtest, evaluating the resulting predictions, and visualising performance over time. If you haven't yet produced your first forecast, start with :doc:`first_forecast` before continuing here.

.. note::

   [DIAGRAM: Timeline showing the sliding-window backtesting process. The horizontal axis is calendar time (e.g. Jan → Dec). Three labelled bands stack vertically: (1) "Available data horizon" — a window that advances right at each step, representing the data the model is allowed to see; (2) "Train events" — periodic markers (e.g. every 7 days) where the model is retrained on the data behind the horizon; (3) "Predict events" — more frequent markers (e.g. every 6 hours) where the model generates a forecast for the horizon ahead. Arrows show the window sliding forward in time, with each predict event producing one forecast chunk that is collected into the final predictions dataset.]


How the pipeline works
----------------------

``BacktestPipeline`` drives two interleaved schedules:

- **Predict schedule** — every ``predict_interval`` (default 6 hours) the model generates a forecast for the upcoming horizon. Only data strictly before the current simulation time is visible.
- **Train schedule** — every ``train_interval`` (default 7 days) the model is retrained from scratch on the accumulated history up to that moment.

This mirrors exactly what a deployed forecaster does, so the evaluation captures realistic degradation between retrains, cold-start effects, and any data-availability constraints.

The pipeline is deliberately a library component: you bring your own forecaster, your own data, and your own evaluation logic. ``BacktestPipeline`` orchestrates the temporal bookkeeping.


Configuring the backtest
------------------------

All timing parameters live in ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

   config = BacktestConfig(
       # Resolution of the output forecast (must match the forecaster's own interval)
       prediction_sample_interval=timedelta(minutes=15),

       # How often to generate a new forecast during the simulation
       predict_interval=timedelta(hours=6),

       # How often to retrain the model
       train_interval=timedelta(days=7),

       # Wall-clock anchor for aligning prediction windows (UTC midnight by default)
       align_time=time.fromisoformat("00:00+00"),
   )

.. note::

   ``prediction_sample_interval`` must equal the ``predict_sample_interval`` set on your forecaster's own config. ``BacktestPipeline`` raises a ``ValueError`` at construction time if they disagree, so mismatches are caught early.

The three interval parameters give you direct control over the cost/fidelity trade-off:

- Shorter ``predict_interval`` → denser prediction coverage, longer runtime.
- Shorter ``train_interval`` → fresher models, more training overhead.
- Longer ``train_interval`` → reveals how quickly model accuracy decays without retraining.


Running the backtest
--------------------

``BacktestPipeline.run()`` accepts versioned time-series datasets for the target variable and the predictor features, plus an optional date range to restrict the simulation window.

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig, BacktestPipeline

   # --- Build config and forecaster (see first_forecast for forecaster setup) ---
   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
   )

   # forecaster must implement BacktestForecasterMixin
   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   # --- Supply historical data ---
   # ground_truth: VersionedTimeSeriesDataset of measured load/generation values
   # predictors:   VersionedTimeSeriesDataset of weather forecasts or other features
   predictions = pipeline.run(
       ground_truth=ground_truth_dataset,
       predictors=predictor_dataset,
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       show_progress=True,   # tqdm progress bar
   )

``run()`` returns a ``TimeSeriesDataset`` containing every forecast chunk produced during the simulation, stamped with the time at which each prediction was made (``available_at``). Passing ``start=None`` or ``end=None`` uses the extent of the supplied data automatically.


Evaluating predictions
----------------------

Once you have the predictions dataset, pass it to ``EvaluationPipeline`` alongside the ground truth to compute metrics broken down by lead time and evaluation window.

.. code-block:: python

   from openstef_beam.backtesting.evaluation_pipeline import EvaluationPipeline
   from openstef_beam.backtesting.evaluation_pipeline import EvaluationConfig
   from openstef_beam.evaluation.metrics import MAEProvider, RMAEProvider
   from openstef_core.types import Quantile

   evaluation_config = EvaluationConfig()

   # Quantiles must include 0.5 (median) — add others for probabilistic evaluation
   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

   metric_providers = [MAEProvider(), RMAEProvider()]

   eval_pipeline = EvaluationPipeline(
       config=evaluation_config,
       quantiles=quantiles,
       window_metric_providers=metric_providers,
       global_metric_providers=metric_providers,
   )

   report = eval_pipeline.run(
       predictions=predictions,
       ground_truth=ground_truth_dataset,
       target_column="load_mw",
   )

The returned ``EvaluationReport`` segments results by ``available_at`` and lead time, giving you a fine-grained picture of where the model performs well and where it struggles.

.. note::

   ``EvaluationPipeline`` requires ``Quantile(0.5)`` to be present in the quantiles list. A ``ValueError`` is raised at construction time if it is missing.


Visualising performance
-----------------------

Raw metric tables are useful, but time-series plots of metric evolution reveal patterns that aggregate numbers hide — seasonal degradation, the effect of retraining gaps, or a sudden data-quality problem. OpenSTEF provides ``WindowedMetricVisualization`` and ``GroupedTargetMetricVisualization`` for exactly this purpose.

**Metric evolution over time**

``WindowedMetricVisualization`` plots a chosen metric computed over a rolling window, so you can see how accuracy changes across the backtesting period:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window
   from openstef_core.types import Quantile

   analysis_config = AnalysisConfig(
       visualization_providers=[
           # 7-day rolling rMAE at the median quantile
           WindowedMetricVisualization(
               name="rmae_7d",
               metric=("rMAE", Quantile(0.5)),
               window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           ),
           # 30-day rolling rMAE — smoother trend line
           WindowedMetricVisualization(
               name="rmae_30d",
               metric=("rMAE", Quantile(0.5)),
               window=Window(lag=timedelta(hours=0), size=timedelta(days=30)),
           ),
           # Probabilistic skill via rCRPS
           WindowedMetricVisualization(
               name="rcrps_7d",
               metric="rCRPS",
               window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           ),
       ]
   )

[VISUALIZATION: Line chart showing rMAE (y-axis, lower is better) plotted against calendar date (x-axis) for the backtesting period. Three lines represent 7-day, 21-day, and 30-day rolling windows. Peaks in the 7-day line indicate short periods of degraded accuracy; the 30-day line shows the underlying seasonal trend.]

**Comparing targets or model runs**

When you backtest multiple targets or want to compare two model configurations side by side, ``GroupedTargetMetricVisualization`` produces bar charts and box plots grouped by target category:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from openstef_core.types import Quantile

   comparison_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="rmae_by_target",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           GroupedTargetMetricVisualization(
               name="rcrps_by_target",
               metric="rCRPS",
           ),
       ]
   )

[VISUALIZATION: Grouped bar chart with target names on the x-axis and rMAE on the y-axis. Bars are colour-coded by target group (e.g. residential, industrial, commercial). A second panel shows rCRPS for the same targets, illustrating which target categories are hardest to forecast probabilistically.]


Understanding the metrics
--------------------------

The table below summarises the metrics available out of the box:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - Metric
     - Type
     - Description
   * - ``MAE``
     - Deterministic
     - Mean Absolute Error — average magnitude of forecast errors in the original unit.
   * - ``rMAE``
     - Deterministic
     - Relative MAE — MAE normalised by a reference (e.g. mean observed value), enabling comparison across targets of different scales.
   * - ``RMSE``
     - Deterministic
     - Root Mean Squared Error — penalises large errors more heavily than MAE.
   * - ``rCRPS``
     - Probabilistic
     - Relative Continuous Ranked Probability Score — measures the full predictive distribution against observations; lower is better.

For probabilistic evaluation you must supply multiple quantiles (e.g. ``0.1``, ``0.5``, ``0.9``). The ``rCRPS`` metric integrates across all supplied quantiles, so a wider quantile set gives a more complete picture of calibration.


Practical tips
--------------

**Choose your backtest window carefully.** A window that is too short may not capture seasonal variation; one that is too long increases runtime significantly. Three to twelve months is a common starting point for energy forecasting.

**Match ``train_interval`` to your operational retraining cadence.** If you retrain weekly in production, use ``train_interval=timedelta(days=7)`` in the backtest. Mismatching this parameter will give you an overly optimistic or pessimistic estimate.

**Use multiple rolling window sizes.** Short windows (7 days) expose transient accuracy drops; long windows (30 days) reveal structural trends. The ``LIANDER2024`` reference configuration in the OpenSTEF examples uses 7-, 21-, and 30-day windows for exactly this reason.

**Restrict the evaluation period with ``evaluation_mask``.** If your dataset contains known data-quality issues in a specific period, pass a ``pd.DatetimeIndex`` to ``EvaluationPipeline.run()`` via ``evaluation_mask`` to exclude those timestamps from metric computation without discarding the predictions.


Next steps
----------

- :doc:`first_forecast` — if you need to set up a forecaster before running a backtest.
- :doc:`advanced_customization` — extend the pipeline with custom metric providers, callbacks, and forecaster implementations.
- :doc:`quickstart` — minimal working example if you want a fast end-to-end reference.