Reliability and Fallback Strategies
====================================

When deploying forecasting models in production, things will go wrong. Data feeds fail, models produce unexpected outputs, and edge cases emerge that weren't caught during development. This page covers practical strategies for building reliable forecasting systems that degrade gracefully when problems occur.

Understanding Production Failures
----------------------------------

Production forecasting systems face several categories of failures:

**Data availability issues**: Missing weather forecasts, incomplete load measurements, or delayed data feeds. These are common in real-world systems where multiple data sources must synchronize.

**Data quality problems**: Flatlined sensors, outliers from faulty equipment, or sudden pattern changes that don't reflect reality. A sensor stuck at zero or reporting the same value for hours can poison model predictions.

**Model failures**: Training failures, prediction errors, or models that haven't been retrained recently enough to capture current patterns. Even well-tested models can fail when encountering data distributions they've never seen.

**Infrastructure issues**: Service outages, memory constraints, or timeout errors during prediction. Production systems must handle these gracefully rather than crashing.

The key principle: **always have a fallback**. Every component should have a simpler alternative that can take over when the primary approach fails.

Fallback Forecasting Models
----------------------------

OpenSTEF provides the ``BaseCaseForecaster`` as a robust fallback model. This simple forecaster repeats weekly patterns and serves as a baseline when more sophisticated models fail:

.. code-block:: python

   from openstef_models.models.forecasting.base_case import BaseCaseForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   # Configure fallback forecaster with custom lag periods
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),    # Use last week's pattern
           fallback_lag=timedelta(days=14),  # Fall back to 2 weeks ago
       ),
   )

The ``BaseCaseForecaster`` implements its own two-tier fallback strategy: it prioritizes the 7-day lag (capturing weekly patterns) but automatically falls back to the 14-day lag when recent data is unavailable. This makes it exceptionally robust for production use.

A practical fallback strategy wraps your primary model with the base case forecaster:

.. code-block:: python

   def predict_with_fallback(forecaster, fallback_forecaster, data):
       """Predict with automatic fallback to base case model."""
       try:
           # Attempt prediction with primary model
           prediction = forecaster.predict(data)
           
           # Validate prediction quality
           if prediction.data.isnull().any().any():
               raise ValueError("Primary model produced NaN values")
           
           return prediction, "primary"
           
       except Exception as e:
           # Log the failure for investigation
           logger.warning(f"Primary model failed: {e}. Using fallback.")
           
           # Use base case forecaster as fallback
           prediction = fallback_forecaster.predict(data)
           return prediction, "fallback"

This pattern ensures you always produce a forecast, even when the primary model encounters unexpected issues.

Handling Missing Data
---------------------

Missing data is inevitable in production. OpenSTEF provides multiple imputation strategies through the ``MissingValueImputer`` transform:

.. code-block:: python

   from openstef_models.transforms.preprocessing import MissingValueImputer

   # Simple forward-fill strategy for real-time predictions
   simple_imputer = MissingValueImputer(
       strategy="mean",
       missing_value=np.nan,
   )

   # More sophisticated iterative imputation for training
   iterative_imputer = MissingValueImputer(
       strategy="iterative",
       missing_value=np.nan,
   )

   # Apply during preprocessing
   data_imputed = simple_imputer.fit_transform(training_data)

Choose your imputation strategy based on the context:

- **mean/median**: Fast and simple, suitable for real-time prediction pipelines
- **iterative**: More accurate but slower, better for training data preparation
- **forward fill**: Appropriate for slowly-changing features like temperature

For production systems, consider the trade-off between imputation quality and latency. A simple mean imputation that returns results in milliseconds is often better than a sophisticated method that times out.

Data Quality Validation
------------------------

OpenSTEF includes validation transforms that check data quality before prediction:

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker,
   )

   # Check for sufficient data coverage
   completeness_checker = CompletenessChecker()
   
   # Detect flatlined sensors
   flatline_checker = FlatlineChecker()
   
   # Ensure input consistency between training and prediction
   consistency_checker = InputConsistencyChecker()

   # Build validation pipeline
   validation_pipeline = TransformPipeline(
       transforms=[
           completeness_checker,
           flatline_checker,
           consistency_checker,
       ]
   )

   # Apply validation
   try:
       validated_data = validation_pipeline.transform(input_data)
   except ValueError as e:
       # Data quality issue detected - use fallback strategy
       logger.error(f"Data validation failed: {e}")
       # Trigger fallback forecast or alert operators

The ``FlatlineChecker`` is particularly valuable for detecting sensor failures. It can identify when measurements are stuck at constant values, indicating a hardware or communication problem rather than actual load patterns.

Model Staleness Detection
--------------------------

Models degrade over time as patterns change. Detecting staleness helps you know when retraining is needed:

