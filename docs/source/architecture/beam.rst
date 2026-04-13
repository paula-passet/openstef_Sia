OpenSTEF BEAM: Backtesting, Evaluation, Analysis, and Metrics
=============================================================

The ``openstef_beam`` package — **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics — provides the complete toolkit for assessing how well energy forecasting models perform under realistic conditions. Where ``openstef_core`` supplies the foundational data structures and ``openstef_models`` provides the model transforms (see the sibling pages for those packages), BEAM sits at the top of the dependency stack and orchestrates end-to-end evaluation workflows: from simulating production-like forecasting runs, through computing performance metrics, to generating comparison reports across multiple forecasting targets.

This page covers the internal architecture of ``openstef_beam``, the design principles that make its backtesting trustworthy, and how to compose its components into evaluation and benchmarking pipelines.

.. note:: [DIAGRAM: Component-level diagram showing the BEAM workflow. Four horizontal stages connected by arrows: (1) Backtesting — BacktestPipeline drives BacktestEventGenerator to produce BacktestEvents, each backed by a RestrictedHorizonVersionedTimeSeries that wraps openstef_core's VersionedTimeSeriesDataset; (2) Evaluation — EvaluationPipeline consumes backtest output and applies metric providers (RMAEProvider, RCRPSProvider, …) to produce EvaluationReports; (3) Analysis — AnalysisConfig selects VisualizationProviders that render EvaluationReports into tables and plots; (4) Benchmarking — BenchmarkPipeline and BenchmarkComparisonPipeline coordinate all three prior stages across multiple targets and models, writing results through a pluggable BenchmarkStorage backend. Vertical dependency arrows show openstef_beam depending on openstef_core (datasets, base model) and openstef_models (forecaster implementations).]


Why BEAM Exists
---------------

Simple train/test splits are not sufficient for energy forecasting. In production, a model is retrained on a rolling basis and must predict future load or generation using only data that was *available at the time the prediction was made*. Naive evaluation ignores this constraint and produces optimistic metrics that do not survive contact with reality.

BEAM enforces temporal honesty throughout. Every evaluation run uses ``VersionedTimeSeriesDataset`` from ``openstef_core`` to track *when* each data point became available. The ``RestrictedHorizonVersionedTimeSeries`` wrapper then gates access so that a model operating at time *t* can only observe data with an ``available_at`` timestamp no later than *t*. This single design decision eliminates data leakage at the infrastructure level rather than relying on the model author to be careful.


Package Structure
-----------------

``openstef_beam`` is organised into four sub-packages that map directly onto the workflow stages:

- ``openstef_beam.backtesting`` — simulates the operational forecasting loop
- ``openstef_beam.evaluation`` — computes performance metrics from backtest output
- ``openstef_beam.analysis`` — turns evaluation reports into visualisations and tables
- ``openstef_beam.benchmarking`` — coordinates all three stages across many targets and models

Each stage is independently usable. You can run a backtest and inspect the raw predictions without ever invoking the evaluation layer, or feed pre-existing predictions into the evaluation layer if you already have them from another source.


Backtesting
-----------

The backtesting sub-package simulates how a forecaster would behave if it were deployed in production. It replays historical data in chronological order, triggering prediction events and periodic retraining events at the same cadence the model would experience in live operation.

The central class is ``BacktestPipeline``. It accepts a ``BacktestConfig`` (which specifies the prediction horizon, the sample interval, and the retraining schedule) and a forecaster object that implements either ``BacktestForecasterMixin`` (for single-prediction models) or ``BacktestBatchForecasterMixin`` (for models that predict multiple horizons in one call).

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        horizon=timedelta(hours=48),
        window_step=timedelta(hours=1),
        retrain_interval=timedelta(days=1),
    )

    # forecaster must implement BacktestForecasterMixin
    pipeline = BacktestPipeline(
        config=config,
        forecaster=my_forecaster,
    )

    backtest_result = pipeline.run(
        dataset=versioned_dataset,  # VersionedTimeSeriesDataset from openstef_core
        start=start_dt,
        end=end_dt,
    )

Internally, ``BacktestPipeline`` delegates event scheduling to ``BacktestEventGenerator``, which produces a stream of ``BacktestEvent`` objects. Each event carries a ``RestrictedHorizonVersionedTimeSeries`` — a thin wrapper around ``VersionedTimeSeriesDataset`` that hard-limits the visible data horizon to the event timestamp. The forecaster never touches a ``VersionedTimeSeriesDataset`` directly; it always receives a horizon-restricted view.

.. note::

   ``BacktestConfig`` is a Pydantic model that inherits from ``openstef_core.base_model.BaseConfig``.
   All configuration objects across BEAM follow this pattern, giving you free validation,
   serialisation to JSON, and environment-variable overrides.


Evaluation
----------

Once a backtest has produced predictions, the evaluation sub-package computes how accurate those predictions were. Metrics are provided through a plugin interface: any class that implements the metric provider protocol can be registered with ``EvaluationConfig``.

BEAM ships two built-in providers:

- ``RMAEProvider`` — Relative Mean Absolute Error, the standard skill metric for load forecasting
- ``RCRPSProvider`` — Relative Continuous Ranked Probability Score, for probabilistic forecasts

