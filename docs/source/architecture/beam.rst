The openstef_beam Package
=========================

The ``openstef_beam`` package provides a structured evaluation framework for energy forecasting models. Where :doc:`core` defines the data contracts and :doc:`models` supplies ready-made forecasting workflows, BEAM answers the question: *how well does a model actually perform in production-like conditions?* It does this through a layered pipeline architecture — backtesting, evaluation, analysis, and benchmarking — that can be applied to any forecasting model, not just those built on OpenSTEF.

.. note::

   This page covers the ``openstef_beam`` package in depth. For the validated dataset hierarchy used throughout these pipelines, see :doc:`core`. For predefined forecasting workflows that plug into the benchmarking baselines, see :doc:`models` and :doc:`meta`.

Installation
------------

The core package depends only on ``openstef-core``::

   pip install openstef-beam

To use the predefined OpenSTEF baseline forecasters (which pull in ``openstef-models`` and ``openstef-meta``), install the optional extra::

   pip install openstef-beam[baselines]

Pipeline Architecture
---------------------

BEAM organises evaluation into four composable pipelines. Three of them form a sequential chain — backtest, evaluate, analyse — and a fourth, ``BenchmarkPipeline``, orchestrates that chain across many models and targets simultaneously.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

BacktestPipeline
^^^^^^^^^^^^^^^^

``BacktestPipeline`` replays historical data under realistic temporal constraints. Rather than training once and evaluating on a held-out set, it simulates the operational schedule: predictions are made at regular intervals, and the model is retrained on a rolling basis exactly as it would be in production. This prevents look-ahead bias and gives evaluation results that reflect real-world latency and data availability.

The pipeline is configured through ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
   )

Any model that implements ``BacktestForecasterMixin`` can be passed to the pipeline. The mixin requires two methods:

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterMixin,
       BacktestForecasterConfig,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.base_model import BaseModel

   class MyForecaster(BaseModel, BacktestForecasterMixin):
       config: BacktestForecasterConfig

       @property
       def quantiles(self) -> list:
           return [0.1, 0.5, 0.9]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           # train on data.get_window(...) — only past data is visible
           ...

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset | None:
           # return probabilistic forecasts or None if insufficient data
           ...

The ``RestrictedHorizonVersionedTimeSeries`` wrapper enforces the horizon constraint: any call to ``get_window`` with an ``available_before`` timestamp will only return data that would have been available at that point in time, making it impossible to accidentally leak future information.

EvaluationPipeline
^^^^^^^^^^^^^^^^^^

``EvaluationPipeline`` takes the raw predictions produced by backtesting and computes performance metrics across multiple dimensions: availability times, lead times, and configurable time windows. The result is an ``EvaluationReport`` — a structured object that captures metric breakdowns at each segmentation level.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationReport

   pipeline = EvaluationPipeline()
   report: EvaluationReport = pipeline.run(predictions=backtest_output)

Because ``EvaluationReport`` is a plain data object, it can be serialised, stored, and loaded later for retrospective analysis without re-running the expensive backtesting step.

AnalysisPipeline
^^^^^^^^^^^^^^^^

``AnalysisPipeline`` converts ``EvaluationReport`` objects into visualisations and summary outputs. It operates at configurable aggregation scopes — individual targets, named groups, or globally across an entire benchmark run.

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig, AnalysisPipeline, AnalysisScope
   from openstef_beam.analysis.models import AnalysisAggregation, TargetMetadata

   analysis_config = AnalysisConfig()
   pipeline = AnalysisPipeline(config=analysis_config)

   # Analyse a single target
   output = pipeline.run_for_reports(
       reports=[(target_metadata, evaluation_report)],
       scope=AnalysisScope.TARGET,
   )

   # Analyse grouped targets (e.g. by region or asset type)
   group_outputs = pipeline.run_for_groups(
       reports=[(target_metadata, evaluation_report), ...],
       scope=AnalysisScope.GROUP,
   )

.. note:: [VISUALIZATION: Example analysis output showing metric breakdowns by lead time horizon, with separate panels for each quantile and a summary table of CRPS and MAE scores per target group.]

