The openstef_beam Package
=========================

The ``openstef-beam`` package provides a structured evaluation framework for short-term energy forecasting. It defines a hierarchy of composable pipelines — backtesting, evaluation, analysis, and benchmarking — that together orchestrate complete model comparison studies across multiple forecasting targets. The name *BEAM* reflects its role as the load-bearing structure that holds an evaluation workflow together.

This page covers the pipeline architecture, how to implement the ``BacktestForecasterMixin`` interface to plug in any model, and how the optional ``baselines`` extra brings in predefined forecasters built on ``openstef-models`` and ``openstef-meta``.

.. note::

   ``openstef-beam`` depends only on ``openstef-core``. It has no hard dependency on ``openstef-models`` or ``openstef-meta``, so you can evaluate entirely custom or third-party models without pulling in the full OpenSTEF model stack.

Pipeline Architecture
---------------------

BEAM organises evaluation into four pipeline classes with a clear separation of concerns:

- **BacktestPipeline** — simulates operational forecasting over a historical window, preventing data leakage by enforcing strict temporal boundaries at each prediction step.
- **EvaluationPipeline** — compares backtest output against ground truth using configurable metrics and produces an ``EvaluationReport``.
- **AnalysisPipeline** — aggregates evaluation reports across targets and groups, producing summaries at configurable scopes (global, group, individual target).
- **BenchmarkPipeline** — orchestrates all three phases across multiple models and targets, managing parallel execution and result storage.

.. mermaid:: /diagrams/architecture/beam_diagram_1.mmd

The separation means each stage can be used independently. You can run a ``BacktestPipeline`` in isolation to generate raw forecast series, then feed those results into ``EvaluationPipeline`` later, or skip straight to ``AnalysisPipeline`` if reports already exist on disk.

The BacktestForecasterMixin Interface
--------------------------------------

The only contract ``BacktestPipeline`` imposes on a model is the ``BacktestForecasterMixin`` interface from ``openstef_beam.backtesting``. Implementing it is straightforward: provide a ``predict`` method (or ``predict_batch`` for the batch variant) and a ``retrain`` method that respects the temporal window passed to it.

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestForecasterMixin, BacktestConfig
   from openstef_beam.backtesting import BacktestPipeline
   from openstef_core.datasets import TimeSeriesDataset

   class MyForecaster(BacktestForecasterMixin):
       """Minimal custom forecaster compatible with BacktestPipeline."""

       prediction_sample_interval = 15  # minutes

       def retrain(self, dataset: TimeSeriesDataset, available_before: datetime) -> None:
           # Fit your model using only data available before the given timestamp.
           ...

       def predict(self, dataset: TimeSeriesDataset, at: datetime) -> float:
           # Return a single-step forecast for the given timestamp.
           ...

   config = BacktestConfig(prediction_sample_interval=15)
   forecaster = MyForecaster()

   pipeline = BacktestPipeline(
       config=config,
       forecaster=forecaster,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
   )
   backtest_result = pipeline.run(dataset)

The ``prediction_sample_interval`` on both the config and the forecaster must agree; ``BacktestPipeline`` raises a ``ValueError`` at construction time if they differ, catching misconfiguration early.

Because the interface is defined entirely in ``openstef-core`` types (``TimeSeriesDataset``, plain ``datetime``), any scikit-learn estimator, PyTorch model, or statistical baseline can be wrapped without importing anything from ``openstef-models``.

Running a Full Benchmark
------------------------

``BenchmarkPipeline`` wires together target acquisition, backtesting, evaluation, and analysis. You supply a ``TargetProvider`` that yields benchmark targets and a ``ForecasterFactory`` that constructs a forecaster for each target–model combination.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkContext
   from openstef_beam.benchmarking.storage import BenchmarkStorage
   from openstef_beam.benchmarking.target_provider import TargetProvider
   from openstef_beam.analysis import AnalysisConfig, AnalysisScope

   # Implement TargetProvider to yield your forecasting targets.
   class MyTargetProvider(TargetProvider):
       def get_targets(self):
           return [...]  # list of BenchmarkTarget instances

   # ForecasterFactory maps a target to a forecaster instance.
   def my_factory(target, model_name: str):
       if model_name == "my_model":
           return MyForecaster()
       raise ValueError(f"Unknown model: {model_name}")

   storage = BenchmarkStorage(base_path="./benchmark_results")
   analysis_config = AnalysisConfig(scope=AnalysisScope.GLOBAL)

   pipeline = BenchmarkPipeline(
       target_provider=MyTargetProvider(),
       forecaster_factory=my_factory,
       model_names=["my_model"],
       storage=storage,
       analysis_config=analysis_config,
   )
   pipeline.run()

