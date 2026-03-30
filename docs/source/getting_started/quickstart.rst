Quickstart
==========

This guide gets you from zero to your first forecast in minutes. OpenSTEF is a Python library for short-term energy forecasting—this page shows the absolute minimum needed to train a model and generate predictions.

Installation
------------

Install OpenSTEF with pip:

.. code-block:: bash

   pip install openstef

This installs the core forecasting functionality. For the complete toolkit including evaluation tools, use ``pip install "openstef[all]"``.

Your First Forecast
-------------------

Here's a complete example that trains a model and creates a forecast:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgb_quantile_forecaster import XGBQuantileForecaster
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime, Quantile

   # Load your data (must have DatetimeIndex and 'load' column)
   data = pd.read_csv('your_data.csv', index_col=0, parse_dates=True)
   
   # Wrap in OpenSTEF dataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )
   
   # Create forecaster for 48-hour ahead predictions
   forecaster = XGBQuantileForecaster(
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )
   
   # Build and train model
   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=14)
   )
   
   # Split data: use all but last 48 hours for training
   train_data = dataset.iloc[:-192]  # 192 = 48 hours at 15-min resolution
   test_data = dataset.iloc[-192:]
   
   # Train the model
   fit_result = model.fit(train_data)
   print(f"Training complete. R²: {fit_result.metrics.r2:.3f}")
   
   # Generate forecast
   forecast = model.predict(test_data)
   
   # Access predictions
   print(forecast.data[['load', 'quantile_P10', 'quantile_P50', 'quantile_P90']].head())

Data Requirements
-----------------

Your input data must include:

- **DatetimeIndex**: Regular timestamps (e.g., 15-minute intervals)
- **load**: Target variable to forecast (can be power, energy, etc.)
- **Features**: Weather data, calendar features, or other predictors

Example data structure:

.. code-block:: python

   #                      load  temperature  radiation  windspeed
   # 2024-01-01 00:00:00  120.5         5.2       0.0        3.1
   # 2024-01-01 00:15:00  118.3         5.1       0.0        3.2
   # 2024-01-01 00:30:00  115.7         5.0       0.0        3.4

OpenSTEF automatically generates datetime features (hour, day of week, etc.) during training. Weather features like temperature and radiation significantly improve forecast accuracy.

Understanding the Output
------------------------

The forecast contains multiple quantiles representing prediction uncertainty:

- **quantile_P10**: 10th percentile (lower bound)
- **quantile_P50**: Median prediction (most likely value)
- **quantile_P90**: 90th percentile (upper bound)

The median (P50) is typically used as the point forecast, while the range between P10 and P90 indicates forecast confidence.

Next Steps
----------

This quickstart uses default settings suitable for many scenarios. To customize for your specific use case:

- **Comprehensive tutorial**: See :doc:`tutorials` for detailed walkthroughs including data preparation, model evaluation, and backtesting
- **Use case selection**: Review :doc:`../guides/use_cases` to identify which forecasting approach matches your needs
- **Production deployment**: Check :doc:`../guides/how_to_guides` for orchestration and data integration patterns
- **Understanding results**: Read :doc:`../reference/concepts` for interpreting forecasts and quantiles

.. note::

   OpenSTEF is a library, not a ready-to-run application. You'll need to integrate it into your own data pipelines and orchestration systems. The tutorials show complete working examples you can adapt.