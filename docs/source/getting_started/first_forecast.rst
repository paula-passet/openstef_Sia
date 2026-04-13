Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with
OpenSTEF from scratch. You will prepare time series data, configure a feature
engineering pipeline, train a model, generate predictions, and evaluate the results.
Each step explains not just *how* but *why*, so you understand the decisions behind
the code.

If you want the absolute shortest path to a working forecast, see :doc:`quickstart`
first. This page goes deeper — it is the right place to read when you want to
understand what OpenSTEF is actually doing.

.. note:: [DIAGRAM: Step-by-step flowchart showing the five stages of an OpenSTEF
   forecast: (1) Data Preparation → (2) Feature Engineering → (3) Model Training →
   (4) Prediction → (5) Evaluation. Decision points include: "Enough history for
   lag features?" between stages 1 and 2, and "Model performance acceptable?" between
   stages 3 and 4 (loop back to reconfigure if not).]

----

Overview
--------

OpenSTEF is a Python *library*. There is no daemon to start and no configuration
file to deploy — you write ordinary Python code that calls OpenSTEF's classes and
functions. The typical workflow looks like this:

1. Wrap your historical measurements in a ``VersionedTimeSeriesDataset``.
2. Build a ``ForecastingModel`` that combines a preprocessing pipeline, a forecaster,
   and optional postprocessing.
3. Call ``workflow.fit(dataset)`` to train.
4. Call ``workflow.predict(dataset)`` to generate forecasts.
5. Inspect the resulting ``ForecastDataset`` to evaluate quality.

The sections below follow this order exactly.

----

Step 1 — Preparing Your Data
-----------------------------

OpenSTEF expects time series data as a ``pandas.DataFrame`` with a
``DatetimeIndex``. The index must be timezone-aware and uniformly spaced. The
target column (the quantity you want to forecast) defaults to ``"load"``; every
other column is treated as an exogenous feature.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   rng = np.random.default_rng(42)
   n = 24 * 90  # 90 days of hourly measurements

   index = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")

   raw_data = pd.DataFrame(
       {
           "load": 50 + 20 * np.sin(2 * np.pi * np.arange(n) / 24) + rng.normal(0, 2, n),
           "temperature": 10 + 5 * np.sin(2 * np.pi * np.arange(n) / (24 * 365)) + rng.normal(0, 1, n),
           "wind_speed": np.abs(rng.normal(5, 2, n)),
       },
       index=index,
   )

Once you have a DataFrame, wrap it in a ``VersionedTimeSeriesDataset``. This
container carries the sampling interval alongside the data and supports combining
multiple data sources with different availability timestamps — important in
production where weather forecasts and metering data arrive at different times.

.. code-block:: python

   from openstef_models.datasets.versioned_time_series_dataset import (
       VersionedTimeSeriesDataset,
   )

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw_data,
       sample_interval=timedelta(hours=1),
   )

   print(dataset.feature_names)   # ['load', 'temperature', 'wind_speed']

.. note::

   OpenSTEF needs enough history to compute lag features. A lag of 14 days
   requires at least 14 days of data before the first usable training row. The
   ``cutoff_history`` parameter on ``ForecastingModel`` tells the library how much
   of the beginning of your dataset to skip during training. See
   :ref:`step3-training` below.

----

Step 2 — Configuring the Feature Pipeline
------------------------------------------

Raw measurements rarely go straight into a model. OpenSTEF's preprocessing
pipeline transforms your data into model-ready features through a sequence of
composable ``TimeSeriesTransform`` steps.

A typical pipeline for energy forecasting includes:

- **HolidayFeatureAdder** — adds binary flags for public holidays, which strongly
  influence energy demand patterns.
- **DatetimeFeaturesAdder** — adds hour-of-day, day-of-week, and similar cyclical
  features derived from the timestamp index.
- **LagsAdder** — creates lagged copies of the target and feature columns so the
  model can learn from recent history.
- **StandardScaler** (or similar) — normalises feature magnitudes so gradient-based
  learners converge reliably.

