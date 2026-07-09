Backtesting
===========

Backtesting answers a critical question before deploying any forecasting model: *how would this model have performed if it had been running in production over the past months or years?* Unlike a simple train/test split, backtesting simulates the full operational lifecycle, including periodic retraining, data availability constraints, and the passage of time.

This page explains how to configure and run a backtest in OpenSTEF, and how to interpret the resulting metrics across different forecast horizons and time windows.

.. mermaid:: /diagrams/user_guide/guides/backtesting_diagram_1.mmd

Why backtesting matters for energy forecasting
----------------------------------------------

Energy forecasting models operate under constraints that simple cross-validation ignores:

- **Data arrives with delays.** Weather forecasts, meter readings, and market prices each have different publication schedules. A model evaluated without respecting these delays will appear more accurate than it truly is.
- **Models are retrained periodically.** In production, you retrain weekly or daily, not on every new sample. Backtesting must replicate this cadence.
- **Accuracy varies by lead time.** A 15-minute-ahead forecast is fundamentally different from a 36-hour-ahead forecast. Aggregating them into a single score hides important failure modes.

OpenSTEF's backtesting framework addresses all three concerns through a pipeline that enforces temporal integrity at every step.


Preventing lookahead with RestrictedHorizonVersionedTimeSeries
--------------------------------------------------------------

The most common backtesting mistake is data leakage: accidentally allowing the model to see future information during training or prediction. OpenSTEF prevents this structurally rather than relying on discipline.

When :class:`~openstef_beam.backtesting.BacktestPipeline` invokes your forecaster's ``fit`` or ``predict`` method, it does not pass raw DataFrames. Instead, it provides a :class:`~openstef_beam.backtesting.restricted_horizon_timeseries.RestrictedHorizonVersionedTimeSeries` object. This wrapper enforces a hard temporal boundary: calls to ``get_window`` will never return data published after the current simulation timestamp, regardless of what exists in the underlying dataset.

This means your :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestForecasterMixin` implementation cannot accidentally peek into the future. The guarantee is architectural, not contractual.


Configuring the BacktestPipeline
---------------------------------

The pipeline requires two components: a :class:`~openstef_beam.backtesting.BacktestConfig` that defines the simulation schedule, and a forecaster that implements :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestForecasterMixin`.

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
     - How often the pipeline generates a new forecast (e.g., every 6 hours). Smaller intervals produce more evaluation points but take longer to run.
   * - ``train_interval``
     - How often the model is retrained (e.g., every 7 days). This should mirror your production retraining cadence.
   * - ``prediction_sample_interval``
     - The resolution of the output forecast (e.g., 15-minute intervals). Must match the forecaster's ``predict_sample_interval``.
   * - ``align_time``
     - A reference time to align prediction schedules to regular clock boundaries.


Event generation and execution
------------------------------

Internally, :class:`~openstef_beam.backtesting.backtest_event_generator.BacktestEventGenerator` creates an ordered sequence of train and predict events. Events are sorted chronologically, with training events preceding prediction events at the same timestamp. This ensures the model is always freshly trained before it predicts.

The pipeline then iterates through these events:

- **Train events** call ``forecaster.fit(data)`` where ``data`` is a :class:`~openstef_beam.backtesting.restricted_horizon_timeseries.RestrictedHorizonVersionedTimeSeries` restricted to the current simulation time.
- **Predict events** call ``forecaster.predict(data)`` under the same restriction, producing forecasts for the configured horizon.

The ``run`` method orchestrates the full simulation:

.. code-block:: python

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=None,  # defaults to data start
       end=None,    # defaults to data end
   )

The result is a time series dataset containing all predictions, each tagged with an ``available_at`` timestamp indicating when that forecast was generated.


Evaluating results with EvaluationPipeline
------------------------------------------

Raw predictions are not directly interpretable. The :class:`~openstef_beam.evaluation.EvaluationPipeline` slices them along three dimensions to produce meaningful metrics:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Dimension
     - What it captures
   * - ``available_at``
     - Filters predictions by when they were generated (e.g., "day-ahead at 06:00"). This simulates operational deadlines.
   * - ``lead_time``
     - Groups predictions by how far ahead they look (e.g., 1 hour, 12 hours, 36 hours). Accuracy typically degrades with longer lead times.
   * - ``windows``
     - Rolling time windows for computing metrics (e.g., 21-day windows). This reveals whether performance is stable or drifting over time.

Configure the evaluation with :class:`~openstef_beam.evaluation.EvaluationConfig`:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline

   eval_config = EvaluationConfig(
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       lead_times=[LeadTime.from_string("PT36H")],
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

The pipeline always includes observed probability as a calibration metric, ensuring that probabilistic forecasts are evaluated for reliability as well as sharpness. See :ref:`concept_beam` for the conceptual framework behind this multi-dimensional evaluation.


Interpreting backtest results
-----------------------------

Per-window vs aggregated metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The evaluation report contains both windowed metrics (computed over rolling time periods) and global metrics (aggregated across the full backtest). Use them differently:

- **Windowed metrics** reveal temporal patterns: seasonal degradation, concept drift after regime changes, or recovery after retraining. If your RMAE spikes in a particular window, investigate what changed in that period.
- **Global metrics** provide a single summary for model comparison. Use these when selecting between model architectures or hyperparameter configurations.

What good looks like
^^^^^^^^^^^^^^^^^^^^

Energy forecasting accuracy depends heavily on the target (solar, wind, load), the lead time, and the available predictors. Some general guidelines:

- **Relative MAE (RMAE)** below 1.0 means your model outperforms a naive persistence baseline. Values of 0.3-0.6 are typical for well-tuned load forecasts at day-ahead horizons.
- **Calibration (observed probability)** should track the nominal quantile levels. If your P10 quantile contains 25% of observations, the model is overconfident.
- **Stability across windows** matters as much as the average. A model with slightly higher average error but consistent performance is often preferable to one that is brilliant in summer and terrible in winter.

For a deeper discussion of the BEAM evaluation methodology and how these metrics compose into a holistic assessment, see :doc:`/user_guide/concepts/beam`.


Practical considerations
------------------------

- **Backtest duration**: Use at least one full year to capture seasonal effects. Shorter backtests risk overfitting to a single season.
- **Train interval alignment**: Match your backtest's ``train_interval`` to your planned production schedule. Testing with daily retraining but deploying with weekly retraining will give misleading results.
- **Computational cost**: Each predict event generates a full forecast horizon. With ``predict_interval=timedelta(hours=1)`` over a year, that is roughly 8,760 prediction runs. Start with larger intervals for initial experiments.

.. warning::

   The ``prediction_sample_interval`` in your :class:`~openstef_beam.backtesting.BacktestConfig` must exactly match the ``predict_sample_interval`` in your :class:`~openstef_beam.backtesting.backtest_forecaster.BacktestForecasterConfig`. A mismatch raises a ``ValueError`` at pipeline initialization.

For a complete worked example including data loading, pipeline setup, evaluation, and visualization, see the :doc:`/tutorials/backtesting_quickstart` tutorial.