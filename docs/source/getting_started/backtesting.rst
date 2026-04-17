Backtesting Models with Historical Data
=======================================

Backtesting is the process of evaluating a forecasting model by replaying historical data as if
predictions were being made in real time. Rather than simply fitting a model to a held-out test
set, a proper backtest simulates the operational environment: models are retrained on a schedule,
predictions are generated at regular intervals, and — critically — no future data is ever visible
to the model at the time it would have made a forecast.

OpenSTEF provides a complete backtesting toolkit through its ``openstef_beam.backtesting`` module.
This page walks through the full workflow: configuring and running a backtest, computing evaluation
metrics, visualising performance over time, and comparing multiple models side-by-side.

.. note::

   This tutorial assumes you have already produced a working forecast. If you are new to OpenSTEF,
   start with :doc:`quickstart` or :doc:`first_forecast` before continuing here.

Why Backtesting Matters
-----------------------

A naive train/test split can give an overly optimistic picture of model performance. In real
energy forecasting deployments, models are retrained periodically (weekly, for example) and
predictions are issued every few hours. A backtest that mirrors this schedule gives results that
accurately reflect what you would observe in production.

OpenSTEF's ``BacktestPipeline`` enforces two key constraints automatically:

- **No data leakage.** The ``RestrictedHorizonVersionedTimeSeries`` wrapper ensures that at any
  simulated forecast time, the model can only see data that would genuinely have been available.
- **Realistic retraining.** The pipeline fires retraining events on the same cadence you configure,
  so model staleness is accounted for in the evaluation.

.. note:: [DIAGRAM: Timeline showing alternating predict and retrain events across a historical
   period, with the restricted data horizon illustrated at each forecast point.]

Configuring the Backtest
------------------------

Everything about the backtest schedule is controlled by ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig

   backtest_config = BacktestConfig(
       # Granularity of the output forecast (must match the forecaster)
       prediction_sample_interval=timedelta(minutes=15),
       # How often new predictions are issued during the backtest
       predict_interval=timedelta(hours=6),
       # How often the model is retrained
       train_interval=timedelta(days=7),
       # Reference time for aligning the prediction schedule
       align_time=time.fromisoformat("00:00+00"),
   )

The four parameters above map directly to the operational decisions you would make when deploying
a forecaster:

- ``prediction_sample_interval`` — the temporal resolution of each forecast (15 minutes is typical
  for electricity grids).
- ``predict_interval`` — how frequently a fresh forecast is issued; six hours means four forecasts
  per day.
- ``train_interval`` — how often the underlying model is retrained on the latest available data.
- ``align_time`` — the UTC anchor used to align prediction events to clock-regular intervals.

.. warning::

   ``prediction_sample_interval`` must match the ``predict_sample_interval`` configured on your
   forecaster. ``BacktestPipeline`` raises a ``ValueError`` at construction time if they differ.

Running the Backtest
--------------------

``BacktestPipeline`` takes a ``BacktestConfig`` and any forecaster that implements
``BacktestForecasterMixin``. For OpenSTEF4-based models, the library ships a ready-made adapter:

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline
   from openstef_beam.backtesting.backtest_forecaster import (
       create_openstef4_preset_backtest_forecaster,
   )

   # Assume `workflow_config` is a ForecastingWorkflowConfig you have already built
   forecaster_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=workflow_config,
   )
   forecaster = forecaster_factory(target)

   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )

   # ground_truth and predictors are VersionedTimeSeriesDataset objects
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       show_progress=True,
   )

``pipeline.run()`` returns a ``TimeSeriesDataset`` containing all predictions generated across the
backtest window. Each row carries both the forecast timestamp and an ``available_at`` column that
records when the prediction was issued — preserving the temporal versioning needed for fair
evaluation.

Evaluation Metrics
------------------

Once you have backtest predictions, pass them to the evaluation layer to compute metrics.
OpenSTEF provides a rich set of metric providers out of the box:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Metric
     - Description
   * - ``MAEProvider``
     - Mean Absolute Error — absolute average deviation in the original unit.
   * - ``RMAEProvider``
     - Relative MAE — MAE normalised by a reference scale, enabling fair cross-target comparison.
   * - ``MAPEProvider``
     - Mean Absolute Percentage Error.
   * - ``R2Provider``
     - Coefficient of determination (R²).
   * - ``RCRPSProvider``
     - Relative Continuous Ranked Probability Score — the primary probabilistic accuracy metric.
   * - ``RCRPSSampleWeightedProvider``
     - rCRPS with sample weights that emphasise large deviations.

