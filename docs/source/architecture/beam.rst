The OpenSTEF BEAM Package
=========================

The ``openstef_beam`` package provides a structured framework for **Backtesting, Evaluation, Analysis, and Metrics** — the four pillars that give BEAM its name. Where ``openstef_core`` and ``openstef_models`` are concerned with *producing* forecasts, BEAM is concerned with *judging* them: running models against historical data under realistic conditions, scoring the results with standardised metrics, and surfacing findings through analysis and comparison reports.

This page covers the design of the BEAM package, how its internal stages connect, and how to integrate your own forecasters and data sources into the workflow.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

Package Dependencies
--------------------

BEAM sits at the top of the OpenSTEF dependency graph. It imports from both sibling packages:

- **openstef_core** — ``TimeSeriesDataset`` and ``RestrictedHorizonVersionedTimeSeries`` are the data containers that flow through every stage. See the :doc:`core` page for details on these types.
- **openstef_models** — model classes that implement ``BacktestForecasterMixin`` (e.g. GBLinear) are registered as forecaster factories inside a benchmark runner. See the :doc:`models` page for the transforms and model internals.

Neither ``openstef_core`` nor ``openstef_models`` depends on BEAM, so you can use them independently. BEAM is the integration layer that wires everything together into a reproducible experiment.

The Four Stages
---------------

Backtesting
^^^^^^^^^^^

The backtesting stage replays historical data chronologically, calling ``fit`` and ``predict`` on your forecaster at each step. The key guarantee is **no data leakage**: the ``RestrictedHorizonVersionedTimeSeries`` object passed to both methods exposes only data that was available at the simulated point in time. You retrieve slices with ``data.get_window(start, end, available_before)``, and the object refuses to return anything beyond ``data.horizon``.

Any forecaster that implements ``BacktestForecasterMixin`` can participate in a backtest:

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.backtesting.backtest_forecaster.mixins import (
        BacktestForecasterMixin,
        BacktestForecasterConfig,
    )
    from openstef_core.data_classes.time_series import TimeSeriesDataset, Quantile as Q
    from openstef_core.versioned_time_series import RestrictedHorizonVersionedTimeSeries


    class MedianForecaster(BacktestForecasterMixin):
        """Baseline: predict the rolling median of recent load."""

        def __init__(self):
            self.config = BacktestForecasterConfig(
                requires_training=False,
                predict_length=timedelta(days=7),
                predict_min_length=timedelta(days=0),
                predict_context_length=timedelta(days=14),
                predict_context_min_coverage=0.5,
                training_context_length=timedelta(days=0),
                training_context_min_coverage=0.0,
                predict_sample_interval=timedelta(minutes=15),
            )
            self._quantiles = [Q(0.05), Q(0.50), Q(0.95)]

        @property
        def quantiles(self):
            return self._quantiles

        def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
            # This baseline needs no training step.
            pass

        def predict(
            self, data: RestrictedHorizonVersionedTimeSeries
        ) -> TimeSeriesDataset | None:
            window = data.get_window(
                data.horizon - timedelta(days=14),
                data.horizon,
                available_before=data.horizon,
            )
            if window is None or window.empty:
                return None

            median = window["load"].median()
            future_index = data.get_future_index()
            result = TimeSeriesDataset(index=future_index)
            result["load"] = median
            result["quantile_P05"] = median * 0.8
            result["quantile_P50"] = median
            result["quantile_P95"] = median * 1.2
            return result

The ``BacktestForecasterConfig`` controls how much historical context the framework provides to each call and how frequently predictions are requested. Models that can process multiple prediction windows simultaneously should implement ``BacktestBatchForecasterMixin`` instead, which adds a ``predict_batch`` method for GPU-friendly bulk inference.

Predictions are written to ``benchmark_results/<RunName>/backtest/<group>/<target>/predictions.parquet`` in a versioned format that records both the prediction timestamp and the ``available_at`` time at which the forecast was generated.

Evaluation
^^^^^^^^^^

The evaluation stage reads the prediction parquets produced by backtesting and scores them. It is driven by ``EvaluationPipeline`` and configured through ``EvaluationConfig``, which specifies:

- **Windows** — time slices over which metrics are aggregated (e.g. full period, individual weeks, seasonal splits).
- **Filterings** — conditional subsets such as peak hours, weekdays, or high-load events.
- **SubsetMetrics** — which metric functions to apply to each window/filtering combination.

The ``metric_providers`` module supplies the built-in metric implementations. Results are collected into ``EvaluationReport`` and ``EvaluationSubsetReport`` objects, which carry the raw numerical scores without any visualisation logic. This clean separation means you can consume evaluation reports programmatically — for example, to feed scores into a CI gate — without ever rendering a plot.

.. code-block:: python

    from openstef_beam.evaluation import (
        EvaluationConfig,
        EvaluationPipeline,
        Window,
        Filtering,
        SubsetMetric,
        metric_providers,
    )

    eval_config = EvaluationConfig(
        windows=[Window.FULL, Window.WEEKLY],
        filterings=[Filtering.ALL, Filtering.PEAK_HOURS],
        metrics=[
            SubsetMetric(name="MAE", provider=metric_providers.mae),
            SubsetMetric(name="PINBALL", provider=metric_providers.pinball_loss),
        ],
    )

    pipeline = EvaluationPipeline(config=eval_config)
    report = pipeline.run(predictions_path="benchmark_results/MyModel/backtest/solar_park/target_A")

