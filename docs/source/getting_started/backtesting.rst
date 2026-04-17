Backtesting
===========

Backtesting lets you answer a deceptively simple question: *how well would this model have performed if it had been running in production over the past year?* Rather than evaluating a model on a held-out test set in isolation, OpenSTEF's ``BacktestPipeline`` replays history the way a live system would have experienced it — generating forecasts at regular intervals, retraining on a schedule, and never peeking at data that would not yet have been available at each point in time.

This page walks through configuring and running a backtest, interpreting the evaluation metrics it produces, and visualising how model performance evolves over time. If you have not yet produced your first forecast, start with :doc:`first_forecast` and return here once you are comfortable with the basics.

.. note::

   [DIAGRAM: Timeline showing the sliding-window backtesting process. The horizontal axis is calendar time (e.g. Jan → Dec). A shaded "training window" block slides rightward, followed immediately by a shorter "prediction window" block. Arrows indicate the train event and the predict event at each step. A vertical dashed line labelled "restricted horizon" marks the data cutoff enforced at each step, showing that future data is invisible. Repeat the train/predict pair four or five times across the timeline to convey the cyclic nature of the process.]

How the pipeline works
----------------------

``BacktestPipeline`` is the core class in ``openstef_beam.backtesting``. It drives two interleaved schedules:

- **Prediction schedule** — every ``predict_interval`` (default: 6 hours) the pipeline calls your forecaster and collects the resulting forecast.
- **Retraining schedule** — every ``train_interval`` (default: 7 days) the pipeline retrains the model on all data available up to that moment.

At every step the pipeline wraps the input datasets in a ``RestrictedHorizonVersionedTimeSeries`` that hard-blocks access to any timestamp beyond the current simulation clock. This is what prevents data leakage and makes the evaluation realistic.

The pipeline is intentionally a *library component* — it does not own your data, your model, or your storage layer. You bring those pieces and wire them together.

Configuring the backtest
------------------------

All timing parameters live in ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

   config = BacktestConfig(
       # Granularity of the output forecast (must match your forecaster)
       prediction_sample_interval=timedelta(minutes=15),

       # How often a new forecast is generated during the simulation
       predict_interval=timedelta(hours=6),

       # How often the model is retrained on accumulated history
       train_interval=timedelta(days=7),

       # Wall-clock anchor for aligning the prediction schedule
       align_time=time.fromisoformat("00:00+00"),
   )

The ``prediction_sample_interval`` must match the ``predict_sample_interval`` declared in your forecaster's own configuration. The pipeline raises a ``ValueError`` at construction time if these differ, so misconfiguration is caught early.

.. note::

   Shorter ``predict_interval`` values produce denser output but increase runtime proportionally. A value of 6 hours is a practical default for day-ahead energy forecasting; intraday use cases may warrant 15–30 minutes.

Implementing a forecaster
--------------------------

``BacktestPipeline`` accepts any object that implements ``BacktestForecasterMixin``. The mixin defines the contract your model must satisfy — primarily a ``predict`` method and, if ``requires_training`` is ``True``, a ``train`` method. The mixin's companion configuration class ``BacktestForecasterConfig`` declares the data requirements the pipeline uses to size context windows:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterMixin,
       BacktestForecasterConfig,
   )

   class MyForecasterConfig(BacktestForecasterConfig):
       requires_training: bool = True
       predict_sample_interval: timedelta = timedelta(minutes=15)
       predict_length: timedelta = timedelta(hours=48)
       predict_min_length: timedelta = timedelta(hours=24)
       predict_context_length: timedelta = timedelta(days=14)
       predict_context_min_coverage: float = 0.8
       training_context_length: timedelta = timedelta(days=365)
       training_context_min_coverage: float = 0.7

   class MyForecaster(BacktestForecasterMixin):
       def __init__(self):
           self.config = MyForecasterConfig()
           self._model = None

       def train(self, ground_truth, predictors):
           # Fit your model on the restricted-horizon data provided
           ...

       def predict(self, predictors):
           # Return a TimeSeriesDataset of forecasts
           ...

Running the backtest
--------------------

With a config and a forecaster in hand, construct the pipeline and call ``run``:

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig, BacktestPipeline

   # ground_truth and predictors are VersionedTimeSeriesDataset objects
   # covering the full historical period you want to evaluate over.

   pipeline = BacktestPipeline(
       config=config,
       forecaster=MyForecaster(),
   )

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1, tzinfo=timezone.utc),
       end=datetime(2023, 12, 31, tzinfo=timezone.utc),
       show_progress=True,   # tqdm progress bar
   )

