Key Forecasting Concepts
========================

OpenSTEF is designed around several core forecasting concepts that make energy predictions both accurate and actionable. Understanding these concepts helps you interpret forecast results, choose appropriate models, and build reliable forecasting systems.

Understanding Forecast Uncertainty
----------------------------------

Energy forecasts are never perfectly accurate, so OpenSTEF provides multiple ways to quantify uncertainty. Every forecast includes confidence information to help you make informed decisions.

Standard Deviation Approach
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest uncertainty measure is the standard deviation column, calculated during model training:

.. code-block:: python

   import pandas as pd
   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType
   
   # Train a standard XGBoost model
   model = ModelCreator.create_model(ModelType.XGB)
   model.fit(train_data, target_values)
   
   # Generate forecast with uncertainty
   forecast = model.predict(forecast_input)
   # Result includes 'forecast' and 'stdev' columns

This standard deviation assumes forecast errors follow a normal distribution. For most energy applications, this provides a reasonable approximation of uncertainty.

Quantile Forecasts
^^^^^^^^^^^^^^^^^^^

For more precise uncertainty estimates, OpenSTEF supports quantile regression models that directly predict specific probability levels:

.. code-block:: python

   # Create quantile model for more precise uncertainty
   quantile_model = ModelCreator.create_model(ModelType.XGB_QUANTILE)
   quantile_model.fit(train_data, target_values)
   
   # Predict specific quantiles
   p10_forecast = quantile_model.predict(forecast_input, quantile=0.1)
   p50_forecast = quantile_model.predict(forecast_input, quantile=0.5)  # median
   p90_forecast = quantile_model.predict(forecast_input, quantile=0.9)

Quantile forecasts are particularly valuable for risk management. The P10 forecast tells you there's only a 10% chance the actual load will be below this level, while P90 indicates a 10% chance of exceeding this threshold.

Choosing the Right Model
------------------------

OpenSTEF offers several model types, each suited to different forecasting scenarios. The choice depends on your data characteristics, accuracy requirements, and computational constraints.

XGBoost for General Purpose
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost models work well for most energy forecasting applications:

.. code-block:: python

   from openstef.enums import ModelType
   
   # Standard XGBoost - good balance of accuracy and speed
   standard_model = ModelCreator.create_model(ModelType.XGB)
   
   # Quantile XGBoost - when you need precise uncertainty estimates
   quantile_model = ModelCreator.create_model(ModelType.XGB_QUANTILE)

XGBoost excels when you have rich feature sets including weather data, calendar information, and historical patterns. It handles missing data well and provides feature importance rankings.

Linear Models for Interpretability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models offer transparency when you need to understand exactly how each factor influences the forecast:

.. code-block:: python

   # Linear model with quantile support
   linear_model = ModelCreator.create_model(ModelType.LINEAR_QUANTILE)
   
   # Easy to interpret coefficients
   coefficients = linear_model.get_feature_importance()

Choose linear models when regulatory requirements demand explainable predictions or when working with limited training data.

Weather Dependency and Key Predictors
--------------------------------------

Energy consumption patterns are heavily influenced by weather conditions. OpenSTEF automatically engineers weather features that capture these relationships.

Temperature Effects
^^^^^^^^^^^^^^^^^^^

Temperature is often the strongest predictor for building energy consumption:

.. code-block:: python

   from openstef.feature_engineering.weather_features import add_humidity_features
   
   # OpenSTEF automatically creates temperature-based features
   # including heating/cooling degree days and humidity calculations
   enhanced_data = add_humidity_features(weather_data)

The library calculates derived features like saturation pressure, vapor pressure, dewpoint, and air density that often predict energy usage better than raw temperature alone.

Wind and Solar Features
^^^^^^^^^^^^^^^^^^^^^^^

For renewable energy forecasting, OpenSTEF provides specialized wind and solar feature engineering:

.. code-block:: python

   from openstef.feature_engineering.weather_features import (
       calculate_windspeed_at_hubheight,
       calculate_windturbine_power_output,
       add_additional_solar_features
   )
   
   # Calculate wind power at specific hub height
   hub_windspeed = calculate_windspeed_at_hubheight(
       windspeed=weather_data['windspeed_10m'],
       hub_height=100.0
   )
   
   # Estimate turbine output
   power_output = calculate_windturbine_power_output(
       windspeed=hub_windspeed,
       n_turbines=50
   )

These features account for the physics of renewable energy generation, improving forecast accuracy compared to using raw weather measurements.

Interpreting Forecast Quality
-----------------------------

OpenSTEF provides multiple metrics to evaluate forecast performance, each highlighting different aspects of accuracy.

Core Accuracy Metrics
^^^^^^^^^^^^^^^^^^^^^^

The most commonly used metrics are:

.. code-block:: python

   from openstef.metrics.metrics import mae, rmse, skill_score
   
   # Mean Absolute Error - easy to interpret
   mae_score = mae(actual_values, forecasted_values)
   
   # Root Mean Square Error - penalizes large errors more
   rmse_score = rmse(actual_values, forecasted_values)
   
   # Skill score - performance relative to naive baseline
   skill = skill_score(actual_values, forecasted_values, baseline_mean)

MAE tells you the average forecast error in the same units as your data. RMSE gives higher weight to large errors. Skill score shows whether your model beats a simple average - values above 0 indicate improvement over the baseline.

Peak Performance Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^

Energy systems care most about accuracy during peak demand periods:

.. code-block:: python

   from openstef.metrics.metrics import r_mae_highest, skill_score_positive_peaks
   
   # Accuracy during highest 5% of demand periods
   peak_accuracy = r_mae_highest(actual_values, forecasted_values)
   
   # Skill score focused on peak periods
   peak_skill = skill_score_positive_peaks(
       actual_values, forecasted_values, baseline_mean
   )

These metrics help you understand whether your model performs well when it matters most for grid operations.

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems need robust fallback mechanisms when primary models fail or training data is insufficient.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's default fallback strategy uses historical patterns from extreme conditions:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast using extreme day profile
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input,
       load=historical_load_data,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )

This approach identifies the most extreme historical day with similar characteristics and uses its load profile as a fallback forecast. The resulting forecast includes a 'quality' column marked as 'substituted' to indicate fallback usage.

Building Reliable Systems
^^^^^^^^^^^^^^^^^^^^^^^^^

In production, combine multiple strategies for maximum reliability:

.. code-block:: python

   try:
       # Attempt primary forecast
       forecast = primary_model.predict(forecast_input)
       forecast['quality'] = 'good'
   except Exception:
       try:
           # Try secondary model
           forecast = backup_model.predict(forecast_input)
           forecast['quality'] = 'backup'
       except Exception:
           # Use fallback strategy
           forecast = generate_fallback(
               forecast_input, historical_data
           )

This layered approach ensures your system always produces a forecast, even when individual components fail.

.. note::
   For more detailed examples of implementing these concepts, see the :doc:`../getting_started/tutorials` page. The :doc:`../guides/use_cases` page shows how these concepts apply to specific energy forecasting scenarios.