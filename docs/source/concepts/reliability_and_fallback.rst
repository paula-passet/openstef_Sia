Reliability and Fallback Strategies
====================================

When deploying forecasting models in production, failures are inevitable. Data sources go offline, models produce unrealistic predictions, and external systems experience outages. This page covers practical strategies for building reliable forecasting systems that degrade gracefully when things go wrong.

Understanding Failure Modes
----------------------------

Production forecasting systems face several common failure scenarios:

**Missing or incomplete data**: Weather APIs fail, sensor data contains gaps, or upstream systems don't deliver expected inputs. Your forecasting pipeline must handle these gracefully rather than crashing or producing no forecast at all.

**Model prediction failures**: Models can fail to produce predictions due to invalid inputs, numerical instability, or unexpected data patterns. A robust system needs fallback strategies when the primary model cannot generate forecasts.

**Stale or unrealistic predictions**: Models may produce technically valid outputs that are clearly wrong—negative load values, predictions orders of magnitude off from recent observations, or forecasts that violate known physical constraints.

**Model staleness**: A model trained months ago may no longer reflect current patterns. Production systems need mechanisms to detect when model performance degrades and trigger retraining.

Fallback Model Strategies
--------------------------

The most reliable approach to handling model failures is maintaining a hierarchy of forecasting models, from sophisticated to simple. When a complex model fails, fall back to simpler alternatives.

OpenSTEF includes a ``BaseCaseForecaster`` specifically designed as a robust fallback model. This model implements a simple but effective strategy: repeat the load pattern from last week. Despite its simplicity, this baseline often performs reasonably well for energy forecasting due to strong weekly patterns in electricity consumption.

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecaster, XGBForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta
   
   # Primary sophisticated model
   primary_model = XGBForecaster(
       horizons=[LeadTime(timedelta(hours=h)) for h in [1, 6, 12, 24]],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )
   
   # Fallback baseline model
   fallback_model = BaseCaseForecaster(
       horizons=[LeadTime(timedelta(hours=h)) for h in [1, 6, 12, 24]],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=14)
       )
   )
   
   # Attempt primary model, fall back if it fails
   try:
       forecast = primary_model.predict(dataset)
       # Validate forecast quality
       if is_forecast_valid(forecast):
           return forecast
       else:
           print("Primary model produced invalid forecast, using fallback")
           return fallback_model.predict(dataset)
   except Exception as e:
       print(f"Primary model failed: {e}, using fallback")
       return fallback_model.predict(dataset)

The ``BaseCaseForecaster`` itself implements a two-tier fallback strategy. It primarily uses data from 7 days ago (configurable via ``primary_lag``), but if that data is missing, it falls back to 14 days ago (``fallback_lag``). This nested fallback approach ensures the model can produce forecasts even with significant data gaps.

Handling Missing and Bad Data
------------------------------

Data quality issues are among the most common production problems. OpenSTEF provides validation transforms to detect and handle problematic data before it reaches your models.

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker
   )
   from openstef_core.datasets import TimeSeriesDataset
   
   # Check for sufficient data completeness
   completeness_checker = CompletenessChecker()
   
   # Detect flatline patterns (sensor failures)
   flatline_checker = FlatlineChecker()
   
   # Ensure input features match training
   consistency_checker = InputConsistencyChecker()
   
   # Apply validation pipeline
   try:
       # Check completeness
       validated_data = completeness_checker.transform(dataset)
       
       # Detect flatlines
       validated_data = flatline_checker.transform(validated_data)
       
       # Verify feature consistency
       consistency_checker.fit(training_dataset)
       validated_data = consistency_checker.transform(validated_data)
       
   except Exception as e:
       print(f"Data validation failed: {e}")
       # Use fallback forecast or cached previous forecast

