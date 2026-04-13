The OpenSTEF BEAM Package
=========================

``openstef_beam`` is the evaluation arm of the OpenSTEF library. Its name is an acronym for
**Backtesting, Evaluation, Analysis and Metrics** — and that sequence is not arbitrary. It
describes the exact order in which BEAM processes a forecasting experiment, from replaying
historical data under realistic constraints all the way through to comparative benchmark
reports. If ``openstef_core`` provides the data abstractions and ``openstef_models`` provides
the transforms and model building blocks (see the sibling pages for those topics), then
``openstef_beam`` is what ties them together into a rigorous, reproducible assessment of how
well a forecasting model actually works.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

Why a Separate Evaluation Package?
-----------------------------------

A common mistake in time-series model evaluation is training on data that was not actually
available at the time a prediction would have been made. A model that has seen tomorrow's
weather in its training set will look far better than it ever could in production. BEAM is
designed around the principle that evaluation must mirror deployment. Every component in the
package enforces this constraint explicitly, using the ``VersionedTimeSeriesDataset`` from
``openstef_core`` to ensure that each prediction is made with only the information that
existed at the simulated prediction timestamp.

Backtesting
-----------

The backtesting module is the entry point for any BEAM workflow. ``BacktestPipeline`` replays
a historical period step by step, generating forecasts at regular intervals and retraining
the model on the schedule that would be used in production. The key abstraction that enforces
temporal integrity is ``RestrictedHorizonVersionedTimeSeries``, a wrapper around
``VersionedTimeSeriesDataset`` that refuses to expose data beyond the current simulation
horizon.

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   # Configure the simulation schedule
   config = BacktestConfig(
       prediction_sample_interval=15,   # generate a forecast every 15 minutes
       training_sample_interval=1440,   # retrain the model once per day (minutes)
   )

   # `forecaster` must implement BacktestForecasterMixin
   pipeline = BacktestPipeline(config=config, forecaster=forecaster)

   predictions: TimeSeriesDataset = pipeline.run(
       ground_truth=versioned_ground_truth,
       predictors=versioned_predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
       show_progress=True,
   )

``BacktestPipeline.run`` returns a plain ``TimeSeriesDataset`` containing every prediction
that was generated during the simulation window. This dataset is the input to the next stage.

Integrating Your Own Model
^^^^^^^^^^^^^^^^^^^^^^^^^^

To plug a custom model into the backtesting pipeline, implement the
``BacktestForecasterMixin`` interface. For models that can predict multiple time series
efficiently in a single call, ``BacktestBatchForecasterMixin`` is available and will be
preferred by the pipeline when detected.

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster import BacktestForecasterMixin
   from openstef_core.datasets import TimeSeriesDataset

   class MyForecaster(BacktestForecasterMixin):
       def train(self, dataset: TimeSeriesDataset) -> None:
           # Fit the model on the supplied historical window
           ...

       def predict(self, dataset: TimeSeriesDataset) -> TimeSeriesDataset:
           # Return probabilistic or point forecasts
           ...

Evaluation
----------

After backtesting produces a set of predictions, the evaluation module turns raw numbers into
structured performance reports. ``EvaluationPipeline`` segments the prediction dataset across
three independent dimensions simultaneously:

- **Lead times** — how does accuracy degrade as the forecast horizon grows from 1 hour to
  48 hours?
- **Time windows** — does performance differ between weekdays and weekends, or across
  seasons?
- **Filterings** — restrict evaluation to specific conditions such as peak-load periods or
  high-renewable-generation intervals.

For each combination of these dimensions, the pipeline computes the configured metrics and
packages the results into an ``EvaluationReport``, which contains a collection of
``EvaluationSubsetReport`` objects — one per segment.

.. code-block:: python

   from openstef_beam.evaluation import (
       EvaluationConfig,
       EvaluationPipeline,
       EvaluationReport,
       Window,
   )
   from openstef_beam.evaluation.models import Filtering, SubsetMetric
   from openstef_beam import evaluation as beam_eval

   config = EvaluationConfig(
       lead_times=[1, 4, 12, 24, 48],          # hours ahead
       windows=[Window.DAY, Window.WEEK],
       metric_providers=[
           beam_eval.metric_providers.MAEMetricProvider(),
           beam_eval.metric_providers.RMSEMetricProvider(),
       ],
   )

   pipeline = EvaluationPipeline(config=config)
   report: EvaluationReport = pipeline.run(
       predictions=predictions,
       ground_truth=ground_truth_dataset,
   )

The ``EvaluationReport`` is a plain data object — it carries no visualisation logic itself.
That responsibility belongs to the analysis module, which keeps the two concerns cleanly
separated.

Analysis
--------

The analysis module consumes one or more ``EvaluationReport`` objects and produces
human-readable outputs: charts, summary tables, and aggregated comparisons. An
``AnalysisPipeline`` is configured with an ``AnalysisConfig`` that specifies which
aggregations to compute and which scopes to report on.

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig, AnalysisPipeline, AnalysisScope

   analysis_config = AnalysisConfig(
       scope=AnalysisScope.FULL,
   )

   analysis_pipeline = AnalysisPipeline(config=analysis_config)
   analysis_pipeline.run(reports=[report])

