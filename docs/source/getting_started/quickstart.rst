Quickstart
==========

This quickstart gets you to your first forecast in minutes. You'll train a model on time series data and generate predictions with minimal setup.

Installation
------------

Install OpenSTEF using pip:

.. code-block:: bash

   pip install openstef

For production use with XGBoost models, install with the ``xgboost`` extra:

.. code-block:: bash

   pip install openstef[xgboost]


Your First Forecast
-------------------

Here's a complete example that creates synthetic data, trains a model, and generates a forecast:

.. code-block:: python

   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting.constant_median_forecaster import ConstantMedianForecaster
   from openstef_models.preprocessing.feature_pipeline import FeaturePipeline
   from openstef_models.preprocessing.transforms import AddHolidayFeatures, AddLagTransforms

   # Create sample data (replace with your own time series)
   dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="15min")
   data = pd.DataFrame({
       "load": np.random.randn(len(dates)).cumsum() + 100,  # Target variable
       "temperature": np.random.randn(len(dates)) * 5 + 15,  # Weather predictor
   }, index=dates)
   
   # Wrap in OpenSTEF dataset
   dataset = VersionedTimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )
   
   # Configure preprocessing pipeline
   preprocessing = FeaturePipeline([
       AddHolidayFeatures(country="NL"),
       AddLagTransforms(lags=[96, 672]),  # 1 day and 1 week lags (15-min intervals)
   ])
   
   # Create forecasting model
   model = ForecastingModel(
       forecaster=ConstantMedianForecaster(),
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=14)  # Remove rows with NaN from lag features
   )
   
   # Train the model
   model.fit(dataset)
   
   # Generate forecast
   forecast = model.predict(dataset)
   
   print(forecast.data.head())


Understanding the Code
^^^^^^^^^^^^^^^^^^^^^^

**Data format**: OpenSTEF expects a pandas DataFrame with a datetime index and a target column (e.g., ``load``). Additional columns become predictor features.

**VersionedTimeSeriesDataset**: Wraps your data with metadata about sample interval and target column. This ensures consistency throughout the pipeline.

**Preprocessing**: The ``FeaturePipeline`` adds derived features before training. Holiday features capture calendar effects, while lag transforms use historical values as predictors.

**Cutoff history**: When using lag transforms, the first N rows will have NaN values. Set ``cutoff_history`` to exclude these incomplete rows from training.

**Forecast output**: The ``predict()`` method returns a ``TimeSeriesDataset`` containing predictions with horizons and availability times.


Next Steps
----------

This quickstart uses a simple median-based forecaster for demonstration. For production forecasting:

- **Use XGBoost models**: See :doc:`tutorials` for examples with ``XGBQuantileForecaster``
- **Add more features**: Include weather forecasts, calendar features, and domain-specific predictors
- **Evaluate performance**: Learn about backtesting and metrics in :doc:`tutorials`
- **Choose the right use case**: Review :doc:`../guides/use_cases` to match your forecasting needs
- **Deploy your model**: Check :doc:`../guides/how_to_guides` for orchestration and data integration

For a comprehensive walkthrough including evaluation and customization, continue to :doc:`tutorials`.