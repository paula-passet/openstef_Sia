Short-Term Forecasting Basics
==============================

Short-term energy forecasting predicts electricity demand or generation from minutes to a few days ahead. This page explains what short-term forecasting is, why it matters for grid operations, and how it differs from other forecasting approaches.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting generates predictions for the immediate future—typically from 15 minutes to 48 hours ahead. Unlike long-term forecasts that predict annual trends or seasonal patterns, short-term forecasts support real-time operational decisions: dispatching generators, balancing supply and demand, and trading energy in spot markets.

The key characteristic of short-term forecasting is its **operational focus**. Grid operators need to know what will happen in the next few hours to make decisions now. A forecast for tomorrow afternoon made this morning is fundamentally different from a forecast for next year made today—the data available, the prediction methods, and the acceptable error margins all differ.

OpenSTEF is designed specifically for this short-term operational context. The library handles the unique challenges of predicting load and generation at high temporal resolution with frequent updates.

Forecast Horizons and Lead Times
---------------------------------

The **forecast horizon** (or **lead time**) is how far into the future you're predicting. In OpenSTEF, horizons are specified as time deltas from the moment the forecast is made:

.. code-block:: python

   from datetime import timedelta
   from openstef.model.forecaster import LeadTime
   
   # Predict 1 hour ahead
   horizon_1h = LeadTime(timedelta(hours=1))
   
   # Predict 6 hours ahead
   horizon_6h = LeadTime(timedelta(hours=6))
   
   # Predict 24 hours ahead
   horizon_24h = LeadTime(timedelta(hours=24))

Each horizon represents a different prediction problem. A 1-hour-ahead forecast can use recent measurements and weather updates that aren't available for a 24-hour-ahead forecast. The further ahead you predict, the more uncertainty enters your forecast.

OpenSTEF models can be configured for multiple horizons simultaneously:

.. code-block:: python

   from openstef.model.regressors.lgbm import LGBMForecaster
   from openstef.model.forecaster import Quantile
   
   # Configure a forecaster for multiple horizons
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime(timedelta(minutes=15)),
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=6)),
           LeadTime(timedelta(hours=24)),
       ]
   )

This multi-horizon approach is essential because different operational decisions require different lead times. Real-time balancing needs 15-minute forecasts, while day-ahead market participation needs 24-hour forecasts.

Why Horizons Matter: Data Availability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The critical constraint in short-term forecasting is **data availability**. When making a forecast, you can only use information that exists at the time you make it. For a 1-hour-ahead forecast made at 10:00, you might have:

- Actual load measurements up to 9:45 (15-minute reporting delay)
- Weather forecasts updated at 9:00
- Calendar information (day of week, holidays)

For a 24-hour-ahead forecast made at 10:00 for tomorrow at 10:00, you have the same calendar information but:

- No recent load measurements are relevant (yesterday's 10:00 is now 24 hours old)
- Weather forecasts are less accurate
- You must rely more on historical patterns

OpenSTEF handles this through **lag features** that respect the forecast horizon. A lag feature only uses data that would actually be available:

.. code-block:: python

   from openstef.preprocessing.feature_engineering import generate_minute_lags
   
   # For a 6-hour forecast, generate valid lag features
   max_horizon = timedelta(hours=6)
   valid_lags = generate_minute_lags(max_horizon)
   
   # This returns lags like [6h, 7h, 8h, ...] - never shorter than the horizon
   # A 6-hour forecast can't use data from 1 hour ago (it won't exist yet)

See :doc:`feature_engineering` for details on how OpenSTEF creates features that respect data availability constraints.

Forecast Frequency and Resolution
----------------------------------

**Forecast frequency** is how often you generate new forecasts. **Resolution** is the granularity of your predictions—the time step between predicted values.

In energy systems, common patterns include:

- **15-minute resolution**: Standard for European balancing markets
- **Hourly resolution**: Common for day-ahead markets
- **5-minute resolution**: Used in some real-time markets

OpenSTEF works with time series data at any regular interval. The ``sample_interval`` parameter defines your resolution:

.. code-block:: python

   from openstef.data.dataset import TimeSeriesDataset
   import pandas as pd
   from datetime import datetime, timedelta
   
   # Create 15-minute resolution data
   timestamps = pd.date_range(
       start=datetime(2024, 1, 1),
       periods=96,  # One day at 15-minute intervals
       freq='15min'
   )
   
   data = TimeSeriesDataset(
       data=pd.DataFrame({
           'load': [100, 105, 110, ...],  # Your measurements
           'temperature': [5.2, 5.1, 5.3, ...],
       }, index=timestamps),
       sample_interval=timedelta(minutes=15)
   )

The resolution you choose affects model design. Higher resolution (shorter intervals) means:

- More data points but potentially more noise
- Shorter valid lag features (a 15-minute lag is meaningful; for hourly data it's not)
- Different seasonal patterns (15-minute data shows intra-hour variations)

Forecast frequency is typically aligned with resolution—you generate new 15-minute forecasts every 15 minutes—but this isn't required. You might generate hourly forecasts every 15 minutes as new data arrives, giving you four updated forecasts per hour.

Short-Term vs. Long-Term Forecasting
-------------------------------------

The distinction between short-term and long-term forecasting isn't just about time scale—it's about fundamentally different problems:

**Short-term forecasting** (minutes to days):

- Uses recent measurements and high-frequency patterns
- Relies on weather forecasts for temperature, wind, solar radiation
- Updates frequently as new data arrives
- Focuses on operational accuracy—errors have immediate costs
- Models learn from autocorrelation and recent trends

**Long-term forecasting** (months to years):

- Uses historical trends and growth patterns
- Relies on scenarios for economic growth, policy changes, technology adoption
- Updates infrequently (quarterly or annually)
- Focuses on planning—errors affect investment decisions
- Models learn from seasonal cycles and structural changes

OpenSTEF is a short-term forecasting library. It's designed for the operational time scale where machine learning can leverage recent patterns and weather forecasts. The library doesn't handle long-term scenario planning or capacity expansion problems.

Practical Example: Making a Forecast
-------------------------------------

Here's a complete example showing how horizons and lead times work in practice:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef.model.regressors.lgbm import LGBMForecaster
   from openstef.model.forecaster import LeadTime, Quantile
   from openstef.model.standard_model import StandardModel
   from openstef.data.dataset import TrainingDataset
   import pandas as pd
   
   # Define the horizons you need
   horizons = [
       LeadTime(timedelta(minutes=15)),  # Real-time operations
       LeadTime(timedelta(hours=1)),     # Intra-hour balancing
       LeadTime(timedelta(hours=6)),     # Short-term dispatch
       LeadTime(timedelta(hours=24)),    # Day-ahead market
   ]
   
   # Create a forecaster for these horizons
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=horizons
   )
   
   # Wrap in a StandardModel for preprocessing
   model = StandardModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=14)
   )
   
   # Train on historical data
   # training_data is a TrainingDataset with load and weather features
   model.fit(training_data)
   
   # Generate forecasts for all horizons
   # The model automatically handles different data availability for each horizon
   forecasts = model.predict(recent_data)
   
   # forecasts is a ForecastDataset with predictions for each horizon
   # Each horizon has quantile predictions (P10, P50, P90)

The model handles the complexity of different horizons automatically. For the 15-minute forecast, it uses recent load measurements and short-term weather updates. For the 24-hour forecast, it relies more on daily patterns and longer-range weather forecasts.

When to Use Different Horizons
-------------------------------

Choosing forecast horizons depends on your operational needs:

**Sub-hourly (15-30 minutes)**:
  Real-time balancing, automatic generation control, responding to unexpected outages. Requires high-frequency data and rapid updates.

**1-6 hours**:
  Intra-day trading, short-term dispatch optimization, managing flexible resources. Balances accuracy with planning time.

**12-48 hours**:
  Day-ahead market participation, maintenance scheduling, resource commitment. Longer planning horizon accepts slightly lower accuracy.

Most operational systems use multiple horizons simultaneously. OpenSTEF's multi-horizon forecasters make this efficient—you train one model that handles all horizons rather than maintaining separate models.

Next Steps
----------

This page covered the fundamentals of short-term forecasting: what horizons and lead times mean, why data availability matters, and how resolution affects your models.

To build on this foundation:

- :doc:`quantiles_and_confidence` explains how to quantify forecast uncertainty
- :doc:`feature_engineering` details how to create features that respect horizon constraints
- :doc:`model_selection` helps you choose the right algorithm for your forecasting problem
- :doc:`reliability_and_fallback` covers production reliability when forecasts fail