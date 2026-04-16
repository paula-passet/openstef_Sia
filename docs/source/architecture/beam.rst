The OpenSTEF BEAM Package
=========================

The ``openstef_beam`` package implements the **Backtesting, Evaluation, Analysis, and Metrics** framework for OpenSTEF. Where the core and models packages focus on building and running forecasting models, BEAM focuses on *evaluating* them rigorously — simulating real-world deployment conditions, scoring predictions against ground truth, and producing reproducible comparison reports across many energy assets.

This page covers the internal architecture of BEAM: how its four phases connect, how it enforces temporal integrity, and how to plug your own models and data into the pipeline.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

Package Dependencies
--------------------

BEAM sits at the top of the OpenSTEF dependency graph. It imports from both sibling packages:

- **openstef_core** — ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and base configuration classes underpin every data exchange inside BEAM. See the :doc:`core` page for details on these types.
- **openstef_models** — The ``openstef_models.presets`` module provides ``ForecastingWorkflowConfig`` and related types that the built-in ``OpenSTEF4BacktestForecaster`` baseline uses. See the :doc:`models` page for the transforms and preset workflows.

Nothing in ``openstef_core`` or ``openstef_models`` imports from ``openstef_beam``, so BEAM is always a leaf dependency — you can add it to a project without affecting the rest of the stack.

Phase 1 — Backtesting
---------------------

The backtesting phase replays historical data as if the model were running in production. The central concern is **preventing data leakage**: a model evaluated on 2023 data must never see measurements that were only recorded after the prediction timestamp.

BEAM enforces this through ``RestrictedHorizonVersionedTimeSeries``, a wrapper around ``VersionedTimeSeriesDataset`` that gates every data access through a ``horizon`` attribute. Calling ``get_window(start, end, available_before=horizon)`` returns only the rows that were physically available before the horizon timestamp, even if the underlying dataset contains later revisions of the same measurements.

The ``BacktestEventGenerator`` walks forward through time, emitting a stream of ``BacktestEvent`` objects — each one carrying a horizon timestamp and the restricted view of the dataset. The ``BacktestPipeline`` consumes this stream, calling ``fit`` on a configurable retraining schedule and ``predict`` at every prediction interval (default: 15 minutes).

The ``BacktestConfig`` dataclass controls the two key timing parameters:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       # retrain_interval and other fields use sensible defaults
   )

The Forecaster Interface
^^^^^^^^^^^^^^^^^^^^^^^^

Any model can participate in backtesting by implementing ``BacktestForecasterMixin``. The interface is intentionally minimal — two methods and one property:

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterMixin,
       BacktestForecasterConfig,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Q


   class MedianForecaster(BacktestForecasterMixin):
       """Predict the rolling median of recent load — a simple baseline."""

       config: BacktestForecasterConfig = BacktestForecasterConfig()
       _recent_median: float = 0.0

       @property
       def quantiles(self) -> list[Q]:
           return [Q(0.05), Q(0.50), Q(0.95)]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           window = data.get_window(
               start=data.horizon - data.config.training_window,
               end=data.horizon,
               available_before=data.horizon,
           )
           self._recent_median = float(window["load"].median())

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset | None:
           index = data.prediction_index
           result = TimeSeriesDataset(index=index)
           result["load"] = self._recent_median
           result["quantile_P05"] = self._recent_median * 0.8
           result["quantile_P50"] = self._recent_median
           result["quantile_P95"] = self._recent_median * 1.2
           return result

``fit`` is called on the retraining schedule; ``predict`` is called at every prediction interval. Both receive the same ``RestrictedHorizonVersionedTimeSeries`` object, so neither can accidentally access future data.

.. note::

   ``DummyForecaster`` in ``openstef_beam.backtesting.backtest_forecaster`` is useful for
   testing pipeline wiring without a real model — it satisfies the interface but raises
   ``NotImplementedError`` on ``predict``.

Phase 2 — Evaluation
---------------------

After backtesting produces a parquet of predictions, the evaluation phase scores them against ground truth. Metrics are configurable: you supply a list of callable metrics, and BEAM applies each one across the full prediction horizon as well as broken down by lead time.

Lead-time analysis is a first-class feature. For operational energy systems, a 1-hour-ahead forecast and a 48-hour-ahead forecast have very different accuracy profiles and different operational uses. BEAM records the ``available_at`` timestamp alongside every prediction row, which makes it straightforward to slice results by lead time after the fact.

The evaluation phase produces an ``EvaluationReport`` — a structured object that carries per-target scores, per-lead-time scores, and the raw prediction/actuals alignment. This report is the input to the analysis phase.

Phase 3 — Analysis
------------------

The analysis phase turns ``EvaluationReport`` objects into human-readable output: interactive HTML plots of forecast vs. actuals, lead-time degradation curves, and metric summary tables. Visualisations are generated per target and written alongside the backtest predictions in the output directory.

You can extend the analysis phase with custom visualisations by subclassing the relevant analyser and registering it with the pipeline — the same plugin pattern used throughout BEAM.

Phase 4 — Benchmarking
-----------------------

The benchmarking layer orchestrates all three preceding phases across many targets and many models simultaneously. It is the entry point most users interact with directly.

