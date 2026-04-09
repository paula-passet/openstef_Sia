Short-Term Energy Forecasting Basics
=====================================

Short-term energy forecasting predicts electricity demand or generation from minutes to several days ahead. Unlike long-term forecasts that plan infrastructure years in advance, short-term forecasts support operational decisions: when to start generators, how to balance the grid, and what prices to set in energy markets.

OpenSTEF specializes in this operational forecasting domain, providing tools to build models that predict energy values at high temporal resolution with quantified uncertainty.

What Makes Forecasting "Short-Term"?
-------------------------------------

The distinction between short-term and long-term forecasting isn't just about time horizons—it's about fundamentally different modeling approaches and data requirements.

**Short-term forecasting** (hours to days ahead):

- Uses recent historical patterns and weather forecasts
- Captures intraday cycles, weekly patterns, and weather sensitivity
- Requires high-resolution data (15-minute to hourly intervals)
- Updates frequently as new data arrives
- Provides probabilistic predictions with uncertainty bounds

**Long-term forecasting** (months to years ahead):

- Uses aggregate trends and scenarios
- Focuses on seasonal patterns and structural changes
- Works with daily or monthly data
- Updates infrequently (quarterly or annually)
- Often deterministic or scenario-based

OpenSTEF focuses exclusively on short-term operational forecasting where recent patterns and weather conditions drive predictions.

Forecast Horizons and Lead Times
---------------------------------

A **forecast horizon** (or lead time) specifies how far into the future you're predicting. In OpenSTEF, horizons are represented as ``timedelta`` objects wrapped in the ``LeadTime`` type.

For example, predicting tomorrow's 14:00 load at today's 10:00 means a horizon of 28 hours. Predicting the next 15-minute interval has a horizon of 15 minutes.

Why horizons matter:

- **Data availability**: A 1-hour-ahead forecast can use very recent measurements; a 24-hour-ahead forecast cannot
- **Feature engineering**: Lag features must be further in the past than the horizon
- **Model accuracy**: Shorter horizons typically yield more accurate predictions
- **Operational needs**: Grid operators need different horizons for different decisions

OpenSTEF models specify their horizons explicitly:

.. code-block:: python

    from datetime import timedelta
    from openstef.model.forecaster import XGBForecaster
    from openstef.model.forecaster.base import LeadTime
    
    # Configure a forecaster for multiple horizons
    forecaster = XGBForecaster(
        horizons=[
            LeadTime(timedelta(minutes=15)),  # Very short-term
            LeadTime(timedelta(hours=1)),     # Short-term
            LeadTime(timedelta(hours=24)),    # Day-ahead
            LeadTime(timedelta(hours=47)),    # Maximum horizon
        ],
        quantiles=[0.1, 0.5, 0.9],  # Probabilistic forecasts
    )
    
    # Access the maximum horizon
    max_horizon = forecaster.max_horizon
    print(f"Maximum forecast horizon: {max_horizon.value}")

When training, OpenSTEF automatically ensures that lag features respect the maximum horizon—no feature uses data that wouldn't be available at prediction time.

Forecast Resolution and Frequency
----------------------------------

**Resolution** is the time interval between consecutive predictions. Energy forecasts commonly use:

- **15-minute resolution**: Standard for many European grid operators
- **Hourly resolution**: Common in energy markets and longer-term planning
- **5-minute resolution**: Used in some real-time balancing applications

**Frequency** is how often you generate new forecasts. You might produce hourly forecasts every 15 minutes as new data arrives, continuously updating your view of the future.

OpenSTEF datasets track resolution through the ``sample_interval`` attribute:

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef.data.dataset import VersionedTimeSeriesDataset
    
    # Create a dataset with 15-minute resolution
    timestamps = pd.date_range(
        start="2024-01-01",
        end="2024-01-02",
        freq="15min",
    )
    
    data = pd.DataFrame({
        "load": [100 + i * 0.5 for i in range(len(timestamps))],
        "temperature": [15 + i * 0.1 for i in range(len(timestamps))],
    }, index=timestamps)
    
    dataset = VersionedTimeSeriesDataset.from_pandas(
        data,
        sample_interval=timedelta(minutes=15),
        available_at=datetime(2024, 1, 2, 12, 0),
    )
    
    print(f"Dataset resolution: {dataset.sample_interval}")
    print(f"Number of samples per day: {timedelta(days=1) / dataset.sample_interval}")

The resolution affects feature engineering—15-minute data allows sub-hourly lag features (15, 30, 45 minutes), while hourly data uses only hourly lags.

Data Versioning and Available-At Times
---------------------------------------

A critical concept in short-term forecasting is **data versioning**: the same timestamp can have different values depending on when you query it. A load measurement at 14:00 might be preliminary at 14:05, revised at 14:30, and finalized days later.

