The OpenSTEF BEAM Package
=========================

**openstef_beam** is the evaluation arm of the OpenSTEF library. Its name is a deliberate acronym: **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics. Where ``openstef_core`` and ``openstef_models`` are concerned with building and running forecasting models, BEAM is concerned with rigorously testing them — simulating real-world deployment conditions, computing structured performance reports, generating visualizations, and coordinating large-scale model comparisons.

This page covers the architecture of the ``openstef_beam`` package in depth: how its four sub-systems relate to one another, the design decisions behind its temporal validation approach, and how to wire the pieces together in your own evaluation workflows.

For the ``TimeSeriesDataset`` and versioned data abstractions that BEAM depends on, see the :doc:`core` page. For the model transforms and forecaster interfaces that BEAM wraps, see the :doc:`models` page.

.. note:: [DIAGRAM: Component-level diagram showing the BEAM workflow. Left to right: (1) VersionedTimeSeriesDataset (from openstef_core) feeds into (2) BacktestPipeline, which produces a stream of (prediction, actuals) pairs. Those pairs flow into (3) EvaluationPipeline, which segments by lead time / time window / filtering and emits EvaluationReport objects. Reports feed into (4) AnalysisPipeline, which calls registered VisualizationProviders to produce VisualizationOutput. All four stages are coordinated by (5) BenchmarkPipeline / BenchmarkComparisonPipeline, which also manages BenchmarkStorage (Local / S3 / InMemory) and optional BenchmarkCallbacks. Dependency arrows: BenchmarkPipeline → BacktestPipeline → openstef_core; BacktestPipeline → BacktestForecasterMixin (openstef_models); EvaluationPipeline → metric_providers; AnalysisPipeline → VisualizationProviders.]

Why Backtesting Matters
-----------------------

A common mistake in time-series evaluation is computing metrics on a held-out test set that was assembled after the fact. When you do this, the model may have been trained on features derived from data that would not have been available at prediction time — a form of data leakage that makes results look better than they really are.

BEAM avoids this by treating evaluation as a *replay* of history. It uses ``VersionedTimeSeriesDataset`` from ``openstef_core`` to represent data as it existed at each point in time. When the backtesting pipeline simulates a forecast at, say, 14:00 on a given day, it restricts the model's view to only the data that was available before that timestamp. Models are retrained periodically on this restricted view, exactly as they would be in production.

The result is that BEAM's metrics are honest: they reflect what you would actually have observed if the model had been running live.

The Backtesting Layer
---------------------

The entry point for single-target backtesting is ``BacktestPipeline``. It requires a ``BacktestConfig`` that specifies the prediction and retraining cadences, and a forecaster that implements either ``BacktestForecasterMixin`` (for point-in-time predictions) or ``BacktestBatchForecasterMixin`` (for batch predictions over a window).

.. code-block:: python

    from datetime import datetime
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        prediction_interval=timedelta(hours=1),
        training_interval=timedelta(days=1),
        horizon=timedelta(hours=48),
    )

    pipeline = BacktestPipeline(
        config=config,
        forecaster=my_forecaster,   # implements BacktestForecasterMixin
    )

    predictions = pipeline.run(
        dataset=versioned_dataset,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
    )

Internally, ``BacktestPipeline`` drives a ``BacktestEventGenerator`` that emits ``BacktestEvent`` objects — one per prediction slot. Each event carries a ``RestrictedHorizonVersionedTimeSeries`` that wraps the underlying versioned dataset and enforces the temporal horizon, making it impossible for the forecaster to accidentally read future data.

The Evaluation Layer
--------------------

Raw predictions from the backtesting stage are not immediately useful for decision-making. The evaluation layer takes those predictions and organises them into structured ``EvaluationReport`` objects by segmenting the data across three orthogonal dimensions:

- **Lead times** — how far ahead the forecast was made (e.g., 1 h, 6 h, 24 h, 48 h).
- **Time windows** — calendar slices such as days, weeks, or seasons.
- **Filterings** — arbitrary conditions such as peak-load hours, weekdays only, or specific weather regimes.

``EvaluationPipeline`` accepts an ``EvaluationConfig`` that declares which lead times, windows, and filterings to compute, along with which ``metric_providers`` to apply to each subset.

.. code-block:: python

    from openstef_beam.evaluation import (
        EvaluationPipeline,
        EvaluationConfig,
        Window,
        Filtering,
        SubsetMetric,
    )
    from openstef_beam.evaluation import metric_providers

    eval_config = EvaluationConfig(
        lead_times=[1, 6, 24, 48],          # hours ahead
        windows=[Window.WEEKLY],
        filterings=[Filtering.ALL, Filtering.PEAK_HOURS],
        metrics=[
            SubsetMetric(provider=metric_providers.MAEProvider()),
            SubsetMetric(provider=metric_providers.RMSEProvider()),
        ],
    )

    eval_pipeline = EvaluationPipeline(config=eval_config)
    report = eval_pipeline.run(predictions=predictions, actuals=actuals)

The resulting ``EvaluationReport`` is a structured, serialisable object containing an ``EvaluationSubsetReport`` for every combination of lead time, window, and filtering. This design makes it straightforward to persist reports, compare them across runs, or feed them into the analysis layer.

The Analysis Layer
------------------

``AnalysisPipeline`` consumes one or more ``EvaluationReport`` objects and produces visualisations. Rather than hard-coding a fixed set of plots, the pipeline is driven by a list of ``VisualizationProvider`` objects registered in ``AnalysisConfig``. This makes it easy to add custom visualisations without modifying the pipeline itself.

The pipeline operates at two aggregation levels:

- **Individual target** — detailed plots for a single forecasting target (e.g., a single substation or wind park).
- **Multiple targets** — comparative plots that aggregate results across a group of targets.

