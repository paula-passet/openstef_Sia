Short-Term Forecasting Basics
==============================

Short-term forecasting predicts energy consumption and generation from minutes to a few days ahead. This page explains what short-term forecasting is, why it matters for grid operations, and how it differs from long-term forecasting approaches.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting generates predictions for the near future—typically from 15 minutes to 48 hours ahead. Unlike long-term forecasts that predict months or years into the future for capacity planning, short-term forecasts support operational decisions that happen daily or hourly.

In energy systems, short-term forecasts answer questions like:

- Will this transformer exceed its capacity in the next 6 hours?
- How much solar generation can we expect tomorrow afternoon?
- When should we ask flexible customers to reduce consumption?

OpenSTEF specializes in this operational forecasting domain, providing machine learning models trained on historical patterns to predict load and generation at specific grid points.

Why Short-Term Forecasting Matters
-----------------------------------

Grid operators face immediate challenges that require accurate near-term predictions:

**Congestion management**: When grid capacity is limited, operators need advance warning of peak loads. With 24-48 hour forecasts, they can contact customers to voluntarily reduce consumption before equipment limits are exceeded.

**Renewable integration**: Solar and wind generation fluctuate rapidly. Short-term forecasts help balance supply and demand by predicting when renewable sources will produce more or less power.

**Operational safety**: Transformers and cables have thermal limits. Forecasting helps prevent overloads that could damage equipment or cause outages.

**Market operations**: Energy trading and balancing markets require forecasts to optimize dispatch decisions and minimize costs.

The key difference from long-term forecasting is the time scale and purpose. Long-term forecasts guide investment decisions about building new infrastructure. Short-term forecasts guide operational decisions about using existing infrastructure efficiently.

Forecast Horizons and Lead Times
---------------------------------

A **forecast horizon** defines how far into the future you're predicting. A **lead time** is the time between when you make the forecast and when the forecasted event occurs.

In OpenSTEF, horizons are specified as ``timedelta`` objects representing the prediction distance:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting import LGBMForecaster, LGBMForecasterHyperParams
   from openstef_models.models.forecasting.base import Quantile
   
   # Configure a forecaster for multiple horizons
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           timedelta(minutes=15),  # Very short-term
           timedelta(hours=1),     # Short-term
           timedelta(hours=6),     # Medium-term
           timedelta(hours=24),    # Day-ahead
           timedelta(hours=47),    # Two-day-ahead
       ],
       hyperparams=LGBMForecasterHyperParams()
   )

Each horizon represents a different prediction challenge. Shorter horizons (15 minutes to 1 hour) can leverage recent patterns and are generally more accurate. Longer horizons (24-48 hours) must account for daily cycles, weather changes, and greater uncertainty.

The maximum horizon determines which lag features are valid. OpenSTEF automatically generates appropriate lags—for a 24-hour horizon, you can use lags of 24 hours or more to capture daily patterns without data leakage.

Forecast Frequency and Resolution
----------------------------------

**Frequency** refers to how often you generate new forecasts. **Resolution** refers to the time granularity of the predictions themselves.

Most energy forecasting operates at 15-minute resolution—each prediction represents the expected load or generation during a 15-minute interval. This matches the temporal resolution of smart meter data and market settlement periods in many regions.

You might generate forecasts at different frequencies:

- **Continuous updates**: Generate new forecasts every 15 minutes as new data arrives
- **Hourly updates**: Generate forecasts once per hour for operational planning
- **Daily updates**: Generate day-ahead forecasts once per day for market participation

The resolution is typically fixed (15 minutes), but the forecast horizon and update frequency vary based on use case. A congestion management system might run hourly forecasts looking 47 hours ahead, while a real-time balancing system might run 15-minute forecasts looking just 1-4 hours ahead.

OpenSTEF handles temporal resolution through the ``sample_interval`` parameter in datasets:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   from openstef_models.data_classes import ForecastInputDataset
   
   # Create input data with 15-minute resolution
   timestamps = pd.date_range(
       start="2024-01-01",
       end="2024-01-07",
       freq="15min"
   )
   
   data = ForecastInputDataset(
       data=pd.DataFrame({
           "load": [100, 105, 110, 108],  # Historical load values
           "temperature": [5.2, 5.1, 5.3, 5.4],
       }, index=timestamps[:4]),
       target_column="load",
       forecast_start=datetime(2024, 1, 7, 12, 0),
       sample_interval=timedelta(minutes=15)
   )

The ``sample_interval`` ensures consistent temporal spacing and enables proper lag feature generation.

Short-Term vs. Long-Term Forecasting
-------------------------------------

Short-term and long-term forecasting differ fundamentally in their methods, inputs, and purposes:

**Time scales**: Short-term covers hours to days; long-term covers months to years.

**Input data**: Short-term models use high-resolution historical data (15-minute intervals) and recent observations. Long-term models use aggregated data (monthly averages) and scenario assumptions.

**Patterns captured**: Short-term models learn hourly and daily cycles, weather sensitivity, and recent trends. Long-term models focus on seasonal patterns, economic growth, and structural changes.

**Uncertainty**: Short-term forecasts have lower uncertainty for near horizons but uncertainty grows with distance. Long-term forecasts have inherent uncertainty from unknown future conditions.

**Model types**: Short-term forecasting typically uses machine learning models (gradient boosting, neural networks) trained on historical patterns. Long-term forecasting often uses statistical models, growth curves, or scenario analysis.

**Update frequency**: Short-term forecasts are updated frequently (minutes to hours) as new data arrives. Long-term forecasts are updated infrequently (quarterly or annually).

OpenSTEF focuses exclusively on short-term operational forecasting. If you need long-term capacity planning forecasts, you'll need different tools and approaches.

Practical Considerations
-------------------------

When implementing short-term forecasting, consider these factors:

**Data availability**: Your maximum useful horizon is limited by when input data becomes available. If weather forecasts are only reliable 48 hours ahead, longer horizons won't improve accuracy.

**Computational resources**: Forecasting at 15-minute resolution for 47-hour horizons means generating nearly 200 predictions per forecast run. Ensure your infrastructure can handle the computational load.

**Accuracy vs. horizon tradeoff**: Accept that accuracy decreases with horizon length. Design systems that can tolerate lower accuracy at longer horizons or use probabilistic forecasts to quantify uncertainty.

**Seasonal patterns**: Short-term models still need sufficient historical data to learn seasonal patterns. A model trained only on summer data will perform poorly in winter.

Next Steps
----------

Now that you understand short-term forecasting fundamentals, explore related topics:

- **Probabilistic forecasts**: See :doc:`quantiles_and_confidence` to understand how OpenSTEF quantifies forecast uncertainty
- **Feature engineering**: Learn about weather data, lag features, and other predictors in :doc:`feature_engineering`
- **Model selection**: Compare available forecasting models and choose the right one in :doc:`model_selection`
- **Production reliability**: Understand fallback strategies for operational systems in :doc:`reliability_and_fallback`