Analysis
^^^^^^^^

The analysis stage transforms ``EvaluationReport`` objects into interactive HTML visualisations. ``AnalysisPipeline`` accepts an ``AnalysisConfig`` that specifies the ``AnalysisScope`` — whether to produce plots at the global level (all targets aggregated), the group level (per asset category), or the individual target level. The ``AnalysisAggregation`` setting controls how scores from multiple targets are combined.

Because analysis operates on already-computed reports, it is cheap to re-run with different scopes or styling without touching the backtesting or evaluation stages.

Benchmarking and Comparison
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``benchmarking`` sub-package ties the three stages above into a single runnable pipeline and adds multi-run comparison. The central entry point is a benchmark runner that you assemble by providing:

1. A **TargetProvider** — tells the pipeline where to find measurement and weather data for each asset.
2. One or more **forecaster factories** — callables that return a fresh ``BacktestForecasterMixin`` instance for each target.
3. An ``EvaluationConfig`` and ``AnalysisConfig``.

``BenchmarkComparisonPipeline`` then operates on the *outputs* of multiple completed runs, automatically detecting which targets are present in all runs and generating side-by-side comparison plots at global, group, and target scope.

Running a Benchmark
-------------------

The fastest way to get started is the built-in **Liander 2024** dataset, which downloads automatically from HuggingFace:

.. code-block:: python

    from openstef_beam.benchmarking import create_liander2024_benchmark_runner

    runner = create_liander2024_benchmark_runner()

    # Register your forecaster alongside the built-in GBLinear baseline
    runner.register_forecaster("MedianBaseline", lambda: MedianForecaster())

    # Run backtesting → evaluation → analysis for all registered forecasters
    runner.pipeline.run(categories=["solar_park"])

Results land in ``./benchmark_results/``. Each registered forecaster gets its own subdirectory containing prediction parquets, evaluation score files, and analysis HTML plots.

Alternatively, run the provided example scripts directly:

.. code-block:: bash

    # Liander 2024 dataset — downloads automatically
    uv run python -m examples.benchmarks.custom_benchmark.run_liander2024_benchmark

    # Compare two or more completed runs
    uv run python -m examples.benchmarks.custom_benchmark.compare_liander2024_results

Evaluating Pre-existing Forecasts
----------------------------------

If you already have predictions from an external system or a previous experiment, you can skip the backtesting stage entirely and feed BEAM only the evaluation and analysis stages. Place your parquets in the expected layout:

.. code-block:: text

    benchmark_results/MyForecasts/
    └── backtest/
        └── <group_name>/
            └── <target_name>/
                └── predictions.parquet

Each parquet must contain a ``DatetimeIndex`` named ``timestamp``, an ``available_at`` column recording when the forecast was generated, and one column per quantile named with the ``quantile_PXX`` convention (e.g. ``quantile_P05``, ``quantile_P50``, ``quantile_P95``). The ``available_at`` column is what enables lead-time filtering during evaluation — without it, D-1 vs. D-2 accuracy comparisons are not possible.

.. note::

   The ``available_at`` timestamp is distinct from the prediction ``timestamp``. A forecast generated on 14 January for 15 January 12:00 would have ``available_at = 2023-01-14 06:00:00`` and ``timestamp = 2023-01-15 12:00:00``.

Custom Data Sources
-------------------

To benchmark against your own data, subclass ``SimpleTargetProvider`` and override two methods:

.. code-block:: python

    from openstef_beam.benchmarking.target_provider import SimpleTargetProvider
    from openstef_beam.benchmarking.models import BenchmarkTarget
    from pathlib import Path


    class MyGridTargetProvider(SimpleTargetProvider):
        """Serves measurement and weather data from a local data lake."""

        def _get_measurements_path_for_target(self, target: BenchmarkTarget) -> Path:
            return Path(f"/data/measurements/{target.group_name}/{target.name}.parquet")

        def _get_weather_path_for_target(self, target: BenchmarkTarget) -> Path:
            return Path(f"/data/weather/{target.group_name}/{target.name}.parquet")

The ``BenchmarkTarget`` objects themselves are typically declared in a YAML file that lists asset names, group memberships, and any target-specific metadata. The target provider's ``get_targets(categories)`` method reads this file and returns the filtered list.

.. note::

   Thread count should be capped when running multiple parallel backtests alongside XGBoost-based models, as XGBoost manages its own internal thread pool. Set ``OMP_NUM_THREADS=1`` and ``OPENBLAS_NUM_THREADS=1`` in your environment before launching a benchmark run to avoid contention.

Output Structure
----------------

A completed benchmark run produces the following directory tree:

.. code-block:: text

    benchmark_results/
    └── <RunName>/
        ├── backtest/
        │   └── <group>/<target>/predictions.parquet
        ├── evaluation/
        │   └── <group>/<target>/evaluation_report.json
        └── analysis/
            └── <group>/<target>/analysis.html

Comparison runs write their output to a separate root:

.. code-block:: text

    benchmark_results_comparison/
    ├── global_comparison.html
    ├── <group>_comparison.html
    └── <group>/<target>_comparison.html

Related Pages
-------------

- :doc:`core` — ``TimeSeriesDataset`` and ``RestrictedHorizonVersionedTimeSeries``, the data containers that flow through every BEAM stage.
- :doc:`models` — model classes and transforms that implement ``BacktestForecasterMixin`` and can be registered as forecaster factories in a benchmark runner.