.. code-block:: python

   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.datetime_features_adder import DatetimeFeaturesAdder
   from openstef_models.transforms.lags_adder import LagsAdder
   from openstef_models.transforms.standard_scaler import StandardScaler
   from openstef_models.transforms.transform_pipeline import TransformPipeline

   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(),
           LagsAdder(lags=[timedelta(hours=24), timedelta(days=7)]),
           StandardScaler(),
       ]
   )

The pipeline is stateful: ``fit`` learns scaling parameters and lag offsets from
training data, then ``transform`` applies the same learned parameters to new data
at prediction time. You never call these methods directly — ``ForecastingModel``
manages the fit/transform lifecycle for you.

----

.. _step3-training:

Step 3 — Building and Training the Model
-----------------------------------------

``ForecastingModel`` is the central object in OpenSTEF. It owns the preprocessing
pipeline, the underlying forecaster, and optional postprocessing, and it enforces
the invariant that ``fit`` must be called before ``predict``.

The ``forecaster`` argument accepts any class that implements
``BaseForecastingModel``. This tutorial uses ``ConstantMedianForecaster`` — a
simple but instructive baseline that predicts the historical median load for each
horizon. For production work you would substitute an ``XGBoostForecaster`` or
``LGBMForecaster``; the rest of the code stays identical.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
   from openstef_models.utils.lead_time import LeadTime
   from openstef_models.utils.quantile import Q

   horizons = [LeadTime.from_string("PT24H")]   # forecast 24 hours ahead
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]        # 10th, median, 90th percentile

   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(
           horizons=horizons,
           quantiles=quantiles,
       ),
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=7),   # skip first 7 days; lag features are incomplete there
   )

The ``cutoff_history`` parameter deserves attention. A ``LagsAdder`` that looks
back 7 days produces ``NaN`` values for the first 7 days of any dataset. Setting
``cutoff_history=timedelta(days=7)`` tells ``ForecastingModel`` to exclude those
rows from training automatically.

Training is orchestrated through a ``CustomForecastingWorkflow``, which wraps the
model and handles concerns like model versioning and optional callbacks:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   workflow = CustomForecastingWorkflow(model=model, model_id="my_first_forecast")
   fit_result = workflow.fit(dataset)

   print(fit_result)   # ModelFitResult with metrics, feature importances, etc.

``workflow.fit`` splits the dataset into training, validation, and test sets
internally (using the ``DataSplitter`` configured on the model), fits the
preprocessing pipeline, trains the forecaster, and returns a ``ModelFitResult``
containing training metrics and, where supported, feature importances.

----

Step 4 — Generating Forecasts
------------------------------

Once the workflow has been fitted, call ``predict`` with a dataset that covers the
period you want to forecast. In practice this is usually a recent window of
observations plus any available weather forecasts:

.. code-block:: python

   # Use the last 48 hours as the prediction context
   forecast_index = raw_data.index[-48:]
   prediction_data = raw_data.loc[forecast_index]

   prediction_dataset = VersionedTimeSeriesDataset.from_dataframe(
       prediction_data,
       sample_interval=timedelta(hours=1),
   )

   forecasts = workflow.predict(prediction_dataset)

``workflow.predict`` returns a ``ForecastDataset``. Its ``.data`` attribute is a
``pandas.DataFrame`` indexed by timestamp, with one column per requested quantile:

.. code-block:: python

   print(forecasts.data.head())
   # timestamp                  q0.10   q0.50   q0.90
   # 2024-03-30 00:00:00+00:00  42.1    51.3    60.7
   # 2024-03-30 01:00:00+00:00  41.8    50.9    60.2
   # ...

The ``q0.50`` column is the point forecast (median). The ``q0.10`` and ``q0.90``
columns form a prediction interval — a direct measure of forecast uncertainty that
is useful for grid operators making reserve decisions.

----

Step 5 — Evaluating the Forecast
----------------------------------

Evaluation compares the ``q0.50`` predictions against actual measurements. The
most common metrics in energy forecasting are Mean Absolute Error (MAE) and the
coefficient of determination (R²).

