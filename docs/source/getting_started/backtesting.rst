Backtesting
===========

Backtesting lets you measure how well a forecasting model would have performed
on historical data, using the same operational constraints it would face in
production. Rather than simply fitting a model to the full dataset and scoring
it, OpenSTEF's backtesting library simulates the real-time forecasting loop:
predictions are generated at regular intervals, the model is retrained
periodically, and — crucially — no future data is ever visible at prediction
time. The result is an honest estimate of production performance.

This page walks through the complete backtesting workflow: configuring and
running a backtest, understanding the evaluation metrics, and visualising
results to compare models.

.. note::

   This tutorial assumes you have already produced a basic forecast. If not,
   see :doc:`first_forecast` first. For installation instructions refer to
   :doc:`installation`.

.. note:: [DIAGRAM: Backtesting timeline showing alternating train and predict
   events replayed over a historical window, with the "data horizon" boundary
   that prevents leakage illustrated at each prediction step.]


Why Backtesting Matters
-----------------------

A common mistake is to evaluate a model by training on the full historical
period and then scoring on a held-out slice. This approach underestimates
real-world error because the model implicitly benefits from data that would not
have been available at the time of each prediction. OpenSTEF's
``BacktestPipeline`` prevents this by enforcing a *restricted horizon*: at
every prediction event the model sees only the data that would have existed at
that moment in time.

Three properties make the simulation realistic:

- **No data leakage** — future observations are never passed to the model.
- **Periodic retraining** — the model is retrained on a configurable schedule,
  mirroring how it would be maintained in production.
- **Aligned schedules** — prediction and training events are aligned to a
  reference time so the cadence matches a real deployment.


Setting Up a Backtest
---------------------

The entry point is ``BacktestPipeline``, which takes a ``BacktestConfig`` and a
forecaster that implements ``BacktestForecasterMixin``.

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   # Configure the backtesting schedule
   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),  # resolution of output
       predict_interval=timedelta(hours=6),               # how often to predict
       train_interval=timedelta(days=7),                  # how often to retrain
   )

``prediction_sample_interval`` sets the temporal resolution of the output
forecast. ``predict_interval`` controls how frequently new predictions are
generated during the replay — every six hours in the example above. The model
is retrained from scratch every ``train_interval``, just as it would be in a
live system.

.. note::

   ``prediction_sample_interval`` must match the ``predict_sample_interval``
   defined in your forecaster's configuration. A ``ValueError`` is raised at
   construction time if they differ.

Once you have a configured forecaster (see :doc:`advanced_customization` for
how to build a custom one), wire everything together and call ``run``:

.. code-block:: python

   from datetime import datetime, timezone

   # my_forecaster implements BacktestForecasterMixin
   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   predictions = pipeline.run(
       ground_truth=ground_truth_dataset,   # VersionedTimeSeriesDataset
       predictors=predictors_dataset,       # VersionedTimeSeriesDataset
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       show_progress=True,
   )

``run`` returns a ``TimeSeriesDataset`` containing every prediction generated
during the replay window. Passing ``show_progress=True`` displays a progress
bar, which is helpful for long historical periods.


Evaluation Metrics
------------------

OpenSTEF provides metrics for both deterministic and probabilistic forecasts.
The two most important ones for energy forecasting are:

- **rMAE** (relative Mean Absolute Error) — point forecast accuracy, expressed
  as a fraction of the target scale. Lower is better.
- **rCRPS** (relative Continuous Ranked Probability Score) — probabilistic
  forecast quality. It rewards forecasts that assign high probability to
  outcomes that actually occur. Lower is better.

For congestion-focused use cases there are also peak-detection metrics, but
rMAE and rCRPS cover the majority of model comparison tasks.

When comparing two models, a reduction in rCRPS indicates that the
probabilistic forecast has improved overall; a reduction in rMAE at the median
quantile (``Quantile(0.5)``) indicates that the central point forecast has
improved.


Visualising Performance
-----------------------

Raw metric numbers are useful, but visualisations reveal *when* and *where*
performance differs between models. OpenSTEF ships built-in interactive
visualisations through ``AnalysisConfig`` — no external plotting library
required.

**Time-series view** — plots actual measurements against forecast quantiles as
shaded uncertainty bands. Use this to spot systematic biases or periods where
the model struggles.

