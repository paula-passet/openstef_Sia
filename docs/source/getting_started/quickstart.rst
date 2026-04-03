Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For explanations of what's happening and why, see :doc:`first_forecast`.

Prerequisites
-------------

OpenSTEF installed:

.. code-block:: bash

   pip install openstef

If you haven't installed yet, see :doc:`installation`.

Minimal Working Example
------------------------

This example creates synthetic data, trains a model, and generates a forecast:

.. code-block:: python

   from datetime import timedelta
   import numpy as np
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_beam.forecasting import ForecastingModel
   from openstef_beam.forecasting.presets import ConstantMedianForecaster

   # Create sample data
   rng = np.random.default_rng(seed=42)
   data = pd.DataFrame(
       {
           "load": 100.0 + rng.normal(10.0, 5.0, 500),
           "temperature": 20.0 + rng.normal(1.0, 0.5, 500),
           "radiation": rng.uniform(0.0, 500.0, 500),
       },
       index=pd.date_range("2024-01-01", periods=500, freq="h", tz="UTC"),
   )
   
   # Wrap in OpenSTEF dataset
   dataset = TimeSeriesDataset(data, timedelta(hours=1))
   
   # Create and train model
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(),
       target_column="load",
   )
   model.train(dataset)
   
   # Generate forecast
   forecast = model.predict(dataset)
   
   print(forecast.data.head())

Expected output shows a DataFrame with forecasted load values and a datetime index.

What Just Happened
------------------

1. **Created synthetic data**: A pandas DataFrame with a datetime index and three columns (load, temperature, radiation)
2. **Wrapped it**: ``TimeSeriesDataset`` validates structure and sample interval
3. **Configured a model**: ``ForecastingModel`` with a simple ``ConstantMedianForecaster``
4. **Trained**: ``model.train()`` learns from historical data
5. **Predicted**: ``model.predict()`` generates forecasts

Using Your Own Data
-------------------

Replace the synthetic data with your own CSV file:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data
   df = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)
   
   # Ensure timezone-aware datetime index
   if df.index.tz is None:
       df.index = df.index.tz_localize("UTC")
   
   # Create dataset
   dataset = TimeSeriesDataset(df, timedelta(minutes=15))

Your CSV should have:

- First column: datetime index
- Remaining columns: target variable (e.g., "load") and features (e.g., "temperature")
- Regular time intervals (e.g., 15 minutes, 1 hour)

Example CSV structure:

.. code-block:: text

   datetime,load,temperature,radiation
   2024-01-01 00:00:00,95.3,18.2,0.0
   2024-01-01 01:00:00,92.1,17.8,0.0
   2024-01-01 02:00:00,89.5,17.5,0.0

Making a Real Forecast
----------------------

The minimal example predicts on the same data used for training. For a real forecast with a train/test split:

.. code-block:: python

   # Split data
   train_data = data[:"2024-01-15"]
   test_data = data["2024-01-16":]
   
   train_dataset = TimeSeriesDataset(train_data, timedelta(hours=1))
   test_dataset = TimeSeriesDataset(test_data, timedelta(hours=1))
   
   # Train on historical data
   model.train(train_dataset)
   
   # Predict on future data
   forecast = model.predict(test_dataset)

Next Steps
----------

This quickstart skips all explanations to get you running fast. Now that you have a working example:

- **Understand what happened**: :doc:`first_forecast` walks through each step with explanations
- **Compare models**: :doc:`backtesting` shows how to evaluate different forecasting approaches
- **Customize behavior**: :doc:`advanced_customization` covers feature engineering, model selection, and pipeline configuration

For production use, you'll want to understand model storage, feature engineering, and evaluation metrics. Start with :doc:`first_forecast`.