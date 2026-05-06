The openstef_beam Package
=========================

The ``openstef-beam`` package provides a structured evaluation framework for energy forecasting models. Where :doc:`core` defines the data primitives and :doc:`models` supplies ready-made forecasting workflows, BEAM answers the question: *how well does a model actually perform in production-like conditions?* It does this through four composable pipelines — backtesting, evaluation, analysis, and benchmarking — that together orchestrate complete model assessment studies.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

Installation
------------

The core evaluation framework depends only on ``openstef-core``:

.. code-block:: bash

   pip install openstef-beam

To use the predefined baseline forecasters (which wrap ``openstef-models`` and ``openstef-meta``), install the optional extra:

.. code-block:: bash

   pip install openstef-beam[baselines]

The ``baselines`` extra is entirely optional. The pipeline machinery itself has no dependency on any particular model implementation — you can plug in any forecaster that implements the ``BacktestForecasterMixin`` interface.


The Four Pipelines
------------------

BacktestPipeline
^^^^^^^^^^^^^^^^

``BacktestPipeline`` replays historical data under realistic temporal constraints. Rather than training once on a fixed split, it simulates the operational rhythm of a deployed forecaster: predictions are generated on a schedule, the model is periodically retrained, and at each step only data that would have been available at that moment in time is visible to the model.

This is controlled by ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
   )

Any model that implements ``BacktestForecasterMixin`` can be passed to the pipeline. The mixin requires two methods — ``fit`` and ``predict`` — both receiving a ``RestrictedHorizonVersionedTimeSeries`` that enforces the horizon constraint automatically, preventing any look-ahead leakage:

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterConfig,
       BacktestForecasterMixin,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.base_model import BaseModel
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile

   class MyForecaster(BaseModel, BacktestForecasterMixin):
       config: BacktestForecasterConfig

       @property
       def quantiles(self) -> list[Quantile]:
           return [0.1, 0.5, 0.9]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           window = data.get_window(data.start, data.end)
           # train your model on window.dataframe ...

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset | None:
           window = data.get_window(data.start, data.end)
           # return a TimeSeriesDataset with quantile columns ...

The ``BacktestForecasterMixin`` is the only contract BEAM imposes on a model. There is no requirement to use OpenSTEF model classes.

EvaluationPipeline
^^^^^^^^^^^^^^^^^^

Once backtesting produces a set of predictions, ``EvaluationPipeline`` segments them across multiple dimensions — availability times, lead times, and configurable time windows — and computes performance metrics for each subset. The result is an ``EvaluationReport`` that captures metric breakdowns at whatever granularity you need.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationReport

   pipeline = EvaluationPipeline()
   report: EvaluationReport = pipeline.run(predictions=backtest_output)

The report is a structured object that can be serialised and stored independently of the analysis step, which matters for large studies where you want to separate the expensive computation from the visualisation.

AnalysisPipeline
^^^^^^^^^^^^^^^^

``AnalysisPipeline`` consumes one or more ``EvaluationReport`` objects and produces visualisations. It operates at configurable aggregation levels — individual targets, named groups, or globally across an entire benchmark run — controlled by ``AnalysisConfig`` and ``AnalysisScope``:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig, AnalysisPipeline, AnalysisScope
   from openstef_beam.analysis.models import AnalysisAggregation, TargetMetadata

   config = AnalysisConfig()
   pipeline = AnalysisPipeline(config=config)

   # Generate visualisations for a list of (metadata, report) pairs
   output = pipeline.run_for_reports(
       reports=[(target_metadata, evaluation_report)],
       scope=AnalysisScope.TARGET,
   )

   # Or aggregate across groups
   group_outputs = pipeline.run_for_groups(
       reports=[(target_metadata, evaluation_report)],
       scope=AnalysisScope.GROUP,
   )

.. note:: [VISUALIZATION: Example analysis output showing metric breakdowns by lead time horizon, with separate panels per quantile and a summary table across target groups.]

BenchmarkPipeline
^^^^^^^^^^^^^^^^^

