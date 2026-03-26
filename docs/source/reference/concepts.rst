Forecasting Concepts
====================

Understanding energy forecasting requires grasping several key concepts that determine how well your models perform in practice. This page explains the core ideas behind OpenSTEF's design through practical examples, helping you make informed decisions about model selection, interpret forecast results, and build reliable forecasting systems.

Understanding Forecast Uncertainty
----------------------------------

Energy forecasts are never perfectly accurate, and understanding uncertainty is crucial for operational decisions. OpenSTEF provides two complementary approaches to quantify forecast uncertainty.

Standard Deviation Approach
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For traditional models like XGBoost and LightGBM, OpenSTEF estimates uncertainty using a standard deviation column that assumes normally distributed errors:

.. code-block:: python

   import pandas as pd
   from openstef.model.confidence import add_confidence_interval
   
   # Forecast with uncertainty
   forecast_with_confidence = add_confidence_interval(forecast, pj)
   
   # The result includes:
   # - 'forecast': point prediction
   # - 'stdev': standard deviation of the error
   # - 'quantile_P10', 'quantile_P90': 80% confidence interval

This approach works well when forecast errors follow a normal distribution, which is often the case for aggregated loads over longer time periods.

Quantile Regression
^^^^^^^^^^^^^^^^^^^

For more precise uncertainty estimates, OpenSTEF supports quantile regression models that directly predict confidence intervals:

.. code-block:: python

   from openstef.enums import ModelType
   
   # Train a quantile model
   pj.model = ModelType.XGB_QUANTILE
   
   # This model directly predicts multiple quantiles
   # providing asymmetric confidence intervals

Quantile models are particularly valuable when:

- Forecast errors are not normally distributed
- You need different confidence levels for different operational decisions
- Extreme events (peaks, outages) create asymmetric uncertainty

Interpreting Forecast Results
-----------------------------

Forecast quality depends on your specific use case. A forecast that's excellent for capacity planning might be inadequate for real-time operations.

Accuracy Metrics
^^^^^^^^^^^^^^^^

OpenSTEF provides several metrics to evaluate forecast performance:

.. code-block:: python

   from openstef.metrics.metrics import mae, r_mae, nsme
   
   # Mean Absolute Error - absolute accuracy
   mae_score = mae(realised, forecast)
   
   # Relative MAE - accuracy relative to load variability
   rmae_score = r_mae(realised, forecast)
   
   # Nash-Sutcliffe efficiency - how much better than naive forecast
   nsme_score = nsme(realised, forecast)

The relative MAE (rMAE) is often most meaningful for energy forecasting because it accounts for the natural variability in your load. An rMAE of 5% means your forecast error is 5% of the typical load variation.

Peak Detection Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^

For congestion management, accurately predicting peak events is more important than overall accuracy:

.. code-block:: python

   # Focus on high-load periods
   high_load_mask = realised > realised.quantile(0.95)
   peak_mae = mae(realised[high_load_mask], forecast[high_load_mask])

This targeted evaluation helps you understand whether your model can reliably identify critical periods when grid constraints might be violated.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF offers several model types, each with distinct strengths for different forecasting scenarios.

XGBoost for Complex Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost (``ModelType.XGB``) excels at capturing complex, non-linear relationships:

.. code-block:: python

   from openstef.enums import ModelType
   
   pj.model = ModelType.XGB
   # Best for: Complex load patterns, multiple weather dependencies
   # Trade-offs: Higher computational cost, potential overfitting

Use XGBoost when you have:
- Complex seasonal patterns
- Strong weather dependencies
- Sufficient historical data (>2 years)
- Computational resources for training

Linear Models for Interpretability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models (``ModelType.LINEAR``) provide interpretable results and stable performance:

.. code-block:: python

   pj.model = ModelType.LINEAR
   # Best for: Simple patterns, limited data, need for interpretability
   # Trade-offs: May miss complex relationships

Choose linear models when:
- You need to explain model behavior to stakeholders
- Historical data is limited
- Load patterns are relatively simple
- Model stability is more important than peak accuracy

LightGBM for Speed
^^^^^^^^^^^^^^^^^^

LightGBM (``ModelType.LGB``) offers a balance between accuracy and training speed:

.. code-block:: python

   pj.model = ModelType.LGB
   # Best for: Fast retraining, moderate complexity
   # Trade-offs: Less feature interaction modeling than XGBoost

Important Predictors and Weather Dependency
--------------------------------------------

Understanding which features drive your forecasts helps with model interpretation and data quality monitoring.

Lag Features
^^^^^^^^^^^^

Historical load values are typically the strongest predictors:

.. code-block:: python

   # OpenSTEF automatically generates lag features
   # - Load 24 hours ago (daily pattern)
   # - Load 168 hours ago (weekly pattern)  
   # - Recent load trends (1-6 hours ago)

These features capture the fundamental patterns in energy consumption that persist across time.

Weather Features
^^^^^^^^^^^^^^^^

Weather impact varies significantly by use case:

.. code-block:: python

   # Temperature-sensitive loads (residential heating/cooling)
   # - Temperature, humidity, wind speed
   # - Derived features: heat index, wind chill
   
   # Industrial loads
   # - Often less weather-dependent
   # - May correlate with specific weather conditions

For residential areas, temperature is usually the dominant weather predictor. Industrial loads may show minimal weather dependency except during extreme conditions.

Calendar Features
^^^^^^^^^^^^^^^^^

Time-based features capture human activity patterns:

.. code-block:: python

   # Automatically generated features:
   # - Hour of day, day of week
   # - Holiday indicators
   # - School vacation periods
   # - Seasonal trends

These features are particularly important for loads driven by human activity rather than industrial processes.

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems need robust fallback mechanisms when primary models fail or data quality issues arise.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's default fallback uses historical profiles from similar extreme conditions:

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback forecast
   fallback_forecast = generate_fallback(
       forecast_input=forecast_input,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )

This approach finds the most similar historical day and uses its load profile, ensuring you always have a reasonable forecast even when models fail.

Quality Indicators
^^^^^^^^^^^^^^^^^^

OpenSTEF marks forecasts with quality indicators to help downstream systems make appropriate decisions:

.. code-block:: python

   # Check forecast quality
   if forecast['quality'].iloc[0] == 'substituted':
       # This forecast used fallback strategy
       # Consider wider confidence intervals
       # Alert operators to data quality issues

Monitoring forecast quality helps you identify when model retraining or data source improvements are needed.

Building Robust Systems
^^^^^^^^^^^^^^^^^^^^^^^

Reliable forecasting systems combine multiple strategies:

1. **Primary model**: Your best-performing model for normal conditions
2. **Fallback model**: Simpler, more robust model for degraded conditions  
3. **Historical fallback**: Profile-based approach when models fail entirely
4. **Quality monitoring**: Automated alerts when forecast quality degrades

This layered approach ensures your forecasting system continues operating even when individual components fail, maintaining the reliability required for operational energy systems.