.. code-block:: python

    from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
    from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider

    evaluation_config = EvaluationConfig(
        metric_providers=[
            RMAEProvider(),
            RCRPSProvider(),
        ]
    )

    evaluation_pipeline = EvaluationPipeline(config=evaluation_config)
    report = evaluation_pipeline.run(backtest_result)

The resulting ``EvaluationReport`` contains per-lead-time metric breakdowns, making it straightforward to see whether a model degrades gracefully as the forecast horizon extends.


Analysis
--------

The analysis sub-package transforms ``EvaluationReport`` objects into human-readable output. Visualisation providers are registered through ``AnalysisConfig`` in the same plugin pattern used by the evaluation layer.

The built-in ``SummaryTableVisualization`` renders a concise comparison table suitable for inclusion in automated reports. Custom providers can produce matplotlib figures, HTML dashboards, or any other output format by implementing the visualisation provider interface.

.. code-block:: python

    from openstef_beam.analysis import AnalysisConfig, AnalysisPipeline
    from openstef_beam.analysis.visualizations import SummaryTableVisualization

    analysis_config = AnalysisConfig(
        visualization_providers=[
            SummaryTableVisualization(name="summary"),
        ]
    )

    analysis_pipeline = AnalysisPipeline(config=analysis_config)
    analysis_pipeline.run(report)


Benchmarking
------------

The benchmarking sub-package is the highest-level entry point in BEAM. It coordinates backtesting, evaluation, and analysis across many forecasting targets and multiple model variants, then persists the results through a pluggable storage backend.

``BenchmarkPipeline`` handles a single model type evaluated across all targets supplied by a ``TargetProvider``. ``BenchmarkComparisonPipeline`` extends this to compare several model types head-to-head, producing side-by-side metric tables.

.. code-block:: python

    from pathlib import Path
    from datetime import timedelta
    from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkContext
    from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
    from openstef_beam.backtesting import BacktestConfig
    from openstef_beam.evaluation import EvaluationConfig
    from openstef_beam.evaluation.metric_providers import RMAEProvider
    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import SummaryTableVisualization

    storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))

    pipeline = BenchmarkPipeline(
        backtest_config=BacktestConfig(
            horizon=timedelta(hours=24),
            window_step=timedelta(days=1),
        ),
        evaluation_config=EvaluationConfig(
            metric_providers=[RMAEProvider()]
        ),
        analysis_config=AnalysisConfig(
            visualization_providers=[SummaryTableVisualization(name="summary")]
        ),
        target_provider=my_target_provider,
        storage=storage,
    )

    # Run across all targets, using 4 parallel worker processes
    pipeline.run(
        forecaster_factory=lambda ctx, target: MyForecaster(target.get_model_config()),
        run_name="baseline_v1",
        n_processes=4,
    )

The ``forecaster_factory`` callable receives a ``BenchmarkContext`` and the current target, letting you customise model hyperparameters per target without duplicating pipeline logic.

Storage backends are swappable: ``LocalBenchmarkStorage`` writes Parquet files and JSON reports to disk; cloud-backed implementations follow the same ``BenchmarkStorage`` interface. Previously saved runs can be reloaded with ``read_evaluation_reports`` for post-hoc analysis without re-running the full benchmark.

A callback system (``BenchmarkCallback``, ``BenchmarkCallbackManager``) lets you hook into lifecycle events — for example, to stream progress to a monitoring dashboard or to trigger alerts when a metric threshold is breached.

The ``benchmarking.benchmarks`` sub-module ships a reference benchmark, ``create_liander2024_benchmark_runner``, which reproduces the evaluation methodology from the Liander 2024 study. This serves both as a reproducibility artefact and as a concrete example of how to assemble a full benchmark configuration.


Dependency Relationships
------------------------

BEAM deliberately sits above the other OpenSTEF packages in the dependency graph:

- **openstef_core** supplies ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, ``BaseConfig``, and the validated dataset types (``ForecastDataset``, ``ForecastInputDataset``, etc.). BEAM imports these directly and does not reimplement them.
- **openstef_models** provides the transform pipeline and concrete forecaster implementations. BEAM's ``BacktestForecasterMixin`` defines the interface that those models must satisfy to participate in a backtest.
- **openstef_beam** itself adds no forecasting logic. It is purely an evaluation harness.

This separation means you can upgrade the model layer independently of the evaluation layer, and you can evaluate third-party models that have nothing to do with ``openstef_models`` as long as they implement the mixin interface.

.. note::

   The core data structures used throughout BEAM — ``TimeSeriesDataset`` and
   ``VersionedTimeSeriesDataset`` — are documented on the **core** sibling page.
   The transform pipeline that most ``openstef_models`` forecasters rely on is
   covered on the **models** sibling page.


Summary
-------

``openstef_beam`` provides a complete, leakage-free evaluation framework for energy forecasting models. Its four-stage pipeline — backtesting, evaluation, analysis, benchmarking — can be used end-to-end or stage-by-stage. The versioned dataset mechanism inherited from ``openstef_core`` is the foundation that makes the results trustworthy, and the plugin interfaces for metrics, visualisations, storage, and callbacks make the framework adaptable to a wide range of evaluation scenarios without modifying library internals.