Backtesting Your Models
=======================

This page shows how to evaluate a forecasting model against historical data using
OpenSTEF BEAM's ``BacktestPipeline``. Backtesting replays your model over a past
time window, respecting the data horizon that would have been available at each
moment — giving you a realistic estimate of how the model would have performed in
production.

If you haven't set up your environment yet, see :doc:`installation`. For a minimal
working forecast without backtesting, start with :doc:`quickstart`.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd

How the backtest works
----------------------

``BacktestPipeline`` drives two interleaved schedules:

- **Prediction schedule** — every ``predict_interval`` (default 6 hours), the
  pipeline calls the forecaster to generate a new forecast batch.
- **Retraining schedule** — every ``train_interval`` (default 7 days), the
  pipeline retrains the model using only data available up to that point.

Between these two schedules, ``prediction_sample_interval`` controls the
resolution of individual forecast points (default 15 minutes). The pipeline
enforces strict temporal consistency: no future data ever leaks into a training
or prediction step.


Configuration
-------------

All timing parameters live in ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig

   config = BacktestConfig(
       # Resolution of each forecast point
       prediction_sample_interval=timedelta(minutes=15),

       # How often a new forecast batch is generated
       predict_interval=timedelta(hours=6),

       # How often the model is retrained from scratch
       train_interval=timedelta(days=7),

       # Reference time for aligning schedules to regular UTC boundaries
       align_time=time.fromisoformat("00:00+00"),
   )

.. note::

   ``prediction_sample_interval`` must match the ``predict_sample_interval``
   configured on your forecaster. The pipeline raises a ``ValueError`` at
   construction time if they differ, so mismatches are caught early.

Choosing sensible intervals depends on your use case:

- A shorter ``predict_interval`` produces denser coverage of the historical
  period but increases compute time proportionally.
- A longer ``train_interval`` reduces retraining overhead; use a shorter one
  if you expect the model to drift over the evaluation window.


Running a backtest
------------------

``BacktestPipeline`` takes a ``BacktestConfig`` and a forecaster that implements
``BacktestForecasterMixin``. Call ``.run()`` with your historical ground-truth
series, predictor features, and the start/end of the evaluation window:

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.backtesting.forecaster import MyForecaster  # your implementation

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
   )

   forecaster = MyForecaster(...)

   pipeline = BacktestPipeline(config=config, forecaster=forecaster)

   predictions = pipeline.run(
       ground_truth=versioned_ground_truth,   # VersionedTimeSeriesDataset
       predictors=versioned_predictors,       # VersionedTimeSeriesDataset
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       show_progress=True,
   )

``pipeline.run()`` returns a ``TimeSeriesDataset`` containing every forecast
point generated across the evaluation window, together with availability
metadata indicating when each prediction was made.

Passing ``start=None`` or ``end=None`` tells the pipeline to use the minimum
or maximum timestamp present in ``ground_truth`` automatically.


Evaluating results
------------------

Once you have predictions, pass them to ``EvaluationPipeline`` alongside the
ground truth to compute metrics:

.. code-block:: python

   from openstef_beam.backtesting import EvaluationPipeline, EvaluationConfig

   eval_config = EvaluationConfig()

   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=quantiles,                        # list[Quantile]
       window_metric_providers=metric_providers,   # per-window metrics
       global_metric_providers=metric_providers,   # aggregate metrics
   )

   report = eval_pipeline.run(
       ground_truth=versioned_ground_truth,
       predictions=predictions,
   )

The returned ``report`` is an ``EvaluationSubsetReport`` that groups metric
results by time window and target. Typical metrics include MAE, RMSE, and
skill scores relative to a naive baseline — the exact set depends on the
``metric_providers`` you supply.


Using the higher-level runner
-----------------------------

For multi-target evaluations, ``BacktestRunner`` wraps both pipelines and
handles storage and callbacks in one call:

.. code-block:: python

   from openstef_beam.backtesting import BacktestRunner

   runner = BacktestRunner(
       backtest_config=config,
       evaluation_config=eval_config,
       target_provider=my_target_provider,
       storage=my_storage,
   )

   runner.run_backtest_for_target(target=my_target, forecaster=forecaster)
   runner.run_evaluation_for_target(
       target=my_target,
       quantiles=quantiles,
       predictions=predictions,
   )

``BacktestRunner`` calls ``on_backtest_start``, ``on_backtest_complete``,
``on_evaluation_start``, and ``on_evaluation_complete`` hooks on any registered
callbacks, making it straightforward to add logging, alerting, or custom
persistence. See :doc:`advanced_customization` for details on writing your own
callbacks.


Visualising performance
-----------------------

``EvaluationSubsetReport`` exposes several ``create_by_*`` factory methods that
produce ``VisualizationOutput`` objects ready for rendering:

.. code-block:: python

   # Aggregate view across all targets
   viz = report.create_by_none(report=subset_report, metadata=target_metadata)

   # Break down by target
   viz_by_target = report.create_by_target(reports=report_tuples)

   # Compare multiple runs side-by-side
   viz_by_run = report.create_by_run_and_target(reports=run_report_dict)

.. note:: [VISUALIZATION: Side-by-side time-series plot comparing ground-truth load curve against backtest predictions for a single target, with shaded quantile bands and per-window RMSE annotations below the x-axis.]

Each ``VisualizationOutput`` can be rendered to your preferred backend (HTML,
PNG, or notebook inline) depending on the visualisation adapter configured in
your environment.


Common pitfalls
---------------

**Interval mismatch**
   If ``BacktestConfig.prediction_sample_interval`` differs from the
   forecaster's ``predict_sample_interval``, the pipeline raises a
   ``ValueError`` immediately. Align both before calling ``.run()``.

**Insufficient history at the start**
   The first training event needs enough historical data to fit the model. If
   ``start`` is too close to the beginning of your dataset, the first retrain
   may fail or produce a degraded model. Leave at least one full training
   window of data before ``start``.

**Timezone-naive datetimes**
   Pass timezone-aware ``datetime`` objects (e.g. ``timezone.utc``) for
   ``start`` and ``end``. Naive datetimes can cause silent misalignment when
   the pipeline aligns schedules to ``align_time``.


Next steps
----------

- :doc:`first_forecast` — build and run your first forecast end-to-end before
  adding a backtest loop.
- :doc:`advanced_customization` — write custom callbacks, metric providers,
  and forecaster mixins to extend the backtesting framework.