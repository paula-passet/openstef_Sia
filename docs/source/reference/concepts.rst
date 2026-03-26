Key Forecasting Concepts
========================

Understanding how OpenSTEF works means grasping several interconnected forecasting concepts. This page explains the most important ideas through practical examples, helping you make informed decisions about model selection, interpret your results correctly, and build reliable forecasting systems.

Understanding Forecast Results
------------------------------

When OpenSTEF generates a forecast, you get more than just predicted values. The library provides rich information about uncertainty and forecast quality that's essential for operational decision-making.

Every forecast includes a point prediction (the most likely value) and uncertainty information. The uncertainty comes in two forms: a standard deviation column and quantile predictions. Here's what a typical forecast looks like:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import ForecastDataset
   from datetime import timedelta
   
   # Example forecast output
   forecast_data = pd.DataFrame({
       'forecast': [100.5, 105.2, 98.7],
       'stdev': [8.2, 9.1, 7.8],
       'quantile_P10': [87.3, 91.8, 85.2],
       'quantile_P50': [100.5, 105.2, 98.7],  # Same as point forecast
       'quantile_P90': [113.7, 118.6, 112.2]
   }, index=pd.date_range('2025-01-01', periods=3, freq='h'))
   
   dataset = ForecastDataset(forecast_data, timedelta(hours=1))
   print(f"Available quantiles: {[q.value for q in dataset.quantiles]}")

The quantile columns tell you about forecast uncertainty. P10 means there's a 10% chance the actual value will be below this level, while P90 means there's a 90% chance it will be below this level. The range between P10 and P90 gives you the 80% confidence interval.

Quantiles and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF generates confidence intervals using two different approaches depending on your model type. For standard models like XGBoost and LightGBM, the library uses the standard deviation column and assumes normally distributed errors. For quantile models, it uses specialized quantile regression techniques.

.. code-block:: python

   from openstef.enums import ModelType
   from openstef.model.confidence_interval_applicator import add_confidence_interval
   
   # Standard models use normal distribution assumption
   standard_forecast = pd.DataFrame({
       'forecast': [100.0, 110.0],
       'stdev': [10.0, 12.0]
   }, index=pd.date_range('2025-01-01', periods=2, freq='h'))
   
   # This adds quantile columns based on normal distribution
   forecast_with_ci = add_confidence_interval(standard_forecast, prediction_job)
   
   # Quantile models directly predict uncertainty
   quantile_forecast = pd.DataFrame({
       'forecast': [100.0, 110.0],
       'quantile_P25': [92.0, 101.0],
       'quantile_P75': [108.0, 119.0]
   }, index=pd.date_range('2025-01-01', periods=2, freq='h'))

The choice between these approaches affects how you interpret uncertainty. Normal distribution assumptions work well for most energy forecasting scenarios, but quantile models can capture asymmetric uncertainty patterns that occur during extreme weather or unusual grid conditions.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF offers several model types, each designed for specific forecasting scenarios. Understanding when to use each model type helps you achieve better performance and more reliable results.

XGBoost models (``ModelType.XGB``) are the workhorses of OpenSTEF. They handle complex non-linear relationships between weather and energy consumption, automatically capture seasonal patterns, and work well with missing data. Use XGBoost for most demand forecasting scenarios:

.. code-block:: python

   from openstef.enums import ModelType
   from openstef.model.model_creator import ModelCreator
   
   # XGBoost for general demand forecasting
   xgb_model = ModelCreator.create_model(ModelType.XGB)
   
   # XGBoost with quantile regression for uncertainty-critical applications
   xgb_quantile = ModelCreator.create_model(ModelType.XGB_QUANTILE)

LightGBM models (``ModelType.LGB``) offer similar capabilities to XGBoost but with faster training times and lower memory usage. Choose LightGBM when you need to retrain models frequently or work with very large datasets.

Linear models (``ModelType.LINEAR``) provide interpretable results and work well when relationships are primarily linear. They're particularly useful for solar and wind forecasting where weather variables have direct physical relationships with generation:

.. code-block:: python

   # Linear model for solar generation forecasting
   linear_model = ModelCreator.create_model(ModelType.LINEAR)
   
   # Linear quantile model for wind generation with uncertainty
   linear_quantile = ModelCreator.create_model(ModelType.LINEAR_QUANTILE)

For specialized scenarios, OpenSTEF provides fallback models. The ARIMA model handles pure time series patterns without external predictors, while the Flatliner model provides constant predictions based on recent averages.

Weather Dependencies and Key Predictors
----------------------------------------

Energy consumption and generation patterns are heavily influenced by weather conditions. OpenSTEF automatically generates weather-based features that capture these relationships, but understanding which predictors matter most helps you interpret model behavior and diagnose issues.

Temperature is the primary driver for heating and cooling demand. OpenSTEF creates multiple temperature-based features including current temperature, temperature changes, and heating/cooling degree days:

.. code-block:: python

   from openstef.feature_engineering.weather_features import add_humidity_features
   
   # Temperature-derived features are automatically created
   # These include: T-1h, T-2h (lagged temperatures)
   # APX (temperature-based demand proxy)
   # heating/cooling degree days
   
   # Humidity features add comfort indices
   data_with_humidity = add_humidity_features(weather_data, feature_names)

Wind speed affects both demand (through perceived temperature) and renewable generation. OpenSTEF calculates wind power curves and wind chill factors automatically. Solar radiation drives photovoltaic generation and affects cooling demand through building heat gain.

The library also creates derived weather features that capture human comfort and energy system physics. Air density affects wind turbine performance, while dewpoint and humidity indices influence air conditioning usage patterns.

Understanding Feature Importance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After training, you can examine which predictors your model considers most important. This helps validate that the model is learning sensible relationships:

.. code-block:: python

   # After training an XGBoost model
   feature_importance = trained_model.feature_importances_
   feature_names = trained_model.feature_names_in_
   
   # Create importance ranking
   importance_df = pd.DataFrame({
       'feature': feature_names,
       'importance': feature_importance
   }).sort_values('importance', ascending=False)
   
   print("Top 10 most important features:")
   print(importance_df.head(10))

Typically, you'll see recent load values (autoregressive terms) at the top, followed by time-of-day and day-of-week indicators, then weather variables. If weather features dominate unexpectedly, it might indicate data quality issues or unusual weather patterns in your training period.

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems must handle various failure modes gracefully. OpenSTEF provides fallback mechanisms that ensure you always get a forecast, even when primary models fail or input data is incomplete.

The primary fallback strategy uses extreme day profiles. When a model fails or produces unreliable results, the system identifies the most similar historical day with extreme conditions and uses its load profile as the forecast:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast using extreme day strategy
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input_data,
       load=historical_load_data,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Fallback forecasts are marked with quality='substituted'
   print(f"Forecast quality: {fallback_forecast['quality'].iloc[0]}")

The extreme day approach works well because energy systems show strong daily patterns, and extreme conditions (very hot or cold days) tend to produce similar load shapes. This gives you a reasonable forecast that captures the expected daily profile while flagging that the prediction comes from fallback logic.

For critical applications, you can configure the system to raise errors instead of using fallbacks:

.. code-block:: python

   # Raise error instead of generating fallback
   try:
       fallback_forecast = generate_fallback(
           forecast_input=forecast_input_data,
           load=historical_load_data,
           fallback_strategy=FallbackStrategy.RAISE_ERROR
       )
   except ValueError as e:
       # Handle the error - perhaps by using a different model
       # or requesting manual intervention
       print(f"Fallback failed: {e}")

Building reliable systems means planning for these scenarios. Consider implementing multiple fallback layers: primary model → secondary model → extreme day fallback → constant forecast based on recent average.

Interpreting Forecast Quality
-----------------------------

OpenSTEF provides several ways to assess forecast quality, both during development and in production. Understanding these metrics helps you tune models, detect performance degradation, and communicate forecast reliability to stakeholders.

The most intuitive metrics are Mean Absolute Error (MAE) and Root Mean Square Error (RMSE). MAE tells you the average size of forecast errors in the same units as your data, while RMSE penalizes large errors more heavily:

.. code-block:: python

   from openstef.metrics.metrics import mae, rmse
   
   # Calculate basic accuracy metrics
   forecast_mae = mae(actual_values, predicted_values)
   forecast_rmse = rmse(actual_values, predicted_values)
   
   print(f"Average error: {forecast_mae:.1f} MW")
   print(f"RMS error: {forecast_rmse:.1f} MW")

For operational applications, relative metrics often matter more than absolute ones. The relative MAE (rMAE) expresses errors as a percentage of the typical load range:

.. code-block:: python

   from openstef.metrics.metrics import r_mae
   
   # Relative error as percentage of load range
   relative_error = r_mae(actual_values, predicted_values)
   print(f"Relative error: {relative_error:.1%}")

Peak detection performance is crucial for grid management. OpenSTEF provides specialized metrics that focus on how well models predict high-load events:

.. code-block:: python

   from openstef.metrics.metrics import r_mae_highest
   
   # Error specifically for the highest 5% of load values
   peak_error = r_mae_highest(actual_values, predicted_values, percentile=0.95)
   print(f"Peak prediction error: {peak_error:.1%}")

For probabilistic forecasts, calibration metrics tell you whether your confidence intervals are reliable. Well-calibrated forecasts have actual values fall within predicted intervals at the expected rates.

The concepts covered here form the foundation for effective use of OpenSTEF. For hands-on experience applying these ideas, see the tutorials in the getting started section. For specific implementation guidance on different forecasting scenarios, consult the use cases guide.