Backtesting Models with Historical Data
=======================================

Backtesting lets you evaluate how well a forecasting model would have performed
on historical data, without the risk of data leakage or look-ahead bias. Rather
than simply fitting a model to all available data and measuring in-sample error,
OpenSTEF's ``BacktestPipeline`` simulates the real operational environment:
predictions are generated at regular intervals, the model is periodically
retrained on only the data that would have been available at that point in time,
and the resulting forecasts are collected for offline analysis.

This page walks through the full backtesting workflow — configuring the pipeline,
running it against historical data, computing evaluation metrics, visualising
results, and comparing multiple models side by side. If you haven't yet produced
your first forecast, start with :doc:`first_forecast` before continuing here.

.. mermaid:: /diagrams/getting_started/backtesting_diagram_1.mmd

How OpenSTEF Backtesting Works
-------------------------------

The ``BacktestPipeline`` class drives the entire simulation. Internally it:

1. Generates a chronological sequence of *prediction events* spaced
   ``predict_interval`` apart.
2. Interleaves *retraining events* every ``train_interval``, each time
   fitting the model on only the historical data available up to that moment.
3. At each prediction event, calls the forecaster with the context window it
   would have had in production — no future data is visible.
4. Assembles all predictions into a ``VersionedTimeSeriesDataset`` that you
   can compare directly against the ground-truth series.

The key design principle is **temporal consistency**: the pipeline enforces that
no information from after a prediction timestamp can influence that prediction,
mirroring the constraints of a live deployment.

.. note::

   ``prediction_sample_interval`` in ``BacktestConfig`` must match
   ``predict_sample_interval`` in the forecaster's own configuration.
   A ``ValueError`` is raised immediately if they differ, so mismatches are
   caught before any computation begins.

Setting Up the Backtest Configuration
---------------------------------------

``BacktestConfig`` controls the three timing parameters that define the
simulation cadence:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestConfig

   config = BacktestConfig(
       # Resolution of the output forecast series
       prediction_sample_interval=timedelta(minutes=15),

       # How often a new forecast is generated during the simulation
       predict_interval=timedelta(hours=6),

       # How often the model is retrained on accumulated history
       train_interval=timedelta(days=7),

       # Reference time used to align prediction schedules (UTC midnight)
       align_time=time.fromisoformat("00:00+00"),
   )

The defaults (15-minute samples, 6-hour prediction cadence, weekly retraining)
are a reasonable starting point for typical grid-connected energy assets. Adjust
``train_interval`` downward if you expect the underlying load pattern to shift
quickly, or upward to reduce computational cost during experimentation.

Running the Pipeline
---------------------

``BacktestPipeline.run()`` accepts versioned time-series datasets for both the
target variable (``ground_truth``) and the input features (``predictors``), plus
optional ``start`` and ``end`` datetimes to narrow the evaluation window.

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting import BacktestPipeline

   # Assume `forecaster` is an already-instantiated model that implements
   # BacktestForecasterMixin, and `ground_truth` / `predictors` are
   # VersionedTimeSeriesDataset objects loaded from your data source.

   pipeline = BacktestPipeline(config=config, forecaster=forecaster)

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       show_progress=True,   # prints a progress bar
   )

The return value is a ``VersionedTimeSeriesDataset`` containing every forecast
generated during the simulation, indexed by both the *prediction timestamp* and
the *availability timestamp* (i.e., when that forecast would have been issued).
Passing ``start=None`` or ``end=None`` uses the full extent of the supplied data.

Evaluating Forecast Accuracy
------------------------------

Once you have the backtest predictions, align them with the ground-truth series
and compute your chosen metrics. OpenSTEF supports both deterministic metrics
(MAE, RMSE) and probabilistic metrics (quantile losses, rCRPS) through its
built-in analysis tooling.

.. code-block:: python

   import pandas as pd

   # Flatten the versioned predictions to a plain time series
   # (select the most-recently-issued forecast for each target timestamp)
   forecast_series = predictions.to_latest_forecast()

   # Ground truth as a plain Series aligned to the same index
   actuals = ground_truth.to_series()

   # Basic deterministic metrics
   common_idx = forecast_series.index.intersection(actuals.index)
   y_pred = forecast_series.loc[common_idx]
   y_true = actuals.loc[common_idx]

   mae  = (y_pred - y_true).abs().mean()
   rmse = ((y_pred - y_true) ** 2).mean() ** 0.5
   rmae = mae / y_true.abs().mean()   # relative MAE, scale-independent

   print(f"MAE:  {mae:.3f}")
   print(f"RMSE: {rmse:.3f}")
   print(f"rMAE: {rmae:.4f}")

