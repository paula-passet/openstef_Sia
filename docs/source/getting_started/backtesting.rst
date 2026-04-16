Backtesting Models with Historical Data
=======================================

Backtesting is the process of evaluating a forecasting model by replaying historical data as if
predictions were being made in real time. Rather than training on the full dataset and scoring
against the same data, a backtest simulates the operational environment: the model sees only
past data at each prediction step, retrains on a schedule, and produces forecasts that can be
compared against what actually happened.

This page walks through the complete backtesting workflow in OpenSTEF — from configuring and
running a backtest, to computing evaluation metrics, to comparing multiple models side by side.
If you haven't yet produced your first forecast, start with :doc:`first_forecast` before
continuing here.

.. note::

   Backtesting functionality is provided by the ``openstef_beam`` package. Make sure it is
   installed alongside the core library. See :doc:`installation` for details.


Why Backtesting Matters
-----------------------

A naive evaluation — train on historical data, score on the same data — almost always
overstates real-world performance. OpenSTEF's backtesting library prevents this by enforcing
strict temporal constraints:

- **No data leakage.** Each prediction is made using only data that would have been available
  at that moment in time.
- **Realistic retraining schedules.** The model is retrained periodically, mirroring how it
  would be operated in production.
- **Fair model comparison.** Every model under evaluation is tested under identical conditions,
  making metric differences meaningful.

The result is an honest estimate of how a model will behave once deployed.

.. note:: [DIAGRAM: Timeline showing alternating train and predict events across a historical
   period, with a sliding "available data" window that grows forward in time.]


Configuring the Backtest
------------------------

The entry point is ``BacktestPipeline``, which is initialised with a ``BacktestConfig`` and a
forecaster that implements the ``BacktestForecasterMixin`` interface.

``BacktestConfig`` controls the three key timing parameters:

- ``prediction_sample_interval`` — the resolution of each forecast (default: 15 minutes).
- ``predict_interval`` — how often a new forecast is generated (default: every 6 hours).
- ``train_interval`` — how often the model is retrained on fresh data (default: every 7 days).

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
       align_time=time.fromisoformat("00:00+00"),
   )

.. note::

   ``prediction_sample_interval`` must match the ``predict_sample_interval`` defined in your
   forecaster's own configuration. ``BacktestPipeline`` raises a ``ValueError`` at construction
   time if these values differ, so mismatches are caught early.


Running the Backtest
--------------------

Once configured, call ``BacktestPipeline.run()`` with your historical ground-truth series and
predictor features. Both arguments are ``VersionedTimeSeriesDataset`` objects — datasets that
carry a timestamp recording when each row of data became available, which is what allows the
pipeline to enforce the "no future data" constraint.

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   # Assume `my_forecaster`, `ground_truth`, and `predictors` are already prepared.
   pipeline = BacktestPipeline(
       config=config,
       forecaster=my_forecaster,
   )

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1, tzinfo=timezone.utc),
       end=datetime(2023, 12, 31, tzinfo=timezone.utc),
       show_progress=True,   # displays a tqdm progress bar
   )

The method returns a ``TimeSeriesDataset`` containing every forecast produced during the
backtesting period. Each row is stamped with both the forecast timestamp and the time at which
it was generated, preserving the full temporal versioning needed for downstream evaluation.

Passing ``start=None`` or ``end=None`` tells the pipeline to use the earliest or latest
timestamp present in the ground-truth data, respectively.


Evaluation Metrics
------------------

Raw predictions become useful only when summarised into metrics. OpenSTEF ships a set of
metric providers under ``openstef_beam.evaluation.metric_providers``. Each provider is a
self-contained object that knows how to compute one metric from a prediction/ground-truth pair.

The most commonly used providers are:

- ``MAEProvider`` — Mean Absolute Error, the simplest absolute error measure.
- ``RMAEProvider`` — Relative MAE, normalised by the inter-quantile range of the target so
  that errors are comparable across sites with different scales.
- ``RMAEPeakHoursProvider`` — rMAE restricted to peak hours (08:00–20:00), useful when
  grid stress during high-demand periods is the primary concern.
- ``MAPEProvider`` — Mean Absolute Percentage Error.
- ``R2Provider`` — Coefficient of determination (R²).
- ``RCRPSProvider`` — Relative Continuous Ranked Probability Score, the standard metric for
  probabilistic (quantile) forecasts.

.. code-block:: python

   from openstef_beam.evaluation.metric_providers import (
       MAEProvider,
       RMAEProvider,
       RCRPSProvider,
   )

   metrics = [
       MAEProvider(),
       RMAEProvider(lower_quantile=0.01, upper_quantile=0.99),
       RCRPSProvider(lower_quantile=0.01, upper_quantile=0.99),
   ]

Metric providers are passed to the evaluation and benchmarking layers described below; you
do not call them directly on raw arrays in normal usage.

