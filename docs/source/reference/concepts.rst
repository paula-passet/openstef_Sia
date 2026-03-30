Key Forecasting Concepts
========================

This page explains the core concepts behind OpenSTEF's forecasting approach through practical examples. Understanding these concepts helps you interpret forecast results, choose appropriate models, and build reliable forecasting systems.

Understanding Forecast Uncertainty
----------------------------------

Energy forecasts are never perfectly accurate. OpenSTEF provides multiple ways to quantify and communicate this uncertainty, helping you make informed decisions based on forecast confidence.

Standard Deviation and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every OpenSTEF forecast includes a ``stdev`` column representing the standard deviation of the prediction error. This value is learned during model training by analyzing historical forecast errors.

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Train a model (learns error patterns)
   model, report = train_model_pipeline(pj, input_data)
   
   # Create forecast with uncertainty
   forecast = create_forecast_pipeline(pj, model, forecast_input)
   
   # Forecast contains: 'forecast', 'stdev', and quantile columns
   print(forecast[['forecast', 'stdev', 'quantile_P05', 'quantile_P95']])

The standard deviation tells you the typical magnitude of forecast errors. For example, if your forecast is 10 MW with a standard deviation of 1 MW, you can expect the actual value to fall within ±1 MW about 68% of the time (assuming normally distributed errors).

Quantile Forecasts
^^^^^^^^^^^^^^^^^^^

Quantiles provide a more detailed view of uncertainty. OpenSTEF generates quantile forecasts using two methods:

1. **Default method**: Assumes forecast errors are normally distributed and derives quantiles from the ``stdev`` column. This works for all model types.

2. **Quantile regression**: Trains separate models for each quantile (P05, P10, P25, P50, P75, P90, P95). This method is available for XGBoost models and captures non-symmetric uncertainty.

.. code-block:: python

   # Quantile columns in forecast
   # P05: 5% chance actual value is below this
   # P50: median forecast (50% chance above/below)
   # P95: 95% chance actual value is below this
   
   # Use quantiles for risk-based decisions
   if forecast['quantile_P95'].max() > grid_capacity:
       print("High risk of congestion - consider preventive action")
   elif forecast['quantile_P75'].max() > grid_capacity:
       print("Moderate risk - monitor closely")

Quantile regression is particularly valuable when forecast uncertainty varies with conditions. For example, solar forecasts may be more uncertain during partly cloudy conditions than during clear or fully overcast weather.

Choosing the Right Model
-------------------------

OpenSTEF supports multiple model types, each suited to different forecasting scenarios. The library defaults to XGBoost for most use cases, but understanding the alternatives helps you optimize for specific situations.

XGBoost: The Workhorse
^^^^^^^^^^^^^^^^^^^^^^^

XGBoost (gradient boosted trees) is OpenSTEF's default model for good reason:

- Handles complex non-linear relationships between weather and load
- Provides feature importance for interpretability
- Supports quantile regression for detailed uncertainty estimates
- Performs well with limited training data (months rather than years)
- Fast training and prediction

Use XGBoost when you have weather-dependent load patterns and want accurate, interpretable forecasts. This covers most energy forecasting use cases.

.. code-block:: python

   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   
   # XGBoost is the default - no special configuration needed
   model, report = train_model_pipeline(pj, input_data)
   
   # Access feature importance to understand drivers
   importance = model.feature_importances_
   print(importance.head(10))  # Top 10 most important features

Linear Models: When Simplicity Matters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models (LinearOpenstfRegressor) work well when relationships are approximately linear and you need maximum interpretability. They're faster to train than XGBoost but less flexible.

Consider linear models for:

- Load patterns with simple weather dependencies
- Situations requiring regulatory transparency
- Extremely fast training requirements
- Baseline comparisons to assess XGBoost value

ARIMA: Capturing Temporal Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ARIMA models excel at capturing temporal patterns when weather data is unavailable or load is weather-independent. They're useful for:

- Indoor loads with minimal weather sensitivity
- Short-term forecasts (next few hours) where recent trends dominate
- Fallback when weather forecasts are unavailable

Flatliner: The Simplest Baseline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Flatliner model simply repeats the most recent observed value. It serves as a sanity check - if your sophisticated model doesn't beat Flatliner, something is wrong with your data or configuration.

Important Predictors and Weather Dependency
--------------------------------------------

Understanding which features drive your forecasts helps you assess forecast reliability and identify data quality issues.

Weather Features
^^^^^^^^^^^^^^^^

OpenSTEF automatically engineers weather features from basic inputs:

- **Temperature**: Often the strongest predictor for heating/cooling loads
- **Wind speed**: Critical for wind generation forecasts, relevant for outdoor temperature effects
- **Solar radiation**: Drives solar generation and cooling loads
- **Humidity-derived features**: Saturation pressure, vapor pressure, dewpoint, air density

The library calculates advanced features like wind speed at hub height for wind turbines and direct normal irradiance (DNI) for solar panels.

