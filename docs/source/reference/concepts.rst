Forecasting Concepts
====================


Understanding Forecast Results
------------------------------


OpenSTEF forecast outputs contain point predictions along with uncertainty quantification through confidence intervals. The primary forecast is typically the median (50th percentile) prediction, while quantile columns provide probability bounds around this central estimate.

Forecast results include a standard deviation column that captures learned uncertainty patterns from training data. Additional quantile columns offer more precise confidence intervals, with values like the 10th and 90th percentiles defining prediction ranges.

The library generates these uncertainty measures through two methods: default confidence intervals using normal distribution assumptions, or quantile regression for models specifically trained to predict uncertainty. This probabilistic output enables users to assess forecast reliability and make risk-informed decisions.


.. code-block:: python

   import pandas as pd
   from openstef.data_classes.prediction_job import PredictionJob
   from openstef.pipeline.create_forecast import create_forecast

   # Create forecast with confidence intervals
   pj = PredictionJob(id=123, model="xgb", name="wind_farm_forecast")
   forecast_data = create_forecast(pj, forecast_input_data)

   # Example forecast output with quantiles
   print(forecast_data.head())
   #                     forecast  stdev  quantile_0.1  quantile_0.5  quantile_0.9
   # 2024-01-01 00:00:00     150.2   12.5        125.3        150.2        175.8
   # 2024-01-01 01:00:00     145.8   11.8        122.1        145.8        169.5

   # Access median forecast (50th percentile)
   median_forecast = forecast_data.median_series

   # Access specific quantiles
   q10_forecast = forecast_data['quantile_0.1']
   q90_forecast = forecast_data['quantile_0.9']

   # Get all quantile data
   quantiles_df = forecast_data.quantiles_data()

   # Access standard deviation for uncertainty
   stdev_series = forecast_data.standard_deviation_series


Model Selection for Different Use Cases
---------------------------------------


OpenSTEF provides several model types optimized for different forecasting scenarios. XGBoost models excel at capturing complex non-linear patterns and feature interactions, making them ideal for congestion forecasting and peak load prediction. Linear regression models offer interpretability and fast training, suitable for transport forecasts and grid loss estimation where relationships are more straightforward.

Quantile regression variants enable uncertainty quantification, crucial for risk-aware congestion management and capacity planning. ARIMA models handle time series with strong seasonal patterns, while LightGBM provides memory-efficient alternatives for large datasets. Model selection depends on data characteristics, interpretability requirements, and computational constraints of your specific use case.


- Congestion forecasting: XGBoost models for handling complex non-linear relationships in grid load patterns with multiple weather and temporal features

- Grid loss forecasting: Linear regression models when relationships are well-understood and interpretable coefficients are needed for regulatory reporting

- Transport capacity estimation: XGBoost Quantile models to capture uncertainty ranges and provide confidence intervals for capacity planning

- Peak load prediction: XGBoost models with early stopping for capturing seasonal patterns and avoiding overfitting on historical peaks

- Short-term operational forecasts: Linear models for faster inference times when real-time predictions are critical

- Research and experimentation: ARIMA models for baseline comparisons and statistical analysis of time series components


Important Predictors and Weather Dependency
-------------------------------------------


Energy forecasting accuracy depends on several key predictor categories. Historical load patterns (1-day and 7-day lags) typically provide the strongest signals for demand prediction. Weather variables including temperature, wind speed, solar irradiance, and humidity form the second most important category, with their relative importance varying by energy type and season.

Temporal features such as weekday/weekend indicators and holiday flags capture regular consumption patterns. Weather-derived features like extrapolated wind speed at 100m height and normalized wind power curves enhance renewable energy forecasts. The OpenSTEF library automatically applies feature importance analysis to identify the most influential predictors for each specific forecasting task.


.. [DIAGRAM: Feature importance visualization showing weather vs load vs calendar features]


Forecast Quality and Accuracy Metrics
-------------------------------------


OpenSTEF provides comprehensive forecast accuracy metrics to evaluate model performance. Key metrics include Mean Absolute Error (MAE) and Root Mean Square Error (RMSE) for overall accuracy, plus specialized relative metrics like r_mae that normalize errors against load range from previous two weeks. The skill score measures model performance relative to a simple mean baseline, while peak-specific metrics like r_mae_highest and r_mne_highest evaluate forecast quality during high-demand periods.

Good forecast performance typically shows skill scores above zero (outperforming mean baseline), low relative MAE values indicating errors are small compared to load variability, and balanced peak estimation without systematic over or underestimation. The library's backtesting pipeline enables realistic performance evaluation by simulating operational conditions.


.. code-block:: python

   import pandas as pd
   from openstef.metrics.metrics import mae, rmse, r_mae, skill_score

   # Sample forecast and actual data
   realised = pd.Series([100, 120, 95, 110, 130])
   forecast = pd.Series([98, 115, 100, 105, 125])
   mean_baseline = realised.mean()

   # Calculate basic accuracy metrics
   mae_score = mae(realised, forecast)
   rmse_score = rmse(realised, forecast)
   relative_mae = r_mae(realised, forecast)
   skill = skill_score(realised, forecast, mean_baseline)

   print(f"MAE: {mae_score:.2f}")
   print(f"RMSE: {rmse_score:.2f}")
   print(f"Relative MAE: {relative_mae:.2f}")
   print(f"Skill Score: {skill:.2f}")


Fallback Strategies and Robustness
----------------------------------


OpenSTEF handles forecast failures through configurable fallback strategies when models encounter insufficient data or training issues. The library provides two main approaches: EXTREME_DAY strategy uses historical profiles from the most extreme day as a substitute forecast, while RAISE_ERROR immediately fails execution for debugging purposes.

Common failure modes include insufficient input data, invalid data formats, ongoing flatliner conditions, and model training failures. The fallback system automatically marks substituted forecasts with a 'quality' column set to 'substituted' to maintain transparency about forecast reliability and enable downstream decision-making based on data quality indicators.


- Use extreme_day fallback strategy to substitute forecasts with historical profiles from the most extreme day when primary models fail

- Implement raise_error strategy for critical applications where forecast substitution is unacceptable and manual intervention is required

- Deploy flatliner models as simple baseline forecasts that provide constant values based on recent averages

- Configure median models for robust fallback forecasting when sophisticated algorithms encounter data quality issues

- Set up ARIMA models as intermediate fallback option providing time-series based predictions with moderate computational requirements

- Establish linear models as lightweight alternatives when complex machine learning models fail due to feature unavailability


