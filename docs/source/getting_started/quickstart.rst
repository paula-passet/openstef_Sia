Quickstart
==========

This page shows you how to create your first forecast with OpenSTEF in just a few steps. OpenSTEF is a Python machine learning library for short-term energy forecasting that handles the complete pipeline from data preparation to prediction.

Creating Your First Forecast
-----------------------------

Here's a minimal example that trains a model and generates a forecast:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig, 
       create_forecasting_workflow
   )

   # Create sample data with load and weather features
   index = pd.date_range(
       start="2024-01-01", 
       end="2024-03-01", 
       freq="15T"
   )
   
   data = pd.DataFrame(index=index)
   data['load'] = 100 + 50 * np.sin(index.hour * np.pi / 12) + np.random.normal(0, 10, len(index))
   data['temperature'] = 15 + 10 * np.sin((index.dayofyear - 80) * 2 * np.pi / 365)
   data['windspeed_100m'] = 5 + 3 * np.random.random(len(index))
   data['radiation'] = np.maximum(0, 500 * np.sin(index.hour * np.pi / 12) * (index.hour >= 6) * (index.hour <= 18))

   # Convert to OpenSTEF dataset format
   dataset = TimeSeriesDataset.from_pandas(data, sample_interval=timedelta(minutes=15))

   # Create and configure the forecasting workflow
   config = ForecastingWorkflowConfig()
   workflow = create_forecasting_workflow(config)

   # Split data for training and forecasting
   split_time = datetime(2024, 2, 15)
   train_data = dataset.filter_by_range(end=split_time)
   forecast_data = dataset.filter_by_range(start=split_time)

   # Train the model
   workflow.fit(train_data)

   # Generate forecasts
   forecasts = workflow.predict(forecast_data, forecast_start=split_time)

   # Access forecast results
   forecast_df = forecasts.to_pandas()
   print(f"Generated {len(forecast_df)} forecast points")
   print(f"Forecast columns: {forecast_df.columns.tolist()}")

What Just Happened?
^^^^^^^^^^^^^^^^^^^

1. **Data Preparation**: We created a synthetic dataset with load measurements and weather features (temperature, wind speed, solar radiation)
2. **Model Training**: The workflow automatically selected appropriate preprocessing, feature engineering, and forecasting algorithms
3. **Forecasting**: We generated probabilistic forecasts with confidence intervals for future time periods

The resulting forecast contains quantile predictions (e.g., 10th, 50th, 90th percentiles) that capture forecast uncertainty.

Working with Real Data
----------------------

For production use, replace the synthetic data with your actual measurements:

.. code-block:: python

   # Load your data (CSV, database, API, etc.)
   df = pd.read_csv('your_data.csv', index_col='timestamp', parse_dates=True)
   
   # Ensure your data has a 'load' column and weather features
   # Required columns: load (target variable)
   # Recommended: temperature, windspeed_100m, radiation
   
   dataset = TimeSeriesDataset.from_pandas(df, sample_interval=timedelta(minutes=15))

Next Steps
----------

This quickstart gets you forecasting immediately with default settings. For production deployments and advanced customization:

- Follow the comprehensive tutorials for detailed explanations
- Check the use cases guide to identify your specific forecasting scenario  
- See the how-to guides for deployment and integration patterns

The default configuration works well for most energy forecasting scenarios, but OpenSTEF provides extensive customization options when you need them.