BenchmarkPipeline
-----------------

``BenchmarkPipeline`` is the top-level orchestrator. It acquires targets from a ``TargetProvider``, instantiates forecasters via a ``ForecasterFactory`` for each target, runs the full backtest → evaluate → analyse chain, and writes results to a ``BenchmarkStorage`` backend. Parallel execution across targets is managed internally.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.benchmarking.benchmark_pipeline import BenchmarkContext
   from openstef_beam.benchmarking.target_provider import TargetProvider
   from openstef_beam.benchmarking.storage import BenchmarkStorage

   # ForecasterFactory is a callable: BenchmarkTarget -> BacktestForecasterMixin
   def my_forecaster_factory(target):
       return MyForecaster(config=BacktestForecasterConfig(...))

   pipeline = BenchmarkPipeline(
       target_provider=my_target_provider,
       forecaster_factory=my_forecaster_factory,
       storage=my_storage_backend,
   )
   pipeline.run()

The ``BenchmarkContext`` carries shared state (configuration, run metadata) across all targets in a single benchmark run, making it straightforward to tag results for later comparison.

Using Predefined Baselines
--------------------------

When the ``baselines`` extra is installed, ``openstef_beam.benchmarking.baselines`` provides ready-made ``BacktestForecaster`` implementations built on top of ``openstef-models`` and ``openstef-meta``. The primary entry point is ``create_openstef4_preset_backtest_forecaster``, which wraps any ``ForecastingWorkflow`` (including the ensemble workflows from ``openstef-meta``) into a factory compatible with ``BenchmarkPipeline``:

.. code-block:: python

   from openstef_beam.benchmarking.baselines.openstef4 import (
       create_openstef4_preset_backtest_forecaster,
   )
   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_beam.backtesting.backtest_forecaster.mixins import BacktestForecasterConfig

   workflow_config = ForecastingWorkflowConfig(...)
   backtest_config = BacktestForecasterConfig(...)

   factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=workflow_config,
       backtest_config=backtest_config,
       cache_dir="cache/",
   )

   # factory is now a ForecasterFactory[BenchmarkTarget] ready for BenchmarkPipeline
   pipeline = BenchmarkPipeline(
       target_provider=my_target_provider,
       forecaster_factory=factory,
       storage=my_storage_backend,
   )
   pipeline.run()

.. note::

   ``OpenSTEF4BacktestForecaster`` creates a fresh workflow instance for every ``fit()`` call by deep-copying the provided template. This ensures that training cycles are fully independent and that no state leaks between backtesting windows.

Comparing Benchmark Runs
------------------------

``BenchmarkComparisonPipeline`` operates on *stored* benchmark results, enabling side-by-side comparison of multiple runs without re-executing any computation. This is useful for evaluating the effect of hyperparameter changes, new model versions, or different feature sets.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.benchmarking.benchmark_pipeline import read_evaluation_reports

   comparison = BenchmarkComparisonPipeline(
       target_provider=my_target_provider,
       storage=my_storage_backend,
   )

   run_data = {
       "baseline_v1": storage_v1,
       "baseline_v2": storage_v2,
   }
   comparison.run(run_data=run_data)

The comparison pipeline aggregates results at global, group, and individual target levels, delegating visualisation to the same ``AnalysisPipeline`` used in a standard benchmark run.

Dependency Model
----------------

The separation between the core package and the ``baselines`` extra is intentional. ``openstef_beam`` itself depends only on ``openstef-core`` for dataset types and base model utilities. This means you can integrate any forecasting model — scikit-learn pipelines, PyTorch models, statistical baselines — by implementing ``BacktestForecasterMixin``, without pulling in the full OpenSTEF model stack.

.. mermaid:: /diagrams/architecture/beam_diagram_2.mmd

The ``baselines`` extra is additive: installing it does not change the behaviour of any existing code; it only makes the predefined forecaster implementations available. See :doc:`models` for details on ``ForecastingWorkflowConfig`` and the preset workflows, and :doc:`meta` for the ``EnsembleForecastingWorkflowConfig`` that can be passed directly to ``create_openstef4_preset_backtest_forecaster``.