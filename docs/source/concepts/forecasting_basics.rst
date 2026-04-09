Short-Term Forecasting Basics
==============================

Short-term energy forecasting predicts power demand or generation from minutes to a few days ahead. Unlike long-term forecasting that plans infrastructure years in advance, short-term forecasting supports operational decisions: dispatching generators, balancing supply and demand, and trading energy in real-time markets.

This page explains the core concepts that define short-term forecasting: what time horizons matter, how lead times affect prediction accuracy, and why forecasts need frequent updates.

What Makes Forecasting "Short-Term"?
-------------------------------------

Short-term forecasting focuses on operational timescales—typically from 15 minutes to 48 hours ahead. These predictions help grid operators and energy traders make immediate decisions about resource allocation and market participation.

The distinction from long-term forecasting is fundamental:

- **Short-term (operational)**: Hours to days ahead, updated frequently, uses recent weather and consumption patterns, supports real-time operations
- **Long-term (strategic)**: Months to years ahead, updated infrequently, uses historical trends and growth projections, supports infrastructure planning

OpenSTEF is designed specifically for short-term forecasting. The library's data structures, models, and workflows assume you're making predictions that will be used within hours or days, not months or years.

Forecast Horizons and Lead Times
---------------------------------

A **forecast horizon** is how far into the future you're predicting. A **lead time** is the time between when you make the forecast and when the predicted event occurs.

In OpenSTEF, horizons are represented as ``LeadTime`` objects that specify the prediction distance:

.. code-block:: python

    from datetime import timedelta
    from openstef.model.forecaster import LeadTime
    
    # Common short-term horizons
    horizons = [
        LeadTime(timedelta(minutes=15)),  # 15 minutes ahead
        LeadTime(timedelta(hours=1)),      # 1 hour ahead
        LeadTime(timedelta(hours=24)),     # Day-ahead
        LeadTime(timedelta(hours=47)),     # 47 hours for next-day markets
    ]

Each horizon represents a different prediction challenge. Fifteen minutes ahead, recent consumption patterns dominate. Twenty-four hours ahead, weather forecasts and daily cycles become critical. Models often train separately for different horizons because the relevant features and patterns change with prediction distance.

.. note:: [DIAGRAM: Timeline showing forecast horizons (15min, 1h, 24h, 48h) with lead times and update frequency. Horizontal axis shows time from "Now" extending 48 hours. Vertical markers indicate forecast points at 15min, 1h, 24h, and 48h. Annotations show "High accuracy, frequent updates" near 15min and "Lower accuracy, less frequent updates" near 48h. Include example: "Forecast made at 10:00 for 11:00 delivery = 1h lead time".]

When configuring a forecaster, you specify which horizons it should predict:

.. code-block:: python

    from openstef.model.regressors.lgbm import LGBMForecaster, LGBMForecasterConfig
    from openstef.model.forecaster import Quantile
    
    config = LGBMForecasterConfig(
        horizons=[
            LeadTime(timedelta(minutes=15)),
            LeadTime(timedelta(hours=1)),
            LeadTime(timedelta(hours=24)),
        ],
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        hyperparams={"n_estimators": 100, "learning_rate": 0.1},
    )
    
    forecaster = LGBMForecaster(config)

The ``horizons`` parameter tells the model which lead times to prepare for during training and prediction.

Forecast Frequency and Updates
-------------------------------

Short-term forecasts become stale quickly. Weather conditions change, unexpected events occur, and new consumption data arrives. To stay accurate, forecasts must update frequently.

Update frequency depends on the forecast horizon:

- **15-minute ahead**: Update every 5-15 minutes as new measurements arrive
- **1-hour ahead**: Update every 15-30 minutes
- **Day-ahead**: Update every 1-6 hours, often synchronized with market schedules
- **48-hour ahead**: Update once or twice daily

OpenSTEF's ``ForecastingModel`` and workflow components support continuous prediction cycles. When you call ``predict()``, the model uses all available data up to that moment:

.. code-block:: python

    from datetime import datetime
    from openstef.model.model import ForecastingModel
    from openstef.dataset.timeseries import TimeSeriesDataset
    
    # Assume model is already trained
    # model = ForecastingModel(...)
    
    # Generate forecast starting from current time
    forecast_start = datetime.now()
    forecast = model.predict(data=historical_data, forecast_start=forecast_start)
    
    # Forecast contains predictions for all configured horizons
    print(forecast.data.head())
    # Output shows quantile predictions at different timestamps

