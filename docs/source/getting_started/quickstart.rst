Quickstart
==========

Get up and running with OpenSTEF in minutes. This guide shows you how to train your first forecasting model and generate predictions with minimal setup.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

For the complete toolkit including evaluation tools:

.. code-block:: bash

   pip install "openstef[all]"

Your First Forecast
-------------------

Here's a complete example that loads data, trains a model, and creates a forecast:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
   from openstef_core.types import LeadTime

   # Load your data (CSV with datetime index and target column)
   data = pd.read_csv('energy_data.csv', parse_dates=['datetime'], index_col='datetime')
   
   # Create OpenSTEF dataset
   dataset = TimeSeriesDataset(data)
   
   # Configure the forecaster
   forecaster = XGBoostForecaster(
       horizons=[LeadTime.from_string("PT24H")]  # 24-hour forecast
   )
   
   # Create and train the model
   model = ForecastingModel(
       forecaster=forecaster,
       cutoff_history=timedelta(days=30)  # Use 30 days of recent data
   )
   
   # Train the model
   fit_result = model.fit(dataset)
   
   # Generate forecasts
   forecasts = model.predict(dataset, forecast_start=datetime.now())
   
   # Access forecast results
   forecast_df = forecasts.data
   print(f"Generated {len(forecast_df)} forecast points")
   print(f"Forecast columns: {list(forecast_df.columns)}")

Data Requirements
-----------------

Your CSV file should contain:

- **datetime**: Timestamp column (15-minute intervals recommended)
- **target**: Energy values to forecast (e.g., 'load', 'generation')
- **features**: Weather data, calendar features, or other predictors (optional)

Example data structure:

.. code-block:: csv

   datetime,load,temperature,wind_speed
   2024-01-01 00:00:00,1250.5,2.1,3.2
   2024-01-01 00:15:00,1180.2,2.0,3.1
   2024-01-01 00:30:00,1165.8,1.9,3.0

Understanding Results
---------------------

The forecast dataset contains quantile predictions:

.. code-block:: python

   # View forecast structure
   print(forecasts.data.head())
   
   # Access specific quantiles
   median_forecast = forecasts.data['quantile_0.5']  # Median prediction
   upper_bound = forecasts.data['quantile_0.9']      # Upper confidence
   lower_bound = forecasts.data['quantile_0.1']      # Lower confidence

Different Forecasters
---------------------

OpenSTEF provides several forecasting algorithms:

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearForecaster
   from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
   
   # Gradient boosted linear model (fast, interpretable)
   linear_forecaster = GBLinearForecaster(
       horizons=[LeadTime.from_string("PT24H")]
   )
   
   # Simple baseline (for comparison)
   baseline_forecaster = ConstantMedianForecaster(
       horizons=[LeadTime.from_string("PT24H")]
   )

Next Steps
----------

Now that you have a working forecast:

- **Learn more**: Check the :doc:`../getting_started/tutorials` for detailed examples
- **Evaluate models**: Use :doc:`../guides/how_to_guides` for backtesting and validation
- **Explore use cases**: See :doc:`../guides/use_cases` for specific applications
- **Production deployment**: Review :doc:`../guides/how_to_guides` for orchestration options

.. note::
   This quickstart uses default settings optimized for getting started quickly. For production use, consider customizing preprocessing, feature engineering, and model hyperparameters based on your specific data characteristics.