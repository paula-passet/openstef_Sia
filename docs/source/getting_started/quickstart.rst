Quickstart
==========

This page gets you from zero to your first forecast in under 5 minutes. Copy, paste, run. For explanations of what's happening and why, see :doc:`first_forecast`.

Prerequisites
-------------

OpenSTEF installed:

.. code-block:: bash

   pip install openstef

That's it. Let's make a forecast.

Minimal Working Example
------------------------

This complete example creates synthetic data, trains a model, and generates a forecast:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.models.constant_median import ConstantMedianForecaster
   from openstef_models.pipelines.forecasting_model import ForecastingModel
   from openstef_models.pipelines.feature_pipeline import FeaturePipeline
   from openstef_models.transforms.holiday import HolidayTransform
   from openstef_models.transforms.general import Scaler
   from openstef_models.transforms.lag import LagTransform
   from openstef_models.storage.local import LocalModelStorage
   from openstef_workflows.workflows.forecasting import CustomForecastingWorkflow

   # Create synthetic training data
   dates = pd.date_range(
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
       freq="15min"
   )
   load = 100 + 20 * np.sin(np.arange(len(dates)) * 2 * np.pi / 96)
   load += np.random.normal(0, 5, len(dates))
   
   data = pd.DataFrame({
       "datetime": dates,
       "load": load,
       "temperature": 15 + 5 * np.sin(np.arange(len(dates)) * 2 * np.pi / 96),
   })
   data.set_index("datetime", inplace=True)
   
   train_data = VersionedTimeSeriesDataset(data, version=1)

   # Configure the forecasting pipeline
   feature_pipeline = FeaturePipeline(
       transforms=[
           HolidayTransform(country="NL"),
           LagTransform(lags=[1, 2, 24]),
           Scaler(),
       ]
   )
   
   model = ForecastingModel(
       model=ConstantMedianForecaster(),
       feature_pipeline=feature_pipeline,
   )

   # Set up model storage
   storage = LocalModelStorage(base_path="./models")

   # Create workflow
   workflow = CustomForecastingWorkflow(
       model=model,
       storage=storage,
   )

   # Train the model
   workflow.train(train_data, target_column="load")

   # Generate forecast
   forecast_start = datetime(2024, 4, 1)
   forecast_horizon = timedelta(hours=24)
   
   forecast = workflow.predict(
       train_data,
       forecast_start=forecast_start,
       horizon=forecast_horizon,
   )
   
   print(forecast.head())

Run this code and you'll see a DataFrame with forecast timestamps and predicted load values.

What Just Happened
------------------

You created:

- **Synthetic data**: 3 months of 15-minute load and temperature data
- **Feature pipeline**: Holiday features, lag transforms, and scaling
- **Model**: A simple constant median forecaster
- **Storage**: Local file-based model persistence
- **Workflow**: High-level orchestration for training and prediction

The workflow trained the model on historical data and generated a 24-hour forecast.

Next Steps
----------

**Want to understand what you just ran?** See :doc:`first_forecast` for a detailed walkthrough with explanations.

**Ready to test your model?** Learn backtesting in :doc:`backtesting`.

**Need to customize?** Check out :doc:`advanced_customization` for power user features.

**Using your own data?** Replace the synthetic data creation with your own DataFrame. Requirements:

- DatetimeIndex
- Target column (e.g., "load")
- Optional: weather features, calendar features

.. code-block:: python

   # Load your data
   data = pd.read_csv("your_data.csv", parse_dates=["datetime"], index_col="datetime")
   train_data = VersionedTimeSeriesDataset(data, version=1)
   
   # Use the same workflow as above
   workflow.train(train_data, target_column="load")

That's it. You're forecasting.