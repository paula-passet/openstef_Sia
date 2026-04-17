The OpenSTEF BEAM Package
=========================

The ``openstef_beam`` package implements the **Backtesting, Evaluation, Analysis, and
Metrics** (BEAM) framework — a complete evaluation layer that sits on top of the core
and models packages. Where ``openstef_core`` provides data structures and
``openstef_models`` provides forecasting transforms, BEAM answers the harder question:
*how well does a model actually perform under realistic operational conditions?*

This page covers the BEAM workflow in depth: how backtesting simulates production
environments, how evaluation slices results by lead time and availability window, how
analysis turns scores into actionable reports, and how the benchmarking layer
orchestrates all of this across many targets and model variants.

For the data structures that BEAM consumes, see :doc:`core`. For the model transforms
that plug into BEAM forecasters, see :doc:`models`.

.. note:: [DIAGRAM: Component-level diagram showing the BEAM workflow. Left column: openstef_core (VersionedTimeSeriesDataset, TimeSeriesDataset) and openstef_models (transforms, forecasting workflows) feeding into BEAM. Central pipeline flows top-to-bottom: BacktestPipeline → EvaluationConfig (lead times, availability windows) → AnalysisConfig (metrics, visualizations) → BenchmarkPipeline. Right column: outputs — predictions.parquet, evaluation scores, HTML analysis reports, comparison plots. Arrows show BenchmarkPipeline orchestrating all stages and ForecasterFactory injecting model implementations.]


Why BEAM Exists
---------------

Standard train/test splits are misleading for operational energy forecasting. A model
evaluated on a held-out test set has implicitly seen the future: feature engineering
choices, hyperparameter tuning, and even the choice of training window are all
influenced by data that would not have been available in production.

BEAM addresses this by replaying history day by day using
``VersionedTimeSeriesDataset`` — a data structure that enforces strict temporal
boundaries. At each simulated forecast time, the model can only access measurements
that were *available at* that moment. Retraining happens on a configurable schedule,
just as it would in a live system. The result is an evaluation that accurately reflects
what you would have observed had the model been running in production.


The Backtesting Layer
---------------------

The entry point for a single-target backtest is ``BacktestPipeline``. It requires two
things: a ``BacktestConfig`` describing the operational schedule, and a forecaster that
implements ``BacktestForecasterMixin``.

``BacktestConfig`` controls the simulation cadence:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),  # output resolution
   )

The forecaster interface is intentionally minimal. Any class that implements
``BacktestForecasterMixin`` can participate in a backtest — whether it wraps an
OpenSTEF model, a statistical baseline, or an external library:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterMixin,
       BacktestForecasterConfig,
   )
   from openstef_core.datasets import TimeSeriesDataset


   class MedianBaselineForecaster(BacktestForecasterMixin):
       """Predicts the rolling median of recent load history."""

       config = BacktestForecasterConfig(
           requires_training=True,
           predict_length=timedelta(days=2),
           predict_min_length=timedelta(minutes=15),
           predict_context_length=timedelta(days=14),
           predict_context_min_coverage=0.5,
           training_context_length=timedelta(days=90),
           training_context_min_coverage=0.5,
           predict_sample_interval=timedelta(minutes=15),
       )

       def fit(self, data) -> None:
           # data is a RestrictedHorizonVersionedTimeSeries — no lookahead possible
           window = data.get_window(
               data.horizon - timedelta(days=90),
               data.horizon,
               available_before=data.horizon,
           )
           self._median = window["load"].median()

       def predict(self, data) -> TimeSeriesDataset:
           index = data.prediction_index
           result = TimeSeriesDataset({"load": self._median, "quantile_P50": self._median}, index=index)
           return result

       @property
       def quantiles(self):
           return []

The ``data`` argument passed to both ``fit`` and ``predict`` is a
``RestrictedHorizonVersionedTimeSeries``. Calling ``get_window`` on it enforces the
``available_before`` constraint — any attempt to read data beyond the current horizon
raises an error, making data leakage structurally impossible.

Once a forecaster is ready, running a backtest produces a ``TimeSeriesDataset``
containing all predictions with their ``available_at`` timestamps intact:

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting.backtest_pipeline import BacktestPipeline, BacktestConfig
   from datetime import timedelta

   pipeline = BacktestPipeline(
       config=BacktestConfig(prediction_sample_interval=timedelta(minutes=15)),
       forecaster=MedianBaselineForecaster(),
   )

   predictions = pipeline.run(
       ground_truth=versioned_ground_truth,   # VersionedTimeSeriesDataset
       predictors=versioned_predictors,       # VersionedTimeSeriesDataset
       start=datetime(2023, 1, 1),
       end=datetime(2023, 6, 30),
       show_progress=True,
   )

