Forecasting Concepts
====================


Understanding Forecast Results
------------------------------


OpenSTEF forecast outputs are structured DataFrames containing multiple components that provide comprehensive prediction information. The primary forecast values are accompanied by uncertainty quantification through confidence intervals, which include both a standard deviation column and quantile columns (such as quantile_P05, quantile_P50, quantile_P95) representing different probability levels. The median forecast corresponds to the 50th percentile (quantile_P50), while other quantiles define the prediction uncertainty range. Additional components may include energy split forecasts that separate total load into constituent parts like solar, wind, and base consumption when component-specific coefficients are available.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Create forecast with quantiles
   pj = PredictionJob(id=123, name="solar_farm_forecast")
   forecast_data = create_forecast_pipeline(pj, input_data, model)

   # Access different forecast components
   median_forecast = forecast_data.forecast_series
   confidence_interval = forecast_data.standard_deviation_series
   quantiles_df = forecast_data.quantiles_data

   # Interpret specific quantiles
   p10_forecast = forecast_data['quantile_P10']  # 10% probability of being below
   p90_forecast = forecast_data['quantile_P90']  # 90% probability of being below
   uncertainty_range = p90_forecast - p10_forecast

   # Filter for specific quantiles of interest
   from openstef.enums import Quantile
   selected_quantiles = forecast_data.filter_quantiles([Quantile.P25, Quantile.P75])

   print(f"Median forecast: {median_forecast.iloc[0]:.2f} MW")
   print(f"80% confidence interval: [{p10_forecast.iloc[0]:.2f}, {p90_forecast.iloc[0]:.2f}] MW")


Quantiles and Confidence Intervals
----------------------------------


Probabilistic forecasts provide uncertainty estimates alongside point predictions, enabling better decision-making in energy systems. Instead of a single forecast value, quantiles represent the probability that actual values will fall below specific thresholds. For example, a 0.9 quantile forecast indicates 90% confidence that actual energy demand will be below the predicted value, while a 0.1 quantile provides the lower bound with 90% confidence the actual value will exceed it.


.. [DIAGRAM: Visualization of quantile forecasts showing P10, P50, P90 bands over time]


Model Selection for Different Use Cases
---------------------------------------


OpenSTEF provides multiple model types to handle different forecasting scenarios. XGBoost models excel for complex non-linear relationships and feature interactions, making them ideal for datasets with many predictors. Linear regression models work best for simpler relationships with good interpretability requirements. Quantile regression models are suitable when prediction intervals are needed alongside point forecasts. ARIMA models handle time series with strong temporal patterns and seasonal components. LightGBM offers faster training for large datasets while maintaining competitive accuracy. Model selection depends on data complexity, interpretability needs, training time constraints, and whether probabilistic forecasts are required.


- Use XGBoost for complex non-linear relationships with mixed data types and when interpretability is less critical

- Choose Linear Regression for simple linear relationships, when interpretability is crucial, or with limited training data

- Select XGB Quantile for probabilistic forecasts requiring uncertainty estimates and confidence intervals

- Apply ARIMA for time series with strong seasonal patterns and when statistical analysis is preferred over machine learning

- Use LightGBM for large datasets requiring faster training times while maintaining gradient boosting performance

- Consider ensemble approaches when data exhibits multiple patterns or when maximum accuracy is required


Key Predictors and Weather Dependency
-------------------------------------


Weather data serves as a fundamental predictor in energy forecasting, with OpenSTEF providing specialized features for different energy sources. Solar forecasting relies heavily on insolation, temperature, and humidity calculations including saturation pressure, vapor pressure, and dewpoint. Wind forecasting incorporates windspeed, air density, and additional wind-derived features. The library automatically calculates these weather-dependent features based on location coordinates, enabling accurate predictions for renewable energy systems where meteorological conditions directly impact generation capacity.


.. image:: _static/images/placeholder_feature_importance_chart_showing_weather_vs_load_patterns.png
   :alt: Feature importance chart showing weather vs load patterns
   :align: center


Reliability and Fallback Strategies
-----------------------------------


OpenSTEF forecasting workflows can fail due to insufficient input data, ongoing flatliners in load measurements, or missing predicted load for specified time ranges. The library provides built-in exception handling through InputDataInsufficientError, InputDataOngoingFlatlinerError, and NoPredictedLoadError to identify these failure modes.

Design resilient workflows by implementing fallback strategies using the generate_fallback function with FallbackStrategy.EXTREME_DAY to substitute forecasts with historic extreme day profiles when primary models fail. Always validate forecast quality using the 'quality' column which indicates 'substituted' values from fallback mechanisms.


.. note::

   Implement fallback strategies using FallbackStrategy.EXTREME_DAY for production resilience. Monitor forecast quality indicators and handle InputDataInsufficientError exceptions gracefully. Always validate model standard deviation exists to prevent ModelWithoutStDev errors during deployment.


