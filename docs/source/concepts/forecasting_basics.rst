Short-Term Forecasting Basics
==============================

Short-term forecasting predicts energy demand or generation from minutes to a few days ahead. This differs fundamentally from long-term forecasting, which projects months or years into the future. OpenSTEF focuses exclusively on short-term horizons where recent patterns, weather conditions, and intraday cycles drive predictions.

Understanding short-term forecasting concepts—horizons, lead times, and forecast frequency—is essential for building effective energy forecasting systems with OpenSTEF.

What is Short-Term Forecasting?
--------------------------------

Short-term energy forecasting predicts load or generation for immediate operational needs. Grid operators use these forecasts to balance supply and demand, schedule generation, and manage energy trading. The prediction window typically ranges from 15 minutes to 48 hours ahead.

Unlike long-term forecasts that rely on economic trends and capacity planning, short-term forecasts depend on:

- Recent historical patterns (last few hours or days)
- Current and predicted weather conditions
- Time-of-day and day-of-week patterns
- Holiday effects and special events

Short-term forecasts update frequently—often every 15 minutes to hourly—as new data becomes available. This continuous updating allows operators to respond to changing conditions.

Forecast Horizons and Lead Times
---------------------------------

The **horizon** or **lead time** specifies how far ahead you're predicting. In OpenSTEF, horizons are represented as time deltas from the forecast start time.

A forecast with a 24-hour horizon predicts conditions 24 hours from now. A forecast with a 30-minute horizon predicts just 30 minutes ahead. Different horizons serve different operational purposes:

- **0-4 hours**: Real-time balancing and immediate dispatch decisions
- **4-24 hours**: Day-ahead market participation and unit commitment
- **24-48 hours**: Extended planning and backup capacity scheduling

OpenSTEF models can predict multiple horizons simultaneously. You configure horizons when creating a forecaster:

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.forecasters import GBLinearForecaster
   from openstef_core.types import LeadTime, Quantile as Q
   
   # Configure forecaster for 6-hour and 24-hour horizons
   model = ForecastingModel(
       forecaster=GBLinearForecaster(
           horizons=[
               LeadTime.from_string("PT6H"),   # 6 hours ahead
               LeadTime.from_string("PT24H"),  # 24 hours ahead
           ],
           quantiles=[Q(0.5), Q(0.1), Q(0.9)],
       ),
       target_column="load",
   )

The ``LeadTime.from_string()`` method accepts ISO 8601 duration format. Common examples:

- ``"PT15M"`` - 15 minutes
- ``"PT1H"`` - 1 hour
- ``"PT36H"`` - 36 hours
- ``"P2D"`` - 2 days

Longer horizons generally produce less accurate forecasts because uncertainty compounds over time. Weather forecasts become less reliable, and unexpected events are more likely to occur.

Forecast Frequency and Resolution
----------------------------------

**Forecast frequency** determines how often you generate new predictions. **Resolution** specifies the time granularity of predictions—whether you predict every 15 minutes, hourly, or at some other interval.

OpenSTEF supports various resolutions through the ``sample_interval`` parameter. Common choices:

- **15 minutes**: Standard for many European grid operators
- **1 hour**: Common for wholesale markets and longer-term planning
- **5 minutes**: Used in some real-time balancing markets

Higher resolution (shorter intervals) captures more detail but requires more data and computational resources. Choose resolution based on your operational needs and data availability.

Here's how to specify resolution when creating datasets:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from datetime import timedelta
   import pandas as pd
   
   # 15-minute resolution data
   timestamps = pd.date_range("2025-01-01", periods=96, freq="15min")
   dataset_15min = TimeSeriesDataset(
       data=pd.DataFrame({"load": range(96)}, index=timestamps),
       sample_interval=timedelta(minutes=15),
   )
   
   # Hourly resolution data
   timestamps_hourly = pd.date_range("2025-01-01", periods=24, freq="h")
   dataset_hourly = TimeSeriesDataset(
       data=pd.DataFrame({"load": range(24)}, index=timestamps_hourly),
       sample_interval=timedelta(hours=1),
   )

The library validates that your data matches the declared ``sample_interval``. Mismatched frequencies raise validation errors.

Short-Term vs. Long-Term Forecasting
-------------------------------------

Short-term and long-term forecasting serve different purposes and use different techniques:

**Short-term forecasting** (hours to days):

- Uses recent historical data and current conditions
- Incorporates detailed weather forecasts
- Updates frequently as new data arrives
- Focuses on operational decisions
- Requires high temporal resolution

**Long-term forecasting** (months to years):

- Uses historical trends and seasonal patterns
- Considers economic factors and capacity changes
- Updates infrequently (monthly or quarterly)
- Supports strategic planning and investment decisions
- Uses lower temporal resolution

OpenSTEF is designed specifically for short-term forecasting. The library's feature engineering, model architectures, and validation approaches all assume short-term horizons where recent patterns matter most.

Generating Forecasts
---------------------

Once you've trained a model, generating forecasts requires input data covering the historical period before your forecast start time. The model uses this history to predict future values at the configured horizons.

.. code-block:: python

   from openstef_workflows import CustomForecastingWorkflow
   from datetime import datetime
   
   # Create workflow with trained model
   workflow = CustomForecastingWorkflow(
       model=model,
       model_id="load_forecaster",
   )
   
   # Train on historical data
   workflow.fit(training_dataset)
   
   # Generate forecasts
   # The model predicts at the configured horizons (6h and 24h)
   forecasts = workflow.predict(
       data=recent_data,
       forecast_start=datetime(2025, 1, 15, 12, 0),
   )
   
   # Access forecast results
   forecast_df = forecasts.to_pandas()
   print(forecast_df[["load_q0.5", "load_q0.1", "load_q0.9"]].head())

The ``predict()`` method returns a ``ForecastDataset`` containing predictions for all configured quantiles at each horizon. The forecast start time determines when predictions begin—the model looks backward from this point to gather features and forward to generate predictions.

Practical Considerations
-------------------------

When implementing short-term forecasting systems, consider:

**Data latency**: Real-world data arrives with delays. A forecast generated at 10:00 might only have data available through 9:45. Account for this when choosing horizons—a "15-minute ahead" forecast might actually predict 30 minutes into the future once data latency is considered.

**Computational constraints**: Generating forecasts every 15 minutes requires models that train and predict quickly. Balance model complexity against latency requirements.

**Horizon selection**: Don't predict more horizons than necessary. Each additional horizon increases computational cost. Focus on horizons that match your operational decision points.

**Resolution trade-offs**: Higher resolution captures more detail but amplifies noise and increases data requirements. Start with hourly resolution unless you have specific needs for finer granularity.

Next Steps
----------

Now that you understand short-term forecasting fundamentals, explore related topics:

- :doc:`quantiles_and_confidence` - Learn how OpenSTEF handles forecast uncertainty through probabilistic predictions
- :doc:`model_selection` - Choose the right forecasting model for your use case
- :doc:`feature_engineering` - Understand which features improve forecast accuracy
- :doc:`reliability_and_fallback` - Build robust production systems that handle failures gracefully