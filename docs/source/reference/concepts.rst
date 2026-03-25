Forecasting Concepts
====================


Understanding Forecast Results
------------------------------


OpenSTEF forecast outputs contain multiple components to represent prediction uncertainty. The primary forecast is typically the median (50th percentile) value, accompanied by quantile columns that define confidence intervals at different probability levels. Standard deviation columns provide additional uncertainty measures when available.

Quantile columns follow the naming convention 'quantile_P{percentile:02d}', such as 'quantile_P10' for the 10th percentile or 'quantile_P90' for the 90th percentile. These quantiles form confidence bands around the central forecast, with wider bands indicating higher uncertainty in the prediction.

The forecast output structure varies depending on the model type. Quantile regression models provide directly trained quantile predictions, while standard models generate quantiles by assuming normally distributed errors around the point forecast using the standard deviation column.


.. code-block:: python

   import pandas as pd
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline

   # Train a quantile model
   model = train_model_pipeline(
       pj=prediction_job,
       input_data=train_data,
       model_type="xgb_quantile"
   )

   # Generate forecast with quantiles
   forecast_data = model.predict(test_data)

   # Access median forecast (50th percentile)
   median_forecast = forecast_data.median_series

   # Access standard deviation if available
   std_dev = forecast_data.standard_deviation_series

   # Extract all quantile columns
   quantiles_df = forecast_data.quantiles_data

   # Access specific quantiles
   lower_bound = quantiles_df['quantile_P10']  # 10th percentile
   upper_bound = quantiles_df['quantile_P90']  # 90th percentile

   # Filter for specific quantiles only
   from openstef.data_classes.prediction_job import Quantile
   selected_quantiles = forecast_data.filter_quantiles([
       Quantile(0.25), Quantile(0.75)
   ])

   # Convert to pandas DataFrame for analysis
   forecast_df = forecast_data.to_pandas()
   print(f"Confidence interval width: {upper_bound - lower_bound}")


Quantiles and Confidence Intervals
----------------------------------


Quantiles represent the probability distribution of forecast uncertainty, showing the likelihood that actual energy demand will fall below specific threshold values. In grid operations, quantiles enable operators to assess risk levels and make informed decisions about reserve capacity, balancing costs against reliability requirements. The quantile bands provide a complete picture of forecast confidence rather than just point estimates.


.. [DIAGRAM: Visual representation of quantile forecasts showing P10, P50, P90 bands over time]


Model Selection and Use Cases
-----------------------------


OpenSTEF provides several model types optimized for different forecasting scenarios. XGBoost models excel at capturing complex non-linear patterns and feature interactions, making them ideal for energy demand forecasting with multiple weather variables. Linear regression offers interpretability and fast training for simpler relationships or when explainability is crucial.

LightGBM provides efficient gradient boosting with lower memory usage, suitable for large datasets or resource-constrained environments. Quantile models (both XGBoost and Linear variants) enable uncertainty quantification by predicting confidence intervals rather than point estimates, valuable for risk assessment and grid stability planning.

ARIMA models handle time series with strong seasonal patterns and autocorrelation, particularly effective for transport forecasts and district heating applications. The choice depends on data complexity, interpretability requirements, computational constraints, and whether probabilistic forecasts are needed for your specific use case.


- XGBoost (XGB) for congestion forecasts requiring high accuracy and complex pattern recognition

- Linear Regression for transport forecasts with clear seasonal patterns and interpretable coefficients

- LightGBM (LGB) for district heating applications needing fast training on large datasets

- XGB Quantile for EV charging capacity estimation requiring uncertainty bounds

- Linear Quantile for grid loss forecasts where prediction intervals are critical

- ARIMA for short-term MV route congestion with strong temporal dependencies


Important Predictors and Weather Dependency
-------------------------------------------


Weather variables impact energy forecasts differently depending on the generation type and forecast horizon. Solar forecasts heavily depend on cloud cover, irradiance, and temperature features, while wind forecasts prioritize wind speed, direction, and turbulence indicators. OpenSTEF's feature engineering automatically adds weather-specific features like extrapolated wind speed at 100m height and normalized wind power curves based on turbine characteristics.

Feature selection becomes critical as weather forecast accuracy degrades beyond 7 days, where 15-minute resolution data becomes unavailable. For short-term forecasts, humidity, temperature variations, and atmospheric pressure provide additional predictive power. The library's feature applicators automatically generate relevant weather features, though filtering may be required to remove unnecessary variables that don't improve specific forecast types.


.. code-block:: python

   from openstef.model.regressors.xgb import XGBOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features
   import pandas as pd

   # Train model with feature engineering
   model = XGBOpenstfRegressor()
   data_with_features = apply_features(train_data, pj=prediction_job)
   X_train = data_with_features.drop(columns=['load'])
   y_train = data_with_features['load']
   model.fit(X_train, y_train)

   # Get feature importance
   importance_df = pd.DataFrame({
       'feature': X_train.columns,
       'importance': model.feature_importances_
   }).sort_values('importance', ascending=False)

   # Analyze weather dependency
   weather_features = importance_df[importance_df['feature'].str.contains('wind|temp|rad|humid')]
   print(f"Top weather predictors:\n{weather_features.head()}")


Fallback Strategies
-------------------


OpenSTEF implements multiple fallback strategies to ensure forecast availability when primary models fail or insufficient data exists. The extreme day strategy uses historical profiles from the most extreme consumption day as a substitute forecast. All fallback forecasts are labeled with quality indicators, enabling transparent tracking of forecast sources for operational decisions. This resilient approach guarantees continuous forecast delivery in critical energy sector applications.


.. note::

   Always implement multiple fallback strategies to ensure forecast availability in critical energy applications. Label fallback forecasts clearly using the 'quality' column to maintain decision traceability. Consider extreme day profiles for emergency situations when primary models fail.


