Key Forecasting Concepts
========================

OpenSTEF is designed around several core forecasting concepts that help you understand and interpret your energy predictions. This page explains the key ideas behind the library's design through practical examples, helping you make informed decisions about model selection, result interpretation, and reliability strategies.

Understanding Forecast Results
------------------------------

When OpenSTEF generates a forecast, it provides more than just a single predicted value. Each forecast includes uncertainty information that helps you understand the reliability of the prediction.

.. code-block:: python

   import pandas as pd
   from openstef.model.trainer import Trainer
   from openstef.data_classes.prediction_job import PredictionJobDataClass
   
   # Train a model and generate forecast
   pj = PredictionJobDataClass(
       id=1, model='xgb', quantiles=[0.10, 0.50, 0.90],
       forecast_type="demand", lat=52.0, lon=5.0
   )
   
   trainer = Trainer()
   model = trainer.train(train_data, pj)
   forecast = model.predict(test_data)
   
   # Examine the forecast structure
   print(forecast.columns)
   # Output: ['forecast', 'stdev', 'quantile_P10', 'quantile_P50', 'quantile_P90']

The forecast DataFrame contains several key columns:

- **forecast**: The point prediction (typically the median)
- **stdev**: Standard deviation indicating forecast uncertainty
- **quantile_P10/P50/P90**: Probabilistic forecasts showing the range of likely outcomes

This rich output allows you to assess not just what will happen, but how confident the model is in that prediction.

Quantiles and Confidence Intervals
----------------------------------

OpenSTEF uses quantiles to express forecast uncertainty in a more nuanced way than simple confidence intervals. Quantiles tell you the probability that the actual value will be below a certain threshold.

.. code-block:: python

   # Interpret quantile forecasts
   forecast_time = "2024-01-15 14:00"
   row = forecast.loc[forecast_time]
   
   print(f"10% chance load will be below: {row['quantile_P10']:.1f} MW")
   print(f"50% chance load will be below: {row['quantile_P50']:.1f} MW") 
   print(f"90% chance load will be below: {row['quantile_P90']:.1f} MW")
   
   # Calculate probability ranges
   prob_range_80 = row['quantile_P90'] - row['quantile_P10']
   print(f"80% of outcomes expected within {prob_range_80:.1f} MW range")

OpenSTEF generates quantiles using two methods depending on the model type:

1. **Default method**: Uses the standard deviation column assuming normally distributed errors
2. **Quantile regression**: Available for quantile-capable models (like XGBoost quantile), providing more accurate uncertainty estimates

The quantile regression approach is particularly valuable for energy forecasting because energy consumption often has asymmetric uncertainty - the potential for extreme high values is often different from extreme low values.

Model Choice for Different Use Cases
------------------------------------

OpenSTEF offers several model types, each suited to different forecasting scenarios:

**XGBoost (xgb)** - The default choice for most energy forecasting tasks:

.. code-block:: python

   pj_xgb = PredictionJobDataClass(
       model='xgb', 
       quantiles=[0.05, 0.25, 0.50, 0.75, 0.95]
   )

XGBoost excels when you have rich feature sets including weather data, calendar features, and historical patterns. It automatically handles feature interactions and non-linear relationships.

**Linear models (linear, linear_quantile)** - For interpretable forecasts:

.. code-block:: python

   pj_linear = PredictionJobDataClass(
       model='linear_quantile',
       quantiles=[0.10, 0.50, 0.90]
   )

Choose linear models when you need to understand exactly how each feature contributes to the forecast, or when working with smaller datasets where XGBoost might overfit.

**ARIMA (arima)** - For time series with strong temporal patterns:

.. code-block:: python

   pj_arima = PredictionJobDataClass(model='arima')

ARIMA works well for loads with consistent seasonal patterns but limited external influences. It's particularly useful when weather data is unavailable.

The choice between models often depends on your data characteristics and interpretability requirements. For most energy forecasting applications, XGBoost provides the best balance of accuracy and robustness.

Weather Dependency and Key Predictors
-------------------------------------

Energy consumption is heavily influenced by weather conditions, and OpenSTEF automatically engineers weather features to capture these relationships:

.. code-block:: python

   # Weather features are automatically calculated from temperature, 
   # humidity, and pressure data
   from openstef.feature_engineering.weather_features import add_humidity_features
   
   # Features include:
   # - Saturation pressure
   # - Vapour pressure  
   # - Dewpoint
   # - Air density
   # - Wind speed at hub height

Understanding weather dependency helps interpret forecast behavior:

- **Temperature**: Primary driver for heating and cooling loads
- **Solar radiation**: Affects both solar generation and cooling demand
- **Wind speed**: Impacts wind generation and building heat loss
- **Humidity**: Influences comfort and HVAC efficiency

The model automatically learns these relationships, but understanding them helps you validate forecast reasonableness. For example, if your forecast shows high electricity demand during a sunny, mild day, investigate whether this reflects air conditioning load or an unusual consumption pattern.

Fallback Strategies for Reliability
-----------------------------------

Even the best forecasting models can fail due to data issues, extreme weather, or system problems. OpenSTEF includes fallback strategies to ensure you always have a forecast:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast when primary model fails
   fallback_forecast = generate_fallback(
       forecast_input=input_data,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )
   
   # Check forecast quality indicator
   print(fallback_forecast['quality'].unique())
   # Output: ['substituted'] - indicates fallback was used

The **EXTREME_DAY** strategy finds the historical day with the most similar extreme conditions and uses that day's load profile. This approach works well because energy consumption patterns tend to be consistent under similar extreme conditions.

Fallback forecasts are marked with a 'substituted' quality flag, allowing downstream systems to handle them appropriately. While less accurate than model-based forecasts, fallback strategies ensure operational continuity when primary forecasting fails.

.. note::
   
   Monitor the frequency of fallback usage - if fallbacks are triggered often, investigate data quality issues or model performance problems.

For more detailed implementation examples, see the :doc:`../getting_started/tutorials` page. To understand how these concepts apply to specific energy forecasting scenarios, visit the :doc:`../guides/use_cases` page.