Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with
OpenSTEF from scratch. By the end you will have loaded time series data, configured a
preprocessing pipeline with feature engineering, trained a forecasting model, generated
predictions, and evaluated the result — understanding *why* each step exists, not just
*how* to run it.

If you just want the shortest possible working script, see :doc:`quickstart` first and
come back here when you want to understand the details. For comparing multiple model
configurations, see :doc:`backtesting`.

.. mermaid:: diagrams/getting_started/first_forecast_diagram_1.mmd

Overview
--------

OpenSTEF structures every forecast around a pipeline of four concerns:

- **Data** — a ``VersionedTimeSeriesDataset`` that tracks when each observation
  became available, enabling realistic point-in-time splits.
- **Preprocessing** — a ``FeaturePipeline`` that enriches raw measurements with
  calendar features, lag transforms, and scaling before any model sees the data.
- **Model** — a ``ForecastingModel`` that wraps a forecaster (e.g. XGBoost) together
  with its preprocessing and postprocessing into a single, serialisable object.
- **Evaluation** — metric utilities that compare predictions against held-out actuals.

Each concern is a separate, composable piece of the library. You can swap any one of
them without touching the others.

Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects time series data as a ``VersionedTimeSeriesDataset``. The "versioned"
part matters: in production, measurements are often revised after the fact, and the
dataset tracks the ``available_at`` timestamp for each row so that training never
accidentally uses data that would not have been available at prediction time.

For this tutorial, the library ships a helper that generates realistic synthetic load
data so you can follow along without a live data connection:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.data_classes.dataset import VersionedTimeSeriesDataset

   # Nine months of hourly data — enough history for meaningful lag features
   raw_dataset = create_synthetic_forecasting_dataset(
       start=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       wind_influence=-0.2,
       temp_influence=0.3,
   )

   # Wrap in a VersionedTimeSeriesDataset for point-in-time correctness
   dataset = VersionedTimeSeriesDataset(data_parts=[raw_dataset])

   print(f"Dataset spans {raw_dataset.data.index.min()} → {raw_dataset.data.index.max()}")
   print(f"Features available: {raw_dataset.feature_names}")

The synthetic dataset includes a ``load`` target column and weather covariates
(``wind``, ``temperature``, ``radiation``). When you bring your own data, create a
``pandas.DataFrame`` with a ``DatetimeIndex`` and pass it through
``VersionedTimeSeriesDataset.from_dataframe()``:

.. code-block:: python

   import pandas as pd
   from openstef_core.data_classes.dataset import VersionedTimeSeriesDataset

   # Your own data: DatetimeIndex, one column per feature, one column for the target
   df = pd.read_csv("my_load_data.csv", index_col="timestamp", parse_dates=True)

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       df,
       sample_interval=timedelta(hours=1),
   )

.. note::

   The index must be a timezone-aware ``DatetimeIndex`` with a uniform frequency.
   Missing timestamps cause downstream feature engineering (especially lag transforms)
   to produce incorrect alignments. Resample and fill gaps before wrapping your data.

Step 2 — Configure Feature Engineering
---------------------------------------

Raw load measurements alone are rarely sufficient for a good forecast. Energy
consumption follows strong calendar patterns (time of day, day of week, public
holidays) and responds to weather. OpenSTEF's ``FeaturePipeline`` lets you declare
these enrichments as a composable list of transforms:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.transforms.feature_pipeline import FeaturePipeline
   from openstef_core.transforms.holiday_features import HolidayFeatures
   from openstef_core.transforms.lag_transform import LagTransform
   from openstef_core.transforms.standard_scaler import StandardScaler

   # Forecast horizon: 24 hours ahead, at hourly resolution
   HORIZON = timedelta(hours=24)
   SAMPLE_INTERVAL = timedelta(hours=1)

   preprocessing = FeaturePipeline(
       transforms=[
           # Calendar and public-holiday indicators for the Netherlands
           HolidayFeatures(country_code="NL"),
           # Lag features: yesterday, last week, two weeks ago
           # These give the model "memory" of recent and seasonal patterns
           LagTransform(
               lags=[
                   timedelta(hours=24),
                   timedelta(hours=48),
                   timedelta(days=7),
                   timedelta(days=14),
               ]
           ),
           # Normalise all features to zero mean, unit variance
           StandardScaler(),
       ],
       horizon=HORIZON,
       sample_interval=SAMPLE_INTERVAL,
   )