For most energy forecasting use cases, **rCRPS** is the recommended headline metric because it
evaluates the full predictive distribution rather than a single point estimate.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline, Window
   from openstef_beam.evaluation.metrics import RMAEProvider, RCRPSProvider
   from openstef_core.types import Quantile
   from datetime import timedelta

   evaluation_config = EvaluationConfig(
       metric_providers=[
           RMAEProvider(quantiles=[Quantile(0.5)], lower_quantile=0.01, upper_quantile=0.99),
           RCRPSProvider(lower_quantile=0.01, upper_quantile=0.99),
       ]
   )

   eval_pipeline = EvaluationPipeline(
       config=evaluation_config,
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       window_metric_providers=[
           RMAEProvider(quantiles=[Quantile(0.5)], lower_quantile=0.01, upper_quantile=0.99),
           RCRPSProvider(lower_quantile=0.01, upper_quantile=0.99),
       ],
       global_metric_providers=[
           RCRPSProvider(lower_quantile=0.01, upper_quantile=0.99),
       ],
   )

   report = eval_pipeline.run(
       ground_truth=ground_truth,
       predictions=predictions,
       target_column="load",
   )

The resulting ``EvaluationReport`` contains both global summary statistics and windowed metrics
computed over rolling time windows — useful for spotting seasonal performance changes.

Visualising Performance
-----------------------

Raw metric tables are informative, but charts make it much easier to spot trends and regressions.
OpenSTEF's analysis module provides two purpose-built visualisation providers.

**Windowed metric plots** show how accuracy evolves over time. Each point on the chart represents
the metric computed over a sliding window, making it straightforward to identify periods of
degraded performance or to determine the optimal retraining cadence:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window
   from datetime import timedelta

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="rcrps_7d",
               metric="rCRPS",
               window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           ),
           WindowedMetricVisualization(
               name="rcrps_30d",
               metric="rCRPS",
               window=Window(lag=timedelta(hours=0), size=timedelta(days=30)),
           ),
       ]
   )

**Grouped target metric charts** produce bar charts and box plots that compare accuracy across
multiple targets or model runs. These are particularly useful when you are forecasting a portfolio
of assets and want to identify which targets are hardest to predict:

.. code-block:: python

   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from openstef_core.types import Quantile

   analysis_config = AnalysisConfig(
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

.. note:: [DIAGRAM: Side-by-side bar chart comparing rCRPS across three model variants for a set
   of forecast targets, with targets on the X-axis and metric value on the Y-axis.]

Comparing Multiple Models
-------------------------

The real power of backtesting emerges when you run the same historical period through several
model variants and compare them objectively. ``BenchmarkComparisonPipeline`` is designed exactly
for this: it operates on pre-computed benchmark results, so you can run each model once and then
explore comparisons without re-executing expensive computations.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       GroupedTargetMetricVisualization,
       WindowedMetricVisualization,
   )
   from openstef_beam.benchmarking.storage import LocalBenchmarkStorage
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   from openstef_core.types import Quantile
   from openstef_beam.evaluation import Window
   from datetime import timedelta
   from pathlib import Path

   # Point each run name at its stored results
   run_data = {
       "baseline":  LocalBenchmarkStorage(Path("results/baseline")),
       "xgboost_v2": LocalBenchmarkStorage(Path("results/xgboost_v2")),
       "ensemble":  LocalBenchmarkStorage(Path("results/ensemble")),
   }

   comparison_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="model_comparison_rcrps",
               metric="rCRPS",
           ),
           GroupedTargetMetricVisualization(
               name="model_comparison_rmae",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           SummaryTableVisualization(name="performance_summary"),
           WindowedMetricVisualization(
               name="rcrps_over_time",
               metric="rCRPS",
               window=Window(lag=timedelta(hours=0), size=timedelta(days=21)),
           ),
       ]
   )

   comparison_pipeline = BenchmarkComparisonPipeline()
   comparison_pipeline.run(run_data=run_data, analysis_config=comparison_config)

The pipeline automatically generates analysis at three aggregation levels:

- **Global** — overall performance across all runs and targets.
- **Group** — performance within target groups (e.g., by region or asset type).
- **Target** — individual target performance across all model runs.

This hierarchical view helps you distinguish between a model that is uniformly better and one that
only improves on a specific subset of targets.

End-to-End Benchmark Pipeline
------------------------------

For production workflows, the ``BenchmarkPipeline`` class ties backtesting, evaluation, and
analysis together into a single orchestrated run. It accepts a ``ForecasterFactory`` — a callable
that returns a configured forecaster for each target — and handles parallelism automatically:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.backtesting import BacktestConfig
   from datetime import timedelta, time

   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
       align_time=time.fromisoformat("00:00+00"),
   )

   def create_forecaster(target):
       return create_openstef4_preset_backtest_forecaster(
           workflow_config=target.get_model_config(),
       )(target)

   benchmark = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       target_provider=my_target_provider,
   )

   benchmark.run(
       forecaster_factory=create_forecaster,
       run_name="xgboost_v2_evaluation",
       n_processes=4,
   )

.. note::

   ``n_processes`` enables parallel execution across targets. Set it to ``None`` to use all
   available CPU cores, or to ``1`` to run sequentially (useful for debugging).

Next Steps
----------

With backtesting results in hand, you can move on to customising model behaviour or tuning
hyperparameters to improve the metrics you have just measured:

- :doc:`advanced_customization` — learn how to plug in custom models, feature engineering
  pipelines, and metric providers.
- :doc:`first_forecast` — revisit the fundamentals if you want to understand how the underlying
  forecasting workflow is constructed before customising it.