OpenSTEF BEAM
=============

**BEAM** (Backtesting, Evaluation, Analysis, Metrics) is the ``openstef_beam`` package — a structured framework for evaluating energy forecasting models under realistic, production-like conditions. This page covers how BEAM's pipelines fit together, how to plug in any forecasting model, and how ``BenchmarkPipeline`` orchestrates complete multi-model, multi-target evaluation workflows.

For the validated dataset hierarchy that BEAM consumes, see :doc:`core`. For the predefined forecasters available as benchmark baselines, see :doc:`models` and :doc:`meta`.

.. note::

   BEAM's core dependency is ``openstef-core`` only. You can evaluate any model — including models with no connection to the OpenSTEF ecosystem — as long as it implements the ``BacktestForecasterMixin`` interface. The optional ``baselines`` extra (``pip install openstef-beam[baselines]``) pulls in ``openstef-models`` and ``openstef-meta``, which provide ready-made benchmark forecasters.


The Four Pipelines
------------------

BEAM decomposes model evaluation into four distinct, composable stages:

- **BacktestPipeline** — replays historical data day by day, retraining the model periodically and generating forecasts without any lookahead. Each prediction is stamped with an ``available_at`` timestamp so downstream stages can filter by lead time.
- **EvaluationPipeline** — scores the backtest predictions against ground truth using configurable metric providers (e.g. RMAE, RCRPS). Produces structured ``EvaluationReport`` objects per target.
- **AnalysisPipeline** — turns evaluation reports into visualisations and summary tables, aggregated at target, group, or global scope.
- **BenchmarkPipeline** — the top-level orchestrator. It drives the three pipelines above across every combination of model and target, managing parallel execution, storage, and cross-model comparison.

.. note:: [DIAGRAM: Pipeline flow showing BacktestPipeline feeding predictions into EvaluationPipeline, which produces EvaluationReports consumed by AnalysisPipeline to generate VisualizationOutputs. BenchmarkPipeline wraps all three in an outer loop over multiple models and targets, with arrows indicating data flow and a shared LocalBenchmarkStorage sink.]


Implementing a Forecaster
-------------------------

Any class that implements ``BacktestForecasterMixin`` can be evaluated by BEAM. The interface requires three things: a ``quantiles`` property, a ``fit`` method, and a ``predict`` method.

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster import BacktestForecasterMixin
   from openstef_core.types import Quantile
   import numpy as np

   class MedianHistoryForecaster(BacktestForecasterMixin):
       """Predicts the rolling median of recent load as a flat forecast."""

       def __init__(self, config):
           self.config = config
           self._quantiles = [Quantile(0.05), Quantile(0.50), Quantile(0.95)]
           self._median = None

       @property
       def quantiles(self):
           return self._quantiles

       def fit(self, data):
           # data is a RestrictedHorizonVersionedTimeSeries — no future leakage
           window = data.get_window(
               data.horizon - np.timedelta64(30, "D"),
               data.horizon,
               available_before=data.horizon,
           )
           self._median = float(window["load"].median())

       def predict(self, data):
           if self._median is None:
               return None
           index = data.forecast_index
           return data.make_dataset({
               "load": self._median,
               "quantile_P05": self._median * 0.8,
               "quantile_P50": self._median,
               "quantile_P95": self._median * 1.2,
           }, index=index)

The ``data`` argument is always a ``RestrictedHorizonVersionedTimeSeries``. It enforces no-lookahead by only exposing data that was available before ``data.horizon``. This is the mechanism that makes BEAM's backtests honest.

.. note::

   ``fit`` is called periodically (controlled by ``BacktestConfig.window_step``). ``predict`` is called at every forecast step within the backtest window. Returning ``None`` from ``predict`` signals that the model has insufficient data and that step is skipped gracefully.


Running a Benchmark
-------------------

The following example wires together all four pipelines using the built-in Liander 2024 dataset. It registers two forecasters and runs the full evaluation workflow.

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
   from openstef_beam.benchmarking.datasets import create_liander2024_benchmark_runner

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

   runner = create_liander2024_benchmark_runner(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       storage=storage,
   )

   # Register forecasters by name
   runner.register_forecaster("MedianBaseline", MedianHistoryForecaster)

   # Run across all targets in the dataset
   runner.run(categories=["solar_park"])