The ``CompletenessChecker`` raises an error if the dataset lacks sufficient data for reliable forecasting. The ``FlatlineChecker`` detects when recent measurements are suspiciously constant, indicating potential sensor failures. The ``InputConsistencyChecker`` ensures prediction inputs match the features the model was trained on, automatically removing unexpected columns and warning about missing expected features.

For missing features, implement graceful degradation strategies:

.. code-block:: python

   def prepare_forecast_input(dataset, required_features, optional_features):
       """Prepare input with graceful handling of missing features."""
       available_features = set(dataset.feature_names)
       
       # Check required features
       missing_required = set(required_features) - available_features
       if missing_required:
           raise ValueError(f"Missing required features: {missing_required}")
       
       # Use optional features if available
       missing_optional = set(optional_features) - available_features
       if missing_optional:
           print(f"Optional features unavailable: {missing_optional}")
           # Model may perform worse but can still run
       
       # Use only available features
       features_to_use = list(available_features & 
                             (set(required_features) | set(optional_features)))
       
       return dataset.select_features(features_to_use)

Forecast Quality Validation
----------------------------

Even when models successfully produce predictions, those predictions may be unrealistic. Implement validation checks to catch bad forecasts before they reach downstream systems:

.. code-block:: python

   def validate_forecast_quality(forecast, historical_data, thresholds):
       """Validate forecast against quality criteria."""
       issues = []
       
       # Check for negative values (impossible for load)
       if (forecast.data['forecast'] < 0).any():
           issues.append("Negative forecast values detected")
       
       # Check for unrealistic magnitude
       recent_max = historical_data['load'].tail(168).max()  # Last week
       recent_min = historical_data['load'].tail(168).min()
       
       forecast_max = forecast.data['forecast'].max()
       forecast_min = forecast.data['forecast'].min()
       
       if forecast_max > recent_max * thresholds['max_ratio']:
           issues.append(f"Forecast exceeds recent max by {thresholds['max_ratio']}x")
       
       if forecast_min < recent_min * thresholds['min_ratio']:
           issues.append(f"Forecast below recent min by {thresholds['min_ratio']}x")
       
       # Check for flatlines in forecast (model failure indicator)
       if forecast.data['forecast'].nunique() < len(forecast.data) * 0.1:
           issues.append("Forecast contains suspicious flatline pattern")
       
       # Check for NaN values
       if forecast.data['forecast'].isna().any():
           issues.append("Forecast contains NaN values")
       
       return len(issues) == 0, issues
   
   # Usage
   is_valid, issues = validate_forecast_quality(
       forecast, 
       historical_data,
       thresholds={'max_ratio': 2.0, 'min_ratio': 0.5}
   )
   
   if not is_valid:
       print(f"Forecast quality issues: {issues}")
       # Use fallback forecast or previous forecast

Model Staleness Detection
--------------------------

Models degrade over time as patterns change. Detect staleness by monitoring prediction performance against actual observations:

.. code-block:: python

   from datetime import datetime, timedelta
   import numpy as np
   
   class ModelStalenessMonitor:
       """Monitor model performance to detect staleness."""
       
       def __init__(self, error_threshold=0.15, window_days=7):
           self.error_threshold = error_threshold
           self.window_days = window_days
           self.recent_errors = []
           self.baseline_error = None
       
       def set_baseline(self, validation_error):
           """Set baseline error from initial validation."""
           self.baseline_error = validation_error
       
       def record_prediction(self, forecast, actual):
           """Record a prediction and its actual outcome."""
           error = np.abs(forecast - actual) / actual
           self.recent_errors.append({
               'timestamp': datetime.now(),
               'error': error
           })
           
           # Keep only recent window
           cutoff = datetime.now() - timedelta(days=self.window_days)
           self.recent_errors = [
               e for e in self.recent_errors 
               if e['timestamp'] > cutoff
           ]
       
       def is_model_stale(self):
           """Check if model performance has degraded significantly."""
           if not self.recent_errors or self.baseline_error is None:
               return False
           
           recent_mean_error = np.mean([e['error'] for e in self.recent_errors])
           
           # Model is stale if error increased by threshold percentage
           return recent_mean_error > self.baseline_error * (1 + self.error_threshold)
       
       def get_status(self):
           """Get current monitoring status."""
           if not self.recent_errors:
               return "No recent predictions"
           
           recent_mean_error = np.mean([e['error'] for e in self.recent_errors])
           
           return {
               'recent_mean_error': recent_mean_error,
               'baseline_error': self.baseline_error,
               'is_stale': self.is_model_stale(),
               'samples': len(self.recent_errors)
           }

