OpenSTEF BEAM: Backtesting, Evaluation, Analysis and Metrics
=============================================================

The ``openstef_beam`` package — BEAM standing for **Backtesting, Evaluation, Analysis and Metrics** — provides the complete toolchain for testing energy forecasting models under realistic conditions. Where the core and models packages handle data structures and model transforms respectively, BEAM sits above both of them to orchestrate end-to-end evaluation workflows: from replaying historical data through to generating comparison reports across multiple forecasting targets.

This page covers how BEAM is structured, how its four stages connect, and how to use the library's pipelines in your own evaluation code. For details on ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``, see the :doc:`core` page. For the transforms and model building blocks that your forecasters will use, see the :doc:`models` page.

.. mermaid:: diagrams/architecture/beam_diagram_1.mmd


Why Realistic Evaluation Matters
---------------------------------

A common pitfall in time-series model evaluation is inadvertently training or validating on data that would not have been available at prediction time — so-called data leakage. BEAM prevents this by building the concept of *versioned data* into the evaluation loop from the start. Rather than slicing a static DataFrame, the backtesting stage uses ``VersionedTimeSeriesDataset`` (from ``openstef_core``) to replay history: at each simulated prediction moment, the model can only see data that was genuinely available at that timestamp.

This means evaluation results from BEAM accurately reflect the performance you would observe in production, not an optimistic estimate inflated by future information.


Package Structure
-----------------

BEAM is organised into four sub-packages that correspond directly to the four stages of its workflow:

- **backtesting** — Simulates operational forecasting by replaying historical data with proper temporal constraints and periodic model retraining.
- **evaluation** — Computes performance metrics (such as RMAE and RCRPS) over the predictions produced by backtesting.
- **analysis** — Generates visualisations and comparative reports from evaluation results.
- **benchmarking** — Ties all three stages together and scales the workflow across multiple forecasting targets, with parallel execution and pluggable storage.

Each stage is independently usable as a library component, but they are designed to compose cleanly through the ``BenchmarkPipeline``.


Stage 1 — Backtesting
----------------------

The ``BacktestPipeline`` is the entry point for realistic model evaluation. It accepts a ``BacktestForecasterMixin``-implementing forecaster and a pair of ``VersionedTimeSeriesDataset`` objects (ground truth and predictors), then steps through time, generating forecasts and periodically retraining the model exactly as it would be retrained in production.

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        horizon=timedelta(hours=24),
        window_step=timedelta(days=1),
    )

    pipeline = BacktestPipeline(
        config=config,
        forecaster=my_forecaster,  # implements BacktestForecasterMixin
    )

    predictions = pipeline.run(
        ground_truth=versioned_ground_truth,
        predictors=versioned_predictors,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
        show_progress=True,
    )

``pipeline.run()`` returns a ``TimeSeriesDataset`` whose columns follow the quantile convention (``quantile_P10``, ``quantile_P50``, ``quantile_P90``, etc.), ready to be consumed by the evaluation stage.

Integrating Your Own Forecaster
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To plug a custom model into ``BacktestPipeline``, implement the ``BacktestForecasterMixin`` interface. The single required method is ``predict``, which receives a ``RestrictedHorizonVersionedTimeSeries`` — a thin wrapper that enforces the horizon constraint so your model cannot accidentally read future rows:

.. code-block:: python

    from openstef_beam.backtesting.backtest_forecaster.mixins import BacktestForecasterMixin
    from openstef_beam.backtesting.restricted_horizon_timeseries import (
        RestrictedHorizonVersionedTimeSeries,
    )
    from openstef_core.datasets import TimeSeriesDataset

    class MyForecaster(BacktestForecasterMixin):

        def predict(
            self, data: RestrictedHorizonVersionedTimeSeries
        ) -> TimeSeriesDataset | None:
            window = data.get_window(
                start=data.horizon - timedelta(days=14),
                end=data.horizon,
            )
            # Build and return quantile predictions from `window`
            ...

For models that benefit from batched inference (neural networks, GPU-accelerated models), implement ``BacktestBatchForecasterMixin`` instead, which adds a ``predict_batch_versioned`` method for processing multiple horizon windows in a single call.

.. note::

   ``RestrictedHorizonVersionedTimeSeries.get_window()`` accepts an optional
   ``available_before`` argument. If omitted, the horizon stored on the object
   is used automatically — you rarely need to set it explicitly.


Stage 2 — Evaluation
---------------------

Once backtesting has produced a set of predictions, the evaluation stage computes performance metrics. Metrics are provided through *metric providers*, small composable objects that encapsulate a single metric calculation. BEAM ships with built-in providers including ``RMAEProvider`` (Relative Mean Absolute Error) and ``RCRPSProvider`` (Relative Continuous Ranked Probability Score):

