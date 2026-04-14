The OpenSTEF BEAM Package
=========================

The ``openstef_beam`` package — **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics — provides a complete framework for assessing energy forecasting model performance under realistic conditions. Where ``openstef_core`` supplies the data primitives and ``openstef_models`` supplies the model transforms (see the sibling pages for those topics), BEAM answers the question: *how well does a model actually perform when deployed?*

This page covers the four sub-systems that make up BEAM, how they connect into a single orchestrated workflow, and how to use the library's APIs to run evaluations ranging from a single backtest to a full multi-target benchmark study.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

Why BEAM Exists
---------------

Standard train/test splits are misleading for time-series forecasting: a model trained on data from 2023 and tested on a held-out slice of 2023 has implicitly seen the statistical distribution of the entire year. In real operations, a model trained on Monday's data must forecast Tuesday without any knowledge of Tuesday's actuals.

BEAM enforces this constraint through *versioned data*. The ``VersionedTimeSeriesDataset`` (from ``openstef_core``) records not just what the measurement was, but when it became available. The backtesting engine replays history by presenting the model only with data that would have existed at each prediction timestamp, preventing any form of data leakage.

Backtesting
-----------

The ``openstef_beam.backtesting`` sub-package is the entry point for all evaluation work. Its central class, ``BacktestPipeline``, simulates the operational forecasting loop: predict on a schedule, retrain periodically, never peek at the future.

.. code-block:: python

    from datetime import datetime
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=60,   # minutes between forecast runs
        training_interval_days=7,        # retrain every 7 days
        horizon_hours=48,                # forecast 48 hours ahead
    )

    pipeline = BacktestPipeline(
        config=config,
        forecaster=my_forecaster,        # implements BacktestForecasterMixin
    )

    predictions = pipeline.run(
        dataset=versioned_dataset,       # VersionedTimeSeriesDataset from openstef_core
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
    )

The ``forecaster`` argument must implement ``BacktestForecasterMixin`` (or ``BacktestBatchForecasterMixin`` for vectorised prediction). These mixins define the interface contract — ``train``, ``predict``, and ``prediction_sample_interval`` — so any model from ``openstef_models``, or a custom implementation, can be plugged in without modifying the pipeline.

Internally, the pipeline uses ``BacktestEventGenerator`` to produce a stream of ``BacktestEvent`` objects, each representing a single prediction or retraining moment. A ``RestrictedHorizonVersionedTimeSeries`` wraps the dataset at each event, enforcing the temporal horizon so the forecaster cannot accidentally access future rows.

Evaluation
----------

After backtesting produces a DataFrame of predictions alongside actuals, the ``openstef_beam.evaluation`` sub-package organises those results into structured performance reports. ``EvaluationPipeline`` segments the data across three orthogonal dimensions:

- **Lead times** — how does accuracy degrade from a 1-hour to a 48-hour horizon?
- **Time windows** — are there systematic differences between weekdays, weekends, or seasons?
- **Filters** — focus on specific conditions such as peak-demand hours or high-renewable periods.

.. code-block:: python

    from openstef_beam.evaluation import (
        EvaluationConfig,
        EvaluationPipeline,
        Window,
        Filtering,
    )

    eval_config = EvaluationConfig(
        lead_times=[1, 4, 12, 24, 48],          # hours ahead to evaluate
        windows=[Window.DAILY, Window.WEEKLY],
        filterings=[Filtering.PEAK_HOURS],
    )

    eval_pipeline = EvaluationPipeline(config=eval_config)
    report = eval_pipeline.run(predictions=predictions)

The output is an ``EvaluationReport`` containing ``EvaluationSubsetReport`` objects — one per combination of lead time, window, and filter. Each subset report holds a collection of ``SubsetMetric`` values computed by pluggable *metric providers* from ``openstef_beam.evaluation.metric_providers``. The library ships with standard energy-forecasting metrics (MAE, RMSE, skill scores), and you can register custom providers by implementing the ``MetricProvider`` protocol.

Analysis
--------

Raw metric numbers are useful for automated comparison, but human decision-making benefits from visualisation. The ``openstef_beam.analysis`` sub-package converts ``EvaluationReport`` objects into charts and summary tables through ``AnalysisPipeline``.

