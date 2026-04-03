Reliability and Fallback Strategies
====================================

Production forecasting systems must handle failures gracefully. Models can fail for many reasons: missing input data, stale training data, corrupted features, or unexpected data patterns. This page covers practical strategies for building reliable forecasting systems that degrade gracefully when things go wrong.

Why Reliability Matters
-----------------------

In production environments, forecasts drive critical decisions: energy trading, grid balancing, and capacity planning. A missing forecast can be worse than a simple one. OpenSTEF provides multiple layers of defense to ensure your system always produces usable predictions.

The key principle: **always have a fallback**. When sophisticated models fail, simpler approaches should take over automatically.

Fallback Model Hierarchy
-------------------------

OpenSTEF implements a natural hierarchy of model complexity. When a complex model fails, the system can fall back to progressively simpler approaches:

1. **Primary model** (e.g., XGBoost with weather features)
2. **Base case model** (weekly pattern repetition)
3. **Constant median** (historical average)

The ``BaseCaseForecaster`` serves as an excellent fallback model. It repeats weekly patterns from historical data, capturing the strong weekly periodicity in energy consumption without requiring weather forecasts or complex features:

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   # Configure base case as fallback
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams={
           "primary_lag": timedelta(days=7),    # Use last week
           "fallback_lag": timedelta(days=14),  # Fall back to 2 weeks ago
       }
   )

The base case model itself has a fallback mechanism: if 7-day lag data is missing, it automatically uses 14-day lag data. This two-tier approach handles common data gaps.

Handling Missing Input Data
----------------------------

Missing features are one of the most common production issues. Weather forecasts may be delayed, sensors may fail, or data pipelines may have gaps.

Detecting Incomplete Data
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides validation transforms to detect data quality issues before they cause prediction failures:

.. code-block:: python

   from openstef_models.transforms.validation import (
       CompletenessChecker,
       FlatlineChecker,
       InputConsistencyChecker
   )
   from openstef_core.transforms import TransformPipeline

   # Build validation pipeline
   validation = TransformPipeline([
       CompletenessChecker(
           min_completeness=0.9,  # Require 90% complete data
           check_columns=["load", "temperature"]
       ),
       FlatlineChecker(
           check_column="load",
           min_variance=0.01  # Detect stuck sensors
       ),
       InputConsistencyChecker()  # Verify feature consistency
   ])

   # Apply validation before prediction
   try:
       validated_data = validation.transform(input_data)
       predictions = primary_model.predict(validated_data)
   except Exception as e:
       # Fall back to base case model
       predictions = fallback_model.predict(input_data)

The ``CompletenessChecker`` raises an error if data is too sparse, allowing you to catch the issue and switch to a fallback strategy. The ``FlatlineChecker`` detects sensor failures where values stop changing—a common hardware issue in production systems.

Handling NaN Values
^^^^^^^^^^^^^^^^^^^

OpenSTEF models handle NaN values differently depending on context:

- **Training data**: Rows with NaN targets are automatically dropped. If all training data is lost, an ``InsufficientlyCompleteError`` is raised.
- **Feature data**: Lag-based features naturally create NaN values for the first N rows. Configure ``predict_history`` to account for this.
- **Prediction time**: If all lag features are NaN, models return NaN predictions rather than failing.

When using lag transforms, ensure your prediction window accounts for the lag duration:

.. code-block:: python

   from openstef_models.preprocessing import LagTransform
   from datetime import timedelta

   # Create 14-day lag features
   lag_transform = LagTransform(
       lag_duration=timedelta(days=14),
       columns=["load"]
   )

   # Configure model to request enough history
   model = ForecastingModel(
       forecaster=my_forecaster,
       predict_history=timedelta(days=14)  # Match lag duration
   )

This ensures the model has enough historical data to compute lag features without NaN values.

Model Staleness Detection
--------------------------

Models degrade over time as patterns shift. Detecting staleness is critical for maintaining forecast quality.