.. code-block:: python

    from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
    from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider

    evaluation_config = EvaluationConfig(
        metric_providers=[RMAEProvider(), RCRPSProvider()],
    )

    evaluation_pipeline = EvaluationPipeline(config=evaluation_config)
    report = evaluation_pipeline.run(
        predictions=predictions,
        ground_truth=ground_truth_dataset,
    )

The result is an ``EvaluationReport`` — a structured object that groups metric values by lead time, target, and any filtering criteria defined in the config. Reports are the currency passed between the evaluation and analysis stages.


Stage 3 — Analysis
-------------------

The analysis stage turns ``EvaluationReport`` objects into human-readable outputs. Like metrics, visualisations are provided through pluggable *visualization providers*. The ``AnalysisPipeline`` processes reports at two aggregation levels: per individual target (detailed breakdowns) and across multiple targets (comparative summaries).

.. code-block:: python

    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig
    from openstef_beam.analysis.visualizations import SummaryTableVisualization

    analysis_config = AnalysisConfig(
        visualization_providers=[
            SummaryTableVisualization(name="summary"),
        ]
    )

    analysis_pipeline = AnalysisPipeline(config=analysis_config)
    output = analysis_pipeline.run(reports=[report])

``AnalysisOutput`` objects carry the generated visualisations and can be persisted through the storage backend described in the next section.


Stage 4 — Benchmarking
-----------------------

``BenchmarkPipeline`` is the top-level orchestrator. It wires the three stages above into a single ``run()`` call, adds parallel execution across targets, and delegates persistence to a ``BenchmarkStorage`` backend. A ``ForecasterFactory`` callable lets you construct a different model configuration for each target:

.. code-block:: python

    from pathlib import Path
    from openstef_beam.benchmarking import BenchmarkPipeline
    from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage

    storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))

    pipeline = BenchmarkPipeline(
        backtest_config=backtest_config,
        evaluation_config=evaluation_config,
        analysis_config=analysis_config,
        target_provider=my_target_provider,
        storage=storage,
    )

    def create_forecaster(context, target):
        """Build a forecaster tailored to each target."""
        return MyForecaster(config=target.get_model_config())

    pipeline.run(
        forecaster_factory=create_forecaster,
        run_name="baseline_comparison",
        n_processes=4,
    )

After the run completes, results are stored under ``./benchmark_results`` and can be reloaded with ``read_evaluation_reports()`` for offline analysis.

Comparing Multiple Runs
^^^^^^^^^^^^^^^^^^^^^^^^

``BenchmarkComparisonPipeline`` extends the benchmarking workflow to compare results from two or more named runs — useful for A/B testing a new model architecture against an established baseline:

.. code-block:: python

    from openstef_beam.benchmarking import BenchmarkComparisonPipeline

    comparison = BenchmarkComparisonPipeline(
        storage=storage,
        analysis_config=analysis_config,
    )
    comparison.run(run_names=["baseline_comparison", "new_model_v2"])

The callback system (``BenchmarkCallback``, ``BenchmarkCallbackManager``) provides hooks into each stage of the benchmark loop, enabling custom logging, early stopping, or result streaming without modifying the pipeline internals.

Built-in Benchmarks
^^^^^^^^^^^^^^^^^^^^

BEAM ships with pre-configured benchmark scenarios under ``openstef_beam.benchmarking.benchmarks``. The ``create_liander2024_benchmark_runner`` factory, for example, sets up the benchmark configuration used in the Liander 2024 study and serves as a concrete reference for structuring your own benchmark definitions.

.. code-block:: python

    from openstef_beam.benchmarking.benchmarks import create_liander2024_benchmark_runner

    runner = create_liander2024_benchmark_runner(
        data_path=Path("./data"),
        output_path=Path("./results"),
    )
    runner.run()


Dependency Relationships
-------------------------

BEAM deliberately sits at the top of the OpenSTEF package hierarchy:

- It **imports from** ``openstef_core`` for ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and ``BaseConfig``.
- It **imports from** ``openstef_models`` for the transform primitives (such as ``HorizonTransform``) that forecasters use internally.
- Neither ``openstef_core`` nor ``openstef_models`` imports from ``openstef_beam``, keeping the dependency graph acyclic.

This means you can use the core and models packages independently for training and inference, and only bring in BEAM when you need structured evaluation. Conversely, BEAM's pipelines are designed to accept any forecaster that implements the mixin interfaces — you are not required to use ``openstef_models`` transforms inside your forecaster, though they are the natural choice.

.. note::

   Storage backends are fully pluggable. ``LocalBenchmarkStorage`` writes to the
   local filesystem; cloud-backed implementations can be substituted without
   changing any pipeline code, as long as they satisfy the ``BenchmarkStorage``
   interface.


Related Pages
--------------

- :doc:`core` — ``TimeSeriesDataset`` and ``VersionedTimeSeriesDataset``, the data structures that BEAM's backtesting layer depends on.
- :doc:`models` — The transforms module and model building blocks used inside forecasters that integrate with BEAM.