Backtesting
===========

Backtesting lets you evaluate how well a forecasting model would have performed on
historical data — without ever touching future observations. Rather than training once
and hoping for the best, you replay the operational environment: the model trains on
data that was genuinely available at each point in time, generates forecasts, and those
forecasts are later compared against what actually happened. This page walks through
the full workflow: configuring a backtest, running it, computing evaluation metrics,
and comparing multiple models side by side.

If you haven't yet built your first forecast, start with :doc:`first_forecast` before
continuing here. For customising model internals, see :doc:`advanced_customization`.

.. note::

   [DIAGRAM: Timeline showing the rolling backtest loop — training window, prediction
   horizon, retrain trigger, and evaluation window advancing through historical data]

How OpenSTEF Backtesting Works
-------------------------------

OpenSTEF's backtesting engine is built around two core classes: ``BacktestConfig`` and
``BacktestPipeline``. Together they simulate the operational forecasting loop as it
would have run in production:

1. At each **train event**, the model is fitted on all data available up to that
   moment.
2. At each **predict event**, the fitted model generates a forecast for the configured
   horizon.
3. The pipeline collects every prediction into a ``VersionedTimeSeriesDataset`` that
   you can then compare against ground truth.

The key design guarantee is **no data leakage**: the pipeline enforces temporal
consistency so that training data never includes observations that post-date the
training timestamp. This makes backtest results directly comparable to live
performance.

.. note::

   The ``prediction_sample_interval`` set in ``BacktestConfig`` must match the
   ``predict_sample_interval`` of your forecaster. OpenSTEF raises a ``ValueError``
   at construction time if these differ, catching misconfiguration early.

Setting Up a Backtest
----------------------

Start by importing the relevant classes and preparing your datasets:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef.backtesting import BacktestConfig, BacktestPipeline
   from openstef.datasets import VersionedTimeSeriesDataset

   # Load historical ground truth (the target variable, e.g. load in MW)
   ground_truth = VersionedTimeSeriesDataset.from_csv("load_history.csv")

   # Load predictor features (weather, calendar flags, etc.)
   predictors = VersionedTimeSeriesDataset.from_csv("features_history.csv")

Next, configure the backtest. The three most important intervals are:

- ``prediction_sample_interval`` — the resolution of your time series (e.g. 15 min).
- ``predict_interval`` — how often a new forecast is issued (e.g. every hour).
- ``train_interval`` — how often the model is retrained (e.g. every week).

.. code-block:: python

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=1),
       train_interval=timedelta(days=7),
   )

Then attach a forecaster and run:

.. code-block:: python

   from openstef.forecasting import MyForecaster, ForecasterConfig

   forecaster_config = ForecasterConfig(
       predict_sample_interval=timedelta(minutes=15),
   )
   forecaster = MyForecaster(config=forecaster_config)

   pipeline = BacktestPipeline(config=config, forecaster=forecaster)

   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True,
   )

``pipeline.run()`` returns a ``VersionedTimeSeriesDataset`` containing every forecast
the model would have issued during the evaluation window, tagged with the timestamp at
which each forecast was available.

Computing Evaluation Metrics
-----------------------------

OpenSTEF ships deterministic and probabilistic metrics in
``openstef_beam.metrics``. For deterministic forecasts the most commonly used
functions are:

.. code-block:: python

   import numpy as np
   from openstef_beam.metrics.metrics_deterministic import mae, mape, rmae

   # Align predictions with ground truth on a shared index
   y_true = ground_truth.to_numpy()
   y_pred = predictions.to_numpy()

   print(f"MAE:  {mae(y_true, y_pred):.3f} MW")
   print(f"MAPE: {mape(y_true, y_pred):.3f} %")
   print(f"rMAE: {rmae(y_true, y_pred):.3f}")

``rmae`` (relative MAE) normalises the error by the range between configurable
quantiles of the target distribution, making it useful when comparing models across
substations or load profiles with very different scales.

For peak-detection tasks — identifying congestion events — OpenSTEF provides a
dedicated confusion matrix:

.. code-block:: python

   from openstef_beam.metrics.metrics_deterministic import confusion_matrix, precision_recall

   cm = confusion_matrix(
       y_true=y_true,
       y_pred=y_pred,
       limit_pos=50.0,   # upper congestion threshold (MW)
       limit_neg=-50.0,  # lower congestion threshold (MW)
   )
   pr = precision_recall(cm)
   print(f"Precision: {pr.precision:.2f}  Recall: {pr.recall:.2f}")

Visualising Performance Over Time
-----------------------------------

A single aggregate metric can hide a lot. A model that performs well on average may
degrade badly during winter peaks or after a data gap. OpenSTEF's built-in
visualisation tools let you inspect performance as a sliding window over the evaluation
period.

**Time series view** — overlay actual measurements against forecast quantile bands:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import TimeSeriesVisualization

   analysis_config = AnalysisConfig(
       visualization_providers=[
           TimeSeriesVisualization(name="forecast_vs_actual"),
       ]
   )

**Windowed metric view** — track how MAE evolves week by week:

.. code-block:: python

   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window
   from datetime import timedelta

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="MAE",
               window=Window(size=timedelta(days=7), step=timedelta(days=1)),
           ),
       ]
   )

The windowed view is particularly useful for deciding **when to retrain**: if MAE
climbs steadily after each training event and then drops sharply after a retrain, you
can tune ``train_interval`` accordingly.

.. note::

   [DIAGRAM: Windowed MAE chart showing periodic drops at each retrain event,
   illustrating the relationship between retraining frequency and forecast accuracy]

Comparing Multiple Models
--------------------------

The most common use of backtesting is head-to-head model comparison. Because
``BacktestPipeline.run()`` returns a standard ``VersionedTimeSeriesDataset``, you can
run the same pipeline with different forecasters and collect results in a plain
dictionary:

.. code-block:: python

   from openstef.forecasting import XGBoostForecaster, LightGBMForecaster
   from openstef_beam.metrics.metrics_deterministic import mae
   import numpy as np

   models = {
       "xgboost": XGBoostForecaster(config=forecaster_config),
       "lightgbm": LightGBMForecaster(config=forecaster_config),
   }

   results = {}
   for name, forecaster in models.items():
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       preds = pipeline.run(
           ground_truth=ground_truth,
           predictors=predictors,
           start=datetime(2023, 1, 1),
           end=datetime(2023, 12, 31),
           show_progress=False,
       )
       y_true = ground_truth.to_numpy()
       y_pred = preds.to_numpy()
       results[name] = {
           "mae": mae(y_true, y_pred),
           "mape": mape(y_true, y_pred),
       }

   for name, scores in results.items():
       print(f"{name:10s}  MAE={scores['mae']:.3f}  MAPE={scores['mape']:.3f}")

Because every run uses the same ``ground_truth``, ``predictors``, ``start``, and
``end``, the comparison is apples-to-apples: differences in scores reflect only model
behaviour, not data splits.

.. note::

   Keep ``train_interval`` and ``predict_interval`` identical across all runs in a
   comparison. Changing these parameters alters how much training data each model sees
   and can produce misleading results.

Practical Tips
---------------

- **Start with a short window.** Run your first backtest over one or two months before
  extending to a full year. This catches configuration errors quickly and saves time.
- **Check completeness first.** Gaps in ``ground_truth`` or ``predictors`` propagate
  into the backtest. Use
  ``openstef_beam.metrics.metrics_deterministic.completeness()`` to audit your data
  before running.
- **Match your evaluation period to your use case.** If you care most about winter
  peaks, make sure your evaluation window covers at least one full winter.
- **Use ``show_progress=True`` during development.** The progress bar shows how many
  train/predict events remain and helps you spot unexpectedly long runs early.

Next Steps
-----------

- :doc:`advanced_customization` — build a custom forecaster that implements
  ``BacktestForecasterMixin`` so it integrates seamlessly with ``BacktestPipeline``.
- :doc:`first_forecast` — if any of the data-loading steps above were unclear, the
  first-forecast tutorial walks through them in detail.
- :doc:`quickstart` — a minimal end-to-end example if you want a quick reference.