Integrate staleness monitoring into your production pipeline:

.. code-block:: python

   monitor = ModelStalenessMonitor(error_threshold=0.15, window_days=7)
   monitor.set_baseline(validation_error=0.08)  # From initial validation
   
   # In production loop
   forecast = model.predict(dataset)
   
   # Later, when actuals are available
   monitor.record_prediction(forecast.data['forecast'].iloc[0], actual_load)
   
   # Periodically check staleness
   status = monitor.get_status()
   if status['is_stale']:
       print("Model performance degraded, triggering retraining")
       trigger_model_retraining()

Graceful Degradation Patterns
------------------------------

When multiple components fail, implement graceful degradation that prioritizes availability over accuracy:

.. code-block:: python

   class RobustForecastingPipeline:
       """Forecasting pipeline with multiple fallback levels."""
       
       def __init__(self, primary_model, fallback_model, cache):
           self.primary_model = primary_model
           self.fallback_model = fallback_model
           self.cache = cache
       
       def generate_forecast(self, dataset):
           """Generate forecast with fallback strategy."""
           
           # Level 1: Try primary model with full features
           try:
               forecast = self.primary_model.predict(dataset)
               if self._validate_forecast(forecast):
                   self.cache.store(forecast)
                   return forecast, "primary"
           except Exception as e:
               print(f"Primary model failed: {e}")
           
           # Level 2: Try primary model with reduced features
           try:
               reduced_dataset = self._use_only_core_features(dataset)
               forecast = self.primary_model.predict(reduced_dataset)
               if self._validate_forecast(forecast):
                   self.cache.store(forecast)
                   return forecast, "primary_reduced"
           except Exception as e:
               print(f"Primary model with reduced features failed: {e}")
           
           # Level 3: Try fallback baseline model
           try:
               forecast = self.fallback_model.predict(dataset)
               if self._validate_forecast(forecast):
                   self.cache.store(forecast)
                   return forecast, "fallback"
           except Exception as e:
               print(f"Fallback model failed: {e}")
           
           # Level 4: Return cached previous forecast
           cached = self.cache.retrieve_latest()
           if cached is not None:
               print("Using cached forecast from previous run")
               return cached, "cached"
           
           # Level 5: Return naive persistence forecast
           print("All methods failed, using persistence forecast")
           return self._persistence_forecast(dataset), "persistence"
       
       def _validate_forecast(self, forecast):
           """Basic forecast validation."""
           return not forecast.data['forecast'].isna().any()
       
       def _use_only_core_features(self, dataset):
           """Reduce to core features only."""
           core_features = ['load_lag_7d', 'hour', 'dayofweek']
           available_core = [f for f in core_features if f in dataset.feature_names]
           return dataset.select_features(available_core)
       
       def _persistence_forecast(self, dataset):
           """Simplest possible forecast: repeat last known value."""
           last_value = dataset.data['load'].iloc[-1]
           # Create forecast with repeated last value
           # (implementation details omitted for brevity)
           return create_persistence_forecast(last_value, horizons)

This multi-level fallback strategy ensures your system always produces some forecast, even under severe failure conditions. The quality degrades gracefully from sophisticated ML models to simple baselines, but the system never fails completely.

.. note::

   For more information on choosing appropriate models for your primary forecasting system, see :doc:`model_selection`. For understanding how to work with the probabilistic forecasts these models produce, see :doc:`quantiles_and_confidence`.