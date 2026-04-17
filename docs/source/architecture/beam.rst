The openstef_beam Package
=========================

**BEAM** (Backtesting, Evaluation, Analysis, Metrics) is the ``openstef_beam`` package — a framework for
rigorously evaluating energy forecasting models under realistic, production-like conditions. This page
covers how BEAM's four pipelines compose into complete evaluation workflows, how to plug in any
forecasting model, and how the optional ``baselines`` extra adds ready-made benchmark forecasters.

.. note::

   BEAM's only mandatory dependency is ``openstef-core``. It is deliberately model-agnostic: any class
   that implements ``BacktestForecasterMixin`` works. The ``openstef-models`` and ``openstef-meta``
   packages are pulled in only when you install the ``baselines`` extra.

Installation
------------

Core BEAM with no predefined models:

.. code-block:: bash

   pip install openstef-beam

With the built-in benchmark forecasters (pulls in ``openstef-models`` and ``openstef-meta``):

.. code-block:: bash

   pip install "openstef-beam[baselines]"

The Four Pipelines
------------------

BEAM decomposes model evaluation into four focused stages, each represented by its own pipeline class.

.. note:: [DIAGRAM: Pipeline flow showing BacktestPipeline feeding predictions into EvaluationPipeline, which feeds EvaluationReport into AnalysisPipeline producing visualizations. BenchmarkPipeline sits above all three, orchestrating them in sequence across multiple models and multiple energy targets in parallel.]

**BacktestPipeline** replays historical data day by day. On each step it retrains the model using only
information that would have been available at that moment, then generates forecasts for the configured
horizon. This prevents data leakage that simple train/test splits cannot guard against.

**EvaluationPipeline** consumes the backtest predictions and computes metrics across configurable time
windows, lead times, and data subsets (e.g. weekdays only, peak hours). It produces structured
``EvaluationReport`` objects rather than raw numbers, making downstream comparison straightforward.

**AnalysisPipeline** turns evaluation reports into visualisations and summary tables. Visualisation
providers are pluggable, so you can add project-specific plots without touching the pipeline logic.

**BenchmarkPipeline** is the top-level orchestrator. It iterates over a set of targets and a set of
models, runs the three pipelines above for each combination, and persists results through a configurable
storage backend. Parallel execution is built in.

Plugging In Your Own Model
--------------------------

BEAM only requires that your forecaster implements ``BacktestForecasterMixin`` from
``openstef_beam.backtesting``. The interface is intentionally minimal:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterMixin,
       BacktestForecasterConfig,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile

   class MedianForecaster(BacktestForecasterMixin):
       """Predicts the rolling median of recent load — a simple but honest baseline."""

       @property
       def config(self) -> BacktestForecasterConfig:
           return BacktestForecasterConfig(
               retrain_interval=timedelta(days=1),
               horizon=timedelta(hours=48),
           )

       @property
       def quantiles(self) -> list[Quantile]:
           return [Quantile(0.05), Quantile(0.50), Quantile(0.95)]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           # data.get_window() only exposes history up to data.horizon — no lookahead
           window = data.get_window(
               start=data.horizon - timedelta(days=30),
               end=data.horizon,
               available_before=data.horizon,
           )
           self._median = float(window["load"].median())

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset:
           index = data.future_index
           return TimeSeriesDataset(
               {"load": self._median, "quantile_P50": self._median},
               index=index,
           )

The ``RestrictedHorizonVersionedTimeSeries`` wrapper enforces the no-lookahead contract at runtime:
any attempt to read data beyond the current horizon raises an error, making accidental leakage
impossible.

Running a Benchmark
-------------------

Once you have a forecaster, wire it into a ``BenchmarkPipeline``. The example below uses the built-in
Liander 2024 dataset so you can run it immediately without providing your own data.

.. code-block:: python

   from pathlib import Path
   from datetime import timedelta

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.backtesting import BacktestConfig
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage

   storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))

   backtest_config = BacktestConfig(
       horizon=timedelta(hours=48),
       window_step=timedelta(days=1),
   )

   evaluation_config = EvaluationConfig(
       metric_providers=[RMAEProvider(), RCRPSProvider()],
   )

   analysis_config = AnalysisConfig(
       visualization_providers=[SummaryTableVisualization(name="summary")],
   )

   pipeline = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       storage=storage,
       target_provider=...,   # see "Providing Targets" below
   )

   # Register one or more forecaster factories, then run
   pipeline.register_forecaster("median_baseline", lambda target: MedianForecaster())
   pipeline.run(categories=["solar_park"])

.. note:: [VISUALIZATION: Summary table output showing RMAE and RCRPS scores per model per target, with rows for each energy asset and columns for each registered forecaster, enabling direct side-by-side comparison.]

Providing Targets
-----------------

A *target provider* tells the pipeline where to find measurement and weather data for each energy
asset. For custom datasets, subclass ``SimpleTargetProvider`` and override two path methods:

