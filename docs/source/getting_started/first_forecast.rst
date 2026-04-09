Creating Your First Forecast
=============================

This tutorial walks you through creating a complete forecast from start to finish. You'll learn how to prepare your data, configure a model, train it, generate predictions, and evaluate the results. By the end, you'll understand not just *how* to create a forecast, but *why* each step matters.

.. note:: [DIAGRAM: Flowchart showing the forecasting workflow: Data Preparation (raw data → cleaned dataset) → Feature Engineering (add temporal/derived features) → Model Training (split data → train forecaster) → Prediction (generate forecast) → Evaluation (calculate metrics). Include decision point: "Validation data available?" branching to optional validation split.]

This page assumes you've already installed OpenSTEF. If not, see :doc:`installation` first. For the absolute minimal example, check :doc:`quickstart`.

Understanding the Forecasting Workflow
---------------------------------------

Before diving into code, let's understand the five key stages:

1. **Data Preparation**: Load and validate your time series data with features and target values
2. **Feature Engineering**: Add temporal features (hour of day, day of week) and domain-specific features (weather derivatives, lag features)
3. **Model Training**: Split your data and train a forecaster on historical patterns
4. **Prediction**: Generate forecasts for future time periods
5. **Evaluation**: Measure forecast quality using metrics like MAE and RMSE

Each stage transforms your data, building toward the final forecast. Let's work through them step by step.

Step 1: Preparing Your Data
----------------------------

OpenSTEF expects your data as a pandas DataFrame with a datetime index. You need at least:

- A **target column**: the value you want to forecast (e.g., energy load)
- **Feature columns**: predictors like temperature, hour of day, or historical values

Here's how to prepare a basic dataset:

.. code-block:: python

    import pandas as pd
    from openstef.data_classes.time_series_dataset import TimeSeriesDataset
    
    # Load your raw data (example with CSV)
    raw_data = pd.read_csv("energy_data.csv", parse_dates=["timestamp"])
    raw_data.set_index("timestamp", inplace=True)
    
    # Ensure regular sampling (15-minute intervals common for energy)
    raw_data = raw_data.asfreq("15T")
    
    # Handle missing values
    raw_data = raw_data.interpolate(method="time", limit=4)
    
    # Create TimeSeriesDataset
    dataset = TimeSeriesDataset(
        data=raw_data,
        target_column="load_mw",
        sample_interval=pd.Timedelta("15T")
    )

**Why this matters**: Regular sampling ensures consistent forecast horizons. Interpolation fills small gaps without introducing bias. The ``TimeSeriesDataset`` wrapper adds metadata that OpenSTEF uses throughout the pipeline.

**Common pitfalls**:

- Irregular timestamps cause horizon calculation errors
- Too much missing data (>10%) degrades forecast quality
- Mismatched timezones between features and target create alignment issues

Step 2: Engineering Features
-----------------------------

Raw data rarely contains all the patterns a model needs. Feature engineering adds temporal structure and domain knowledge:

.. code-block:: python

    from openstef.feature_engineering.feature_adder import (
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        CyclicFeaturesAdder,
    )
    from openstef.preprocessing.preprocessing_pipeline import PreprocessingPipeline
    
    # Build feature engineering pipeline
    feature_pipeline = PreprocessingPipeline(
        steps=[
            DatetimeFeaturesAdder(onehot_encode=True),
            HolidayFeatureAdder(country_code="NL"),
            CyclicFeaturesAdder(),
        ]
    )
    
    # Transform the dataset
    engineered_dataset = feature_pipeline.transform(data=dataset)

**What each feature adder does**:

- ``DatetimeFeaturesAdder``: Extracts hour, day of week, month. One-hot encoding creates binary features for each value, helping models learn daily and weekly patterns.
- ``HolidayFeatureAdder``: Marks public holidays, which often show different energy consumption patterns.
- ``CyclicFeaturesAdder``: Converts periodic features (hour, month) to sine/cosine pairs so hour 23 is "close" to hour 0.

**When to add more features**: If you have weather data, use ``AtmosphereDerivedFeaturesAdder`` or ``RadiationDerivedFeaturesAdder``. For solar/wind forecasting, add ``WindPowerFeatureAdder``. For capturing recent trends, use ``RollingAggregatesAdder``.

Step 3: Training a Model
-------------------------

Now we configure and train a forecaster. OpenSTEF provides several model types; we'll use XGBoost for its balance of speed and accuracy:

.. code-block:: python

    from openstef.model.regressors.xgb import XGBOpenstfRegressor
    from openstef.model.forecaster import Forecaster
    from datetime import timedelta
    
    # Define forecast horizons (in minutes)
    horizons = [15, 30, 60, 120, 240]  # 15 min to 4 hours ahead
    
    # Configure the forecaster
    forecaster = Forecaster(
        model=XGBOpenstfRegressor(),
        horizons=horizons,
        quantiles=[0.1, 0.5, 0.9],  # Probabilistic forecasts
        target_column="load_mw"
    )
    
    # Split data: use last 7 days for validation
    split_date = engineered_dataset.index.max() - timedelta(days=7)
    train_data = engineered_dataset.filter_by_range(end=split_date)
    val_data = engineered_dataset.filter_by_range(start=split_date)
    
    # Train the model
    forecaster.fit(
        data=train_data,
        data_val=val_data
    )

**Understanding the configuration**:

- **Horizons**: Define how far ahead to forecast. Multiple horizons train separate models optimized for each lead time.
- **Quantiles**: Produce probabilistic forecasts. 0.5 is the median (most likely), 0.1 and 0.9 give uncertainty bounds.
- **Validation data**: Monitors overfitting during training. The model stops early if validation error stops improving.