**Windowed metric view** — plots a metric (e.g. rMAE or rCRPS) computed over a
rolling window, showing how accuracy evolves over time. This is the primary
tool for detecting performance degradation and choosing retraining intervals.

**Grouped target view** — bar or box charts comparing metric values across
multiple targets or model runs. Use this when comparing two model variants
side-by-side.

The example below configures all three visualisation types:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import Quantile
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       TimeSeriesVisualization,
       WindowedMetricVisualization,
       GroupedTargetMetricVisualization,
   )
   from openstef_beam.evaluation import Window

   analysis_config = AnalysisConfig(
       visualization_providers=[
           # Forecast vs actuals with uncertainty bands
           TimeSeriesVisualization(name="forecast_vs_actual"),

           # Rolling 7-day rMAE at the median quantile
           WindowedMetricVisualization(
               name="rMAE_windowed_7D",
               metric=("rMAE", Quantile(0.5)),
               window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
           ),

           # Rolling 30-day probabilistic score
           WindowedMetricVisualization(
               name="rCRPS_windowed_30D",
               metric="rCRPS",
               window=Window(lag=timedelta(hours=0), size=timedelta(days=30)),
           ),

           # Cross-target rMAE comparison (median)
           GroupedTargetMetricVisualization(
               name="rMAE_grouped",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),

           # Cross-target probabilistic comparison
           GroupedTargetMetricVisualization(
               name="rCRPS_grouped",
               metric="rCRPS",
           ),
       ]
   )

The resulting HTML files are interactive and can be opened directly in a
browser. Hovering over a data point shows the exact metric value, the time
window it covers, and the run or target it belongs to.


Comparing Multiple Models
-------------------------

The most common use of backtesting is to decide between two model variants —
for example, a baseline and a candidate with new features. The recommended
workflow is:

1. Run ``BacktestPipeline.run`` for each model over the **same** historical
   window and with the **same** ``BacktestConfig``. This ensures the comparison
   is fair: both models see identical data at every prediction event.
2. Label each run with a distinct ``run_name`` so the analysis layer can
   distinguish them.
3. Pass both result sets to the analysis pipeline with the shared
   ``AnalysisConfig``. The ``GroupedTargetMetricVisualization`` and
   ``WindowedMetricVisualization`` providers will automatically render
   side-by-side comparisons when multiple runs are present.

.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   shared_config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
   )

   # Run baseline model
   baseline_pipeline = BacktestPipeline(
       config=shared_config,
       forecaster=baseline_forecaster,
   )
   baseline_predictions = baseline_pipeline.run(
       ground_truth=ground_truth_dataset,
       predictors=predictors_dataset,
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
   )

   # Run candidate model with identical settings
   candidate_pipeline = BacktestPipeline(
       config=shared_config,
       forecaster=candidate_forecaster,
   )
   candidate_predictions = candidate_pipeline.run(
       ground_truth=ground_truth_dataset,
       predictors=predictors_dataset,
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
   )

With both prediction sets in hand, pass them to the analysis pipeline together.
The windowed metric plots will overlay both runs on the same axes, making it
straightforward to see whether the candidate improves or regresses across
different seasons or load conditions.

.. note::

   Always use the same ``start`` and ``end`` dates and the same
   ``BacktestConfig`` when comparing models. Changing the evaluation window or
   the retraining cadence between runs invalidates the comparison.


Choosing Window Sizes
---------------------

The ``size`` parameter of ``Window`` controls the trade-off between noise and
responsiveness in windowed metric plots:

- **Short windows (7 days)** — sensitive to recent changes; useful for
  detecting sudden degradation after a data quality issue or a distribution
  shift.
- **Medium windows (21 days)** — balance between noise and trend visibility;
  good default for most comparisons.
- **Long windows (30 days)** — smooth out weekly seasonality; best for
  assessing overall model health across a full month.

It is common to configure all three window sizes simultaneously, as shown in
the ``AnalysisConfig`` example above, so you can inspect performance at
multiple time scales in a single analysis run.


Next Steps
----------

- :doc:`advanced_customization` — implement a custom forecaster that satisfies
  ``BacktestForecasterMixin`` and plug it into the pipeline.
- :doc:`first_forecast` — if you need a refresher on loading data and
  constructing the datasets expected by ``BacktestPipeline.run``.
- :doc:`quickstart` — a minimal end-to-end example if you want to see the
  whole workflow at a glance before diving into backtesting.