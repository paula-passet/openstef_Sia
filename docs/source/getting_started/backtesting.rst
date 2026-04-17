Backtesting
===========

When you train a model on historical data and then evaluate it on that same data, you get an
optimistic picture of performance that rarely holds in production. Backtesting solves this by
replaying history as if it were happening in real time: the model only ever sees data that would
have been available at each moment, retrains on a schedule that mirrors real deployment, and
generates predictions that can be compared against what actually happened.

This page walks through the OpenSTEF backtesting workflow — from configuring a single-model
backtest to comparing multiple models side by side. If you haven't installed the library yet,
see :doc:`installation`. For a minimal working forecast without backtesting, start with
:doc:`quickstart`.

.. note:: [DIAGRAM: Backtesting timeline showing train/predict windows advancing through historical data with no data leakage]

How OpenSTEF Backtesting Works
-------------------------------

The ``BacktestPipeline`` in ``openstef_beam`` simulates the operational environment your model
would face in production. At each step along the historical timeline it:

1. **Restricts data visibility** — the model can only access data with timestamps earlier than
   the current simulation time, preventing any leakage of future information.
2. **Retrains on a schedule** — the model is retrained periodically (e.g., every seven days),
   just as it would be in a live system.
3. **Generates predictions** — forecasts are produced at a configurable interval and collected
   into a single dataset for evaluation.

Because every model is tested under identical temporal constraints, the results are directly
comparable across model variants.

Configuring the Backtest
-------------------------

Two configuration objects control the backtesting process: ``BacktestConfig`` governs the
simulation schedule, and ``BacktestForecasterConfig`` governs the model's own data requirements.
The ``prediction_sample_interval`` on both objects must match — the pipeline raises a
``ValueError`` at construction time if they don't.

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig

   backtest_config = BacktestConfig(
       # Resolution of the output forecast (must match your forecaster's interval)
       prediction_sample_interval=timedelta(minutes=15),

       # How often new predictions are generated during the simulation
       predict_interval=timedelta(hours=6),

       # How often the model is retrained
       train_interval=timedelta(days=7),

       # Reference time for aligning prediction schedules
       align_time=time.fromisoformat("00:00+00"),
   )

The ``predict_interval`` and ``train_interval`` parameters let you experiment with operational
trade-offs. A shorter ``train_interval`` keeps the model fresh but increases compute cost; a
longer one is cheaper but may miss concept drift.

Running a Single-Model Backtest
--------------------------------

With a configuration in hand, you wrap your model in a ``BacktestForecasterMixin`` implementation
and pass both to ``BacktestPipeline.run()``. The pipeline accepts versioned time-series datasets
for the target variable (``ground_truth``) and the input features (``predictors``), plus optional
``start`` and ``end`` datetimes to narrow the evaluation window.

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   # Assume `my_forecaster` implements BacktestForecasterMixin
   # and `ground_truth`, `predictors` are VersionedTimeSeriesDataset objects

   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=my_forecaster,
   )

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1, tzinfo=timezone.utc),
       end=datetime(2023, 12, 31, tzinfo=timezone.utc),
       show_progress=True,   # tqdm progress bar
   )

``run()`` returns a ``TimeSeriesDataset`` containing every prediction generated during the
simulation, aligned to the ground-truth timestamps and ready for evaluation.

.. note::

   If you pass ``start=None`` or ``end=None``, the pipeline uses the minimum and maximum
   timestamps found in the provided datasets.

Implementing a Forecaster
^^^^^^^^^^^^^^^^^^^^^^^^^^

Your model must implement the ``BacktestForecasterMixin`` interface. At minimum this means
providing a ``BacktestForecasterConfig``, a ``fit()`` method for training, and a ``predict()``
method for inference.

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterConfig,
       BacktestForecasterMixin,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile

   class MyForecasterConfig(BacktestForecasterConfig):
       requires_training: bool = True
       predict_sample_interval: timedelta = timedelta(minutes=15)
       predict_length: timedelta = timedelta(hours=24)
       predict_min_length: timedelta = timedelta(hours=1)
       predict_context_length: timedelta = timedelta(days=7)
       predict_context_min_coverage: float = 0.8
       training_context_length: timedelta = timedelta(days=90)
       training_context_min_coverage: float = 0.7

   class MyForecaster(BacktestForecasterMixin):
       def __init__(self):
           self.config = MyForecasterConfig()
           self._model = None

       @property
       def quantiles(self) -> list[Quantile]:
           return [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

       def fit(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           # Train your model on the restricted historical window
           df = data.to_dataframe()
           self._model = train_my_model(df)   # your training logic here

       def predict(self, data: RestrictedHorizonVersionedTimeSeries) -> TimeSeriesDataset | None:
           if self._model is None:
               return None
           df = data.to_dataframe()
           return self._model.predict(df)     # your inference logic here

For models that benefit from batching multiple prediction requests together, implement
``BacktestBatchForecasterMixin`` instead and override ``predict_batch()``.

Evaluation Metrics
-------------------

After ``BacktestPipeline.run()`` returns predictions, you evaluate them against the ground truth
using the ``openstef_beam.metrics`` module. OpenSTEF provides metrics suited to both deterministic
and probabilistic forecasts:

- **rMAE** (relative Mean Absolute Error) — point forecast accuracy, normalised by load scale.
- **RMSE** (Root Mean Squared Error) — penalises large errors more heavily than rMAE.
- **rCRPS** (relative Continuous Ranked Probability Score) — measures the quality of the full
  predictive distribution for probabilistic forecasts; lower is better.

The ``EvaluationConfig`` and ``EvaluationPipeline`` classes handle metric computation and produce
an ``EvaluationReport`` that feeds directly into the visualisation layer.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider

   evaluation_config = EvaluationConfig()

   eval_pipeline = EvaluationPipeline(
       config=evaluation_config,
       quantiles=my_forecaster.quantiles,
       window_metric_providers=[RMAEProvider(), RCRPSProvider()],
       global_metric_providers=[RMAEProvider(), RCRPSProvider()],
   )

   report = eval_pipeline.run(
       ground_truth=ground_truth,
       predictions=predictions,
       evaluation_mask=None,   # optional mask to exclude certain periods
       target_column="load_mw",
   )

Visualising Performance
------------------------

OpenSTEF ships with built-in interactive HTML visualisations so you don't need to reach for
matplotlib. Configure them through ``AnalysisConfig`` and run them via ``AnalysisPipeline``.

**Time-windowed metric evolution** shows how accuracy changes over the backtesting period —
useful for spotting seasonal degradation or identifying the right retraining cadence:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       WindowedMetricVisualization,
       TimeSeriesVisualization,
       SummaryTableVisualization,
   )
   from datetime import timedelta

   analysis_config = AnalysisConfig(
       visualization_providers=[
           # Rolling metric over time
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="rMAE",
               window=timedelta(days=7),
           ),
           # Forecast vs actual with uncertainty bands
           TimeSeriesVisualization(name="forecast_vs_actual"),
           # Tabular summary of all metrics
           SummaryTableVisualization(name="summary"),
       ]
   )

