Key Forecasting Concepts
========================

Understanding the fundamentals behind OpenSTEF's design helps you make better decisions when implementing energy forecasting solutions. This page explains core concepts through practical examples, showing not just how the library works, but why it works that way.

Interpreting Forecast Results
-----------------------------

OpenSTEF produces probabilistic forecasts that go beyond simple point predictions. Understanding what these results mean is crucial for making informed decisions.

Point Forecasts vs Probabilistic Forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A traditional forecast gives you a single number - for example, "tomorrow's peak load will be 150 MW." OpenSTEF provides much richer information:

.. code-block:: python

   # Example forecast output
   forecast_result = {
       'forecast': 150.0,      # Point forecast (median)
       'stdev': 15.0,          # Standard deviation
       'quantile_P10': 125.0,  # 10% chance load will be below this
       'quantile_P50': 150.0,  # Median (same as point forecast)
       'quantile_P90': 175.0,  # 90% chance load will be below this
   }

This tells you not just what to expect, but how confident you should be in that expectation. A forecast of 150 MW ± 5 MW is very different from 150 MW ± 25 MW for operational planning.

Understanding Quantiles and Confidence Intervals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Quantiles represent the probability that actual values will fall below a certain threshold. OpenSTEF uses two methods to generate these:

1. **Standard deviation method**: Assumes forecast errors are normally distributed and uses the trained model's standard deviation to calculate quantiles
2. **Quantile regression**: Trains separate models for each quantile, providing more accurate uncertainty estimates

.. code-block:: python

   # Interpreting quantile forecasts
   if forecast['quantile_P90'] > grid_capacity:
       print("90% chance of exceeding capacity - consider preventive action")
   elif forecast['quantile_P70'] > grid_capacity:
       print("Moderate risk - monitor closely")
   else:
       print("Low risk of capacity issues")

The choice between methods depends on your model type. Quantile regression models (like XGB_QUANTILE) provide more sophisticated uncertainty estimates but require more computational resources.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF offers several model types, each optimized for specific forecasting scenarios. Understanding when to use each one can significantly impact your results.

XGBoost Models: The Workhorses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost models handle most energy forecasting tasks well due to their ability to capture complex non-linear relationships:

.. code-block:: python

   # Standard XGBoost for most use cases
   pj = PredictionJobDataClass(
       model='xgb',
       quantiles=[0.10, 0.30, 0.50, 0.70, 0.90],
       forecast_type="demand"
   )

Use XGBoost when:
- You have sufficient training data (typically 1+ years)
- Load patterns show complex relationships with weather
- You need good performance with minimal tuning

Quantile Models: When Uncertainty Matters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For applications where understanding forecast uncertainty is critical, quantile models provide superior confidence intervals:

.. code-block:: python

   # Quantile regression for better uncertainty estimates
   pj = PredictionJobDataClass(
       model='xgb_quantile',
       quantiles=[0.05, 0.25, 0.50, 0.75, 0.95],
       forecast_type="demand"
   )

Choose quantile models for:
- Grid congestion management where risk assessment is crucial
- Capacity planning where overestimation has high costs
- Applications requiring regulatory compliance with uncertainty reporting

Linear Models: Simple and Interpretable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models work well for stable load patterns with clear weather dependencies:

.. code-block:: python

   # Linear model for simple, interpretable forecasts
   pj = PredictionJobDataClass(
       model='linear',
       forecast_type="demand"
   )

Use linear models when:
- Load patterns are relatively simple and stable
- Model interpretability is more important than accuracy
- You have limited training data
- Computational resources are constrained

Weather Dependency and Important Predictors
-------------------------------------------

Energy consumption patterns are heavily influenced by weather conditions. OpenSTEF automatically engineers weather features to capture these relationships effectively.

Temperature Effects
^^^^^^^^^^^^^^^^^^^

Temperature is typically the strongest weather predictor for energy demand:

.. code-block:: python

   # OpenSTEF automatically creates temperature-based features
   weather_features = [
       'temp',                    # Current temperature
       'temp_mean_24h',          # 24-hour moving average
       'temp_min_24h',           # Daily minimum
       'temp_max_24h',           # Daily maximum
       'heating_degree_days',     # Heating demand indicator
       'cooling_degree_days'      # Cooling demand indicator
   ]