**Why lag transforms matter:** A lag-24h feature tells the model what load looked like
at the same hour yesterday — one of the strongest predictors of today's load. The
``cutoff_history`` parameter on ``ForecastingModel`` (set in the next step) must be
configured to exclude the first ``max(lags)`` rows from training, because those rows
have ``NaN`` lag values and would corrupt the fit.

Step 3 — Configure and Train the Model
----------------------------------------

``ForecastingModel`` is the central class in OpenSTEF. It binds a forecaster
(the underlying ML algorithm), a preprocessing pipeline, and optional postprocessing
into a single object that you can fit, predict with, and persist.

.. code-block:: python

   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasters.xgboost_forecaster import XGBoostForecaster

   forecaster = XGBoostForecaster(
       horizon=HORIZON,
       sample_interval=SAMPLE_INTERVAL,
       quantiles=[0.1, 0.5, 0.9],   # predict median + 80 % prediction interval
   )

   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=preprocessing,
       # Exclude the first 14 days from training — they have incomplete lag features
       cutoff_history=timedelta(days=14),
   )

Now split the dataset into a training window and a held-out evaluation window, then
call ``fit()``:

.. code-block:: python

   from datetime import timezone

   # Use the last 30 days as a held-out evaluation set
   split_time = datetime(2024-9-1, tzinfo=timezone.utc)

   train_data = dataset.select_version(
       available_before=split_time,
       horizon=HORIZON,
   )
   eval_data = dataset.select_version(
       available_before=split_time + timedelta(days=30),
       horizon=HORIZON,
   )

   # Fit the full pipeline: preprocessing is fitted on training data only,
   # then the forecaster is trained on the transformed features.
   model.fit(train_data)
   print("Training complete.")

.. note::

   ``fit()`` applies the entire preprocessing pipeline to ``train_data`` before
   passing it to the forecaster. The ``StandardScaler`` parameters (mean and variance)
   are computed from the training window only, preventing data leakage into evaluation.

Step 4 — Generate a Forecast
------------------------------

Once the model is fitted, call ``predict()`` with the evaluation dataset. OpenSTEF
returns a ``ForecastDataset`` containing the predicted quantiles and, if available,
the ground-truth actuals for comparison:

.. code-block:: python

   forecast_result = model.predict(eval_data)

   # forecast_result.forecast is a pd.DataFrame indexed by (timestamp, horizon)
   forecast_df = forecast_result.forecast
   print(forecast_df.head())

The output DataFrame contains one column per requested quantile (``q0.1``, ``q0.5``,
``q0.9``) plus a ``horizon`` column indicating how far ahead each row was predicted.
The median quantile (``q0.5``) is your point forecast; the outer quantiles form a
prediction interval.

.. code-block:: python

   # Inspect the prediction interval width as a proxy for model uncertainty
   forecast_df["interval_width"] = forecast_df["q0.9"] - forecast_df["q0.1"]
   print(forecast_df[["q0.5", "interval_width"]].describe())

Step 5 — Evaluate the Forecast
--------------------------------

A forecast is only useful if you can measure how good it is. OpenSTEF provides metric
utilities that operate directly on ``ForecastDataset`` objects:

.. code-block:: python

   from openstef_beam.evaluation.metric_providers import R2Provider, ObservedProbabilityProvider

   # R² — proportion of variance explained (higher is better, 1.0 is perfect)
   r2_provider = R2Provider()
   r2_score = r2_provider.compute(forecast_result)
   print(f"R²: {r2_score:.4f}")

   # Observed probability — fraction of actuals falling inside the prediction interval
   # A well-calibrated 80 % interval should score close to 0.80
   obs_prob_provider = ObservedProbabilityProvider(lower_quantile=0.1, upper_quantile=0.9)
   obs_prob = obs_prob_provider.compute(forecast_result)
   print(f"Observed probability (80 % interval): {obs_prob:.4f}")

For a quick sanity check you can also compute standard regression metrics directly
from the forecast DataFrame:

.. code-block:: python

   import numpy as np

   y_true = forecast_df["load"].values
   y_pred = forecast_df["q0.5"].values

   mae = np.mean(np.abs(y_true - y_pred))
   rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
   print(f"MAE:  {mae:.2f} MW")
   print(f"RMSE: {rmse:.2f} MW")