Time-Based Staleness
^^^^^^^^^^^^^^^^^^^^

The simplest approach tracks model age:

.. code-block:: python

   from datetime import datetime, timedelta

   def is_model_stale(model_metadata, max_age=timedelta(days=7)):
       """Check if model is too old."""
       training_date = model_metadata.get("trained_at")
       if training_date is None:
           return True
       
       age = datetime.now() - training_date
       return age > max_age

   # In production workflow
   if is_model_stale(model.metadata):
       # Trigger retraining or use fallback
       predictions = fallback_model.predict(data)
   else:
       predictions = model.predict(data)

For energy forecasting, weekly retraining is common. Recent patterns (holidays, weather trends, consumption shifts) have the most predictive power.

Performance-Based Staleness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

More sophisticated systems monitor prediction quality and trigger retraining when performance degrades:

.. code-block:: python

   def check_prediction_quality(predictions, actuals, threshold=0.15):
       """Monitor forecast error and detect degradation."""
       from sklearn.metrics import mean_absolute_percentage_error
       
       mape = mean_absolute_percentage_error(actuals, predictions)
       
       if mape > threshold:
           return {"stale": True, "mape": mape}
       return {"stale": False, "mape": mape}

   # Track rolling forecast quality
   quality = check_prediction_quality(
       recent_predictions,
       recent_actuals,
       threshold=0.15  # 15% MAPE threshold
   )
   
   if quality["stale"]:
       # Model performance has degraded
       trigger_retraining()

This approach catches model drift caused by changing patterns, not just age.

Graceful Degradation Patterns
------------------------------

Production systems should degrade gracefully through multiple fallback layers.

Try-Except Cascades
^^^^^^^^^^^^^^^^^^^

The most straightforward pattern uses nested exception handling:

.. code-block:: python

   def predict_with_fallbacks(data, primary, base_case, constant):
       """Attempt prediction with multiple fallback layers."""
       
       # Try primary model
       try:
           return primary.predict(data)
       except Exception as e:
           logger.warning(f"Primary model failed: {e}")
       
       # Fall back to base case
       try:
           return base_case.predict(data)
       except Exception as e:
           logger.warning(f"Base case failed: {e}")
       
       # Last resort: constant median
       try:
           return constant.predict(data)
       except Exception as e:
           logger.error(f"All models failed: {e}")
           raise

This ensures you always get a prediction unless all fallbacks fail.

Partial Degradation
^^^^^^^^^^^^^^^^^^^

Sometimes only specific features are missing. You can degrade to a simpler feature set:

.. code-block:: python

   def predict_with_available_features(data, model_full, model_minimal):
       """Use full model if all features available, minimal model otherwise."""
       
       required_features = ["temperature", "wind_speed", "radiation"]
       available = set(data.feature_names)
       
       if all(f in available for f in required_features):
           # All features available - use full model
           return model_full.predict(data)
       else:
           # Missing features - use minimal model (lag features only)
           return model_minimal.predict(data)

This approach maintains better accuracy when possible while ensuring reliability.

Lessons from Production Systems
--------------------------------

Real-world deployments have revealed several critical patterns:

**Always log fallback events.** When a fallback triggers, you need to know. This helps identify systemic issues before they cascade.

**Test your fallbacks regularly.** Don't wait for production failures to discover your fallback model is misconfigured. Include fallback scenarios in your testing.

**Monitor fallback frequency.** If fallbacks trigger often, your primary model is unreliable. High fallback rates indicate architectural problems.

**Keep fallbacks simple.** Fallback models should have minimal dependencies. The base case model works well because it only needs historical load data—no weather forecasts, no external APIs.

**Set conservative thresholds.** It's better to fall back unnecessarily than to serve bad predictions. Start with strict validation and relax as you gain confidence.

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding forecast horizons and lead times
- :doc:`quantiles_and_confidence` - Interpreting uncertainty in fallback scenarios
- :doc:`model_selection` - Choosing appropriate fallback models