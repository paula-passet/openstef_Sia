Key Forecasting Concepts
========================

Understanding the principles behind energy forecasting helps you make better decisions when using OpenSTEF. This page explains the core concepts through practical examples, showing why certain design choices matter and how to interpret your results effectively.

Understanding Forecast Uncertainty
----------------------------------

Energy forecasting is inherently uncertain. OpenSTEF provides two complementary ways to quantify this uncertainty: standard deviations and quantile predictions.

Standard Deviation Approach
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The simplest uncertainty measure is a standard deviation that varies by time of day and season. OpenSTEF learns these patterns during training::

   from openstef.model.confidence_interval_applicator import ConfidenceIntervalApplicator
   
   # After training, add uncertainty estimates
   ci_applicator = ConfidenceIntervalApplicator(model, forecast_input_data)
   forecast_with_uncertainty = ci_applicator.add_confidence_interval(forecast, pj)
   
   # The result includes both point forecast and uncertainty
   print(forecast_with_uncertainty.columns)
   # ['forecast', 'stdev', 'quantile_0.1', 'quantile_0.9', ...]

This approach assumes forecast errors follow a normal distribution. It works well for most energy forecasting applications but may underestimate extreme events.

Quantile Predictions
^^^^^^^^^^^^^^^^^^^^

For more precise uncertainty estimates, OpenSTEF can train models that directly predict quantiles. These models learn the full shape of the prediction distribution::

   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType
   
   # Train a quantile model
   quantile_model = ModelCreator.create_model(ModelType.XGB_QUANTILE)
   quantile_model.fit(train_data)
   
   # Get probabilistic forecasts
   forecast = quantile_model.predict(test_data)

Quantile models are particularly valuable when you need to understand asymmetric risks or tail events that matter for grid operations.

Choosing the Right Model
------------------------

OpenSTEF offers several model types, each suited to different forecasting scenarios. The choice depends on your data characteristics and operational requirements.

Tree-Based Models for Complex Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost models excel when you have rich feature sets and complex non-linear relationships::

   # XGBoost handles weather interactions, seasonality, and load patterns automatically
   xgb_model = ModelCreator.create_model(ModelType.XGB)
   
   # Good for: congestion forecasting, demand prediction with weather dependency
   # Pros: Handles missing data, captures interactions, provides feature importance
   # Cons: Less interpretable, requires more computational resources

Linear Models for Interpretability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models work well when relationships are straightforward and you need explainable results::

   # Linear models are transparent and fast
   linear_model = ModelCreator.create_model(ModelType.LINEAR)
   
   # Good for: simple load forecasting, baseline comparisons
   # Pros: Fast training, interpretable coefficients, stable predictions
   # Cons: Cannot capture complex interactions or non-linear patterns

The choice often comes down to the complexity of your forecasting problem. Start with linear models for baseline performance, then move to XGBoost when you need to capture more sophisticated patterns.

Important Predictors and Weather Dependency
-------------------------------------------

Understanding which features drive your forecasts helps you focus data collection efforts and interpret model behavior.

Weather Features
^^^^^^^^^^^^^^^^

OpenSTEF automatically creates weather-derived features that capture energy system dependencies::

   from openstef.feature_engineering.weather_features import add_solar_features, add_additional_wind_features
   
   # Solar features for PV forecasting
   data_with_solar = add_solar_features(data, pj, feature_names=['solar_irradiance', 'clearsky_ghi'])
   
   # Wind features for wind power or temperature-driven load
   data_with_wind = add_additional_wind_features(data, feature_names=['windspeed_100m', 'wind_power'])

These features often become the most important predictors in energy forecasting models. The library handles the complex physics calculations automatically.

Historical Load Patterns
^^^^^^^^^^^^^^^^^^^^^^^^

Past energy consumption provides crucial context for future predictions::

   # OpenSTEF automatically includes lagged features
   # - Load 1 day ago (same hour)
   # - Load 7 days ago (same weekday/hour)
   # - Recent trend information

These temporal features capture recurring patterns that weather alone cannot explain, such as industrial schedules or behavioral routines.

Evaluating Forecast Quality
---------------------------

Different metrics reveal different aspects of forecast performance. Choose evaluation criteria that match your operational needs.

Point Forecast Accuracy
^^^^^^^^^^^^^^^^^^^^^^^

For deterministic forecasts, focus on metrics that reflect real-world costs::

   from openstef.metrics.metrics import mae, rmae, nsme
   
   # Mean Absolute Error - interpretable in original units
   error_mw = mae(realized_load, forecast)
   
   # Relative MAE - normalized for comparison across different scales
   relative_error = rmae(realized_load, forecast)
   
   # Nash-Sutcliffe efficiency - compares to naive baseline
   skill_score = nsme(realized_load, forecast)

Probabilistic Forecast Assessment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When using quantile predictions, evaluate both accuracy and calibration::

   from openstef_beam.metrics.metrics_probabilistic import crps, mean_absolute_calibration_error
   
   # CRPS measures overall probabilistic performance
   crps_score = crps(y_true, y_pred_quantiles, quantiles)
   
   # Calibration error shows if uncertainty estimates are reliable
   calibration_error = mean_absolute_calibration_error(y_true, y_pred_quantiles, quantiles)

Well-calibrated forecasts have uncertainty estimates that match observed variability - crucial for operational decision-making.

Fallback Strategies for Reliability
-----------------------------------

Production forecasting systems need robust fallback mechanisms when primary models fail or insufficient data is available.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^

OpenSTEF's default fallback uses historical profiles from extreme conditions::

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # When model fails, use profile from most extreme historical day
   fallback_forecast = generate_fallback(
       forecast_input, 
       historical_load, 
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Forecast includes quality indicator
   print(fallback_forecast['quality'].unique())
   # ['substituted'] - indicates fallback was used

This strategy provides reasonable estimates during data outages while clearly marking when normal model predictions aren't available.

Designing Robust Systems
^^^^^^^^^^^^^^^^^^^^^^^^

Build reliability into your forecasting workflow from the start::

   # Check data quality before forecasting
   if len(recent_data) < minimum_required_points:
       forecast = generate_fallback(forecast_input, historical_load)
   else:
       try:
           forecast = model.predict(forecast_input)
       except Exception:
           # Model failed - use fallback
           forecast = generate_fallback(forecast_input, historical_load)

This pattern ensures your system continues operating even when individual components fail, maintaining service reliability for critical energy operations.

The key is balancing forecast accuracy with operational robustness. Perfect models that fail unpredictably are less valuable than good models that degrade gracefully.