**Interpreting the results:**

- An R² above 0.90 is generally considered good for short-term load forecasting.
- If the observed probability for an 80 % interval is well below 0.80, the model is
  overconfident — consider adding more lag features or increasing regularisation.
- If MAE is unexpectedly high, check whether the training window is long enough to
  capture seasonal patterns (at least one full year is recommended for annual cycles).

Putting It All Together
------------------------

Here is the complete, self-contained script for reference:

.. code-block:: python

   import numpy as np
   from datetime import datetime, timedelta, timezone

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.data_classes.dataset import VersionedTimeSeriesDataset
   from openstef_core.transforms.feature_pipeline import FeaturePipeline
   from openstef_core.transforms.holiday_features import HolidayFeatures
   from openstef_core.transforms.lag_transform import LagTransform
   from openstef_core.transforms.standard_scaler import StandardScaler
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasters.xgboost_forecaster import XGBoostForecaster
   from openstef_beam.evaluation.metric_providers import R2Provider

   HORIZON = timedelta(hours=24)
   SAMPLE_INTERVAL = timedelta(hours=1)

   # 1. Data
   raw_dataset = create_synthetic_forecasting_dataset(
       start=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
       length=timedelta(days=270),
       sample_interval=SAMPLE_INTERVAL,
   )
   dataset = VersionedTimeSeriesDataset(data_parts=[raw_dataset])

   # 2. Feature engineering
   preprocessing = FeaturePipeline(
       transforms=[
           HolidayFeatures(country_code="NL"),
           LagTransform(lags=[timedelta(hours=24), timedelta(days=7)]),
           StandardScaler(),
       ],
       horizon=HORIZON,
       sample_interval=SAMPLE_INTERVAL,
   )

   # 3. Model
   model = ForecastingModel(
       forecaster=XGBoostForecaster(
           horizon=HORIZON,
           sample_interval=SAMPLE_INTERVAL,
           quantiles=[0.1, 0.5, 0.9],
       ),
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=7),
   )

   split_time = datetime(2024, 9, 1, tzinfo=timezone.utc)
   train_data = dataset.select_version(available_before=split_time, horizon=HORIZON)
   eval_data = dataset.select_version(
       available_before=split_time + timedelta(days=30), horizon=HORIZON
   )

   model.fit(train_data)

   # 4. Forecast
   forecast_result = model.predict(eval_data)
   forecast_df = forecast_result.forecast

   # 5. Evaluate
   r2_score = R2Provider().compute(forecast_result)
   y_true = forecast_df["load"].values
   y_pred = forecast_df["q0.5"].values
   mae = np.mean(np.abs(y_true - y_pred))
   print(f"R²: {r2_score:.4f}  |  MAE: {mae:.2f} MW")

Common Pitfalls
---------------

**Insufficient training history**
   Lag features require history equal to the largest lag before the first usable
   training row. Set ``cutoff_history`` on ``ForecastingModel`` to match the largest
   lag in your ``LagTransform``, otherwise the model trains on rows with ``NaN``
   features.

**Timezone-naive index**
   OpenSTEF requires timezone-aware timestamps. Pass ``tz="UTC"`` (or your local
   timezone) when parsing your index, or use ``df.index = df.index.tz_localize("UTC")``.

**Scaler fitted on evaluation data**
   Always construct the train/eval split *before* calling ``model.fit()``. The
   ``FeaturePipeline`` fits its ``StandardScaler`` inside ``fit()`` using only the
   data you pass — if you accidentally pass the full dataset, evaluation metrics will
   be optimistic.

**Horizon mismatch**
   The ``horizon`` argument must be consistent across ``FeaturePipeline``,
   ``XGBoostForecaster``, and the ``select_version()`` calls. A mismatch raises a
   validation error at fit time.

Next Steps
----------

- :doc:`backtesting` — learn how to rigorously compare model configurations over
  multiple historical windows rather than a single train/eval split.
- :doc:`advanced_customization` — write your own transforms, custom forecasters, and
  postprocessing steps to extend the library for your specific use case.
- :doc:`installation` — if you ran into import errors above, check the optional
  dependency groups for ``openstef-models`` and ``openstef-beam``.