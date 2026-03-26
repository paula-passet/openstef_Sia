Quickstart
==========

Get your first OpenSTEF forecast running in minutes. This guide shows the minimal steps to load data, train a model, and generate forecasts using the OpenSTEF Python library.

Basic Forecast
--------------

Here's how to create your first forecast with just a few lines of code:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset, ForecastInputDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgb_quantile_openstef import XGBQuantileOpenstef
   from openstef_core.types import LeadTime

   # Create sample data with datetime index
   dates = pd.date_range('2024-01-01', periods=1000, freq='15min')
   data = pd.DataFrame({
       'load': [100 + 50 * (i % 96) / 96 for i in range(1000)],  # Simple daily pattern
       'temperature': [15 + 10 * (i % 96) / 96 for i in range(1000)],
       'hour': dates.hour,
       'day_of_week': dates.dayofweek
   }, index=dates)

   # Create dataset
   dataset = ForecastInputDataset(
       data=data,
       target_column='load',
       sample_interval=timedelta(minutes=15)
   )

   # Create and configure model
   forecaster = XGBQuantileOpenstef(
       horizons=[LeadTime.from_string("PT36H")]  # 36-hour forecast
   )
   
   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=7)
   )

   # Train the model
   model.fit(dataset)

   # Generate forecast
   forecast_start = datetime(2024, 2, 15)
   forecasts = model.predict(dataset, forecast_start=forecast_start)

   # View results
   print(f"Generated forecast with {len(forecasts.data)} time steps")
   print(f"Forecast columns: {list(forecasts.data.columns)}")

What Happens Next
-----------------

This quickstart gets you a working forecast, but OpenSTEF offers much more:

- **Advanced tutorials**: Learn proper data preparation, model evaluation, and backtesting in :doc:`tutorials`
- **Production deployment**: Set up automated forecasting with :doc:`../guides/how_to_guides`  
- **Different use cases**: Explore congestion forecasts, grid losses, and more in :doc:`../guides/use_cases`
- **Understanding results**: Learn to interpret forecasts and quantiles in :doc:`../reference/concepts`

.. note::
   The sample data above creates a simple pattern for demonstration. Real forecasting requires historical energy data with weather features and proper validation. See the tutorials for production-ready examples.