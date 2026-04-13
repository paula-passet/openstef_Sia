Backtesting Models with Historical Data
=======================================

Backtesting is the practice of evaluating a forecasting model against historical data
as if it were operating in real time — generating predictions only from information that
would have been available at each point in the past. OpenSTEF provides a dedicated
``BacktestPipeline`` that simulates this operational environment faithfully, preventing
data leakage and respecting the constraints of a live forecasting system.

This page walks through the full backtesting workflow: configuring the pipeline,
running it against historical data, computing evaluation metrics, and comparing
multiple models side by side.

.. note::

   This tutorial assumes you already have a working forecaster. If you are new to
   OpenSTEF, start with :doc:`first_forecast` before continuing here.

How OpenSTEF Backtesting Works
------------------------------

A naive backtest trains a model once on all available history and then scores it
against a held-out window. OpenSTEF's ``BacktestPipeline`` goes further: it replays
the operational timeline, periodically retraining the model and generating fresh
predictions at regular intervals, exactly as a deployed system would behave.

Three timing parameters control this simulation:

- **prediction_sample_interval** — the resolution of the output forecast (e.g. 15 minutes).
- **predict_interval** — how often a new prediction run is triggered (e.g. every 6 hours).
- **train_interval** — how often the model is retrained on the most recent history (e.g. weekly).

.. note:: [DIAGRAM: Timeline showing alternating train events and predict events over a multi-week backtest window, with arrows indicating the restricted data horizon available at each step.]

This design means the backtest result reflects the accuracy you would actually observe
in production, not an optimistic offline estimate.

Configuring the Pipeline
------------------------

Start by importing the relevant classes and constructing a ``BacktestConfig``:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting.pipeline import BacktestPipeline
   from openstef_beam.backtesting.pipeline import BacktestConfig

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       predict_interval=timedelta(hours=6),
       train_interval=timedelta(days=7),
       align_time=time.fromisoformat("00:00+00"),
   )

``align_time`` anchors the prediction schedule to a fixed wall-clock reference so that
prediction windows align consistently across days, which matters when comparing models
trained on different datasets.

.. note::

   The ``prediction_sample_interval`` in ``BacktestConfig`` **must** match the
   ``predict_sample_interval`` declared in your forecaster's configuration. OpenSTEF
   raises a ``ValueError`` at construction time if these values differ, so mismatches
   are caught before any computation begins.

Implementing the Forecaster Interface
--------------------------------------

``BacktestPipeline`` accepts any object that implements ``BacktestForecasterMixin``.
This mixin defines the contract your model must satisfy:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting.backtest_forecaster.mixins import (
       BacktestForecasterConfig,
       BacktestForecasterMixin,
   )
   from openstef_beam.backtesting.restricted_horizon_timeseries import (
       RestrictedHorizonVersionedTimeSeries,
   )
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Quantile

   class MyForecasterConfig(BacktestForecasterConfig):
       requires_training: bool = True
       predict_sample_interval: timedelta = timedelta(minutes=15)
       predict_length: timedelta = timedelta(hours=48)
       predict_min_length: timedelta = timedelta(hours=1)
       predict_context_length: timedelta = timedelta(days=14)
       predict_context_min_coverage: float = 0.8
       training_context_length: timedelta = timedelta(days=90)
       training_context_min_coverage: float = 0.7

   class MyForecaster(BacktestForecasterMixin):
       def __init__(self):
           self.config = MyForecasterConfig()
           self._model = None

       @property
       def quantiles(self) -> list[Quantile]:
           return [0.1, 0.5, 0.9]

       def train(self, data: RestrictedHorizonVersionedTimeSeries) -> None:
           # Fit your model on data.ground_truth and data.predictors
           ...

       def predict(
           self, data: RestrictedHorizonVersionedTimeSeries
       ) -> TimeSeriesDataset | None:
           # Return predictions as a TimeSeriesDataset, or None if not ready
           ...

The ``RestrictedHorizonVersionedTimeSeries`` argument passed to both ``train`` and
``predict`` exposes only the data that would have been available at the simulated
timestamp — the pipeline enforces this restriction automatically.

For rapid prototyping and pipeline testing, OpenSTEF ships a ``DummyForecaster`` that
satisfies the interface without any real prediction logic:

.. code-block:: python

   from openstef_beam.backtesting.backtest_forecaster.dummy_forecaster import DummyForecaster

   forecaster = DummyForecaster()

Running the Backtest
--------------------

