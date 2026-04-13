Backtesting Models with Historical Data
=======================================

Backtesting is the process of evaluating a forecasting model by simulating how it
would have performed in the past — training only on data that would have been
available at each point in time, then generating predictions and comparing them to
what actually happened. This page walks through how to use OpenSTEF's backtesting
infrastructure to run such simulations, extract evaluation metrics, visualise
performance over time, and compare multiple models against one another.

If you haven't yet run a basic forecast, see :doc:`first_forecast` first. For
advanced model customisation before backtesting, see :doc:`advanced_customization`.

.. note:: [DIAGRAM: Timeline showing train/predict/retrain cycle during a backtest — events spaced along a time axis with shaded training windows and prediction arrows.]

Why Backtesting Matters
-----------------------

A model that scores well on a held-out test set is not the same as a model that
performs well in production. In real operations, forecasts are generated repeatedly
on a rolling basis, the model is periodically retrained as new data arrives, and
the available history at any moment is strictly limited to the past. OpenSTEF's
``BacktestPipeline`` reproduces this operational reality precisely, so the
performance numbers you measure during backtesting are directly comparable to what
you would observe in a live deployment.

The pipeline prevents data leakage by design: when generating a prediction at time
*t*, it only exposes data with timestamps strictly before *t* to the model. Periodic
retraining events are also scheduled automatically according to the interval you
configure.

Core Concepts
-------------

Three configuration parameters control the shape of a backtest:

- **prediction_sample_interval** — the temporal resolution of each individual
  forecast (e.g. ``timedelta(minutes=15)`` for quarter-hourly output). This must
  match the ``predict_sample_interval`` set on your forecaster.
- **predict_interval** — how often a new forecast is generated during the
  simulation (e.g. every six hours).
- **train_interval** — how often the model is retrained on the expanding history
  (e.g. every seven days).

These three parameters together determine the total number of training and
prediction events that the pipeline will execute, and therefore the runtime of the
backtest.

Running Your First Backtest
---------------------------

The entry point is ``BacktestPipeline``. You construct it with a ``BacktestConfig``
and a forecaster that implements ``BacktestForecasterMixin``, then call ``.run()``
with your historical data.

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    # Configure the simulation cadence
    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
        align_time=time.fromisoformat("00:00+00"),
    )

    # Assume `my_forecaster` is already constructed and configured
    pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

    # `ground_truth` and `predictors` are VersionedTimeSeriesDataset objects
    # loaded from your historical data store
    predictions = pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=None,   # use the earliest timestamp in the data
        end=None,     # use the latest timestamp in the data
        show_progress=True,
    )

``pipeline.run()`` returns a ``TimeSeriesDataset`` containing every prediction
generated during the simulation, together with an ``available_at`` column that
records when each forecast was produced. Passing ``start`` and ``end`` as ``None``
tells the pipeline to span the full extent of your data; you can narrow the window
by supplying explicit ``datetime`` values.

.. note::

   ``BacktestConfig.prediction_sample_interval`` must equal
   ``forecaster.config.predict_sample_interval``. A ``ValueError`` is raised at
   construction time if they differ, so mismatches are caught before any
   computation begins.

Configuring the Training Schedule
----------------------------------

The ``train_interval`` parameter controls how stale the model is allowed to become
before it is retrained. A shorter interval keeps the model fresh but increases
total compute time; a longer interval is faster but may miss concept drift.

A common starting point for energy forecasting is weekly retraining with six-hourly
predictions:

.. code-block:: python

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
    )

If you are investigating the effect of retraining frequency itself, you can run the
same backtest with different ``train_interval`` values and compare the resulting
metric curves — this is a natural use of the model comparison workflow described
below.

Evaluating Performance Over Time
---------------------------------

A single aggregate metric (e.g. overall MAE for the entire backtest period) hides
important information: performance often varies seasonally, degrades before a
retraining event, or improves after a data quality fix. OpenSTEF provides
``WindowedMetricVisualization`` to plot any supported metric computed over a sliding
window, giving you a time-series view of model accuracy.

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import WindowedMetricVisualization
    from openstef_beam.evaluation import Window

    analysis_config = AnalysisConfig(
        visualization_providers=[
            # MAE over a rolling 7-day window
            WindowedMetricVisualization(
                name="mae_7d",
                metric="MAE",
                window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
            ),
            # Relative MAE over a rolling 30-day window
            WindowedMetricVisualization(
                name="rmae_30d",
                metric="rMAE",
                window=Window(lag=timedelta(hours=0), size=timedelta(days=30)),
            ),
            # Probabilistic skill score if your model produces quantile forecasts
            WindowedMetricVisualization(
                name="rcrps_21d",
                metric="rCRPS",
                window=Window(lag=timedelta(hours=0), size=timedelta(days=21)),
            ),
        ]
    )