``BenchmarkPipeline``
^^^^^^^^^^^^^^^^^^^^^

``BenchmarkPipeline`` (from ``openstef_beam.benchmarking``) takes a **target provider**, a dict of named **forecaster factories**, and a **storage backend**, then runs the full Backtesting → Evaluation → Analysis cycle for every (target, model) combination. Execution is parallelised across targets.

A *forecaster factory* is a callable that accepts a ``BenchmarkTarget`` and returns a configured ``BacktestForecasterMixin`` instance. This indirection lets BEAM instantiate a fresh model for each target without the caller managing object lifetimes.

.. code-block:: python

   import multiprocessing
   from pathlib import Path

   from openstef_beam.benchmarking import (
       BenchmarkTarget,
       LocalBenchmarkStorage,
   )
   from openstef_beam.benchmarking.benchmarks import create_liander2024_benchmark_runner

   # Use the built-in Liander 2024 dataset (auto-downloaded from HuggingFace)
   runner = create_liander2024_benchmark_runner()

   # Register a custom forecaster factory alongside the built-in baselines
   def my_forecaster_factory(target: BenchmarkTarget):
       return MedianForecaster()  # defined in the section above

   runner.register_forecaster("median_baseline", my_forecaster_factory)

   runner.pipeline.run(
       output=LocalBenchmarkStorage(Path("./benchmark_results/MedianBaseline")),
       n_processes=multiprocessing.cpu_count(),
   )

Results land in ``./benchmark_results/MedianBaseline/`` with one subdirectory per target, each containing ``predictions.parquet``, evaluation scores, and analysis plots.

Built-in Baselines
^^^^^^^^^^^^^^^^^^

The ``openstef_beam.benchmarking.baselines.openstef4`` module ships ``OpenSTEF4BacktestForecaster``, which wraps any ``ForecastingWorkflowConfig`` from ``openstef_models`` into the ``BacktestForecasterMixin`` interface. The convenience function ``create_openstef4_preset_backtest_forecaster`` returns a ready-made factory:

.. code-block:: python

   from openstef_beam.benchmarking.baselines.openstef4 import (
       create_openstef4_preset_backtest_forecaster,
   )
   from openstef_models.presets import ForecastingWorkflowConfig

   workflow_cfg = ForecastingWorkflowConfig(model_type="xgb")
   xgb_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=workflow_cfg,
       cache_dir=Path("./cache"),
   )

   runner.register_forecaster("xgb", xgb_factory)

Comparing Multiple Runs
^^^^^^^^^^^^^^^^^^^^^^^

``BenchmarkComparisonPipeline`` (from ``openstef_beam.benchmarking.benchmark_comparison_pipeline``) accepts a dict mapping run names to ``BenchmarkStorage`` instances and produces side-by-side comparison plots — global, per-group, and per-target. It auto-detects which targets are present in all runs, so partial results from failed targets do not block the comparison.

.. code-block:: python

   from openstef_beam.benchmarking import LocalBenchmarkStorage
   from openstef_beam.benchmarking.benchmark_comparison_pipeline import (
       BenchmarkComparisonPipeline,
   )

   run_data = {
       "median_baseline": LocalBenchmarkStorage(Path("./benchmark_results/MedianBaseline")),
       "xgb": LocalBenchmarkStorage(Path("./benchmark_results/XGB")),
   }

   comparison = BenchmarkComparisonPipeline()
   comparison.run(run_data=run_data)
   # HTML comparison plots are written to ./benchmark_results_comparison/

Evaluating Pre-existing Forecasts
----------------------------------

If you already have predictions from an external system, you can skip backtesting entirely and run only the evaluation and analysis phases. Place your forecast parquets in the expected layout:

.. code-block:: text

   benchmark_results/MyForecasts/
   └── backtest/
       └── <group_name>/
           └── <target_name>/
               └── predictions.parquet

Each parquet must contain a ``DatetimeIndex`` named ``timestamp``, an ``available_at`` column recording when each prediction was generated, and one column per quantile named with the ``Quantile(x).format()`` convention (e.g. ``quantile_P50``). Pass the storage path to ``LocalBenchmarkStorage`` and call the evaluation phase directly — the pipeline detects that backtest outputs already exist and skips re-running them.

.. note::

   The ``available_at`` column is what enables lead-time analysis. If your external system
   does not record generation timestamps, set all values to a fixed offset before the
   earliest ``timestamp`` to treat all predictions as same-horizon.

Relationship to Other Packages
-------------------------------

BEAM deliberately does not re-implement data loading or model training — it delegates those concerns to ``openstef_core`` and ``openstef_models`` respectively. The dependency boundary is clean:

- Data structures (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``) flow *into* BEAM from ``openstef_core``.
- Model configurations (``ForecastingWorkflowConfig``) flow *into* BEAM from ``openstef_models`` when using the built-in baselines.
- BEAM owns the temporal simulation logic, the metric computation, and the result storage format.

For ensemble models and advanced meta-learning approaches that can be plugged into BEAM as forecaster factories, see :doc:`meta`. For the ``TimeSeriesDataset`` and versioned data abstractions that underpin ``RestrictedHorizonVersionedTimeSeries``, see :doc:`core`.