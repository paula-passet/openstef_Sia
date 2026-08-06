Backtesting
===========

Backtesting answers a deceptively simple question: "How would this model have performed if we had deployed it six months ago?" A naive train/test split cannot answer this reliably because it ignores the temporal dynamics of real operations, where models are retrained on a schedule, data arrives with delays, and forecasts at different lead times have different accuracy profiles.

OpenSTEF's backtesting framework replays history as if it were happening in real time. At each simulated moment, the model sees only data that would have been available at that point. This prevents *lookahead bias*, the most common source of over-optimistic offline evaluations in energy forecasting.

This page explains how to configure and run a backtest, then evaluate the results across the dimensions that matter for operational decision-making.

.. mermaid::

   graph LR
       A[(Historical Data)] --> B[BacktestPipeline]
       B --> C[Step t1: Train]
       C --> D[Step t1: Predict]
       D --> E[Step t2: Train]
       E --> F[Step t2: Predict]
       F --> G[Step tN: ...]
       G --> H[EvaluationPipeline]
       H --> I[Per-Horizon Metrics]
   
       J([RestrictedHorizonVersionedTimeSeries]) -.->|blocks future| C
       J -.->|blocks future| E
   
       D -->|15min; 1h; 4h| H
       F -->|15min; 1h; 4h| H
   
       class B,C,D,E,F,G primary
       class A,I secondary
       class J,H accent
   
       classDef primary fill:#00D9C5,stroke:#1E3A5F,stroke-width:2px,color:#000
       classDef secondary fill:#1E3A5F,stroke:#00D9C5,stroke-width:2px,color:#fff
       classDef accent fill:#e6f7f5,stroke:#00D9C5,stroke-width:2px,color:#000

Why Simple Train/Test Splits Fail
----------------------------------

Energy forecasting models operate under constraints that a single holdout split cannot capture:

- **Scheduled retraining**: In production, models are retrained periodically (e.g., weekly). A single fit on all training data overstates performance.
- **Data publication delays**: Weather forecasts, meter readings, and market data become available at different times. A model evaluated on perfectly aligned data will appear better than it actually is.
- **Lead-time dependence**: A forecast made 15 minutes ahead is fundamentally different from one made 36 hours ahead. Aggregating them into a single metric hides critical performance variation.

OpenSTEF's backtesting framework addresses all three by simulating the operational loop: generate events, train on schedule, predict with restricted data, then evaluate along multiple dimensions.


Preventing Lookahead with Restricted Data Access
-------------------------------------------------

The foundation of realistic backtesting is :class:`~openstef_beam.backtesting.restricted_horizon_timeseries.RestrictedHorizonVersionedTimeSeries`. This wrapper sits between the forecaster and the underlying dataset, enforcing a hard temporal boundary (the "horizon"). When the forecaster calls ``get_window()``, the wrapper silently filters out any data published after the current simulation time.

