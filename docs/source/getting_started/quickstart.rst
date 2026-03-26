Quickstart
==========

Get up and running with OpenSTEF in minutes. This guide shows you how to train your first forecasting model and generate predictions with minimal setup.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

For development or full functionality, install with all extras:

.. code-block:: bash

   pip install "openstef[all]"

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import ForecastInputDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_core.types import LeadTime

   # Load your data (replace with your actual data source)
   # Data should have datetime index and columns: load, temperature, etc.
   df = pd.read_csv("your_energy_data.csv", index_col=0, parse_dates=True)
   
   # Create dataset - OpenSTEF expects 15-minute intervals by default
   dataset = ForecastInputDataset(
       data=df,
       target_column="load",  # Your energy consumption column
       sample_interval=timedelta(minutes=15)
   )
   
   # Configure forecaster for 36-hour ahead predictions
   forecaster = XGBoostForecaster(
       horizons=[LeadTime.from_string("PT36H")]
   )
   
   # Create and train model
   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=14)
   )
   
   # Split data for training (use last 20% for validation)
   split_point = int(len(df) * 0.8)
   train_data = dataset.slice_time(end_index=split_point)
   
   # Train the model
   fit_result = model.fit(train_data)
   print(f"Training completed. MAE: {fit_result.metrics.get('mae', 'N/A')}")
   
   # Generate forecasts for new data
   forecast_data = dataset.slice_time(start_index=split_point)
   forecasts = model.predict(forecast_data)
   
   # Access predictions
   print("Forecast quantiles available:", forecasts.quantiles)
   print("Forecast data shape:", forecasts.data.shape)

Data Requirements
-----------------

OpenSTEF expects time series data with:

- **DateTime index**: Regular intervals (typically 15 minutes)
- **Target column**: Energy values to forecast (default name: "load")
- **Weather features**: Temperature, solar radiation, wind speed (optional but recommended)
- **Minimum history**: At least 2 weeks of data for reliable training

Example data structure:

.. code-block:: python

   # Your DataFrame should look like this:
   #                     load  temperature  solar_radiation
   # 2024-01-01 00:00:00  150.5        2.1             0.0
   # 2024-01-01 00:15:00  148.2        2.0             0.0
   # 2024-01-01 00:30:00  145.8        1.9             0.0

Understanding Results
---------------------

OpenSTEF produces probabilistic forecasts with multiple quantiles:

.. code-block:: python

   # Access different forecast quantiles
   forecast_df = forecasts.data
   
   # Common quantiles (if available):
   median_forecast = forecast_df["q50"]      # 50th percentile (median)
   lower_bound = forecast_df["q10"]          # 10th percentile
   upper_bound = forecast_df["q90"]          # 90th percentile
   
   # Plot results
   import matplotlib.pyplot as plt
   
   plt.figure(figsize=(12, 6))
   plt.plot(forecast_df.index, median_forecast, label="Forecast (median)")
   plt.fill_between(forecast_df.index, lower_bound, upper_bound, 
                    alpha=0.3, label="80% confidence interval")
   plt.legend()
   plt.show()

Next Steps
----------

Now that you have a working forecast:

- **Improve accuracy**: Add weather data and tune hyperparameters
- **Learn more**: Follow the comprehensive tutorials guide
- **Explore use cases**: See the use cases guide for specific applications
- **Production deployment**: Check the how-to guides for deployment patterns

.. note::
   This quickstart uses default settings optimized for common energy forecasting scenarios. For production use, consider customizing the preprocessing pipeline, feature engineering, and model hyperparameters based on your specific data characteristics.