.. code-block:: python

    from openstef_beam.analysis import AnalysisConfig, AnalysisPipeline

    analysis_config = AnalysisConfig(
        visualization_providers=[
            LeadTimeAccuracyProvider(),   # accuracy vs. lead time curve
            SeasonalHeatmapProvider(),    # metric heatmap by week/hour
        ]
    )

    analysis_pipeline = AnalysisPipeline(config=analysis_config)

    # For a single target
    output = analysis_pipeline.run_for_reports(
        reports=[(target_metadata, report)],
        scope=AnalysisScope.SINGLE,
    )

The pipeline operates at two aggregation levels. ``run_for_reports`` handles individual targets, producing detailed per-target visualisations. ``run_for_groups`` handles collections of targets, producing comparative views — for example, overlaying accuracy curves for solar, wind, and load forecasters on the same axes.

``VisualizationProvider`` is the extension point: implement the protocol to add domain-specific plots without modifying the pipeline itself.

Benchmarking
------------

``BenchmarkPipeline`` is the top-level orchestrator that wires backtesting, evaluation, and analysis into a single repeatable study across many forecasting targets. It is the right starting point when you need to compare multiple model architectures or evaluate a model across a diverse portfolio of energy assets.

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

    def create_forecaster(context: BenchmarkContext, target):
        # Customise model per target — e.g. different feature sets for solar vs. load
        return MyForecaster(config=target.get_model_config())

    pipeline.run(
        forecaster_factory=create_forecaster,
        run_name="v2_vs_v3_comparison",
        n_processes=4,
    )

The ``ForecasterFactory`` pattern (``Callable[[BenchmarkContext, T], BacktestForecasterMixin]``) is the key integration point between BEAM and ``openstef_models``. The factory receives a ``BenchmarkContext`` — containing the run name and environment metadata — and a typed ``BenchmarkTarget``, giving it all the information needed to construct a target-specific forecaster.

Storage backends are swappable: ``InMemoryBenchmarkStorage`` is convenient for interactive exploration, ``LocalBenchmarkStorage`` persists results to disk, and ``S3BenchmarkStorage`` supports cloud workflows. All three implement the ``BenchmarkStorage`` protocol, so custom backends require only a handful of methods.

Callbacks and Lifecycle Hooks
------------------------------

``BenchmarkPipeline`` exposes a callback system for cross-cutting concerns such as logging, alerting, or early stopping. Register one or more ``BenchmarkCallback`` implementations when constructing the pipeline:

.. code-block:: python

    from openstef_beam.benchmarking import BenchmarkCallbackManager, StrictExecutionCallback

    pipeline = BenchmarkPipeline(
        ...,
        callbacks=[
            StrictExecutionCallback(),   # raises on any per-target failure
            MyLoggingCallback(),         # custom progress reporting
        ],
    )

``StrictExecutionCallback`` is the built-in implementation that converts per-target errors into hard failures — useful in CI pipelines where silent degradation is unacceptable.

Reading Saved Results
---------------------

Benchmark results stored by any ``BenchmarkStorage`` backend can be reloaded for post-hoc analysis without re-running the full pipeline:

.. code-block:: python

    from openstef_beam.benchmarking import read_evaluation_reports

    reports = read_evaluation_reports(storage=LocalBenchmarkStorage(path="./benchmark_results"))

    for target_metadata, report in reports:
        print(target_metadata.name, report.summary_metrics())

This makes it straightforward to compare runs across time — for example, tracking whether a model retrained on a new data vintage improves on the previous baseline.

Package Dependencies
--------------------

BEAM sits at the top of the OpenSTEF package hierarchy. It imports from both sibling packages:

- **openstef_core** — ``VersionedTimeSeriesDataset``, ``TimeSeriesDataset``, and ``BaseConfig`` are used throughout the backtesting and evaluation layers. See the :doc:`core` page for details on the dataset model.
- **openstef_models** — Forecaster implementations from ``openstef_models`` are the natural choice for the ``ForecasterFactory``, particularly when using the transforms module to build feature pipelines. See the :doc:`models` page for how transforms compose with model training.

Neither ``openstef_core`` nor ``openstef_models`` depends on ``openstef_beam``, so the evaluation framework can be updated or replaced independently of the modelling and data layers.

.. note::

   BEAM is a library, not a command-line application. There is no ``openstef-beam`` executable. All workflows are constructed programmatically, which means every configuration parameter is a typed Python object — discoverable through your IDE's autocomplete and validated by Pydantic at construction time.