Results are persisted by ``BenchmarkStorage`` after each target completes, so a partial run can be resumed and individual ``EvaluationReport`` objects can be inspected without re-running the full study.

Comparing Benchmark Runs
^^^^^^^^^^^^^^^^^^^^^^^^

``BenchmarkComparisonPipeline`` operates on already-stored results, making it cheap to re-analyse without re-running expensive backtests. This is useful when tuning analysis parameters or adding a new model to an existing study.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.analysis import AnalysisConfig, AnalysisScope

   comparison = BenchmarkComparisonPipeline(
       run_names=["baseline_run", "improved_run"],
       storage=storage,
       analysis_config=AnalysisConfig(scope=AnalysisScope.GROUP),
   )
   comparison.run()

The ``AnalysisScope`` controls the granularity of the output: ``GLOBAL`` produces a single aggregate summary, ``GROUP`` breaks results down by target group, and the default target-level scope reports per-target metrics.

The ``baselines`` Extra
-----------------------

Installing ``openstef-beam[baselines]`` pulls in ``openstef-models`` and ``openstef-meta`` and unlocks the ``openstef_beam.benchmarking.baselines`` sub-package. This provides ready-made ``BacktestForecasterMixin`` implementations built on the full OpenSTEF model stack, so you can benchmark your own model against established OpenSTEF forecasters without writing the integration yourself.

.. code-block:: bash

   pip install openstef-beam[baselines]

The flagship baseline is ``OpenSTEF4BacktestForecaster``, which wraps an ``openstef-models`` ``ForecastingWorkflow`` and handles the retraining schedule, feature engineering, and horizon-restricted data access automatically.

.. code-block:: python

   # Requires openstef-beam[baselines]
   from openstef_beam.benchmarking.baselines.openstef4 import OpenSTEF4BacktestForecaster

   openstef_forecaster = OpenSTEF4BacktestForecaster(
       coordinate=...,   # pydantic_extra_types Coordinate
       # additional workflow config fields
   )

   pipeline = BenchmarkPipeline(
       target_provider=MyTargetProvider(),
       forecaster_factory=lambda target, name: openstef_forecaster,
       model_names=["openstef4"],
       storage=storage,
       analysis_config=analysis_config,
   )
   pipeline.run()

A predefined benchmark runner for the Liander 2024 dataset is also available:

.. code-block:: python

   from openstef_beam.benchmarking.benchmarks import create_liander2024_benchmark_runner

   runner = create_liander2024_benchmark_runner()
   runner.run()

.. note::

   If you import from ``openstef_beam.benchmarking.baselines`` without the ``baselines`` extra installed, ``openstef-core`` raises a ``MissingExtraError`` with a clear installation hint rather than a bare ``ImportError``.

Temporal Integrity and Data Leakage Prevention
-----------------------------------------------

A recurring concern in backtesting is accidentally training on future data. ``BacktestPipeline`` addresses this through ``RestrictedHorizonVersionedTimeSeries``, a wrapper around ``openstef-core``'s ``TimeSeriesDataset`` that gates every data access call with an ``available_before`` timestamp. Any attempt to read data beyond that boundary raises an error at the dataset level, not silently returning stale or future values.

This means the temporal integrity guarantee is enforced in the data layer, not left to the forecaster implementation. A ``BacktestForecasterMixin`` implementor cannot accidentally leak future data even if they forget to filter it themselves.

For more on the dataset types that underpin this mechanism, see the :doc:`core` page.

Analysis and Metrics
--------------------

``EvaluationPipeline`` accepts a configurable set of metrics. The resulting ``EvaluationReport`` carries per-horizon and aggregate scores that ``AnalysisPipeline`` can then roll up across targets and groups.

``AnalysisPipeline`` supports three aggregation levels via ``AnalysisAggregation`` and can be scoped to a subset of targets using ``TargetName`` and ``GroupName`` filters. This makes it straightforward to answer questions like "how does model A perform on substations in region X compared to region Y?" without re-running any backtests.

.. note:: [VISUALIZATION: Heatmap of per-target evaluation metrics (e.g. MAE by forecast horizon) produced by AnalysisPipeline at GROUP scope, with targets on one axis and horizon buckets on the other.]

Related Pages
-------------

- :doc:`core` — the ``TimeSeriesDataset``, validated dataset hierarchy, and ``openstef-core`` types that BEAM pipelines consume.
- :doc:`models` — the transform-organised model presets in ``openstef-models`` used by the ``baselines`` extra.
- :doc:`meta` — the ``EnsembleForecastingModel`` in ``openstef-meta``, also available as a baseline forecaster.