For probabilistic forecasters that produce multiple quantiles, use the
``rCRPS`` (relative Continuous Ranked Probability Score) to capture the full
predictive distribution in a single number.

Visualising Results
--------------------

OpenSTEF ships with ``ForecastTimeSeriesPlotter``, which produces interactive
plots comparing forecasts against measurements. This is the recommended way to
spot systematic biases, seasonal degradation, or periods where the model
struggles.

.. code-block:: python

   from openstef_core.visualization import ForecastTimeSeriesPlotter

   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(actuals)
   plotter.add_model("MyForecaster", forecast=forecast_series)

   fig = plotter.plot(title="Backtest: MyForecaster vs Actuals")
   fig.show()   # opens an interactive Plotly figure

The resulting figure includes:

- A line chart of measured values alongside the model forecast.
- Shaded confidence bands when quantile forecasts are available.
- Interactive hover tooltips and zoom controls.

To track how accuracy evolves over the backtest window — useful for detecting
model drift or identifying optimal retraining intervals — use
``WindowedMetricVisualization``:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import WindowedMetricVisualization

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_over_time",
               metric="MAE",
               window=timedelta(days=14),
           ),
       ]
   )

This produces a time-series chart of MAE computed over a rolling 14-day window,
making it straightforward to see whether accuracy degrades towards the end of
each training cycle.

Comparing Multiple Models
--------------------------

The most common use of backtesting is to decide between candidate models before
deploying to production. Run the pipeline once per model, then compare their
metrics side by side.

.. code-block:: python

   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from openstef_core.types import Quantile

   results = {}
   for name, forecaster in {
       "XGBoost": xgb_forecaster,
       "LightGBM": lgbm_forecaster,
   }.items():
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       predictions = pipeline.run(
           ground_truth=ground_truth,
           predictors=predictors,
           start=datetime(2024, 1, 1, tzinfo=timezone.utc),
           end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       )
       results[name] = predictions

   # Visualise rMAE at the median quantile for each model
   analysis_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="rmae_comparison",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           GroupedTargetMetricVisualization(
               name="rcrps_comparison",
               metric="rCRPS",
           ),
       ]
   )

``GroupedTargetMetricVisualization`` renders bar charts and box plots grouped by
model, making it easy to identify which model performs best overall and which
targets are hardest to forecast for either candidate.

The internal model-selection logic also exposes ``_check_is_new_model_better``,
which compares a configurable ``model_selection_metric`` (quantile, metric name,
and optimisation direction) between an incumbent and a challenger. You can use
this programmatically to automate promotion decisions in a CI/CD pipeline.

Common Pitfalls
----------------

.. warning::

   **Mismatched sample intervals.** ``BacktestConfig.prediction_sample_interval``
   must equal the forecaster's ``predict_sample_interval``. A ``ValueError`` is
   raised at pipeline construction time if they differ — check both values when
   you see this error.

- **Too-short training windows.** If ``train_interval`` is much shorter than
  the forecaster's ``training_context_length``, early retraining events will
  have insufficient history and may produce degraded models. Start with weekly
  retraining and tighten only after profiling.

- **Evaluating on the training period.** Always set ``start`` to a point after
  the initial training burn-in period so that the first reported metrics
  correspond to a fully trained model, not a cold-start one.

- **Ignoring the availability dimension.** The returned
  ``VersionedTimeSeriesDataset`` records *when* each forecast was issued.
  If you flatten to the latest forecast without considering lead time, you may
  inadvertently mix short-horizon and long-horizon predictions in the same
  metric. Segment by lead time for a fair comparison.

Next Steps
-----------

With backtesting results in hand, the natural next step is to customise model
architecture, feature engineering, or hyperparameters to improve the metrics
you've measured. See :doc:`advanced_customization` for guidance on extending
OpenSTEF's built-in forecasters and plugging in your own models.

If you're still working through the basics, :doc:`first_forecast` covers the
full forecasting pipeline from data loading to producing a single prediction,
and :doc:`quickstart` provides the minimal working example to get something
running immediately.