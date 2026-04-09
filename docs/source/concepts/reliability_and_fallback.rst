Reliability and Fallback Strategies
====================================

Production forecasting systems must handle failures gracefully. Models can fail to train, input data may be incomplete or corrupted, and predictions can become stale. This page covers strategies for building reliable forecasting systems that degrade gracefully when things go wrong.

Why Reliability Matters
-----------------------

In production environments, forecasts drive critical decisions: energy trading, grid balancing, and operational planning. A missing or incorrect forecast can have real financial and operational consequences. Rather than failing completely, a robust system should:

- Detect when models or data are problematic
- Fall back to simpler, more reliable alternatives
- Continue producing reasonable forecasts even with degraded inputs
- Alert operators to issues requiring attention

Fallback Forecasting Models
----------------------------

The most fundamental reliability strategy is having a fallback model that always works, even when sophisticated machine learning models fail.

Base Case Forecaster
^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides ``BaseCaseForecaster`` as a production-ready fallback model. It implements a simple but effective strategy: repeat last week's pattern. This naive approach works surprisingly well for energy load forecasting because of strong weekly periodicity.

.. code-block:: python

   from openstef_models.models.forecasting.base_case import (
       BaseCaseForecaster,
       BaseCaseForecasterHyperParams,
   )
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   # Create a fallback forecaster
   fallback_forecaster = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),    # Use last week
           fallback_lag=timedelta(days=14),  # If unavailable, use 2 weeks ago
       ),
   )

   # Fit and predict - works even with minimal data
   fallback_forecaster.fit(training_data)
   fallback_forecast = fallback_forecaster.predict(forecast_input)

The base case forecaster has its own internal fallback: if 7-day lag data is missing, it automatically falls back to 14-day lag data. This two-tier approach ensures predictions even when recent historical data has gaps.

When to Use Fallback Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Consider using a fallback forecaster when:

- **Training fails**: Insufficient data, numerical instability, or optimization failures
- **Prediction fails**: Missing features, corrupted inputs, or runtime errors
- **Model is stale**: No recent retraining and performance has degraded
- **Cold start**: New prediction locations without historical model training

A typical production pattern is to attempt the primary model first, catch exceptions, and fall back to the base case:

.. code-block:: python

   def generate_forecast(data, primary_model, fallback_model):
       """Generate forecast with automatic fallback."""
       try:
           # Attempt primary model
           forecast = primary_model.predict(data)
           
           # Validate forecast quality (discussed below)
           if is_forecast_valid(forecast):
               return forecast, "primary"
       except Exception as e:
           logger.warning(f"Primary model failed: {e}")
       
       # Fall back to base case
       try:
           forecast = fallback_model.predict(data)
           return forecast, "fallback"
       except Exception as e:
           logger.error(f"Fallback model also failed: {e}")
           raise

Handling Missing and Bad Data
------------------------------

Data quality issues are the most common cause of forecasting failures. OpenSTEF provides built-in tools for detecting and handling incomplete data.

Completeness Checking
^^^^^^^^^^^^^^^^^^^^^

The ``CompletenessChecker`` transform validates that datasets have sufficient non-missing values before training or prediction:

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker
   from openstef_core.exceptions import InsufficientlyCompleteError

   # Configure completeness requirements
   completeness_checker = CompletenessChecker(
       columns=["load", "temperature", "windspeed"],
       weights={"load": 2.0, "temperature": 1.0, "windspeed": 1.0},
       min_completeness=0.95,  # Require 95% complete
   )

   # Check data before training
   try:
       validated_data = completeness_checker.transform(training_data)
   except InsufficientlyCompleteError as e:
       logger.error(f"Data too incomplete: {e}")
       # Fall back to using older model or base case

The completeness check is particularly important for training data. Missing target values (load) are more critical than missing features, which is why the example weights load more heavily.

Handling Missing Features
^^^^^^^^^^^^^^^^^^^^^^^^^^

For prediction, missing features are common when external data sources (weather forecasts, calendar data) are unavailable. OpenSTEF's preprocessing pipeline handles this through several mechanisms:

- **Forward fill**: Carry forward last known values for slowly-changing features
- **Lag-based features**: Use historical values when current values are missing
- **Feature importance**: Critical features should trigger fallback, while minor features can be imputed

When preparing input data, the workflow automatically drops rows with missing target values during training:

.. code-block:: python

   # This pattern is built into OpenSTEF workflows
   # Training data: drop rows where target is NaN
   training_data_clean = training_data.dropna(subset=["load"])
   
   if training_data_clean.empty:
       raise InsufficientlyCompleteError(
           "No training data available after dropping NaN targets"
       )

For prediction data, missing features should be handled more gracefully, potentially by falling back to a simpler model that requires fewer inputs.

Model Staleness Detection
--------------------------

Models degrade over time as patterns change. Detecting when a model has become stale is crucial for maintaining forecast quality.

Age-Based Staleness
^^^^^^^^^^^^^^^^^^^

The simplest approach is time-based: retrain models on a regular schedule. OpenSTEF's MLFlow integration includes ``model_reuse_max_age`` to control this:

.. code-block:: python

   from openstef_beam.workflows.callbacks import MLFlowStorageCallback
   from datetime import timedelta

   callback = MLFlowStorageCallback(
       model_reuse_enable=True,
       model_reuse_max_age=timedelta(days=7),  # Retrain weekly
   )

If a stored model is older than the maximum age, the workflow automatically triggers retraining rather than reusing the cached model.

Performance-Based Staleness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

More sophisticated staleness detection compares recent forecast performance against expectations. OpenSTEF's model selection mechanism can detect when a newly trained model significantly outperforms the old one:

.. code-block:: python

   callback = MLFlowStorageCallback(
       model_selection_enable=True,
       model_selection_metric=(Quantile(0.5), "R2", "higher_is_better"),
       model_selection_old_model_penalty=1.2,  # New model must be 20% better
   )

The penalty factor (1.2) biases selection toward newer models: a new model is selected if its R² score is at least old_R² / 1.2. This prevents unnecessary model churn while ensuring models don't become stale.

Monitoring for Staleness
^^^^^^^^^^^^^^^^^^^^^^^^^

In production, monitor these indicators of model staleness:

- **Forecast error trends**: Increasing RMSE or MAE over time
- **Residual patterns**: Systematic over- or under-prediction
- **Feature drift**: Changes in input data distributions
- **External events**: Known changes in the system being forecasted (new equipment, operational changes)

When staleness is detected, trigger retraining or switch to a fallback model until a fresh model is available.

Graceful Degradation Strategies
--------------------------------

A well-designed system degrades gracefully through multiple fallback layers:

**Layer 1: Primary Model**
   Latest trained XGBoost or LightGBM model with full feature set

**Layer 2: Simplified Model**
   Same model type but with reduced features or simpler hyperparameters

**Layer 3: Base Case Model**
   ``BaseCaseForecaster`` using weekly repetition

**Layer 4: Persistence**
   Repeat the most recent known value (last resort)

Each layer has progressively lower requirements and higher reliability. The system attempts each layer in order until one succeeds.

Implementing Multi-Layer Fallback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   def robust_forecast(data, models):
       """Generate forecast with multi-layer fallback."""
       
       # Layer 1: Primary model
       if models["primary"] is not None:
           try:
               forecast = models["primary"].predict(data)
               if validate_forecast(forecast):
                   return forecast, "primary"
           except Exception as e:
               logger.warning(f"Primary model failed: {e}")
       
       # Layer 2: Simplified model (fewer features)
       if models["simplified"] is not None:
           try:
               simplified_data = data[essential_features]
               forecast = models["simplified"].predict(simplified_data)
               if validate_forecast(forecast):
                   return forecast, "simplified"
           except Exception as e:
               logger.warning(f"Simplified model failed: {e}")
       
       # Layer 3: Base case
       try:
           forecast = models["base_case"].predict(data)
           return forecast, "base_case"
       except Exception as e:
           logger.error(f"Base case failed: {e}")
           
           # Layer 4: Persistence (last resort)
           last_value = data["load"].iloc[-1]
           forecast = pd.DataFrame({
               "forecast": [last_value] * 48,
               "quantile_0.5": [last_value] * 48,
           })
           return forecast, "persistence"

Validation and Quality Checks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each forecast should be validated before use:

.. code-block:: python

   def validate_forecast(forecast):
       """Check if forecast is reasonable."""
       
       # Check for NaN or infinite values
       if forecast.isna().any().any() or np.isinf(forecast).any().any():
           return False
       
       # Check for physically impossible values
       if (forecast < 0).any().any():
           return False
       
       # Check for unrealistic magnitude
       if (forecast > expected_max_load * 1.5).any().any():
           return False
       
       # Check quantile ordering
       if "quantile_0.1" in forecast and "quantile_0.9" in forecast:
           if (forecast["quantile_0.1"] > forecast["quantile_0.9"]).any():
               return False
       
       return True

These checks catch common failure modes: numerical errors, bugs that produce negative loads, and quantile crossing issues.

Practical Recommendations
--------------------------

Based on production experience with OpenSTEF:

**Always have a fallback**: Never deploy a system that can fail completely. The ``BaseCaseForecaster`` is simple but reliable.

**Validate inputs and outputs**: Check data completeness before training and forecast validity after prediction. Fail fast and fall back.

**Monitor model age**: Set reasonable ``model_reuse_max_age`` values (typically 7-14 days for energy forecasting). Stale models lose accuracy.

**Log fallback usage**: Track when and why fallbacks are used. High fallback rates indicate systemic issues requiring investigation.

**Test failure modes**: Deliberately inject missing data, corrupted inputs, and training failures in testing to verify fallback behavior.

**Bias toward reliability**: In production, a slightly less accurate forecast delivered reliably is better than a perfect forecast that fails 1% of the time.

The goal is not to prevent all failures—that's impossible—but to ensure the system continues producing reasonable forecasts even when components fail.

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding what you're forecasting helps design better fallback strategies
- :doc:`model_selection` - Choosing appropriate primary and fallback models
- :doc:`feature_engineering` - Understanding feature importance helps determine which missing features should trigger fallback