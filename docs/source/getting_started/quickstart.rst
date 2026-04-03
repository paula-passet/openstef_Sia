Quickstart
==========

Get your first forecast running in under 5 minutes. This page provides a minimal, copy-paste ready example using synthetic data.

For detailed explanations of each step, see :doc:`first_forecast`. For installation instructions, see :doc:`installation`.

Complete Working Example
-------------------------

This example creates synthetic load data, trains a model, and generates a forecast:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models.xgb import XGBModel
   from openstef_models.pipelines.forecasting_model import ForecastingModel
   from openstef_models.pipelines.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.features import AddHolidayFeatures, AddLagFeatures
   from openstef_models.transforms.general import Scaler
   
   # Create synthetic training data (7 days, 15-minute intervals)
   dates = pd.date_range(
       start=datetime(2024, 1, 1),
       end=datetime(2024, 1, 7),
       freq="15min"
   )
   
   # Simulate daily load pattern with some noise
   hours = dates.hour + dates.minute / 60
   load = 100 + 50 * np.sin((hours - 6) * np.pi / 12) + np.random.normal(0, 5, len(dates))
   
   data = pd.DataFrame({
       'load': load,
       'temp': 15 + 5 * np.sin(hours * np.pi / 12) + np.random.normal(0, 2, len(dates))
   }, index=dates)
   
   # Wrap in OpenSTEF dataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )
   
   # Configure feature engineering pipeline
   feature_pipeline = FeaturePipeline(
       transforms=[
           AddHolidayFeatures(country="NL"),
           AddLagFeatures(lags=[96, 672]),  # 1 day and 1 week lags
           Scaler()
       ]
   )
   
   # Create forecasting model
   model = ForecastingModel(
       model=XGBModel(),
       feature_pipeline=feature_pipeline
   )
   
   # Train the model
   model.fit(dataset)
   
   # Generate 24-hour forecast
   forecast_input = dataset.get_latest_data(
       lookback=timedelta(days=7)
   )
   
   forecast = model.predict(
       data=forecast_input,
       forecast_start=dates[-1] + timedelta(minutes=15),
       horizon=timedelta(hours=24)
   )
   
   print(f"Generated {len(forecast)} forecast points")
   print(forecast.head())

What Just Happened
------------------

The code above:

1. **Created synthetic data** - A week of 15-minute load measurements with temperature
2. **Wrapped it in a dataset** - ``TimeSeriesDataset`` handles time series validation
3. **Configured features** - Holiday indicators, lag features, and scaling
4. **Trained a model** - XGBoost with the configured feature pipeline
5. **Generated a forecast** - 24 hours ahead from the last training point

The output is a pandas DataFrame with forecast values indexed by timestamp.

Running With Your Own Data
---------------------------

Replace the synthetic data creation with your own CSV or database:

.. code-block:: python

   # Load from CSV with datetime index
   data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)
   
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )

Your data must have:

- A datetime index
- A ``load`` column (or specify ``target_column`` parameter)
- Consistent time intervals matching ``sample_interval``

Next Steps
----------

- :doc:`first_forecast` - Detailed tutorial explaining each component
- :doc:`advanced_customization` - Customize models, features, and pipelines
- :doc:`backtesting` - Evaluate forecast accuracy on historical data