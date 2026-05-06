Backtesting Your Models
=======================

This page walks through evaluating a forecasting model on historical data using
``BacktestPipeline`` from ``openstef_beam``. By the end you will know how to configure
a backtest, run it over a historical window, and interpret the resulting evaluation
metrics and visualisations.

If you have not yet installed the library or run your first forecast, start with
:doc:`installation` and :doc:`first_forecast` first.

What is backtesting?
--------------------

A backtest replays history the way a live system would have experienced it. At each
step the pipeline is only allowed to see data that would have been available at that
moment in time — no future information leaks in. The model is retrained periodically,
predictions are generated on a regular cadence, and the outputs are compared against
the actual measurements that were recorded later.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd

This approach gives a realistic estimate of how a model would perform in production,
which is more meaningful than a simple train/test split on shuffled data.

Configuring the backtest
------------------------

All timing parameters live in ``BacktestConfig``. The three most important fields are:

- ``prediction_sample_interval`` — resolution of each individual forecast (default 15 min).
- ``predict_interval`` — how often a new forecast is generated during the replay (default 6 h).
- ``train_interval`` — how often the model is retrained on the growing history (default 7 days).

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting import BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
        align_time=time.fromisoformat("00:00+00"),
    )

``align_time`` anchors the prediction schedule to a fixed clock time so that forecast
boundaries stay consistent across days — useful when downstream consumers expect
forecasts at round hours.

.. note::
   ``prediction_sample_interval`` must match the resolution that your forecaster
   produces. ``BacktestPipeline`` raises a ``ValueError`` at construction time if
   they disagree, so mismatches are caught early.

Running the pipeline
--------------------

``BacktestPipeline`` requires a ``BacktestConfig`` and a forecaster that implements
``BacktestForecasterMixin`` (or ``BacktestBatchForecasterMixin`` for batch-optimised
models). Call ``pipeline.run()`` with the ground-truth time series, the predictor
features, and the start/end of the historical window you want to evaluate.

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_beam.backtesting import BacktestPipeline

    # Assume `my_forecaster` implements BacktestForecasterMixin
    # and `ground_truth`, `predictors` are TimeSeriesDataset objects
    # loaded for your target location.

    pipeline = BacktestPipeline(
        config=config,
        forecaster=my_forecaster,
    )

    predictions = pipeline.run(
        ground_truth=ground_truth,
        predictors=predictors,
        start=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end=datetime(2023, 6, 30, tzinfo=timezone.utc),
    )

``predictions`` is a ``TimeSeriesDataset`` containing every forecast the pipeline
generated during the replay window. Each forecast row carries the timestamp at which
it was *made*, the horizon it covers, and the predicted value — enough information to
reconstruct exactly what the live system would have dispatched.

Using the higher-level runner
-----------------------------

For evaluating multiple targets in one go, ``BacktestPipeline`` is typically driven by
a runner that also handles storage and callbacks. The runner calls
``run_backtest_for_target`` and ``run_evaluation_for_target`` in sequence:

.. code-block:: python

    from openstef_beam.backtesting import BacktestConfig
    from openstef_beam.evaluation import EvaluationConfig

    # The runner wires together the pipeline, storage, and callbacks.
    # Consult the API reference for the full runner interface.
    runner.run_backtest_for_target(
        target=my_target,
        forecaster=my_forecaster,
    )

    runner.run_evaluation_for_target(
        target=my_target,
        quantiles=[0.1, 0.5, 0.9],
        predictions=predictions,
    )

The runner pattern is covered in depth in :doc:`advanced_customization`.

Evaluation metrics
------------------

After the backtest produces predictions, ``EvaluationPipeline`` computes metrics by
comparing those predictions against the ground-truth measurements. Metrics are
organised into two scopes:

- **Window metrics** — computed over rolling or fixed sub-windows (e.g. per day, per
  week). Useful for spotting seasonal degradation.
- **Global metrics** — computed over the entire evaluation period. Useful for a single
  summary number per target.

Both are supplied as ``window_metric_providers`` and ``global_metric_providers`` when
constructing ``EvaluationPipeline``:

.. code-block:: python

    from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig

    eval_config = EvaluationConfig()

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.5, 0.9],
        window_metric_providers=metrics,
        global_metric_providers=metrics,
    )

    report = eval_pipeline.run(
        ground_truth=ground_truth,
        predictions=predictions,
    )

``report`` is an ``EvaluationSubsetReport`` that groups results by target, run name,
and (optionally) a user-defined group label. The report object is the input to all
visualisation helpers.

Visualising results
-------------------

Visualisation helpers accept the report and return a ``VisualizationOutput`` object.
Four grouping strategies are available depending on how you want to slice the results:

.. code-block:: python

    from openstef_beam.evaluation.visualization import SomeVisualizer

    # Single target, no grouping
    output = SomeVisualizer.create_by_none(report=report, metadata=target_metadata)

    # Compare multiple runs for the same target
    output = SomeVisualizer.create_by_run_and_target(reports=reports_by_run)

    # Compare runs across user-defined groups (e.g. season, region)
    output = SomeVisualizer.create_by_run_and_group(reports=reports_by_run_and_group)

.. note:: [VISUALIZATION: Example backtest performance chart — predicted vs. actual time series overlaid for a six-month window, with shaded quantile bands (10th–90th percentile) and a secondary panel showing the rolling MAE per week to highlight seasonal variation.]

The ``VisualizationOutput`` can be rendered to HTML, saved as an image, or embedded in
a report notebook — see the API reference for export options.

Common pitfalls
---------------

**Choosing intervals that don't divide evenly.**
  If ``train_interval`` is not a multiple of ``predict_interval``, the schedule can
  drift relative to ``align_time``. Keep the ratio an integer to avoid surprises.

**Evaluation window shorter than one train cycle.**
  If ``end - start < train_interval`` the model may never retrain during the backtest,
  so you are effectively evaluating a model trained on data from before the window.
  Use at least two or three ``train_interval`` lengths for a meaningful result.

**Mismatched sample intervals.**
  As noted above, ``BacktestPipeline`` validates this at construction time. If your
  raw data has gaps or irregular timestamps, resample it to a uniform grid before
  passing it in.

Next steps
----------

- :doc:`quickstart` — if you want a minimal end-to-end example before diving into
  backtesting configuration.
- :doc:`advanced_customization` — how to plug in custom forecasters, callbacks, and
  storage backends into the runner.
- :doc:`first_forecast` — step-by-step guide to building the forecaster object that
  you pass to ``BacktestPipeline``.