When multiple ``EvaluationReport`` objects are passed — for example, one per model variant —
the analysis pipeline produces side-by-side comparisons, making it straightforward to
identify which model performs better at which lead time or under which conditions.

Benchmarking
------------

The benchmarking module is the highest-level abstraction in BEAM. ``BenchmarkPipeline``
orchestrates the entire backtesting → evaluation → analysis sequence across a collection of
forecasting *targets* (individual substations, wind parks, regions, etc.) and stores the
results through a pluggable ``BenchmarkStorage`` backend.

.. mermaid:: /diagrams/architecture/beam_diagram_2.mmd

The factory pattern is central to how ``BenchmarkPipeline`` handles heterogeneous targets.
Rather than requiring every target to use the same model configuration, a
``ForecasterFactory`` callable receives both the ``BenchmarkContext`` and the specific
``BenchmarkTarget``, allowing per-target customisation:

.. code-block:: python

   from openstef_beam.benchmarking import (
       BenchmarkContext,
       BenchmarkPipeline,
       BenchmarkTarget,
       ForecasterFactory,
       LocalBenchmarkStorage,
       SimpleTargetProvider,
   )
   from openstef_beam.backtesting import BacktestConfig
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.analysis import AnalysisConfig, AnalysisScope

   def create_forecaster(context: BenchmarkContext, target: BenchmarkTarget):
       # Customise model configuration per target if needed
       return MyForecaster(config=target.get_model_config())

   pipeline = BenchmarkPipeline(
       backtest_config=BacktestConfig(
           prediction_sample_interval=15,
           training_sample_interval=1440,
       ),
       evaluation_config=EvaluationConfig(lead_times=[1, 4, 12, 24]),
       analysis_config=AnalysisConfig(scope=AnalysisScope.FULL),
       target_provider=SimpleTargetProvider(targets=my_targets),
       storage=LocalBenchmarkStorage(path="./benchmark_results"),
   )

   pipeline.run(
       forecaster_factory=create_forecaster,
       run_name="baseline_v1",
       n_processes=4,          # parallelise across targets
   )

Storage Backends
^^^^^^^^^^^^^^^^

Three storage backends ship with the package, and the interface is open for extension:

- ``InMemoryBenchmarkStorage`` — results live only for the duration of the process; useful
  for interactive exploration or unit tests.
- ``LocalBenchmarkStorage`` — writes results to a local directory hierarchy.
- ``S3BenchmarkStorage`` — writes results to an S3-compatible object store, suitable for
  shared team workflows or CI pipelines.

Callbacks and Observability
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``BenchmarkCallback`` provides lifecycle hooks that fire at key points in the benchmark run.
The ``BenchmarkCallbackManager`` composes multiple callbacks together. A
``StrictExecutionCallback`` is included out of the box: it converts any per-target failure
into an immediate exception rather than silently skipping the target, which is the safer
default for automated pipelines.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkCallbackManager, StrictExecutionCallback

   callbacks = [StrictExecutionCallback()]
   # Pass to BenchmarkPipeline via the `callbacks` argument

Comparing Multiple Runs
^^^^^^^^^^^^^^^^^^^^^^^

``BenchmarkComparisonPipeline`` and the ``read_evaluation_reports`` utility make it easy to
load previously stored results and compare them across runs — for instance, to confirm that a
model change improved performance before promoting it to production.

.. code-block:: python

   from openstef_beam.benchmarking import read_evaluation_reports, BenchmarkComparisonPipeline

   reports = read_evaluation_reports(storage=LocalBenchmarkStorage(path="./benchmark_results"))
   comparison = BenchmarkComparisonPipeline().run(reports=reports)

Package Dependencies
--------------------

``openstef_beam`` sits at the top of the OpenSTEF dependency graph. It imports from both
sibling packages but neither of them imports from BEAM, keeping the dependency direction
clean:

- **openstef_core** supplies ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``,
  ``BaseConfig``, ``Quantile``, and the ``run_parallel`` utility. See the :doc:`core` page
  for a detailed treatment of the dataset abstractions.
- **openstef_models** supplies the transform primitives and model building blocks that
  concrete forecaster implementations are typically built from. See the :doc:`models` page
  for details on the transforms module.

.. note::

   ``openstef_beam`` does not mandate any specific model implementation. The
   ``BacktestForecasterMixin`` interface is intentionally thin, so you can wrap a
   scikit-learn pipeline, a PyTorch model, or any other estimator without modifying the
   evaluation infrastructure.

Summary
-------

BEAM provides a complete, leakage-free evaluation framework as a library you compose into
your own workflows. The four stages — backtesting, evaluation, analysis, benchmarking — can
be used independently or chained together through ``BenchmarkPipeline``. The pluggable
design (factory pattern for models, swappable storage backends, composable callbacks) means
the framework adapts to a wide range of operational contexts without requiring changes to
the core evaluation logic.