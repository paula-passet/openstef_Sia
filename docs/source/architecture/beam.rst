The OpenSTEF BEAM Package
=========================

**openstef_beam** is the evaluation and benchmarking layer of the OpenSTEF library. Its name is a deliberate acronym: **B**\acktesting, **E**\valuation, **A**\nalysis, and **M**\etrics. Where ``openstef_core`` provides data structures and ``openstef_models`` provides transforms and model primitives, BEAM orchestrates the complete workflow for determining how well a forecasting model actually performs under realistic conditions.

This page covers the BEAM package in depth — its design philosophy, the four sub-systems it contains, how they connect, and how to use them in practice. For the data structures that BEAM consumes (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``), see the :doc:`core` page. For the model transforms that BEAM-compatible forecasters are built from, see the :doc:`models` page.

.. mermaid:: diagrams/architecture/beam_diagram_1.mmd

Why Realistic Evaluation Matters
---------------------------------

A common mistake in time-series model evaluation is training on a portion of history and testing on the remainder without accounting for *when* data was actually available. In energy forecasting, measurements are often revised after the fact, weather forecasts improve as the horizon shrinks, and operational systems retrain models on a rolling schedule. Evaluating a model without respecting these constraints produces optimistic results that do not transfer to production.

BEAM addresses this by requiring that all data be supplied as ``VersionedTimeSeriesDataset`` objects — a ``openstef_core`` type that tracks *when* each observation became available. The backtesting engine then enforces a strict temporal horizon: at any simulated prediction time, the model may only see data that was available *before* that moment. This prevents data leakage at the library level rather than relying on the user to be careful.

The Four Sub-Systems
---------------------

Backtesting
^^^^^^^^^^^

The ``openstef_beam.backtesting`` module simulates operational deployment by replaying history in chronological order. At each prediction step the pipeline calls the forecaster with only the data that would have been available at that instant; at each retraining step it retrains the model from scratch on the same restricted view. The key classes are ``BacktestPipeline`` and its configuration object ``BacktestConfig``.

.. code-block:: python

    from datetime import datetime
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        prediction_interval=60,          # predict every 60 minutes
        training_interval=1440,          # retrain every 24 hours
        horizon=48,                      # forecast 48 hours ahead
    )

    # `forecaster` must implement BacktestForecasterMixin
    pipeline = BacktestPipeline(config=config, forecaster=forecaster)

    predictions: TimeSeriesDataset = pipeline.run(
        ground_truth=versioned_ground_truth,
        predictors=versioned_predictors,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
        show_progress=True,
    )

``BacktestPipeline.run`` returns a plain ``TimeSeriesDataset`` containing all predictions generated during the simulation period. This dataset is the primary input to the evaluation stage.

To integrate your own model, implement ``BacktestForecasterMixin`` (for single-step prediction) or ``BacktestBatchForecasterMixin`` (for vectorised batch prediction). The mixin interface is intentionally minimal: implement ``predict`` and ``train``, and BEAM handles all scheduling and data windowing.

Evaluation
^^^^^^^^^^

The ``openstef_beam.evaluation`` module takes the raw predictions produced by backtesting and organises them into structured performance reports. Rather than computing a single aggregate score, ``EvaluationPipeline`` segments the data across three dimensions simultaneously:

- **Lead times** — how accuracy degrades as the forecast horizon grows (e.g., 1 h, 6 h, 24 h, 48 h ahead).
- **Time windows** — performance across calendar periods such as days, weeks, or seasons.
- **Filterings** — user-defined conditions such as peak-load hours, weekdays only, or specific weather regimes.

Each combination of these dimensions produces an ``EvaluationSubsetReport`` containing the computed ``SubsetMetric`` values. All subset reports are collected into a single ``EvaluationReport``.

.. code-block:: python

    from openstef_beam.evaluation import (
        EvaluationPipeline,
        EvaluationConfig,
        EvaluationReport,
        Window,
        Filtering,
    )

    eval_config = EvaluationConfig(
        lead_times=[1, 6, 24, 48],
        windows=[Window.DAY, Window.WEEK],
        filterings=[Filtering.ALL, Filtering.PEAK_HOURS],
    )

    eval_pipeline = EvaluationPipeline(config=eval_config)
    report: EvaluationReport = eval_pipeline.run(
        predictions=predictions,
        ground_truth=ground_truth,
    )

    # Access a specific subset
    for subset in report.subset_reports:
        print(subset.lead_time, subset.window, subset.metrics)

The ``metric_providers`` sub-module ships with standard energy-forecasting metrics (MAE, RMSE, skill scores) and exposes an interface for registering custom metrics, so you are not limited to the built-in set.

Analysis
^^^^^^^^

Evaluation produces numbers; analysis turns those numbers into insight. The ``openstef_beam.analysis`` module accepts one or more ``EvaluationReport`` objects and produces comparative visualisations and aggregated tables. ``AnalysisPipeline`` is configured with an ``AnalysisConfig`` that specifies which aggregations and plots to generate, and an ``AnalysisScope`` that controls whether the analysis covers a single run or compares multiple runs side by side.

.. code-block:: python

    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig, AnalysisScope

    analysis_config = AnalysisConfig(
        scope=AnalysisScope.SINGLE_RUN,
        aggregations=["lead_time_summary", "window_heatmap"],
    )

    analysis_pipeline = AnalysisPipeline(config=analysis_config)
    analysis_pipeline.run(reports=[report], run_name="baseline_v1")

