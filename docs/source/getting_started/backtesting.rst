Backtesting Your Models
=======================

This page walks through evaluating a forecasting model on historical data using
OpenSTEF BEAM's ``BacktestPipeline``. You will learn how to configure a backtest,
run it against versioned historical data, compute evaluation metrics, and inspect
the results. If you have not yet set up the library, see :doc:`installation` first.
For a minimal working forecast without backtesting, start with :doc:`quickstart`.

What backtesting does
---------------------

A naive train/test split tells you how a model performs on one fixed slice of
history. Backtesting goes further: it replays the past the way production would
have experienced it. At each prediction step the model can only see data that
was genuinely available at that moment in time, and the model is periodically
retrained on a rolling window of history — exactly as it would be in a live
system. This prevents data leakage and gives a realistic picture of operational
accuracy.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd

The ``BacktestPipeline`` class in ``openstef_beam.backtesting`` orchestrates this
loop. It consumes two ``VersionedTimeSeriesDataset`` objects — one for the target
(ground truth) and one for the predictor features — and returns a dataset of
predictions aligned with the original time axis.

Configuring the backtest
------------------------

``BacktestPipeline`` takes a ``BacktestConfig`` and a forecaster that implements
``BacktestForecasterMixin``. The config controls the cadence of the simulation:

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    config = BacktestConfig(
        # How often a new batch of predictions is generated
        predict_interval=timedelta(hours=1),
        # How often the model is retrained on fresh history
        train_interval=timedelta(days=7),
        # Granularity of each individual prediction sample
        prediction_sample_interval=timedelta(minutes=15),
        # Align prediction windows to a fixed clock time (e.g. midnight)
        align_time=True,
    )

.. note::

   ``prediction_sample_interval`` must match the ``predict_sample_interval``
   declared on your forecaster's own config. The pipeline raises a ``ValueError``
   at construction time if they differ, so mismatches are caught early.

The ``predict_interval`` and ``train_interval`` are independent. A common
production pattern is to predict every hour but only retrain once a week, which
is what the example above reflects.

Running the backtest
--------------------

Once you have a config and a forecaster, call ``BacktestPipeline.run()``:

.. code-block:: python

    from datetime import datetime
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig

    pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

    predictions = pipeline.run(
        ground_truth=ground_truth_dataset,   # VersionedTimeSeriesDataset
        predictors=predictor_dataset,        # VersionedTimeSeriesDataset
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
        show_progress=True,                  # prints a progress bar
    )

``run()`` returns a ``VersionedTimeSeriesDataset`` containing every prediction
made during the simulation, tagged with the timestamp at which each prediction
became available. Passing ``start=None`` or ``end=None`` lets the pipeline infer
the range from the data itself.

The ``show_progress=True`` flag is useful during development; disable it in
automated pipelines to keep logs clean.

Evaluating the results
----------------------

Raw predictions are only useful once you attach metrics. The ``EvaluationPipeline``
in ``openstef_beam.evaluation`` computes metrics across multiple dimensions
simultaneously: lead times, rolling time windows, and prediction availability
times.

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.evaluation import (
        EvaluationConfig,
        EvaluationPipeline,
        Window,
        metric_providers,
    )

    eval_config = EvaluationConfig(
        # When during the day predictions are "published" (D-1 at 06:00)
        available_ats=["D-1T06:00"],
        # Lead times to evaluate: 1-hour-ahead through 36-hour-ahead
        lead_times=["PT1H", "PT6H", "PT12H", "PT24H", "PT36H"],
        # Rolling 21-day evaluation window
        windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
    )

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.5, 0.9],
        window_metric_providers=[
            metric_providers.MAEProvider(),
            metric_providers.RMSEProvider(),
        ],
        global_metric_providers=[
            metric_providers.MAEProvider(),
            metric_providers.RMSEProvider(),
        ],
    )

    report = eval_pipeline.run(
        predictions=predictions,
        ground_truth=ground_truth_dataset,
    )

The returned ``EvaluationReport`` contains ``EvaluationSubsetReport`` objects
organised by lead time and availability time. Each subset report holds a list of
``SubsetMetric`` entries — one per rolling window timestamp — plus a single
``global`` entry that covers the entire evaluation period.

Understanding lead-time analysis
---------------------------------

