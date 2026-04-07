Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For explanations of what's happening and why, see :doc:`first_forecast`.

Prerequisites
-------------

OpenSTEF installed::

   pip install openstef

That's it. The example below uses synthetic data, so no external data sources required.

Minimal Working Example
-----------------------

This complete example trains a forecasting model and generates predictions:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.models import ForecastingModel
   from openstef_core.models.forecasters import ConstantMedianForecaster
   from openstef_core.pipelines import FeaturePipeline
   from openstef_core.transforms.features import AddHolidayFeatures, AddLagFeatures
   from openstef_core.workflows import CustomForecastingWorkflow
   from openstef_core.storage import LocalModelStorage
   from pathlib import Path

   # Create synthetic time series data
   start = datetime(2024, 1, 1)
   dates = pd.date_range(start, periods=1000, freq="15min")
   load = 100 + 50 * np.sin(np.arange(1000) * 2 * np.pi / 96) + np.random.randn(1000) * 10
   
   data = VersionedTimeSeriesDataset(
       data=pd.DataFrame({"load": load}, index=dates),
       sample_interval=timedelta(minutes=15),
       forecast_start=start + timedelta(days=7),
   )

   # Configure preprocessing pipeline
   feature_pipeline = FeaturePipeline(
       transforms=[
           AddHolidayFeatures(country="NL"),
           AddLagFeatures(lags=[timedelta(days=1), timedelta(days=7)]),
       ]
   )

   # Create forecasting model
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(),
       feature_pipeline=feature_pipeline,
   )

   # Set up model storage
   storage = LocalModelStorage(base_path=Path("./models"))

   # Create workflow
   workflow = CustomForecastingWorkflow(
       model=model,
       storage=storage,
   )

   # Train model
   workflow.train(data=data)

   # Generate forecast
   forecast = workflow.predict(data=data)
   
   print(forecast.data.head())

Expected Output
---------------

The forecast is returned as a pandas DataFrame with timestamps and predicted values::

                         quantile_0.50
   2024-01-08 00:00:00          145.3
   2024-01-08 00:15:00          147.8
   2024-01-08 00:30:00          150.2
   2024-01-08 00:45:00          152.1
   2024-01-08 01:00:00          153.5

The ``quantile_0.50`` column represents the median forecast (50th percentile).

What Just Happened
------------------

1. **Created synthetic data**: 1000 time steps of 15-minute load data with daily patterns
2. **Configured features**: Added holiday effects and lagged values (1 day, 7 days ago)
3. **Trained a model**: ConstantMedianForecaster learns from historical patterns
4. **Generated predictions**: Forecast starts 7 days after data begins
5. **Saved the model**: Stored to ``./models/`` directory for reuse

Using Your Own Data
-------------------

Replace the synthetic data section with your own CSV or DataFrame:

.. code-block:: python

   # Load from CSV
   df = pd.read_csv("your_data.csv", index_col=0, parse_dates=True)
   
   data = VersionedTimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15),
       forecast_start=datetime(2024, 1, 8),
   )

Your data must have:

- A datetime index
- A ``load`` column (or specify ``target_column`` parameter)
- Regular time intervals (e.g., 15min, 1h)

Next Steps
----------

This quickstart uses default settings. To understand what's happening and customize your forecasts:

- :doc:`first_forecast` - Detailed walkthrough with explanations
- :doc:`advanced_customization` - Change models, features, and hyperparameters
- :doc:`backtesting` - Evaluate model performance on historical data

For installation issues, see :doc:`installation`.

Common Issues
-------------

**Import errors**: Ensure OpenSTEF is installed with ``pip install openstef``

**Data format errors**: Check that your datetime index is properly parsed with ``pd.to_datetime()``

**Storage errors**: The script creates a ``./models/`` directory automatically, but ensure write permissions exist

**Memory issues**: The example uses 1000 data points. For larger datasets, consider sampling or using chunked processing (see :doc:`advanced_customization`)