When ``AnalysisScope.MULTI_RUN`` is used, the pipeline aligns reports from different runs by target and lead time, enabling direct model-to-model comparison without manual data wrangling.

Benchmarking
^^^^^^^^^^^^

The three sub-systems above are powerful individually, but the real value of BEAM comes from running them together across many forecasting targets at once. ``BenchmarkPipeline`` is the top-level orchestrator that does exactly this.

.. code-block:: python

    from openstef_beam.benchmarking import (
        BenchmarkPipeline,
        BenchmarkContext,
        ForecasterFactory,
        LocalBenchmarkStorage,
        SimpleTargetProvider,
    )
    from openstef_beam.backtesting import BacktestConfig
    from openstef_beam.evaluation import EvaluationConfig
    from openstef_beam.analysis import AnalysisConfig, AnalysisScope

    def create_forecaster(context: BenchmarkContext, target) -> MyForecaster:
        """Factory function — called once per target."""
        return MyForecaster(config=target.get_model_config())

    pipeline = BenchmarkPipeline(
        backtest_config=BacktestConfig(prediction_interval=60, training_interval=1440, horizon=48),
        evaluation_config=EvaluationConfig(lead_times=[1, 6, 24, 48]),
        analysis_config=AnalysisConfig(scope=AnalysisScope.MULTI_RUN),
        target_provider=SimpleTargetProvider(targets=my_targets),
        storage=LocalBenchmarkStorage(path="./benchmark_results"),
    )

    pipeline.run(
        forecaster_factory=create_forecaster,
        run_name="xgboost_vs_lightgbm",
        n_processes=4,
    )

``BenchmarkPipeline`` iterates over every target supplied by the ``TargetProvider``, applies the ``ForecasterFactory`` to create a target-specific model instance, runs the full backtesting → evaluation → analysis chain, and persists results via the configured ``BenchmarkStorage`` backend.

Storage Backends
----------------

BEAM ships three storage backends for benchmark results, all implementing the ``BenchmarkStorage`` interface:

- ``InMemoryBenchmarkStorage`` — results are kept in memory; useful for interactive exploration and unit tests.
- ``LocalBenchmarkStorage`` — results are written to a local directory as structured files; suitable for single-machine workflows.
- ``S3BenchmarkStorage`` — results are written to an S3-compatible object store; intended for distributed or cloud-based benchmark runs.

Switching backends requires only changing the ``storage=`` argument to ``BenchmarkPipeline``; the rest of the workflow is identical.

Callbacks and Extensibility
----------------------------

``BenchmarkPipeline`` accepts a list of ``BenchmarkCallback`` objects that receive events at each stage of the workflow. This is the primary extension point for adding monitoring, logging to external systems, or triggering downstream actions without modifying the pipeline itself. ``StrictExecutionCallback`` is a built-in callback that causes the pipeline to abort on the first target failure rather than continuing — useful when you need all-or-nothing semantics.

.. code-block:: python

    from openstef_beam.benchmarking import BenchmarkCallback, StrictExecutionCallback

    class SlackNotificationCallback(BenchmarkCallback):
        def on_target_complete(self, context, target, report):
            post_to_slack(f"Finished target {target.name}: MAE={report.mae:.3f}")

    pipeline = BenchmarkPipeline(
        ...,
        callbacks=[StrictExecutionCallback(), SlackNotificationCallback()],
    )

Comparing Multiple Runs
------------------------

After one or more benchmark runs have been stored, ``read_evaluation_reports`` retrieves them for post-hoc comparison without re-running the pipeline:

.. code-block:: python

    from openstef_beam.benchmarking import read_evaluation_reports
    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig, AnalysisScope

    reports = read_evaluation_reports(
        storage=LocalBenchmarkStorage(path="./benchmark_results"),
        run_names=["xgboost_baseline", "lightgbm_tuned"],
    )

    AnalysisPipeline(
        config=AnalysisConfig(scope=AnalysisScope.MULTI_RUN)
    ).run(reports=reports)

This separation between *running* a benchmark and *analysing* its results means you can iterate on analysis and visualisation without paying the cost of re-running backtests.

.. note::

   ``BenchmarkComparisonPipeline`` provides a higher-level wrapper around ``read_evaluation_reports`` + ``AnalysisPipeline`` for the common case of comparing exactly two runs head-to-head. It is a convenience class; everything it does can be replicated with the lower-level APIs.

Dependency Summary
------------------

BEAM sits at the top of the OpenSTEF package dependency graph:

- ``openstef_beam`` depends on ``openstef_core`` for ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and base configuration types.
- ``openstef_beam`` depends on ``openstef_models`` for the transform primitives and ``HorizonTransform`` used inside ``BacktestForecasterMixin``.
- Neither ``openstef_core`` nor ``openstef_models`` depends on ``openstef_beam``, keeping the lower layers lean and independently usable.

This means you can use ``openstef_core`` and ``openstef_models`` to build and deploy forecasting models without pulling in the evaluation machinery, and you can use BEAM to evaluate any model that implements the ``BacktestForecasterMixin`` interface — including models built entirely outside OpenSTEF.