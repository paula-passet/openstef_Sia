Short-Term Forecasting Basics
==============================

Short-term energy forecasting predicts electricity demand or generation from minutes to a few days ahead. This page explains what makes short-term forecasting distinct, the key concepts of horizons and lead times, and how forecast frequency affects your modeling choices.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting focuses on predictions from 15 minutes to 48 hours ahead. Unlike long-term forecasts that predict seasonal patterns months or years in advance, short-term forecasts support operational decisions: dispatching generators, balancing supply and demand, and managing grid stability.

The defining characteristic is **operational relevance**. A day-ahead forecast helps schedule generation assets. A 15-minute-ahead forecast enables real-time grid balancing. These forecasts must be accurate, timely, and updated frequently as new information becomes available.

Key differences from long-term forecasting:

- **Temporal resolution**: Short-term forecasts typically use 15-minute or hourly intervals, while long-term forecasts might use daily or monthly aggregates
- **Update frequency**: Short-term models often run every 15 minutes to incorporate the latest data; long-term models might update weekly or monthly
- **Feature importance**: Weather conditions and recent load patterns dominate short-term forecasts, while long-term forecasts emphasize seasonal trends and economic factors
- **Accuracy requirements**: Operational decisions require high accuracy at specific horizons (e.g., the next hour), while long-term forecasts tolerate more uncertainty

Horizons and Lead Times
------------------------

The **horizon** or **lead time** specifies how far ahead you're predicting. In OpenSTEF, horizons are represented as ``timedelta`` objects and configured per forecaster:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_core.types import LeadTime, Quantile

   # Configure a forecaster for 1-hour ahead predictions
   forecaster = LGBMForecaster(
       horizons=[LeadTime(timedelta(hours=1))],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

The horizon determines which historical features are valid. For a 1-hour-ahead forecast, you can use data from 1 hour ago or earlier, but not from 30 minutes ago—that data won't exist when you need to make the prediction.

Multiple Horizons
^^^^^^^^^^^^^^^^^

Many applications require forecasts at multiple horizons. A grid operator might need predictions at 15 minutes, 1 hour, 6 hours, and 24 hours ahead. OpenSTEF supports this through multi-horizon configurations:

.. code-block:: python

   forecaster = LGBMForecaster(
       horizons=[
           LeadTime(timedelta(minutes=15)),
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=6)),
           LeadTime(timedelta(hours=24))
       ],
       quantiles=[Quantile(0.5)]
   )

Each horizon may have different accuracy characteristics. Near-term forecasts (15 minutes) typically achieve higher accuracy because recent patterns persist. Longer horizons (24 hours) face more uncertainty as weather and demand patterns evolve.

The ``max_horizon`` property returns the furthest prediction distance, useful for determining how much historical data you need:

.. code-block:: python

   max_lead = forecaster.max_horizon  # timedelta(hours=24)

Forecast Frequency and Resolution
----------------------------------

**Forecast frequency** is how often you generate new predictions. **Resolution** is the time interval between predicted values.

A typical setup might generate forecasts every 15 minutes (frequency) with predictions at 15-minute intervals (resolution) extending 48 hours ahead. Each forecast run produces a new set of predictions incorporating the latest available data.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset
   import pandas as pd

   # Create dataset with 15-minute resolution
   timestamps = pd.date_range("2024-01-01", periods=100, freq="15min")
   data = pd.DataFrame({
       "load": [100 + i * 0.5 for i in range(100)]
   }, index=timestamps)

   dataset = VersionedTimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

The ``sample_interval`` parameter defines your data resolution. This must match the frequency of your input data and determines the granularity of predictions.

Common resolution choices:

- **15 minutes**: Standard for transmission system operators, balances detail with computational cost
- **1 hour**: Common for distribution networks and renewable generation forecasts
- **5 minutes**: Used in real-time markets requiring rapid response

Higher resolution (shorter intervals) increases data volume and computational requirements but provides finer-grained predictions for operational control.