``BenchmarkPipeline`` is the top-level orchestrator. It acquires targets from a ``TargetProvider``, runs the full backtest → evaluate → analyse sequence for each target and model combination, manages parallel execution, and writes results to a ``BenchmarkStorage`` backend. You interact with it primarily through a ``ForecasterFactory`` — a callable that returns a fresh forecaster instance for a given target:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.benchmarking.models import BenchmarkTarget
   from openstef_beam.benchmarking.benchmark_pipeline import (
       BenchmarkContext,
       ForecasterFactory,
   )

   def my_forecaster_factory(target: BenchmarkTarget) -> MyForecaster:
       return MyForecaster(
           config=BacktestForecasterConfig(
               horizon=target.horizon,
               retrain_interval=target.retrain_interval,
           )
       )

   pipeline = BenchmarkPipeline(
       target_provider=my_target_provider,
       storage=my_storage,
       backtest_config=BacktestConfig(),
   )

   pipeline.run(forecaster_factory=my_forecaster_factory)

The pipeline stores ``EvaluationReport`` objects per target so that analysis can be re-run without repeating the backtesting step.


Using the Built-in Baselines
----------------------------

Installing ``openstef-beam[baselines]`` makes ``openstef_beam.benchmarking.baselines`` available. The primary baseline is ``OpenSTEF4BacktestForecaster``, which wraps any ``ForecastingWorkflow`` from ``openstef-models`` (including ensemble workflows from ``openstef-meta``) into the ``BacktestForecasterMixin`` interface.

The convenience factory ``create_openstef4_preset_backtest_forecaster`` handles the wiring:

.. code-block:: python

   from openstef_beam.benchmarking.baselines.openstef4 import (
       create_openstef4_preset_backtest_forecaster,
   )
   from openstef_models.presets import ForecastingWorkflowConfig

   workflow_config = ForecastingWorkflowConfig(
       # ... your workflow configuration
   )

   forecaster_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=workflow_config,
       cache_dir="cache/",
   )

   # Pass directly to BenchmarkPipeline
   pipeline.run(forecaster_factory=forecaster_factory)

The factory creates a new workflow instance for each ``fit()`` call, ensuring no state leaks between training windows. If you are using an ensemble from ``openstef-meta``, pass an ``EnsembleForecastingWorkflowConfig`` in place of ``ForecastingWorkflowConfig`` — the factory accepts both.

.. note::

   The ``baselines`` extra is only needed for ``OpenSTEF4BacktestForecaster``. Custom forecasters that implement ``BacktestForecasterMixin`` directly require only the base ``openstef-beam`` install.


Comparing Runs
--------------

After running benchmarks with different model configurations, ``BenchmarkComparisonPipeline`` lets you analyse the stored results side-by-side without re-running any backtesting:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.benchmarking.storage import BenchmarkStorage

   run_data = {
       "baseline": BenchmarkStorage(path="results/baseline/"),
       "candidate": BenchmarkStorage(path="results/candidate/"),
   }

   comparison = BenchmarkComparisonPipeline(
       target_provider=my_target_provider,
   )
   comparison.run(run_data=run_data)

The comparison pipeline reads ``EvaluationReport`` objects from each storage location and passes them through ``AnalysisPipeline`` at global, group, and target aggregation levels, producing a unified set of comparison visualisations.

.. note:: [VISUALIZATION: Side-by-side metric comparison across two benchmark runs, showing relative improvement per target group with a global summary row.]


Design Principles
-----------------

A few patterns are worth understanding before building on BEAM:

**Temporal integrity.** ``RestrictedHorizonVersionedTimeSeries`` is not a convenience wrapper — it is the mechanism that makes backtesting results trustworthy. Every ``get_window`` call enforces the ``available_before`` constraint, so a model physically cannot access future data even if it tries.

**Separation of computation and analysis.** Backtesting and evaluation are expensive; analysis is cheap. Storing ``EvaluationReport`` objects between steps means you can iterate on visualisations and aggregations without re-running multi-hour backtests. ``BenchmarkComparisonPipeline`` exploits this directly.

**Model agnosticism.** The only coupling between BEAM and any model is the ``BacktestForecasterMixin`` interface. The ``openstef-models`` and ``openstef-meta`` packages are entirely optional. See :doc:`models` for the OpenSTEF model presets and :doc:`meta` for ensemble workflows if you want to use them as baselines.

**Composability.** Each pipeline can be used independently. If you already have backtest predictions from another system, you can feed them directly into ``EvaluationPipeline`` and ``AnalysisPipeline`` without touching ``BacktestPipeline`` at all.