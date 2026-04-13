The OpenSTEF BEAM Package
=========================

The ``openstef_beam`` package implements the **Backtesting, Evaluation, Analysis and
Metrics** framework for OpenSTEF. Where ``openstef_core`` provides data structures and
``openstef_models`` provides the transforms that shape features, BEAM sits one level
higher: it orchestrates complete model evaluation workflows, from replaying historical
data under realistic constraints all the way through to comparative benchmark reports.

This page covers how BEAM is structured, how its four sub-systems relate to one
another, and how to use the library's public API to evaluate and compare forecasting
models.

.. note::
   BEAM depends on both ``openstef_core`` (for ``TimeSeriesDataset`` and
   ``VersionedTimeSeriesDataset``) and ``openstef_models`` (for the transform-based
   forecaster interface). See the sibling pages on :doc:`core` and :doc:`models` for
   details on those packages.

.. note:: [DIAGRAM: Component-level diagram showing the BEAM evaluation workflow. Four
   vertically stacked stages connected by arrows: (1) Backtesting — BacktestPipeline
   consumes VersionedTimeSeriesDataset, enforces temporal horizon constraints via
   RestrictedHorizonVersionedTimeSeries, and emits a TimeSeriesDataset of predictions;
   (2) Evaluation — EvaluationPipeline segments predictions by lead time, time window,
   and filter, then computes metrics to produce an EvaluationReport; (3) Analysis —
   AnalysisPipeline aggregates EvaluationReports across runs/targets and produces
   visualisations; (4) Benchmarking — BenchmarkPipeline orchestrates all three stages
   in parallel across many targets using a ForecasterFactory and a pluggable
   BenchmarkStorage backend. Arrows also show the dependency edges: BenchmarkPipeline
   → BacktestPipeline, EvaluationPipeline, AnalysisPipeline; all stages → openstef_core
   datasets; BacktestForecasterMixin ← openstef_models transforms.]


Why Realistic Evaluation Matters
---------------------------------

A common mistake in time-series model evaluation is training on a full historical
dataset and then measuring accuracy on a held-out slice. This ignores the fact that
in production, a model is periodically retrained with whatever data was available *at
that moment*, and predictions are made without access to future observations.

BEAM addresses this through **versioned data**. The ``VersionedTimeSeriesDataset``
(from ``openstef_core``) records not just what happened, but *when each data point
became available*. BEAM's backtesting layer wraps this dataset in a
``RestrictedHorizonVersionedTimeSeries`` that enforces a strict temporal horizon:
the model can only see data that would have existed at prediction time. Retraining
events are scheduled at realistic intervals, mirroring how the model would be
operated in a live deployment.

The result is an evaluation that accurately reflects real-world model performance
rather than an optimistic in-sample score.


Backtesting
-----------

The ``openstef_beam.backtesting`` sub-package is the foundation of every BEAM
workflow. ``BacktestPipeline`` drives the simulation loop: it generates a sequence
of ``BacktestEvent`` objects (train events and prediction events), processes each
one in chronological order, and collects the resulting predictions into a single
``TimeSeriesDataset``.

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   # Configure the simulation
   config = BacktestConfig(
       train_interval_hours=24,        # retrain every 24 hours
       prediction_sample_interval="15min",
   )

   # Attach your forecaster (must implement BacktestForecasterMixin)
   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   # Run the simulation over a historical window
   predictions: TimeSeriesDataset = pipeline.run(
       ground_truth=versioned_ground_truth,
       predictors=versioned_predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
   )

The ``forecaster`` argument must implement ``BacktestForecasterMixin``, which defines
``fit`` and ``predict`` (or their batch equivalents for models that support
``BacktestBatchForecasterMixin``). This interface is deliberately thin so that any
model — including those built on ``openstef_models`` transforms — can be plugged in
with minimal boilerplate.

The returned ``TimeSeriesDataset`` carries an ``available_at`` column alongside the
predicted values, preserving the temporal metadata needed by the evaluation stage.


Evaluation
----------

Once backtesting produces a dataset of predictions, ``openstef_beam.evaluation``
turns those raw numbers into structured performance reports. The
``EvaluationPipeline`` segments the prediction data across three orthogonal
dimensions and computes metrics for every resulting subset:

- **Lead times** — how accuracy degrades from a 1-hour to a 48-hour horizon.
- **Time windows** — performance differences across days, weeks, or seasons.
- **Filters** — focus on specific conditions such as peak-load hours or weekdays.

.. code-block:: python

   from openstef_beam.evaluation import (
       EvaluationConfig,
       EvaluationPipeline,
       Window,
       Filtering,
   )

   eval_config = EvaluationConfig(
       lead_times=[1, 4, 12, 24, 48],   # hours ahead
       windows=[Window.DAILY, Window.WEEKLY],
       filterings=[Filtering.PEAK_HOURS],
   )

   eval_pipeline = EvaluationPipeline(config=eval_config)
   report: EvaluationReport = eval_pipeline.run(
       predictions=predictions,
       ground_truth=ground_truth_dataset,
   )

The ``EvaluationReport`` is a structured object containing ``EvaluationSubsetReport``
instances, each holding a list of ``SubsetMetric`` results. This hierarchical
structure makes it straightforward to compare a specific lead time across different
time windows, or to drill down into a particular filtering condition.

