Your First Forecast with OpenSTEF
==================================

This tutorial walks you through creating your first energy forecast with OpenSTEF, explaining each step in detail. By the end, you'll understand how to prepare data, configure a model, train it, generate forecasts, and evaluate performance.

If you're looking for the absolute fastest path to a working forecast, see the :doc:`quickstart` guide. For comparing multiple models systematically, check out the :doc:`backtesting` tutorial.

Overview
--------

A typical OpenSTEF forecasting workflow consists of five key steps:

1. **Data preparation** - Load and structure your time series data
2. **Model configuration** - Choose a forecaster and preprocessing pipeline
3. **Training** - Fit the model to historical data
4. **Forecasting** - Generate predictions for future time periods
5. **Evaluation** - Assess model performance with metrics

Let's work through each step with a practical example.

Step 1: Preparing Your Data
----------------------------

OpenSTEF expects data in a ``TimeSeriesDataset`` object, which wraps a pandas DataFrame with time series metadata. Your data should have:

- A DatetimeIndex representing timestamps
- A target column (typically named ``load``) containing the values to forecast
- Optional feature columns (weather, calendar features, etc.)

Here's how to create a dataset from a pandas DataFrame:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef.data import TimeSeriesDataset
   
   # Load your data (from CSV, database, etc.)
   df = pd.read_csv('energy_data.csv', parse_dates=['timestamp'])
   df = df.set_index('timestamp')
   
   # Create a TimeSeriesDataset
   # sample_interval should match your data frequency
   dataset = TimeSeriesDataset(
       data=df,
       sample_interval=timedelta(minutes=15)
   )

Your DataFrame should include the target variable and any features you want to use for forecasting:

.. code-block:: python

   # Example data structure
   #                      load  temperature  windspeed  is_weekend
   # timestamp                                                    
   # 2024-01-01 00:00:00  1250         5.2        3.1           0
   # 2024-01-01 00:15:00  1180         5.1        3.2           0
   # 2024-01-01 00:30:00  1150         5.0        3.4           0
   # ...

The ``sample_interval`` parameter tells OpenSTEF how frequently your data is sampled. Common values are ``timedelta(minutes=15)`` for 15-minute data or ``timedelta(hours=1)`` for hourly data.

Step 2: Configuring Your Model
-------------------------------

OpenSTEF provides a ``ForecastingModel`` that combines preprocessing, a forecaster, and postprocessing into a single pipeline. The most common forecaster is ``XGBQuantileForecaster``, which uses gradient boosting to predict multiple quantiles.

.. code-block:: python

   from openstef.model import ForecastingModel
   from openstef.model.forecaster import XGBQuantileForecaster
   from openstef.preprocessing import TransformPipeline
   from openstef.preprocessing.transforms import (
       AddMissingValuesAhead,
       AddLagFeatures,
       AddWeatherFeatures,
   )
   
   # Configure preprocessing pipeline
   preprocessing = TransformPipeline([
       AddMissingValuesAhead(),  # Handle missing values in future data
       AddLagFeatures(lag_hours=[24, 48, 168]),  # Add historical lags
       AddWeatherFeatures(),  # Engineer weather-based features
   ])
   
   # Create the forecaster
   forecaster = XGBQuantileForecaster(
       quantiles=[0.1, 0.5, 0.9],  # Predict 10th, 50th, 90th percentiles
       max_horizon=timedelta(hours=47),  # Forecast up to 47 hours ahead
   )
   
   # Combine into a complete model
   model = ForecastingModel(
       preprocessing=preprocessing,
       forecaster=forecaster,
   )

**Why these components?**

- ``AddMissingValuesAhead`` ensures your model can handle gaps in future weather forecasts
- ``AddLagFeatures`` creates features from historical load values (e.g., load 24 hours ago)
- ``AddWeatherFeatures`` generates useful features from raw weather data
- ``XGBQuantileForecaster`` provides probabilistic forecasts (not just point predictions)

The ``quantiles`` parameter determines which percentiles you want to predict. The median (0.5) gives you a central forecast, while 0.1 and 0.9 provide uncertainty bounds.

Step 3: Training the Model
---------------------------

