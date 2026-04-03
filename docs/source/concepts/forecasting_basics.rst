Short-Term Energy Forecasting Basics
=====================================

Short-term energy forecasting predicts electricity demand or generation from minutes to a few days ahead. This page explains what distinguishes short-term forecasting from other time horizons, the key concepts of lead time and forecast frequency, and how OpenSTEF approaches these challenges.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting focuses on predictions with horizons ranging from 15 minutes to 48 hours ahead. Unlike long-term forecasting (months or years), which supports strategic planning and capacity investments, short-term forecasting serves operational decision-making:

- **Grid operations**: Balancing supply and demand in real-time
- **Energy trading**: Day-ahead and intraday market participation
- **Demand response**: Triggering load adjustments based on predicted peaks
- **Renewable integration**: Managing variable solar and wind generation

The defining characteristic is the need for high accuracy at fine temporal resolution. A 5% error in a yearly forecast might be acceptable for capacity planning, but the same error in a 15-minute-ahead forecast could cause grid instability or significant trading losses.

Key Temporal Concepts
---------------------

Understanding short-term forecasting requires clarity on three temporal concepts:

**Forecast Horizon (Lead Time)**

The horizon is how far into the future you're predicting. In OpenSTEF, this is represented by the ``LeadTime`` type, typically expressed as a ``timedelta``:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime
   
   # Predict 15 minutes ahead
   horizon_15min = LeadTime(timedelta(minutes=15))
   
   # Predict 6 hours ahead
   horizon_6h = LeadTime(timedelta(hours=6))
   
   # Predict 47 hours ahead (day-ahead + buffer)
   horizon_47h = LeadTime(timedelta(hours=47))

Models in OpenSTEF can be configured to predict multiple horizons. The accuracy typically degrades as the horizon increases—predicting 15 minutes ahead is easier than predicting 24 hours ahead because less uncertainty accumulates.

**Available At Time**

This is when the input data becomes available for making a forecast. In real-world systems, not all data arrives instantly. Weather forecasts might be published every 6 hours, smart meter data might lag by 15 minutes, and sensor readings might have varying delays.

OpenSTEF explicitly models data availability through the ``available_at`` metadata in datasets. This ensures forecasts only use information that would actually be available at prediction time, preventing data leakage during model training.

**Forecast Frequency**

How often you generate new forecasts. Common patterns include:

- **Continuous**: New forecast every 15 minutes for rolling operations
- **Hourly**: Updated predictions each hour for intraday trading
- **Daily**: Single day-ahead forecast for next-day market participation

The frequency depends on your use case and the cost of computation. More frequent forecasts provide fresher information but require more resources.

Short-Term vs. Long-Term Forecasting
-------------------------------------

The distinction between short-term and long-term forecasting isn't just about the time horizon—it fundamentally changes what matters:

**Data Granularity**

Short-term forecasting requires high-resolution data (15-minute or hourly intervals). Long-term forecasting typically works with daily or monthly aggregates. This means short-term models process much larger datasets and must handle more noise.

**Feature Importance**

Short-term forecasting relies heavily on:

- Recent historical values (autoregressive patterns)
- Weather forecasts (temperature, solar radiation, wind speed)
- Calendar effects (time of day, day of week, holidays)
- Near-term events (scheduled maintenance, known outages)

Long-term forecasting emphasizes:

- Seasonal trends
- Economic indicators
- Population growth
- Infrastructure changes

See :doc:`feature_engineering` for detailed coverage of feature selection.

**Model Complexity**

Short-term models can leverage complex machine learning approaches because:

- Training data is abundant (years of 15-minute data = hundreds of thousands of samples)
- Patterns are relatively stable over short periods
- Computational cost per forecast is acceptable

Long-term forecasting often uses simpler statistical models or scenario analysis because training data is sparse (years of monthly data = dozens of samples).

**Uncertainty Quantification**

Short-term forecasting benefits from probabilistic predictions. Instead of a single point forecast, models predict quantiles that capture uncertainty:

.. code-block:: python

   from openstef_core.types import Quantile
   
   # Configure model to predict multiple quantiles
   quantiles = [
       Quantile(0.1),   # 10th percentile (optimistic)
       Quantile(0.5),   # 50th percentile (median)
       Quantile(0.9),   # 90th percentile (pessimistic)
   ]

This allows operators to make risk-aware decisions. For example, a grid operator might provision capacity based on the 90th percentile to avoid shortfalls, while an energy trader might bid based on the median to maximize expected profit.

See :doc:`quantiles_and_confidence` for comprehensive coverage of probabilistic forecasting.

Working with Horizons in OpenSTEF
----------------------------------

OpenSTEF models are configured with specific horizons they're designed to predict. Here's a practical example:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.forecasters import XGBForecaster
   from openstef_core.types import LeadTime, Quantile
   
   # Configure a forecaster for multiple horizons
   forecaster = XGBForecaster(
       horizons=[
           LeadTime(timedelta(minutes=15)),
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=6)),
           LeadTime(timedelta(hours=24)),
       ],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       target_column="load",
   )

When you train this model and make predictions, it generates forecasts for all specified horizons simultaneously. The model learns different patterns for different horizons—short horizons rely more on recent values, while longer horizons emphasize calendar and weather features.

You can filter predictions to specific horizons:

.. code-block:: python

   # After training and prediction
   forecast = forecaster.predict(input_data)
   
   # Extract just the 15-minute-ahead predictions
   forecast_15min = forecast.filter_by_lead_time(LeadTime(timedelta(minutes=15)))
   
   # Or work with all horizons together
   all_horizons = forecast.horizons  # List of all predicted lead times

Practical Considerations
-------------------------

**Choosing Horizons**

Select horizons based on your operational needs:

- **Grid balancing**: 15 minutes to 4 hours (real-time operations)
- **Day-ahead markets**: 24 to 48 hours (next-day bidding)
- **Intraday trading**: 1 to 6 hours (adjustment opportunities)

Don't predict more horizons than necessary—each adds computational cost and model complexity.

**Handling Data Availability**

Real-world forecasting must respect data availability. If weather forecasts update every 6 hours, there's limited value in generating new predictions every 15 minutes—the inputs haven't changed. OpenSTEF's ``available_at`` tracking helps you model this correctly.

**Forecast Updates**

As new data arrives, update forecasts for the same target time. For example, at 10:00 you might forecast demand at 14:00 (4 hours ahead). At 11:00, you forecast 14:00 again (now 3 hours ahead) with updated information. This rolling forecast pattern provides progressively more accurate predictions as the target time approaches.

**Model Selection**

Different model types excel at different horizons. Tree-based models (XGBoost, LightGBM) work well across all short-term horizons. Simpler models might suffice for very short horizons (under 1 hour) where recent history dominates. See :doc:`model_selection` for detailed guidance.

Next Steps
----------

This page covered the fundamentals of short-term forecasting. To deepen your understanding:

- :doc:`quantiles_and_confidence` - Learn how to work with probabilistic forecasts
- :doc:`feature_engineering` - Understand which predictors matter for different horizons
- :doc:`model_selection` - Choose the right model for your forecasting needs
- :doc:`reliability_and_fallback` - Ensure production systems handle edge cases gracefully