With a config and a forecaster in hand, construct the pipeline and call ``run()``:

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_beam.backtesting.pipeline import BacktestPipeline

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   predictions = pipeline.run(
       ground_truth=ground_truth_dataset,
       predictors=predictors_dataset,
       start=datetime(2024, 1, 1, tzinfo=timezone.utc),
       end=datetime(2024, 6, 30, tzinfo=timezone.utc),
       show_progress=True,
   )

``ground_truth`` and ``predictors`` are ``VersionedTimeSeriesDataset`` objects covering
the full historical window. Passing ``None`` for ``start`` or ``end`` tells the pipeline
to use the minimum or maximum timestamp present in the data.

The return value is a ``VersionedTimeSeriesDataset`` containing every prediction
generated during the simulation, tagged with the timestamp at which each forecast was
made and the availability horizon that was in effect at that time.

Evaluating Forecast Accuracy
-----------------------------

OpenSTEF's metrics module provides purpose-built functions for energy forecasting
evaluation, covering both deterministic and probabilistic outputs.

.. code-block:: python

   import numpy as np
   from openstef_beam.metrics.metrics_deterministic import mae, rmae

   # Align predictions with ground truth on a common index
   y_true = ground_truth_series.values
   y_pred = predictions.median_series.values  # or your point forecast column

   mean_abs_error = mae(y_true, y_pred)
   relative_mae = rmae(y_true, y_pred)

   print(f"MAE:  {mean_abs_error:.2f} MW")
   print(f"rMAE: {relative_mae:.4f}")

For probabilistic forecasts the metrics module includes reliability and sharpness
measures suited to quantile outputs. The ``EvaluationPipeline`` can aggregate these
across lead times and sliding windows automatically — see the API reference for
``openstef_beam.metrics`` for the full list of available metrics.

Comparing Multiple Models
--------------------------

The most common use of backtesting is comparing candidate models on the same historical
period. The pattern is straightforward: run the pipeline independently for each model,
collect the results, and compute metrics on a shared index.

.. code-block:: python

   from openstef_beam.metrics.metrics_deterministic import mae

   models = {
       "model_a": MyForecasterA(),
       "model_b": MyForecasterB(),
   }

   results = {}
   for name, forecaster in models.items():
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       predictions = pipeline.run(
           ground_truth=ground_truth_dataset,
           predictors=predictors_dataset,
           start=datetime(2024, 1, 1, tzinfo=timezone.utc),
           end=datetime(2024, 6, 30, tzinfo=timezone.utc),
           show_progress=True,
       )
       results[name] = predictions

   # Compute MAE for each model over the common period
   for name, preds in results.items():
       y_true = ground_truth_series.reindex(preds.index).values
       y_pred = preds.values
       print(f"{name}: MAE = {mae(y_true, y_pred):.3f}")

Because every run uses the same ``BacktestConfig`` and the same historical window, the
comparison is apples-to-apples: both models see identical training and prediction
schedules, and neither has access to future data.

.. note::

   Keep ``train_interval`` consistent across model runs when comparing. A model
   retrained more frequently will generally score better simply because it has fresher
   data, not because it is inherently more accurate.

Avoiding Common Pitfalls
-------------------------

**Data leakage** is the most dangerous mistake in backtesting. OpenSTEF's
``RestrictedHorizonVersionedTimeSeries`` prevents leakage automatically by exposing
only data up to the current simulation timestamp. If you pre-process features outside
the pipeline (for example, computing a rolling mean over the full dataset before
passing it in), you may inadvertently introduce future information. Always compute
derived features inside the ``train`` or ``predict`` methods where the restricted
horizon is enforced.

**Overfitting to the backtest window** is a subtler risk. If you tune model
hyperparameters by repeatedly running backtests on the same period and selecting the
best result, the chosen model is likely to underperform on genuinely unseen data.
Reserve a separate holdout period for final evaluation, and use the backtest window
only for development decisions.

**Mismatched sample intervals** will raise a ``ValueError`` at pipeline construction.
Check that ``BacktestConfig.prediction_sample_interval`` equals
``forecaster.config.predict_sample_interval`` before running long experiments.

Next Steps
----------

- :doc:`advanced_customization` — learn how to plug custom feature engineering and
  model architectures into the OpenSTEF pipeline.
- :doc:`first_forecast` — if you need a refresher on building and running a basic
  forecast before backtesting it.
- :doc:`quickstart` — a minimal end-to-end example if you want to see the full flow
  in one place.