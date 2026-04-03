Short-Term Forecasting Basics
==============================

Short-term energy forecasting predicts electricity demand or generation from minutes to a few days ahead. This page explains what short-term forecasting is, how it differs from long-term forecasting, and the key concepts you need to understand when working with OpenSTEF.

What is Short-Term Forecasting?
--------------------------------

Short-term forecasting focuses on predicting energy values in the immediate future—typically from 15 minutes to 48 hours ahead. Unlike long-term forecasts that predict months or years into the future for capacity planning, short-term forecasts support operational decisions: balancing supply and demand, scheduling generation assets, and managing grid stability.

The defining characteristics of short-term forecasting are:

- **Frequent updates**: Forecasts are regenerated multiple times per day as new data becomes available
- **High temporal resolution**: Predictions are made at fine granularities (15-minute or hourly intervals)
- **Recent data dependency**: Models rely heavily on recent observations and weather forecasts
- **Operational focus**: Results inform immediate decisions rather than strategic planning

For example, a grid operator might generate a new 48-hour forecast every 15 minutes, using the latest meter readings and updated weather predictions to adjust their operational plans continuously.

Key Concepts
------------

Understanding short-term forecasting requires familiarity with several interconnected concepts.

Forecast Horizon
^^^^^^^^^^^^^^^^

The **forecast horizon** (also called lead time) is how far into the future you're predicting. In OpenSTEF, horizons are represented as ``LeadTime`` objects that specify the time difference between when data is available and when the prediction is for.

A 6-hour horizon means you're predicting what will happen 6 hours from now. A 48-hour horizon predicts two days ahead. Different horizons often require different models or features—predicting 15 minutes ahead can rely on very recent trends, while predicting 48 hours ahead requires understanding daily patterns and weather forecasts.

OpenSTEF models can be configured to predict multiple horizons:

.. code-block:: python

   from openstef_core.types import LeadTime
   from datetime import timedelta

   # Define horizons for different prediction distances
   horizons = [
       LeadTime.from_string("PT15M"),   # 15 minutes ahead
       LeadTime.from_string("PT1H"),    # 1 hour ahead
       LeadTime.from_string("PT6H"),    # 6 hours ahead
       LeadTime.from_string("PT24H"),   # 24 hours ahead
       LeadTime.from_string("PT48H"),   # 48 hours ahead
   ]

The choice of horizons depends on your operational needs. Intraday trading might require 15-minute to 6-hour forecasts, while day-ahead market participation needs 24-48 hour predictions.

Sample Interval and Resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The **sample interval** is the time between consecutive predictions. A 15-minute sample interval means you generate a prediction for every 15-minute period. An hourly interval produces one prediction per hour.

Higher resolution (shorter intervals) provides more granular information but requires more computational resources and more frequent data updates. Energy markets often dictate the required resolution—European day-ahead markets typically use 15-minute intervals, while some regions use hourly intervals.

.. code-block:: python

   from openstef_core.datasets import ForecastInputDataset
   from datetime import timedelta
   import pandas as pd

   # Create forecast input with 15-minute resolution
   data = ForecastInputDataset(
       data=timeseries_df,  # DataFrame with DatetimeIndex
       sample_interval=timedelta(minutes=15),
       horizon_column="horizon",
       available_at_column="available_at"
   )

The sample interval affects feature engineering—with 15-minute data, you might use lags of 15, 30, and 45 minutes, while hourly data uses hourly lags.

Forecast Frequency
^^^^^^^^^^^^^^^^^^

**Forecast frequency** is how often you regenerate the entire forecast. You might produce a 48-hour forecast every 15 minutes, every hour, or every 6 hours. Higher frequency means more up-to-date predictions but requires more computational resources.

In production systems, forecast frequency balances:

- **Data availability**: New weather forecasts might arrive every 6 hours
- **Computational cost**: Complex models take time to run
- **Operational value**: How quickly do decisions need to respond to changing conditions?

A common pattern is to generate detailed forecasts every 15 minutes for the next 6 hours, and update longer-horizon forecasts (24-48 hours) every hour or when new weather data arrives.

Data Availability and Versioning
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A critical aspect of short-term forecasting is understanding when data becomes available. When making a forecast at 10:00 AM, you typically don't have complete data up to 10:00 AM—there's usually a delay while data is collected, validated, and transmitted.

OpenSTEF handles this through the ``available_at`` concept. Each data point has a timestamp (when the measurement occurred) and an ``available_at`` timestamp (when that data became usable for forecasting). This ensures models only use data that would have been available in real-time.

.. code-block:: python

   # Example: Data with availability timestamps
   # The 09:00 load measurement wasn't available until 09:15
   data_df = pd.DataFrame({
       'timestamp': pd.date_range('2024-01-01 09:00', periods=4, freq='15min'),
       'load': [150.2, 152.1, 148.9, 151.3],
       'available_at': pd.date_range('2024-01-01 09:15', periods=4, freq='15min')
   })

This versioning prevents "look-ahead bias" where models accidentally use information that wouldn't have been available at prediction time.

Short-Term vs. Long-Term Forecasting
-------------------------------------

Short-term and long-term forecasting serve different purposes and use different techniques:

**Short-term forecasting** (minutes to days):

- Uses recent observations and high-frequency patterns
- Incorporates detailed weather forecasts
- Updates frequently as new data arrives
- Focuses on operational decisions
- Requires handling data delays and real-time constraints

**Long-term forecasting** (months to years):

- Uses historical trends and seasonal patterns
- Considers economic factors and policy changes
- Updates infrequently (monthly or quarterly)
- Supports strategic planning and investment decisions
- Doesn't face real-time data constraints

OpenSTEF is designed specifically for short-term forecasting. The library's features—like versioned data handling, sub-hourly resolution support, and frequent retraining—address the unique challenges of operational forecasting.

Practical Example
-----------------

Here's how these concepts come together in a typical forecasting workflow:

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_core.types import LeadTime, Quantile
   from datetime import timedelta

   # Configure a forecaster for day-ahead predictions
   forecaster = LGBMForecaster(
       horizons=[LeadTime.from_string("PT24H")],  # 24-hour ahead forecast
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]  # Probabilistic forecast
   )

   # Create the forecasting model
   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=14)  # Use 14 days of history for features
   )

   # Train on historical data (with proper versioning)
   model.fit(training_data)

   # Generate forecast for new data
   # This produces predictions 24 hours ahead at your sample interval
   forecast = model.predict(current_data)

This example creates a model that predicts 24 hours ahead, producing probabilistic forecasts (10th, 50th, and 90th percentiles). The model would typically be retrained periodically (daily or weekly) and used to generate new forecasts every 15 minutes or hourly.

Next Steps
----------

This page covered the fundamentals of short-term forecasting. To build effective forecasts, you'll need to understand:

- :doc:`quantiles_and_confidence` for probabilistic forecasting and uncertainty quantification
- :doc:`feature_engineering` for creating predictive features from raw data
- :doc:`model_selection` for choosing appropriate forecasting algorithms
- :doc:`reliability_and_fallback` for ensuring production reliability

These concepts work together to create robust, operational forecasting systems that support real-time energy management decisions.