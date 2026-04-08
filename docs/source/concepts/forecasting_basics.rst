Short-Term Forecasting Basics
==============================

Short-term energy forecasting predicts power demand or generation from minutes to a few days ahead. This page explains what short-term forecasting is, why it matters for grid operations, and how it differs from long-term planning forecasts.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting focuses on operational timescales—typically from 15 minutes to 48 hours ahead. These forecasts help grid operators make real-time decisions about:

- **Unit commitment**: Which power plants to activate
- **Energy trading**: Bidding in day-ahead and intraday markets
- **Grid balancing**: Maintaining supply-demand equilibrium
- **Congestion management**: Preventing transmission bottlenecks

Unlike long-term forecasts (months to years ahead) used for infrastructure planning, short-term forecasts require high temporal resolution and frequent updates as new data becomes available.

Key Temporal Concepts
---------------------

Understanding three core concepts is essential for working with OpenSTEF:

**Forecast Horizon**
   The time interval between when a forecast is made and when the predicted event occurs. In OpenSTEF, horizons are represented as ``LeadTime`` objects that specify how far ahead you're predicting.

**Lead Time**
   Synonymous with forecast horizon in OpenSTEF. A lead time of 15 minutes means predicting what will happen 15 minutes from now. Models can predict multiple horizons simultaneously—for example, forecasts at 15 minutes, 30 minutes, 1 hour, and 24 hours ahead.

**Sample Interval**
   The time resolution of your predictions. A 15-minute sample interval means you generate forecasts for every 15-minute period (e.g., 00:00, 00:15, 00:30). This differs from horizon—you might forecast 24 hours ahead (horizon) but produce predictions at 15-minute intervals (resolution).

Here's how these concepts relate in practice:

.. code-block:: python

   from datetime import timedelta
   from openstef.model.forecaster import LeadTime
   
   # Define forecast horizons (how far ahead to predict)
   horizons = [
       LeadTime(timedelta(minutes=15)),   # Very short-term
       LeadTime(timedelta(hours=1)),      # Short-term
       LeadTime(timedelta(hours=24)),     # Day-ahead
       LeadTime(timedelta(hours=47)),     # Full day-ahead market
   ]
   
   # Sample interval defines prediction resolution
   sample_interval = timedelta(minutes=15)
   
   # This means: predict 15min, 1h, 24h, and 47h ahead,
   # with predictions every 15 minutes

Short-Term vs. Long-Term Forecasting
-------------------------------------

The distinction between short-term and long-term forecasting goes beyond just the time horizon:

**Data Requirements**

Short-term forecasts rely heavily on recent observations and high-frequency data. Weather forecasts, recent load patterns, and real-time measurements are critical. Long-term forecasts depend more on seasonal patterns, economic trends, and historical statistics.

**Update Frequency**

Short-term forecasts are regenerated frequently—often every 15 minutes or hourly—as new data arrives. Each new forecast incorporates the latest measurements, improving accuracy. Long-term forecasts might be updated monthly or quarterly.

**Accuracy Expectations**

Short-term forecasts are generally more accurate because near-future conditions resemble the present. Accuracy degrades as the horizon increases. A 1-hour-ahead forecast will typically outperform a 24-hour-ahead forecast, which in turn beats a week-ahead forecast.

**Model Complexity**

Short-term models can leverage complex patterns like intraday cycles and weather sensitivity. Long-term models focus on broader trends and may use simpler statistical approaches since fine-grained patterns average out over longer periods.

Forecast Horizons in Practice
------------------------------

Different operational needs require different forecast horizons:

**15 minutes to 1 hour ahead**
   Real-time grid balancing and automatic generation control. These ultra-short-term forecasts help operators respond to immediate imbalances.

**1 to 6 hours ahead**
   Intraday energy trading and unit commitment adjustments. Operators can still make economical decisions about which resources to activate.

**24 to 48 hours ahead**
   Day-ahead market participation. Most European electricity markets require bids 12-36 hours before delivery, making this horizon critical for commercial operations.

OpenSTEF models can predict multiple horizons simultaneously, which is more efficient than training separate models for each horizon:

.. code-block:: python

   from openstef.model.forecaster.lgbm import LGBMForecaster
   from openstef.model.forecaster import Quantile, LeadTime
   from datetime import timedelta
   
   # Configure a forecaster for multiple horizons
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime(timedelta(minutes=15)),
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=6)),
           LeadTime(timedelta(hours=24)),
       ],
   )
   
   # The model learns relationships between lead time and prediction accuracy
   # Horizon becomes a feature the model can use

Data Availability and Lead Time
--------------------------------

A critical aspect of short-term forecasting is understanding when data becomes available. The ``available_at`` timestamp indicates when forecast inputs are known, which determines the earliest possible forecast time.

Consider weather forecasts: a weather prediction for tomorrow might be available today, but it gets updated multiple times as meteorological models refine their estimates. OpenSTEF's versioned datasets handle this complexity:

.. code-block:: python

   from openstef.data.dataset import VersionedTimeSeriesDataset
   import pandas as pd
   from datetime import datetime, timedelta
   
   # Example: Weather forecast data with availability timestamps
   data = pd.DataFrame({
       'timestamp': pd.date_range('2024-01-01', periods=96, freq='15min'),
       'temperature': [5.2, 5.1, 5.0, 4.9] * 24,
       'available_at': datetime(2023, 12, 31, 12, 0),  # Forecast made yesterday
   })
   
   dataset = VersionedTimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
   )
   
   # Filter to data available before a specific time
   # This ensures you only use information that would have been available
   # when making historical forecasts
   available_data = dataset.filter_by_available_before(
       available_before=datetime(2023, 12, 31, 18, 0)
   )

This versioning is essential for realistic model evaluation. Without it, you might accidentally use future information during training, leading to overly optimistic performance estimates that don't reflect real-world accuracy.

Forecast Frequency and Computational Considerations
----------------------------------------------------

How often should you generate new forecasts? The answer depends on:

1. **Data update frequency**: No benefit to forecasting more often than new data arrives
2. **Forecast horizon**: Longer horizons change slowly; 48-hour forecasts don't need minute-by-minute updates
3. **Computational resources**: Model inference takes time and energy
4. **Operational requirements**: Market deadlines and control system needs

A typical setup might be:

- **Ultra-short-term (0-1h)**: Update every 5-15 minutes
- **Short-term (1-6h)**: Update every 15-30 minutes  
- **Day-ahead (24-48h)**: Update every 1-4 hours

OpenSTEF is designed as a library, so you control the scheduling. Integrate it into your existing systems using cron jobs, workflow orchestrators, or event-driven architectures.

Practical Example: Complete Forecasting Workflow
-------------------------------------------------

Here's a minimal example showing how these concepts come together:

.. code-block:: python

   from openstef.data.dataset import VersionedTimeSeriesDataset, ForecastInputDataset
   from openstef.model.forecaster.lgbm import LGBMForecaster
   from openstef.model.forecaster import LeadTime, Quantile
   from datetime import datetime, timedelta
   import pandas as pd
   
   # 1. Prepare historical data with 15-minute resolution
   historical_data = pd.DataFrame({
       'timestamp': pd.date_range('2024-01-01', periods=2880, freq='15min'),
       'load': [100 + 20 * (i % 96) / 96 for i in range(2880)],  # Synthetic load
       'temperature': [5 + 3 * (i % 96) / 96 for i in range(2880)],
       'available_at': datetime(2024, 1, 1),
   })
   
   dataset = VersionedTimeSeriesDataset(
       data=historical_data,
       sample_interval=timedelta(minutes=15),
   )
   
   # 2. Configure forecaster for multiple horizons
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=6)),
           LeadTime(timedelta(hours=24)),
       ],
   )
   
   # 3. Prepare training data
   forecast_start = datetime(2024, 1, 15)
   train_data = ForecastInputDataset.from_versioned_dataset(
       dataset=dataset.filter_by_range(end=forecast_start),
       target_column='load',
       forecast_start=forecast_start,
   )
   
   # 4. Train the model
   forecaster.fit(train_data)
   
   # 5. Generate forecasts for all configured horizons
   forecast = forecaster.predict(train_data)
   
   # Access predictions for specific horizons
   print(f"Forecast shape: {forecast.data.shape}")
   print(f"Available horizons: {forecast.horizons}")

This example demonstrates the core workflow: prepare versioned data, configure horizons, train a model, and generate multi-horizon forecasts. For production systems, you'd add feature engineering (see :doc:`feature_engineering`), model selection logic (see :doc:`model_selection`), and reliability measures (see :doc:`reliability_and_fallback`).

Understanding Forecast Uncertainty
-----------------------------------

Short-term forecasts are never perfectly accurate. OpenSTEF generates probabilistic forecasts using quantiles, which express uncertainty as prediction intervals. A forecast might predict:

- 10th percentile (P10): 450 MW (pessimistic)
- 50th percentile (P50): 500 MW (median/most likely)
- 90th percentile (P90): 550 MW (optimistic)

This means there's a 90% probability the actual load will fall between 450 and 550 MW. Uncertainty typically increases with forecast horizon—predictions 24 hours ahead have wider intervals than predictions 1 hour ahead.

For a detailed explanation of probabilistic forecasting and quantiles, see :doc:`quantiles_and_confidence`.

Next Steps
----------

Now that you understand short-term forecasting fundamentals, explore these related topics:

- :doc:`quantiles_and_confidence` - Learn how OpenSTEF quantifies forecast uncertainty
- :doc:`feature_engineering` - Discover which predictors improve forecast accuracy
- :doc:`model_selection` - Choose the right forecasting algorithm for your use case
- :doc:`reliability_and_fallback` - Ensure your forecasts remain available even when models fail