.. note::

   ``BacktestPipeline`` validates that ``BacktestConfig.prediction_sample_interval``
   matches ``BacktestForecasterConfig.predict_sample_interval`` at construction time.
   A ``ValueError`` is raised immediately if they differ, preventing silent
   misconfigurations.


Evaluation: Lead Times and Availability Windows
------------------------------------------------

Raw backtest predictions are a flat dataset of timestamped forecasts. Evaluation
structures them into operationally meaningful slices using two concepts:

- **Available-at windows** — when was the forecast generated? A day-ahead forecast
  available at 06:00 the previous day (``D-1T06:00``) is evaluated separately from an
  intraday forecast.
- **Lead times** — how far ahead is the forecast horizon? Accuracy typically degrades
  with lead time, and BEAM makes this degradation visible.

These are configured through ``EvaluationConfig``, which is embedded in the higher-level
``BenchmarkPipeline``:

.. code-block:: python

   from openstef_beam.benchmarking.benchmark_pipeline import EvaluationConfig, AvailableAt, LeadTime, Window
   from datetime import timedelta

   evaluation_config = EvaluationConfig(
       available_ats=[
           AvailableAt.from_string("D-1T06:00"),   # day-ahead at 06:00
       ],
       lead_times=[
           LeadTime.from_string("P1D"),             # 24-hour horizon
       ],
       windows=[
           Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           Window(lag=timedelta(hours=0), size=timedelta(days=30)),
       ],
   )

Metrics are computed per slice. BEAM ships with standard energy forecasting metrics
including ``rMAE``, ``rCRPS``, ``rCRPS_sample_weighted``, and effective precision/recall
curves for probabilistic forecasts.


Analysis and Visualisation
--------------------------

The analysis layer converts evaluation scores into reports. ``AnalysisConfig`` maps
metric names to visualisation types. BEAM provides several built-in visualisation
classes that produce interactive HTML output:

- ``GroupedTargetMetricVisualization`` — bar charts comparing a single metric across
  target groups (e.g. solar parks vs. industrial loads).
- ``SummaryTableVisualization`` — tabular overview of all metrics across all targets.
- ``PrecisionRecallCurveVisualization`` — standard and effective precision/recall curves
  for probabilistic forecast quality.
- ``QuantileProbabilityVisualization`` — calibration plots showing whether predicted
  quantiles match empirical frequencies.

A typical analysis configuration looks like this:

.. code-block:: python

   from openstef_beam.benchmarking.benchmark_pipeline import AnalysisConfig
   from openstef_beam.benchmarking.visualizations import (
       GroupedTargetMetricVisualization,
       SummaryTableVisualization,
       PrecisionRecallCurveVisualization,
       QuantileProbabilityVisualization,
   )
   from openstef_core.quantiles import Quantile

   analysis_config = AnalysisConfig(
       visualizations=[
           GroupedTargetMetricVisualization(
               name="rMAE_grouped",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           GroupedTargetMetricVisualization(
               name="rCRPS_grouped",
               metric="rCRPS",
           ),
           SummaryTableVisualization(name="summary"),
           PrecisionRecallCurveVisualization(
               name="precision_recall_curve",
               effective_precision_recall=False,
           ),
           QuantileProbabilityVisualization(name="quantile_probability"),
       ]
   )

All outputs are written to the configured ``BenchmarkStorage`` backend. The default
``LocalBenchmarkStorage`` organises results under a directory tree keyed by run name,
target group, and target name.


The Benchmarking Layer
----------------------

``BenchmarkPipeline`` is the top-level orchestrator. It ties together a target
provider, a forecaster factory, backtest configuration, evaluation configuration, and
analysis configuration into a single ``run()`` call that can execute across many targets
in parallel.

The **target provider** is responsible for supplying the list of targets and loading
their data. BEAM ships with ``create_liander2024_benchmark_runner()``, a factory that
configures a complete pipeline against the publicly available Liander 2024 energy
forecasting dataset (auto-downloaded from HuggingFace):

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking.benchmarks import create_liander2024_benchmark_runner
   from openstef_beam.benchmarking.benchmark_pipeline import LocalBenchmarkStorage
   from openstef_beam.benchmarking.callbacks import StrictExecutionCallback

   runner = create_liander2024_benchmark_runner(
       storage=LocalBenchmarkStorage(base_path=Path("./results/my_model")),
       callbacks=[StrictExecutionCallback()],
   )

   runner.run(
       forecaster_factory=my_forecaster_factory,
       run_name="my_model_v1",
       n_processes=4,
       filter_args=None,   # None = run all target categories
   )

The ``forecaster_factory`` argument is a callable that receives a ``BenchmarkContext``
and a ``BenchmarkTarget`` and returns a fresh forecaster instance. This pattern ensures
each target gets an independent model with no shared state:

.. code-block:: python

   from openstef_beam.benchmarking.benchmark_pipeline import BenchmarkContext, BenchmarkTarget

   def my_forecaster_factory(
       context: BenchmarkContext,
       target: BenchmarkTarget,
   ) -> MedianBaselineForecaster:
       return MedianBaselineForecaster()

For OpenSTEF model workflows, BEAM provides a convenience factory builder that wraps
any ``ForecastingWorkflowConfig`` into a ready-to-use factory:

.. code-block:: python

   from openstef_beam.benchmarking.openstef4_forecaster import (
       create_openstef4_preset_backtest_forecaster,
   )

   forecaster_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=my_workflow_config,
       cache_dir=Path("./cache"),
   )

   runner.run(
       forecaster_factory=forecaster_factory,
       run_name="gblinear_v1",
       n_processes=4,
   )


