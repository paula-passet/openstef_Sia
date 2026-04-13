The OpenSTEF BEAM Package
=========================

**openstef_beam** is the evaluation arm of the OpenSTEF library. Its name is an acronym for
**B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics — and that sequence
describes exactly how the package is meant to be used. Where :doc:`core <core>` provides the
foundational data structures and :doc:`models <models>` provides the forecasting transforms,
BEAM provides the tooling to answer the harder question: *how well does a model actually
perform under real-world conditions?*

This page covers the internal architecture of ``openstef_beam``, the design choices that
prevent data leakage during evaluation, and how to wire the four stages together — from a
single backtest run up to a full multi-target benchmark study.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd


Why Versioned Data Matters
--------------------------

A naive backtest loads a historical dataset and asks the model to predict each timestep
using the full dataset — including data that would not yet have existed at prediction time.
This *data leakage* produces optimistic metrics that do not survive contact with production.

BEAM avoids this by requiring that both ground-truth and predictor datasets are supplied as
``VersionedTimeSeriesDataset`` objects (defined in ``openstef_core``). Each version of the
dataset represents the state of the world as it was known at a specific point in time.
``RestrictedHorizonVersionedTimeSeries`` wraps these versioned datasets and enforces a
*horizon* — a hard cutoff that prevents the forecaster from seeing any data timestamped
after the moment the prediction is being simulated.

The result is that every prediction in a BEAM backtest is made with exactly the information
that would have been available in a live deployment. Retraining events are also replayed on
schedule, so the evaluation captures model drift and the cost of periodic retraining.


Stage 1 — Backtesting
---------------------

The ``backtesting`` sub-package contains ``BacktestPipeline``, the engine that replays
history. You configure it with a ``BacktestConfig`` (prediction interval, training interval,
and related scheduling parameters) and hand it a forecaster that implements
``BacktestForecasterMixin``.

.. code-block:: python

    from datetime import datetime
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=...,   # e.g. timedelta(minutes=15)
        training_period=...,              # how far back to train
        retrain_interval=...,             # how often to retrain
    )

    pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

    predictions = pipeline.run(
        ground_truth=versioned_ground_truth,   # VersionedTimeSeriesDataset
        predictors=versioned_predictors,       # VersionedTimeSeriesDataset
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
        show_progress=True,
    )

``pipeline.run()`` returns a plain ``TimeSeriesDataset`` containing the model's predictions
for every simulated timestep in the requested window. This dataset is the input to the next
stage.

To integrate a custom model, implement ``BacktestForecasterMixin``. For batch-capable
models, implement ``BacktestBatchForecasterMixin`` instead; the pipeline detects the
interface automatically and uses the more efficient batch path.

.. note::

   ``BacktestPipeline`` validates that the ``prediction_sample_interval`` declared in
   ``BacktestConfig`` matches the interval reported by the forecaster. A ``ValueError`` is
   raised at construction time if they disagree, preventing silent misconfiguration.


Stage 2 — Evaluation
--------------------

Raw predictions are only useful once they are compared against ground truth across
meaningful slices of time. The ``evaluation`` sub-package does this through
``EvaluationPipeline``, which segments the prediction dataset along three orthogonal
dimensions:

- **Lead times** — how does accuracy degrade as the forecast horizon grows from 1 hour to
  48 hours?
- **Time windows** — does the model perform differently on weekdays versus weekends, or
  across seasons?
- **Filters** — restrict evaluation to specific conditions such as peak-load hours or
  high-generation periods.

Each combination of dimensions produces an ``EvaluationSubsetReport``. The collection of
all subset reports is wrapped in an ``EvaluationReport``, which is a structured, serialisable
object that can be stored, compared, and fed into the analysis stage.

.. code-block:: python

    from openstef_beam.evaluation import (
        EvaluationPipeline,
        EvaluationConfig,
        Window,
        Filtering,
    )

    eval_config = EvaluationConfig(
        windows=[
            Window(name="weekdays", ...),
            Window(name="weekends", ...),
        ],
        filterings=[
            Filtering(name="peak_hours", ...),
        ],
        lead_times=[1, 4, 12, 24, 48],   # hours ahead
    )

    eval_pipeline = EvaluationPipeline(config=eval_config)
    report = eval_pipeline.run(
        predictions=predictions,
        ground_truth=versioned_ground_truth,
    )

The ``metric_providers`` module inside ``openstef_beam.evaluation`` supplies the built-in
metric implementations (MAE, RMSE, skill scores, and probabilistic metrics for quantile
forecasts). Custom metrics can be added by implementing the ``SubsetMetric`` interface and
passing them through ``EvaluationConfig``.


