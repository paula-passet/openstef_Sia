Backtesting with BEAM
=====================

When you train a model and evaluate it on a held-out test set, you get one number for one split. That tells you little about how the model would have behaved in production over months of real operation. BEAM's ``BacktestPipeline`` addresses this by *replaying* history: it moves a data horizon forward in time, retraining and predicting on a schedule that mirrors your operational deployment. The result is a realistic picture of model performance across many conditions — seasonal variation, data quality events, and changing load patterns.

This page walks through configuring and running a backtest, understanding the output, and computing evaluation metrics. If you haven't installed OpenSTEF yet, see :doc:`installation` first. For a minimal working forecast without backtesting, see :doc:`quickstart`.

.. note:: [DIAGRAM: Timeline showing backtesting sliding window. The horizontal axis is calendar time (e.g. Jan → Dec). A moving "horizon" marker advances left to right. Behind the horizon is the training window (shaded blue), which grows or resets on a weekly retrain schedule. Ahead of the horizon is the prediction window (shaded orange, e.g. 24–48 h). Vertical tick marks show retrain events (every 7 days) and predict events (every 6 hours). Arrows illustrate that at each predict event only data available before the horizon is visible — no lookahead.]

How the backtest simulation works
----------------------------------

``BacktestPipeline`` drives two interleaved schedules:

- **Predict schedule** — every ``predict_interval`` (default 6 hours) the forecaster's ``predict()`` method is called. The forecaster receives a ``RestrictedHorizonVersionedTimeSeries`` that only exposes data available at the current horizon, preventing any accidental lookahead.
- **Retrain schedule** — every ``train_interval`` (default 7 days) the forecaster's ``fit()`` method is called with the same restricted view of history.

All predictions are collected and returned as a single ``TimeSeriesDataset`` indexed by both the forecast timestamp and the ``available_at`` time at which each prediction was generated. This ``available_at`` column is what enables lead-time analysis later.

Configuring the backtest
-------------------------

``BacktestConfig`` holds the timing parameters. The only hard constraint is that ``prediction_sample_interval`` must match the forecaster's own ``predict_sample_interval`` — BEAM raises a ``ValueError`` at construction time if they differ.

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

    config = BacktestConfig(
        # Resolution of the output forecast (must match your forecaster)
        prediction_sample_interval=timedelta(minutes=15),
        # How often a new forecast is generated during the replay
        predict_interval=timedelta(hours=6),
        # How often the model is retrained on accumulated history
        train_interval=timedelta(days=7),
        # Reference time for aligning schedules (UTC midnight by default)
        align_time=time.fromisoformat("00:00+00"),
    )

Increasing ``predict_interval`` speeds up the backtest at the cost of fewer forecast origins. Decreasing ``train_interval`` gives the model more chances to adapt but increases compute time. For a quick sanity check, set ``predict_interval=timedelta(days=1)`` and ``train_interval=timedelta(days=30)`` to get a fast run before committing to a full evaluation.

Implementing a forecaster
--------------------------

``BacktestPipeline`` works with any class that implements ``BacktestForecasterMixin``. The interface requires two methods and a ``config`` attribute:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_beam.backtesting.backtest_forecaster.mixins import BacktestForecasterMixin
    from openstef_core.base_model import BaseConfig
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_beam.backtesting.restricted_horizon_timeseries import (
        RestrictedHorizonVersionedTimeSeries,
    )

    class MedianForecasterConfig(BaseConfig):
        predict_sample_interval: timedelta = timedelta(minutes=15)
        history_days: int = 14

    class MedianForecaster(BacktestForecasterMixin):
        """Predicts the rolling median of recent history as a simple baseline."""

        config = MedianForecasterConfig()

        def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
            window_start = data.horizon - timedelta(days=self.config.history_days)
            history = data.get_window(window_start, data.horizon, data.horizon)
            self._median = history["load"].median()

        def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset:
            horizon = data.horizon
            future_index = pd.date_range(
                start=horizon,
                periods=96,  # 24 h at 15-min resolution
                freq=self.config.predict_sample_interval,
            )
            predictions = pd.DataFrame(
                {"load": self._median, "quantile_P50": self._median},
                index=future_index,
            )
            return TimeSeriesDataset(predictions)

The ``data.get_window(start, end, available_before)`` call is the key data-access primitive. The ``available_before`` argument is enforced by ``RestrictedHorizonVersionedTimeSeries`` — requesting data beyond the current horizon raises an error rather than silently leaking future information.

