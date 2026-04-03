Your First Forecast
====================

This tutorial walks you through creating your first forecast with OpenSTEF. You'll learn how to prepare data, configure a forecasting model, train it, generate predictions, and evaluate the results. By the end, you'll understand the complete forecasting workflow and what each step accomplishes.

We'll use a complete example that demonstrates the typical pattern you'll follow when using OpenSTEF in your own projects.

Overview of the Workflow
-------------------------

A typical OpenSTEF forecasting workflow consists of five main steps:

1. **Data preparation**: Load and structure your time series data
2. **Model configuration**: Set up the forecasting pipeline with preprocessing and postprocessing
3. **Training**: Fit the model to historical data
4. **Prediction**: Generate forecasts for future time periods
5. **Evaluation**: Assess forecast quality using metrics

Each step serves a specific purpose in the forecasting pipeline. Let's work through them in detail.

Step 1: Preparing Your Data
----------------------------

OpenSTEF expects time series data in a specific format. The library uses ``TimeSeriesDataset`` objects that combine a pandas DataFrame with metadata about the forecast target.

Here's how to prepare your data:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   
   # Create a time index (15-minute intervals for 30 days)
   start_date = datetime(2024, 1, 1)
   end_date = start_date + timedelta(days=30)
   time_index = pd.date_range(start=start_date, end=end_date, freq="15min")
   
   # Create synthetic load data with daily patterns
   import numpy as np
   hours = (time_index.hour + time_index.minute / 60).values
   load = 100 + 50 * np.sin(2 * np.pi * (hours - 6) / 24) + np.random.normal(0, 5, len(time_index))
   
   # Add temperature as a feature (inversely correlated with load)
   temperature = 15 + 10 * np.sin(2 * np.pi * (hours - 14) / 24) + np.random.normal(0, 2, len(time_index))
   
   # Create DataFrame with target and features
   df = pd.DataFrame({
       "load": load,
       "temperature": temperature,
       "hour": time_index.hour,
       "dayofweek": time_index.dayofweek,
   }, index=time_index)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       target_column="load",
       forecast_resolution=timedelta(minutes=15)
   )

The ``TimeSeriesDataset`` requires:

- A pandas DataFrame with a datetime index
- A ``target_column`` specifying what you're forecasting (in this case, "load")
- A ``forecast_resolution`` indicating the time step between predictions

Your features can include weather data, calendar information, or any other relevant predictors. OpenSTEF will automatically create lag features and other temporal features during preprocessing.

Step 2: Configuring the Model
------------------------------

OpenSTEF uses a ``ForecastingModel`` that wraps a forecaster with preprocessing and postprocessing pipelines. This modular design lets you customize each component independently.

.. code-block:: python

   from openstef_models.models import ForecastingModel
   from openstef_models.forecasters import XGBForecaster
   from openstef_core.feature_engineering import FeaturePipeline
   from openstef_core.feature_engineering.features import (
       HolidayFeature,
       LagTransform,
       StandardScaler,
   )
   
   # Configure feature engineering
   feature_pipeline = FeaturePipeline(
       features=[
           HolidayFeature(country="NL"),  # Add Dutch holiday indicators
           LagTransform(lags=[96, 672]),  # Add 1-day and 1-week lags (96 = 24h at 15min resolution)
           StandardScaler(),  # Normalize features
       ]
   )
   
   # Create the forecaster (XGBoost in this case)
   forecaster = XGBForecaster(
       horizons=[1, 4, 8, 16, 32, 96],  # Forecast horizons: 15min to 24h ahead
       quantiles=[0.1, 0.5, 0.9],  # Probabilistic forecasts
   )
   
   # Combine into a complete forecasting model
   model = ForecastingModel(
       forecaster=forecaster,
       feature_pipeline=feature_pipeline,
   )

**What's happening here:**

- ``FeaturePipeline`` applies transformations to your raw data before training. Holiday features help capture special days, lag transforms add historical values as predictors, and scaling normalizes feature ranges.
- ``XGBForecaster`` is the machine learning model that learns patterns from your data. The ``horizons`` parameter specifies which future time steps to predict.
- ``quantiles`` enable probabilistic forecasting, giving you prediction intervals in addition to point forecasts.

You can swap out any of these components. For example, replace ``XGBForecaster`` with ``LightGBMForecaster`` or add different feature transforms.

Step 3: Training the Model
---------------------------

Training fits the model to your historical data. The model learns relationships between features and the target variable.

.. code-block:: python

   # Split data into training and test sets
   split_date = start_date + timedelta(days=25)
   train_data = dataset.filter_by_range(end=split_date)
   test_data = dataset.filter_by_range(start=split_date)
   
   # Train the model
   model.fit(data=train_data)
   
   print(f"Model trained on {len(train_data)} samples")

The ``fit`` method:

1. Applies the feature pipeline to create engineered features
2. Prepares the data in the format expected by the forecaster
3. Trains the underlying machine learning model
4. Stores learned parameters for later prediction

Training can take from seconds to minutes depending on data size and model complexity. XGBoost and LightGBM are typically fast even on large datasets.

You can optionally provide validation data to monitor training progress:

.. code-block:: python

   # Use validation data for early stopping
   val_data = train_data.filter_by_range(start=split_date - timedelta(days=5))
   train_data_only = train_data.filter_by_range(end=split_date - timedelta(days=5))
   
   model.fit(data=train_data_only, data_val=val_data)

Step 4: Generating Predictions
-------------------------------

Once trained, use the model to forecast future values. OpenSTEF generates predictions for all configured horizons simultaneously.

.. code-block:: python

   from datetime import datetime
   
   # Generate forecasts starting from the test period
   forecast_start = split_date
   predictions = model.predict(
       data=test_data,
       forecast_start=forecast_start
   )
   
   # Predictions contain forecasts for all horizons
   print(f"Generated {len(predictions)} forecast points")
   print(f"Forecast columns: {predictions.data.columns.tolist()}")

The ``predict`` method returns a ``ForecastDataset`` containing:

- Point forecasts (median predictions)
- Quantile forecasts (prediction intervals)
- Metadata about the forecast timing

The model automatically applies the same feature engineering used during training, ensuring consistency between training and prediction.

**Accessing forecast values:**

.. code-block:: python

   # Get the forecast DataFrame
   forecast_df = predictions.data
   
   # Point forecast is typically the median (quantile 0.5)
   point_forecast = forecast_df["forecast"]
   
   # Prediction intervals
   lower_bound = forecast_df["quantile_0.1"]
   upper_bound = forecast_df["quantile_0.9"]
   
   # Compare with actual values
   actual = test_data.data[dataset.target_column]

Step 5: Evaluating Forecast Quality
------------------------------------

Evaluation quantifies how well your forecasts match actual values. OpenSTEF provides an evaluation pipeline that calculates multiple metrics.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import MAE, RMSE, MAPE
   
   # Configure evaluation
   eval_config = EvaluationConfig(
       available_ats=[],  # No specific availability filtering
       lead_times=[1, 4, 8, 16, 32, 96],  # Evaluate at each horizon
   )
   
   # Create evaluation pipeline
   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[0.1, 0.5, 0.9],
       window_metric_providers=[],
       global_metric_providers=[MAE(), RMSE(), MAPE()],
   )
   
   # Run evaluation
   evaluation_report = eval_pipeline.run_for_subset(
       filtering=96,  # Evaluate 24-hour ahead forecasts
       predictions=predictions,
   )
   
   # Extract metrics
   global_metrics = evaluation_report.get_global_metric()
   if global_metrics:
       print(f"MAE: {global_metrics.metrics.get('mae'):.2f}")
       print(f"RMSE: {global_metrics.metrics.get('rmse'):.2f}")
       print(f"MAPE: {global_metrics.metrics.get('mape'):.2f}%")

**Understanding the metrics:**

- **MAE (Mean Absolute Error)**: Average magnitude of forecast errors in the same units as your target
- **RMSE (Root Mean Square Error)**: Similar to MAE but penalizes larger errors more heavily
- **MAPE (Mean Absolute Percentage Error)**: Error as a percentage of actual values

Lower values indicate better forecast accuracy. Choose metrics appropriate for your use case—MAPE is useful for comparing across different scales, while MAE is more interpretable in absolute terms.

Putting It All Together
------------------------

Here's a complete minimal example combining all steps:

.. code-block:: python

   from datetime import datetime, timedelta
   import pandas as pd
   import numpy as np
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.forecasters import XGBForecaster
   from openstef_core.feature_engineering import FeaturePipeline
   from openstef_core.feature_engineering.features import LagTransform, StandardScaler
   
   # 1. Prepare data
   time_index = pd.date_range(start="2024-01-01", end="2024-01-31", freq="15min")
   hours = (time_index.hour + time_index.minute / 60).values
   df = pd.DataFrame({
       "load": 100 + 50 * np.sin(2 * np.pi * (hours - 6) / 24) + np.random.normal(0, 5, len(time_index)),
       "temperature": 15 + 10 * np.sin(2 * np.pi * (hours - 14) / 24) + np.random.normal(0, 2, len(time_index)),
   }, index=time_index)
   
   dataset = TimeSeriesDataset(data=df, target_column="load", forecast_resolution=timedelta(minutes=15))
   
   # 2. Configure model
   model = ForecastingModel(
       forecaster=XGBForecaster(horizons=[1, 4, 8, 16], quantiles=[0.1, 0.5, 0.9]),
       feature_pipeline=FeaturePipeline(features=[LagTransform(lags=[96]), StandardScaler()]),
   )
   
   # 3. Train
   split_date = datetime(2024, 1, 26)
   train_data = dataset.filter_by_range(end=split_date)
   test_data = dataset.filter_by_range(start=split_date)
   model.fit(data=train_data)
   
   # 4. Predict
   predictions = model.predict(data=test_data, forecast_start=split_date)
   
   # 5. Evaluate
   score = model.score(data=test_data)
   print(f"Forecast metrics: {score.metrics}")

Next Steps
----------

Now that you understand the basic workflow, you can:

- Explore different forecasters and feature engineering options in :doc:`advanced_customization`
- Learn how to compare multiple models systematically using :doc:`backtesting`
- Experiment with the minimal working example in :doc:`quickstart` for rapid prototyping

The key to effective forecasting is iteration: try different features, tune model parameters, and evaluate results to find what works best for your specific use case.