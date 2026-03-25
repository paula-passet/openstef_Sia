Quick Start
===========


Installation
------------


.. code-block:: bash

   pip install openstef


.. note::

   OpenSTEF requires Python 3.8 or higher. Install with pip install openstef for core functionality. Additional dependencies may be needed for specific features like advanced forecasting models or database connectors.


Your First Forecast
-------------------


.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_models.workflows.custom_forecasting_workflow import CustomForecastingWorkflow
   from openstef_models.data_classes import TimeSeriesDataset

   # Create sample data
   dates = pd.date_range('2023-01-01', periods=1000, freq='15T')
   data = pd.DataFrame({
       'datetime': dates,
       'load': 100 + 50 * pd.np.sin(pd.np.arange(1000) * 0.01) + pd.np.random.normal(0, 10, 1000),
       'temperature': 15 + 10 * pd.np.sin(pd.np.arange(1000) * 0.005) + pd.np.random.normal(0, 2, 1000),
       'radiation': pd.np.maximum(0, 500 + 300 * pd.np.sin(pd.np.arange(1000) * 0.01) + pd.np.random.normal(0, 50, 1000))
   }).set_index('datetime')

   # Split data
   split_point = len(data) - 96  # Last 24 hours for validation
   train_data = TimeSeriesDataset(data.iloc[:split_point])
   val_data = TimeSeriesDataset(data.iloc[split_point:])

   # Create and train workflow
   workflow = CustomForecastingWorkflow()
   model_result = workflow.fit(train_data, val_data)

   # Generate forecast
   forecast_data = TimeSeriesDataset(data.iloc[-48:])  # Last 12 hours as input
   forecast = workflow.predict(forecast_data)

   print(f"Forecast shape: {forecast.data.shape}")
   print(forecast.data.head())


This code demonstrates a complete forecasting workflow using OpenSTEF's library components. It creates sample time series data, initializes a CustomForecastingWorkflow with an XGBoost model, trains the model on historical data, and generates predictions. The expected output is a ForecastDataset containing forecasted values with timestamps and confidence intervals for the specified prediction horizon.


Understanding the Results
-------------------------


The forecast output is a pandas DataFrame with datetime index and quantile columns. Key columns include quantile forecasts (e.g., 'forecast_0.1', 'forecast_0.5', 'forecast_0.9') representing prediction intervals, with 'forecast_0.5' being the median prediction. Additional columns may include standard deviation estimates and feature contributions depending on your model configuration.


.. code-block:: python

   import matplotlib.pyplot as plt

   # Inspect forecast structure
   print(f"Forecast period: {forecast_result.index[0]} to {forecast_result.index[-1]}")
   print(f"Available quantiles: {forecast_result.quantiles}")
   print(f"Forecast shape: {forecast_result.shape}")

   # Extract key series
   median_forecast = forecast_result.median_series()
   std_forecast = forecast_result.standard_deviation_series()

   # Basic visualization
   plt.figure(figsize=(12, 6))
   plt.plot(forecast_result.index, median_forecast, label='Median Forecast', linewidth=2)

   # Plot confidence intervals if available
   if len(forecast_result.quantiles) > 1:
       q10 = forecast_result.quantiles_data()['quantile_0.1']
       q90 = forecast_result.quantiles_data()['quantile_0.9']
       plt.fill_between(forecast_result.index, q10, q90, alpha=0.3, label='80% Confidence')

   plt.xlabel('Time')
   plt.ylabel('Load (MW)')
   plt.title('Energy Load Forecast')
   plt.legend()
   plt.grid(True, alpha=0.3)
   plt.show()

   # Display forecast statistics
   print(f"Mean forecast: {median_forecast.mean():.2f} MW")
   print(f"Peak forecast: {median_forecast.max():.2f} MW")


Next Steps
----------


- Explore the tutorials section for step-by-step guides on specific forecasting scenarios

- Review use cases to see OpenSTEF applied to real-world energy forecasting problems

- Check the API reference for detailed documentation of all available functions and classes

- Visit the configuration guide to learn about customizing model parameters and settings

- Read about data preparation best practices for optimal forecasting performance

- Learn advanced features like custom model implementations and pipeline extensions


OpenSTEF offers extensive capabilities beyond this quickstart guide. As a comprehensive forecasting library, it provides advanced model configurations, custom feature engineering, ensemble methods, and flexible pipeline architectures. Explore the API reference and advanced tutorials to unlock its full potential for your forecasting applications.