Comparing Multiple Runs
-----------------------

After running benchmarks for several models, ``BenchmarkComparisonPipeline`` generates
side-by-side comparison plots across all runs. It automatically detects which targets
are present in every run, ensuring fair comparisons:

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking.benchmark_comparison_pipeline import BenchmarkComparisonPipeline
   from openstef_beam.benchmarking.benchmark_pipeline import LocalBenchmarkStorage
   from openstef_beam.benchmarking.benchmarks import create_liander2024_benchmark_runner

   run_storages = {
       "baseline": LocalBenchmarkStorage(base_path=Path("./results/baseline")),
       "gblinear":  LocalBenchmarkStorage(base_path=Path("./results/gblinear_v1")),
   }

   target_provider = create_liander2024_benchmark_runner(
       storage=LocalBenchmarkStorage(base_path=Path("./results_comparison")),
   ).target_provider

   comparison = BenchmarkComparisonPipeline(
       analysis_config=analysis_config,
       storage=LocalBenchmarkStorage(base_path=Path("./results_comparison")),
       target_provider=target_provider,
   )
   comparison.run(run_data=run_storages)

Comparison output — global, per-group, and per-target HTML plots — is written to the
storage path. This makes it straightforward to track model improvements across
development iterations or to compare a new architecture against an established baseline.


Evaluating Pre-existing Forecasts
----------------------------------

BEAM does not require you to run backtesting through its pipeline. If you already have
predictions from an external system or a previous run, you can point the pipeline at
pre-existing ``predictions.parquet`` files and run only the evaluation and analysis
phases.

The expected directory layout is::

   benchmark_results/<RunName>/backtest/<group_name>/<target_name>/predictions.parquet

Each parquet file must contain a ``DatetimeIndex`` named ``timestamp``, an
``available_at`` column recording when each forecast was generated, and one column per
quantile named using the ``Quantile(x).format()`` convention (e.g. ``quantile_P05``,
``quantile_P50``, ``quantile_P95``). The ``quantile_P50`` column is required.

.. note::

   This workflow is particularly useful when integrating BEAM into an existing
   forecasting system that already produces operational forecasts. You gain access to
   BEAM's full evaluation and analysis stack without needing to restructure your
   production pipeline.


Package Dependencies
--------------------

BEAM is deliberately positioned as the evaluation layer of the OpenSTEF library stack.
It depends on both sibling packages:

- **openstef_core** — for ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and
  ``BaseConfig``. BEAM's temporal restriction mechanism is built directly on top of the
  versioned dataset abstraction described in :doc:`core`.
- **openstef_models** — for ``ForecastingWorkflowConfig`` and the transform pipeline
  that ``create_openstef4_preset_backtest_forecaster`` wraps. The model transforms
  covered in :doc:`models` are what BEAM exercises during each simulated retraining
  cycle.

Neither ``openstef_core`` nor ``openstef_models`` depends on ``openstef_beam``. The
dependency is strictly one-directional: BEAM consumes the other packages but does not
affect them. This means you can use the core data structures or the models transforms
independently without pulling in the full evaluation framework.

For ensemble models and advanced meta-learning approaches that can be plugged into BEAM
as forecasters, see :doc:`meta`.