**Why split chronologically**: Time series data has temporal dependencies. Random splits leak future information into training. Always split by date.

Step 4: Generating Predictions
-------------------------------

With a trained model, you can forecast future values. You need historical context (features up to the forecast start) to generate predictions:

.. code-block:: python

    from datetime import datetime
    
    # Define when to start forecasting
    forecast_start = datetime(2024, 1, 15, 0, 0)
    
    # Prepare input data (features up to forecast start)
    input_data = engineered_dataset.filter_by_range(end=forecast_start)
    
    # Generate forecast
    forecast = forecaster.predict(
        data=input_data,
        forecast_start=forecast_start
    )
    
    # Access predictions
    print(forecast.forecast_series)  # Median forecast (quantile 0.5)
    print(forecast.quantile_forecasts)  # All quantile predictions

**What happens during prediction**:

1. The forecaster extracts features for each horizon's target time
2. Each horizon-specific model generates predictions
3. Quantile forecasts provide uncertainty estimates
4. Results are packaged in a ``ForecastDataset`` with metadata

**Using the forecast**: The ``forecast_series`` gives point predictions for plotting or decision-making. The ``quantile_forecasts`` DataFrame contains columns like ``forecast_0.1`` and ``forecast_0.9`` for confidence intervals.

Step 5: Evaluating Performance
-------------------------------

Evaluation measures how well your forecast matches reality. You need ground truth (actual values) for the forecast period:

.. code-block:: python

    from openstef.metrics.evaluation_pipeline import EvaluationPipeline
    from openstef.metrics.evaluation_config import EvaluationConfig
    from openstef.metrics.metrics import mae, rmse, bias
    
    # Configure evaluation
    eval_config = EvaluationConfig(
        available_ats=[],  # No availability filtering
        lead_times=horizons  # Evaluate each horizon
    )
    
    eval_pipeline = EvaluationPipeline(
        config=eval_config,
        quantiles=[0.1, 0.5, 0.9],
        global_metric_providers=[mae, rmse, bias]
    )
    
    # Run evaluation (requires forecast with target values)
    evaluation_result = eval_pipeline.run(
        predictions=forecast,
        ground_truth=val_data,
        target_column="load_mw"
    )
    
    # View results
    for subset_report in evaluation_result.subset_reports:
        print(f"Horizon: {subset_report.filtering}")
        print(f"MAE: {subset_report.metrics['MAE']:.2f}")
        print(f"RMSE: {subset_report.metrics['RMSE']:.2f}")

**Understanding the metrics**:

- **MAE (Mean Absolute Error)**: Average prediction error in the same units as your target. Lower is better.
- **RMSE (Root Mean Squared Error)**: Penalizes large errors more than MAE. Useful for detecting outliers.
- **Bias**: Average signed error. Positive means over-forecasting, negative means under-forecasting.

**Interpreting results**: Compare metrics across horizons. Longer horizons typically have higher errors. If one horizon performs poorly, consider adding features relevant to that time scale (e.g., weather forecasts for longer horizons).

Putting It All Together
------------------------

Here's a complete example combining all steps:

.. code-block:: python

    import pandas as pd
    from datetime import datetime, timedelta
    from openstef.data_classes.time_series_dataset import TimeSeriesDataset
    from openstef.feature_engineering.feature_adder import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
    )
    from openstef.preprocessing.preprocessing_pipeline import PreprocessingPipeline
    from openstef.model.regressors.xgb import XGBOpenstfRegressor
    from openstef.model.forecaster import Forecaster
    
    # 1. Load and prepare data
    raw_data = pd.read_csv("energy_data.csv", parse_dates=["timestamp"])
    raw_data.set_index("timestamp", inplace=True)
    raw_data = raw_data.asfreq("15T").interpolate(method="time")
    
    dataset = TimeSeriesDataset(
        data=raw_data,
        target_column="load_mw",
        sample_interval=pd.Timedelta("15T")
    )
    
    # 2. Engineer features
    feature_pipeline = PreprocessingPipeline(
        steps=[
            DatetimeFeaturesAdder(onehot_encode=True),
            CyclicFeaturesAdder(),
        ]
    )
    engineered = feature_pipeline.transform(data=dataset)
    
    # 3. Train model
    split_date = engineered.index.max() - timedelta(days=7)
    train_data = engineered.filter_by_range(end=split_date)
    val_data = engineered.filter_by_range(start=split_date)
    
    forecaster = Forecaster(
        model=XGBOpenstfRegressor(),
        horizons=[15, 60, 240],
        quantiles=[0.1, 0.5, 0.9],
        target_column="load_mw"
    )
    forecaster.fit(data=train_data, data_val=val_data)
    
    # 4. Generate forecast
    forecast_start = val_data.index.min()
    forecast = forecaster.predict(
        data=train_data,
        forecast_start=forecast_start
    )
    
    # 5. Evaluate
    score = forecaster.score(data=val_data)
    print(f"Validation MAE: {score.metrics.get('MAE', 'N/A')}")

Next Steps
----------

You now understand the complete forecasting workflow. To deepen your skills:

- **Compare models**: See :doc:`backtesting` to systematically test different configurations
- **Customize pipelines**: Learn advanced techniques in :doc:`advanced_customization`
- **Production deployment**: Explore the workflows module for operational forecasting

The key to good forecasts is iteration: try different features, tune hyperparameters, and always validate on held-out data. Start simple, measure performance, then add complexity only where it helps.