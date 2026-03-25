Now I'll create a comprehensive concepts documentation page that explains key forecasting concepts through practical examples.

==============================
Key Forecasting Concepts
==============================

Understanding how OpenSTEF approaches forecasting helps you make better decisions about model selection, interpret results correctly, and build reliable forecasting systems. This page explains the core concepts through practical examples and real-world scenarios.

Understanding Forecast Results
------------------------------

OpenSTEF produces probabilistic forecasts that go beyond simple point predictions. Each forecast includes uncertainty estimates that help you understand the confidence level of predictions.

Point Predictions and Uncertainty
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every OpenSTEF forecast includes a point prediction (the most likely value) and uncertainty estimates expressed through quantiles and standard deviations:

.. code-block:: python

   # A typical forecast result includes multiple columns
   forecast_result = model.predict(input_data)
   print(forecast_result.columns)
   # ['forecast', 'stdev', 'quantile_0.05', 'quantile_0.25', 
   #  'quantile_0.75', 'quantile_0.95']

The ``forecast`` column contains the point prediction, while quantile columns show the range of likely outcomes. For example, ``quantile_0.05`` means there's a 5% chance the actual value will be below this threshold.

Interpreting Quantiles in Practice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Consider a substation forecast predicting peak load for grid congestion management:

.. code-block:: python

   # Peak hour forecast example
   peak_forecast = {
       'forecast': 85.2,      # Most likely load (MW)
       'quantile_0.95': 92.1, # 95% confidence upper bound
       'quantile_0.05': 78.3, # 5% confidence lower bound
       'stdev': 4.2           # Standard deviation
   }

This tells you:

- The expected peak load is 85.2 MW
- There's a 90% chance the actual load will be between 78.3 and 92.1 MW
- There's only a 5% chance of exceeding 92.1 MW (critical for congestion planning)

For congestion management, you might trigger preventive measures when the 95th percentile exceeds your capacity limit, even if the point forecast doesn't.

Model Selection for Different Use Cases
----------------------------------------

OpenSTEF supports various forecasting scenarios, each requiring different modeling approaches based on aggregation level, accuracy requirements, and business context.

Congestion Management Forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These forecasts prioritize accuracy during peak periods and handle high variability at individual connection points:

.. code-block:: python

   from openstef.model.model_creator import ModelCreator
   from openstef.enums import ModelType
   
   # Configure for congestion forecasting
   congestion_model_spec = {
       'model_type': ModelType.XGB_QUANTILE,
       'hyper_params': {
           'objective': 'reg:quantileerror',
           'quantile_alpha': [0.05, 0.25, 0.5, 0.75, 0.95],
           'max_depth': 8,  # Higher complexity for peak detection
           'n_estimators': 200
       }
   }

Quantile models excel here because they provide the uncertainty estimates needed for risk-based decision making during congestion events.

Transport Forecasts
^^^^^^^^^^^^^^^^^^^

Transport forecasts require balanced accuracy across all time periods for coordination with upstream/downstream grid operators:

.. code-block:: python

   # Transport forecast configuration
   transport_model_spec = {
       'model_type': ModelType.XGB,  # Standard regression
       'hyper_params': {
           'objective': 'reg:squarederror',
           'max_depth': 6,  # Moderate complexity
           'n_estimators': 150,
           'learning_rate': 0.1
       }
   }

Standard regression models work well because transport forecasts operate at medium aggregation levels where patterns are more predictable.

Grid Loss Forecasts
^^^^^^^^^^^^^^^^^^^^

Grid losses are highly aggregated and follow system-wide patterns with minimal weather dependency:

.. code-block:: python

   # Grid loss forecast - emphasizes temporal patterns
   loss_model_spec = {
       'model_type': ModelType.LINEAR,  # Simple model for aggregated data
       'feature_modules': [
           'temporal',  # Strong emphasis on time patterns
           'lag',       # Historical patterns
           # Note: weather features less important at this aggregation
       ]
   }

