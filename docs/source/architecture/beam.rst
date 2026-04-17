OpenSTEF BEAM: Backtesting, Evaluation, Analysis and Metrics
=============================================================

The ``openstef_beam`` package provides a rigorous framework for evaluating energy
forecasting models under realistic conditions. BEAM — **B**\ acktesting,
**E**\ valuation, **A**\ nalysis, **M**\ etrics — orchestrates the complete
workflow from raw historical data to scored, visualised results, while
guaranteeing that no future information leaks into model training or prediction.

This page covers the four pipeline stages that make up BEAM, how they compose
into a full benchmark, and how to plug in any forecasting model — including
models that have nothing to do with the rest of the OpenSTEF ecosystem.

.. note::

   ``openstef_beam`` depends only on ``openstef_core``. The optional
   ``baselines`` extra (``pip install openstef-beam[baselines]``) pulls in
   ``openstef-models`` and ``openstef-meta``, which provide ready-made
   benchmark forecasters. See :doc:`models` and :doc:`meta` for details on
   those packages.

.. note:: [DIAGRAM: Pipeline flow showing BacktestPipeline → EvaluationPipeline → AnalysisPipeline as sequential stages, with BenchmarkPipeline as an outer orchestrator that loops over multiple (model, target) combinations and fans out to all three inner pipelines in parallel]


The Four Pipeline Stages
------------------------

BEAM decomposes model evaluation into four clearly separated concerns.

**BacktestPipeline** replays history day by day. At each step it exposes only
the data that would have been available at that moment in production, retrains
the model on the configured schedule, and collects the resulting predictions
into a ``TimeSeriesDataset``. This simulation prevents the data leakage that
plagues simpler train/test splits.

**EvaluationPipeline** takes the backtest predictions alongside the ground
truth and computes a configurable set of metrics — R², pinball loss, observed
probability, and any custom ``MetricProvider`` you register. Results are
collected into an ``EvaluationReport`` that records scores broken down by lead
time, making it straightforward to ask "how does accuracy degrade as the
horizon grows from one hour to 48 hours?"

**AnalysisPipeline** turns the evaluation report into human-readable output:
interactive HTML plots, per-group summaries, and per-target detail pages. The
scope of the analysis (global, group, or individual target) is controlled by
``AnalysisScope``.

**BenchmarkPipeline** is the top-level orchestrator. It iterates over a
collection of *targets* (energy assets or locations), runs all three stages for
each (model, target) pair, and stores results in a ``BenchmarkStorage``
directory layout that downstream comparison tools can read directly. Parallel
execution across targets is controlled by the ``n_processes`` argument.


The ``BacktestForecasterMixin`` Interface
-----------------------------------------

The only contract BEAM imposes on a forecasting model is the
``BacktestForecasterMixin``. Any class — scikit-learn estimator, PyTorch
module, statistical model, or hand-crafted heuristic — can participate in a
BEAM benchmark as long as it satisfies this interface.

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
       """Predict the median of recent observations — a simple but honest baseline."""

       config = BacktestForecasterConfig(
           requires_training=True,
           predict_sample_interval=timedelta(minutes=15),
           predict_length=timedelta(hours=48),
           predict_min_length=timedelta(hours=1),
           predict_context_length=timedelta(days=14),
           predict_context_min_coverage=0.5,
           training_context_length=timedelta(days=60),
           training_context_min_coverage=0.5,
       )

       @property
       def quantiles(self) -> list[Quantile]:
           return [Q(0.05), Q(0.50), Q(0.95)]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           window = data.get_window(
               data.horizon - self.config.training_context_length,
               data.horizon,
               available_before=data.horizon,
           )
           self._median = float(window.load.median())

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset | None:
           index = pd.date_range(
               data.horizon,
               periods=int(self.config.predict_length / self.config.predict_sample_interval),
               freq=self.config.predict_sample_interval,
           )
           return TimeSeriesDataset(
               pd.DataFrame(
                   {
                       "quantile_P05": self._median * 0.8,
                       "quantile_P50": self._median,
                       "quantile_P95": self._median * 1.2,
                   },
                   index=index,
               )
           )