.. code-block:: python

   import numpy as np

   # Align actuals with predictions on the overlapping index
   actuals = raw_data["load"]
   predicted = forecasts.data["q0.50"]
   common_index = actuals.index.intersection(predicted.index)

   y_true = actuals.loc[common_index].to_numpy()
   y_pred = predicted.loc[common_index].to_numpy()

   mae = np.mean(np.abs(y_true - y_pred))
   ss_res = np.sum((y_true - y_pred) ** 2)
   ss_tot = np.sum((y_true - y_true.mean()) ** 2)
   r2 = 1 - ss_res / ss_tot

   print(f"MAE : {mae:.2f} MW")
   print(f"R²  : {r2:.4f}")

For a baseline model like ``ConstantMedianForecaster`` you should expect a modest
R² — its purpose is to give you a lower bound on performance. Switching to
``XGBoostForecaster`` with the same pipeline typically raises R² substantially.

.. note::

   For systematic comparison of multiple models across a historical period, see
   :doc:`backtesting`. That tutorial shows how to use OpenSTEF's built-in
   backtesting utilities to get statistically reliable performance estimates rather
   than evaluating on a single held-out window.

----

Putting It All Together
------------------------

Here is the complete script without interruptions, ready to copy and run:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import timedelta

   from openstef_models.datasets.versioned_time_series_dataset import VersionedTimeSeriesDataset
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.time_domain.datetime_features_adder import DatetimeFeaturesAdder
   from openstef_models.transforms.lags_adder import LagsAdder
   from openstef_models.transforms.standard_scaler import StandardScaler
   from openstef_models.transforms.transform_pipeline import TransformPipeline
   from openstef_models.models.forecasting.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
   from openstef_models.utils.lead_time import LeadTime
   from openstef_models.utils.quantile import Q
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow

   # --- 1. Data ---
   rng = np.random.default_rng(42)
   n = 24 * 90
   index = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
   raw_data = pd.DataFrame(
       {
           "load": 50 + 20 * np.sin(2 * np.pi * np.arange(n) / 24) + rng.normal(0, 2, n),
           "temperature": 10 + 5 * np.sin(2 * np.pi * np.arange(n) / (24 * 365)) + rng.normal(0, 1, n),
       },
       index=index,
   )
   dataset = VersionedTimeSeriesDataset.from_dataframe(raw_data, sample_interval=timedelta(hours=1))

   # --- 2. Preprocessing pipeline ---
   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code="NL"),
           DatetimeFeaturesAdder(),
           LagsAdder(lags=[timedelta(hours=24), timedelta(days=7)]),
           StandardScaler(),
       ]
   )

   # --- 3. Model and training ---
   horizons = [LeadTime.from_string("PT24H")]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(horizons=horizons, quantiles=quantiles),
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=7),
   )
   workflow = CustomForecastingWorkflow(model=model, model_id="my_first_forecast")
   workflow.fit(dataset)

   # --- 4. Prediction ---
   prediction_dataset = VersionedTimeSeriesDataset.from_dataframe(
       raw_data.iloc[-48:], sample_interval=timedelta(hours=1)
   )
   forecasts = workflow.predict(prediction_dataset)

   # --- 5. Evaluation ---
   actuals = raw_data["load"]
   predicted = forecasts.data["q0.50"]
   common_index = actuals.index.intersection(predicted.index)
   y_true = actuals.loc[common_index].to_numpy()
   y_pred = predicted.loc[common_index].to_numpy()
   mae = np.mean(np.abs(y_true - y_pred))
   print(f"MAE: {mae:.2f} MW")

----

Next Steps
----------

This tutorial used a simple baseline forecaster to keep the focus on the
workflow. In practice you will want to:

- **Swap the forecaster** — replace ``ConstantMedianForecaster`` with
  ``XGBoostForecaster`` or ``LGBMForecaster`` for production-grade accuracy.
  See :doc:`advanced_customization` for guidance on tuning hyperparameters and
  building custom preprocessing steps.

- **Persist the trained model** — ``LocalModelStorage`` saves and loads
  ``ForecastingModel`` instances to disk. The :doc:`advanced_customization` page
  covers model storage patterns in detail.

- **Benchmark rigorously** — a single evaluation window can be misleading.
  :doc:`backtesting` shows how to evaluate across many historical windows to
  get reliable performance estimates before deploying a model.