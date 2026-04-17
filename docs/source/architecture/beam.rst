OpenSTEF BEAM: Backtesting, Evaluation, Analysis and Metrics
=============================================================

**openstef_beam** is the evaluation engine of the OpenSTEF library. Its name is an acronym for its four responsibilities: **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics. This page covers how those four concerns are organised into pipelines, how they compose into a complete benchmarking workflow, and how to plug in any forecasting model — not just those shipped with OpenSTEF.

For the data structures that flow through these pipelines see :doc:`core`. For the predefined OpenSTEF forecasters that can be used as benchmark baselines see :doc:`models` and :doc:`meta`.

.. note::

   **[DIAGRAM: Pipeline composition in openstef_beam. BacktestPipeline produces a TimeSeriesDataset of predictions. EvaluationPipeline consumes those predictions and ground truth to produce an EvaluationReport. AnalysisPipeline consumes EvaluationReports to produce visualisations and summary tables. BenchmarkPipeline orchestrates all three stages across N models × M targets in parallel, collecting and storing results at each stage.]**

   .. code-block:: text

      ┌─────────────────────────────────────────────────────────────────┐
      │                      BenchmarkPipeline                          │
      │                                                                 │
      │  for each model × target:                                       │
      │  ┌──────────────────┐   predictions   ┌──────────────────────┐ │
      │  │  BacktestPipeline │ ─────────────▶ │  EvaluationPipeline  │ │
      │  └──────────────────┘                 └──────────┬───────────┘ │
      │                                                  │ EvaluationReport
      │                                                  ▼             │
      │                                       ┌──────────────────────┐ │
      │                                       │   AnalysisPipeline   │ │
      │                                       └──────────────────────┘ │
      └─────────────────────────────────────────────────────────────────┘


Installation
------------

``openstef-beam`` depends only on ``openstef-core`` from the OpenSTEF family, so it installs cleanly without pulling in any model training code:

.. code-block:: bash

   pip install openstef-beam

To also get the predefined benchmark forecasters built on ``openstef-models`` and ``openstef-meta``, install the ``baselines`` extra:

.. code-block:: bash

   pip install "openstef-beam[baselines]"

The ``baselines`` extra adds ``openstef-models`` and ``openstef-meta`` as dependencies, making the ``OpenSTEF4BacktestForecaster`` adapter and the ensemble preset available. You do not need this extra to run BEAM with your own models.


The Backtesting Pipeline
------------------------

``BacktestPipeline`` simulates the operational forecasting environment by replaying history day by day. At each step it exposes only the data that would have been available at that moment in time, preventing any look-ahead leakage. The pipeline calls ``fit`` on your model periodically (controlled by the training interval in ``BacktestConfig``) and ``predict`` at every prediction step.

The entry point for integrating any model is ``BacktestForecasterMixin``. Implementing it requires three things:

- a ``config`` attribute of type ``BacktestForecasterConfig`` that declares prediction and training intervals,
- a ``quantiles`` property listing the output quantiles,
- ``fit(data)`` and ``predict(data)`` methods.

The ``data`` argument is a ``RestrictedHorizonVersionedTimeSeries``: a wrapper around ``openstef_core`` versioned datasets that enforces the no-lookahead contract. Use ``data.get_window(start, end, available_before)`` to retrieve any historical slice.

.. code-block:: python

   from datetime import timedelta

   import numpy as np
   import pandas as pd

   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterConfig,
       BacktestForecasterMixin,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Q, Quantile


   class MedianForecaster(BacktestForecasterMixin):
       """Predict the rolling median of the last 7 days as a flat forecast."""

       def __init__(self) -> None:
           self.config = BacktestForecasterConfig(
               predict_sample_interval=timedelta(minutes=15),
               retrain_interval=timedelta(days=1),
               train_window=timedelta(days=30),
           )
           self._median: float = 0.0

       @property
       def quantiles(self) -> list[Quantile]:
           return [Q(0.05), Q(0.50), Q(0.95)]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           window = data.get_window(
               data.horizon - timedelta(days=7),
               data.horizon,
               available_before=data.horizon,
           )
           self._median = float(window["load"].median())

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset:
           index = pd.date_range(
               data.horizon,
               periods=96,  # 24 h at 15-min resolution
               freq="15min",
           )
           return TimeSeriesDataset(
               pd.DataFrame(
                   {
                       "load": self._median,
                       "quantile_P05": self._median * 0.8,
                       "quantile_P50": self._median,
                       "quantile_P95": self._median * 1.2,
                   },
                   index=index,
               )
           )

.. note::

   ``BacktestForecasterMixin`` is the only interface BEAM requires. There is no dependency on ``openstef-models`` or any other OpenSTEF package. Any Python object that satisfies the mixin contract — a scikit-learn pipeline, a PyTorch model, a statistical baseline — can be backtested.

