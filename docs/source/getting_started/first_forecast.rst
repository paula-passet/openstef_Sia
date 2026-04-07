Your First Forecast
===================

This tutorial walks you through building your first energy forecast with OpenSTEF, step by step. You'll learn how to prepare time series data, configure a forecasting model with feature engineering, train it, generate predictions, and evaluate the results.

By the end, you'll understand the core workflow that underpins every OpenSTEF forecasting pipeline.

.. note::

   This tutorial explains each step in detail. If you just want a minimal working example, see :doc:`quickstart`. For installation instructions, see :doc:`installation`.


Overview of the Workflow
------------------------

Every forecast in OpenSTEF follows the same pattern:

1. **Prepare data** — Load your time series into a ``TimeSeriesDataset``
2. **Configure preprocessing** — Define feature engineering transforms (holidays, lags, scaling)
3. **Build the model** — Combine a forecaster with preprocessing into a ``ForecastingModel``
4. **Train** — Call ``fit()`` on historical data
5. **Predict** — Call ``predict()`` to generate forecasts
6. **Evaluate** — Compare predictions against actuals

.. note:: [DIAGRAM: Linear pipeline flow showing Data → Preprocessing → Forecaster → Postprocessing → Forecast]

Let's work through each step.


Step 1: Prepare Your Data
-------------------------

OpenSTEF uses ``TimeSeriesDataset`` as its core data structure. This wraps a pandas DataFrame with a ``DatetimeIndex`` and adds metadata like the target column name and sample interval.

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset

   # Create synthetic load data: 60 days of 15-minute intervals
   n_days = 60
   freq = timedelta(minutes=15)
   timestamps = pd.date_range(
       start="2024-01-01",
       periods=n_days * 24 * 4,
       freq=freq,
   )

   # Simulate a daily load pattern with some noise
   hours = timestamps.hour + timestamps.minute / 60.0
   daily_pattern = 50 + 30 * np.sin(2 * np.pi * (hours - 6) / 24)
   noise = np.random.default_rng(42).normal(0, 3, size=len(timestamps))

   df = pd.DataFrame(
       {"load": daily_pattern + noise},
       index=timestamps,
   )

   # Wrap in a TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=freq,
       target_column="load",
   )

The ``target_column`` parameter (default: ``"load"``) tells OpenSTEF which column contains the values you want to forecast. The ``sample_interval`` specifies the expected time resolution of your data.

.. note::

   Your DataFrame **must** have a ``DatetimeIndex``. The target column must be present in the data. Additional columns (e.g., temperature, wind speed) can be included as exogenous features.


Step 2: Configure Feature Engineering
--------------------------------------

Raw time series data rarely produces good forecasts on its own. OpenSTEF's ``FeaturePipeline`` lets you define preprocessing transforms that create informative features from your data. Common transforms include holiday indicators, lag features, and data scaling.

.. code-block:: python

   from openstef_models.preprocessing import FeaturePipeline
   from openstef_models.preprocessing.transforms import (
       HolidayTransform,
       LagTransform,
       StandardScalerTransform,
   )

   preprocessing = FeaturePipeline(
       transforms=[
           HolidayTransform(country_code="NL"),
           LagTransform(lags=[timedelta(days=1), timedelta(days=7), timedelta(days=14)]),
           StandardScalerTransform(),
       ]
   )

Here's what each transform does:

- **HolidayTransform** — Adds binary features indicating whether each timestamp falls on a public holiday. The ``country_code`` parameter determines which country's holiday calendar to use.
- **LagTransform** — Creates features from past values of the target. A ``timedelta(days=1)`` lag gives the model access to "what the load was 24 hours ago." Lag-7 and lag-14 capture weekly patterns.
- **StandardScalerTransform** — Normalizes feature values to zero mean and unit variance, which helps many ML algorithms converge faster.

.. warning::

   Lag features create ``NaN`` values at the start of your dataset. A 14-day lag means the first 14 days of data will have missing lag values. You **must** account for this with the ``cutoff_history`` parameter when building your model (see Step 3).


Step 3: Build the Forecasting Model
------------------------------------

The ``ForecastingModel`` ties together your preprocessing pipeline and a forecaster into a single object. This is the central abstraction in OpenSTEF — it orchestrates the full workflow of feature engineering, model training, and prediction.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )

   # Use a simple median forecaster to start
   forecaster = ConstantMedianForecaster()

   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=14),
   )

The ``cutoff_history`` parameter is crucial. It tells the model to discard the first 14 days of transformed data during training — exactly the period where lag features are incomplete. Set this to match the longest lag in your preprocessing pipeline.

.. note::

   We use ``ConstantMedianForecaster`` here for simplicity. For real forecasting tasks, you'll want to use more powerful models like XGBoost or LightGBM. See :doc:`advanced_customization` for details on swapping in different forecasters.


Step 4: Train the Model
------------------------

Training is a single ``fit()`` call. The model applies preprocessing to your data, removes the cutoff period, and trains the underlying forecaster on the resulting features.