The ``forecast_start`` parameter defines when the forecast period begins. The model generates predictions for each configured horizon relative to this start time.

Data Availability and Versioning
---------------------------------

Short-term forecasting faces a practical challenge: not all data is available when you need to make a prediction. Weather forecasts arrive on schedules, consumption measurements have processing delays, and external data sources update asynchronously.

OpenSTEF's ``VersionedTimeSeriesDataset`` tracks when each data point became available, not just when it was measured:

.. code-block:: python

    from openstef.dataset.versioned_timeseries import VersionedTimeSeriesDataset
    import pandas as pd
    
    # Data with availability timestamps
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=24, freq="1h"),
        "load": [100, 105, 110, ...],
        "temperature": [5.2, 5.1, 5.3, ...],
        "available_at": pd.date_range("2024-01-01 00:05", periods=24, freq="1h"),
        "horizon": [timedelta(hours=1)] * 24,
    })
    
    dataset = VersionedTimeSeriesDataset.from_pandas(
        df, 
        sample_interval=timedelta(hours=1),
    )

The ``available_at`` column records when each measurement became available for forecasting. This enables realistic backtesting: you can simulate making predictions with only the data that would have been available at that historical moment.

Filtering by availability ensures your training and evaluation reflect real-world conditions:

.. code-block:: python

    from datetime import datetime
    
    # Get only data available before a specific time
    available_data = dataset.filter_by_available_before(
        datetime(2024, 1, 1, 12, 0)
    )
    
    # Train model with realistic data availability
    model.fit(available_data)

This versioning system is crucial for short-term forecasting where data freshness directly impacts accuracy.

Forecast Start Time and Prediction Windows
-------------------------------------------

When you generate a forecast, you specify a ``forecast_start`` time—the beginning of the prediction window. The model then produces predictions for each configured horizon relative to this start:

- Forecast start: 10:00
- Horizon 15 minutes: Predicts 10:15
- Horizon 1 hour: Predicts 11:00  
- Horizon 24 hours: Predicts 10:00 next day

The ``ForecastDataset`` returned by ``predict()`` contains predictions for all horizons:

.. code-block:: python

    forecast = model.predict(data=dataset, forecast_start=datetime(2024, 1, 1, 10, 0))
    
    # Access predictions for specific quantiles
    median_forecast = forecast.median_series
    lower_bound = forecast.quantiles_data["quantile_P10"]
    upper_bound = forecast.quantiles_data["quantile_P90"]

The forecast dataset includes timestamps, quantile predictions, and metadata about the forecast generation. See :doc:`quantiles_and_confidence` for details on interpreting probabilistic forecasts.

Why Short-Term Forecasting Is Different
----------------------------------------

Short-term forecasting requires different techniques than long-term prediction:

**Data patterns**: Recent observations matter more than distant history. A sudden temperature drop yesterday is more relevant than average temperatures from last year.

**Feature engineering**: Short-term models use lag features (consumption 1 hour ago, 24 hours ago) and recent weather changes. See :doc:`feature_engineering` for details on building effective features.

**Model selection**: Tree-based models like LightGBM and XGBoost excel at capturing complex short-term patterns. See :doc:`model_selection` for guidance on choosing appropriate models.

**Uncertainty quantification**: Short-term forecasts need probabilistic predictions to support risk management. Quantile forecasts provide confidence intervals that inform operational decisions.

**Production reliability**: Forecasts must be available on schedule even when data sources fail. See :doc:`reliability_and_fallback` for strategies to ensure continuous operation.

Next Steps
----------

Now that you understand short-term forecasting fundamentals, explore related topics:

- :doc:`quantiles_and_confidence` - Learn how to interpret and use probabilistic forecasts
- :doc:`feature_engineering` - Discover which features improve forecast accuracy
- :doc:`model_selection` - Choose the right forecasting model for your use case
- :doc:`reliability_and_fallback` - Ensure your forecasts remain available in production

For hands-on examples, see the ``examples/`` directory in the OpenSTEF repository, particularly ``configuring_model_pipeline_example.py`` which demonstrates a complete forecasting workflow.