Running the pipeline directly against a versioned dataset:

.. code-block:: python

   from datetime import datetime, timedelta

   from openstef_beam.backtesting.backtest_pipeline import BacktestPipeline
   from openstef_beam.backtesting.backtest_config import BacktestConfig

   config = BacktestConfig(
       horizon=timedelta(hours=24),
       window_step=timedelta(days=1),
   )

   pipeline = BacktestPipeline(config=config, forecaster=MedianForecaster())

   predictions = pipeline.run(
       ground_truth=versioned_ground_truth,   # VersionedTimeSeriesDataset
       predictors=versioned_predictors,       # VersionedTimeSeriesDataset
       start=datetime(2023, 1, 1),
       end=datetime(2023, 6, 30),
   )
   # predictions is a TimeSeriesDataset with one column per quantile


The Evaluation Pipeline
-----------------------

``EvaluationPipeline`` takes the ``TimeSeriesDataset`` produced by backtesting and scores it against ground truth across multiple dimensions: availability time (D-1, D-2, …), lead time (1 h ahead, 6 h ahead, …), and configurable time windows. The result is an ``EvaluationReport`` — a structured object that records every metric for every subset.

Metrics are provided as ``MetricProvider`` plugins. Two are included out of the box:

- ``RMAEProvider`` — relative mean absolute error,
- ``RCRPSProvider`` — relative continuous ranked probability score for probabilistic forecasts.

.. code-block:: python

   from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline
   from openstef_beam.evaluation.evaluation_config import EvaluationConfig
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider

   evaluation_config = EvaluationConfig(
       metric_providers=[RMAEProvider(), RCRPSProvider()],
   )

   eval_pipeline = EvaluationPipeline(config=evaluation_config)
   report = eval_pipeline.run(predictions=predictions, ground_truth=ground_truth)

   # report.subsets contains per-lead-time, per-window metric breakdowns
   print(report.subsets[0].metrics)

The ``EvaluationConfig`` lets you restrict which lead times and availability windows are scored, which is important for operational use cases where only certain horizons matter.


The Analysis Pipeline
---------------------

``AnalysisPipeline`` consumes one or more ``EvaluationReport`` objects and produces visualisations and summary tables. Visualisation providers are pluggable; ``SummaryTableVisualization`` is the default and renders an interactive HTML table of aggregated scores.

.. code-block:: python

   from openstef_beam.analysis.analysis_pipeline import AnalysisPipeline
   from openstef_beam.analysis.analysis_config import AnalysisConfig
   from openstef_beam.analysis.visualizations import SummaryTableVisualization

   analysis_config = AnalysisConfig(
       visualization_providers=[SummaryTableVisualization(name="summary")],
   )

   analysis_pipeline = AnalysisPipeline(config=analysis_config)
   analysis_pipeline.run(reports={"MedianForecaster": report})

**[VISUALIZATION: Example BEAM analysis output — an interactive HTML summary table showing RMAE and RCRPS scores broken down by model, lead time (1 h, 6 h, 12 h, 24 h), and target group, with colour-coded cells highlighting best-performing models per row.]**


The Benchmark Pipeline
----------------------

``BenchmarkPipeline`` is the top-level orchestrator. It wires together a ``TargetProvider`` (which supplies the versioned datasets for each energy asset), one or more forecaster factories, and the three sub-pipelines described above. It runs the full workflow — backtest → evaluate → analyse — for every combination of model and target, with optional parallel execution.

.. code-block:: python

   from pathlib import Path

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.backtesting.backtest_config import BacktestConfig
   from openstef_beam.evaluation.evaluation_config import EvaluationConfig
   from openstef_beam.analysis.analysis_config import AnalysisConfig
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from datetime import timedelta

   storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))

   pipeline = BenchmarkPipeline(
       backtest_config=BacktestConfig(
           horizon=timedelta(hours=24),
           window_step=timedelta(days=1),
       ),
       evaluation_config=EvaluationConfig(
           metric_providers=[RMAEProvider(), RCRPSProvider()],
       ),
       analysis_config=AnalysisConfig(
           visualization_providers=[SummaryTableVisualization(name="summary")],
       ),
       storage=storage,
       target_provider=my_target_provider,   # see below
   )

   pipeline.run(
       forecaster_factory=lambda ctx, target: MedianForecaster(),
       run_name="median_baseline",
       n_processes=4,
   )

Results are written to ``./benchmark_results/median_baseline/`` with one subdirectory per target containing the raw prediction parquets, evaluation JSON, and HTML analysis artefacts.

