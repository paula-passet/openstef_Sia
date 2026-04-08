Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For detailed explanations of what's happening, see :doc:`first_forecast`.

What You'll Do
--------------

1. Create sample data
2. Configure a forecasting model
3. Train and predict
4. Done

The Complete Example
---------------------

Here's the entire working code. Copy this into a Python file or notebook:

.. code-block:: python

    from datetime import datetime, timedelta
    import pandas as pd
    import numpy as np
    from openstef_core.datasets import ForecastInputDataset
    from openstef_models.forecasting.models import XGBQuantileForecaster
    from openstef_models.forecasting.model import ForecastingModel
    from openstef_models.forecasting.feature_pipeline import FeaturePipeline
    from openstef_models.forecasting.workflow import CustomForecastingWorkflow
    
    # 1. Create sample data (7 days of hourly load data)
    dates = pd.date_range(start='2024-01-01', periods=168, freq='h')
    load = 100 + 20 * np.sin(np.arange(168) * 2 * np.pi / 24) + np.random.randn(168) * 5
    
    data = pd.DataFrame({
        'load': load,
    }, index=dates)
    
    dataset = ForecastInputDataset(
        data=data,
        sample_interval=timedelta(hours=1),
        target_column='load'
    )
    
    # 2. Configure the forecasting model
    model = ForecastingModel(
        forecaster=XGBQuantileForecaster(),
        feature_pipeline=FeaturePipeline(),
    )
    
    # 3. Create workflow and train
    workflow = CustomForecastingWorkflow(model=model)
    workflow.fit(data=dataset)
    
    # 4. Generate forecast
    forecast_start = datetime(2024, 1, 8)
    forecast = workflow.predict(data=dataset, forecast_start=forecast_start)
    
    # 5. View results
    print(forecast.to_pandas().head())

Run this code and you'll see forecast output with quantile predictions (P10, P50, P90).

What Just Happened?
-------------------

**Sample Data**: Created a week of synthetic hourly load data with daily patterns and noise.

**Model Configuration**: Set up an XGBoost quantile forecaster with default feature engineering (the ``FeaturePipeline`` automatically adds time-based features like hour of day, day of week).

**Training**: The ``fit()`` method trains the model on your historical data.

**Prediction**: The ``predict()`` method generates probabilistic forecasts starting from your specified timestamp.

Next Steps
----------

**Understand the concepts**: Read :doc:`first_forecast` for detailed explanations of each component.

**Use real data**: Replace the synthetic data with your own time series. Ensure it has a datetime index and a target column (e.g., 'load').

**Evaluate performance**: See :doc:`backtesting` to compare different models and validate accuracy.

**Customize the model**: Explore :doc:`advanced_customization` to add features, tune hyperparameters, or use different algorithms.

Common Issues
-------------

**Import errors**: Make sure OpenSTEF is installed. See :doc:`installation`.

**Data format errors**: Your data must have a datetime index and numeric values. Check for missing timestamps or non-numeric data.

**Insufficient data**: XGBoost needs at least a few days of data to learn patterns. If you have less than 24 hours, try a simpler model first.