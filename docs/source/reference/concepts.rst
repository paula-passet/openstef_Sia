Key Forecasting Concepts
========================

Understanding how OpenSTEF works requires grasping several fundamental forecasting concepts. This page explains the key ideas through practical examples, helping you make informed decisions about model selection, interpret results correctly, and build reliable forecasting systems.

Interpreting Forecast Results
-----------------------------

When OpenSTEF generates a forecast, it provides more than just a single predicted value. Understanding what each component means is crucial for making operational decisions.

.. code-block:: python

   import pandas as pd
   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType
   
   # After training and forecasting (see quickstart for full example)
   forecast_result = model.predict(forecast_input)
   
   # Typical forecast result columns:
   # - 'forecast': the main prediction
   # - 'stdev': standard deviation indicating uncertainty
   # - 'quantile_P10', 'quantile_P90': 10th and 90th percentiles
   # - 'quality': indicates if values are 'substituted' (fallback used)
   
   print(forecast_result.columns)
   # ['forecast', 'stdev', 'quantile_P10', 'quantile_P50', 'quantile_P90', 'quality']

The ``forecast`` column contains the primary prediction - typically the median (50th percentile) for most use cases. The ``stdev`` column provides a measure of uncertainty, while quantile columns give you the full probability distribution.

For congestion management, you might focus on the 90th percentile (``quantile_P90``) to ensure grid capacity isn't exceeded. For energy trading, the median forecast might be most relevant for volume planning.

Quantiles and Confidence Intervals
----------------------------------

OpenSTEF provides uncertainty estimates through two complementary approaches: standard deviation and quantile regression.

The standard deviation approach assumes forecast errors follow a normal distribution. This works well for many energy forecasting scenarios but can miss the asymmetric nature of some loads (like solar generation on cloudy days).

.. code-block:: python

   # Using standard deviation for confidence intervals
   forecast_mean = forecast_result['forecast']
   forecast_std = forecast_result['stdev']
   
   # 95% confidence interval assuming normal distribution
   upper_95 = forecast_mean + 1.96 * forecast_std
   lower_95 = forecast_mean - 1.96 * forecast_std

Quantile regression provides more accurate uncertainty estimates by training separate models for different percentiles. This captures the true shape of forecast uncertainty without distributional assumptions.

.. code-block:: python

   from openstef.enums import ModelType
   
   # Train a quantile model for better uncertainty estimates
   model_creator = ModelCreator()
   quantile_model = model_creator.create_model(ModelType.XGB_QUANTILE)
   
   # Quantile models provide direct estimates for specific percentiles
   # No distributional assumptions needed

For critical applications like grid congestion management, quantile regression typically provides more reliable uncertainty estimates, especially for extreme events.

Model Selection for Different Use Cases
---------------------------------------

OpenSTEF offers several model types, each suited to different forecasting scenarios. Understanding when to use each type can significantly impact forecast quality.

**Linear models** work well for stable, predictable loads with clear seasonal patterns. They're interpretable and fast but may miss complex non-linear relationships.

**XGBoost models** excel at capturing complex patterns and interactions between features. They handle missing data well and often provide the best accuracy for energy forecasting tasks.

**Quantile models** (XGB_QUANTILE, LINEAR_QUANTILE) are essential when uncertainty quantification matters more than point accuracy - particularly for congestion management and risk assessment.

.. code-block:: python

   # For congestion management - uncertainty matters most
   congestion_model = model_creator.create_model(ModelType.XGB_QUANTILE)
   
   # For energy trading - point accuracy is key
   trading_model = model_creator.create_model(ModelType.XGB)
   
   # For simple, stable loads - interpretability matters
   simple_model = model_creator.create_model(ModelType.LINEAR)

The **ARIMA model** handles time series with strong autocorrelation but requires stationary data. **Median models** provide robust baselines by using historical patterns. **Flatliner models** simply repeat the last known value - useful for very short-term forecasts or as fallbacks.

Weather Dependency and Key Predictors
-------------------------------------

Energy consumption and generation patterns are heavily influenced by weather conditions. OpenSTEF's feature engineering automatically captures these relationships, but understanding them helps with model interpretation and troubleshooting.

Temperature drives heating and cooling demand, creating strong correlations with total load. Solar irradiance directly affects photovoltaic generation, while wind speed impacts wind turbines. Cloud cover influences both solar generation and temperature patterns.

.. code-block:: python

   # After training, examine feature importance
   feature_importance = model.feature_importances_
   
   # Common high-importance features:
   # - T-1h, T-24h: recent load values (autoregressive features)
   # - temp, radiation: weather conditions
   # - hour, day_of_week: temporal patterns
   # - holiday indicators: special day effects

Weather forecasts become less reliable beyond 7 days, which naturally limits OpenSTEF's effective forecasting horizon. The library focuses on short-term forecasting (hours to about a week) where weather predictions maintain sufficient accuracy for energy applications.

For loads with minimal weather dependency (like industrial processes), autoregressive features (previous load values) often dominate. For weather-sensitive loads (residential heating/cooling), weather features become critical predictors.

Fallback Strategies for Reliability
-----------------------------------

Production forecasting systems must handle situations where normal prediction fails - missing data, model errors, or extreme conditions. OpenSTEF provides fallback mechanisms to ensure continuous operation.

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # When primary forecast fails, use fallback
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Check forecast quality to identify fallback usage
   substituted_periods = forecast_result[forecast_result['quality'] == 'substituted']

The **extreme day** strategy identifies the historical day with the highest peak load and uses its daily pattern as a fallback. This conservative approach ensures grid capacity isn't exceeded during forecast failures.

Fallback forecasts are marked with ``quality='substituted'`` so downstream systems can identify and handle them appropriately. In production, you might trigger alerts when fallback usage exceeds certain thresholds, indicating data quality issues or model problems.

.. note::
   
   Fallback strategies are particularly important for congestion management where forecast failures could lead to grid instability. Always monitor the ``quality`` column in production deployments.

The extreme day approach works well for most energy applications because it provides a conservative estimate during uncertainty. However, it may overestimate load during normal conditions, so balancing reliability with accuracy requires careful consideration of your specific use case.