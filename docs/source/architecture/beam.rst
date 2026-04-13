The OpenSTEF BEAM Package
=========================

``openstef_beam`` is the **Backtesting, Evaluation, Analysis and Metrics** framework within the OpenSTEF library ecosystem. Where ``openstef_core`` defines the data structures and ``openstef_models`` provides the forecasting transforms, BEAM provides everything needed to answer the critical question: *how well does a model actually perform under realistic conditions?*

This page covers the four interlocking subsystems of BEAM — backtesting, evaluation, analysis, and benchmarking — and explains how they compose into complete evaluation workflows. For the data structures that BEAM consumes, see the :doc:`core` page. For the model transforms that BEAM evaluates, see the :doc:`models` page.

.. note::

   [DIAGRAM: Component-level diagram of the BEAM workflow. Left-to-right flow: (1) VersionedTimeSeriesDataset (from openstef_core) feeds into (2) BacktestPipeline, which uses RestrictedHorizonVersionedTimeSeries to enforce temporal constraints and a BacktestForecasterMixin (from openstef_models) to produce a TimeSeriesDataset of predictions. Those predictions flow into (3) EvaluationPipeline, which computes metrics across AvailableAt × LeadTime × Window dimensions and produces an EvaluationReport. The report feeds into (4) AnalysisPipeline, which generates visualisations and comparison reports. Multiple AnalysisReports from different runs feed into (5) BenchmarkComparisonPipeline for cross-run comparison. BenchmarkPipeline sits above steps 2–5 as the top-level orchestrator, delegating to each sub-pipeline in sequence and routing results through a pluggable BenchmarkStorage backend.]


Why Realistic Evaluation Matters
---------------------------------

A common pitfall in time-series forecasting is evaluating a model on data it could not have seen in production. BEAM prevents this by using ``VersionedTimeSeriesDataset`` — a data structure that records *when* each observation became available, not just what its timestamp is. During backtesting, every prediction is made with only the data that would have existed at that moment in time. Models are retrained on a schedule that mirrors production deployment, so the evaluation reflects genuine operational performance rather than an optimistic in-sample fit.


Backtesting
-----------

The ``openstef_beam.backtesting`` subpackage is the engine that replays history. ``BacktestPipeline`` drives the simulation: it walks forward through time, fires training events at the configured retraining cadence, and fires prediction events according to the prediction schedule. At each prediction event the pipeline wraps the full dataset in a ``RestrictedHorizonVersionedTimeSeries``, which enforces that the forecaster can only call ``get_window`` for timestamps strictly before the current simulation horizon.

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

   config = BacktestConfig(
       prediction_sample_interval="PT15M",
   )

   pipeline = BacktestPipeline(
       config=config,
       forecaster=my_forecaster,  # implements BacktestForecasterMixin
   )

   predictions = pipeline.run(
       ground_truth=versioned_ground_truth,   # VersionedTimeSeriesDataset
       predictors=versioned_predictors,       # VersionedTimeSeriesDataset
       start=datetime(2024, 1, 1),
       end=datetime(2024, 6, 30),
       show_progress=True,
   )
   # predictions is a TimeSeriesDataset with an `available_at` column
   # recording when each prediction was generated

The return value is a plain ``TimeSeriesDataset`` whose ``available_at`` column records the simulation timestamp at which each row was produced. This provenance information is essential for the evaluation stage.

Any forecaster plugged into ``BacktestPipeline`` must implement ``BacktestForecasterMixin``. Models that support vectorised inference can additionally implement ``BacktestBatchForecasterMixin``, which allows the pipeline to group prediction events into batches and call ``predict_batch_versioned`` instead of making individual calls — a significant throughput improvement for large backtests.


Evaluation
----------

Once predictions exist, ``EvaluationPipeline`` computes performance metrics across multiple dimensions simultaneously. The key insight is that a single ``EvaluationReport`` captures performance broken down by:

- **AvailableAt** — the time of day when the forecast was issued (e.g. ``D-1T06:00``, meaning the day-ahead forecast available at 06:00 the previous day).
- **LeadTime** — how far ahead each prediction looks (e.g. ``PT36H`` for a 36-hour horizon).
- **Window** — rolling time windows over the evaluation period for detecting drift or seasonal effects.

``EvaluationConfig`` controls which combinations are computed:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
   from openstef_beam.evaluation.models import AvailableAt, LeadTime, Window
   from datetime import timedelta

   config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[
           LeadTime.from_string("PT12H"),
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT36H"),
       ],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

   pipeline = EvaluationPipeline(
       config=config,
       quantiles=[0.1, 0.5, 0.9],   # 0.5 is required
       window_metric_providers=[rmse_provider, mae_provider],
       global_metric_providers=[skill_score_provider],
   )

   report = pipeline.run(
       predictions=predictions,
       ground_truth=versioned_ground_truth,
       target_column="load_mw",
   )

``EvaluationPipeline`` automatically appends an ``ObservedProbabilityProvider`` to the global metrics list, ensuring that probabilistic calibration is always measured regardless of which custom metrics are supplied. The resulting ``EvaluationReport`` is a structured object that carries the full metric matrix and is the primary input to the analysis stage.

.. note::

   The quantiles list passed to ``EvaluationPipeline`` must always include ``0.5``. Omitting the median raises a ``ValueError`` at construction time, because the median forecast is required for point-forecast metrics such as RMSE.


Analysis
--------

