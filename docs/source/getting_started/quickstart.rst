Quick Start
===========

This guide shows you how to create your first forecast with OpenSTEF in just a few lines of code. You'll train a model and generate predictions using synthetic data.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

Your First Forecast
-------------------

Here's a complete example that creates synthetic data, trains a model, and generates a forecast:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_models.models.forecasting_model import ForecastingModel

   # Create synthetic energy load data (9 months of hourly data)
   data = create_synthetic_forecasting_dataset(
       start=datetime(2024, 1, 1),
       length=timedelta(days=270),
       sample_interval=timedelta(hours=1)
   )

   # Split data for training and testing
   train_end = datetime(2024, 8, 1)
   train_data = data.filter_by_range(end=train_end)
   test_data = data.filter_by_range(start=train_end)

   # Create and train the model
   model = ForecastingModel()
   fit_result = model.fit(train_data)

   # Generate forecasts
   forecasts = model.predict(test_data)

   print(f"Training completed with {len(train_data)} samples")
   print(f"Generated forecasts for {len(forecasts)} time points")

This example uses OpenSTEF's default configuration, which includes:

- XGBoost regressor with quantile prediction
- Automatic feature engineering (weather, time-based features)
- 47-hour forecast horizon
- Standard preprocessing and validation

Understanding the Results
-------------------------

The forecast dataset contains predictions at multiple quantile levels (10%, 50%, 90%) for up to 47 hours ahead. Each prediction includes confidence intervals to help you assess forecast uncertainty.

.. code-block:: python

   # Examine forecast structure
   print(f"Forecast quantiles: {model.quantiles}")
   print(f"Maximum horizon: {model.max_horizon}")
   
   # Access predictions for a specific time
   forecast_df = forecasts.to_pandas()
   print(forecast_df.head())

Next Steps
----------

This quickstart uses synthetic data and default settings. For real-world usage:

- See :doc:`tutorials` for comprehensive examples with real data
- Check :doc:`../guides/use_cases` to identify your specific forecasting scenario  
- Review :doc:`../guides/how_to_guides` for deployment and integration patterns

The synthetic dataset includes realistic weather dependencies and seasonal patterns, making it suitable for initial experimentation and testing your integration.