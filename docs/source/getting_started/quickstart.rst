Quick Start
===========

Get your first energy forecast running in under 5 minutes. This page shows the minimal steps to train a model and create forecasts using OpenSTEF.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: python

   pip install openstef

Your First Forecast
-------------------

Here's a complete example that loads sample data, trains a model, and creates a forecast:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import ForecastInputDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgb_quantile_forecaster import XGBQuantileForecaster
   from openstef_models.transforms import StandardTransforms

   # Create sample energy load data (15-minute intervals)
   dates = pd.date_range('2023-01-01', '2023-12-31', freq='15min')
   load_data = pd.DataFrame({
       'datetime': dates,
       'load': 100 + 50 * pd.np.sin(2 * pd.np.pi * dates.dayofyear / 365) + 
               20 * pd.np.random.randn(len(dates)),
       'horizon': 0.25  # 15-minute horizon
   })
   load_data.set_index('datetime', inplace=True)

   # Create dataset
   dataset = ForecastInputDataset(load_data)

   # Configure model with standard preprocessing
   model = ForecastingModel(
       forecaster=XGBQuantileForecaster(),
       preprocessing=StandardTransforms()
   )

   # Split data for training and testing
   split_date = datetime(2023, 11, 1)
   train_data = dataset.restrict_to_datetime_range(end=split_date)
   test_data = dataset.restrict_to_datetime_range(start=split_date)

   # Train the model
   model.fit(train_data)

   # Create forecast
   forecast = model.predict(test_data)

   print(f"Forecast created with {len(forecast.data)} predictions")
   print(f"Forecast range: {forecast.data.index.min()} to {forecast.data.index.max()}")

What Just Happened?
^^^^^^^^^^^^^^^^^^^

1. **Data Creation**: We generated synthetic energy load data with seasonal patterns and noise
2. **Dataset Wrapping**: The data was wrapped in a ``ForecastInputDataset`` for validation and processing
3. **Model Configuration**: We used an XGBoost quantile forecaster with standard feature engineering
4. **Training**: The model learned patterns from historical data up to November 2023
5. **Forecasting**: We generated probabilistic forecasts for the remaining months

Next Steps
----------

This minimal example gets you started, but OpenSTEF offers much more:

- **Real Data**: Replace the synthetic data with your actual energy measurements
- **Weather Features**: Add temperature, wind, and solar data to improve accuracy
- **Multiple Horizons**: Forecast multiple time steps ahead simultaneously
- **Backtesting**: Evaluate model performance using historical simulations
- **Advanced Models**: Try ensemble methods or custom feature engineering

For comprehensive tutorials and real-world examples, see:

- **Tutorials** - Step-by-step guides with realistic datasets
- `OpenSTEF Offline Examples <https://github.com/OpenSTEF/openstef-offline-example>`_ - Jupyter notebooks with sample data
- **Use Cases Guide** - Common energy forecasting applications

.. note::
   The example above uses synthetic data for demonstration. For production use, you'll need historical energy measurements and weather data. See the tutorials for examples with real datasets.