OpenSTEF's ``VersionedTimeSeriesDataset`` tracks when each data point became available through the ``available_at`` attribute. This ensures training uses only data that would have been available at prediction time, preventing look-ahead bias.

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef.data.dataset import VersionedTimeSeriesDataset
    
    # Simulate data arriving over time
    timestamps = pd.date_range("2024-01-01", periods=96, freq="15min")
    
    df = pd.DataFrame({
        "load": range(100, 196),
        "available_at": [
            ts + timedelta(minutes=20)  # Data available 20 minutes after measurement
            for ts in timestamps
        ],
    }, index=timestamps)
    
    dataset = VersionedTimeSeriesDataset.from_pandas(
        df,
        sample_interval=timedelta(minutes=15),
        available_at_column="available_at",
    )
    
    # Filter to data available before a specific time
    cutoff = datetime(2024, 1, 1, 12, 0)
    available_data = dataset.filter_by_available_before(cutoff)
    
    print(f"Total samples: {len(dataset)}")
    print(f"Available before {cutoff}: {len(available_data)}")

This versioning is essential for realistic model evaluation and production deployment. See :doc:`reliability_and_fallback` for how OpenSTEF handles missing or delayed data in production.

Typical Forecasting Workflow
-----------------------------

A complete short-term forecasting workflow involves:

1. **Data preparation**: Load historical data with appropriate resolution
2. **Feature engineering**: Create lag features, weather inputs, and calendar features (see :doc:`feature_engineering`)
3. **Model configuration**: Choose horizons, quantiles, and forecaster type (see :doc:`model_selection`)
4. **Training**: Fit the model on historical data
5. **Prediction**: Generate forecasts for future timestamps
6. **Evaluation**: Assess accuracy and reliability (see :doc:`quantiles_and_confidence`)

Here's a minimal example:

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    from openstef.data.dataset import TrainingDataset
    from openstef.model.forecaster import XGBForecaster
    from openstef.model.forecaster.base import LeadTime
    from openstef.model.model import ForecastingModel
    from openstef.pipeline.preprocessing import FeaturePipeline
    
    # 1. Prepare training data (simplified example)
    timestamps = pd.date_range("2024-01-01", periods=1000, freq="15min")
    train_data = pd.DataFrame({
        "load": 100 + 20 * pd.np.sin(pd.np.arange(1000) * 2 * pd.np.pi / 96),
        "temperature": 15 + 5 * pd.np.cos(pd.np.arange(1000) * 2 * pd.np.pi / 96),
    }, index=timestamps)
    
    training_dataset = TrainingDataset.from_pandas(
        train_data,
        target_column="load",
        sample_interval=timedelta(minutes=15),
    )
    
    # 2. Configure model with preprocessing
    forecaster = XGBForecaster(
        horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=24))],
        quantiles=[0.1, 0.5, 0.9],
    )
    
    feature_pipeline = FeaturePipeline()  # Adds lag features automatically
    
    model = ForecastingModel(
        forecaster=forecaster,
        preprocessing=feature_pipeline,
    )
    
    # 3. Train
    model.fit(training_dataset)
    
    # 4. Predict
    forecast_start = datetime(2024, 1, 15, 0, 0)
    predictions = model.predict(
        data=training_dataset,
        forecast_start=forecast_start,
    )
    
    print(f"Forecast shape: {predictions.to_pandas().shape}")
    print(f"Quantiles: {predictions.quantiles}")

This example demonstrates the core pattern. Real applications add model storage, workflow orchestration, and fallback strategies—see the sibling pages for these topics.

Why Probabilistic Forecasts?
-----------------------------

Short-term energy forecasting inherently involves uncertainty: weather forecasts are imperfect, consumption patterns vary, and unexpected events occur. OpenSTEF emphasizes **probabilistic forecasting** through quantile predictions.

Instead of a single point prediction, you get multiple quantiles (e.g., 10th, 50th, 90th percentiles) that describe the full distribution of possible outcomes. This allows operators to make risk-aware decisions: use the median for expected values, the 90th percentile for reserve planning, and the 10th percentile for minimum generation requirements.

For detailed coverage of quantiles and uncertainty quantification, see :doc:`quantiles_and_confidence`.

Key Takeaways
-------------

- Short-term forecasting operates at high resolution (15-minute to hourly) over horizons from minutes to days
- Horizons determine data availability and feature engineering constraints
- Data versioning prevents look-ahead bias by tracking when information becomes available
- OpenSTEF models explicitly specify horizons and quantiles for transparent, reproducible forecasts
- Probabilistic predictions quantify uncertainty for risk-aware decision-making

For next steps, explore :doc:`feature_engineering` to learn what predictors drive accurate forecasts, or :doc:`model_selection` to choose the right forecasting algorithm for your use case.