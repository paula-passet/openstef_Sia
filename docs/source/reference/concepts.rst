Key Forecasting Concepts
========================

Understanding how to interpret and work with OpenSTEF forecasts is essential for building reliable energy forecasting systems. This page explains the core concepts through practical examples, helping you understand not just what the library does, but why it works the way it does.

Understanding Forecast Results
------------------------------

OpenSTEF forecasts come with multiple components that provide different insights into prediction uncertainty and reliability. A typical forecast DataFrame contains several key columns:

.. code-block:: python

   import pandas as pd
   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType
   
   # After training and predicting (see quickstart for full example)
   forecast = model.predict(forecast_input)
   print(forecast.columns)
   # Output: ['forecast', 'stdev', 'quantile_0.1', 'quantile_0.9', 'quality']

The ``forecast`` column contains your point prediction - the most likely value. The ``stdev`` column provides a measure of prediction uncertainty based on patterns learned during training. Quantile columns (like ``quantile_0.1`` and ``quantile_0.9``) define prediction intervals, while ``quality`` indicates whether the forecast is based on the trained model or a fallback strategy.

Quantiles and Confidence Intervals
-----------------------------------

OpenSTEF provides two approaches for quantifying forecast uncertainty, each suited to different needs and model types.

**Standard Deviation Approach**

For most model types, uncertainty is captured through a standard deviation that assumes normally distributed errors:

.. code-block:: python

   # 68% of actual values should fall within ±1 standard deviation
   lower_bound = forecast['forecast'] - forecast['stdev']
   upper_bound = forecast['forecast'] + forecast['stdev']
   
   # 95% confidence interval (approximately ±2 standard deviations)
   lower_95 = forecast['forecast'] - 2 * forecast['stdev']
   upper_95 = forecast['forecast'] + 2 * forecast['stdev']

**Quantile Regression Approach**

For quantile models (like ``XGB_QUANTILE``), OpenSTEF learns the actual distribution of errors and provides more accurate prediction intervals:

.. code-block:: python

   # Direct quantile predictions - no distributional assumptions needed
   p10_forecast = forecast['quantile_0.1']  # 10th percentile
   p90_forecast = forecast['quantile_0.9']  # 90th percentile
   
   # 80% of actual values should fall between these bounds
   prediction_interval_80 = (p10_forecast, p90_forecast)

Quantile regression is particularly valuable for energy forecasting because forecast errors often have asymmetric distributions - the uncertainty isn't the same above and below the point forecast.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF offers several model types, each optimized for specific forecasting scenarios. Understanding when to use each type helps achieve better performance.

**XGBoost Models for Complex Patterns**

XGBoost excels at capturing non-linear relationships and interactions between weather variables and energy consumption:

.. code-block:: python

   from openstef.enums import ModelType
   
   # For complex demand patterns with strong weather dependency
   model_creator = ModelCreator()
   xgb_model = model_creator.create_model(ModelType.XGB)
   
   # For uncertainty quantification in critical applications
   quantile_model = model_creator.create_model(ModelType.XGB_QUANTILE)

**Linear Models for Interpretability**

Linear models provide clear insights into how each predictor affects the forecast:

.. code-block:: python

   # When you need to understand and explain predictions
   linear_model = model_creator.create_model(ModelType.LINEAR)
   
   # View feature coefficients after training
   coefficients = linear_model.feature_importances_
   # Positive coefficients increase the forecast, negative decrease it

**Specialized Models for Renewable Energy**

Solar and wind forecasting benefit from domain-specific approaches:

.. code-block:: python

   # Solar forecasting often uses polynomial relationships
   # between irradiance and PV output
   from openstef.tasks.create_solar_forecast import apply_fit_insol
   
   # Wind forecasting incorporates turbine power curves
   from openstef.feature_engineering.weather_features import calc_wind_power_curve

Weather Dependency and Key Predictors
--------------------------------------

Energy forecasting success heavily depends on understanding how weather variables influence energy consumption and generation. OpenSTEF automatically engineers weather features that capture these relationships.

**Temperature Effects**

Temperature is often the strongest predictor for demand forecasting, but its effect varies by season and time of day:

.. code-block:: python

   # OpenSTEF automatically creates temperature-based features
   # including heating/cooling degree days and temperature lags
   from openstef.feature_engineering.weather_features import add_humidity_features
   
   # Humidity affects both comfort and equipment efficiency
   data_with_humidity = add_humidity_features(weather_data, 
                                            feature_names=['dewpoint', 'air_density'])

**Solar Radiation**

For solar forecasting and demand splitting, solar radiation features are critical:

.. code-block:: python

   from openstef.feature_engineering.weather_features import add_solar_features
   
   # Adds features like solar elevation angle, clear sky index
   solar_enhanced_data = add_solar_features(data, pj, 
                                          feature_names=['solar_elevation', 'clear_sky_index'])

**Wind Patterns**

Wind affects both renewable generation and heating/cooling demand:

.. code-block:: python

   from openstef.feature_engineering.weather_features import add_additional_wind_features
   
   # Creates wind chill, gust factors, and directional components
   wind_enhanced_data = add_additional_wind_features(data, 
                                                   feature_names=['wind_chill', 'wind_power'])

The library's feature engineering captures complex interactions - for example, how temperature effects change with wind speed, or how solar generation depends on both irradiance and temperature.

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems must handle situations where normal prediction fails - missing data, model errors, or unusual conditions. OpenSTEF provides fallback strategies to maintain service reliability.

**Extreme Day Fallback**

When insufficient recent data is available, the system can fall back to historical patterns from similar extreme conditions:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast using historical extreme day pattern
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Check forecast quality
   print(fallback_forecast['quality'].unique())
   # Output: ['substituted'] - indicates fallback was used

**Quality Indicators**

Every forecast includes quality metadata that helps downstream systems make appropriate decisions:

.. code-block:: python

   # Normal forecasts have quality='good'
   # Fallback forecasts have quality='substituted'
   
   # Use quality information for decision making
   reliable_forecasts = forecast[forecast['quality'] == 'good']
   fallback_forecasts = forecast[forecast['quality'] == 'substituted']
   
   # Apply different confidence intervals or alerts based on quality
   if len(fallback_forecasts) > 0:
       print(f"Warning: {len(fallback_forecasts)} forecasts using fallback strategy")

**Handling Data Gaps**

The fallback system automatically activates when data quality issues are detected:

- Missing weather data beyond acceptable thresholds
- Sensor failures or communication outages  
- Unusual patterns that suggest data corruption

This ensures your forecasting system continues operating even when input data is compromised, though with appropriately flagged uncertainty.

.. note::
   
   For production deployments, monitor the frequency of fallback usage. High fallback rates may indicate data quality issues that need addressing. See the how-to guides for deployment monitoring strategies.