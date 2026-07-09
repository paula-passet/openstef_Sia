Backtesting
===========

Backtesting answers a critical question: how would your forecasting model have performed if it had been running in production over the past months or years? Unlike a simple train/test split, backtesting simulates the full operational lifecycle, including periodic retraining, data availability constraints, and multi-horizon evaluation. This page explains how to configure and run a backtest in OpenSTEF, and how to interpret the results.

.. mermaid:: /diagrams/user_guide/guides/backtesting_diagram_1.mmd

Why Backtesting Matters for Energy Forecasting
-----------------------------------------------

Energy forecasting models operate under strict temporal constraints. A day-ahead forecast submitted at 06:00 can only use data published before that moment. Weather forecasts update on their own schedule. Meter data arrives with latency. A model that looks good on a random holdout set may fail in production because it inadvertently used future information during evaluation.

Backtesting in OpenSTEF addresses this by replaying history as if it were happening in real time. The pipeline enforces that:

- Models are retrained only at scheduled intervals (not continuously).
- Predictions use only data that would have been *published* at prediction time.
- Evaluation segments results by lead time and availability, matching how forecasts are actually consumed.

This approach aligns with the :ref:`concept_beam` framework, which treats forecasting as a pipeline of composable, temporally-aware stages.


Preventing Lookahead with RestrictedHorizonVersionedTimeSeries
--------------------------------------------------------------

The foundation of realistic backtesting is preventing data leakage. When :class:`~openstef_beam.backtesting.backtest_pipeline.BacktestPipeline` calls your forecaster's ``predict`` or ``fit`` method, it does not pass a raw DataFrame. Instead, it provides a :class:`~openstef_beam.backtesting.restricted_horizon_timeseries.RestrictedHorizonVersionedTimeSeries` object.

This wrapper enforces a hard temporal boundary: calls to ``get_window`` will never return data with an ``available_at`` timestamp beyond the current simulation time. Even if the underlying dataset contains the full history, your model cannot accidentally access future values.

This guarantee is structural, not advisory. You do not need to manually filter data or trust that your feature pipeline respects time boundaries; the wrapper enforces it at the data access layer.


Configuring the Backtest
-------------------------

A backtest is configured through :class:`~openstef_beam.backtesting.backtest_pipeline.BacktestConfig`, which controls the simulation schedule:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig

   config = BacktestConfig(
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
       prediction_sample_interval=timedelta(minutes=15),
       align_time=time.fromisoformat("00:00+00"),
   )

The key parameters are:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Parameter
     - Purpose
   * - ``predict_interval``
     - How often the pipeline generates a new forecast (e.g., every 6 hours).
   * - ``train_interval``
     - How often the model is retrained (e.g., weekly).
   * - ``prediction_sample_interval``
     - The resolution of the output forecast (e.g., 15-minute intervals).
   * - ``align_time``
     - Reference time for aligning prediction schedules to regular clock times.

The ``predict_interval`` and ``train_interval`` should mirror your intended production schedule. If you plan to retrain weekly and predict every 6 hours, configure the backtest identically.


Event Generation and Pipeline Execution
-----------------------------------------

Internally, :class:`~openstef_beam.backtesting.backtest_event_generator.BacktestEventGenerator` translates the configuration into a chronologically ordered sequence of events. Training events always precede prediction events at the same timestamp, ensuring the model is up to date before generating forecasts.

The :class:`~openstef_beam.backtesting.backtest_pipeline.BacktestPipeline` then steps through these events:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)
   predictions = pipeline.run(
       ground_truth=ground_truth_data,
       predictors=predictor_data,
       start=None,  # Uses data minimum
       end=None,    # Uses data maximum
   )

The ``run`` method returns a versioned time series dataset containing all predictions, each tagged with the ``available_at`` timestamp indicating when that forecast was generated.

.. note::

   The ``prediction_sample_interval`` in your ``BacktestConfig`` must match the ``predict_sample_interval`` in your forecaster's :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestForecasterConfig`. A mismatch raises a ``ValueError``.


Evaluating Results with EvaluationPipeline
-------------------------------------------

Raw predictions are not directly interpretable. The same forecast point may appear in multiple prediction runs (generated at different ``available_at`` times) and serve different operational purposes depending on its lead time. The :class:`~openstef_beam.evaluation.EvaluationPipeline` slices predictions along three dimensions:

- **available_at** — when the forecast was generated (e.g., "day-ahead at 06:00").
- **lead_time** — how far ahead the forecast looks (e.g., 1 hour, 36 hours).
- **time_windows** — rolling evaluation windows for tracking performance over time.

Configure these dimensions through :class:`~openstef_beam.evaluation.EvaluationConfig`:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

The pipeline computes both windowed metrics (performance within each rolling window) and global metrics (aggregated over the full backtest period). It always includes observed probability as a calibration metric to assess whether your probabilistic forecasts are well-calibrated.


Interpreting Backtest Results
------------------------------

Backtest results should be examined at multiple levels of granularity:

**Per-window metrics** reveal whether performance is stable over time or degrading. Seasonal patterns in error (e.g., higher errors in winter when load is more volatile) are expected and informative.

**Per-lead-time metrics** show how accuracy degrades with forecast horizon. For energy forecasting, typical patterns include:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Lead time
     - Expected behavior
   * - 15 min – 1 hour
     - Dominated by persistence; ML models should clearly beat naive baselines.
   * - 1 – 6 hours
     - Weather becomes important; models should leverage NWP data effectively.
   * - 6 – 48 hours
     - Day-ahead regime; calendar features and weather forecasts drive accuracy.

**Calibration** (observed probability) tells you whether your quantile forecasts are reliable. A well-calibrated P10 quantile should be exceeded roughly 10% of the time. Poor calibration means your uncertainty estimates cannot be trusted for decision-making.

.. warning::

   A model that scores well on aggregated metrics but poorly on specific windows or lead times may be unsuitable for production. Always inspect the per-window breakdown before deploying.


Implementing a Forecaster for Backtesting
-------------------------------------------

Your forecaster must implement :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestForecasterMixin`, which requires:

- A ``fit`` method that accepts a :class:`~openstef_beam.backtesting.restricted_horizon_timeseries.RestrictedHorizonVersionedTimeSeries` and trains the model.
- A ``predict`` method that accepts the same type and returns a time series of quantile predictions (or ``None`` if insufficient data is available).
- A ``quantiles`` property listing the quantiles the model produces.

Returning ``None`` from ``predict`` is the correct behavior when data coverage is insufficient. The pipeline handles this gracefully and moves to the next event.

For a complete worked example, see :doc:`/tutorials/backtesting_quickstart`.


Relationship to the BEAM Framework
------------------------------------

Backtesting is one stage in the broader :ref:`concept_beam` architecture. The BEAM framework treats forecasting as a pipeline where each stage (data ingestion, feature engineering, model training, prediction, evaluation) is independently configurable and composable. The backtesting components described here (``BacktestPipeline``, ``EvaluationPipeline``) are designed to plug into this framework, enabling systematic comparison of models under identical conditions.

For production deployment patterns that build on backtesting results, see :doc:`/user_guide/guides/deployment`.