The generated HTML files are interactive and can be opened directly in a browser. Each
``TimeSeriesVisualization`` overlays actual measurements with forecast quantiles as shaded
uncertainty bands, making it easy to spot systematic biases or periods where the model
underestimates uncertainty.

Comparing Multiple Models
--------------------------

The real power of backtesting comes from running the same evaluation on several model variants
and comparing them objectively. The ``BenchmarkPipeline`` and ``BenchmarkComparisonPipeline``
classes automate this workflow.

**Step 1 — Run each model independently and persist results:**

.. code-block:: python

   from pathlib import Path
   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage

   for model_name, forecaster in [("xgboost", xgb_forecaster), ("gblinear", gblinear_forecaster)]:
       storage = LocalBenchmarkStorage(base_path=Path(f"./results/{model_name}"))

       bench = BenchmarkPipeline(
           backtest_config=backtest_config,
           evaluation_config=evaluation_config,
           analysis_config=analysis_config,
           storage=storage,
           target_provider=my_target_provider,
       )
       bench.run(forecaster_factory=lambda ctx, tgt: forecaster)

**Step 2 — Generate a side-by-side comparison report:**

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from pathlib import Path

   run_data = {
       "xgboost":  LocalBenchmarkStorage(base_path=Path("./results/xgboost")),
       "gblinear": LocalBenchmarkStorage(base_path=Path("./results/gblinear")),
   }

   comparison_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(name="rmae_comparison",  metric="rMAE"),
           GroupedTargetMetricVisualization(name="rcrps_comparison", metric="rCRPS"),
           SummaryTableVisualization(name="performance_summary"),
       ]
   )

   output_storage = LocalBenchmarkStorage(base_path=Path("./results/comparison"))

   comparison = BenchmarkComparisonPipeline(
       analysis_config=comparison_config,
       target_provider=my_target_provider,
       storage=output_storage,
   )

   comparison.run(run_data=run_data)

``BenchmarkComparisonPipeline.run()`` automatically generates analysis at three levels of
aggregation:

- **Global** — overall performance across every target and run.
- **Group** — performance broken down by target category (e.g., transformer type, voltage level).
- **Target** — per-target detail, useful for diagnosing which assets are hardest to forecast.

.. note::

   Results are stored as structured HTML files under the ``output_storage`` path. Pass
   ``filter_args`` to ``comparison.run()`` to restrict the comparison to a subset of targets.

Interpreting Results
---------------------

A few practical guidelines when reading backtest output:

- **Compare rMAE and rCRPS together.** A model can have low rMAE (good point forecasts) but
  poor rCRPS (poorly calibrated uncertainty). For operational decisions that depend on
  confidence intervals — such as congestion management — rCRPS is often the more important
  metric.
- **Look at windowed metrics, not just global averages.** A model that performs well on average
  may degrade badly in winter or during public holidays. The ``WindowedMetricVisualization``
  makes these patterns visible.
- **Check the retraining interval.** If windowed rMAE rises steadily between retraining events
  and drops sharply after each one, shortening ``train_interval`` in ``BacktestConfig`` will
  likely improve production performance.
- **Validate temporal consistency.** The pipeline prevents data leakage by design, but if your
  feature engineering pipeline introduces look-ahead bias (e.g., using future weather actuals
  instead of forecasts), the backtest will still be optimistic. Review your ``predictors``
  dataset carefully.

Next Steps
-----------

With a working backtest in place, you can move on to customising the model itself — feature
engineering, hyperparameter tuning, and plugging in alternative algorithms are all covered in
:doc:`advanced_customization`. If you want to understand the full end-to-end forecasting
workflow before diving into backtesting, :doc:`first_forecast` provides a step-by-step
walkthrough.