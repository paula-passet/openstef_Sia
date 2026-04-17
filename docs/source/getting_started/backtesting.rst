Backtesting Your Models
=======================

Backtesting lets you measure how well a forecasting model would have performed on
historical data before deploying it in production. Rather than evaluating a single
static model, OpenSTEF's ``BacktestPipeline`` replays your history in chronological
order — generating predictions at regular intervals and retraining the model
periodically — so the evaluation faithfully mirrors the operational conditions the
model will face in the real world.

This page walks through configuring and running a backtest, then evaluating and
visualising the results. For installation instructions see :doc:`installation`, and
for a minimal working example of a live forecast see :doc:`quickstart`.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd

How the pipeline works
----------------------

``BacktestPipeline`` enforces two key constraints that distinguish a realistic
backtest from a naive train/test split:

- **Temporal consistency** — at every prediction step the pipeline wraps the
  input data in a ``RestrictedHorizonVersionedTimeSeries`` so that no future
  observations can leak into the model.
- **Periodic retraining** — the model is retrained on a configurable schedule
  (``train_interval``), matching the cadence you would use in production.

The pipeline is driven by ``BacktestConfig``, which controls the three timing
parameters that matter most:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Parameter
     - Default
     - Meaning
   * - ``prediction_sample_interval``
     - 15 minutes
     - Resolution of each individual forecast (must match the forecaster's own interval)
   * - ``predict_interval``
     - 6 hours
     - How often a new forecast is generated during the replay
   * - ``train_interval``
     - 7 days
     - How often the model is retrained on the growing history

Configuring a backtest
----------------------

Import ``BacktestConfig`` and ``BacktestPipeline`` from the ``openstef_beam``
backtesting package:

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting.backtest_pipeline import BacktestConfig, BacktestPipeline

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
        align_time=time.fromisoformat("00:00+00"),
    )

``align_time`` anchors the prediction schedule to a fixed wall-clock reference so
that forecast timestamps stay aligned to round hours across daylight-saving
transitions.

.. note::
   ``prediction_sample_interval`` must equal the ``predict_sample_interval`` set on
   your forecaster. The pipeline raises a ``ValueError`` at construction time if
   they differ, so mismatches are caught before any data is processed.

Running the backtest
--------------------

``BacktestPipeline`` requires a forecaster that implements
``BacktestForecasterMixin`` (single-step) or ``BacktestBatchForecasterMixin``
(vectorised). Pass your configured forecaster together with the backtest config,
then call ``run`` with the historical ground-truth and predictor datasets:

.. code-block:: python

    from datetime import datetime, timezone

    # forecaster is your model implementing BacktestForecasterMixin
    pipeline = BacktestPipeline(
        config=config,
        forecaster=forecaster,
    )

    predictions = pipeline.run(
        ground_truth=ground_truth_dataset,   # VersionedTimeSeriesDataset
        predictors=predictor_dataset,        # VersionedTimeSeriesDataset
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 30, tzinfo=timezone.utc),
        show_progress=True,
    )

``run`` returns a ``TimeSeriesDataset`` containing every prediction generated
during the replay window. Passing ``start=None`` or ``end=None`` uses the
earliest and latest timestamps present in the input data.

Evaluating the results
----------------------

Once you have predictions, pass them through ``EvaluationPipeline`` to compute
metrics against the observed ground truth:

.. code-block:: python

    from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline, EvaluationConfig
    from openstef_beam.evaluation import Window
    from openstef_core.datasets import Quantile

    eval_config = EvaluationConfig()

    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],   # 0.5 (median) is required
        window_metric_providers=metrics,
        global_metric_providers=metrics,
    )

    report = eval_pipeline.run(
        predictions=predictions,
        ground_truth=ground_truth_dataset,
        target_column="load",
    )

The ``quantiles`` list must include ``0.5``; the pipeline raises a ``ValueError``
otherwise. The returned ``EvaluationReport`` contains both global summary metrics
and windowed time-series metrics that you can inspect directly or feed into the
analysis pipeline.

.. note::
   Metrics are segmented by ``available_at`` and lead time, so you can compare
   short-horizon accuracy (e.g. 1-hour ahead) against long-horizon accuracy
   (e.g. 24-hour ahead) from the same backtest run.

Visualising performance over time
----------------------------------

``AnalysisPipeline`` turns an ``EvaluationReport`` into plots. The most useful
visualisation for a backtest is ``WindowedMetricVisualization``, which shows how
a metric evolves across the evaluation period using a rolling window:

.. code-block:: python

    from datetime import timedelta
    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import (
        WindowedMetricVisualization,
        GroupedTargetMetricVisualization,
    )
    from openstef_beam.evaluation import Window
    from openstef_core.datasets import Quantile

    analysis_config = AnalysisConfig(
        visualization_providers=[
            # Rolling MAE over a 7-day window
            WindowedMetricVisualization(
                name="mae_7d",
                metric="MAE",
                window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
            ),
            # Rolling rCRPS over a 21-day window (probabilistic sharpness)
            WindowedMetricVisualization(
                name="rcrps_21d",
                metric="rCRPS",
                window=Window(lag=timedelta(hours=0), size=timedelta(days=21)),
            ),
            # Cross-target comparison of relative MAE
            GroupedTargetMetricVisualization(
                name="rmae_grouped",
                metric="rMAE",
                quantile=Quantile(0.5),
            ),
        ]
    )

    from openstef_beam.analysis.analysis_pipeline import AnalysisPipeline

    analysis_pipeline = AnalysisPipeline(config=analysis_config)

.. note:: [VISUALIZATION: Line chart produced by WindowedMetricVisualization. The X-axis spans the backtest period (e.g. Jan–Jun 2024). The Y-axis shows the chosen metric (MAE or rCRPS). Each point represents the metric computed over the preceding rolling window. A rising trend indicates model degradation between retraining events; a sharp drop after a train event confirms the retrain improved accuracy.]

Choosing window sizes is a trade-off: a short window (7 days) highlights rapid
changes in accuracy but is noisier; a long window (30 days) smooths out
day-to-day variation and reveals seasonal trends.

Putting it all together
-----------------------

The ``BenchmarkPipeline`` (used in production benchmark runs) wires
``BacktestPipeline``, ``EvaluationPipeline``, and ``AnalysisPipeline`` together
automatically. For exploratory work or custom integrations, calling each pipeline
in sequence as shown above gives you full control over which targets, date ranges,
and metrics to include.

A minimal end-to-end script looks like this:

.. code-block:: python

    from datetime import datetime, timedelta, time, timezone
    from openstef_beam.backtesting.backtest_pipeline import BacktestConfig, BacktestPipeline
    from openstef_beam.evaluation.evaluation_pipeline import EvaluationPipeline, EvaluationConfig
    from openstef_beam.analysis.analysis_pipeline import AnalysisPipeline
    from openstef_beam.analysis import AnalysisConfig
    from openstef_beam.analysis.visualizations import WindowedMetricVisualization
    from openstef_beam.evaluation import Window

    # 1. Configure and run the backtest
    backtest_config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),
        predict_interval=timedelta(hours=6),
        train_interval=timedelta(days=7),
        align_time=time.fromisoformat("00:00+00"),
    )

    pipeline = BacktestPipeline(config=backtest_config, forecaster=forecaster)
    predictions = pipeline.run(
        ground_truth=ground_truth_dataset,
        predictors=predictor_dataset,
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 6, 30, tzinfo=timezone.utc),
    )

    # 2. Evaluate
    eval_pipeline = EvaluationPipeline(
        config=EvaluationConfig(),
        quantiles=[0.1, 0.5, 0.9],
        window_metric_providers=metrics,
        global_metric_providers=metrics,
    )
    report = eval_pipeline.run(
        predictions=predictions,
        ground_truth=ground_truth_dataset,
        target_column="load",
    )

    # 3. Visualise
    analysis_pipeline = AnalysisPipeline(
        config=AnalysisConfig(
            visualization_providers=[
                WindowedMetricVisualization(
                    name="mae_7d",
                    metric="MAE",
                    window=Window(lag=timedelta(hours=0), size=timedelta(days=7)),
                )
            ]
        )
    )

Common pitfalls
---------------

- **Mismatched sample intervals** — ensure ``BacktestConfig.prediction_sample_interval``
  equals your forecaster's ``predict_sample_interval`` or the pipeline will raise
  a ``ValueError`` on construction.
- **Too short a backtest window** — a window shorter than ``train_interval`` means
  the model is never retrained during the replay, which may not reflect production
  behaviour.
- **Missing the median quantile** — ``EvaluationPipeline`` requires ``0.5`` in the
  quantiles list; omitting it raises a ``ValueError``.
- **Data leakage** — always supply data as a ``VersionedTimeSeriesDataset`` so the
  pipeline can apply the restricted-horizon wrapper correctly. Passing a plain
  ``DataFrame`` bypasses the temporal guard.

Next steps
----------

- :doc:`first_forecast` — build and run your first live forecast before backtesting it.
- :doc:`advanced_customization` — implement a custom ``BacktestForecasterMixin`` to
  plug your own model into the pipeline.
- :doc:`quickstart` — a minimal working example if you want to get something running
  immediately.