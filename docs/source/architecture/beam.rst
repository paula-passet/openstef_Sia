The openstef_beam Package
=========================

**BEAM** (Backtesting, Evaluation, Analysis, Metrics) is the ``openstef_beam`` package — a structured framework for evaluating energy forecasting models under realistic, production-like conditions. This page covers how BEAM's pipelines fit together, how to plug in any forecasting model, and how ``BenchmarkPipeline`` orchestrates complete multi-model, multi-target evaluation workflows.

For the validated dataset hierarchy that BEAM consumes, see :doc:`core`. For the predefined forecasters available as benchmark baselines, see :doc:`models` and :doc:`meta`.

.. note::

   BEAM's core dependency is ``openstef-core`` only. You can evaluate any model that implements ``BacktestForecasterMixin`` without pulling in ``openstef-models`` or ``openstef-meta``. The optional ``baselines`` extra adds those packages and exposes a set of ready-made benchmark forecasters.


The Four Pipelines
------------------

BEAM decomposes a full evaluation run into four focused pipeline stages. Three of them — ``BacktestPipeline``, ``EvaluationPipeline``, and ``AnalysisPipeline`` — each own a single concern. ``BenchmarkPipeline`` acts as the top-level orchestrator, running all three across every combination of model and target.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

**BacktestPipeline** replays historical data day by day. At each step it exposes only the data that would have been available at that point in time — no lookahead — retrains the model on a rolling window, and records the resulting probabilistic forecasts. The output is a ``predictions.parquet`` per target.

**EvaluationPipeline** scores those predictions against ground truth using a configurable set of metric providers (e.g. ``RMAEProvider``, ``RCRPSProvider``). It produces ``EvaluationReport`` objects that carry per-lead-time breakdowns, which is important for operational planning where a 2-hour forecast and a 48-hour forecast have very different value.

**AnalysisPipeline** turns evaluation reports into visualisations and summary tables. It operates at three aggregation levels — per-target, per-group, and global — so you can drill down from a fleet-wide summary to a single asset.

**BenchmarkPipeline** wires everything together. It fetches targets from a ``TargetProvider``, fans out backtesting across them (with optional parallelism), collects all reports, and drives analysis. Results are persisted through a pluggable storage backend so runs are reproducible and comparable.


Installing BEAM
---------------

The core package has no dependency on ``openstef-models`` or ``openstef-meta``:

.. code-block:: bash

   pip install openstef-beam

To also get the predefined baseline forecasters (GBLinear, ensemble models, etc.) described in :doc:`models` and :doc:`meta`:

.. code-block:: bash

   pip install "openstef-beam[baselines]"


Implementing a Forecaster
-------------------------

Any class that implements ``BacktestForecasterMixin`` can be evaluated by BEAM. The interface is intentionally minimal:

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterMixin,
       BacktestForecasterConfig,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile


   class MedianHistoryForecaster(BacktestForecasterMixin):
       """Predicts the rolling median of recent load — a simple but honest baseline."""

       def __init__(self, config: BacktestForecasterConfig):
           self.config = config
           self._quantiles = [Quantile(0.05), Quantile(0.50), Quantile(0.95)]
           self._median = None

       @property
       def quantiles(self) -> list[Quantile]:
           return self._quantiles

       def fit(self, data) -> None:
           # data is a RestrictedHorizonVersionedTimeSeries — only past data visible
           window = data.get_window(
               data.horizon - self.config.training_window,
               data.horizon,
               available_before=data.horizon,
           )
           self._median = window["load"].median()

       def predict(self, data) -> TimeSeriesDataset | None:
           if self._median is None:
               return None
           index = data.forecast_index
           return TimeSeriesDataset(
               {
                   "load": self._median,
                   "quantile_P05": self._median * 0.8,
                   "quantile_P50": self._median,
                   "quantile_P95": self._median * 1.2,
               },
               index=index,
           )

The ``data`` argument is always a ``RestrictedHorizonVersionedTimeSeries``. It enforces the no-lookahead contract: calling ``get_window`` with an ``available_before`` timestamp beyond the current horizon raises an error rather than silently leaking future data.

For models that benefit from batching (e.g. neural networks with GPU inference), implement ``BacktestBatchForecasterMixin`` instead and override ``predict_batch``.


Running a Benchmark
-------------------

The example below runs two forecasters — the custom baseline above and a GBLinear model from ``openstef-models`` — against the built-in Liander 2024 dataset:

.. code-block:: python

   from pathlib import Path
   from datetime import timedelta

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.backtesting import BacktestConfig
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from openstef_beam.benchmarking.datasets.liander2024 import (
       create_liander2024_benchmark_runner,
   )

   storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))

   backtest_config = BacktestConfig(
       horizon=timedelta(hours=24),
       window_step=timedelta(days=1),
   )
   evaluation_config = EvaluationConfig(
       metric_providers=[RMAEProvider(), RCRPSProvider()],
   )
   analysis_config = AnalysisConfig(
       visualization_providers=[SummaryTableVisualization(name="summary")],
   )

   pipeline = create_liander2024_benchmark_runner(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       storage=storage,
   )

   # Register forecasters under a display name
   pipeline.register_forecaster("MedianBaseline", MedianHistoryForecaster)

   # The 'baselines' extra is needed for GBLinear
   from openstef_beam.baselines import GBLinearForecaster
   pipeline.register_forecaster("GBLinear", GBLinearForecaster)

   pipeline.run(categories=["solar_park"])

Results land in ``./benchmark_results/``. Each registered model gets its own subdirectory containing the raw prediction parquets, evaluation scores, and analysis plots.

.. note:: [VISUALIZATION: Side-by-side RMAE bar chart comparing MedianBaseline vs GBLinear across lead times (1h, 6h, 12h, 24h) for a solar park target group, as produced by SummaryTableVisualization.]


Bringing Your Own Data
----------------------

To evaluate against your own dataset, subclass ``SimpleTargetProvider`` and point it at your parquet files:

.. code-block:: python

   from openstef_beam.benchmarking.target_providers import SimpleTargetProvider


   class MyGridTargetProvider(SimpleTargetProvider):
       def _get_measurements_path_for_target(self, target):
           return Path(f"/data/measurements/{target.name}.parquet")

       def _get_weather_path_for_target(self, target):
           return Path(f"/data/weather/{target.group_name}.parquet")

Then pass an instance of ``MyGridTargetProvider`` when constructing ``BenchmarkPipeline`` directly:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline

   pipeline = BenchmarkPipeline(
       target_provider=MyGridTargetProvider(targets_yaml=Path("targets.yaml")),
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       storage=storage,
   )
   pipeline.register_forecaster("MyModel", MyForecaster)
   pipeline.run()


Evaluating Pre-existing Forecasts
----------------------------------

If you already have predictions from an external system, you can skip backtesting entirely and run only evaluation and analysis. Place your parquet files in the expected layout:

.. code-block:: text

   benchmark_results/MyForecasts/
   └── backtest/
       └── <group_name>/
           └── <target_name>/
               └── predictions.parquet

Each ``predictions.parquet`` must contain a ``DatetimeIndex`` named ``timestamp``, an ``available_at`` column (used for lead-time filtering), and one column per quantile named with the ``quantile_PXX`` convention. Then call the pipeline with the ``skip_backtest=True`` flag — the ``EvaluationPipeline`` and ``AnalysisPipeline`` stages run as normal.

.. note::

   The ``available_at`` column is what enables lead-time analysis. A prediction timestamped ``2023-01-15 12:00`` with ``available_at = 2023-01-14 06:00`` is a 30-hour-ahead forecast. BEAM uses this to bucket scores by lead time automatically.


Comparing Runs
--------------

After running two or more models, generate side-by-side comparison plots with the built-in comparison utilities:

.. code-block:: python

   from openstef_beam.benchmarking.comparison import compare_runs

   compare_runs(
       results_dirs=[
           Path("./benchmark_results/MedianBaseline"),
           Path("./benchmark_results/GBLinear"),
       ],
       output_dir=Path("./benchmark_results_comparison"),
   )

The comparison scripts auto-detect which targets are present in all runs, so partial results from a failed run do not skew the comparison. Output is a set of HTML plots — global, per-group, and per-target — saved to the output directory.


Dependency Summary
------------------

+------------------------------+------------------------------------------+
| Install                      | What you get                             |
+==============================+==========================================+
| ``openstef-beam``            | All four pipelines, ``BacktestForecaster |
|                              | Mixin``, metric providers, storage       |
|                              | backends. Depends on ``openstef-core``   |
|                              | only.                                    |
+------------------------------+------------------------------------------+
| ``openstef-beam[baselines]`` | Everything above, plus predefined        |
|                              | forecasters from ``openstef-models`` and |
|                              | ``openstef-meta`` (GBLinear, ensemble    |
|                              | models). See :doc:`models` and           |
|                              | :doc:`meta`.                             |
+------------------------------+------------------------------------------+