``run`` returns a ``TimeSeriesDataset`` containing every forecast generated during the simulation, tagged with the ``available_at`` timestamp that records when each forecast was produced. This versioning information is what allows the downstream evaluation to segment results by lead time.

Evaluating the predictions
---------------------------

Once you have the backtest predictions, pass them to ``EvaluationPipeline`` alongside the ground-truth observations:

.. code-block:: python

   from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline, EvaluationConfig
   from openstef_beam.evaluation.metrics import MAEProvider, RMAEProvider
   from openstef_core.types import Quantile

   evaluation_config = EvaluationConfig()

   metrics = [MAEProvider(), RMAEProvider()]

   eval_pipeline = EvaluationPipeline(
       config=evaluation_config,
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       window_metric_providers=metrics,
       global_metric_providers=metrics,
   )

   report = eval_pipeline.run(
       predictions=predictions,
       ground_truth=ground_truth,
       target_column="load_mw",
   )

The ``quantiles`` list must include ``0.5`` (the median); the pipeline raises a ``ValueError`` otherwise. The report segments results by ``available_at`` and lead time, giving you a detailed picture of how accuracy varies across the forecast horizon.

Available metrics include:

- **MAE** — Mean Absolute Error; straightforward absolute deviation.
- **rMAE** — Relative MAE, normalised by a reference quantile range; useful for comparing targets with different scales.
- **MAPE** — Mean Absolute Percentage Error.
- **rCRPS** — Relative Continuous Ranked Probability Score; the primary metric for probabilistic forecasts.
- **rMAE_peak_hours** — rMAE restricted to peak demand hours; relevant for grid capacity planning.

Visualising performance over time
----------------------------------

A single aggregate metric can hide important dynamics — a model that performs well on average may degrade badly in winter or after a public holiday. ``WindowedMetricVisualization`` plots how a chosen metric evolves across rolling time windows, making these patterns visible:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.analysis.analysis_pipeline import AnalysisPipeline
   from openstef_beam.evaluation import Window
   from openstef_core.types import Quantile

   analysis_config = AnalysisConfig(
       visualization_providers=[
           # 7-day rolling rMAE at the median quantile
           WindowedMetricVisualization(
               name="rMAE_7D",
               metric=("rMAE", Quantile(0.5)),
               window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           ),
           # 30-day rolling rMAE for a smoother trend line
           WindowedMetricVisualization(
               name="rMAE_30D",
               metric=("rMAE", Quantile(0.5)),
               window=Window(lag=timedelta(hours=0), size=timedelta(days=30)),
           ),
           # Probabilistic performance via rCRPS
           WindowedMetricVisualization(
               name="rCRPS_7D",
               metric="rCRPS",
               window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           ),
       ]
   )

   analysis_pipeline = AnalysisPipeline(config=analysis_config)

   # reports is a list of (TargetMetadata, EvaluationReport) tuples
   visualizations = analysis_pipeline.run_for_reports(reports=reports, scope=scope)

Each ``WindowedMetricVisualization`` produces an interactive line chart. Multiple window sizes on the same metric are complementary: the short window (7 days) highlights sharp transitions while the longer window (30 days) reveals gradual drift.

**[VISUALIZATION: Example WindowedMetricVisualization output — a line chart with calendar date on the X-axis and rMAE on the Y-axis, showing two overlapping lines for 7-day and 30-day rolling windows. A visible performance spike around a public holiday period illustrates the kind of insight the chart provides.]**

Interpreting the results
------------------------

When reviewing backtest output, focus on three questions:

1. **Is accuracy stable over time?** A flat windowed-metric line indicates a robust model. Spikes or upward trends suggest the model struggles with specific conditions or is drifting as the data distribution shifts.

2. **How does accuracy degrade with lead time?** The evaluation report segments results by lead time. Accuracy typically degrades as lead time increases; a sharp cliff may indicate that a key predictor (e.g. a weather forecast) loses skill beyond a certain horizon.

3. **Is the retraining interval appropriate?** If the windowed metric consistently improves just after a retrain event and then degrades before the next one, shortening ``train_interval`` is likely worthwhile.

.. note::

   Backtesting is computationally heavier than a single train/test split because the model is trained and evaluated many times. For long historical periods or slow models, consider narrowing the ``start``/``end`` window first to validate your setup, then expanding to the full period.

Next steps
----------

- :doc:`advanced_customization` — implement custom metric providers, callbacks, and forecaster mixins to tailor the pipeline to your use case.
- :doc:`first_forecast` — if you want to revisit the basics of producing a single forecast before running a full backtest.
- :doc:`quickstart` — minimal working example to get something running in minutes.