Results are written under ``./benchmark_results/``. Each registered model gets its own subdirectory containing backtest predictions (Parquet), evaluation scores, and analysis plots.

.. note:: [VISUALIZATION: Example summary table output showing RMAE and RCRPS scores per model (rows) and target group (columns), with colour-coded cells indicating relative performance.]


Using Your Own Data
-------------------

If you have your own measurement and weather data, subclass ``SimpleTargetProvider`` and override two path methods:

.. code-block:: python

   from openstef_beam.benchmarking.target_providers import SimpleTargetProvider

   class MyTargetProvider(SimpleTargetProvider):

       def _get_measurements_path_for_target(self, target):
           return Path(f"./data/measurements/{target.name}.parquet")

       def _get_weather_path_for_target(self, target):
           return Path(f"./data/weather/{target.group_name}.parquet")

Pass an instance of your provider when constructing ``BenchmarkPipeline`` directly, rather than using a dataset factory. The rest of the workflow is identical.


Evaluating Pre-existing Forecasts
----------------------------------

If you already have predictions from an external system, you can skip backtesting entirely and run only the evaluation and analysis stages. Place your forecast Parquets in the expected layout:

.. code-block:: text

   benchmark_results/MyForecasts/
   └── backtest/
       └── <group_name>/
           └── <target_name>/
               └── predictions.parquet

Each Parquet file must include a ``DatetimeIndex`` named ``timestamp``, an ``available_at`` column, and one column per quantile formatted as ``quantile_P05``, ``quantile_P50``, etc. BEAM then runs ``EvaluationPipeline`` and ``AnalysisPipeline`` against these files without touching ``BacktestPipeline`` at all.

This is useful for integrating legacy models, third-party forecasts, or operational systems into a standardised scoring framework.


Predefined Baselines
--------------------

Installing the ``baselines`` extra gives access to forecasters built on ``openstef-models`` and ``openstef-meta``:

.. code-block:: bash

   pip install "openstef-beam[baselines]"

These include gradient-boosted tree models and ensemble forecasters that serve as meaningful reference points in benchmarks. Because they implement ``BacktestForecasterMixin``, they are registered and run exactly like any custom forecaster — there is no special handling. See :doc:`models` for the available model transforms and :doc:`meta` for the ``EnsembleForecastingModel`` that combines them.

.. note::

   The ``baselines`` extra is entirely optional. BEAM's evaluation machinery has no dependency on ``openstef-models`` or ``openstef-meta``. You can run a complete benchmark comparing only your own models without installing either package.


Comparing Multiple Runs
-----------------------

After accumulating results from several runs (different models, hyperparameter sweeps, or time periods), BEAM can generate side-by-side comparison plots automatically:

.. code-block:: python

   from openstef_beam.benchmarking.comparison import compare_benchmark_runs

   compare_benchmark_runs(
       results_dir=Path("./benchmark_results"),
       output_dir=Path("./benchmark_results_comparison"),
   )

The comparison utility auto-detects which targets are present in all runs and produces global, per-group, and per-target HTML plots. Only targets common to every run are included, so partial runs do not distort the comparison.

.. note:: [VISUALIZATION: Side-by-side bar chart comparing RMAE across three models (MedianBaseline, GBLinear, EnsembleForecaster) for each target group, with error bars showing variance across targets within each group.]


Output Structure
----------------

A completed benchmark produces a consistent directory layout regardless of which models were evaluated:

.. code-block:: text

   benchmark_results/
   ├── ModelA/
   │   ├── backtest/<group>/<target>/predictions.parquet
   │   ├── evaluation/<group>/<target>/scores.json
   │   └── analysis/<group>/<target>/summary.html
   └── ModelB/
       └── ...

This layout is consumed directly by the comparison utilities and can also be queried programmatically via the ``LocalBenchmarkStorage`` API.