The key design point is ``RestrictedHorizonVersionedTimeSeries``: it
enforces the no-lookahead guarantee at the data-access level. Calling
``data.get_window(start, end, available_before=data.horizon)`` will raise if
you accidentally request data from the future, making it impossible to
accidentally cheat.


Running a Benchmark
-------------------

With a forecaster in hand, the simplest path to a full benchmark is
``BenchmarkPipeline``. The example below uses the built-in Liander 2024 dataset
(auto-downloaded from HuggingFace) so you can run it immediately without
providing your own data.

.. code-block:: python

   import logging
   import os
   from pathlib import Path

   # Prevent thread contention when running multiple targets in parallel
   os.environ["OMP_NUM_THREADS"] = "1"
   os.environ["OPENBLAS_NUM_THREADS"] = "1"
   os.environ["MKL_NUM_THREADS"] = "1"

   from openstef_beam.benchmarking import BenchmarkContext, LocalBenchmarkStorage
   from openstef_beam.benchmarking.benchmark_pipeline import BenchmarkPipeline

   logging.basicConfig(level=logging.INFO, format="[%(asctime)s][%(levelname)s] %(message)s")

   OUTPUT_PATH = Path("./benchmark_results")

   # A forecaster factory receives a BenchmarkContext (target metadata, storage
   # paths, etc.) and returns a BacktestForecasterMixin instance.
   def create_median_forecaster(context: BenchmarkContext) -> MedianForecaster:
       return MedianForecaster()

   # Use the built-in Liander 2024 runner as the pipeline base
   from openstef_beam.benchmarking.liander2024 import create_liander2024_benchmark_runner

   pipeline = create_liander2024_benchmark_runner(
       storage=LocalBenchmarkStorage(OUTPUT_PATH),
   )

   # Run the median forecaster across all targets, using 4 parallel processes
   pipeline.run(
       forecaster_factory=create_median_forecaster,
       run_name="median_baseline",
       n_processes=4,
   )

Results land in ``./benchmark_results/median_baseline/`` with one subfolder per
target containing ``predictions.parquet``, an evaluation JSON, and HTML analysis
plots.


Using the ``baselines`` Extra
------------------------------

Installing ``openstef-beam[baselines]`` makes pre-built benchmark forecasters
available. These wrap the full ``openstef-models`` training workflow — feature
engineering, hyperparameter defaults, and ensemble stacking from
``openstef-meta`` — behind the same ``BacktestForecasterMixin`` interface.

.. code-block:: python

   # pip install openstef-beam[baselines]
   from openstef_beam.benchmarking.baselines.openstef4 import (
       create_openstef4_preset_backtest_forecaster,
   )
   from openstef_models.presets import ForecastingWorkflowConfig
   from openstef_core.types import Q

   def create_gblinear_forecaster(context: BenchmarkContext):
       return create_openstef4_preset_backtest_forecaster(
           ForecastingWorkflowConfig(model_type="gblinear"),
           quantiles=[Q(0.05), Q(0.50), Q(0.95)],
       )

   pipeline.run(
       forecaster_factory=create_gblinear_forecaster,
       run_name="gblinear",
       n_processes=4,
   )

Because both ``median_baseline`` and ``gblinear`` write into the same
``OUTPUT_PATH``, the comparison pipeline can pick them up automatically:

.. code-block:: python

   from openstef_beam.benchmarking.benchmark_comparison_pipeline import (
       BenchmarkComparisonPipeline,
   )
   from openstef_beam.analysis import AnalysisConfig, AnalysisScope

   comparison = BenchmarkComparisonPipeline(
       storage=LocalBenchmarkStorage(OUTPUT_PATH),
       analysis_config=AnalysisConfig(scope=AnalysisScope.GLOBAL),
   )
   comparison.run(
       run_names=["median_baseline", "gblinear"],
   )