The resulting plots show metric values on the Y-axis and time on the X-axis, with
one data point per evaluation window. Patterns to look for include:

- **Periodic spikes** before retraining events — a sign that ``train_interval``
  may be too long.
- **Seasonal degradation** — accuracy drops in summer or winter that suggest the
  model needs season-aware features.
- **Sudden step changes** — often caused by upstream data quality issues or
  changes in the measurement equipment.

Supported metrics include ``MAE``, ``rMAE``, ``RMSE``, ``rCRPS``, and
``rCRPS_sample_weighted``. Use relative metrics (prefixed ``r``) when comparing
across targets with different scales.

Comparing Multiple Models
--------------------------

The most common use of backtesting is deciding between two or more candidate
models. OpenSTEF supports this through the ``RunName`` concept: each backtest run
is labelled, and the visualisation layer can overlay multiple runs on the same
plot, drawing one line per model.

The typical workflow is:

1. Run ``BacktestPipeline.run()`` once per model, collecting the predictions from
   each run.
2. Pass all results into the analysis layer tagged with their run names.
3. Inspect the windowed metric plots to identify which model performs better and
   under what conditions.

.. code-block:: python

    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
    from datetime import timedelta

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
    )

    # Run backtest for model A
    pipeline_a = BacktestPipeline(config=config, forecaster=forecaster_a)
    predictions_a = pipeline_a.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=None,
        end=None,
    )

    # Run backtest for model B with the same data and config
    pipeline_b = BacktestPipeline(config=config, forecaster=forecaster_b)
    predictions_b = pipeline_b.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=None,
        end=None,
    )

Because both pipelines use identical ``config``, ``ground_truth``, and
``predictors``, any difference in the resulting metrics is attributable to the
model itself rather than to differences in the evaluation setup. This is the key
principle of a fair model comparison.

.. note::

   Keep ``BacktestConfig`` identical across all runs in a comparison. Changing
   ``train_interval`` or ``predict_interval`` between runs introduces a confound
   that makes the metric difference uninterpretable.

Interpreting Results
--------------------

When reviewing backtest output, consider the following:

- **Aggregate vs. windowed metrics** — a model with a lower overall MAE may still
  have worse worst-case windows. Check both.
- **Horizon breakdown** — energy forecast errors typically grow with the forecast
  horizon. If your analysis supports it, inspect accuracy separately for short
  (0–6 h) and longer (6–24 h) horizons.
- **Data coverage** — the ``available_at`` column in the returned
  ``TimeSeriesDataset`` lets you verify that predictions were generated at the
  expected cadence and flag any gaps caused by training failures.
- **Relative metrics for cross-target comparison** — when backtesting across
  multiple substations or assets, use ``rMAE`` or ``rCRPS`` so that high-load
  targets do not dominate the aggregate score.

Common Pitfalls
---------------

**Mismatched sample intervals**
   ``BacktestConfig.prediction_sample_interval`` must equal
   ``forecaster.config.predict_sample_interval``. The pipeline raises a
   ``ValueError`` immediately if they differ.

**Insufficient warm-up data**
   The first training event needs enough history to fit the model. If your
   ``start`` date is too close to the beginning of your dataset, the first
   training window may be too short. Either shift ``start`` forward or ensure
   your dataset extends well before the evaluation period.

**Comparing runs with different configs**
   Changing ``train_interval`` or ``predict_interval`` between model runs
   invalidates the comparison. Always hold the config constant when the goal is
   to compare model quality.

Next Steps
----------

- :doc:`advanced_customization` — learn how to implement custom forecasters that
  satisfy the ``BacktestForecasterMixin`` interface and plug into the pipeline.
- :doc:`first_forecast` — if you need a refresher on constructing a forecaster
  before backtesting it.
- :doc:`quickstart` — a minimal end-to-end example if you want to get something
  running quickly.