.. code-block:: python

   # Split data: first 50 days for training, last 10 for testing
   split_point = datetime(2024, 2, 20)

   train_data = TimeSeriesDataset(
       data=df.loc[:split_point],
       sample_interval=freq,
       target_column="load",
   )

   test_data = TimeSeriesDataset(
       data=df.loc[split_point:],
       sample_interval=freq,
       target_column="load",
   )

   # Train the model
   train_predictions, val_predictions, test_predictions, fit_result = model.fit(
       data=train_data,
   )

The ``fit()`` method returns several objects:

- ``train_predictions`` — The model's predictions on the training set (useful for diagnosing overfitting)
- ``val_predictions`` — Predictions on a validation split, if applicable
- ``test_predictions`` — Predictions on a held-out test split, if applicable
- ``fit_result`` — A ``ModelFitResult`` containing training metrics and metadata


Step 5: Generate Forecasts
--------------------------

Once trained, call ``predict()`` with new data to generate forecasts:

.. code-block:: python

   forecast = model.predict(data=test_data)

   # The forecast is a ForecastDataset containing predictions
   print(forecast.data.head())

The ``predict()`` method applies the same preprocessing pipeline that was fitted during training, then passes the transformed features to the forecaster. The result is a ``ForecastDataset`` — a specialized dataset that holds forecast values and, if configured, quantile predictions for uncertainty estimation.

.. note::

   You must call ``fit()`` before ``predict()``. The preprocessing pipeline needs to learn its parameters (e.g., scaler mean and variance) from training data first.


Step 6: Evaluate the Results
-----------------------------

Compare your forecasts against the actual values to assess model quality:

.. code-block:: python

   from sklearn.metrics import mean_absolute_error, mean_squared_error

   actuals = test_data.data["load"]
   predictions = forecast.data["load"]

   # Align on common timestamps
   common_idx = actuals.index.intersection(predictions.index)
   actuals = actuals.loc[common_idx]
   predictions = predictions.loc[common_idx]

   mae = mean_absolute_error(actuals, predictions)
   rmse = mean_squared_error(actuals, predictions, squared=False)

   print(f"MAE:  {mae:.2f}")
   print(f"RMSE: {rmse:.2f}")

For energy forecasting, MAE (Mean Absolute Error) and RMSE (Root Mean Squared Error) are the most commonly used metrics. Lower values indicate better forecast accuracy.

For systematic model comparison across different configurations, see :doc:`backtesting`.


Persisting Your Model
----------------------

In production, you'll want to save trained models and load them later for prediction. OpenSTEF provides ``LocalModelStorage`` for file-based persistence:

.. code-block:: python

   from openstef_models.storage import LocalModelStorage
   from pathlib import Path

   storage = LocalModelStorage(base_path=Path("./models"))

   # Save the trained model
   storage.save(model=model, model_id="my_first_forecast")

   # Load it back later
   loaded_model = storage.load(model_id="my_first_forecast")
   forecast = loaded_model.predict(data=test_data)

This stores the complete model — including the fitted preprocessing pipeline and forecaster weights — so you can reload it without retraining.


Putting It All Together
-----------------------

Here's the complete workflow in one block:

.. code-block:: python

   import numpy as np
   import pandas as pd
   from datetime import datetime, timedelta
   from pathlib import Path

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
   )
   from openstef_models.preprocessing import FeaturePipeline
   from openstef_models.preprocessing.transforms import (
       HolidayTransform,
       LagTransform,
       StandardScalerTransform,
   )
   from openstef_models.storage import LocalModelStorage

   # 1. Prepare data
   timestamps = pd.date_range("2024-01-01", periods=60 * 96, freq="15min")
   hours = timestamps.hour + timestamps.minute / 60.0
   load = 50 + 30 * np.sin(2 * np.pi * (hours - 6) / 24)
   load += np.random.default_rng(42).normal(0, 3, size=len(timestamps))

   dataset = TimeSeriesDataset(
       data=pd.DataFrame({"load": load}, index=timestamps),
       sample_interval=timedelta(minutes=15),
       target_column="load",
   )

   # 2. Configure preprocessing
   preprocessing = FeaturePipeline(
       transforms=[
           HolidayTransform(country_code="NL"),
           LagTransform(lags=[timedelta(days=1), timedelta(days=7), timedelta(days=14)]),
           StandardScalerTransform(),
       ]
   )

   # 3. Build model
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(),
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=14),
   )

   # 4. Train
   train_preds, val_preds, test_preds, fit_result = model.fit(data=dataset)

   # 5. Predict
   forecast = model.predict(data=dataset)

   # 6. Save
   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model=model, model_id="my_first_forecast")


Next Steps
----------

Now that you understand the core workflow, explore these topics:

- :doc:`quickstart` — Minimal example for quick reference
- :doc:`backtesting` — Systematically compare model configurations
- :doc:`advanced_customization` — Use XGBoost/LightGBM, custom transforms, and probabilistic forecasting