Lead time is the gap between when a forecast is *generated* and the moment it
is *for*. A 1-hour-ahead forecast is almost always more accurate than a
36-hour-ahead one; the evaluation pipeline makes this degradation explicit.

.. code-block:: python

    # Inspect MAE at each lead time for the global window
    for subset in report.subsets:
        global_metric = next(m for m in subset.metrics if m.window == "global")
        print(
            f"Lead time {subset.filtering.lead_time} | "
            f"MAE = {global_metric.metrics['mae']:.3f}"
        )

.. note:: [VISUALIZATION: Line chart with lead time (hours) on the x-axis and MAE on the y-axis, showing accuracy degrading as lead time increases. A second line shows RMSE on the same axes for comparison.]

This view is critical for operational planning: a grid operator scheduling
day-ahead actions needs to know the 24-hour-ahead accuracy, not just the
average across all horizons.

Visualising results with AnalysisPipeline
-----------------------------------------

The ``AnalysisPipeline`` in ``openstef_beam.analysis`` turns evaluation reports
into charts. It accepts the same reports produced by ``EvaluationPipeline`` and
dispatches them to configurable ``VisualizationProvider`` objects.

.. code-block:: python

    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig

    analysis_config = AnalysisConfig(
        available_ats=eval_config.available_ats,
        lead_times=eval_config.lead_times,
    )

    analysis = AnalysisPipeline(config=analysis_config)
    visuals = analysis.run(reports=[(target_metadata, report)])

Each entry in ``visuals`` is a ``VisualizationOutput`` that can be rendered to
a file or displayed inline in a notebook. The pipeline groups outputs by target,
lead time, and time window so you can drill down from a fleet-wide summary to a
single substation.

.. note:: [VISUALIZATION: Grid of small multiples — one panel per lead time — each showing a time-series plot of observed vs. predicted load for a rolling 21-day window, with shaded quantile bands at 10th and 90th percentiles.]

Putting it all together
-----------------------

A complete backtest-to-report workflow looks like this:

.. code-block:: python

    from datetime import datetime, timedelta
    from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
    from openstef_beam.evaluation import (
        EvaluationConfig,
        EvaluationPipeline,
        Window,
        metric_providers,
    )
    from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig

    # 1. Configure and run the backtest
    backtest_config = BacktestConfig(
        predict_interval=timedelta(hours=1),
        train_interval=timedelta(days=7),
        prediction_sample_interval=timedelta(minutes=15),
        align_time=True,
    )
    pipeline = BacktestPipeline(config=backtest_config, forecaster=my_forecaster)
    predictions = pipeline.run(
        ground_truth=ground_truth_dataset,
        predictors=predictor_dataset,
        start=datetime(2024, 1, 1),
        end=datetime(2024, 6, 30),
    )

    # 2. Evaluate across lead times and rolling windows
    eval_config = EvaluationConfig(
        available_ats=["D-1T06:00"],
        lead_times=["PT1H", "PT6H", "PT24H", "PT36H"],
        windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
    )
    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.5, 0.9],
        window_metric_providers=[metric_providers.MAEProvider()],
        global_metric_providers=[metric_providers.RMSEProvider()],
    )
    report = eval_pipeline.run(predictions=predictions, ground_truth=ground_truth_dataset)

    # 3. Generate visualisations
    analysis = AnalysisPipeline(
        config=AnalysisConfig(
            available_ats=eval_config.available_ats,
            lead_times=eval_config.lead_times,
        )
    )
    visuals = analysis.run(reports=[(target_metadata, report)])

Common pitfalls
---------------

- **Mismatched sample intervals** — ``BacktestConfig.prediction_sample_interval``
  must equal the forecaster's ``predict_sample_interval``. The pipeline raises a
  ``ValueError`` immediately if they differ.
- **Insufficient warm-up data** — The first training event needs enough history
  to fit the model. Make sure your ``start`` datetime leaves at least one full
  training window of data before it.
- **Data leakage in feature engineering** — ``VersionedTimeSeriesDataset`` tracks
  when each data point became available. If you pre-compute features outside this
  structure using future data, the leakage protection is bypassed.

Next steps
----------

- :doc:`first_forecast` — build and run your first forecast before adding
  backtesting complexity.
- :doc:`advanced_customization` — implement a custom ``BacktestForecasterMixin``,
  add bespoke metric providers, or write your own ``VisualizationProvider``.