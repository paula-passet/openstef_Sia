Quickstart
==========

Get started with OpenSTEF in minutes. This guide shows you how to train a forecasting model and create your first forecast using the minimal code needed.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

Basic Example
-------------

Here's a complete example that trains a model and generates forecasts:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
   from openstef_core.types import LeadTime

   # Create sample data
   dates = pd.date_range(
       start="2024-01-01", 
       end="2024-03-01", 
       freq="15min"
   )
   
   # Sample energy consumption data with some weather features
   data = pd.DataFrame({
       "datetime": dates,
       "load": 100 + 50 * pd.np.sin(pd.np.arange(len(dates)) * 2 * pd.np.pi / (24 * 4)) + 
               10 * pd.np.random.randn(len(dates)),
       "temperature": 15 + 10 * pd.np.sin(pd.np.arange(len(dates)) * 2 * pd.np.pi / (24 * 4)) +
                     5 * pd.np.random.randn(len(dates)),
       "wind_speed": 5 + 3 * pd.np.random.randn(len(dates))
   })
   
   # Create TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data.set_index("datetime"),
       sample_interval=timedelta(minutes=15)
   )

   # Create and configure model
   forecaster = ConstantMedianForecaster(
       horizons=[LeadTime.from_string("PT36H")]
   )
   
   model = ForecastingModel(
       forecaster=forecaster,
       target_column="load"
   )

   # Split data for training and forecasting
   split_date = datetime(2024, 2, 15)
   train_data = dataset.filter_time_range(end=split_date)
   forecast_data = dataset.filter_time_range(start=split_date)

   # Train the model
   model.fit(train_data)

   # Generate forecasts
   forecasts = model.predict(forecast_data)
   
   # View results
   print("Forecast median values:")
   print(forecasts.median_series.head())

What Just Happened?
-------------------

1. **Data Preparation**: Created a TimeSeriesDataset with energy load and weather features
2. **Model Setup**: Configured a simple median-based forecaster for 36-hour predictions  
3. **Training**: Fitted the model on historical data
4. **Forecasting**: Generated predictions for new time periods

The forecast results include quantile predictions (confidence intervals) that help you understand forecast uncertainty.

Next Steps
----------

This example uses the simplest possible forecaster. For production use, you'll want to:

- Use more sophisticated models like XGBoost or ensemble approaches
- Add comprehensive feature engineering and preprocessing
- Implement proper validation and backtesting
- Set up automated model retraining

See the tutorials for detailed examples of production-ready forecasting workflows, or browse the use cases guide to find the forecasting approach that matches your specific needs.