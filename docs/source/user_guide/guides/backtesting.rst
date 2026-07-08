Backtesting
===========

Backtesting answers a critical question before deploying a forecasting model: how would this model have performed if it had been running in production over the past months or years? Unlike a simple train/test split, backtesting simulates the full operational lifecycle, including periodic retraining and strict enforcement that no future data leaks into predictions.

This page explains how to configure and run a backtest in OpenSTEF, and how to interpret the evaluation results that follow.

.. mermaid:: /diagrams/user_guide/guides/backtesting_diagram_1.mmd

Why Backtesting Matters for Energy Forecasting
-----------------------------------------------

Energy forecasting models operate under constraints that simple cross-validation ignores:

- **Data arrives with delays.** Weather forecasts, meter readings, and market prices each have different publication schedules. A model must only use data that was actually available at prediction time.
- **Models retrain on a schedule.** In production, you retrain weekly or daily, not on every new sample. Performance between retraining events can degrade.
- **Lead times vary.** A day-ahead forecast (36 hours out) faces fundamentally different uncertainty than a 15-minute-ahead forecast. Aggregating them into a single error metric hides important information.

OpenSTEF's backtesting framework addresses all three by replaying history as if it were happening in real time, then slicing the resulting predictions along multiple evaluation dimensions.


Preventing Lookahead with RestrictedHorizonVersionedTimeSeries
--------------------------------------------------------------

The foundation of realistic backtesting is preventing data leakage. When :class:`~openstef_beam.backtesting.backtest_pipeline.BacktestPipeline` calls your forecaster's ``predict`` or ``fit`` method, it does not pass a raw DataFrame. Instead, it provides a :class:`~openstef_beam.backtesting.restricted_horizon_timeseries.RestrictedHorizonVersionedTimeSeries` object.

This wrapper enforces a hard temporal boundary: calls to ``get_window`` will never return data published after the current simulation timestamp. Even if the underlying dataset contains the full history, the forecaster cannot access future information. This guarantee is structural, not merely conventional, so bugs in forecaster code cannot accidentally introduce lookahead bias.


Configuring the Backtest
-------------------------

The backtest schedule is controlled by :class:`~openstef_beam.backtesting.backtest_pipeline.BacktestConfig`, which has three key parameters:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Parameter
     - Default
     - Purpose
   * - ``predict_interval``
     - 6 hours
     - How often the pipeline generates a new forecast (simulating an operational cron job).
   * - ``train_interval``
     - 7 days
     - How often the model is retrained on all data available up to that point.
   * - ``prediction_sample_interval``
     - 15 minutes
     - The resolution of the output forecast (must match the forecaster's ``predict_sample_interval``).

A shorter ``predict_interval`` produces more prediction events and therefore richer evaluation data, at the cost of longer runtime. The ``train_interval`` should mirror your intended production retraining cadence so the backtest reflects realistic model staleness.

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting import BacktestConfig

   config = BacktestConfig(
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
   )


Running the BacktestPipeline
-----------------------------

The :class:`~openstef_beam.backtesting.backtest_pipeline.BacktestPipeline` orchestrates the simulation. Internally, it uses :class:`~openstef_beam.backtesting.backtest_event_generator.BacktestEventGenerator` to produce a chronologically ordered sequence of train and predict events.

Events are interleaved so that at any given timestamp, a train event always precedes a predict event. This ensures the model is freshly retrained before generating predictions at that moment.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=None,  # defaults to data start
       end=None,    # defaults to data end
   )

The ``run`` method returns a time series dataset containing all predictions, each tagged with an ``available_at`` timestamp indicating when that forecast was generated. This metadata is essential for the evaluation stage.

For a complete working example including data loading and forecaster setup, see :doc:`/tutorials/backtesting_quickstart`.


Evaluating Results with EvaluationPipeline
-------------------------------------------

Raw predictions are not directly interpretable. The :class:`~openstef_beam.evaluation.EvaluationPipeline` slices them along three dimensions to produce meaningful metrics:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Dimension
     - What it captures
   * - ``available_at``
     - When the forecast was issued (e.g., "day-ahead at 06:00"). Filters predictions to those matching a specific operational deadline.
   * - ``lead_time``
     - The gap between forecast issuance and the target timestamp (e.g., 1 hour, 36 hours). Reveals how accuracy degrades with horizon.
   * - ``windows``
     - Rolling time windows over the evaluation period (e.g., 21-day windows). Shows whether performance is stable or drifting over time.

These dimensions are configured via :class:`~openstef_beam.evaluation.EvaluationConfig`:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
   )

The pipeline always includes observed probability as a calibration metric, ensuring that probabilistic forecasts are assessed for reliability as well as sharpness. For more on probabilistic evaluation, see :doc:`/user_guide/guides/probabilistic_forecasting`.


Interpreting Backtest Metrics
------------------------------

Per-window vs. aggregated metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Global metrics (computed over the entire backtest period) give you a single summary number, but they can mask seasonal patterns or regime changes. Per-window metrics reveal:

- **Seasonal degradation** (e.g., worse performance in winter when load is more volatile).
- **Model drift** (e.g., gradual accuracy loss between retraining events).
- **Data quality issues** (e.g., a window with anomalously high error due to missing predictors).

Always inspect per-window results before relying on the aggregate.

What "good" looks like
^^^^^^^^^^^^^^^^^^^^^^

Energy forecasting accuracy depends heavily on the target type and horizon. Some rough benchmarks:

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Target type
     - Day-ahead RMAE (median)
     - Intraday RMAE (median)
   * - Transmission substation
     - 2-5%
     - 1-3%
   * - Distribution feeder
     - 5-15%
     - 3-8%
   * - Individual prosumer
     - 30-60%
     - 20-40%

These ranges are indicative. The BEAM framework provides a structured way to compare your model against baselines and track improvements over time; see :ref:`concept_beam` for the conceptual foundation.

.. warning::

   A model that appears accurate on aggregate but shows high variance across windows may be unreliable in production. Stability matters as much as average accuracy for operational decision-making.


Relationship to the BEAM Framework
------------------------------------

Backtesting is one component of the broader BEAM (Benchmarking for Energy Accuracy Metrics) framework described in :ref:`concept_beam`. While this page covers the mechanics of running a single backtest, BEAM adds:

- Standardized comparison across multiple models and targets.
- Automated analysis and visualization pipelines.
- Consistent reporting formats for stakeholder communication.

If you are evaluating multiple candidate models or comparing against a baseline, the benchmark framework (``openstef_beam.benchmarking``) wraps the backtest and evaluation pipelines into a single orchestrated workflow.