Reliability and Fallback Strategies
====================================

When forecasting models run in production, failures happen. Data feeds go offline, models produce invalid predictions, or input features contain unexpected values. A robust forecasting system needs strategies to handle these situations gracefully rather than crashing or returning no forecast at all.

This page covers practical approaches to building reliable forecasting systems: fallback strategies when primary models fail, handling missing or incomplete data, detecting model staleness, and implementing graceful degradation. These patterns come from lessons learned running OpenSTEF in production energy systems where forecast availability is critical.

Why Reliability Matters
-----------------------

In production energy forecasting, a missing or invalid forecast can have real consequences. Grid operators need predictions to make decisions about energy dispatch, trading, and balancing. A system that crashes when data is incomplete is worse than one that provides a simple but reliable fallback forecast.

The goal is not perfection—it's resilience. Your system should degrade gracefully, providing the best forecast possible given the available data and model state.

Fallback Forecasting Strategies
--------------------------------

The most fundamental reliability pattern is the fallback chain: when your primary model fails, fall back to progressively simpler models that are more likely to succeed.

OpenSTEF includes the ``BaseCaseForecaster`` as a robust fallback option. This model implements a simple persistence strategy: it repeats the pattern from the previous week, assuming that energy load exhibits weekly periodicity. Because it only requires historical target data (no weather features or complex preprocessing), it's highly reliable even when other data sources fail.

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecaster
   from openstef_core.types import Quantile, LeadTime
   from datetime import timedelta

   # Create a simple fallback forecaster
   fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=h)) for h in range(1, 48)],
   )

   # Fit only requires historical target data
   fallback.fit(training_data)
   
   # Will succeed even if weather features are missing
   fallback_forecast = fallback.predict(forecast_data)

The ``BaseCaseForecaster`` has built-in fallback logic within itself: it tries to use data from 7 days ago (``primary_lag``), but if that's unavailable, it falls back to 14 days ago (``fallback_lag``). You can configure these lags based on your data availability patterns:

.. code-block:: python

   from openstef_models.models.forecasting import BaseCaseForecasterHyperParams

   # Custom fallback configuration
   custom_fallback = BaseCaseForecaster(
       quantiles=[Quantile(0.5)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=BaseCaseForecasterHyperParams(
           primary_lag=timedelta(days=7),
           fallback_lag=timedelta(days=21),  # Try 3 weeks ago if 1 week fails
       ),
   )

A complete fallback strategy might look like this:

.. code-block:: python

   def get_forecast_with_fallback(data, primary_model, fallback_model):
       """Try primary model, fall back to base case if it fails."""
       try:
           # Attempt primary forecast
           forecast = primary_model.predict(data)
           
           # Check for invalid predictions
           if forecast.data.isna().any().any():
               raise ValueError("Primary model returned NaN predictions")
               
           return forecast, "primary"
           
       except Exception as e:
           # Log the failure for investigation
           print(f"Primary model failed: {e}, using fallback")
           
           # Use simpler fallback model
           forecast = fallback_model.predict(data)
           return forecast, "fallback"

This pattern ensures you always return a forecast, even if it's from a simpler model.

Handling Missing and Incomplete Data
-------------------------------------

Missing data is inevitable in production systems. Weather APIs go down, sensors fail, or data pipelines experience delays. OpenSTEF provides validation transforms to detect data quality issues before they cause model failures.

The ``CompletenessChecker`` validates that your dataset has sufficient data coverage:

.. code-block:: python

   from openstef_models.transforms.validation import CompletenessChecker
   
   # Add completeness validation to your pipeline
   completeness_check = CompletenessChecker()
   
   # This will raise an error if data is too incomplete
   validated_data = completeness_check.transform(input_data)

The ``FlatlineChecker`` detects when your target variable stops changing—often a sign of sensor failure or data pipeline issues:

.. code-block:: python

   from openstef_models.transforms.validation import FlatlineChecker
   
   # Detect flatline issues in load data
   flatline_check = FlatlineChecker(
       load_column="load",
       flatliner_threshold=0.95,  # Flag if 95%+ of values are identical
       detect_non_zero_flatliner=True,  # Detect flatlines at non-zero values
       error_on_flatliner=False,  # Warn but don't crash
   )

When validation detects issues, you have several options:

1. **Reject and use fallback**: If data quality is too poor, skip the primary model entirely and use a fallback that doesn't depend on the problematic features.

2. **Proceed with warnings**: For minor issues, log warnings but continue with the primary model. The model may handle missing features gracefully.

3. **Impute missing values**: Fill gaps using forward fill, interpolation, or historical averages. Be cautious—bad imputation can be worse than missing data.

For models that use lag features, missing historical data creates NaN values in the first N rows. Configure your pipeline to account for this:

.. code-block:: python

   from datetime import timedelta
   
   # If using 14-day lag features, first 14 days will have NaN
   config = {
       "predict_history": timedelta(days=14),
       # ... other config
   }

The ``InputConsistencyChecker`` validates that your input data structure matches what the model expects, catching schema mismatches before they cause cryptic errors.

Model Staleness Detection
--------------------------

Models degrade over time as patterns in the data change. A model trained six months ago may no longer capture current behavior. Detecting staleness helps you know when to retrain.

OpenSTEF's workflow configuration includes model age limits and performance monitoring:

.. code-block:: python

   from openstef_beam.workflows import EnsembleForecastingWorkflowConfig
   from openstef_core.types import Q
   from datetime import timedelta
   
   config = EnsembleForecastingWorkflowConfig(
       # Reject models older than 30 days
       model_max_age=timedelta(days=30),
       
       # Monitor R² at median quantile
       model_selection_metric=(Q(0.5), "R2", "higher_is_better"),
       
       # Bias toward newer models: old model needs 20% better metric to win
       model_selection_old_model_penalty=1.2,
   )

The ``model_selection_old_model_penalty`` is particularly useful: it creates a bias toward newer models even if the old model performs slightly better. This prevents your system from getting stuck with an outdated model that happens to perform well on recent validation data but may be overfitting to old patterns.

You can also implement custom staleness checks based on prediction quality:

.. code-block:: python

   def check_model_staleness(model, recent_predictions, recent_actuals):
       """Check if model performance has degraded significantly."""
       from sklearn.metrics import mean_absolute_error
       
       # Calculate recent error
       recent_mae = mean_absolute_error(recent_actuals, recent_predictions)
       
       # Compare to model's training performance
       if hasattr(model, 'training_mae'):
           if recent_mae > model.training_mae * 1.5:  # 50% worse
               return True, f"MAE degraded: {recent_mae:.2f} vs {model.training_mae:.2f}"
       
       return False, "Model performance acceptable"

Graceful Degradation Patterns
------------------------------

When things go wrong, degrade gracefully rather than failing completely. Here are practical patterns:

**1. Reduce forecast horizon**: If your model struggles with long-term predictions, provide shorter-term forecasts that are more reliable:

.. code-block:: python

   def get_forecast_with_horizon_fallback(model, data, max_horizon_hours=47):
       """Try full horizon, fall back to shorter horizon if needed."""
       try:
           return model.predict(data)
       except Exception:
           # Reduce to 24-hour horizon
           shorter_horizons = [h for h in model.horizons 
                              if h.value.total_seconds() / 3600 <= 24]
           model_short = type(model)(
               quantiles=model.quantiles,
               horizons=shorter_horizons,
           )
           model_short.fit(training_data)
           return model_short.predict(data)

**2. Reduce quantile coverage**: If full probabilistic forecasts fail, provide just the median:

.. code-block:: python

   def get_forecast_with_quantile_fallback(model, data):
       """Try full quantile forecast, fall back to median only."""
       try:
           return model.predict(data)
       except Exception:
           # Provide only median forecast
           median_model = type(model)(
               quantiles=[Quantile(0.5)],
               horizons=model.horizons,
           )
           median_model.fit(training_data)
           return median_model.predict(data)

**3. Feature degradation**: If weather forecasts are unavailable, use historical weather or remove weather features entirely:

.. code-block:: python

   def prepare_features_with_fallback(data):
       """Use best available features."""
       if has_weather_forecast(data):
           return data  # Use all features
       elif has_historical_weather(data):
           # Use historical weather as proxy
           return data.with_historical_weather()
       else:
           # Remove weather features, use only temporal features
           return data.drop_weather_features()

Monitoring and Alerting
------------------------

Reliability requires visibility. Track these metrics in production:

- **Fallback usage rate**: How often are you using fallback models? A sudden increase indicates problems with your primary model or data pipeline.

- **Prediction latency**: Slow predictions may indicate model complexity issues or infrastructure problems.

- **NaN prediction rate**: Models returning NaN predictions signal data quality or model issues.

- **Model age**: Track how long since the active model was trained. Set alerts for models approaching your maximum age threshold.

- **Data completeness**: Monitor what percentage of expected features are present in each prediction request.

.. code-block:: python

   def log_forecast_metrics(forecast, model_type, execution_time):
       """Log key reliability metrics."""
       metrics = {
           "model_type": model_type,  # "primary" or "fallback"
           "execution_time_ms": execution_time * 1000,
           "nan_predictions": forecast.data.isna().sum().sum(),
           "forecast_horizon_hours": len(forecast.horizons),
           "quantiles_provided": len(forecast.quantiles),
       }
       # Send to your monitoring system
       return metrics

Testing Reliability
--------------------

Test your fallback strategies before production:

.. code-block:: python

   def test_fallback_chain():
       """Verify fallback works when primary model fails."""
       # Simulate missing weather data
       incomplete_data = test_data.drop(columns=["temperature", "windspeed"])
       
       # Should fall back gracefully
       forecast, model_used = get_forecast_with_fallback(
           incomplete_data, primary_model, fallback_model
       )
       
       assert model_used == "fallback"
       assert not forecast.data.isna().any().any()
       assert len(forecast.data) > 0

Test with realistic failure scenarios: missing features, corrupted data, extreme values, and stale models.

Next Steps
----------

This page covered reliability and fallback strategies. For related topics:

- :doc:`forecasting_basics` - Understanding what you're forecasting and why
- :doc:`model_selection` - Choosing the right primary model for your use case
- :doc:`feature_engineering` - Building robust features that handle missing data well

Reliability is not optional in production forecasting systems. Build fallback strategies from the start, not as an afterthought.