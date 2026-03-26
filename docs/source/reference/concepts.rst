Key Forecasting Concepts
========================

This page explains the core concepts behind OpenSTEF's forecasting approach through practical examples. Understanding these concepts helps you make better decisions about model selection, interpret forecast results correctly, and build reliable forecasting systems.

Understanding Forecast Results
------------------------------

OpenSTEF forecasts contain multiple types of information beyond just the predicted value. Each forecast includes uncertainty estimates that help you understand how confident the model is in its predictions.

.. code-block:: python

   import pandas as pd
   from openstef.data_classes import ForecastDataset
   
   # Example forecast data with confidence information
   forecast_data = pd.DataFrame({
       'forecast': [100.5, 105.2, 98.7],
       'stdev': [5.2, 6.1, 4.8],
       'quantile_P10': [92.1, 95.8, 91.2],
       'quantile_P50': [100.5, 105.2, 98.7],  # Same as forecast
       'quantile_P90': [108.9, 114.6, 106.2]
   }, index=pd.date_range('2025-01-01', periods=3, freq='h'))
   
   dataset = ForecastDataset(forecast_data, pd.Timedelta(hours=1))
   print(f"Available quantiles: {dataset.quantiles}")

The forecast contains three key components:

- **Point forecast**: The most likely value (quantile_P50)
- **Standard deviation**: Uncertainty estimate assuming normal distribution
- **Quantile forecasts**: More precise confidence intervals

Quantiles and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Quantiles provide a more nuanced view of forecast uncertainty than standard deviation alone. The P10 quantile means there's a 10% chance the actual value will be below this threshold, while P90 means 90% chance it will be below.

.. code-block:: python

   # Interpreting quantile forecasts
   forecast_hour = forecast_data.iloc[0]
   
   print(f"Point forecast: {forecast_hour['forecast']:.1f} MW")
   print(f"90% confidence interval: {forecast_hour['quantile_P10']:.1f} - {forecast_hour['quantile_P90']:.1f} MW")
   print(f"Interval width: {forecast_hour['quantile_P90'] - forecast_hour['quantile_P10']:.1f} MW")

Wide intervals indicate high uncertainty, often during volatile weather conditions or unusual demand patterns. Narrow intervals suggest the model is confident in its prediction.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF offers several model types, each optimized for different forecasting scenarios. The choice depends on your data characteristics, accuracy requirements, and need for uncertainty quantification.

XGBoost Models
^^^^^^^^^^^^^^

XGBoost models excel with complex, non-linear relationships and abundant training data. They automatically capture interactions between weather variables, time patterns, and load behavior.

.. code-block:: python

   from openstef.enums import ModelType
   from openstef.model.model_creator import ModelCreator
   
   # Standard XGBoost for point forecasts
   xgb_model = ModelCreator.create_model(ModelType.XGB)
   
   # XGBoost with quantile regression for uncertainty
   xgb_quantile = ModelCreator.create_model(ModelType.XGB_QUANTILE)

Use XGBoost when:

- You have at least 6-12 months of training data
- Weather dependency is strong and complex
- You need to capture non-linear patterns
- Computational resources allow longer training times

Linear Models
^^^^^^^^^^^^^

Linear models provide interpretable results and work well with limited data or when relationships are primarily linear.

.. code-block:: python

   # Linear model for interpretable forecasts
   linear_model = ModelCreator.create_model(ModelType.LINEAR)
   
   # Linear quantile model for uncertainty with interpretability
   linear_quantile = ModelCreator.create_model(ModelType.LINEAR_QUANTILE)

Choose linear models when:

- Training data is limited (less than 6 months)
- You need to understand which features drive predictions
- Computational resources are constrained
- The load pattern is relatively stable and predictable

ARIMA Models
^^^^^^^^^^^^

ARIMA models focus purely on time series patterns without external features like weather. They're useful for baseline comparisons or when weather data is unavailable.

.. code-block:: python

   # ARIMA for time-series-only forecasting
   arima_model = ModelCreator.create_model(ModelType.ARIMA)

Use ARIMA when:

- Weather data is unreliable or unavailable
- You want a simple baseline model
- The load pattern has strong seasonal components
- External factors have minimal impact

Important Predictors and Weather Dependency
--------------------------------------------

OpenSTEF automatically engineers features from raw weather and time data. Understanding which predictors matter most helps you assess forecast reliability and identify potential issues.

Weather Features
^^^^^^^^^^^^^^^^

Weather variables are transformed into energy-relevant features that better capture their impact on electricity demand.

.. code-block:: python

   from openstef.feature_engineering.weather_features import add_wind_features, add_humidity_features
   
   # Example of weather feature engineering
   raw_weather = pd.DataFrame({
       'windspeed_100m': [8.5, 12.3, 6.1],
       'temperature': [15.2, 18.7, 12.4],
       'humidity': [65, 72, 58],
       'pressure': [1013, 1015, 1011]
   })
   
   # Wind features include power curve transformations
   weather_with_wind = add_wind_features(raw_weather, ['windspeed_100m'])
   
   # Humidity features include dewpoint, air density
   weather_complete = add_humidity_features(weather_with_wind, ['humidity'])

Key weather predictors include:

- **Wind power**: Transformed using turbine power curves, not raw wind speed
- **Temperature**: Both absolute values and deviations from seasonal norms
- **Humidity indices**: Dewpoint, air density, and vapour pressure
- **Solar radiation**: For areas with significant solar generation

Time-Based Features
^^^^^^^^^^^^^^^^^^^

Temporal patterns capture regular human and economic activities that drive electricity demand.

.. code-block:: python

   # Time features are automatically added
   from openstef.feature_engineering.apply_features import apply_features
   
   # Features include:
   # - Hour of day, day of week, month of year
   # - Holiday indicators
   # - Load values from 1 day and 7 days ago
   # - Trend components
   
   enhanced_data = apply_features(raw_data, feature_names=['T-7d', 'T-1d', 'IsWeekDay'])

Historical load values (T-7d, T-1d) are often the strongest predictors, especially for stable consumption patterns.

Fallback Strategies for Reliability
------------------------------------

Real-world forecasting systems must handle missing data, model failures, and extreme conditions. OpenSTEF provides fallback mechanisms to ensure continuous operation.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^^

When insufficient recent data is available, the system can use historical profiles from similar extreme conditions.

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast using extreme day strategy
   fallback_forecast = generate_fallback(
       forecast_input=input_data,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Check forecast quality indicator
   print(fallback_forecast['quality'].unique())  # Shows 'substituted' for fallback periods

The fallback system:

- Identifies the most extreme historical day similar to current conditions
- Uses that day's load profile as the forecast
- Marks the forecast quality as 'substituted'
- Provides continuity when primary models fail

Quality Indicators
^^^^^^^^^^^^^^^^^^

Every forecast includes quality metadata that indicates the reliability of the prediction.

.. code-block:: python

   # Quality levels in forecasts:
   # 'good' - Normal model prediction with sufficient data
   # 'substituted' - Fallback strategy was used
   # 'insufficient_data' - Not enough data for any prediction
   
   quality_summary = forecast_data.groupby('quality').size()
   print(f"Forecast quality distribution:\n{quality_summary}")

Monitor quality indicators to:

- Detect when models are struggling with unusual conditions
- Identify periods requiring manual intervention
- Assess overall system reliability
- Plan maintenance windows for data collection systems

.. note::
   
   For more detailed information on specific topics:
   
   - Model training and evaluation: see :doc:`../getting_started/tutorials`
   - Specific use case implementations: see :doc:`../guides/use_cases`
   - Technical architecture details: see :doc:`architecture`