The library calculates heating and cooling degree days automatically, capturing the non-linear relationship between temperature and energy demand. Most energy systems show increased consumption both when it's very cold (heating) and very hot (cooling).

Solar and Wind Effects
^^^^^^^^^^^^^^^^^^^^^^

Renewable energy generation creates complex load patterns:

.. code-block:: python

   # Solar radiation affects both demand and net load
   solar_features = [
       'radiation',               # Current solar radiation
       'radiation_mean_3h',       # Short-term average
       'radiation_cumsum_24h'     # Daily cumulative radiation
   ]
   
   # Wind affects renewable generation
   wind_features = [
       'windspeed_100m',          # Wind at turbine height
       'windspeed_mean_6h',       # Wind persistence
       'winddirection'            # Direction matters for local effects
   ]

High solar radiation typically reduces net electricity demand during daylight hours, while wind patterns affect the variability of renewable generation.

Humidity and Derived Weather Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF calculates additional weather features that capture subtle effects:

.. code-block:: python

   # Automatically calculated humidity features
   humidity_features = [
       'humidity',                # Relative humidity
       'dewpoint',               # Dew point temperature
       'vapour_pressure',        # Water vapor pressure
       'air_density'             # Air density (affects heating/cooling efficiency)
   ]

These derived features help capture how weather conditions affect heating and cooling efficiency, improving forecast accuracy especially during extreme weather events.

Fallback Strategies for Reliability
-----------------------------------

Production forecasting systems need robust fallback mechanisms when primary models fail or data is unavailable. OpenSTEF provides several strategies to ensure continuous operation.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^

The most common fallback strategy uses historical data from similar extreme conditions:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast when primary model fails
   fallback_forecast = generate_fallback(
       forecast_input=current_data,
       load=historical_load_data,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )

This strategy identifies the most extreme historical day with similar characteristics and uses its load profile as a forecast. The forecast quality is marked as 'substituted' to indicate it's not from the primary model.

When to Use Fallback Strategies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Implement fallback strategies for:

- **Data quality issues**: When weather data is missing or corrupted
- **Model failures**: When the primary model produces unrealistic results
- **Extreme conditions**: When current conditions are outside the model's training range
- **System maintenance**: During model retraining or system updates

.. code-block:: python

   # Example fallback logic
   if forecast_quality == 'substituted':
       # Use wider confidence intervals for fallback forecasts
       forecast['quantile_P10'] *= 0.8  # Increase uncertainty
       forecast['quantile_P90'] *= 1.2
       
       # Alert operators about fallback usage
       send_alert("Using fallback forecast - verify manually")

Quality Indicators and Monitoring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF tracks forecast quality to help you understand when fallback strategies are active:

.. code-block:: python

   # Monitor forecast quality in your results
   quality_summary = forecast_df['quality'].value_counts()
   
   if quality_summary.get('substituted', 0) > 0:
       print(f"Warning: {quality_summary['substituted']} forecasts using fallback")
   
   # Track fallback usage over time
   fallback_rate = quality_summary.get('substituted', 0) / len(forecast_df)
   if fallback_rate > 0.05:  # More than 5% fallback usage
       print("High fallback usage - investigate data quality issues")

.. note::
   Fallback strategies are essential for production systems, but high usage rates indicate underlying issues with data quality or model performance that should be investigated.

Making Informed Decisions
-------------------------

Understanding these concepts helps you make better choices when implementing OpenSTEF:

1. **Choose the right model** based on your accuracy needs, computational constraints, and interpretability requirements
2. **Interpret uncertainty correctly** by understanding what quantiles represent and how they're calculated  
3. **Leverage weather dependencies** by ensuring your prediction jobs include appropriate location information
4. **Plan for reliability** by implementing appropriate fallback strategies for your operational context

For detailed implementation guidance, see the :doc:`../getting_started/tutorials` and :doc:`../guides/use_cases` pages.