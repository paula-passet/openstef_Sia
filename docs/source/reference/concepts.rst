Key Forecasting Concepts
========================

This page explains the fundamental concepts behind OpenSTEF's forecasting approach through practical examples. Understanding these concepts helps you make better decisions about model selection, interpret forecast results correctly, and build reliable forecasting systems.

Understanding Quantiles and Uncertainty
----------------------------------------

OpenSTEF produces probabilistic forecasts, not just single point predictions. Every forecast includes multiple quantiles that describe the full range of possible outcomes.

When you create a forecast, you get columns like ``quantile_P10``, ``quantile_P50``, and ``quantile_P90``. The P50 quantile is the median prediction—half the time the actual value will be above this, half below. The P10 and P90 quantiles define a prediction interval: 80% of actual values should fall between these bounds.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   
   # Train and predict
   model = ForecastingModel.from_config(config)
   model.fit(training_data)
   forecast = model.predict(test_data)
   
   # Examine uncertainty
   print(forecast.data[['quantile_P10', 'quantile_P50', 'quantile_P90']].head())

OpenSTEF generates quantiles in two ways depending on the model type. For quantile-aware models like XGBoost with quantile regression, each quantile is predicted by a separately trained model that learns the conditional distribution. For other models, quantiles are derived from a learned standard deviation column (``stdev``) assuming normally distributed errors.

The standard deviation is learned during training by analyzing forecast errors across different hours of the day and days of the week. This captures patterns like higher uncertainty during peak hours or weather-dependent periods.

.. note::

   Wider prediction intervals don't mean a bad forecast—they mean honest uncertainty. A forecast that's uncertain but accurate about its uncertainty is more valuable than overconfident predictions.

Choosing the Right Model for Your Use Case
-------------------------------------------

OpenSTEF includes multiple model types, each with different strengths. Understanding when to use each one is crucial for good results.

**XGBoost** is the default choice for most forecasting tasks. It excels at learning complex non-linear relationships between features and can capture interactions between weather, time patterns, and load automatically. XGBoost handles missing data gracefully and provides feature importance metrics to understand what drives your forecasts.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting import XGBoostForecaster
   
   # XGBoost configuration
   config = ModelConfig(
       forecaster=XGBoostForecaster.HyperParams(
           n_estimators=100,
           max_depth=5,
           learning_rate=0.1
       ),
       quantiles=[0.1, 0.5, 0.9]
   )

**Linear quantile regression** is better when you need to predict extreme values or peaks that weren't present in training data. While XGBoost learns to follow historical patterns closely, linear models extrapolate more reliably beyond the training distribution. This makes them valuable for capacity planning or identifying potential overload situations.

.. code-block:: python

   from openstef_models.models.forecasting import LinearQuantileForecaster
   
   # Linear model for peak prediction
   config = ModelConfig(
       forecaster=LinearQuantileForecaster.HyperParams(
           alpha=0.01  # Regularization strength
       ),
       quantiles=[0.1, 0.5, 0.9]
   )

The tradeoff is that linear models are slower to train on large datasets and may underperform on typical days. A practical approach is to use XGBoost for operational forecasts and linear models for capacity planning scenarios.

**Base case forecasters** simply repeat weekly patterns from historical data. They're useful as fallback models or benchmarks to measure how much value your ML models add. If your XGBoost model barely outperforms the base case, you may have data quality issues or insufficient training data.

Important Predictors and Weather Dependency
--------------------------------------------

Understanding which features drive your forecasts helps you identify data quality issues and explains forecast behavior to stakeholders.

OpenSTEF automatically engineers features from your input data. The most important feature types are:

**Lag features** capture recent load patterns. Features like ``load_7d`` (load from 7 days ago) and ``load_1d`` (load from 1 day ago) let the model learn weekly and daily cycles. Short-term lags like ``load_15min`` help predict immediate trends.

**Weather features** are critical for solar and wind forecasting. Temperature affects heating and cooling demand. Radiation and cloud cover drive solar generation. Wind speed determines wind power output. OpenSTEF automatically calculates derived features like dewpoint, air density, and humidity from basic weather inputs.

**Time features** encode hour of day, day of week, and seasonal patterns. These help the model distinguish between weekday and weekend behavior or summer and winter load profiles.