Training fits both the preprocessing pipeline and the forecaster to your historical data:

.. code-block:: python

   # Fit the model
   result = model.fit(data=dataset)
   
   # Inspect training results
   print(f"Training completed in {result.duration:.2f} seconds")
   print(f"Model performance: {result.metrics}")

The ``fit()`` method:

1. Fits preprocessing transforms on your data (e.g., learns scaling parameters)
2. Transforms the data into model-ready features
3. Trains the forecaster on the transformed features
4. Returns a ``ModelFitResult`` with metrics and metadata

You can optionally provide validation and test sets:

.. code-block:: python

   # Split your data
   train_data = dataset.filter_by_range(end='2024-06-30')
   val_data = dataset.filter_by_range(start='2024-07-01', end='2024-07-31')
   test_data = dataset.filter_by_range(start='2024-08-01')
   
   # Train with validation
   result = model.fit(
       data=train_data,
       data_val=val_data,
       data_test=test_data,
   )

Providing validation data enables early stopping in XGBoost, which can prevent overfitting.

Step 4: Generating Forecasts
-----------------------------

Once trained, use ``predict()`` to generate forecasts. You need to provide:

- Historical data up to the forecast start time
- Future features (weather forecasts, calendar info, etc.)

.. code-block:: python

   # Prepare input data (historical + future features)
   # This should include all data up to forecast_start
   # plus future features for the forecast horizon
   forecast_start = pd.Timestamp('2024-08-15 00:00:00')
   
   # Generate forecasts
   forecasts = model.predict(
       data=dataset,
       forecast_start=forecast_start,
   )
   
   # Access forecast data
   forecast_df = forecasts.data
   print(forecast_df.head())

The returned ``ForecastDataset`` contains a DataFrame with columns for each quantile:

.. code-block:: python

   #                      q_0.1  q_0.5  q_0.9
   # timestamp                               
   # 2024-08-15 00:00:00   1050   1200   1350
   # 2024-08-15 00:15:00   1040   1190   1340
   # 2024-08-15 00:30:00   1030   1180   1330
   # ...

The median forecast (``q_0.5``) is typically your primary prediction, while the other quantiles represent uncertainty.

Step 5: Evaluating Performance
-------------------------------

OpenSTEF provides built-in evaluation through the ``score()`` method:

.. code-block:: python

   # Evaluate on test data
   metrics = model.score(data=test_data)
   
   # Access specific metrics
   print(f"R² score: {metrics['q_0.5']['R2']:.3f}")
   print(f"MAE: {metrics['q_0.5']['MAE']:.2f}")
   print(f"RMSE: {metrics['q_0.5']['RMSE']:.2f}")

The ``score()`` method compares the model's predictions against actual values in the provided dataset. It returns metrics for each quantile, including:

- **R²** - Coefficient of determination (1.0 is perfect)
- **MAE** - Mean Absolute Error
- **RMSE** - Root Mean Squared Error
- **Bias** - Average prediction error

For more sophisticated evaluation, including comparing multiple models over time, see the :doc:`backtesting` tutorial.

Understanding What Happens Inside
----------------------------------

When you call ``model.predict()``, OpenSTEF:

1. **Applies preprocessing** - Transforms your input data using the fitted pipeline (adds lags, engineers features, handles missing values)
2. **Extracts features** - Selects the relevant time window and features for prediction
3. **Generates predictions** - Runs the forecaster to produce quantile forecasts
4. **Applies postprocessing** - Optionally transforms outputs (e.g., clipping negative values)

The ``ForecastingModel`` ensures preprocessing is consistent between training and prediction, which is critical for model performance.

Next Steps
----------

Now that you understand the basic workflow, you can:

- **Customize preprocessing** - Add domain-specific feature engineering (see :doc:`advanced_customization`)
- **Compare models** - Use backtesting to evaluate different configurations (see :doc:`backtesting`)
- **Tune hyperparameters** - Adjust forecaster parameters for better performance
- **Deploy models** - Integrate OpenSTEF into production systems

The key to good forecasts is understanding your data and choosing appropriate features. Experiment with different lag periods, weather features, and model configurations to find what works best for your use case.