Forecasting Concepts
====================


Understanding Forecast Results
------------------------------


OpenSTEF forecast outputs are structured as DataFrames containing multiple components that represent forecast uncertainty. The median forecast series provides the central prediction, while quantile columns follow the format 'quantile_P{percentile:02d}' (e.g., 'quantile_P10', 'quantile_P90') to represent prediction intervals. Standard deviation series may also be included when available, offering an alternative measure of forecast uncertainty alongside the quantile-based approach.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.create_forecast import create_forecast_pipeline

   # Create forecast using OpenSTEF pipeline
   job = PredictionJob(id=123, model="xgb", name="solar_forecast")
   forecast_dataset = create_forecast_pipeline(job, input_data)

   # Access median forecast (50th percentile)
   median_forecast = forecast_dataset.median_series()

   # Access standard deviation if available
   std_forecast = forecast_dataset.standard_deviation_series()

   # Get all quantile data as DataFrame
   quantiles_df = forecast_dataset.quantiles_data()
   print(quantiles_df.columns)  # ['quantile_P05', 'quantile_P10', ..., 'quantile_P95']

   # Filter specific quantiles
   from openstef.enums import Quantile
   selected_quantiles = forecast_dataset.filter_quantiles([Quantile.P10, Quantile.P90])

   # Convert to standard pandas DataFrame
   full_df = forecast_dataset.to_pandas()


Quantiles and Confidence Intervals
----------------------------------


Quantiles represent specific percentiles of a forecast's probability distribution, capturing the range of possible outcomes rather than just a single prediction. For example, the 10th quantile indicates there's a 10% chance the actual value will be below this threshold, while the 90th quantile suggests a 90% probability of being below it. This probabilistic approach enables OpenSTEF to quantify forecast uncertainty by providing confidence intervals that reflect the model's certainty about different prediction ranges.


.. [DIAGRAM: Visualization showing forecast quantiles over time with actual values]


Model Selection and Use Cases
-----------------------------


OpenSTEF is a model-agnostic framework that supports multiple machine learning algorithms rather than being tied to a specific model type. The library provides complete pipelines for preprocessing, feature engineering, training, and forecasting that work with various underlying models. Users can leverage built-in domain knowledge for energy-specific feature engineering, such as converting solar radiation data into photovoltaic generation estimates. The framework generates probabilistic forecasts with uncertainty estimates, making it suitable for congestion management, transport forecasting, EV charging capacity planning, and grid loss prediction across different time horizons.


- High-frequency data (15-min intervals) with weather features: Use XGBoost or LightGBM for capturing complex non-linear patterns and feature interactions

- Low-frequency data (hourly/daily) with limited features: Linear models provide interpretable results and stable performance with minimal overfitting risk

- Large datasets (>10k samples) with mixed feature types: Ensemble methods like Random Forest handle categorical and numerical features effectively

- Small datasets (<1k samples) or sparse data: Ridge regression prevents overfitting while maintaining reasonable forecast accuracy

- Real-time applications requiring fast inference: Pre-trained linear models or lightweight tree models minimize prediction latency

- Probabilistic forecasting needs: Models supporting quantile regression (XGBoost, LightGBM) provide uncertainty estimates alongside point forecasts

- Seasonal patterns dominant: Include time-based features and consider models that capture cyclical behavior effectively

- External factors critical (weather, holidays): Feature-rich models like gradient boosting leverage domain-specific engineered features


Feature Importance and Weather Dependencies
-------------------------------------------


OpenSTEF automatically calculates feature importance to help you understand which variables drive your forecasts. Weather dependencies are revealed through engineered features like humidity calculations, wind characteristics, and solar radiation patterns. The library generates additional weather features including saturation pressure, vapor pressure, dewpoint, and air density to capture complex meteorological relationships that impact energy predictions.


.. code-block:: python

   import matplotlib.pyplot as plt
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.feature_engineering.apply_features import apply_features

   # Train model with feature engineering
   model = XGBQuantileOpenstfRegressor()
   train_data = apply_features(train_data, pj)
   model.fit(train_data[feature_columns], train_data['load'])

   # Extract feature importance
   feature_importance = model.feature_importances_
   feature_names = feature_columns

   # Create importance dataframe
   import pandas as pd
   importance_df = pd.DataFrame({
       'feature': feature_names,
       'importance': feature_importance
   }).sort_values('importance', ascending=False)

   # Visualize top 15 features
   plt.figure(figsize=(10, 8))
   top_features = importance_df.head(15)
   plt.barh(top_features['feature'], top_features['importance'])
   plt.xlabel('Feature Importance')
   plt.title('Top 15 Most Important Features')
   plt.gca().invert_yaxis()
   plt.tight_layout()
   plt.show()

   # Show weather feature importance
   weather_features = importance_df[importance_df['feature'].str.contains('temp|wind|radiation|humidity')]
   print("Weather feature importance:")
   print(weather_features)


Fallback Strategies and Error Handling
--------------------------------------


OpenSTEF provides robust fallback mechanisms when insufficient data prevents normal forecasting. The primary fallback strategy is EXTREME_DAY, which uses the daily profile from the most extreme historical day when training data is unavailable. Alternatively, RAISE_ERROR can be configured to throw exceptions instead of generating fallback forecasts. When fallback forecasts are generated, the quality column is automatically set to 'substituted' to indicate the forecast reliability. These mechanisms ensure continuous operation even when input data quality issues occur.


.. note::

   Implement proper error handling by catching specific OpenSTEF exceptions like InputDataInsufficientError and ComponentForecastTooShortHorizonError. Use FallbackStrategy.EXTREME_DAY for graceful degradation when primary models fail, and always validate forecast quality indicators before downstream usage.