**APX prices** (day-ahead electricity prices) can improve forecasts for industrial loads that respond to price signals, though they're optional for most use cases.

You can inspect feature importance after training:

.. code-block:: python

   # After training a model
   importances = model.get_explainable_components()['forecaster'].feature_importances()
   print(importances.sort_values('importance', ascending=False).head(10))

For individual predictions, SHAP contributions show how each feature influenced a specific forecast:

.. code-block:: python

   # Get feature contributions for predictions
   contributions = model.predict_contributions(test_data)
   
   # Examine contributions for a specific timestamp
   timestamp = test_data.data.index[0]
   print(contributions.data.loc[timestamp].sort_values(ascending=False).head())

If weather features dominate your forecast, you're vulnerable to weather forecast errors. If lag features dominate, you have a stable pattern-based forecast but may be slow to respond to structural changes.

Interpreting Forecast Results
------------------------------

A forecast is more than just predicted values—it includes metadata that tells you how to use it correctly.

**Horizon** indicates how far ahead each prediction looks. A horizon of 0.25 means predicting 15 minutes ahead; 47.0 means 47 hours ahead. Forecast accuracy typically degrades with longer horizons as uncertainty compounds.

.. code-block:: python

   # Analyze accuracy by horizon
   for horizon in forecast.data['horizon'].unique():
       horizon_data = forecast.data[forecast.data['horizon'] == horizon]
       mae = (horizon_data['realised'] - horizon_data['forecast']).abs().mean()
       print(f"Horizon {horizon}: MAE = {mae:.2f}")

**Quality indicators** flag forecasts that may be unreliable. A quality value of ``substituted`` means the forecast came from a fallback strategy rather than the trained model. This happens when input data is missing or the model fails to produce a prediction.

**Forecast start time** (``available_at``) indicates when the forecast was generated. This matters for backtesting—you should only use data that would have been available at forecast time, not future information.

When evaluating forecasts, always segment by horizon and time period. A model that performs well on average may have poor accuracy during peak hours or specific seasons. The evaluation module helps structure this analysis:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import rmse, mae
   
   # Configure evaluation windows
   eval_config = EvaluationConfig(
       metrics=[rmse, mae],
       horizons=[0.25, 1.0, 6.0, 24.0, 47.0]
   )
   
   # Run evaluation
   pipeline = EvaluationPipeline(eval_config, quantiles=[0.1, 0.5, 0.9])
   report = pipeline.evaluate(forecast_data)

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems need fallback strategies for when the primary model fails. OpenSTEF provides mechanisms to ensure you always get a forecast, even when data is missing or models encounter errors.

The **extreme day fallback** strategy finds the most extreme historical day (highest peak load) and uses its daily profile as the forecast. This conservative approach ensures you don't underestimate potential load during data outages.

.. code-block:: python

   from openstef.model.fallback import generate_fallback
   from openstef.enums import FallbackStrategy
   
   # Generate fallback when model fails
   try:
       forecast = model.predict(input_data)
   except Exception as e:
       logger.warning(f"Model prediction failed: {e}")
       fallback = generate_fallback(
           forecast_input=input_data,
           load=historical_load,
           fallback_strategy=FallbackStrategy.EXTREME_DAY
       )
       # Fallback includes quality='substituted' flag
       forecast = fallback

The fallback forecast includes a ``quality`` column set to ``substituted`` so downstream systems know the forecast came from a fallback rather than the trained model. This lets you track fallback frequency and investigate root causes.

For critical applications, consider maintaining multiple models with different training data or algorithms. If your primary XGBoost model fails, fall back to a simpler linear model or base case forecaster before resorting to the extreme day profile.

**Monitoring fallback frequency** is essential. Frequent fallbacks indicate data quality issues, model instability, or infrastructure problems that need attention:

.. code-block:: python

   # Track fallback usage
   substituted_count = (forecast.data['quality'] == 'substituted').sum()
   total_count = len(forecast.data)
   fallback_rate = substituted_count / total_count
   
   if fallback_rate > 0.05:  # More than 5% fallbacks
       logger.error(f"High fallback rate: {fallback_rate:.1%}")

A robust forecasting system combines accurate models with reliable fallback strategies and comprehensive monitoring. Understanding these concepts helps you build systems that perform well not just on average, but in the edge cases that matter most for grid operations.