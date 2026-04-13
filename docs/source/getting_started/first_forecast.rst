Your First Forecast
===================

This tutorial walks you through building a complete short-term energy forecast with
OpenSTEF from scratch. You will prepare time series data, configure a preprocessing
pipeline with feature engineering, train a model, generate predictions, and evaluate
the results — with an explanation of *why* each step matters, not just *how* to do it.

If you want the absolute shortest path to a working forecast first, see
:doc:`quickstart`. Come back here when you are ready to understand what is actually
happening under the hood.

.. note:: [DIAGRAM: Step-by-step flowchart showing the five stages of the OpenSTEF
   forecasting workflow: (1) Data Preparation — load or create a
   ``VersionedTimeSeriesDataset``; decision point: does data have correct frequency
   and target column? (2) Feature Engineering — attach a ``FeaturePipeline`` with
   holiday features, lag transforms, and scaling; decision point: are lag windows
   appropriate for the horizon? (3) Model Training — call ``ForecastingModel.fit()``
   or ``CustomForecastingWorkflow.train()``; decision point: is validation loss
   acceptable? (4) Prediction — call ``predict()`` to obtain a ``ForecastDataset``
   with point forecasts and quantile intervals; (5) Evaluation — compute MAE/RMSE
   against held-out actuals and inspect residuals.]


Overview
--------

OpenSTEF is a **library**. It does not run a server or manage a scheduler — it gives
you composable Python objects that you wire together in whatever application or
notebook suits your use case. The core objects you will use in this tutorial are:

- ``VersionedTimeSeriesDataset`` — the standard data container, aware of when each
  observation became available (important for realistic backtesting).
- ``ForecastingModel`` — a full pipeline of preprocessing → forecaster →
  postprocessing, trained and called as a single unit.
- ``CustomForecastingWorkflow`` — an optional orchestration layer that adds model
  persistence and lifecycle callbacks on top of a ``ForecastingModel``.

Each of these is described in more detail in the sections below.


Step 1 — Prepare Your Data
--------------------------

OpenSTEF expects time series data with a ``DatetimeIndex`` and at least one column
representing the quantity you want to forecast (conventionally called ``load``).
Additional columns become features available to the model.

For this tutorial, use the built-in synthetic data generator so you can run the
example without any external files:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset

   # Generate ~9 months of hourly data with weather-correlated load
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       wind_influence=-10.0,
       temp_influence=5.0,
       radiation_influence=-7.0,
       stochastic_influence=2.0,
   )

   print(dataset.data.head())
   print(f"Columns: {dataset.feature_names}")
   print(f"Rows:    {len(dataset.data)}")

``create_synthetic_forecasting_dataset`` returns a ``TimeSeriesDataset`` whose
``.data`` attribute is a ``pandas.DataFrame`` indexed by timestamp. The function
accepts ``include_available_at=True`` if you want to simulate data arriving with
realistic delays — useful when you move on to backtesting.

**Using your own data.** Wrap a real ``DataFrame`` in a
``VersionedTimeSeriesDataset`` instead:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # df must have a DatetimeIndex and a 'load' column
   df = pd.read_csv("my_measurements.csv", index_col="timestamp", parse_dates=True)

   dataset = VersionedTimeSeriesDataset.from_dataframe(
       df,
       sample_interval=timedelta(hours=1),
   )

.. note::

   OpenSTEF validates that the index has a consistent frequency. If your data has
   gaps, fill them before wrapping (e.g., with ``df.asfreq("1h")``). Rows with
   ``NaN`` in the target column are handled by the imputation step in the
   preprocessing pipeline.


Step 2 — Configure Feature Engineering
---------------------------------------

Raw load measurements alone are rarely enough for a good forecast. OpenSTEF's
``FeaturePipeline`` lets you declaratively compose the transformations applied to
your data before it reaches the model. Common additions include:

- **Holiday features** — binary indicators for public holidays, which capture the
  demand dip that occurs on bank holidays.
- **Lag transforms** — past values of the target at fixed offsets (e.g., load 24 h
  ago, load 168 h ago). These are the single most powerful predictors for load
  forecasting.
- **Datetime features** — hour of day, day of week, month, encoded as cyclical or
  one-hot variables.