Stage 3 — Analysis
------------------

An ``EvaluationReport`` is rich but dense. The ``analysis`` sub-package transforms it into
human-readable artefacts: charts, summary tables, and comparative views. The
``AnalysisPipeline`` is configured with an ``AnalysisConfig`` that specifies which
visualisations to produce and at what granularity.

Analysis is intentionally decoupled from evaluation: you can re-run analysis with a
different configuration without repeating the (potentially expensive) backtest and
evaluation steps, provided the ``EvaluationReport`` has been persisted to storage.


Stage 4 — Benchmarking
----------------------

The three stages above evaluate a single model on a single target. In practice, energy
forecasting involves many targets — substations, solar parks, wind farms, industrial
consumers — and multiple candidate models. The ``benchmarking`` sub-package automates the
entire workflow at scale.

``BenchmarkPipeline`` is the top-level orchestrator. It accepts:

- A ``TargetProvider`` that supplies the list of targets and their associated datasets.
- A ``ForecasterFactory`` — a callable ``(BenchmarkContext, target) -> BacktestForecasterMixin``
  that creates a target-specific forecaster on demand.
- A ``BenchmarkStorage`` backend for persisting results.
- Optional ``BenchmarkCallback`` hooks for progress reporting, alerting, or custom
  post-processing.

.. code-block:: python

    from openstef_beam.benchmarking import (
        BenchmarkPipeline,
        BenchmarkContext,
        LocalBenchmarkStorage,
        SimpleTargetProvider,
    )
    from openstef_beam.backtesting import BacktestConfig
    from openstef_beam.evaluation import EvaluationConfig
    from openstef_beam.analysis import AnalysisConfig  # configure as needed

    storage = LocalBenchmarkStorage(path="./benchmark_results")

    pipeline = BenchmarkPipeline(
        backtest_config=backtest_config,
        evaluation_config=eval_config,
        analysis_config=analysis_config,
        target_provider=SimpleTargetProvider(targets=my_targets),
        storage=storage,
    )

    def create_forecaster(context: BenchmarkContext, target):
        # Customise model per target if needed
        return MyForecaster(config=target.get_model_config())

    pipeline.run(
        forecaster_factory=create_forecaster,
        run_name="q1_2024_baseline",
        n_processes=4,
    )

After the run, ``read_evaluation_reports`` can load persisted reports back from storage for
offline comparison:

.. code-block:: python

    from openstef_beam.benchmarking import read_evaluation_reports

    reports = read_evaluation_reports(storage=storage, run_name="q1_2024_baseline")

To compare two benchmark runs against each other, ``BenchmarkComparisonPipeline`` accepts
two sets of reports and produces a differential analysis, making it straightforward to
quantify whether a model change represents a genuine improvement across the target
population.

Storage backends ship in three flavours — ``InMemoryBenchmarkStorage`` for testing,
``LocalBenchmarkStorage`` for single-machine workflows, and ``S3BenchmarkStorage`` for
cloud-based or team-shared result repositories. All three implement the same
``BenchmarkStorage`` interface, so switching backends requires only a one-line change.


Package Dependencies
--------------------

BEAM sits at the top of the OpenSTEF dependency graph within the library:

- **openstef_core** supplies ``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``, and
  ``BaseConfig``. Every pipeline in BEAM consumes these types at its boundaries. See
  :doc:`core` for a detailed treatment of the dataset classes.
- **openstef_models** supplies the transform-based forecasting models that implement
  ``BacktestForecasterMixin``. The mixin interface is deliberately thin so that any model
  — including those built outside OpenSTEF — can be plugged in. See :doc:`models` for
  details on the transforms module and how models are constructed.

BEAM itself has no hard dependency on a specific model implementation. The
``ForecasterFactory`` pattern in ``BenchmarkPipeline`` means the choice of model is
deferred to call time, keeping evaluation logic cleanly separated from modelling logic.


Extending BEAM
--------------

The four primary extension points are:

- **Custom forecasters** — implement ``BacktestForecasterMixin`` (or the batch variant).
- **Custom metrics** — implement ``SubsetMetric`` and register via ``EvaluationConfig``.
- **Custom visualisations** — implement the analysis plugin interface and pass to
  ``AnalysisConfig``.
- **Custom target providers** — implement ``TargetProvider`` to load targets from any
  data source (databases, object stores, configuration files).

Callbacks (``BenchmarkCallback``) provide a hook into the benchmarking loop without
requiring subclassing. ``StrictExecutionCallback`` is a built-in callback that converts
per-target errors into hard failures, useful in CI pipelines where silent degradation is
unacceptable.