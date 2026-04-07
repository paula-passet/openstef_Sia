Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For explanations of what's happening and why, see :doc:`first_forecast`.

Prerequisites
-------------

OpenSTEF installed::

   pip install openstef

That's it. The example below uses synthetic data, so no external data sources are needed.

Minimal Working Example
------------------------

This complete example trains a forecasting model and generates predictions:

.. code-block:: python

   from datetime import datetime, timedelta
   import numpy as np
   import pandas as pd
   
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.model.regressors import XGBQuantileOpenstfRegressor
   from openstef_beam.workflows import CustomForecastingWorkflow
   from openstef_beam.storage import LocalModelStorage
   
   # Create synthetic training data (7 days, 15-min intervals)
   dates = pd.date_range(
       start="2024-01-01", 
       end="2024-01-08", 
       freq="15min"
   )
   data = pd.DataFrame({
       "load": 100 + 20 * np.sin(np.arange(len(dates)) * 2 * np.pi / 96) + np.random.randn(len(dates)) * 5,
   }, index=dates)
   
   # Wrap in OpenSTEF dataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )
   
   # Configure model
   model = XGBQuantileOpenstfRegressor()
   
   # Set up storage
   storage = LocalModelStorage(base_path="./models")
   
   # Create workflow
   workflow = CustomForecastingWorkflow(
       model=model,
       storage=storage
   )
   
   # Train model
   workflow.train(
       train_data=dataset,
       model_id="quickstart_model"
   )
   
   # Generate 48-hour forecast
   forecast = workflow.predict(
       predict_data=dataset,
       model_id="quickstart_model",
       forecast_start=datetime(2024, 1, 8),
       horizon_hours=48
   )
   
   print(forecast.data.head())

Expected output::

                         forecast  forecast_quantile_0.1  forecast_quantile_0.9
   2024-01-08 00:00:00     98.234                 92.145                104.323
   2024-01-08 00:15:00     99.876                 93.787                105.965
   2024-01-08 00:30:00    101.523                 95.434                107.612
   ...

What Just Happened
------------------

1. **Created synthetic data**: A sine wave representing daily load patterns with noise
2. **Wrapped in TimeSeriesDataset**: OpenSTEF's data container with validation
3. **Configured XGBoost model**: A quantile regression model for probabilistic forecasts
4. **Trained the model**: Learned patterns from the 7-day history
5. **Generated forecast**: Predicted 48 hours ahead with confidence intervals

The model automatically:

- Engineered time-based features (hour of day, day of week)
- Handled missing values
- Generated quantile predictions (10th, 50th, 90th percentiles)

Using Your Own Data
-------------------

Replace the synthetic data with your own time series. Requirements:

- Pandas DataFrame with DatetimeIndex
- Regular sampling interval (e.g., 15 minutes, 1 hour)
- Numeric target column (default name: ``load``)

.. code-block:: python

   # Load from CSV
   data = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)
   
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(hours=1),
       target_column="power"  # if not named "load"
   )

Your CSV should look like::

   datetime,power
   2024-01-01 00:00:00,102.3
   2024-01-01 01:00:00,98.7
   2024-01-01 02:00:00,95.1
   ...

Next Steps
----------

Now that you have a working forecast:

- **Understand the process**: Read :doc:`first_forecast` for detailed explanations of each step
- **Evaluate performance**: See :doc:`backtesting` to compare model accuracy
- **Customize the pipeline**: Check :doc:`advanced_customization` for feature engineering, model selection, and hyperparameter tuning
- **Production deployment**: Explore the workflows documentation for scheduling and monitoring

Common Issues
-------------

**Import errors**: Verify installation with ``pip show openstef``

**Data validation errors**: Ensure your DataFrame has a DatetimeIndex and regular intervals

**Model training fails**: Check you have enough data (at least 48 hours recommended)

**Forecast is constant**: The synthetic example is simple - real data with patterns will produce better forecasts

For installation problems, see :doc:`installation`.