.. code-block:: python

   from datetime import datetime, timedelta

   def check_model_staleness(model, max_age_days=30):
       """Check if model needs retraining based on age."""
       if not hasattr(model, 'training_timestamp'):
           return True, "No training timestamp found"
       
       model_age = datetime.now() - model.training_timestamp
       
       if model_age > timedelta(days=max_age_days):
           return True, f"Model is {model_age.days} days old"
       
       return False, f"Model age: {model_age.days} days"

   def check_prediction_quality(predictions, actuals, threshold=0.3):
       """Check if recent prediction quality has degraded."""
       recent_predictions = predictions.tail(168)  # Last week
       recent_actuals = actuals.tail(168)
       
       # Calculate recent error
       mae = (recent_predictions - recent_actuals).abs().mean()
       normalized_mae = mae / recent_actuals.mean()
       
       if normalized_mae > threshold:
           return True, f"Recent MAE: {normalized_mae:.2%}"
       
       return False, f"Recent MAE: {normalized_mae:.2%}"

Combine age-based and performance-based staleness detection for robust monitoring:

.. code-block:: python

   def should_retrain(model, predictions, actuals):
       """Determine if model retraining is needed."""
       stale_age, age_msg = check_model_staleness(model, max_age_days=30)
       stale_quality, quality_msg = check_prediction_quality(
           predictions, actuals, threshold=0.3
       )
       
       if stale_age or stale_quality:
           logger.warning(f"Retraining needed: {age_msg}, {quality_msg}")
           return True
       
       return False

Graceful Degradation Patterns
------------------------------

Production systems should degrade gracefully through multiple fallback tiers:

.. code-block:: python

   class RobustForecaster:
       """Forecaster with multiple fallback tiers."""
       
       def __init__(self, primary_model, secondary_model, base_case_model):
           self.primary = primary_model
           self.secondary = secondary_model
           self.base_case = base_case_model
       
       def predict(self, data):
           """Predict with multi-tier fallback strategy."""
           # Tier 1: Primary model (e.g., XGBoost)
           try:
               prediction = self.primary.predict(data)
               if self._validate_prediction(prediction):
                   return prediction, "primary"
           except Exception as e:
               logger.warning(f"Primary model failed: {e}")
           
           # Tier 2: Secondary model (e.g., Linear)
           try:
               prediction = self.secondary.predict(data)
               if self._validate_prediction(prediction):
                   return prediction, "secondary"
           except Exception as e:
               logger.warning(f"Secondary model failed: {e}")
           
           # Tier 3: Base case (always works)
           prediction = self.base_case.predict(data)
           return prediction, "base_case"
       
       def _validate_prediction(self, prediction):
           """Check if prediction is reasonable."""
           data = prediction.data
           
           # Check for NaN values
           if data.isnull().any().any():
               return False
           
           # Check for negative values (if inappropriate)
           if (data < 0).any().any():
               return False
           
           # Check for unreasonable magnitudes
           if (data > 1e6).any().any():
               return False
           
           return True

This pattern ensures you always produce a forecast, with clear logging of which tier was used. This information is valuable for monitoring system health and identifying persistent issues.

Monitoring and Alerting
------------------------

Track which fallback strategies are triggered to identify systemic issues:

.. code-block:: python

   from collections import defaultdict
   from datetime import datetime

   class FallbackMonitor:
       """Monitor fallback usage patterns."""
       
       def __init__(self):
           self.fallback_counts = defaultdict(int)
           self.last_reset = datetime.now()
       
       def record_prediction(self, model_tier):
           """Record which model tier was used."""
           self.fallback_counts[model_tier] += 1
       
       def get_fallback_rate(self):
           """Calculate percentage of predictions using fallback."""
           total = sum(self.fallback_counts.values())
           if total == 0:
               return 0.0
           
           fallback = total - self.fallback_counts.get("primary", 0)
           return fallback / total
       
       def should_alert(self, threshold=0.1):
           """Alert if fallback rate exceeds threshold."""
           rate = self.get_fallback_rate()
           if rate > threshold:
               return True, f"Fallback rate: {rate:.1%}"
           return False, f"Fallback rate: {rate:.1%}"

Use this monitoring to set up alerts when fallback usage indicates problems with your primary models or data sources.

Lessons from Production
-----------------------

OpenSTEF is used in production at Alliander for over 10,000 grid locations. Key lessons learned:

**Always have a working forecast**: It's better to produce a simple but reliable forecast than to fail completely. The ``BaseCaseForecaster`` ensures you can always generate predictions.

**Validate early and often**: Catch data quality issues before they reach your models. The validation transforms help detect problems at ingestion time.

**Monitor fallback patterns**: High fallback usage indicates systemic issues. Track which fallback tiers are used and investigate patterns.

**Test failure modes**: Don't just test the happy path. Deliberately inject missing data, bad data, and model failures to verify your fallback strategies work.

**Keep fallback models simple**: Complex fallback models can fail too. The base case forecaster works because it's nearly impossible to break.

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding what short-term forecasting is and why it matters
- :doc:`model_selection` - Choosing the right primary forecasting model
- :doc:`feature_engineering` - Building robust features that handle missing data well