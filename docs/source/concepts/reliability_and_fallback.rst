Reliability and Fallback Strategies
====================================

When forecasting models run in production, failures are inevitable. Input data may be incomplete, external APIs may timeout, or models may produce unrealistic predictions. This page covers strategies to ensure your forecasting system degrades gracefully rather than failing catastrophically.

Understanding Production Failures
----------------------------------

Production forecasting systems face several types of failures:

**Missing or incomplete data**: Weather APIs fail, sensor data arrives late, or database connections timeout. Your model may require features that simply aren't available at prediction time.

**Model prediction failures**: The model itself may fail to produce predictions due to unexpected input patterns, numerical instability, or bugs triggered by edge cases.

**Stale models**: A model trained weeks ago may no longer reflect current patterns. Energy consumption shifts due to holidays, weather regime changes, or grid modifications.

**Unrealistic predictions**: The model produces a prediction, but it's clearly wrong—negative load values, sudden spikes that violate physical constraints, or predictions that diverge wildly from recent observations.

The key principle: **always have a fallback**. Never let your system return no prediction when downstream systems depend on it.

Fallback Prediction Strategies
-------------------------------

OpenSTEF implements several fallback strategies, from sophisticated to simple:

Primary Model with Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Your primary forecasting model (XGBoost, LightGBM, etc.) should be your first choice. But wrap predictions with validation:

.. code-block:: python

   from openstef_core.datasets.validated_datasets import ForecastDataset
   
   def predict_with_validation(forecaster, data, target_column="load"):
       """Predict with basic validation checks."""
       try:
           predictions = forecaster.predict(data)
           
           # Check for NaN values
           if predictions.data[target_column].isna().any():
               return None, "predictions contain NaN"
           
           # Check for negative values (if physically impossible)
           if (predictions.data[target_column] < 0).any():
               return None, "predictions contain negative values"
           
           # Check for unrealistic magnitude
           recent_max = data.data[target_column].tail(168).max()  # Last week
           if predictions.data[target_column].max() > 3 * recent_max:
               return None, "predictions exceed 3x recent maximum"
           
           return predictions, None
           
       except Exception as e:
           return None, f"prediction failed: {str(e)}"

Base Case Forecaster as Fallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's ``BaseCaseForecaster`` provides a robust fallback by repeating weekly patterns. It's simple but surprisingly effective for energy forecasting:

.. code-block:: python

   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta
   
   # Create fallback forecaster
   fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),    # Use last week
           fallback_lag=timedelta(days=14),  # If unavailable, use 2 weeks ago
       ),
   )
   
   # Fit on historical data (just stores the pattern)
   fallback.fit(training_data)
   
   # Use as fallback when primary model fails
   primary_pred, error = predict_with_validation(primary_model, forecast_data)
   
   if primary_pred is None:
       print(f"Primary model failed: {error}, using base case fallback")
       prediction = fallback.predict(forecast_data)
   else:
       prediction = primary_pred

The ``BaseCaseForecaster`` has its own fallback mechanism: if the primary lag (7 days) isn't available, it automatically falls back to the fallback lag (14 days). This makes it extremely robust.

Last Known Good Prediction
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For very short-term forecasts (next 15 minutes to 1 hour), the most recent prediction may still be valid:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   
   class PredictionCache:
       """Cache predictions with timestamps for fallback."""
       
       def __init__(self, max_age: timedelta = timedelta(hours=2)):
           self.max_age = max_age
           self.last_prediction = None
           self.last_timestamp = None
       
       def store(self, prediction, timestamp=None):
           """Store a successful prediction."""
           self.last_prediction = prediction
           self.last_timestamp = timestamp or datetime.now()
       
       def get_fallback(self, forecast_start):
           """Get cached prediction if recent enough."""
           if self.last_prediction is None:
               return None
           
           age = datetime.now() - self.last_timestamp
           if age > self.max_age:
               return None
           
           # Shift the cached prediction forward in time
           time_shift = forecast_start - self.last_prediction.forecast_start
           shifted_data = self.last_prediction.data.copy()
           shifted_data.index = shifted_data.index + time_shift
           
           return shifted_data

This approach works because energy load patterns change slowly. A prediction made 30 minutes ago, shifted forward, is often better than no prediction.

Handling Missing Input Data
----------------------------

Missing features are a common cause of prediction failures. OpenSTEF provides several mechanisms to handle this:

Lag Features as Reliable Fallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Lag features (historical values of the target variable) are the most reliable features because they depend only on your own data, not external APIs:

.. code-block:: python

   from openstef_models.transforms.features import LagTransform
   from datetime import timedelta
   
   # Add lag features that don't depend on external data
   lag_transform = LagTransform(
       target_column="load",
       lags=[
           timedelta(days=1),
           timedelta(days=7),
           timedelta(days=14),
       ],
   )

If weather data is missing, a model trained with both weather and lag features can often still make reasonable predictions using just the lags.

Graceful Feature Degradation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Train models that can handle missing features by using algorithms that support sparse input (like tree-based models) or by explicitly handling NaN values:

.. code-block:: python

   from openstef_models.models.forecasting.xgb import XGBForecaster
   
   # XGBoost handles missing values internally
   forecaster = XGBForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
   )
   
   # Model will use available features and handle missing ones
   forecaster.fit(training_data)
   prediction = forecaster.predict(forecast_data_with_missing_features)

Tree-based models learn to route samples with missing features down alternative branches, providing natural robustness.

Detecting Model Staleness
--------------------------

A model trained months ago may no longer be accurate. Detect staleness by monitoring prediction quality:

.. code-block:: python

   from datetime import datetime, timedelta
   import numpy as np
   
   class StalenessDetector:
       """Detect when model predictions degrade over time."""
       
       def __init__(
           self,
           window_size: int = 168,  # 1 week of hourly data
           error_threshold: float = 1.5,  # 50% worse than training
       ):
           self.window_size = window_size
           self.error_threshold = error_threshold
           self.recent_errors = []
           self.training_error = None
       
       def set_training_error(self, error: float):
           """Set baseline error from training/validation."""
           self.training_error = error
       
       def add_observation(self, predicted: float, actual: float):
           """Add a new prediction-actual pair."""
           error = abs(predicted - actual)
           self.recent_errors.append(error)
           
           # Keep only recent window
           if len(self.recent_errors) > self.window_size:
               self.recent_errors.pop(0)
       
       def is_stale(self) -> bool:
           """Check if model appears stale."""
           if self.training_error is None or len(self.recent_errors) < self.window_size:
               return False
           
           recent_mae = np.mean(self.recent_errors)
           return recent_mae > self.training_error * self.error_threshold

When staleness is detected, trigger model retraining or switch to a more robust fallback strategy.

Implementing a Complete Fallback Chain
---------------------------------------

In production, implement a fallback chain that tries strategies in order of sophistication:

.. code-block:: python

   from typing import Optional
   from openstef_core.datasets.validated_datasets import ForecastDataset
   
   class RobustForecaster:
       """Forecaster with complete fallback chain."""
       
       def __init__(self, primary_model, base_case_model, cache):
           self.primary = primary_model
           self.base_case = base_case_model
           self.cache = cache
           self.staleness_detector = StalenessDetector()
       
       def predict(self, data: ForecastDataset) -> ForecastDataset:
           """Predict with full fallback chain."""
           
           # Try primary model
           try:
               if not self.staleness_detector.is_stale():
                   prediction, error = predict_with_validation(
                       self.primary, data
                   )
                   if prediction is not None:
                       self.cache.store(prediction)
                       return prediction
                   else:
                       print(f"Primary validation failed: {error}")
           except Exception as e:
               print(f"Primary model error: {e}")
           
           # Try base case model
           try:
               prediction = self.base_case.predict(data)
               if prediction is not None:
                   self.cache.store(prediction)
                   return prediction
           except Exception as e:
               print(f"Base case model error: {e}")
           
           # Try cached prediction
           cached = self.cache.get_fallback(data.forecast_start)
           if cached is not None:
               print("Using cached prediction fallback")
               return cached
           
           # Last resort: return historical mean
           print("All fallbacks failed, using historical mean")
           return self._historical_mean_fallback(data)
       
       def _historical_mean_fallback(self, data: ForecastDataset):
           """Absolute last resort: historical average by hour."""
           historical = data.data[data.target_column].dropna()
           hourly_means = historical.groupby(historical.index.hour).mean()
           
           # Create forecast using hourly averages
           forecast_index = pd.date_range(
               data.forecast_start,
               periods=len(data.horizons),
               freq=data.frequency,
           )
           forecast_values = [hourly_means[t.hour] for t in forecast_index]
           
           return ForecastDataset(
               data=pd.DataFrame({
                   data.target_column: forecast_values
               }, index=forecast_index),
               forecast_start=data.forecast_start,
               frequency=data.frequency,
               horizons=data.horizons,
               target_column=data.target_column,
           )

Practical Recommendations
--------------------------

Based on production experience with OpenSTEF:

1. **Always implement at least two fallback levels**: Primary model → Base case → Last known good.

2. **Monitor fallback usage**: If you're frequently falling back, investigate root causes. High fallback rates indicate data quality issues or model problems.

3. **Test fallback paths regularly**: Don't wait for production failures. Regularly test that fallbacks work by simulating missing data and model failures.

4. **Set appropriate staleness thresholds**: Energy patterns change seasonally. A model trained in summer may be stale by winter, even if recent errors look acceptable.

5. **Log everything**: Record which fallback strategy was used for each prediction. This data is invaluable for debugging and improving reliability.

6. **Use validation transforms**: OpenSTEF provides ``CompletenessChecker`` and ``FlatlineChecker`` transforms to detect data quality issues before they cause prediction failures.

For more on model selection and when to use different forecasting approaches, see :doc:`model_selection`. For understanding how to work with the probabilistic predictions these models produce, see :doc:`quantiles_and_confidence`.