Key Forecasting Concepts
========================

This page explains the fundamental concepts behind OpenSTEF's forecasting approach through practical examples. Understanding these concepts helps you interpret forecast results, choose appropriate models, and build reliable forecasting systems.

Probabilistic Forecasting with Quantiles
-----------------------------------------

OpenSTEF produces probabilistic forecasts rather than single point predictions. This means you get multiple quantile predictions that represent different confidence levels.

What are quantiles?
^^^^^^^^^^^^^^^^^^^

A quantile represents the probability that the actual value will be below the forecast. For example:

- **P10 (0.1 quantile)**: There's a 10% chance the actual load will be below this value
- **P50 (0.5 quantile)**: The median forecast - 50% chance actual load is above or below
- **P90 (0.9 quantile)**: There's a 90% chance the actual load will be below this value

This gives you a range of possible outcomes instead of a single number:

.. code-block:: python

   from openstef_core.types import Quantile as Q
   from openstef_models.models.forecasting import XGBoostForecaster
   from datetime import timedelta
   
   # Configure forecaster for multiple quantiles
   forecaster = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
   )
   
   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)
   
   # Result contains three quantile predictions for each timestamp
   # predictions['quantile_P10']: Conservative estimate (low)
   # predictions['quantile_P50']: Median forecast
   # predictions['quantile_P90']: Optimistic estimate (high)

Why probabilistic forecasts matter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Different use cases need different quantiles:

- **Congestion management**: Use P90 or P95 to ensure grid capacity isn't exceeded
- **Trading optimization**: Use P50 for expected value calculations
- **Risk assessment**: Compare P10 and P90 to understand forecast uncertainty

The width between P10 and P90 tells you how confident the model is. Narrow ranges indicate high confidence, while wide ranges suggest greater uncertainty (often during extreme weather or unusual conditions).

Forecast calibration
^^^^^^^^^^^^^^^^^^^^

A well-calibrated model produces quantiles that match reality. If your P90 forecast is truly calibrated, actual values should exceed it about 10% of the time. You can verify calibration:

.. code-block:: python

   from openstef_core.visualization import QuantileProbabilityPlotter
   
   plotter = QuantileProbabilityPlotter()
   
   # Compare forecasted vs observed probabilities
   forecasted = [Q(0.1), Q(0.3), Q(0.5), Q(0.9)]
   observed = [Q(0.12), Q(0.28), Q(0.52), Q(0.88)]
   plotter.add_model("XGBoost", forecasted, observed)
   
   fig = plotter.plot(title="Forecast Calibration Analysis")

Points close to the diagonal line indicate good calibration. Systematic deviations suggest the model is over-confident (predictions too narrow) or under-confident (predictions too wide).

Choosing the Right Model
-------------------------

OpenSTEF provides multiple model types optimized for different scenarios. The choice depends on your data characteristics and forecasting requirements.

XGBoost: The default choice
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

XGBoost gradient boosting trees work well for most energy forecasting tasks. They automatically capture non-linear relationships and interactions between features:

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_models.models.forecasting.hyperparams import XGBoostHyperParams
   
   forecaster = XGBoostForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=XGBoostHyperParams(
           n_estimators=100,
           max_depth=6,
           learning_rate=0.1,
       ),
   )

**Best for**: General-purpose forecasting, complex patterns, non-linear relationships between weather and load.

**Limitations**: Requires more training data and computation than linear models.

GBLinear: Fast and interpretable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

GBLinear uses gradient boosting with linear models instead of trees. It's faster to train and easier to interpret:

.. code-block:: python

   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.hyperparams import GBLinearHyperParams
   
   forecaster = GBLinearForecaster(
       quantiles=[Q(0.5), Q(0.1), Q(0.9)],
       horizons=[LeadTime(timedelta(hours=36))],
       hyperparams=GBLinearHyperParams(
           n_steps=1000,
           learning_rate=0.3,
       ),
   )

**Best for**: Linear relationships, limited training data, fast iteration, interpretable coefficients.

**Limitations**: Cannot capture complex non-linear patterns or feature interactions.

LightGBM models
^^^^^^^^^^^^^^^

LightGBM provides both tree-based and linear variants similar to XGBoost/GBLinear but with different optimization strategies. Useful when XGBoost performance is suboptimal.

Model selection guidelines
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start with XGBoost for most use cases. Consider alternatives when:

- **Limited training data** (< 3 months): Try GBLinear
- **Need fast training**: Use GBLinear or LightGBM
- **Highly linear patterns**: GBLinear may match XGBoost accuracy with less complexity
- **XGBoost underperforms**: Try LightGBM variants