``AnalysisPipeline`` transforms an ``EvaluationReport`` (or a collection of reports) into human-readable visualisations and comparison tables. It operates at three scopes controlled by ``AnalysisScope``:

- **Target level** — detailed breakdown for a single forecasting target.
- **Group level** — aggregated view across a named group of targets (e.g. all solar parks in a region).
- **Global level** — summary across every target and run.

The ``AnalysisAggregation`` enum governs which aggregation is applied, and ``AnalysisPipeline.run_for_reports`` accepts a list of ``(TargetMetadata, EvaluationReport)`` tuples so that multiple runs can be compared in a single call:

.. code-block:: python

   from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig, AnalysisScope
   from openstef_beam.analysis.models import AnalysisAggregation

   analysis_pipeline = AnalysisPipeline(config=AnalysisConfig())

   visualisations = analysis_pipeline.run_for_reports(
       reports=[(target_metadata, report)],
       scope=AnalysisScope(
           aggregation=AnalysisAggregation.NONE,
           target_name="substation_42",
           group_name="north_region",
           run_name="xgboost_v2",
       ),
   )

The output ``visualisations`` object can be persisted through any ``BenchmarkStorage`` backend (see below).


Benchmarking: Orchestrating the Full Workflow
---------------------------------------------

``BenchmarkPipeline`` is the top-level orchestrator that wires together all of the above into a single, repeatable workflow. Given a ``TargetProvider`` (which supplies the list of forecasting targets) and a ``ForecasterFactory`` (a callable that constructs a forecaster for each target), ``BenchmarkPipeline.run`` executes the full sequence — backtest, evaluate, analyse — for every target, optionally in parallel:

.. code-block:: python

   from openstef_beam.benchmarking import (
       BenchmarkPipeline,
       BenchmarkContext,
       BenchmarkTarget,
       LocalBenchmarkStorage,
       SimpleTargetProvider,
   )

   # ForecasterFactory: (BenchmarkContext, BenchmarkTarget) -> BacktestForecasterMixin
   def my_factory(context: BenchmarkContext, target: BenchmarkTarget):
       return MyForecaster(target=target, run_name=context.run_name)

   pipeline = BenchmarkPipeline(
       target_provider=SimpleTargetProvider(targets=my_targets),
       storage=LocalBenchmarkStorage(path="./benchmark_results"),
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=AnalysisConfig(),
   )

   pipeline.run(
       forecaster_factory=my_factory,
       run_name="xgboost_v2",
       n_processes=4,   # parallelise across targets
   )

The ``BenchmarkContext`` passed to the factory carries the ``run_name`` and any other metadata needed to customise model creation per run. This factory pattern means the same pipeline definition can be reused across experiments simply by swapping the factory or the ``run_name``.

Storage Backends
^^^^^^^^^^^^^^^^

``BenchmarkPipeline`` writes results through a ``BenchmarkStorage`` interface, keeping the evaluation logic independent of where results end up. Three backends ship with BEAM:

- ``InMemoryBenchmarkStorage`` — for interactive exploration and unit tests.
- ``LocalBenchmarkStorage`` — writes artefacts to a local directory tree.
- ``S3BenchmarkStorage`` — writes artefacts directly to an S3-compatible object store.

Callbacks
^^^^^^^^^

``BenchmarkCallback`` provides hooks at each stage of the pipeline (``on_evaluation_complete``, ``on_analysis_complete``, and so on). ``BenchmarkCallbackManager`` composes multiple callbacks, and ``StrictExecutionCallback`` can be added to convert any per-target failure into an immediate pipeline abort — useful in CI environments where silent failures are unacceptable.


Comparing Multiple Runs
-----------------------

After running ``BenchmarkPipeline`` for several model variants, ``BenchmarkComparisonPipeline`` reads the stored ``EvaluationReport`` objects and produces cross-run comparison analysis. The ``read_evaluation_reports`` helper loads persisted reports from any storage backend:

.. code-block:: python

   from openstef_beam.benchmarking import (
       BenchmarkComparisonPipeline,
       read_evaluation_reports,
       LocalBenchmarkStorage,
   )

   storage = LocalBenchmarkStorage(path="./benchmark_results")
   reports = read_evaluation_reports(storage=storage)

   comparison = BenchmarkComparisonPipeline(analysis_config=AnalysisConfig())
   comparison.run(reports=reports)

``BenchmarkComparisonPipeline`` calls ``run_global``, ``run_for_groups``, and ``run_for_targets`` internally, producing a layered set of comparison visualisations that make it straightforward to identify which model variant performs best at which lead time or for which target group.


Package Dependencies
--------------------

BEAM sits at the top of the OpenSTEF dependency graph. It imports from both sibling packages:

- **openstef_core** — ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, ``BaseConfig``, ``run_parallel``, and the ``Quantile`` type alias are all consumed directly by BEAM's pipelines. See :doc:`core` for details on these types.
- **openstef_models** — forecasters passed to ``BacktestPipeline`` and ``BenchmarkPipeline`` are expected to implement the mixin interfaces defined in ``openstef_models``. See :doc:`models` for the transform and mixin patterns.

Neither ``openstef_core`` nor ``openstef_models`` depends on ``openstef_beam``, so BEAM can be installed independently when only evaluation tooling is needed without pulling in the full model training stack.

.. note::

   ``openstef_beam`` is a library. Nothing runs automatically on import. All pipelines are plain Python objects that you instantiate and call explicitly, making them straightforward to embed in notebooks, scripts, CI pipelines, or larger orchestration frameworks such as Apache Airflow or Prefect.