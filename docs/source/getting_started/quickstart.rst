Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For detailed explanations of what's happening, see :doc:`first_forecast`.

Prerequisites
-------------

OpenSTEF must be installed. If you haven't done this yet::

   pip install openstef

See :doc:`installation` for system requirements and alternative installation methods.

Minimal working example
-----------------------

This example creates synthetic data, trains a model, and generates a forecast:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   import numpy as np
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting import ConstantMedianForecaster
   from openstef_models.preprocessing import FeaturePipeline

   # Create synthetic training data
   dates = pd.date_range(
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
       freq="15min"
   )
   
   data = pd.DataFrame({
       "load": np.random.uniform(100, 200, len(dates)) + 
               50 * np.sin(np.arange(len(dates)) * 2 * np.pi / 96),  # Daily pattern
       "temp": np.random.uniform(5, 25, len(dates)),
   }, index=dates)
   
   # Wrap in OpenSTEF dataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )
   
   # Configure forecasting model
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(horizons=[1, 4, 8, 12]),
       preprocessing=FeaturePipeline(),
   )
   
   # Train the model
   model.fit(data=dataset)
   
   # Create forecast input data (last 7 days)
   forecast_start = datetime(2024, 4, 1)
   forecast_dates = pd.date_range(
       start=forecast_start - timedelta(days=7),
       end=forecast_start + timedelta(hours=47, minutes=45),
       freq="15min"
   )
   
   forecast_data = pd.DataFrame({
       "load": np.random.uniform(100, 200, len(forecast_dates)),
       "temp": np.random.uniform(5, 25, len(forecast_dates)),
   }, index=forecast_dates)
   
   forecast_dataset = TimeSeriesDataset(
       data=forecast_data,
       sample_interval=timedelta(minutes=15),
       target_column="load",
       forecast_start=forecast_start
   )
   
   # Generate predictions
   predictions = model.predict(data=forecast_dataset)
   
   # Access forecast results
   forecast_df = predictions.data
   print(forecast_df.head())
   print(f"\nForecast shape: {forecast_df.shape}")
   print(f"Horizons: {predictions.horizons}")

Run this code and you'll see forecast output with multiple horizons. The predictions DataFrame contains columns for each forecast horizon (1, 4, 8, 12 steps ahead).

What just happened
------------------

The example follows OpenSTEF's standard workflow:

1. **Data preparation**: Historical data wrapped in a ``TimeSeriesDataset`` with datetime index and target column
2. **Model configuration**: A ``ForecastingModel`` combining a forecaster algorithm with preprocessing
3. **Training**: The ``fit()`` method learns patterns from historical data
4. **Prediction**: The ``predict()`` method generates forecasts for multiple horizons

The ``ConstantMedianForecaster`` is a simple baseline model that predicts the median value for each horizon. Real forecasts typically use more sophisticated models like XGBoost or LightGBM.

Using real data
---------------

Replace the synthetic data with your own time series. Requirements:

- Pandas DataFrame with DatetimeIndex
- Target column (e.g., energy load)
- Optional: weather features, calendar features, or other predictors
- Regular sampling interval (e.g., 15min, 1h)

Example with CSV data:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data
   df = pd.read_csv("energy_data.csv", index_col="timestamp", parse_dates=True)
   
   # Ensure regular frequency
   df = df.asfreq("15min")
   
   # Create dataset
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )

Your CSV should have a timestamp column and at least one target column (energy load, demand, generation, etc.).

Next steps
----------

This quickstart used minimal configuration. To build production-ready forecasts:

- **Learn the workflow**: :doc:`first_forecast` explains each step in detail with best practices
- **Evaluate models**: :doc:`backtesting` shows how to compare different forecasters
- **Customize behavior**: :doc:`advanced_customization` covers feature engineering, model tuning, and postprocessing

For API details, see the :doc:`../api/index` reference documentation.