.. note::

   ``BenchmarkPipeline`` automatically skips backtesting for any target that already has a ``predictions.parquet`` on disk. This makes it safe to re-run after a partial failure, and it also lets you evaluate forecasts produced by an external system without re-running the backtest at all.


Providing Targets
-----------------

A ``TargetProvider`` tells the benchmark where to find data for each energy asset. ``SimpleTargetProvider`` is the recommended base class for custom data layouts — override ``_get_measurements_path_for_target()`` and ``_get_weather_path_for_target()`` to return paths to your parquet files:

.. code-block:: python

   from openstef_beam.benchmarking.target_provider import SimpleTargetProvider
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from pathlib import Path


   class MyTargetProvider(SimpleTargetProvider):
       def _get_measurements_path_for_target(self, target: BenchmarkTarget) -> Path:
           return Path("data") / target.group_name / target.name / "measurements.parquet"

       def _get_weather_path_for_target(self, target: BenchmarkTarget) -> Path:
           return Path("data") / target.group_name / target.name / "weather.parquet"

For quick experimentation, BEAM ships with a built-in **Liander 2024** dataset that is downloaded automatically from HuggingFace:

.. code-block:: python

   from openstef_beam.benchmarking.datasets.liander2024 import create_liander2024_benchmark_runner

   runner = create_liander2024_benchmark_runner()
   runner.run(
       forecaster_factory=lambda ctx, target: MedianForecaster(),
       run_name="median_baseline",
   )


Using Predefined Baselines
--------------------------

When the ``baselines`` extra is installed (``pip install "openstef-beam[baselines]"``), the ``OpenSTEF4BacktestForecaster`` adapter becomes available. It wraps any ``ForecastingWorkflow`` from ``openstef-models`` — including the GBLinear, LightGBM, and XGBoost presets — so they can participate in a BEAM benchmark without any additional glue code.

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster import OpenSTEF4BacktestForecaster
   from openstef_models.presets import create_forecasting_workflow, ForecastingWorkflowConfig

   workflow_config = ForecastingWorkflowConfig(model_type="xgb")
   workflow = create_forecasting_workflow(workflow_config)

   forecaster = OpenSTEF4BacktestForecaster(
       workflow_template=workflow,
       cache_dir=Path("./model_cache"),
   )

   pipeline.run(
       forecaster_factory=lambda ctx, target: forecaster,
       run_name="xgb_baseline",
   )

The ensemble forecaster from ``openstef-meta`` (see :doc:`meta`) can be used in exactly the same way — wrap it in ``OpenSTEF4BacktestForecaster`` and pass it as the factory.


Comparing Multiple Runs
-----------------------

After running two or more models, ``BenchmarkComparisonPipeline`` loads the stored ``EvaluationReport`` objects and produces side-by-side comparison plots at global, group, and individual-target granularity:

.. code-block:: python

   from openstef_beam.benchmarking.benchmark_comparison_pipeline import (
       BenchmarkComparisonPipeline,
   )
   from openstef_beam.analysis.analysis_config import AnalysisConfig, AnalysisScope
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from pathlib import Path

   storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))

   comparison = BenchmarkComparisonPipeline(
       storage=storage,
       target_provider=my_target_provider,
       analysis_config=AnalysisConfig(
           visualization_providers=[SummaryTableVisualization(name="comparison")],
           scope=AnalysisScope.GLOBAL,
       ),
   )

   comparison.run(
       run_names=["median_baseline", "xgb_baseline"],
       output_path=Path("./benchmark_results_comparison"),
   )

**[VISUALIZATION: Side-by-side comparison HTML output from BenchmarkComparisonPipeline — bar charts showing RMAE per model across all target groups, with one panel per lead-time bucket (D-1, D-2) and a global aggregate row at the top.]**

.. note::

   The comparison pipeline operates entirely on stored artefacts. It never re-runs backtesting or evaluation, so it is fast and cheap to re-run with different visualisation configurations.


Summary
-------

``openstef_beam`` provides a complete, reproducible evaluation framework that is independent of any particular forecasting model. The dependency on ``openstef-core`` only means you can integrate it with scikit-learn models, PyTorch networks, statistical baselines, or external forecasting systems — anything that implements ``BacktestForecasterMixin``. The optional ``baselines`` extra layers in the OpenSTEF model ecosystem for teams that want ready-made benchmark competitors.

The four pipeline classes map cleanly onto the four letters of the acronym:

- **B** — ``BacktestPipeline``: leak-free historical simulation
- **E** — ``EvaluationPipeline``: multi-dimensional metric scoring
- **A** — ``AnalysisPipeline``: visualisation and reporting
- **M** — ``BenchmarkPipeline`` + ``BenchmarkComparisonPipeline``: orchestration and metrics aggregation across models and targets