Custom metrics can be registered through the ``metric_providers`` module, allowing
domain-specific measures (e.g. curtailment-weighted error) to sit alongside the
built-in ones without modifying library code.


Analysis
--------

The analysis layer consumes one or more ``EvaluationReport`` objects and produces
human-readable outputs: visualisations, aggregated tables, and comparison summaries.
``AnalysisPipeline`` is configured with an ``AnalysisConfig`` that specifies which
aggregations and scopes are relevant for a given study.

``AnalysisScope`` controls the granularity of the output — whether results are
aggregated at the level of an individual run, a target type, or the full benchmark.
``AnalysisAggregation`` determines how metrics are combined across subsets (mean,
median, percentile bands, etc.).

Because analysis is a separate stage with its own pipeline, it is easy to re-run
visualisation and reporting logic against previously stored ``EvaluationReport``
data without repeating the expensive backtesting step.


Benchmarking
------------

``openstef_beam.benchmarking`` is the top-level orchestrator that ties all three
stages together and scales them across many forecasting targets. A *target* in BEAM
terminology is any entity you want to forecast — a substation, a solar park, a
regional grid connection — represented by a ``BenchmarkTarget`` instance.

The central class is ``BenchmarkPipeline``, which accepts:

- a ``TargetProvider`` that supplies the list of targets and their datasets,
- a ``ForecasterFactory`` callable that constructs a forecaster for each target,
- a ``BenchmarkStorage`` backend for persisting results,
- and the three stage-level config objects.

.. code-block:: python

   from openstef_beam.benchmarking import (
       BenchmarkPipeline,
       BenchmarkContext,
       LocalBenchmarkStorage,
       SimpleTargetProvider,
       TargetProviderConfig,
   )
   from openstef_beam.backtesting import BacktestConfig
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.analysis import AnalysisConfig, AnalysisScope

   def create_forecaster(context: BenchmarkContext, target):
       # Instantiate and return a BacktestForecasterMixin implementation.
       # The context carries the run_name and any benchmark-level metadata.
       return MyForecaster(target_id=target.id)

   pipeline = BenchmarkPipeline(
       backtest_config=BacktestConfig(train_interval_hours=24),
       evaluation_config=EvaluationConfig(lead_times=[1, 4, 24]),
       analysis_config=AnalysisConfig(scope=AnalysisScope.TARGET),
       target_provider=SimpleTargetProvider(
           config=TargetProviderConfig(targets=my_target_list)
       ),
       storage=LocalBenchmarkStorage(path="./benchmark_results"),
   )

   pipeline.run(
       forecaster_factory=create_forecaster,
       run_name="baseline_v1",
       n_processes=4,
   )

Targets are processed in parallel when ``n_processes > 1``. The ``BenchmarkCallback``
mechanism lets you hook into lifecycle events (target started, target completed,
benchmark finished) for logging, alerting, or intermediate result flushing — without
subclassing the pipeline itself.

Storage backends are pluggable. ``LocalBenchmarkStorage`` writes results to the
filesystem; ``S3BenchmarkStorage`` targets object storage for team-shared studies;
``InMemoryBenchmarkStorage`` is convenient for unit tests and notebook exploration.
Previously stored results can be loaded back with ``read_evaluation_reports`` for
post-hoc analysis or comparison against a new run.

Comparing Two Runs
^^^^^^^^^^^^^^^^^^

``BenchmarkComparisonPipeline`` extends the single-run pipeline to compare two named
runs — for example, a baseline model against a candidate — and produce a diff report
highlighting where performance improved or regressed:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline

   comparison = BenchmarkComparisonPipeline(
       baseline_run="baseline_v1",
       candidate_run="candidate_v2",
       storage=LocalBenchmarkStorage(path="./benchmark_results"),
       analysis_config=AnalysisConfig(scope=AnalysisScope.TARGET),
   )
   comparison.run()

.. note::
   ``StrictExecutionCallback`` is a built-in callback that converts any per-target
   failure into an immediate exception, useful in CI pipelines where a silent failure
   would otherwise go unnoticed.


Package Dependencies
--------------------

BEAM is intentionally positioned as the highest-level package in the OpenSTEF
library stack. Its dependency graph is one-directional:

- ``openstef_beam`` → ``openstef_core`` for dataset types (``TimeSeriesDataset``,
  ``VersionedTimeSeriesDataset``) and base configuration classes.
- ``openstef_beam`` → ``openstef_models`` for the forecaster interface and any
  transform-based model implementations passed in via ``ForecasterFactory``.

Neither ``openstef_core`` nor ``openstef_models`` imports from ``openstef_beam``,
which means you can use the lower-level packages independently when you only need
data handling or model transforms. BEAM is the right entry point when you need the
full evaluation workflow.

.. note::
   If you are building a custom forecaster to plug into BEAM, start with the
   ``BacktestForecasterMixin`` interface in ``openstef_beam.backtesting`` and the
   transform primitives described on the :doc:`models` sibling page. The
   :doc:`core` page covers ``VersionedTimeSeriesDataset`` and the versioning
   semantics that underpin BEAM's data-leakage prevention.