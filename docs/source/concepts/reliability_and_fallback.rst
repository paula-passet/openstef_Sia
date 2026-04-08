Reliability and Fallback Strategies
====================================

Production forecasting systems must handle failures gracefully. When models fail to produce predictions—whether due to missing data, stale inputs, or runtime errors—your system needs fallback strategies to ensure continuous operation. This page covers practical approaches to building reliable forecasting pipelines using OpenSTEF.

Why Reliability Matters
-----------------------

Energy forecasting systems often feed critical operational decisions: grid balancing, trading positions, and capacity planning. A missing forecast can be worse than a slightly inaccurate one. Production systems need multiple layers of defense:

- **Data quality issues**: Sensor failures, network outages, or corrupted measurements
- **Model failures**: Runtime errors, numerical instability, or resource exhaustion  
- **Staleness**: Outdated training data or missing recent observations
- **Edge cases**: Unusual conditions not seen during training

OpenSTEF provides built-in tools for validation, fallback models, and graceful degradation.

Data Validation Transforms
---------------------------

OpenSTEF includes validation transforms that check data quality before model training or prediction. These transforms can detect problems early and provide clear error messages:

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker
   )
   from openstef_core.datasets import TimeSeriesDataset
   
   # Check for sufficient data completeness
   completeness = CompletenessChecker()
   
   try:
       validated_data = completeness.transform(data)
   except Exception as e:
       # Handle incomplete data - trigger fallback strategy
       print(f"Data completeness check failed: {e}")
       # Use fallback forecast
   
   # Detect flatline patterns (sensor stuck at same value)
   flatline = FlatlineChecker()
   
   if flatline.detect_ongoing_flatliner(data.data['load']):
       print("Warning: Flatline detected in load data")
       # Flag for manual review or use alternative data source

The ``CompletenessChecker`` validates that sufficient historical data exists for training. The ``FlatlineChecker`` detects when sensors report identical values repeatedly—a common hardware failure mode.

The ``InputConsistencyChecker`` ensures that prediction inputs match the features seen during training:

.. code-block:: python

   # During training pipeline setup
   consistency = InputConsistencyChecker()
   consistency.fit(training_data)
   
   # During prediction
   try:
       validated_input = consistency.transform(forecast_input)
   except Exception as e:
       print(f"Input mismatch: {e}")
       # Missing features or unexpected columns

This catches schema mismatches early, before they cause cryptic model errors.

Fallback Models: BaseCaseForecaster
------------------------------------

The simplest fallback strategy is a naive baseline model. OpenSTEF provides ``BaseCaseForecaster``, which repeats weekly patterns from historical data. This model serves two purposes:

1. **Baseline comparison**: Evaluate whether sophisticated models outperform simple patterns
2. **Production fallback**: Generate reasonable forecasts when primary models fail

The forecaster implements a two-tier fallback strategy internally:

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta
   
   # Configure with primary and fallback lags
   fallback_model = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams={
           'primary_lag': timedelta(days=7),    # Use last week
           'fallback_lag': timedelta(days=14)   # Fall back to 2 weeks ago
       }
   )
   
   fallback_model.fit(training_data)
   predictions = fallback_model.predict(forecast_input)

If data from 7 days ago is missing, the model automatically uses data from 14 days ago. This handles common scenarios like holiday weeks or data collection gaps.

Implementing Multi-Tier Fallback
---------------------------------

A robust production system typically uses multiple fallback layers:

.. code-block:: python

   from openstef_models.models.forecasting import XGBForecaster, BaseCaseForecaster
   from openstef_core.exceptions import InsufficientlyCompleteError
   
   # Primary model: sophisticated ML
   primary_model = XGBForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)]
   )
   
   # Fallback model: naive baseline
   fallback_model = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)]
   )
   
   def generate_forecast(data, forecast_input):
       """Generate forecast with automatic fallback."""
       
       # Validate input data first
       try:
           completeness = CompletenessChecker()
           validated_data = completeness.transform(data)
       except InsufficientlyCompleteError:
           print("Insufficient data for primary model, using fallback")
           fallback_model.fit(data)
           return fallback_model.predict(forecast_input)
       
       # Try primary model
       try:
           primary_model.fit(validated_data)
           predictions = primary_model.predict(forecast_input)
           return predictions
           
       except Exception as e:
           print(f"Primary model failed: {e}, using fallback")
           
           # Fall back to baseline model
           try:
               fallback_model.fit(data)
               return fallback_model.predict(forecast_input)
               
           except Exception as fallback_error:
               print(f"Fallback model also failed: {fallback_error}")
               # Last resort: return None or raise alert
               raise

This pattern ensures that forecasts are always available, even when the primary model encounters unexpected conditions.

Handling Missing Data
---------------------

OpenSTEF models handle missing data differently depending on the context:

**During training**, models typically drop rows with missing target values:

.. code-block:: python

   # The pipeline automatically drops rows where target is NaN
   pipeline.fit(data)  # Raises InsufficientlyCompleteError if too much data is missing

If all training data is missing targets, OpenSTEF raises ``InsufficientlyCompleteError`` rather than silently producing a useless model.

**During prediction**, lag-based models return NaN when required features are missing:

.. code-block:: python

   from openstef_models.models.forecasting import MedianForecaster
   
   median_model = MedianForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=1))]
   )
   
   median_model.fit(training_data)
   
   # If lag features are missing, predict returns NaN
   predictions = median_model.predict(forecast_input)
   
   # Check for NaN predictions and handle appropriately
   if predictions.data.isna().any().any():
       print("Warning: Some predictions are NaN due to missing features")
       # Trigger fallback or interpolation

For production systems, monitor the rate of NaN predictions as a health metric.

Model Staleness Detection
--------------------------

Models degrade over time as patterns change. Detect staleness by tracking prediction quality:

.. code-block:: python

   from datetime import datetime, timedelta
   
   class ModelMonitor:
       """Track model age and performance for staleness detection."""
       
       def __init__(self, max_age_days=30, error_threshold=1.5):
           self.training_date = None
           self.max_age = timedelta(days=max_age_days)
           self.error_threshold = error_threshold
           self.recent_errors = []
       
       def record_training(self):
           """Record when model was last trained."""
           self.training_date = datetime.now()
       
       def record_error(self, actual, predicted):
           """Track recent prediction errors."""
           error = abs(actual - predicted)
           self.recent_errors.append(error)
           
           # Keep only last 100 errors
           if len(self.recent_errors) > 100:
               self.recent_errors.pop(0)
       
       def is_stale(self):
           """Check if model needs retraining."""
           # Check age
           if self.training_date is None:
               return True
           
           age = datetime.now() - self.training_date
           if age > self.max_age:
               return True
           
           # Check error degradation
           if len(self.recent_errors) >= 50:
               recent_avg = sum(self.recent_errors[-20:]) / 20
               baseline_avg = sum(self.recent_errors[:30]) / 30
               
               if recent_avg > baseline_avg * self.error_threshold:
                   return True
           
           return False

Integrate this monitor into your prediction loop:

.. code-block:: python

   monitor = ModelMonitor(max_age_days=14)
   
   # After training
   model.fit(training_data)
   monitor.record_training()
   
   # During prediction
   predictions = model.predict(forecast_input)
   
   # After actuals arrive
   monitor.record_error(actual_load, predicted_load)
   
   if monitor.is_stale():
       print("Model is stale - triggering retraining")
       # Retrain or switch to fallback

Graceful Degradation Strategies
--------------------------------

When primary systems fail, degrade gracefully rather than failing completely:

**Reduce forecast horizon**: If weather forecasts are unavailable beyond 24 hours, produce shorter-term forecasts:

.. code-block:: python

   def adaptive_forecast(model, forecast_input, max_horizon_hours=47):
       """Produce forecast with available data."""
       
       # Check weather forecast availability
       weather_available_until = check_weather_availability(forecast_input)
       
       if weather_available_until < timedelta(hours=max_horizon_hours):
           print(f"Weather only available for {weather_available_until.total_seconds()/3600} hours")
           # Reduce horizon to match available weather
           reduced_horizons = [
               h for h in model.horizons 
               if h.value <= weather_available_until
           ]
           # Predict with reduced horizon
           return model.predict(forecast_input)  # Will only predict where features exist
       
       return model.predict(forecast_input)

**Widen confidence intervals**: When uncertainty is high, reflect this in predictions:

.. code-block:: python

   def adjust_confidence_for_uncertainty(predictions, uncertainty_factor=1.5):
       """Widen confidence intervals when data quality is poor."""
       
       median = predictions.data['q_0.5']
       lower = predictions.data['q_0.1']
       upper = predictions.data['q_0.9']
       
       # Widen intervals around median
       adjusted_lower = median - (median - lower) * uncertainty_factor
       adjusted_upper = median + (upper - median) * uncertainty_factor
       
       predictions.data['q_0.1'] = adjusted_lower
       predictions.data['q_0.9'] = adjusted_upper
       
       return predictions

**Reduce update frequency**: If retraining fails, continue using the existing model:

.. code-block:: python

   def safe_retrain(model, new_data, current_model_age):
       """Attempt retraining with fallback to existing model."""
       
       max_model_age = timedelta(days=60)  # Absolute limit
       
       try:
           model.fit(new_data)
           return model, timedelta(0)  # Successfully retrained
           
       except Exception as e:
           print(f"Retraining failed: {e}")
           
           if current_model_age > max_model_age:
               raise Exception("Model too old and retraining failed")
           
           # Continue with existing model
           print(f"Continuing with model age: {current_model_age}")
           return model, current_model_age + timedelta(days=1)

Production Checklist
--------------------

When deploying OpenSTEF in production, implement these reliability measures:

- **Validation**: Use ``CompletenessChecker`` and ``FlatlineChecker`` before training and prediction
- **Fallback models**: Keep a ``BaseCaseForecaster`` ready as backup
- **Error handling**: Catch and log exceptions from fit/predict operations
- **Staleness monitoring**: Track model age and prediction quality
- **Alerting**: Notify operators when fallbacks are triggered
- **Graceful degradation**: Reduce horizons or widen intervals rather than failing
- **Health metrics**: Monitor NaN prediction rates, fallback trigger frequency, and error trends

See Also
--------

- :doc:`forecasting_basics` - Understanding what short-term forecasting provides
- :doc:`model_selection` - Choosing appropriate primary and fallback models
- :doc:`feature_engineering` - Ensuring robust feature availability