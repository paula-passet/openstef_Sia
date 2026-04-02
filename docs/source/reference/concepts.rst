Key Forecasting Concepts
========================

This page explains the fundamental concepts behind OpenSTEF's forecasting approach. Rather than diving into API details, we focus on the "why" behind the library's design decisions and how to interpret what your forecasts are telling you.

Understanding these concepts will help you make better decisions about model selection, feature engineering, and deployment strategies.


Understanding Forecast Outputs
-------------------------------

When OpenSTEF generates a forecast, it doesn't just give you a single predicted value. It provides a probabilistic view of the future through quantiles.

What quantiles tell you
^^^^^^^^^^^^^^^^^^^^^^^^

A quantile forecast answers the question: "What load value will we stay below with X% probability?" 

For example:

- **q10 (10th percentile)**: There's a 10% chance the actual load will be below this value
- **q50 (50th percentile/median)**: The most likely forecast - half the time actual load will be higher, half the time lower
- **q90 (90th percentile)**: There's a 90% chance the actual load will be below this value

The spread between quantiles tells you about forecast uncertainty. Wide spreads indicate high uncertainty (perhaps due to weather variability or limited training data), while narrow spreads indicate confident predictions.

.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Train a model that outputs multiple quantiles
   model, model_specs = train_model_pipeline(
       pj=prediction_job,
       input_data=train_data,
       quantiles=[0.1, 0.5, 0.9]  # Request 10th, 50th, 90th percentiles
   )
   
   # Make predictions
   forecast = model.predict(test_data)
   
   # Forecast contains columns: forecast_q10, forecast_q50, forecast_q90
   # Wide gap between q10 and q90? High uncertainty
   # Narrow gap? Confident prediction

Why not just use the median?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Grid operators need to plan for different scenarios. The median (q50) tells you the most likely outcome, but:

- **Congestion management**: You care about the q90 or q95 - what happens in high-load scenarios
- **Free capacity estimation**: You might use q10 to be conservative about available space
- **Cost optimization**: Balance between over-provisioning (expensive) and under-provisioning (risky)

Different use cases require different quantiles. OpenSTEF makes it easy to generate multiple quantiles in a single forecast run.


Choosing the Right Model
-------------------------

OpenSTEF supports multiple model types. Each has strengths and weaknesses depending on your use case.

XGBoost: The default choice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost (Extreme Gradient Boosting) is OpenSTEF's default model for good reasons:

- **Handles non-linear relationships**: Captures complex patterns between weather, time, and load
- **Robust to missing data**: Can work with incomplete weather forecasts
- **Feature importance**: Tells you which predictors matter most
- **Quantile regression**: Native support for probabilistic forecasts

Use XGBoost when you have sufficient training data (ideally 1+ years) and need accurate forecasts that adapt to complex patterns.

.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   
   # XGBoost is the default, but you can customize it
   model = XGBQuantileOpenstfRegressor(
       n_estimators=100,
       max_depth=5,
       learning_rate=0.1
   )

Linear models: Fast and interpretable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Linear models assume relationships between predictors and load are linear. They're simpler but have advantages:

- **Fast training**: Train in seconds instead of minutes
- **Interpretable**: Coefficients directly show predictor impact
- **Stable**: Less prone to overfitting with limited data
- **Lightweight**: Minimal memory and compute requirements

Use linear models when you need fast retraining, have limited computational resources, or want maximum interpretability.

.. code-block:: python

   from openstef.model.regressors import LinearQuantileOpenstfRegressor
   
   model = LinearQuantileOpenstfRegressor()
   # Much faster training, but may miss non-linear patterns

When to use each model type
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Choose XGBoost when:**

- You have 1+ years of training data
- Load patterns are complex (e.g., industrial customers with irregular schedules)
- Computational resources are available
- Accuracy is the top priority

**Choose linear models when:**

- Training data is limited (< 6 months)
- You need frequent retraining (e.g., daily)
- Interpretability is critical for stakeholder communication
- Running on resource-constrained systems

**Start with XGBoost.** It works well in most scenarios. Switch to linear models only if you have a specific reason.


Important Predictors and Weather Dependency
--------------------------------------------

Understanding which features drive your forecasts helps you improve data collection and interpret model behavior.

Time-based features
^^^^^^^^^^^^^^^^^^^

These capture regular patterns:

- **Hour of day**: Load typically peaks in morning and evening for residential areas
- **Day of week**: Weekdays differ from weekends
- **Month/season**: Heating in winter, cooling in summer
- **Holidays**: Special days with different consumption patterns

OpenSTEF automatically generates these features from timestamps. They're the foundation of every forecast.

Weather features
^^^^^^^^^^^^^^^^

Weather is crucial for temperature-dependent loads:

- **Temperature**: Strongest predictor for heating/cooling loads
- **Wind speed**: Important for wind-heavy generation areas
- **Solar radiation**: Drives solar generation and cooling loads
- **Cloud cover**: Affects solar generation

The importance of weather varies by use case:

- **Residential areas**: Highly weather-dependent (heating/cooling)
- **Industrial loads**: Often weather-independent (continuous processes)
- **Solar generation**: Extremely weather-dependent
- **Grid losses**: Moderate weather dependency (temperature affects resistance)

.. code-block:: python

   # Check which features matter most for your forecast
   from openstef.feature_engineering.feature_applicator import TrainFeatureApplicator
   
   # After training, inspect feature importance
   importance = model.feature_importances_
   feature_names = model.feature_names_
   
   # Sort by importance
   sorted_features = sorted(
       zip(feature_names, importance),
       key=lambda x: x[1],
       reverse=True
   )
   
   print("Top 10 most important features:")
   for name, score in sorted_features[:10]:
       print(f"{name}: {score:.3f}")

If weather features dominate, ensure you have high-quality weather forecasts. If time features dominate, weather may not be critical for your use case.

Lagged features
^^^^^^^^^^^^^^^

Recent history helps predict the near future:

- **Load lags**: Yesterday's load at the same hour predicts today's load
- **Weather lags**: Recent temperature trends matter for thermal inertia

OpenSTEF automatically creates lag features. They're especially valuable for very short-term forecasts (next few hours).


Fallback Strategies for Reliability
------------------------------------

Production forecasting systems must handle failures gracefully. OpenSTEF provides multiple layers of fallback.

Why fallbacks matter
^^^^^^^^^^^^^^^^^^^^

Real-world systems face many failure modes:

- Weather API is down or delayed
- Model training fails due to data quality issues
- New model performs worse than expected
- Input data is missing or corrupted

Without fallbacks, your system stops producing forecasts. With fallbacks, you degrade gracefully.

Model fallback hierarchy
^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF supports a fallback chain:

1. **Primary model**: Your latest trained model (e.g., XGBoost)
2. **Secondary model**: A simpler backup model (e.g., linear model)
3. **Historical average**: Simple average of same hour/day from historical data

.. code-block:: python

   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   try:
       # Try primary model
       forecast = create_forecast_pipeline(
           pj=prediction_job,
           model=primary_model,
           input_data=forecast_input
       )
   except Exception as e:
       print(f"Primary model failed: {e}")
       try:
           # Fall back to simpler model
           forecast = create_forecast_pipeline(
               pj=prediction_job,
               model=backup_model,
               input_data=forecast_input
           )
       except Exception as e:
           print(f"Backup model failed: {e}")
           # Fall back to historical average
           forecast = calculate_historical_average(
               historical_data,
               forecast_horizon
           )

Data quality fallbacks
^^^^^^^^^^^^^^^^^^^^^^

When input data is problematic:

- **Missing weather data**: Use last available forecast or climatological averages
- **Outliers in recent load**: Apply outlier detection and interpolation
- **Incomplete training data**: Extend training window or use transfer learning from similar locations

The key principle: **Always produce a forecast.** A simple forecast based on historical patterns is better than no forecast at all.

Monitoring and alerting
^^^^^^^^^^^^^^^^^^^^^^^

Track when fallbacks activate:

- Log every fallback event with reason
- Alert operators when primary model fails repeatedly
- Monitor forecast quality metrics to detect degradation

This helps you identify systemic issues before they impact operations.


Interpreting Forecast Quality
------------------------------

How do you know if your forecasts are good enough?

Skill score: The key metric
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Skill score compares your model to a naive baseline (typically persistence or historical average):

.. code-block:: python

   skill_score = 1 - (model_error / baseline_error)

- **Skill score = 0**: Your model is no better than the baseline
- **Skill score = 0.5**: Your model reduces error by 50% vs baseline
- **Skill score < 0**: Your model is worse than the baseline (something is wrong!)

For short-term energy forecasting, typical skill scores:

- **Excellent**: > 0.7 (70% error reduction)
- **Good**: 0.5 - 0.7
- **Acceptable**: 0.3 - 0.5
- **Poor**: < 0.3

Skill scores vary by forecast horizon. Expect higher scores for near-term forecasts (next few hours) and lower scores for longer horizons (2-3 days ahead).

Quantile calibration
^^^^^^^^^^^^^^^^^^^^^

For probabilistic forecasts, check if quantiles are well-calibrated:

- If actual load exceeds q90 more than 10% of the time, your q90 is too low
- If actual load exceeds q90 less than 10% of the time, your q90 is too high

Well-calibrated quantiles are essential for reliable risk assessment.

Seasonal patterns
^^^^^^^^^^^^^^^^^

Forecast quality often varies by season:

- **Winter/summer**: Higher errors due to extreme weather sensitivity
- **Spring/fall**: Lower errors with mild, stable weather

Track metrics by season to understand when your model struggles and where to focus improvement efforts.


Next Steps
----------

Now that you understand the key concepts, explore:

- :doc:`/getting_started/tutorials` - Apply these concepts in hands-on examples
- :doc:`/guides/use_cases` - See how concepts apply to specific forecasting scenarios
- :doc:`/guides/faq` - Common questions about forecasting with OpenSTEF