- **Scaling** — standardising features so that gradient-boosted models converge
  faster and are less sensitive to outlier measurements.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.preprocessing.feature_pipeline import FeaturePipeline
   from openstef_models.models.preprocessing.transforms import (
       HolidayFeatureAdder,
       LagTransformer,
       StandardScaler,
   )

   preprocessing = FeaturePipeline(
       transforms=[
           HolidayFeatureAdder(country_code="NL"),
           LagTransformer(lags=[timedelta(hours=24), timedelta(hours=168)]),
           StandardScaler(exclude_columns=["load"]),
       ]
   )

.. note::

   The ``cutoff_history`` parameter on ``ForecastingModel`` (set in Step 3) must be
   at least as large as your longest lag. A 168-hour lag means the first 168 rows of
   training data will have ``NaN`` lag values. Setting ``cutoff_history=timedelta(hours=168)``
   tells the model to skip those rows during training rather than imputing them.


Step 3 — Build and Train the Model
------------------------------------

``ForecastingModel`` wraps a preprocessing pipeline, a forecaster, and an optional
postprocessing pipeline into a single object with a scikit-learn-style ``fit`` /
``predict`` interface.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.models.postprocessing.transforms import QuantileSorter

   horizons = [LeadTime.from_string("PT24H"), LeadTime.from_string("PT48H")]
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   forecaster = XGBoostForecaster(
       quantiles=quantiles,
       horizons=horizons,
   )

   model = ForecastingModel(
       preprocessing=preprocessing,   # defined in Step 2
       forecaster=forecaster,
       postprocessing=[QuantileSorter()],
       cutoff_history=timedelta(hours=168),  # skip lag warm-up rows
   )

   # Train on the full dataset
   model.fit(dataset)
   print("Training complete.")

A few things worth understanding here:

- **Horizons** are ``LeadTime`` objects that describe how far ahead you want to
  forecast. ``PT24H`` means 24 hours ahead. You can supply multiple horizons and the
  model trains a separate predictor for each.
- **Quantiles** let you produce probabilistic forecasts. ``Q(0.5)`` is the median
  (point forecast); ``Q(0.1)`` and ``Q(0.9)`` give you an 80 % prediction interval.
- **``QuantileSorter``** is a postprocessing step that guarantees quantile crossing
  does not occur in the output — a common artefact of independent quantile
  regression.

.. note::

   ``XGBoostForecaster`` is a good default for most energy forecasting problems. For
   a quick sanity check or a baseline comparison, swap it for
   ``ConstantMedianForecaster`` — it predicts the historical median and trains
   instantly. See :doc:`backtesting` for guidance on comparing models systematically.


Step 4 — Generate Forecasts
-----------------------------

Once the model is trained, call ``predict`` with a dataset that covers the future
period you want to forecast. In a real deployment this would be a dataset of weather
forecasts and calendar features for the coming days; here we use the tail of the
synthetic dataset to simulate a held-out test period.

.. code-block:: python

   from datetime import datetime, timezone, timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Simulate a forecast run: use the last 48 hours as the "future" window
   cutoff = dataset.data.index[-1] - timedelta(hours=48)
   future_data = dataset.data[dataset.data.index > cutoff]

   future_dataset = VersionedTimeSeriesDataset.from_dataframe(
       future_data,
       sample_interval=timedelta(hours=1),
   )

   forecasts = model.predict(future_dataset)
   print(forecasts.data.head())

The ``predict`` call returns a ``ForecastDataset``. Its ``.data`` attribute is a
``DataFrame`` with one column per quantile (e.g., ``q0.1``, ``q0.5``, ``q0.9``) and
a ``horizon`` column indicating which lead time each row belongs to.

.. note::

   The model only needs the feature columns in ``future_dataset`` — it does not need
   actual ``load`` values for the prediction period. In practice you would feed in
   weather forecast data for the coming hours alongside the calendar features that
   the preprocessing pipeline adds automatically.


Step 5 — Evaluate the Results
-------------------------------

With forecasts in hand, compare them against the actuals that were held out. A
standard evaluation uses Mean Absolute Error (MAE) and Root Mean Squared Error
(RMSE):

