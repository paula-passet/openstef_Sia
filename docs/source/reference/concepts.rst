Key Forecasting Concepts
========================

Understanding how to interpret and work with OpenSTEF forecasts requires grasping several fundamental concepts. This page explains the most important ideas through practical examples, helping you understand not just what the library does, but why it works the way it does.

Understanding Forecast Results
------------------------------

When OpenSTEF generates a forecast, you get more than just a single predicted value. The library provides rich information about uncertainty and confidence, which is crucial for making operational decisions in energy systems.

.. code-block:: python

   import pandas as pd
   from openstef.model.model_creator import ModelCreator
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Create a prediction job with quantiles
   pj = PredictionJobDataClass(
       id=1,
       model='xgb',
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       forecast_type="demand",
       lat=52.0,
       lon=5.0
   )
   
   # After training and prediction, your forecast contains:
   # - 'forecast': the main prediction (P50 quantile)
   # - 'stdev': standard deviation for confidence intervals
   # - 'quantile_P10', 'quantile_P30', etc.: specific quantile predictions

The forecast DataFrame structure tells a story. The main 'forecast' column represents the most likely outcome (50th percentile), while the quantile columns show the range of possible outcomes. For example, if your P90 quantile shows 150 MW and your P10 shows 100 MW, there's an 80% chance the actual load will fall between these values.

Quantiles and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides uncertainty information through two complementary approaches. The standard deviation column assumes normally distributed errors and works well for most situations. However, energy load often exhibits asymmetric uncertainty - peaks might be harder to predict than valleys.

.. code-block:: python

   # Interpreting quantile forecasts
   forecast_data = {
       'forecast': [120, 115],           # P50 - most likely outcome
       'quantile_P10': [100, 95],        # 10% chance of being below this
       'quantile_P90': [140, 135],       # 90% chance of being below this
       'stdev': [8, 7]                   # Standard deviation
   }
   
   # The P90-P10 range gives you the 80% confidence interval
   # Wider ranges indicate more uncertainty

For quantile-capable models like XGBoost quantile regression, OpenSTEF trains separate models for each quantile, providing more accurate uncertainty estimates than the normal distribution assumption. This is particularly valuable for peak detection and congestion management where you need to know the probability of exceeding certain thresholds.

Model Choice for Different Use Cases
-------------------------------------

OpenSTEF supports multiple model types, each with distinct strengths. Understanding when to use each model is crucial for getting the best results from your forecasting system.

XGBoost models excel at capturing complex, non-linear relationships in your data. They automatically discover interactions between weather variables, time patterns, and historical load. This makes them ideal for general-purpose forecasting where you want high overall accuracy.

.. code-block:: python

   # XGBoost for complex patterns
   pj_xgb = PredictionJobDataClass(
       model='xgb',  # Good for: complex patterns, feature interactions
       quantiles=[0.10, 0.50, 0.90]
   )
   
   # Linear quantile regression for interpretability
   pj_linear = PredictionJobDataClass(
       model='linear_quantile',  # Good for: extreme events, interpretability
       quantiles=[0.10, 0.50, 0.90]
   )

Linear quantile regression offers different advantages. While it may have lower overall accuracy, it often performs better at predicting extreme events that weren't well-represented in training data. The model coefficients are also directly interpretable, making it valuable when you need to understand exactly how each factor influences the forecast.

For congestion forecasting, you might prefer linear models because they're more conservative with peaks. For general demand forecasting with rich historical data, XGBoost typically provides better results. The choice depends on your specific operational needs and risk tolerance.

Weather Dependency and Important Predictors
--------------------------------------------

Energy consumption patterns are heavily influenced by weather conditions, but the relationships are more complex than simple temperature correlations. OpenSTEF automatically engineers weather features that capture these nuanced relationships.

.. code-block:: python

   from openstef.feature_engineering.weather_features import humidity_calculations
   
   # OpenSTEF automatically creates derived weather features
   # Temperature -> heating/cooling degree days
   # Humidity + temperature -> air density, dewpoint
   # Wind speed -> adjusted for hub height
   
   # Example of derived features OpenSTEF creates:
   weather_features = humidity_calculations(
       temperature=20.0,  # Celsius
       rh=65.0,          # Relative humidity %
       pressure=1013.25   # hPa
   )
   # Returns: saturation_pressure, vapour_pressure, dewpoint, air_density

The library considers not just current weather but also weather forecasts at different horizons. Solar radiation affects load patterns differently in residential versus industrial areas. Wind speed matters for areas with significant renewable generation. Air density influences the efficiency of power transmission.

Understanding these relationships helps explain forecast behavior. If your model shows high uncertainty during weather transitions, it's responding appropriately to the inherent unpredictability of load during these periods. The geographic coordinates in your prediction job aren't just for weather data - they're used to calculate sun angles, seasonal patterns, and other location-specific features.

Fallback Strategies for Reliability
------------------------------------

Real-world forecasting systems must handle situations where the primary model fails or produces unreliable results. OpenSTEF includes fallback mechanisms to ensure you always get a forecast, even when conditions are challenging.

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # When primary forecast fails, use fallback
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input_data,
       load=historical_load_data,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Fallback forecast includes 'quality' column marked as 'substituted'
   # This lets downstream systems know the forecast reliability

The extreme day strategy identifies the historical day with the most similar conditions and uses its load profile. This approach provides reasonable estimates when your primary model encounters data it hasn't seen before, such as during equipment failures or extreme weather events.

The quality indicator in fallback forecasts is crucial for operational systems. It allows automatic processes to adjust their behavior - perhaps using wider safety margins or triggering manual review when forecasts are substituted rather than model-generated.

Forecast Quality and Evaluation
--------------------------------

Understanding forecast quality requires looking beyond simple accuracy metrics. Energy systems care about different types of errors differently - missing a peak might be more costly than slightly overestimating base load.

.. code-block:: python

   from openstef.metrics.metrics import rmse, bias, mae, r_mae_highest
   
   # Different metrics tell different stories
   overall_rmse = rmse(actual_load, forecast_load)
   peak_accuracy = r_mae_highest(actual_load, forecast_load, percentile=0.95)
   systematic_bias = bias(actual_load, forecast_load)
   
   # Peak accuracy often matters more than overall accuracy
   # for congestion management applications

The library provides specialized metrics for energy forecasting. The `r_mae_highest` function focuses on the accuracy of peak predictions, which is often more operationally relevant than overall error. The `frac_in_stdev` metric tells you how well-calibrated your uncertainty estimates are.

When evaluating forecasts, consider the operational context. A forecast that's slightly less accurate overall but better at predicting peaks might be more valuable for grid operations. The quantile forecasts let you evaluate not just point accuracy but also the quality of uncertainty estimates, which is crucial for risk-based decision making.

.. note::
   For comprehensive evaluation workflows and backtesting examples, see the :doc:`../getting_started/tutorials` page. For specific use case guidance, consult the :doc:`../guides/use_cases` documentation.