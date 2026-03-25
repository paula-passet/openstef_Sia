Key Forecasting Concepts
========================

Understanding how to interpret and work with OpenSTEF forecasts is essential for making informed decisions in energy management. This page explains the core concepts behind the library's design through practical examples, helping you understand not just what the forecasts mean, but why they work the way they do.

Understanding Forecast Results
------------------------------

OpenSTEF produces probabilistic forecasts rather than single-point predictions. Each forecast includes multiple components that tell different parts of the story:

.. code-block:: python

   import pandas as pd
   from openstef.pipeline import create_forecast
   
   # Generate a forecast with uncertainty bands
   forecast = create_forecast(
       prediction_job=pj,
       input_data=data,
       model=trained_model
   )
   
   # Examine the forecast structure
   print(forecast.columns)
   # ['forecast', 'stdev', 'quantile_0.1', 'quantile_0.9', 'quality']

The ``forecast`` column contains the most likely prediction, while the quantile columns show the range of possible outcomes. For instance, ``quantile_0.1`` means there's a 10% chance the actual load will be below this value, while ``quantile_0.9`` indicates a 90% probability threshold.

The ``quality`` column is crucial for operational reliability - it indicates whether the forecast comes from the trained model (``good``) or a fallback strategy (``substituted``). This transparency allows you to make risk-adjusted decisions based on forecast confidence.

Quantiles and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF generates confidence intervals using two complementary approaches. For standard models, it uses the ``stdev`` column with normal distribution assumptions:

.. code-block:: python

   # Standard confidence interval (±1 standard deviation ≈ 68% confidence)
   upper_bound = forecast['forecast'] + forecast['stdev']
   lower_bound = forecast['forecast'] - forecast['stdev']

For quantile models like XGBQuantile, the library provides more precise uncertainty estimates through dedicated quantile regression:

.. code-block:: python

   from openstef.enums import ModelType
   
   # Train a quantile model for better uncertainty estimation
   quantile_model = train_model(
       prediction_job=pj.with_model_type(ModelType.XGB_QUANTILE),
       input_data=training_data
   )

Quantile models learn the actual distribution of forecast errors during training, making them particularly valuable for peak load scenarios where normal distribution assumptions break down.

Model Selection for Different Use Cases
----------------------------------------

Choosing the right model depends on your specific forecasting challenge and data characteristics. OpenSTEF provides several model types, each optimized for different scenarios.

For most energy forecasting applications, **XGBoost** (``ModelType.XGB``) offers the best balance of accuracy and interpretability. It handles non-linear relationships well and automatically captures interactions between weather variables and load patterns:

.. code-block:: python

   from openstef.enums import ModelType
   
   # XGBoost for general energy forecasting
   pj_xgb = prediction_job.with_model_type(ModelType.XGB)
   
   # Linear models for simple, interpretable forecasts
   pj_linear = prediction_job.with_model_type(ModelType.LINEAR)
   
   # Quantile models when uncertainty estimation is critical
   pj_quantile = prediction_job.with_model_type(ModelType.XGB_QUANTILE)

**Linear models** (``ModelType.LINEAR``) work well when you need maximum interpretability or have limited training data. They're particularly effective for industrial loads with predictable patterns and minimal weather dependency.

**Quantile models** become essential when you need precise risk assessment. For congestion management, knowing the 95th percentile of possible load is often more valuable than the expected value, as it helps prevent equipment overload.

**ARIMA models** (``ModelType.ARIMA``) excel with highly seasonal data that has clear time-series patterns but limited external predictors. They're useful for baseline forecasts or when weather data is unreliable.

Important Predictors and Weather Dependency
--------------------------------------------

OpenSTEF automatically generates hundreds of features, but understanding which ones matter most helps you interpret model behavior and diagnose issues.

Weather features dominate most energy forecasts. Temperature drives heating and cooling loads, while solar radiation and wind speed directly impact renewable generation:

.. code-block:: python

   # Weather features are automatically generated
   from openstef.feature_engineering.weather_features import (
       add_humidity_features,
       calculate_gti,
       calculate_windturbine_power_output
   )
   
   # These create features like:
   # - temperature_2m (direct heating/cooling impact)
   # - gti_surface_0 (solar generation potential)
   # - windspeed_100m (wind generation)
   # - humidity_relative (affects cooling efficiency)

Lag features capture load persistence - yesterday's consumption strongly predicts today's. OpenSTEF generates both trivial lags (same hour yesterday) and non-trivial lags (peak hours, similar weather conditions):

.. code-block:: python

   # Lag features capture temporal patterns
   # - load_lag_24h (same time yesterday)
   # - load_lag_168h (same time last week)  
   # - load_lag_8760h (same time last year)

Calendar features encode human behavior patterns that don't follow weather:

.. code-block:: python

   # Calendar features capture social patterns
   # - hour_of_day (daily cycles)
   # - day_of_week (weekday/weekend differences)
   # - month_of_year (seasonal patterns)
   # - is_holiday (special day behavior)

The relative importance of these feature groups varies by use case. Residential areas show strong temperature sensitivity, while industrial loads depend more on calendar patterns. Solar forecasts rely heavily on weather features, while district heating combines temperature with lag features.

Fallback Strategies for Reliability
------------------------------------

Energy systems require forecasts even when models fail or data is missing. OpenSTEF implements fallback strategies to ensure operational continuity while clearly marking when substitutions occur.

The primary fallback strategy uses extreme day profiles:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast using historical extreme day
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Fallback forecasts are clearly marked
   assert (fallback_forecast['quality'] == 'substituted').all()

This strategy identifies the day in recent history with the most extreme load pattern and uses its profile as a conservative forecast. It's particularly effective for congestion management, where overestimating peak load is safer than underestimating it.

.. note::
   Fallback forecasts always include the ``quality`` column set to ``'substituted'``, allowing downstream systems to apply appropriate risk adjustments or alert operators to reduced forecast confidence.

The fallback system activates automatically when:

- Insufficient training data is available
- Weather data is missing or corrupted  
- Model training fails due to data quality issues
- Real-time input data is incomplete

For critical applications, you can configure multiple fallback layers:

.. code-block:: python

   try:
       # Primary forecast attempt
       forecast = create_forecast(pj, input_data, model)
   except InputDataInsufficientError:
       # First fallback: use extreme day profile
       forecast = generate_fallback(
           forecast_input, 
           historical_load, 
           FallbackStrategy.EXTREME_DAY
       )
   except Exception:
       # Final fallback: raise error for manual intervention
       forecast = generate_fallback(
           forecast_input,
           historical_load, 
           FallbackStrategy.RAISE_ERROR
       )

This layered approach ensures system reliability while maintaining transparency about forecast quality, enabling operators to make informed decisions even under adverse conditions.