Weather Dependency and Feature Importance
------------------------------------------

Understanding when and how weather affects your forecasts is crucial for model configuration and performance expectations.

Weather Impact by Aggregation Level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Weather dependency varies dramatically with aggregation level:

.. code-block:: python

   # Individual customer (low aggregation) - high weather sensitivity
   individual_features = [
       'temperature',
       'irradiance', 
       'windspeed',
       'humidity',
       'temperature_lag_1h',  # Recent weather matters
   ]
   
   # Regional aggregate (high aggregation) - reduced weather sensitivity  
   regional_features = [
       'temperature_daily_avg',  # Smoothed weather patterns
       'temporal',               # Dominant system patterns
       'lag',                   # Historical behavior
       # Individual weather variations cancel out
   ]

Solar and Wind Forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Renewable energy forecasts are heavily weather-dependent and require specialized feature engineering:

.. code-block:: python

   # Solar forecast configuration
   solar_config = {
       'forecast_type': 'solar',
       'feature_modules': [
           'weather',      # Critical for solar
           'solar',        # Solar-specific calculations
           'temporal',     # Day/night cycles
       ]
   }
   
   # The solar module adds features like:
   # - solar_elevation_angle
   # - clear_sky_irradiance  
   # - cloud_cover_impact

Weather features become less important as you aggregate more customers, but remain critical for renewable energy components regardless of scale.

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems need robust fallback mechanisms when primary models fail or insufficient data is available.

Extreme Day Fallback
^^^^^^^^^^^^^^^^^^^^^

The most common fallback strategy uses historical patterns from extreme conditions:

.. code-block:: python

   from openstef.enums import FallbackStrategy
   from openstef.model.fallback import generate_fallback
   
   # Configure fallback in prediction job
   prediction_job.fallback_strategy = FallbackStrategy.EXTREME_DAY
   
   # Fallback is automatically triggered when:
   # - Insufficient training data
   # - Model prediction fails
   # - Data quality issues detected
   
   fallback_forecast = generate_fallback(
       forecast_input=input_data,
       load=historical_load,
       fallback_strategy=FallbackStrategy.EXTREME_DAY
   )

The extreme day strategy identifies the most similar historical day with extreme conditions and uses its load profile as the forecast. This provides a reasonable estimate when sophisticated models cannot operate.

Quality Indicators
^^^^^^^^^^^^^^^^^^

OpenSTEF marks fallback forecasts in the quality column:

.. code-block:: python

   # Check forecast quality
   print(forecast_result['quality'].value_counts())
   # normal        8640  # Regular model predictions
   # substituted     96  # Fallback predictions used

This transparency allows downstream systems to apply different confidence levels or decision thresholds based on forecast quality.

Base Case Models
^^^^^^^^^^^^^^^^

For critical applications, consider running base case models alongside sophisticated models:

.. code-block:: python

   from openstef.enums import ModelType
   
   # Simple base case using weekly patterns
   base_case_config = {
       'model_type': ModelType.BASECASE,
       'feature_modules': ['lag']  # Uses historical patterns only
   }

Base case models provide a reliability floor - they're simple enough to almost always work, giving you a baseline forecast even when complex models fail.

Choosing the Right Approach
----------------------------

Your forecasting approach should match your specific requirements:

**For critical infrastructure (congestion management):**
- Use quantile models for uncertainty estimates
- Implement multiple fallback layers
- Monitor forecast quality indicators
- Focus accuracy on peak periods

**For operational planning (transport forecasts):**
- Standard regression models often sufficient
- Emphasize overall accuracy over peak detection
- Simpler fallback strategies acceptable

**For financial optimization (grid losses):**
- Consider cost-weighted error metrics
- Weather features less critical
- Temporal patterns dominate

The key is understanding your use case requirements and configuring OpenSTEF's flexible architecture accordingly. Each component - from model selection to fallback strategies - should align with your specific accuracy needs, risk tolerance, and operational constraints.