Always validate model choice through backtesting on your specific data. See :doc:`../getting_started/tutorials` for backtesting examples.

Important Predictors and Feature Engineering
---------------------------------------------

Understanding which features drive forecast accuracy helps you prioritize data collection and diagnose model issues.

Weather dependency
^^^^^^^^^^^^^^^^^^

Energy demand is highly weather-dependent. The key predictors are:

- **Temperature**: Strongest predictor for most loads (heating/cooling)
- **Wind speed**: Important for wind-exposed areas and wind generation
- **Solar radiation**: Critical for solar generation and cooling loads
- **Pressure and humidity**: Secondary effects on demand

OpenSTEF automatically engineers temporal features from weather data through lag transformations and rolling statistics. The preprocessing pipeline handles this:

.. code-block:: python

   from openstef_core.preprocessing import TransformPipeline, Scaler
   from openstef_core.types import FeatureSelection
   
   preprocessing = TransformPipeline(
       transforms=[
           Scaler(
               method="standard",
               selection=FeatureSelection(
                   include={"temp", "wind", "radiation", "pressure"}
               )
           ),
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
       ],
   )

Energy price signals
^^^^^^^^^^^^^^^^^^^^

Day-ahead electricity prices (APX prices) can improve forecasts for industrial loads that respond to price signals. Include the price column in your input data:

.. code-block:: python

   from openstef_workflows import ForecastingWorkflowConfig
   
   config = ForecastingWorkflowConfig(
       energy_price_column="day_ahead_electricity_price",
       # ... other configuration
   )

Temporal patterns
^^^^^^^^^^^^^^^^^

Time-based features capture recurring patterns:

- **Hour of day**: Daily cycles (morning/evening peaks)
- **Day of week**: Weekday vs weekend patterns
- **Holidays**: Special day behavior
- **Seasonal trends**: Annual cycles

These are automatically generated by OpenSTEF's preprocessing pipeline.

Feature importance
^^^^^^^^^^^^^^^^^^

After training, examine which features the model relies on most. This helps validate that the model learned sensible patterns and identifies data quality issues if unexpected features dominate.

Fallback Strategies for Reliability
------------------------------------

Production forecasting systems need fallback strategies to handle failures gracefully. OpenSTEF is designed as a library, so you implement fallback logic in your deployment code.

Common failure scenarios
^^^^^^^^^^^^^^^^^^^^^^^^

- **Missing weather data**: Weather API unavailable or incomplete forecasts
- **Model training failures**: Insufficient data or numerical issues
- **Prediction errors**: Invalid input data or model corruption
- **Data quality issues**: Gaps, outliers, or sensor failures

Fallback hierarchy
^^^^^^^^^^^^^^^^^^

Implement fallbacks in order of sophistication:

1. **Use previous forecast**: If new prediction fails, return the most recent successful forecast shifted forward
2. **Historical average**: Use same-hour-same-day-of-week average from recent history
3. **Persistence**: Assume load remains constant at last observed value
4. **Fixed capacity**: Return conservative estimate (e.g., P90 from historical distribution)

Example fallback implementation:

.. code-block:: python

   def get_forecast_with_fallback(forecaster, input_data, fallback_store):
       """Attempt forecast with multiple fallback strategies."""
       try:
           # Primary: Generate new forecast
           forecast = forecaster.predict(input_data)
           fallback_store.save_successful_forecast(forecast)
           return forecast
       except PredictionError as e:
           logger.warning(f"Prediction failed: {e}, using fallback")
           
           # Fallback 1: Use previous forecast
           try:
               return fallback_store.get_previous_forecast()
           except NoForecastAvailable:
               pass
           
           # Fallback 2: Historical average
           try:
               return compute_historical_average(
                   input_data.index,
                   lookback_days=28
               )
           except InsufficientData:
               pass
           
           # Fallback 3: Conservative fixed estimate
           return get_conservative_estimate(input_data.index)

Monitoring and alerts
^^^^^^^^^^^^^^^^^^^^^

Track fallback usage to detect systemic issues:

- Alert when fallbacks are used more than X% of the time
- Monitor forecast age (time since last successful prediction)
- Track data quality metrics (missing values, outliers)
- Compare fallback accuracy to normal forecast accuracy

Graceful degradation is better than no forecast. Design your system to always produce a usable output, even if it's lower quality than normal.

See :doc:`../guides/how_to_guides` for deployment patterns that implement robust fallback strategies.

Next Steps
----------

- :doc:`../getting_started/tutorials` - Learn backtesting to validate model choices
- :doc:`../guides/use_cases` - See how concepts apply to specific forecasting scenarios
- :doc:`../guides/faq` - Common questions about forecasting approaches