```rst
Concept Explanations
====================

This page explains key forecasting concepts used in OpenSTEF. Understanding these concepts will help you interpret forecast results, choose appropriate models, and make informed decisions based on OpenSTEF's output.

.. note::
   OpenSTEF is a Python library for building forecasting applications, not a pre-trained model or deployable application. You use these concepts when building your own forecasting system with OpenSTEF.

Interpreting Forecast Results
-----------------------------

OpenSTEF produces probabilistic forecasts that provide more information than simple point predictions. Understanding how to read and interpret these results is crucial for effective decision-making.

Forecast Output Format
^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF forecasts typically include:

- **Point forecast**: The most likely value (usually the median or P50 quantile)
- **Quantile forecasts**: Multiple probability levels (e.g., P10, P25, P50, P75, P90)
- **Forecast horizon**: Time periods covered (typically 24-48 hours ahead)
- **Resolution**: Time granularity (commonly 15-minute intervals)

.. code-block:: python

   # Example forecast output structure
   forecast_result = {
       'forecast': pd.DataFrame({
           'datetime': [...],
           'forecast': [...],      # Point forecast (P50)
           'quantile_P10': [...],  # 10th percentile
           'quantile_P90': [...],  # 90th percentile
       })
   }

Understanding Forecast Horizons
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF supports single-shot, multi-horizon forecasting:

- **Short-term**: 1-48 hours ahead (primary focus)
- **Resolution**: Typically 15-minute intervals for grid applications
- **Accuracy degradation**: Forecasts become less accurate further into the future
- **Weather dependency**: Longer horizons rely more heavily on weather forecasts

.. [DIAGRAM: Forecast accuracy vs horizon showing typical degradation pattern]

Quantiles and Confidence Intervals
-----------------------------------

Probabilistic forecasting provides uncertainty estimates alongside predictions, enabling risk-aware decision making.

What Are Quantiles?
^^^^^^^^^^^^^^^^^^^

Quantiles represent the probability that the actual value will be below a given threshold:

- **P10 (10th percentile)**: 10% chance actual value will be below this level
- **P50 (50th percentile/median)**: 50% chance actual value will be below this level  
- **P90 (90th percentile)**: 90% chance actual value will be below this level

The range between P10 and P90 represents an 80% confidence interval.

Confidence Estimation Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides two methods for confidence estimation:

1. **Quantile Regression**: Direct prediction of quantiles during model training
2. **Conformal Prediction**: Post-hoc uncertainty estimation using historical residuals

.. [DIAGRAM: Comparison of quantile regression vs conformal prediction methods]

.. note::
   The choice between methods depends on your use case. Quantile regression is integrated into the model training, while conformal prediction can be applied to any point forecast.

Using Quantiles for Decision Making
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Different quantiles serve different purposes:

- **P10**: Conservative planning (low probability of exceeding capacity)
- **P50**: Balanced planning (median expectation)
- **P90**: Optimistic planning (high probability of sufficient capacity)

For congestion management, you might use P90 to ensure adequate capacity, while for cost optimization, P50 might be more appropriate.

Model Choice and Use Cases
---------------------------

OpenSTEF supports multiple machine learning models, each with strengths for different scenarios.

Available Models
^^^^^^^^^^^^^^^^

- **XGBoost**: Gradient boosting, excellent for complex patterns
- **LightGBM**: Fast gradient boosting, good for large datasets
- **Linear models**: Simple, interpretable, fast training

Model Performance by Aggregation Level
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Model effectiveness varies with data aggregation:

**High Aggregation (System-level)**
- Linear models often perform well
- Weather predictors have reduced impact
- Temporal patterns dominate
- Example: Grid losses forecasting

**Medium Aggregation (Substation-level)**
- Tree-based models (XGBoost, LightGBM) excel
- Good balance of predictability and granularity
- Example: Transport forecasts

**Low Aggregation (Individual customers)**
- All models face challenges due to behavioral variability
- Ensemble approaches recommended
- Example: Individual customer forecasts for congestion management

Automatic Model Selection
^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF can automatically select the best model based on:

- Historical performance on validation data
- Cross-validation results
- Use case requirements (accuracy vs speed)

.. code-block:: python

   # Example of model configuration
   prediction_job = PredictionJob(
       model='auto',  # Automatic selection
       # or specify: 'xgb', 'lgb', 'linear'
       quantiles=[0.1, 0.5, 0.9]
   )

Important Predictors and Weather Dependency
--------------------------------------------

Understanding which features drive forecasts helps interpret results and troubleshoot issues.

Key Predictor Categories
^^^^^^^^^^^^^^^^^^^^^^^^

**Temporal Features**
- Hour of day, day of week, month of year
- Holiday indicators and special events
- Historical load patterns (lag features)

**Weather Features**
- Temperature (most important for heating/cooling loads)
- Solar irradiance (for solar generation and temperature-driven demand)
- Wind speed (for wind generation)
- Humidity, cloud cover (secondary effects)

**Load History Features**
- Recent load values (autoregressive features)
- Same time previous day/week (seasonal patterns)
- Rolling averages and trends

Weather Dependency by Use Case
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**High Weather Dependency**
- Individual customer forecasts
- Heating/cooling dominated loads
- Solar and wind generation forecasts

**Medium Weather Dependency**
- Substation-level aggregated loads
- Mixed residential/commercial areas

**Low Weather Dependency**
- Highly aggregated system loads
- Industrial-dominated areas
- Grid losses (system-level patterns dominate)

Feature Importance and Explainability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides built-in explainability features:

- **SHAP values**: Understand individual prediction drivers
- **Feature importance**: Identify most influential predictors
- **Partial dependence plots**: Visualize feature relationships

.. code-block:: python

   # Example of accessing feature importance
   model_result = train_model(train_data, prediction_job)
   importance = model_result.feature_importance
   shap_values = model_result.explain_forecast(forecast_input)

Fallback Strategies
-------------------

Robust forecasting systems need fallback mechanisms when primary models fail or data is unavailable.

Handling Missing Data
^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes several strategies for missing data:

**Weather Data Missing**
- Use historical weather patterns
- Interpolation from nearby weather stations
- Reduced model complexity (temporal features only)

**Load History Missing**
- Use seasonal patterns from previous years
- Aggregate patterns from similar locations
- Simple persistence models

**Model Failure Scenarios**
- Automatic fallback to simpler models
- Historical average patterns
- Persistence forecasts (last known value)

Degraded Mode Operation
^^^^^^^^^^^^^^^^^^^^^^^

When optimal conditions aren't available:

1. **Reduced feature set**: Use only available predictors
2. **Simplified models**: Fall back to linear models or persistence
3. **Increased uncertainty**: Wider confidence intervals to reflect reduced accuracy
4. **Graceful degradation**: Maintain service with reduced quality rather than complete failure

Built-in Resilience Features
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes several resilience mechanisms:

- **Data validation**: Automatic detection of anomalies and outliers
- **Model validation**: Performance monitoring and automatic retraining triggers
- **Fallback chains**: Multiple levels of fallback strategies
- **Error handling**: Graceful handling of edge cases and data issues

.. note::
   Fallback strategies should be tested regularly to ensure they work when needed. Consider implementing monitoring and alerting for when fallback modes are activated.

.. [DIAGRAM: Fallback strategy decision tree showing progression from optimal to degraded modes]
```