.. code-block:: python

   import numpy as np

   actuals = future_data["load"].values
   point_forecast = forecasts.data["q0.5"].values

   mae = np.mean(np.abs(actuals - point_forecast))
   rmse = np.sqrt(np.mean((actuals - point_forecast) ** 2))

   print(f"MAE:  {mae:.3f}")
   print(f"RMSE: {rmse:.3f}")

For probabilistic forecasts, also check whether the prediction intervals are
well-calibrated — roughly 80 % of actuals should fall between ``q0.1`` and ``q0.9``:

.. code-block:: python

   lower = forecasts.data["q0.1"].values
   upper = forecasts.data["q0.9"].values
   coverage = np.mean((actuals >= lower) & (actuals <= upper))
   print(f"80% interval coverage: {coverage:.1%}")

A coverage well below 80 % means your intervals are overconfident; well above 80 %
means they are too wide. Both are worth investigating before deploying.

.. note::

   For a more rigorous evaluation across multiple historical periods — including
   proper train/test splits that respect temporal ordering — see :doc:`backtesting`.


Persisting the Model
---------------------

In production you will want to save a trained model and reload it for later
prediction runs without retraining. ``CustomForecastingWorkflow`` adds persistence
on top of ``ForecastingModel`` using a storage backend:

.. code-block:: python

   from pathlib import Path
   from openstef_models.models.forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.integrations.local import LocalModelStorage

   storage = LocalModelStorage(path=Path("./model_store"))

   workflow = CustomForecastingWorkflow(model=model, storage=storage)

   # Train and automatically save the model
   workflow.train(dataset, model_id="my_first_forecast_v1")

   # Later: load and predict without retraining
   workflow_loaded = CustomForecastingWorkflow.load(
       model_id="my_first_forecast_v1",
       storage=storage,
   )
   forecasts = workflow_loaded.predict(future_dataset)

``LocalModelStorage`` writes the serialised model to disk. For team environments,
swap it for ``MLFlowStorage`` to track experiments and model versions in MLflow —
see :doc:`advanced_customization` for details.


Putting It All Together
------------------------

Here is the complete script combining every step above:

.. code-block:: python

   import numpy as np
   from datetime import timedelta
   from pathlib import Path

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, Q

   from openstef_models.models.preprocessing.feature_pipeline import FeaturePipeline
   from openstef_models.models.preprocessing.transforms import (
       HolidayFeatureAdder,
       LagTransformer,
       StandardScaler,
   )
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_models.models.postprocessing.transforms import QuantileSorter
   from openstef_models.models.forecasting_model import ForecastingModel

   # --- 1. Data ---
   dataset = create_synthetic_forecasting_dataset(
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1),
       wind_influence=-10.0,
       temp_influence=5.0,
   )

   # --- 2. Feature engineering ---
   preprocessing = FeaturePipeline(
       transforms=[
           HolidayFeatureAdder(country_code="NL"),
           LagTransformer(lags=[timedelta(hours=24), timedelta(hours=168)]),
           StandardScaler(exclude_columns=["load"]),
       ]
   )

   # --- 3. Model ---
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=XGBoostForecaster(
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           horizons=[LeadTime.from_string("PT24H")],
       ),
       postprocessing=[QuantileSorter()],
       cutoff_history=timedelta(hours=168),
   )
   model.fit(dataset)

   # --- 4. Predict ---
   cutoff = dataset.data.index[-1] - timedelta(hours=48)
   future_dataset = VersionedTimeSeriesDataset.from_dataframe(
       dataset.data[dataset.data.index > cutoff],
       sample_interval=timedelta(hours=1),
   )
   forecasts = model.predict(future_dataset)

   # --- 5. Evaluate ---
   actuals = dataset.data.loc[dataset.data.index > cutoff, "load"].values
   point_forecast = forecasts.data["q0.5"].values
   mae = np.mean(np.abs(actuals - point_forecast))
   print(f"MAE: {mae:.3f}")


Next Steps
----------

You now have a working forecast pipeline. From here:

- :doc:`backtesting` — learn how to evaluate your model across many historical
  periods and compare it against alternative configurations.
- :doc:`advanced_customization` — write custom forecasters, transforms, and
  callbacks to adapt OpenSTEF to your specific problem.
- :doc:`installation` — if you are setting up a new environment, this page covers
  optional dependencies (MLflow, beam runners) and version requirements.