.. note::

    The built-in Liander 2024 dataset is a convenient starting point for testing your forecaster without preparing your own data. See the ``run_liander2024_benchmark.py`` example in the repository for a ready-to-run script.

Running the backtest
---------------------

With a config and a forecaster in hand, construct the pipeline and call ``run()``:

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_beam.backtesting.backtest_pipeline import BacktestPipeline

    forecaster = MedianForecaster()

    pipeline = BacktestPipeline(
        config=config,
        forecaster=forecaster,
    )

    predictions = pipeline.run(
        ground_truth=versioned_ground_truth,   # VersionedTimeSeriesDataset
        predictors=versioned_predictors,        # VersionedTimeSeriesDataset
        start=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end=datetime(2023, 12, 31, tzinfo=timezone.utc),
        show_progress=True,
    )

``run()`` returns a ``TimeSeriesDataset``. Each row is one 15-minute slot in the forecast, and the ``available_at`` column records when that forecast was generated. Passing ``start=None`` or ``end=None`` uses the extent of the provided data automatically.

.. note::

    Thread contention can slow down backtests that use XGBoost internally. Set ``OMP_NUM_THREADS=1``, ``OPENBLAS_NUM_THREADS=1``, and ``MKL_NUM_THREADS=1`` before importing any numerical libraries when running parallel backtests.

Evaluating the output
----------------------

The ``EvaluationPipeline`` takes the predictions returned by ``BacktestPipeline`` and computes metrics against the ground truth. Metrics are computed both globally (over the entire period) and per rolling window, and can be broken down by lead time.

.. code-block:: python

    from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline, EvaluationConfig
    from openstef_core.types import Quantile

    eval_config = EvaluationConfig()

    quantiles = [Quantile(0.05), Quantile(0.50), Quantile(0.95)]

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=quantiles,
        window_metric_providers=metrics,
        global_metric_providers=metrics,
    )

    report = eval_pipeline.run(
        ground_truth=versioned_ground_truth,
        predictions=predictions,
    )

The ``report`` object contains metric scores that can be inspected directly or passed to the analysis stage for visualisation. Standard metrics include MAE, RMSE, and pinball loss for each quantile.

.. note:: [VISUALIZATION: Bar chart comparing MAE and RMSE across multiple lead-time buckets (e.g. 0–6 h, 6–12 h, 12–24 h, 24–48 h), showing how forecast accuracy degrades with increasing lead time. A second panel shows pinball loss per quantile (P05, P50, P95).]

Using the full benchmark runner
--------------------------------

For evaluating multiple models across many energy assets, the ``BenchmarkRunner`` wraps ``BacktestPipeline`` and ``EvaluationPipeline`` into a single orchestrated workflow. It handles parallelism, result storage, and comparison plots automatically:

.. code-block:: python

    from openstef_beam.benchmarking.benchmarks.liander2024 import (
        create_liander2024_benchmark_runner,
        Liander2024Category,
    )
    from openstef_core.types import LeadTime, Quantile

    runner = create_liander2024_benchmark_runner(
        output_path="./benchmark_results",
    )

    runner.register_forecaster("median_baseline", lambda: MedianForecaster())

    runner.run(
        categories=[Liander2024Category.SOLAR],
        quantiles=[Quantile(0.05), Quantile(0.50), Quantile(0.95)],
        lead_times=[LeadTime("PT6H"), LeadTime("PT24H"), LeadTime("PT48H")],
    )

Results are written to ``./benchmark_results/<model_name>/`` with separate subdirectories for backtest predictions, evaluation scores, and analysis plots. To compare two runs side by side after the fact, use the ``compare_liander2024_results.py`` script from the examples directory.

Skipping the backtest step
---------------------------

If you already have predictions from an external system or a previous run, you can point the pipeline at existing parquet files and run only evaluation and analysis. Each ``predictions.parquet`` must contain a ``DatetimeIndex`` of 15-minute UTC timestamps, an ``available_at`` column, and one column per quantile (e.g. ``quantile_P50``). See the ``evaluate_existing_forecasts.py`` example for the exact directory layout expected.

Next steps
----------

- To plug in a production-grade OpenSTEF model rather than a hand-written forecaster, see :doc:`first_forecast` for how models are trained and serialised.
- For custom metrics, bespoke visualisations, and advanced pipeline composition, see :doc:`advanced_customization`.