.. code-block:: python

   from openstef.feature_engineering.weather_features import (
       add_humidity_features,
       calculate_windspeed_at_hubheight,
       calculate_dni
   )
   
   # These are applied automatically during training
   # but you can use them directly for custom workflows
   data_with_humidity = add_humidity_features(data)
   
   # Wind speed at turbine hub height (default 100m from 10m measurement)
   data['windspeed_100m'] = calculate_windspeed_at_hubheight(
       data['windspeed'], 
       fromheight=10.0, 
       hub_height=100.0
   )

Temporal Features
^^^^^^^^^^^^^^^^^

Time-based features capture daily, weekly, and seasonal patterns:

- Hour of day and day of week (capturing routine behavior)
- Month and season (capturing seasonal effects)
- Holiday indicators (capturing exceptional days)
- Lagged load values (capturing short-term persistence)

These features are particularly important for loads with strong human behavioral components - commercial buildings, residential areas, industrial facilities with shift patterns.

Assessing Weather Dependency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Feature importance reveals how weather-dependent your load is. High importance for temperature or radiation indicates strong weather dependency, while high importance for temporal features suggests behavioral patterns dominate.

.. code-block:: python

   # After training, examine feature importance
   importance = model.feature_importances_
   
   weather_features = ['temp', 'windspeed', 'radiation', 'humidity']
   temporal_features = ['hour', 'dayofweek', 'month']
   
   weather_importance = importance[
       importance.index.str.contains('|'.join(weather_features))
   ].sum()
   temporal_importance = importance[
       importance.index.str.contains('|'.join(temporal_features))
   ].sum()
   
   print(f"Weather dependency: {weather_importance:.1%}")
   print(f"Temporal patterns: {temporal_importance:.1%}")

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems need fallback strategies for when normal forecasting fails - missing data, model errors, or exceptional conditions.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^

OpenSTEF's default fallback strategy uses the historical profile from the most extreme day in your training data. This provides a conservative estimate when current forecasting fails.

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   try:
       forecast = create_forecast_pipeline(pj, model, forecast_input)
   except Exception as e:
       # Generate fallback forecast using extreme day profile
       forecast = generate_fallback(
           forecast_input,
           load_history,
           fallback_strategy=FallbackStrategy.EXTREME_DAY
       )
       # Forecast quality column is set to 'substituted'
       print(f"Using fallback forecast: {forecast['quality'].unique()}")

The extreme day strategy is particularly useful for capacity planning and congestion management, where conservative estimates reduce risk.

When to Use Fallback
^^^^^^^^^^^^^^^^^^^^

Implement fallback strategies when:

- Weather forecast data is unavailable or delayed
- Model prediction fails due to data quality issues
- Input features are outside the training data range
- System errors prevent normal forecast generation

Always mark fallback forecasts clearly (via the ``quality`` column) so downstream systems can adjust their confidence and decision-making accordingly.

.. code-block:: python

   # Check forecast quality before using
   if (forecast['quality'] == 'substituted').any():
       print("Warning: Forecast contains fallback values")
       # Increase safety margins, alert operators, etc.

Interpreting Forecast Results
------------------------------

Understanding what your forecasts mean in practical terms helps you use them effectively for decision-making.

Forecast Quality Indicators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond the ``quality`` column (which flags substituted/fallback values), assess forecast quality through:

- **Validation metrics**: RMSE, MAE, and skill score from training reports
- **Quantile coverage**: Do actual values fall within predicted quantiles at the expected rates?
- **Feature importance stability**: Do important features remain consistent across retraining?

.. code-block:: python

   # Training report contains validation metrics
   model, report = train_model_pipeline(pj, input_data)
   
   print(f"RMSE: {report['rmse']:.2f} MW")
   print(f"MAE: {report['mae']:.2f} MW")
   print(f"Skill score: {report['skill_score']:.2%}")
   
   # Skill score > 0 means better than persistence forecast
   # Skill score > 0.3 is generally considered good

Forecast Horizon Effects
^^^^^^^^^^^^^^^^^^^^^^^^^

Forecast accuracy typically decreases with forecast horizon. Short-term forecasts (next few hours) benefit from recent observations and persistence, while longer horizons (24-48 hours ahead) depend more on weather forecast accuracy.

Consider this when using forecasts:

- Use high-confidence short-term forecasts for real-time operations
- Use longer-horizon forecasts with wider uncertainty margins for planning
- Update forecasts regularly as new observations and weather forecasts become available

Seasonal and Situational Variation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forecast accuracy varies with conditions:

- Higher uncertainty during weather transitions (fronts, storms)
- Better accuracy during stable weather patterns
- Seasonal variations in weather predictability affect forecast quality
- Special events (holidays, major sports events) may reduce accuracy

Monitor these patterns in your specific use case to understand when forecasts are most and least reliable. This knowledge helps you adjust operational decisions appropriately.

.. note::
   For detailed examples of applying these concepts, see :doc:`../getting_started/tutorials`. For specific use cases showing how concepts apply in practice, see :doc:`../guides/use_cases`.