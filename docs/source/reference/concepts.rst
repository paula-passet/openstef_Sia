Forecasting Concepts
====================


Understanding Forecast Results
------------------------------


OpenSTEF forecast outputs contain multiple components that provide comprehensive uncertainty information. The primary forecast is typically the median (50th percentile) prediction, representing the most likely outcome. Standard deviation columns indicate forecast uncertainty when available from model training.

Quantile columns provide detailed confidence intervals using the format 'quantile_P{percentile}', such as 'quantile_P10' for the 10th percentile and 'quantile_P90' for the 90th percentile. These quantiles define prediction intervals and are generated either through quantile regression for specialized models or by assuming normal error distribution for standard models.

The forecast structure enables comprehensive uncertainty analysis, allowing users to assess both point predictions and the full probability distribution of potential outcomes. This multi-component approach supports robust decision-making under uncertainty in energy forecasting applications.


.. code-block:: python

   import pandas as pd
   from openstef.model.forecast_dataset import ForecastDataset

   # Example forecast output with quantiles
   forecast_data = pd.DataFrame({
       'datetime': pd.date_range('2024-01-01', periods=24, freq='H'),
       'forecast': [100, 105, 110, 95, 90, 85, 80, 75, 70, 65,
                    60, 55, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105],
       'stdev': [5.2, 5.8, 6.1, 4.9, 4.5, 4.2, 3.8, 3.5, 3.2, 2.9,
                 2.6, 2.3, 2.0, 2.3, 2.6, 2.9, 3.2, 3.5, 3.8, 4.2, 4.5, 4.9, 5.2, 5.8],
       'quantile_P10': [89, 93, 97, 84, 80, 76, 72, 68, 64, 60,
                        56, 52, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 89, 93],
       'quantile_P25': [95, 99, 103, 89, 85, 81, 77, 72, 68, 63,
                        59, 54, 50, 54, 59, 63, 68, 72, 77, 81, 85, 89, 95, 99],
       'quantile_P50': [100, 105, 110, 95, 90, 85, 80, 75, 70, 65,
                        60, 55, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 105],
       'quantile_P75': [105, 111, 117, 101, 95, 89, 83, 78, 72, 67,
                        61, 56, 52, 56, 61, 67, 72, 78, 83, 89, 95, 101, 105, 111],
       'quantile_P90': [111, 117, 123, 106, 100, 94, 88, 82, 76, 70,
                        64, 58, 52, 58, 64, 70, 76, 82, 88, 94, 100, 106, 111, 117]
   })

   # Create ForecastDataset
   forecast_dataset = ForecastDataset(forecast_data.set_index('datetime'))

   # Access median forecast
   median_forecast = forecast_dataset.median_series

   # Access standard deviation
   std_dev = forecast_dataset.standard_deviation_series

   # Access all quantiles
   quantiles_df = forecast_dataset.quantiles_data

   # Access specific quantile columns
   p10_forecast = forecast_data['quantile_P10']
   p90_forecast = forecast_data['quantile_P90']

   # Calculate confidence intervals
   confidence_80 = forecast_data['quantile_P90'] - forecast_data['quantile_P10']
   confidence_50 = forecast_data['quantile_P75'] - forecast_data['quantile_P25']


Quantiles and Uncertainty
-------------------------


Quantiles in forecasting represent probability levels that describe the likelihood of actual energy demand falling below a predicted value. Unlike point forecasts that provide single predictions, quantile forecasts deliver multiple scenarios with associated confidence levels. For grid operators, this uncertainty information enables risk-aware decision making by quantifying the probability of demand exceeding available capacity or falling below minimum operational thresholds.


.. image:: _static/images/placeholder_visualization_showing_forecast_quantiles_over_time_with_actual_values.png
   :alt: Visualization showing forecast quantiles over time with actual values
   :align: center


Model Selection and Use Cases
-----------------------------


OpenSTEF provides multiple model types for different forecasting scenarios. XGBoost models excel at capturing non-linear patterns and feature interactions, making them suitable for complex energy forecasting with multiple weather variables. Linear regression models offer interpretability and work well for simpler relationships or when model transparency is required.

Quantile models like XGBQuantileOpenstfRegressor provide uncertainty estimates alongside point forecasts, essential for risk assessment and operational planning. ARIMA models handle time series with strong seasonal patterns but require careful statistical tuning. LightGBM models offer faster training while maintaining competitive accuracy for large datasets.

Model selection depends on data complexity, interpretability requirements, training time constraints, and whether uncertainty quantification is needed. The library's model factory supports easy switching between types for experimentation and comparison.


- XGBoost models: Best for complex non-linear patterns, large datasets with mixed feature types, and when interpretability through feature importance is needed

- Linear regression: Optimal for simple linear relationships, small datasets, when fast training is required, or when model coefficients need direct interpretation

- ARIMA models: Suitable for time series with clear seasonal patterns, limited external features, and when statistical forecasting approaches are preferred

- Quantile regression: Choose when uncertainty quantification is critical, risk assessment is needed, or probabilistic forecasts are required

- LightGBM models: Ideal for very large datasets, when faster training than XGBoost is needed, and memory efficiency is important

- Ensemble models: Use when maximum accuracy is priority, diverse data patterns exist, and computational resources allow multiple model training


Feature Importance and Weather Dependencies
-------------------------------------------


OpenSTEF automatically calculates feature importance to help you understand which variables drive your forecasts. Weather dependencies are revealed through features like wind speed, temperature, humidity, and solar radiation that the library engineers from raw meteorological data. The feature engineering module creates derived weather features such as air density, dewpoint, and saturation pressure to capture complex atmospheric relationships that impact energy predictions.


.. code-block:: python

   from openstef.model.model import OpenstfRegressor
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   import pandas as pd
   import matplotlib.pyplot as plt

   # Load trained model
   model = OpenstfRegressor.load_model("path/to/saved/model.pkl")

   # Extract feature importance
   feature_importance = model.feature_importance_
   feature_names = model.feature_names_

   # Create importance DataFrame
   importance_df = pd.DataFrame({
       'feature': feature_names,
       'importance': feature_importance
   }).sort_values('importance', ascending=False)

   # Display top 10 most important features
   print(importance_df.head(10))

   # Visualize feature importance
   plt.figure(figsize=(10, 6))
   plt.barh(importance_df.head(15)['feature'], importance_df.head(15)['importance'])
   plt.xlabel('Feature Importance')
   plt.title('Top 15 Most Important Features')
   plt.gca().invert_yaxis()
   plt.tight_layout()
   plt.show()

   # Filter weather-related features
   weather_features = importance_df[importance_df['feature'].str.contains('temp|wind|radiation|humidity')]
   print("Weather feature importance:")
   print(weather_features)


Fallback Strategies
-------------------


OpenSTEF provides robust fallback mechanisms to ensure forecast availability even when primary models fail or insufficient data is available. The library implements multiple fallback strategies, with the primary approach using extreme day profiles from historical data to generate substitute forecasts when normal prediction methods cannot proceed.

When fallback mechanisms activate, OpenSTEF automatically marks forecast quality as 'substituted' to maintain transparency about data reliability. The extreme day strategy selects the most representative historical daily profile to fill gaps, ensuring continuous forecast delivery while preserving forecast integrity through quality indicators.


.. [DIAGRAM: Flowchart showing fallback decision tree when data is missing or models fail]