Your forecaster never needs to implement lookahead prevention itself. By implementing :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestForecasterMixin`, its ``fit()`` and ``predict()`` methods receive a ``RestrictedHorizonVersionedTimeSeries`` instance that makes future data simply invisible.

.. code-block:: python

   class MyForecaster(BacktestForecasterMixin):
       def predict(self, data: RestrictedHorizonVersionedTimeSeries):
           # data.get_window() automatically blocks future access
           window = data.get_window(start, end)
           return self.model.predict(window)


Configuring the Backtest
------------------------

:class:`~openstef_beam.backtesting.BacktestConfig` controls the simulation schedule with three key parameters:

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Parameter
     - Default
     - Purpose
   * - ``predict_interval``
     - 6 hours
     - How often the pipeline generates a new forecast
   * - ``train_interval``
     - 7 days
     - How often the model is retrained on accumulated data
   * - ``prediction_sample_interval``
     - 15 minutes
     - Resolution of the output forecast time series

The ``align_time`` parameter (default: midnight UTC) ensures prediction events snap to operationally meaningful times rather than arbitrary offsets from the start of the backtest window.

.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig

   config = BacktestConfig(
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
   )


Running the Pipeline
--------------------

:class:`~openstef_beam.backtesting.BacktestPipeline` orchestrates the full simulation. Internally, it uses :class:`~openstef_beam.backtesting.backtest_event_generator.BacktestEventGenerator` to produce a chronologically ordered sequence of train and predict events. Training events always precede prediction events at the same timestamp, ensuring the model is up to date before forecasting.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=start_dt,
       end=end_dt,
   )

The ``run()`` method returns a ``TimeSeriesDataset`` containing all predictions, each tagged with an ``available_at`` timestamp indicating when that forecast was generated. This metadata is essential for the evaluation stage.

.. note::

   The pipeline validates that ``config.prediction_sample_interval`` matches your forecaster's ``predict_sample_interval``. A mismatch raises a ``ValueError`` immediately rather than producing silently misaligned results.


Event Generation Logic
^^^^^^^^^^^^^^^^^^^^^^

The :class:`~openstef_beam.backtesting.backtest_event_generator.BacktestEventGenerator` creates two interleaved streams:

- **Train events** at every ``train_interval``, starting from the earliest point where sufficient training context exists.
- **Predict events** at every ``predict_interval``, starting only after the first training event completes.

Events are merged chronologically. At each predict event, the forecaster produces a forecast covering multiple future time steps (and therefore multiple lead times). A predict event is skipped if the available context data has insufficient coverage, preventing unreliable predictions from entering the evaluation.


Evaluating Results
------------------

Raw predictions are not directly comparable because they span different lead times and were generated at different moments. :class:`~openstef_beam.evaluation.EvaluationPipeline` slices the prediction dataset along three dimensions to produce meaningful metrics:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Dimension
     - What it captures
   * - ``available_at``
     - When the forecast was issued (e.g., "day-ahead at 06:00")
   * - ``lead_time``
     - How far ahead the forecast looks (e.g., 1h, 12h, 36h)
   * - ``windows``
     - Rolling time periods for detecting performance drift

Each combination of these dimensions produces a separate metric calculation, giving you a multi-faceted view of model quality.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
   )

The evaluation pipeline automatically includes calibration metrics (observed probability) alongside any custom metric providers you supply, such as RMAE or RCRPS.


Interpreting Backtest Metrics
-----------------------------

Per-window vs. aggregated metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Global metrics (computed over the entire backtest period) tell you the model's average quality. Windowed metrics (computed over rolling periods) reveal whether performance is stable or degrading. In energy forecasting, seasonal effects are strong: a model that performs well in summer may struggle in winter. Always inspect windowed metrics to catch this.

What "good" looks like
^^^^^^^^^^^^^^^^^^^^^^

Energy forecasting accuracy depends heavily on the prediction target and lead time. Some rules of thumb:

- **Very short-term (< 1h)**: Persistence baselines are hard to beat. Your model should clearly outperform naive persistence.
- **Short-term (1-6h)**: Weather-driven models typically achieve 3-8% RMAE for load forecasting at this horizon.
- **Day-ahead (12-36h)**: 5-15% RMAE is typical for aggregated load; solar and wind have higher variability.

Calibration (observed probability matching nominal quantile levels) is equally important for probabilistic forecasts. A well-calibrated model's 90% prediction interval should contain the actual value approximately 90% of the time across all windows.

For a deeper discussion of evaluation methodology and the metrics framework, see :ref:`concept_beam`.


Practical Considerations
------------------------

- **Backtest duration**: Use at least one full year to capture seasonal patterns. Shorter backtests risk misleading conclusions.
- **Train interval trade-offs**: Frequent retraining (e.g., daily) is more realistic but slower to execute. Weekly retraining is a reasonable default for most energy forecasting applications.
- **Predict interval vs. sample interval**: The predict interval controls how often a *new* forecast is issued. The sample interval controls the resolution within each forecast. A 6-hour predict interval with 15-minute samples means each forecast covers multiple hours at quarter-hour granularity.
- **Batch prediction**: For models that benefit from batched inference (e.g., neural networks), implement :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestBatchForecasterMixin` instead of the single-prediction mixin.

.. warning::

   Backtesting is computationally expensive. A one-year backtest with 6-hour predict intervals and weekly retraining generates approximately 1,460 prediction events and 52 training events. Plan compute resources accordingly, or use the benchmark framework (``openstef_beam.benchmarking``) which adds parallelization and result caching.


For a hands-on walkthrough with real data, see :doc:`/tutorials/backtesting_quickstart`. For the conceptual foundations of the BEAM evaluation framework, see :doc:`/user_guide/concepts/beam`.