Lag Features and Horizon Constraints
-------------------------------------

Historical values (lags) are powerful predictors in short-term forecasting. A lag feature uses past observations to predict future values. For example, load from 24 hours ago often predicts today's load well due to daily patterns.

The critical constraint: **lag features must respect the forecast horizon**. For a 1-hour-ahead forecast, you can use a 1-hour lag (or longer), but not a 30-minute lag—that data won't be available at prediction time.

OpenSTEF's feature generation utilities automatically filter lags based on your horizon:

.. code-block:: python

   from openstef_models.feature_engineering.lag_features import generate_minute_lags

   # Generate valid lags for 1-hour-ahead forecasting
   valid_lags = generate_minute_lags(max_horizon=timedelta(hours=1))
   # Returns: [1h, 2h, 3h, ..., 23h] (sub-hourly lags filtered out)

   # For 15-minute-ahead forecasting
   valid_lags_short = generate_minute_lags(max_horizon=timedelta(minutes=15))
   # Returns: [15min, 30min, 45min, 1h, 2h, ..., 23h]

For longer horizons, day-based lags capture weekly patterns:

.. code-block:: python

   from openstef_models.feature_engineering.lag_features import generate_day_lags

   # Generate daily lags for day-ahead forecasting
   daily_lags = generate_day_lags(
       max_horizon=timedelta(hours=24),
       max_day_lags=14  # Two weeks of history
   )
   # Returns: [1d, 2d, 3d, ..., 14d]

These functions ensure your features are valid for the specified horizon, preventing data leakage where future information inadvertently influences predictions.

Practical Example: Day-Ahead Forecasting
-----------------------------------------

Here's a complete example configuring a day-ahead forecasting pipeline with appropriate horizons and features:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_models.preprocessing.preprocessing_pipeline import PreprocessingPipeline
   from openstef_models.preprocessing.transforms.lag_transformer import LagTransformer
   from openstef_core.types import LeadTime, Quantile

   # Configure for 24-hour-ahead predictions
   horizon = LeadTime(timedelta(hours=24))

   # Create lag features valid for this horizon
   lag_transformer = LagTransformer(
       lags=[
           timedelta(hours=24),   # Yesterday same hour
           timedelta(hours=48),   # Two days ago
           timedelta(days=7)      # Last week same hour
       ]
   )

   # Build preprocessing pipeline
   preprocessing = PreprocessingPipeline(
       transforms=[lag_transformer],
       horizons=[horizon]
   )

   # Configure forecaster with quantiles for uncertainty
   forecaster = LGBMForecaster(
       horizons=[horizon],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

This configuration produces probabilistic forecasts (see :doc:`quantiles_and_confidence`) at the 24-hour horizon, using historical patterns from 1, 2, and 7 days ago.

When to Use Different Horizons
-------------------------------

Choosing horizons depends on your operational needs:

**Intraday horizons (15 min - 6 hours)**:
   - Real-time balancing and dispatch
   - Renewable generation forecasts for grid integration
   - High accuracy achievable with recent data
   - Frequent updates (every 15-60 minutes) recommended

**Day-ahead horizons (12 - 48 hours)**:
   - Market participation and unit commitment
   - Maintenance scheduling
   - Weather forecasts become critical
   - Daily updates often sufficient

**Multi-horizon forecasts**:
   - Comprehensive operational planning
   - Different models or features per horizon
   - Higher computational cost but better decision support

For model selection guidance based on your horizon and data characteristics, see :doc:`model_selection`. For feature engineering strategies that vary by horizon, see :doc:`feature_engineering`.

Next Steps
----------

Now that you understand forecasting horizons and lead times, explore related topics:

- :doc:`quantiles_and_confidence` - Learn how to generate probabilistic forecasts with uncertainty estimates
- :doc:`feature_engineering` - Discover which features work best at different horizons
- :doc:`model_selection` - Choose the right forecasting model for your use case
- :doc:`reliability_and_fallback` - Ensure your forecasts remain available even when models fail