.. note::

   ``RMAEProvider`` accepts an optional ``norm_value`` parameter. Supply a pre-computed
   normalisation constant when you want metrics to be comparable across separate evaluation
   runs that may have seen different data ranges.


Storing and Comparing Results
------------------------------

For a single model, inspecting the returned ``TimeSeriesDataset`` is often sufficient. When
you want to compare several models — different algorithms, different hyperparameter sets, or
before/after a model update — OpenSTEF provides a structured benchmarking layer built around
``BenchmarkComparisonPipeline``.

The workflow has two stages:

1. **Run each model independently** and persist its results to a ``LocalBenchmarkStorage``
   directory.
2. **Load all results** into ``BenchmarkComparisonPipeline`` and generate comparative
   visualisations.

.. code-block:: python

   from pathlib import Path
   from typing import cast
   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.benchmarking.storage import LocalBenchmarkStorage
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       GroupedTargetMetricVisualization,
       SummaryTableVisualization,
   )

   # Point to the directories produced by each benchmark run.
   run_storages = {
       "Baseline": LocalBenchmarkStorage(base_path=Path("./results/Baseline")),
       "GBLinear":  LocalBenchmarkStorage(base_path=Path("./results/GBLinear")),
       "XGBoost":   LocalBenchmarkStorage(base_path=Path("./results/XGBoost")),
   }

   # Verify that all runs have been completed before comparing.
   for name, storage in run_storages.items():
       base_path = cast(LocalBenchmarkStorage, storage).base_path
       if not base_path.exists():
           raise FileNotFoundError(
               f"Benchmark directory not found for '{name}': {base_path}. "
               "Run the benchmarks first."
           )

   # Configure the visualisations to generate.
   analysis_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="rmae_comparison",
               metric="rMAE",
           ),
           GroupedTargetMetricVisualization(
               name="rcrps_comparison",
               metric="rCRPS",
           ),
           SummaryTableVisualization(name="performance_summary"),
       ]
   )

   output_path = Path("./results/comparison")
   comparison = BenchmarkComparisonPipeline(
       analysis_config=analysis_config,
       storage=LocalBenchmarkStorage(base_path=output_path),
       target_provider=target_provider,   # reuse the provider from your benchmark runner
   )

   comparison.run(run_data=run_storages)

``BenchmarkComparisonPipeline.run()`` loads evaluation reports from every named run and
produces HTML visualisations at three aggregation levels:

- **Global** — overall performance across all targets and runs.
- **Group** — performance broken down by target group (e.g., by region or asset type).
- **Target** — per-target performance across all runs.

This hierarchy makes it straightforward to answer both "which model is best overall?" and
"are the gains consistent, or does one model win only on a specific subset of sites?"


Visualising Performance Over Time
----------------------------------

Aggregate metrics can hide important dynamics. A model might achieve a good average rMAE
while performing poorly during winter peaks or degrading steadily between retraining events.
``WindowedMetricVisualization`` addresses this by plotting a chosen metric over a rolling
time window, making trends and seasonal patterns immediately visible.

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="MAE",
               window=Window(size=timedelta(days=7), step=timedelta(days=1)),
           ),
       ]
   )

The resulting chart plots metric values on the Y-axis against time on the X-axis. When
multiple models are included in the same comparison run, each appears as a separate line,
making it easy to see where one model overtakes another and whether the difference is
sustained or transient.

Useful patterns to look for:

- **Gradual degradation** between retraining events suggests the ``train_interval`` should
  be shortened.
- **Seasonal spikes** in error indicate that the feature set may be missing relevant
  calendar or weather signals.
- **Sudden jumps** often correspond to changes in the underlying data source and warrant
  investigation before drawing conclusions about model quality.


Practical Tips
--------------

**Choose a representative backtesting window.** A period of at least one full year is
recommended for energy forecasting, as it captures seasonal variation. Shorter windows can
produce misleading rankings if one model happens to suit the specific conditions in that
period.

**Match ``train_interval`` to your production schedule.** If the deployed model is retrained
weekly, use ``train_interval=timedelta(days=7)`` in the backtest. Mismatches between the
evaluation schedule and the production schedule are a common source of over-optimistic
results.

**Use rMAE and rCRPS as primary metrics.** Raw MAE values are hard to compare across sites
with different load magnitudes. The relative metrics normalise by the target's own range,
making cross-site and cross-model comparisons meaningful.

**Persist results before comparing.** ``BenchmarkComparisonPipeline`` operates on stored
evaluation reports rather than re-running the backtests. This separation means you can add
a new model to an existing comparison without re-running the models that have already been
evaluated.


Next Steps
----------

- :doc:`first_forecast` — if you need a refresher on building and running a forecaster
  before plugging it into a backtest.
- :doc:`advanced_customization` — covers implementing custom ``BacktestForecasterMixin``
  classes, writing bespoke metric providers, and plugging in alternative storage backends.
- :doc:`quickstart` — a minimal end-to-end example if you want to see the full pipeline
  in the fewest possible lines of code.