Forecasting Concepts
====================


Understanding Forecast Results
------------------------------


OpenSTEF forecast outputs contain multiple components that provide comprehensive uncertainty information. The core forecast includes a median prediction (50th percentile) representing the most likely outcome. Standard deviation columns provide uncertainty estimates based on training data variability. Quantile columns offer precise confidence intervals, with names following the format 'quantile_P{percentile}' such as 'quantile_P10' and 'quantile_P90'. These quantiles are generated either through normal distribution assumptions or specialized quantile regression models, depending on the forecasting model type used.


.. code-block:: python

   # Example forecast output with quantiles
   import pandas as pd
   from openstef.model.regressors.xgb import XGBQuantileOpenstfRegressor
   from openstef.pipeline.create_forecast import create_forecast

   # Create forecast with quantiles
   forecast_data = create_forecast(
       pj=pj,
       input_data=forecast_input,
       model=trained_model
   )

   # Access point forecast (median)
   median_forecast = forecast_data['forecast']

   # Access quantile predictions
   quantile_10 = forecast_data['quantile_P10']  # 10th percentile
   quantile_90 = forecast_data['quantile_P90']  # 90th percentile

   # Access standard deviation if available
   if 'stdev' in forecast_data.columns:
       uncertainty = forecast_data['stdev']

   # Filter specific quantiles
   quantile_columns = [col for col in forecast_data.columns if col.startswith('quantile_')]
   quantiles_only = forecast_data[quantile_columns]

   # Calculate 80% confidence interval
   lower_bound = forecast_data['quantile_P10']
   upper_bound = forecast_data['quantile_P90']
   confidence_width = upper_bound - lower_bound


Quantiles and Uncertainty Estimation
------------------------------------


Quantile forecasting enables probabilistic predictions by estimating multiple percentiles of the forecast distribution rather than just point estimates. This is crucial for grid operations as it provides uncertainty bounds for decision-making, allowing operators to assess risks and plan for various scenarios.

OpenSTEF implements quantile regression through specialized models like XGBQuantileOpenstfRegressor that can predict specific quantiles. The library's ConfidenceIntervalApplicator adds quantile predictions to forecasts, generating both standard deviation estimates and precise quantile columns for comprehensive uncertainty characterization.


.. [DIAGRAM: Visualization of forecast quantiles showing prediction intervals around point forecast]


Model Selection and Use Cases
-----------------------------


OpenSTEF provides multiple machine learning algorithms for energy forecasting, with XGBoost quantile models being the primary approach for single-shot, multi-horizon predictions. The library supports different model configurations through prediction jobs that define input data preparation, feature engineering, and training methodologies. Models can be optimized for various forecasting horizons and include confidence estimation capabilities to quantify prediction uncertainty.


- XGBoost models: Best for short to medium-term forecasts (1-48 hours) with structured tabular data and when interpretability is important

- Linear models: Suitable for long-term forecasts, limited training data, or when computational resources are constrained

- Quantile models: Choose when uncertainty quantification is critical for risk assessment or confidence intervals are required

- High-frequency data (15-min intervals): Use XGBoost with extensive feature engineering for capturing complex patterns

- Low-frequency data (hourly/daily): Linear models often sufficient, especially for seasonal patterns and trend analysis

- Limited historical data (<1 year): Prefer simpler linear models to avoid overfitting with complex algorithms

- Rich feature sets available: XGBoost can leverage weather, calendar, and lagged features effectively

- Real-time applications: Consider model complexity vs inference speed requirements for production deployment


Feature Importance and Weather Dependencies
-------------------------------------------


OpenSTEF provides feature importance analysis to help you understand which factors drive your forecasts. Weather features like wind speed, solar irradiance, and temperature often show high importance for energy load predictions. The library automatically adds weather-derived features such as extrapolated wind speed at 100m height and normalized wind power based on turbine-specific power curves.

Feature importance outputs rank predictors by their contribution to forecast accuracy. Historical load patterns (1-day and 7-day lags) typically rank high for baseline consumption, while weather features become more important for renewable energy components. Time-based features like weekday/holiday indicators help capture regular consumption patterns that weather alone cannot explain.


.. image:: _static/images/placeholder_example_feature_importance_plot_showing_weather_variables_impact_on_load_forecast.png
   :alt: Example feature importance plot showing weather variables impact on load forecast
   :align: center


Fallback Strategies and Model Reliability
-----------------------------------------


OpenSTEF provides robust fallback mechanisms when primary forecasting models fail or produce unreliable results. The library implements fallback strategies through the `generate_fallback` function, which automatically substitutes failed forecasts with alternative predictions and marks them with a 'substituted' quality flag.

The primary fallback strategy is `EXTREME_DAY`, which uses the historical profile of the most extreme day from available load data. This approach ensures continuity in forecasting workflows by providing reasonable estimates based on historical patterns when machine learning models encounter issues or insufficient data.

To implement robust forecasting workflows, combine fallback strategies with confidence estimation methods. OpenSTEF automatically adds confidence intervals to forecasts through quantile regression or default methods, providing uncertainty bounds alongside fallback predictions to maintain forecast reliability assessment.


.. note::

   Production forecasting systems should implement robust fallback strategies to handle model failures. OpenSTEF provides fallback mechanisms like extreme_day strategy that uses historical profiles when primary models fail. Monitor forecast quality indicators and implement automated fallback triggers. Always validate model reliability using confidence intervals and track forecast performance metrics in production environments.