.. code-block:: python

   from openstef_beam.benchmarking.target_providers import SimpleTargetProvider, BenchmarkTarget
   from pathlib import Path

   class MyTargetProvider(SimpleTargetProvider):
       def _get_measurements_path_for_target(self, target: BenchmarkTarget) -> Path:
           return Path(f"data/measurements/{target.name}.parquet")

       def _get_weather_path_for_target(self, target: BenchmarkTarget) -> Path:
           return Path(f"data/weather/{target.group_name}.parquet")

Targets are described in a YAML file that lists names, group names, and any metadata the forecaster
needs. The provider resolves that YAML into ``BenchmarkTarget`` objects at runtime.

Using the Baselines Extra
-------------------------

Installing ``openstef-beam[baselines]`` makes the ``openstef_beam.benchmarking.baselines`` subpackage
available. It provides ``OpenSTEF4BacktestForecaster``, a thin adapter that wraps any
``ForecastingWorkflow`` from ``openstef_models`` (or an ``EnsembleForecastingWorkflow`` from
``openstef_meta``) into the ``BacktestForecasterMixin`` interface.

.. code-block:: python

   from openstef_beam.benchmarking.baselines.openstef4 import (
       create_openstef4_preset_backtest_forecaster,
   )
   from openstef_models.presets import ForecastingWorkflowConfig

   workflow_config = ForecastingWorkflowConfig(model_type="gblinear")

   forecaster_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=workflow_config,
       cache_dir=Path("./cache"),
   )

   pipeline.register_forecaster("gblinear", forecaster_factory)

The factory pattern matters here: ``BenchmarkPipeline`` calls the factory once per target, so each
target gets a fresh, untrained model instance. The adapter deep-copies the workflow template on every
``fit()`` call to guarantee isolation between training cycles.

.. note::

   ``create_openstef4_preset_backtest_forecaster`` raises ``MissingExtraError`` at import time if
   ``openstef-beam[baselines]`` is not installed, giving a clear message rather than a cryptic
   ``ImportError``.

Evaluating Pre-existing Forecasts
----------------------------------

If you already have predictions from an external system, you can skip backtesting entirely and run
only the evaluation and analysis stages. Place your forecast parquets in the expected layout:

.. code-block:: text

   benchmark_results/MyForecasts/
   └── backtest/
       └── <group_name>/
           └── <target_name>/
               └── predictions.parquet

Each parquet must contain a ``DatetimeIndex`` named ``timestamp``, an ``available_at`` column
(recording when the prediction was generated), and one column per quantile named with the
``Quantile(x).format()`` convention (e.g. ``quantile_P50``). The ``available_at`` column is what
enables lead-time filtering during evaluation — without it, D-1 vs. D-2 accuracy cannot be
distinguished.

Comparing Multiple Runs
-----------------------

After benchmarking two or more model configurations, ``BenchmarkComparisonPipeline`` generates
side-by-side comparison plots at global, per-group, and per-target granularity:

.. code-block:: python

   from openstef_beam.benchmarking.benchmark_comparison_pipeline import (
       BenchmarkComparisonPipeline,
   )
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from pathlib import Path

   run_data = {
       "median_baseline": LocalBenchmarkStorage(Path("./benchmark_results/median_baseline")),
       "gblinear":        LocalBenchmarkStorage(Path("./benchmark_results/gblinear")),
   }

   comparison = BenchmarkComparisonPipeline()
   comparison.run(run_data=run_data)

The pipeline auto-detects which targets are present in all runs and restricts the comparison to that
common subset, so partial runs do not cause errors.

.. note:: [VISUALIZATION: Side-by-side bar charts comparing RMAE scores across models at global level, per energy-asset group, and for individual targets, with error bars showing variance across the evaluation window.]

Key Design Decisions
--------------------

**No data leakage by construction.** ``RestrictedHorizonVersionedTimeSeries`` makes it structurally
impossible to read future data, rather than relying on developer discipline.

**Pluggable at every layer.** Metrics, visualisations, storage backends, and forecasters are all
injected via configuration. The pipeline itself contains no model-specific or metric-specific logic.

**openstef-core is the only hard dependency.** This keeps the install footprint small for teams that
bring their own models and only need the evaluation scaffolding. The ``baselines`` extra is strictly
opt-in.

**Parallel execution is built in.** ``BenchmarkPipeline`` processes targets concurrently. Set
``OMP_NUM_THREADS=1`` (or equivalent) when running XGBoost-based models to avoid thread contention
between the parallelism layers.

Related Pages
-------------

- :doc:`core` — ``openstef_core`` validated datasets and the ``TimeSeriesDataset`` type used
  throughout BEAM's interfaces.
- :doc:`models` — ``openstef_models`` forecasting workflows that the ``baselines`` extra wraps.
- :doc:`meta` — ``openstef_meta`` ensemble workflows available through
  ``create_openstef4_preset_backtest_forecaster``.