Side-by-side HTML plots are written to ``./benchmark_results_comparison/``.


Bringing Your Own Data
-----------------------

The ``SimpleTargetProvider`` base class is the integration point for custom
datasets. Override two methods to point BEAM at your own parquet files:

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking.target_provider import SimpleTargetProvider
   from openstef_beam.benchmarking.models import BenchmarkTarget


   class MyTargetProvider(SimpleTargetProvider):
       def _get_measurements_path_for_target(self, target: BenchmarkTarget) -> Path:
           return Path(f"./data/measurements/{target.name}.parquet")

       def _get_weather_path_for_target(self, target: BenchmarkTarget) -> Path:
           return Path(f"./data/weather/{target.group_name}.parquet")

Targets themselves are declared in a YAML file and loaded via the provider.
Once the provider is in place, pass it to ``BenchmarkPipeline`` and the rest of
the workflow is identical to the built-in dataset path.


Evaluating Pre-existing Forecasts
-----------------------------------

If you already have predictions from an external system — a commercial forecast
service, a legacy model, or a manual process — you can skip the backtesting
stage entirely and run only evaluation and analysis. Place your prediction
parquets in the expected directory layout:

.. code-block:: text

   benchmark_results/MyForecasts/
   └── backtest/
       └── <group_name>/
           └── <target_name>/
               └── predictions.parquet

Each parquet must contain a ``DatetimeIndex`` named ``timestamp``, an
``available_at`` column recording when each forecast was generated, and one
column per quantile named with the ``quantile_PXX`` convention (e.g.
``quantile_P05``, ``quantile_P50``, ``quantile_P95``). The ``available_at``
column is what enables lead-time filtering: BEAM uses it to reconstruct which
forecasts were genuinely available at each decision point.

With the files in place, call ``BenchmarkPipeline.run_evaluation_for_target``
and ``run_analysis_for_target`` directly, or use the ``evaluate_existing_forecasts``
example script from the repository as a starting template.


Lead-time Analysis
-------------------

A distinctive feature of BEAM's evaluation layer is first-class support for
lead-time analysis. Because every prediction row carries an ``available_at``
timestamp alongside the target ``timestamp``, the ``EvaluationPipeline`` can
slice metrics by how far in advance a forecast was made. This answers the
operationally critical question: "Is our day-ahead forecast good enough, and
where does accuracy start to degrade?"

The ``SubsetMetric`` wrapper lets you apply any metric to a specific lead-time
window without writing custom filtering logic:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.evaluation import EvaluationConfig, SubsetMetric
   from openstef_beam.evaluation.metric_providers import R2Provider

   config = EvaluationConfig(
       metrics=[
           SubsetMetric(
               metric=R2Provider(),
               lead_time_min=timedelta(hours=1),
               lead_time_max=timedelta(hours=24),
               name="R2_day_ahead",
           ),
           SubsetMetric(
               metric=R2Provider(),
               lead_time_min=timedelta(hours=24),
               lead_time_max=timedelta(hours=48),
               name="R2_two_day_ahead",
           ),
       ]
   )


Summary
-------

``openstef_beam`` is a self-contained evaluation library. Its core dependency
is ``openstef_core`` alone, so it imposes no obligation to use OpenSTEF models.
Any forecaster that implements ``BacktestForecasterMixin`` — two methods
(``fit``, ``predict``) and a ``config`` attribute — gains access to the full
BEAM workflow: leak-proof backtesting, standardised metric computation,
interactive analysis reports, and multi-model comparison. The optional
``baselines`` extra layers in the OpenSTEF model ecosystem for teams that want
ready-made benchmark forecasters without building them from scratch.

For the validated dataset abstractions that BEAM's pipelines consume, see
:doc:`core`. For the model transforms and presets available through the
``baselines`` extra, see :doc:`models` and :doc:`meta`.