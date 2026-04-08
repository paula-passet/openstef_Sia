Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For explanations of what's happening and why, see :doc:`first_forecast`.

Prerequisites
-------------

OpenSTEF must be installed. If you haven't done this yet, see :doc:`installation`.

Minimal Working Example
-----------------------

This example creates synthetic data, trains a model, and generates a forecast. Copy this into a Python file or notebook:

.. code-block:: python

    from datetime import datetime, timedelta
    from pathlib import Path
    
    import numpy as np
    import pandas as pd
    
    from openstef_core.datasets import VersionedTimeSeriesDataset
    from openstef_core.models.forecasting_model import ForecastingModel
    from openstef_core.models.constant_median import ConstantMedianForecaster
    from openstef_core.models.feature_pipeline import FeaturePipeline
    from openstef_core.models.storage import LocalModelStorage
    from openstef_core.workflows.forecasting_workflow import CustomForecastingWorkflow
    
    # Create synthetic time series data
    dates = pd.date_range(
        start=datetime(2024, 1, 1),
        end=datetime(2024, 3, 31),
        freq="15min"
    )
    
    data = pd.DataFrame({
        "datetime": dates,
        "load": 100 + 50 * np.sin(np.arange(len(dates)) * 2 * np.pi / 96) + np.random.randn(len(dates)) * 5,
    })
    data.set_index("datetime", inplace=True)
    
    # Wrap in OpenSTEF dataset
    dataset = VersionedTimeSeriesDataset(
        data=data,
        sample_interval=timedelta(minutes=15),
        version=datetime.now()
    )
    
    # Configure the forecasting model
    feature_pipeline = FeaturePipeline(
        add_holiday_features=True,
        add_lag_features=True,
        scale_features=True
    )
    
    model = ForecastingModel(
        forecaster=ConstantMedianForecaster(),
        feature_pipeline=feature_pipeline
    )
    
    # Set up model storage
    storage = LocalModelStorage(base_path=Path("./models"))
    
    # Create workflow
    workflow = CustomForecastingWorkflow(
        model=model,
        storage=storage
    )
    
    # Train the model
    print("Training model...")
    workflow.train(dataset, target_column="load")
    
    # Generate forecast
    print("Generating forecast...")
    forecast_start = datetime(2024, 4, 1)
    forecast = workflow.predict(
        dataset=dataset,
        forecast_start=forecast_start,
        horizon_hours=24
    )
    
    print(f"\nForecast generated for {len(forecast)} time steps")
    print(forecast.head())

Run this code. You should see training output followed by a forecast DataFrame.

What Just Happened
------------------

The code above:

1. **Created synthetic data** - A sine wave representing daily load patterns with noise
2. **Wrapped it in a dataset** - OpenSTEF's ``VersionedTimeSeriesDataset`` structure
3. **Configured a model** - A simple constant median forecaster with feature engineering
4. **Trained the model** - Using historical data to learn patterns
5. **Generated a forecast** - 24-hour ahead predictions

Using Your Own Data
-------------------

Replace the synthetic data section with your own CSV or DataFrame:

.. code-block:: python

    # Load from CSV
    data = pd.read_csv("your_data.csv", parse_dates=["datetime"], index_col="datetime")
    
    # Your data needs:
    # - DatetimeIndex
    # - A target column (e.g., "load", "power", "demand")
    # - Regular time intervals (e.g., 15min, 1h)
    
    dataset = VersionedTimeSeriesDataset(
        data=data,
        sample_interval=timedelta(minutes=15),  # Match your data's interval
        version=datetime.now()
    )

Your data must have a datetime index and at least one numeric column to forecast.

Next Steps
----------

This quickstart used default settings and a simple model. To understand what each component does and how to customize them:

- **Learn the concepts** - See :doc:`first_forecast` for a step-by-step tutorial with explanations
- **Compare models** - See :doc:`backtesting` to evaluate different forecasting approaches
- **Customize everything** - See :doc:`advanced_customization` for power user features

The quickstart uses ``ConstantMedianForecaster`` for simplicity. For real forecasting tasks, you'll want to explore other models like XGBoost or LightGBM, which are covered in the first forecast tutorial.

Troubleshooting
---------------

**Import errors**: Ensure OpenSTEF is installed with ``pip install openstef``

**Data errors**: Check that your datetime index is sorted and has no gaps

**Model storage errors**: The ``LocalModelStorage`` creates a ``./models`` directory. Ensure you have write permissions.

For detailed troubleshooting and common issues, see the :doc:`first_forecast` tutorial.