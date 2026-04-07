Reliability and Fallback Strategies
====================================

Production forecasting systems must handle failures gracefully. Models can fail to train, input data can be incomplete or corrupted, and predictions can become stale. This page covers strategies for building resilient forecasting systems that degrade gracefully rather than fail catastrophically.

Why Reliability Matters
-----------------------

Energy forecasting systems often operate in critical infrastructure where forecast failures can lead to:

- Suboptimal energy trading decisions
- Grid imbalance penalties
- Loss of confidence in automated systems
- Manual intervention overhead

A robust production system needs multiple layers of defense: fallback models, data quality checks, staleness detection, and graceful degradation strategies.

Fallback Model Strategies
--------------------------

The most fundamental reliability pattern is having a fallback model when your primary model fails or produces unreliable predictions.

Using BaseCaseForecaster as a Fallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``BaseCaseForecaster`` is designed specifically as a reliable baseline. It repeats weekly patterns from historical data, making it nearly impossible to fail as long as you have recent historical observations:

.. code-block:: python

   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta
   
   # Configure a fallback forecaster
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),    # Use last week's pattern
           fallback_lag=timedelta(days=14)   # Fall back to 2 weeks ago if needed
       )
   )

The ``BaseCaseForecaster`` has built-in fallback logic: if data from 7 days ago is missing, it automatically uses data from 14 days ago. This two-tier approach handles common data gaps.

Implementing a Fallback Chain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In production, you typically want a chain of models with decreasing sophistication but increasing reliability:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow
   )
   from openstef_core.exceptions import NotFittedError
   
   def predict_with_fallback(dataset, primary_workflow, fallback_workflow):
       """Predict using primary model, falling back if it fails."""
       try:
           # Try primary model (e.g., XGBoost)
           forecasts = primary_workflow.predict(dataset)
           
           # Validate predictions contain expected quantiles
           required_quantiles = [q.format() for q in primary_workflow.quantiles]
           if not all(q in forecasts.feature_names for q in required_quantiles):
               raise ValueError("Primary model missing required quantiles")
           
           return forecasts, "primary"
           
       except (NotFittedError, ValueError, RuntimeError) as e:
           # Log the failure for monitoring
           print(f"Primary model failed: {e}, using fallback")
           
           # Fall back to baseline model
           forecasts = fallback_workflow.predict(dataset)
           return forecasts, "fallback"

This pattern ensures you always produce a forecast, even when the sophisticated model fails.

Loading Models with Storage Fallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When loading models from storage, implement fallback logic to handle missing or corrupted model files:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       CustomForecastingWorkflow
   )
   from openstef_models.models.forecasting_model import ForecastingModel
   
   def load_model_with_fallback(model_id, storage, fallback_forecaster):
       """Load model from storage with fallback to fresh model."""
       try:
           # Try loading from storage
           workflow = CustomForecastingWorkflow.from_storage(
               model_id=model_id,
               storage=storage
           )
           return workflow, "loaded"
           
       except (FileNotFoundError, ValueError) as e:
           # Storage failed, create fresh workflow with fallback model
           print(f"Failed to load model: {e}, using fresh fallback")
           
           workflow = CustomForecastingWorkflow(
               model=ForecastingModel(forecaster=fallback_forecaster),
               model_id=model_id
           )
           return workflow, "fresh_fallback"

Handling Missing and Bad Data
------------------------------

Data quality issues are the most common cause of forecast failures. OpenSTEF provides several mechanisms to detect and handle problematic data.

Completeness Validation
^^^^^^^^^^^^^^^^^^^^^^^^

Use data validators to check completeness before training:

.. code-block:: python

   from openstef_core.datasets.validators import CompletenessValidator
   from openstef_core.exceptions import InsufficientlyCompleteError
   from datetime import timedelta
   
   # Require 90% data completeness
   validator = CompletenessValidator(
       min_completeness=0.9,
       ignore_first=timedelta(days=14)  # Ignore first 14 days (lag features)
   )
   
   try:
       validated_dataset = validator.validate(dataset)
       # Proceed with training
       result = workflow.fit(validated_dataset)
       
   except InsufficientlyCompleteError as e:
       print(f"Data too incomplete: {e}")
       # Skip training, use existing model or fallback
       print("Skipping model update, using previous version")

The ``ignore_first`` parameter is crucial when using lag features, as the first N days naturally contain NaN values from the lag transformation.

Handling Missing Features
^^^^^^^^^^^^^^^^^^^^^^^^^^

When making predictions, check for missing features and handle them appropriately:

.. code-block:: python

   def predict_with_feature_check(workflow, dataset):
       """Predict with graceful handling of missing features."""
       try:
           forecasts = workflow.predict(dataset)
           return forecasts, None
           
       except ValueError as e:
           if "missing the following lag features" in str(e):
               # Extract missing features from error message
               print(f"Missing features: {e}")
               
               # Option 1: Use a simpler model that needs fewer features
               # Option 2: Fill missing features with historical means
               # Option 3: Skip this forecast cycle
               
               return None, "missing_features"
           else:
               raise

For lag-based models like ``MedianForecaster``, missing lag features will cause prediction failures. Design your system to handle these gracefully.

Model Staleness Detection
--------------------------

Models degrade over time as patterns change. Detecting staleness is critical for maintaining forecast quality.

Time-Based Staleness
^^^^^^^^^^^^^^^^^^^^

The simplest approach is time-based: retrain models on a schedule and flag models that haven't been updated recently:

.. code-block:: python

   from datetime import datetime, timedelta
   
   def check_model_staleness(workflow, max_age_days=7):
       """Check if model needs retraining based on age."""
       if not workflow.model.is_fitted:
           return True, "not_fitted"
       
       # Check when model was last trained
       # (This requires storing training timestamp in your system)
       last_trained = workflow.last_training_time  # Your implementation
       age = datetime.now() - last_trained
       
       if age > timedelta(days=max_age_days):
           return True, f"stale_{age.days}_days"
       
       return False, "fresh"
   
   # In your forecasting loop
   is_stale, reason = check_model_staleness(workflow)
   if is_stale:
       print(f"Model is stale ({reason}), triggering retraining")
       result = workflow.fit(training_dataset)

Performance-Based Staleness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

More sophisticated systems monitor forecast accuracy and trigger retraining when performance degrades:

.. code-block:: python

   from openstef_core.metrics.evaluator import Evaluator
   from openstef_core.types import Quantile
   import numpy as np
   
   def check_performance_degradation(
       recent_forecasts,
       recent_actuals,
       baseline_mae,
       threshold_ratio=1.5
   ):
       """Detect if recent forecast quality has degraded."""
       evaluator = Evaluator(quantiles=[Quantile(0.5)])
       
       report = evaluator.evaluate(
           predictions=recent_forecasts,
           ground_truth=recent_actuals,
           target_column="load"
       )
       
       # Get MAE from evaluation report
       current_mae = report.subsets[0].metrics.mae
       
       # Check if performance has degraded significantly
       if current_mae > baseline_mae * threshold_ratio:
           return True, f"mae_degraded_{current_mae:.2f}_vs_{baseline_mae:.2f}"
       
       return False, "performance_ok"

This approach requires storing baseline performance metrics and continuously evaluating recent forecasts against actuals.

Graceful Degradation Patterns
------------------------------

When problems occur, degrade gracefully rather than failing completely.

Reducing Forecast Horizon
^^^^^^^^^^^^^^^^^^^^^^^^^^

If a model struggles with long-term predictions, fall back to shorter horizons:

.. code-block:: python

   def predict_with_horizon_fallback(workflow, dataset, max_horizon_hours=48):
       """Try full horizon, fall back to shorter horizon if needed."""
       try:
           # Try full horizon forecast
           forecasts = workflow.predict(dataset)
           return forecasts
           
       except RuntimeError:
           # Reduce horizon and try again
           reduced_horizons = [
               h for h in workflow.horizons 
               if h.total_seconds() / 3600 <= max_horizon_hours / 2
           ]
           
           # Create temporary workflow with reduced horizons
           reduced_workflow = CustomForecastingWorkflow(
               model=workflow.model,
               model_id=workflow.model_id
           )
           reduced_workflow.horizons = reduced_horizons
           
           return reduced_workflow.predict(dataset)

Reducing Quantile Coverage
^^^^^^^^^^^^^^^^^^^^^^^^^^^

If quantile prediction fails, fall back to point forecasts:

.. code-block:: python

   def predict_with_quantile_fallback(workflow, dataset):
       """Try full quantile forecast, fall back to median only."""
       try:
           return workflow.predict(dataset)
           
       except Exception as e:
           print(f"Full quantile prediction failed: {e}")
           
           # Create workflow with only median quantile
           median_workflow = CustomForecastingWorkflow(
               model=workflow.model,
               model_id=workflow.model_id
           )
           median_workflow.quantiles = [Quantile(0.5)]
           
           return median_workflow.predict(dataset)

Monitoring and Callbacks
-------------------------

Use callbacks to monitor reliability issues in production:

.. code-block:: python

   from openstef_models.workflows.custom_forecasting_workflow import (
       ForecastingCallback
   )
   
   class ReliabilityMonitoringCallback(ForecastingCallback):
       """Monitor and log reliability issues."""
       
       def on_fit_start(self, context, dataset):
           """Check data quality before training."""
           completeness = self._calculate_completeness(dataset)
           if completeness < 0.9:
               print(f"Warning: Low data completeness {completeness:.2%}")
       
       def on_fit_end(self, context, result):
           """Log training success."""
           print(f"Model trained successfully at {datetime.now()}")
       
       def on_predict_start(self, context, dataset):
           """Check model staleness before prediction."""
           # Implement staleness check
           pass
       
       def on_predict_end(self, context, dataset, forecasts):
           """Validate forecast output."""
           if forecasts.data.isna().any().any():
               print("Warning: Forecast contains NaN values")
       
       def _calculate_completeness(self, dataset):
           """Calculate dataset completeness."""
           return dataset.data.notna().mean().mean()
   
   # Use the callback
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="monitored_model",
       callbacks=[ReliabilityMonitoringCallback()]
   )

Production Checklist
--------------------

When deploying forecasting systems, ensure you have:

1. **Fallback models**: At least one reliable baseline model (e.g., ``BaseCaseForecaster``)
2. **Data validation**: Completeness checks before training and prediction
3. **Staleness detection**: Time-based or performance-based triggers for retraining
4. **Error handling**: Try-catch blocks around training and prediction with appropriate fallbacks
5. **Monitoring**: Callbacks or logging to track failures and degradation
6. **Graceful degradation**: Ability to reduce horizons or quantiles when needed
7. **Storage fallbacks**: Handle missing or corrupted model files

See Also
--------

- :doc:`forecasting_basics` - Understanding the forecasting problem
- :doc:`model_selection` - Choosing appropriate models for different scenarios
- :doc:`feature_engineering` - Building robust features that handle missing data