.. code-block:: python

    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig
    from openstef_beam.analysis.models import AnalysisScope, TargetMetadata

    analysis_config = AnalysisConfig(
        visualization_providers=[
            LeadTimeErrorProvider(),    # custom or built-in provider
            SeasonalPerformanceProvider(),
        ]
    )

    analysis_pipeline = AnalysisPipeline(config=analysis_config)

    # Run for a single target
    output = analysis_pipeline.run_for_reports(
        reports=[(TargetMetadata(name="substation_A"), report)],
        scope=AnalysisScope.SINGLE,
    )

    # Run across a group of targets
    group_outputs = analysis_pipeline.run_for_groups(
        reports=target_report_pairs,
        scope=AnalysisScope.GROUP,
    )

Each call returns ``AnalysisOutput`` (or a dict of them for groups), which bundles the ``VisualizationOutput`` objects produced by each registered provider.

The Benchmarking Layer
----------------------

The three layers above handle a single model on a single target. Real-world model selection requires comparing multiple forecasting approaches across many different targets — different equipment types, consumption vs. prosumption profiles, solar and wind parks, geographic regions, and seasons. ``BenchmarkPipeline`` automates this entire process.

``BenchmarkPipeline`` is generic over a target type ``T`` (a subclass of ``BenchmarkTarget``) and a forecaster type ``F``. It wires together all four stages and adds:

- A **``TargetProvider``** that supplies the set of targets to evaluate. ``SimpleTargetProvider`` covers common cases; you can implement ``TargetProvider`` for custom data sources.
- A **``ForecasterFactory``** — a callable ``(BenchmarkContext, T) -> BacktestForecasterMixin`` that creates a target-specific forecaster. The factory pattern lets you customise model configuration per target without coupling the pipeline to any particular model class.
- A **``BenchmarkStorage``** backend (``LocalBenchmarkStorage``, ``S3BenchmarkStorage``, or ``InMemoryBenchmarkStorage``) for persisting results.
- Optional **``BenchmarkCallback``** hooks for progress reporting, alerting, or custom side-effects at each stage.

.. code-block:: python

    from openstef_beam.benchmarking import (
        BenchmarkPipeline,
        BenchmarkContext,
        LocalBenchmarkStorage,
        SimpleTargetProvider,
    )

    pipeline = BenchmarkPipeline(
        backtest_config=backtest_config,
        evaluation_config=eval_config,
        analysis_config=analysis_config,
        target_provider=SimpleTargetProvider(targets=my_targets),
        storage=LocalBenchmarkStorage(path="./benchmark_results"),
    )

    def create_forecaster(context: BenchmarkContext, target: MyTarget):
        # Customise the model per target — e.g., use target metadata
        # to select features or hyperparameters.
        return MyForecaster(config=target.get_model_config())

    pipeline.run(
        forecaster_factory=create_forecaster,
        run_name="baseline_v1",
        n_processes=4,
    )

When you need to compare the *outputs* of two or more completed benchmark runs — for example, to decide whether a new model architecture beats the current baseline — ``BenchmarkComparisonPipeline`` reads the stored ``EvaluationReport`` objects from each run and feeds them through the analysis layer together, producing side-by-side visualisations. The ``read_evaluation_reports`` helper function loads persisted reports from any supported storage backend.

.. code-block:: python

    from openstef_beam.benchmarking import (
        BenchmarkComparisonPipeline,
        read_evaluation_reports,
        LocalBenchmarkStorage,
    )

    storage = LocalBenchmarkStorage(path="./benchmark_results")

    baseline_reports = read_evaluation_reports(storage, run_name="baseline_v1")
    candidate_reports = read_evaluation_reports(storage, run_name="candidate_v2")

    comparison = BenchmarkComparisonPipeline(analysis_config=analysis_config)
    comparison.run(
        report_sets={"baseline": baseline_reports, "candidate": candidate_reports}
    )

Error Handling and Callbacks
----------------------------

By default, ``BenchmarkPipeline`` is tolerant of individual target failures — if one target's backtest raises an exception, the pipeline logs the error and continues with the remaining targets. For stricter workflows (e.g., CI pipelines where any failure should abort the run), register a ``StrictExecutionCallback``:

.. code-block:: python

    from openstef_beam.benchmarking import StrictExecutionCallback

    pipeline = BenchmarkPipeline(
        ...,
        callbacks=[StrictExecutionCallback()],
    )

Custom callbacks implement the ``BenchmarkCallback`` interface and can react to events at the start and end of each target's evaluation, making them useful for progress bars, external monitoring systems, or writing intermediate results.

Package Dependencies
--------------------

BEAM sits at the top of the OpenSTEF dependency graph. It depends on both sibling packages:

- **openstef_core** — for ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, ``BaseConfig``, and general utilities. The versioned dataset abstraction is what makes honest temporal validation possible. See :doc:`core` for details.
- **openstef_models** — for the ``BacktestForecasterMixin`` and ``BacktestBatchForecasterMixin`` interfaces that forecasters must implement to be compatible with ``BacktestPipeline``. See :doc:`models` for the transforms and model structure that underpin those interfaces.

Neither ``openstef_core`` nor ``openstef_models`` depends on ``openstef_beam``. This one-way dependency means you can use the core dataset abstractions or the model transforms independently, without pulling in the full evaluation framework.

.. note::

   BEAM is designed for *offline* evaluation, not real-time inference. Its pipelines are batch-oriented and may run for minutes to hours depending on the number of targets, the length of the historical period, and the retraining cadence. Use ``n_processes`` in ``BenchmarkPipeline.run()`` to parallelise across targets when running on multi-core hardware.