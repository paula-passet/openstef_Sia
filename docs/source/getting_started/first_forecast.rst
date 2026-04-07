Your First Forecast
===================

This tutorial walks you through creating your first forecast with OpenSTEF. You'll learn how to prepare data, configure a forecasting model, train it, make predictions, and evaluate the results. By the end, you'll understand the complete forecasting workflow and be ready to apply it to your own energy forecasting problems.

If you're looking for the absolute fastest path to a working example, see the :doc:`quickstart` guide. This page provides more detailed explanations of each step.

Overview
--------

A typical OpenSTEF forecasting workflow consists of five main steps:

1. **Data preparation**: Load and structure your time series data
2. **Model configuration**: Set up preprocessing, forecaster, and postprocessing
3. **Training**: Fit the model to historical data
4. **Prediction**: Generate forecasts for future time periods
5. **Evaluation**: Assess forecast quality using metrics

Let's work through each step with a concrete example.

Data Preparation
----------------

OpenSTEF expects data in the form of a ``TimeSeriesDataset``, which is a pandas DataFrame with a datetime index and columns for the target variable and features.

Creating a Dataset
^^^^^^^^^^^^^^^^^^

Here's how to create a basic dataset from a pandas DataFrame:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data (example with CSV)
   df = pd.read_csv("energy_data.csv", parse_dates=["datetime"])
   df = df.set_index("datetime")
   
   # Create a TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       target_column="load",  # The variable you want to forecast
   )

Your DataFrame should include:

- A datetime index with regular intervals (e.g., 15-minute or hourly)
- A target column containing the values to forecast (e.g., energy load)
- Feature columns that might help predict the target (e.g., temperature, day of week)

For this tutorial, we'll use synthetic data to demonstrate the workflow:

.. code-block:: python

   import numpy as np
   from datetime import datetime, timedelta
   
   # Generate 90 days of hourly data
   dates = pd.date_range(start="2024-01-01", periods=90*24, freq="h")
   
   # Synthetic load with daily pattern
   hours = dates.hour
   daily_pattern = 50 + 30 * np.sin((hours - 6) * np.pi / 12)
   noise = np.random.normal(0, 5, len(dates))
   load = daily_pattern + noise
   
   # Create DataFrame with features
   df = pd.DataFrame({
       "load": load,
       "temperature": 15 + 10 * np.sin(hours * np.pi / 12) + np.random.normal(0, 2, len(dates)),
       "hour": hours,
       "dayofweek": dates.dayofweek,
   }, index=dates)
   
   # Convert to TimeSeriesDataset
   dataset = TimeSeriesDataset(data=df, target_column="load")

Model Configuration
-------------------

OpenSTEF's ``ForecastingModel`` combines three components:

- **Preprocessing**: Feature engineering transforms (e.g., lag features, scaling)
- **Forecaster**: The machine learning algorithm that makes predictions
- **Postprocessing**: Optional transforms applied to predictions (e.g., clipping negative values)

Let's configure a simple but effective forecasting model:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models import ForecastingModel
   from openstef_models.models.forecasting import XGBQuantileForecaster
   from openstef_models.transforms import FeaturePipeline, AddHolidayFeatures, AddLagTransform, StandardScaler
   
   # Configure preprocessing pipeline
   preprocessing = FeaturePipeline(
       transforms=[
           AddHolidayFeatures(country="NL"),  # Add holiday indicators
           AddLagTransform(lag=timedelta(days=1)),  # Add 24-hour lag features
           AddLagTransform(lag=timedelta(days=7)),  # Add 7-day lag features
           StandardScaler(),  # Normalize features
       ]
   )
   
   # Create forecasting model
   model = ForecastingModel(
       forecaster=XGBQuantileForecaster(),
       preprocessing=preprocessing,
       target_column="load",
       cutoff_history=timedelta(days=7),  # Exclude first 7 days (due to lag features)
   )

**Why these choices?**

- **Holiday features**: Energy consumption often differs on holidays
- **Lag features**: Yesterday's and last week's values are strong predictors
- **Standard scaling**: Helps the XGBoost model converge faster
- **Cutoff history**: The 7-day lag creates NaN values for the first week, so we exclude it from training

The ``XGBQuantileForecaster`` produces probabilistic forecasts with quantiles (e.g., 10th, 50th, 90th percentiles), which is valuable for understanding forecast uncertainty.

Training the Model
------------------

Training fits both the preprocessing pipeline and the forecaster to your historical data:

.. code-block:: python

   # Train the model
   model.fit(data=dataset)

The ``fit()`` method performs several steps internally:

1. Fits the preprocessing pipeline to learn parameters (e.g., scaling factors)
2. Transforms the training data through the pipeline
3. Splits data into train/validation/test sets (if splitters are configured)
4. Trains the forecaster on the processed data

For this simple example, we're training on all available data. In practice, you'd typically hold out recent data for validation. See the :doc:`backtesting` guide for more sophisticated evaluation strategies.

Making Predictions
------------------

Once trained, you can generate forecasts for future time periods:

.. code-block:: python

   from datetime import datetime
   
   # Prepare forecast input (uses most recent data)
   forecast_start = datetime(2024, 3, 31, 0, 0)
   input_data = model.prepare_input(data=dataset, forecast_start=forecast_start)
   
   # Generate 48-hour forecast
   forecast = model.predict(data=input_data, forecast_start=forecast_start)
   
   print(forecast)

The ``prepare_input()`` method applies preprocessing and filters the data to include only what's needed for forecasting. The ``predict()`` method returns a ``ForecastDataset`` containing:

- **Quantile forecasts**: Multiple prediction quantiles (e.g., q10, q50, q90)
- **Datetime index**: The forecast horizon
- **Metadata**: Information about the forecast

You can access specific quantiles:

.. code-block:: python

   # Get median forecast (50th percentile)
   median_forecast = forecast.quantile_series(0.5)
   
   # Get prediction interval (10th to 90th percentile)
   lower_bound = forecast.quantile_series(0.1)
   upper_bound = forecast.quantile_series(0.9)
   
   # Plot the forecast
   import matplotlib.pyplot as plt
   
   plt.figure(figsize=(12, 6))
   plt.plot(median_forecast.index, median_forecast, label="Median forecast", color="blue")
   plt.fill_between(lower_bound.index, lower_bound, upper_bound, alpha=0.3, label="80% prediction interval")
   plt.xlabel("Time")
   plt.ylabel("Load")
   plt.legend()
   plt.title("48-Hour Energy Load Forecast")
   plt.show()

Evaluating Forecast Quality
----------------------------

To assess how well your model performs, compare predictions against actual values using evaluation metrics:

.. code-block:: python

   from openstef_beam.metrics import mae, rmse, mape
   
   # For evaluation, we need actual values in the forecast period
   # Let's create a test set from the last week of data
   test_data = dataset.iloc[-7*24:]  # Last 7 days
   
   # Generate forecasts for this period
   test_forecast = model.predict(
       data=model.prepare_input(data=dataset.iloc[:-7*24], forecast_start=test_data.index[0]),
       forecast_start=test_data.index[0]
   )
   
   # Get actual values and predictions
   actual = test_data["load"]
   predicted = test_forecast.quantile_series(0.5)  # Median forecast
   
   # Align indices (forecast might be shorter)
   common_index = actual.index.intersection(predicted.index)
   actual = actual.loc[common_index]
   predicted = predicted.loc[common_index]
   
   # Calculate metrics
   mae_score = mae(actual, predicted)
   rmse_score = rmse(actual, predicted)
   mape_score = mape(actual, predicted)
   
   print(f"Mean Absolute Error: {mae_score:.2f}")
   print(f"Root Mean Squared Error: {rmse_score:.2f}")
   print(f"Mean Absolute Percentage Error: {mape_score:.2f}%")

**Common metrics:**

- **MAE (Mean Absolute Error)**: Average absolute difference between predictions and actuals
- **RMSE (Root Mean Squared Error)**: Penalizes large errors more heavily than MAE
- **MAPE (Mean Absolute Percentage Error)**: Error as a percentage of actual values

Lower values indicate better forecast accuracy. The choice of metric depends on your use case—MAPE is useful when you care about relative errors, while MAE is more interpretable in the original units.

Understanding What Happens During Training
-------------------------------------------

When you call ``model.fit(data=dataset)``, OpenSTEF executes a carefully orchestrated sequence:

**Preprocessing fit**: Each transform in the pipeline learns from the data. For example, ``StandardScaler`` calculates mean and standard deviation for each feature, while ``AddLagTransform`` determines which columns to lag.

**Data transformation**: The fitted preprocessing pipeline transforms the raw data, creating new features and normalizing values.

**Data filtering**: The ``cutoff_history`` parameter removes incomplete rows. With a 7-day lag feature, the first 7 days contain NaN values and must be excluded.

**Forecaster training**: The underlying machine learning model (XGBoost in our example) trains on the processed data, learning patterns that map features to target values.

This separation between preprocessing and forecasting allows you to experiment with different feature engineering strategies independently from the choice of algorithm.

Why Cutoff History Matters
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``cutoff_history`` parameter is crucial when using lag-based features. Consider a 7-day lag transform:

- Day 1-7 of your data: Cannot create 7-day lag (no data available)
- Day 8 onwards: Can create valid lag features

If you don't set ``cutoff_history=timedelta(days=7)``, the model will train on rows with NaN lag values, degrading performance. OpenSTEF requires you to configure this manually because it cannot automatically infer the maximum lag from your preprocessing pipeline.

Next Steps
----------

You now understand the complete forecasting workflow in OpenSTEF. Here are some ways to build on this foundation:

- **Compare models**: Use :doc:`backtesting` to systematically evaluate different forecasters and preprocessing configurations
- **Advanced customization**: Learn how to create custom transforms and forecasters in :doc:`advanced_customization`
- **Production deployment**: Explore model persistence, versioning, and workflow orchestration for operational forecasting

The key to successful forecasting is iteration—experiment with different features, models, and evaluation strategies to find what works best for your specific use case.