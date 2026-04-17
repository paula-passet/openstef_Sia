Backtesting Your Models
=======================

Backtesting lets you measure how well a forecasting model would have performed on
historical data, without ever letting it peek at the future. This page walks through
configuring and running a backtest with OpenSTEF BEAM's ``BacktestPipeline``, and
shows how to interpret the evaluation metrics and visualisations it produces.

If you haven't installed the library yet, see :doc:`installation`. For a minimal
working forecast without backtesting, start with :doc:`quickstart`.

.. note:: [DIAGRAM: Timeline showing sliding-window backtesting. The full historical period is divided into sequential steps. At each step there is a restricted data horizon: the model can only see data to the left of the current position. A "train" event fires every ``train_interval`` (e.g. weekly), followed by repeated "predict" events every ``predict_interval`` (e.g. every 6 hours) until the next retrain. The window advances in time, replaying the entire history from ``start`` to ``end``.]


How backtesting works
---------------------

``BacktestPipeline`` replays history in strict chronological order. At every
prediction step it exposes only the data that would have been available at that
moment in real operations — no future values leak into training or inference. The
pipeline fires two kinds of events:

- **Train events** — triggered every ``train_interval``. The model is retrained on
  all data up to the current horizon.
- **Predict events** — triggered every ``predict_interval``. The model produces a
  forecast using the most recently trained weights.

This mirrors the operational schedule of a deployed forecaster, so the accuracy
numbers you see in a backtest are a realistic estimate of live performance.


Configuring the backtest
------------------------

All timing parameters live in ``BacktestConfig``:

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

    config = BacktestConfig(
        # Resolution of the output forecast (must match the forecaster's own interval)
        prediction_sample_interval=timedelta(minutes=15),

        # How often to generate a new set of predictions
        predict_interval=timedelta(hours=6),

        # How often to retrain the model on fresh data
        train_interval=timedelta(days=7),

        # Align prediction schedules to midnight UTC
        align_time=time.fromisoformat("00:00+00"),
    )

.. note::

   ``prediction_sample_interval`` must equal the forecaster's own
   ``predict_sample_interval``. The pipeline raises a ``ValueError`` at
   construction time if they differ, so mismatches are caught early.

The three interval parameters let you trade off compute cost against evaluation
fidelity:

- A shorter ``predict_interval`` produces denser coverage of the historical period
  but increases runtime.
- A shorter ``train_interval`` tests whether the model benefits from frequent
  retraining; a longer one is cheaper and closer to a "train once, evaluate many"
  regime.


Running the pipeline
--------------------

``BacktestPipeline`` takes a configured ``BacktestConfig`` and a forecaster that
implements ``BacktestForecasterMixin``. Call ``run()`` with your historical datasets
and the time window you want to evaluate:

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_beam.backtesting.backtest_pipeline import BacktestPipeline

    # Assume `forecaster` is already constructed — see the first_forecast tutorial
    pipeline = BacktestPipeline(config=config, forecaster=forecaster)

    predictions = pipeline.run(
        ground_truth=ground_truth_dataset,   # VersionedTimeSeriesDataset
        predictors=predictor_dataset,        # VersionedTimeSeriesDataset
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 30, tzinfo=timezone.utc),
        show_progress=True,
    )

``run()`` returns a ``TimeSeriesDataset`` containing every prediction that was made
during the replay, tagged with the timestamp at which it was generated. Passing
``start=None`` or ``end=None`` defaults to the earliest or latest timestamp present
in ``ground_truth``.

A progress bar is shown by default (``show_progress=True``). Disable it in
automated pipelines by passing ``show_progress=False``.


Evaluating results
------------------

Once you have the predictions dataset, pass it to ``EvaluationPipeline`` alongside
the ground truth to compute metrics:

.. code-block:: python

    from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline
    from openstef_beam.evaluation import EvaluationConfig

    eval_config = EvaluationConfig()

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.5, 0.9],
        window_metric_providers=metrics,
        global_metric_providers=metrics,
    )

    report = eval_pipeline.run(
        ground_truth=ground_truth_dataset,
        predictions=predictions,
    )

The report contains both **global metrics** (aggregated over the entire evaluation
window) and **windowed metrics** (computed over a rolling time window), giving you
both a headline number and a picture of how performance evolves over time.

Common metrics available out of the box:

- **MAE** — Mean Absolute Error, easy to interpret in the original unit (e.g. MW).
- **RMSE** — Root Mean Squared Error, penalises large errors more heavily.
- **rMAE** — Relative MAE, normalised by the target's mean, useful for comparing
  across sites with different scales.
- **rCRPS** — Relative Continuous Ranked Probability Score, the primary metric for
  probabilistic (quantile) forecasts.


Visualising performance
-----------------------

Two visualisation providers cover the most common analysis needs.

**Performance over time** — ``WindowedMetricVisualization`` plots a chosen metric
as a time series, making it easy to spot seasonal degradation or the effect of
retraining events:

.. code-block:: python

    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import WindowedMetricVisualization
    from openstef_beam.evaluation import Window
    from datetime import timedelta

    analysis_config = AnalysisConfig(
        visualization_providers=[
            WindowedMetricVisualization(
                name="mae_over_time",
                metric="MAE",
                window=Window(size=timedelta(days=7)),
            ),
        ]
    )

.. note:: [VISUALIZATION: Line chart with time on the X-axis and MAE on the Y-axis. Each point represents the metric computed over a 7-day rolling window. Dips and spikes reveal periods of high or low forecast accuracy, and vertical markers can indicate retraining events.]

**Per-target comparison** — ``GroupedTargetMetricVisualization`` produces bar or
box-plot charts that compare accuracy across multiple forecasting targets:

.. code-block:: python

    from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
    from openstef_core.types import Quantile

    analysis_config = AnalysisConfig(
        visualization_providers=[
            GroupedTargetMetricVisualization(
                name="rmae_by_target",
                metric="rMAE",
                quantile=Quantile(0.5),
            ),
            GroupedTargetMetricVisualization(
                name="rcrps_by_target",
                metric="rCRPS",
            ),
        ]
    )

.. note:: [VISUALIZATION: Bar chart with one bar per forecasting target. Bar height shows rMAE at the median quantile. Targets are colour-coded by group, making it straightforward to identify which sites are hardest to forecast.]


Practical tips
--------------

- **Match intervals to operations.** Set ``predict_interval`` and
  ``train_interval`` to the values used in your production system. A backtest
  with a weekly retrain but hourly predictions is only realistic if that is how
  the live system runs.

- **Watch for data gaps.** ``VersionedTimeSeriesDataset`` tracks data
  availability at each point in time. If your historical predictor data has gaps,
  the pipeline will reflect that — predictions during gap periods may be less
  accurate, just as they would be in production.

- **Start small.** Run the backtest over a short window (a few weeks) first to
  verify configuration and check that metrics look sensible before committing to
  a multi-month evaluation.

- **Batch forecasters.** If your forecaster implements
  ``BacktestBatchForecasterMixin``, the pipeline automatically groups prediction
  events into batches, which can significantly reduce overhead for models with
  high per-call startup costs.


Next steps
----------

- :doc:`first_forecast` — build and configure a forecaster before running it
  through a backtest.
- :doc:`advanced_customization` — extend the pipeline with custom callbacks,
  metric providers, and forecaster implementations.