Your First Forecast with OpenSTEF
==================================

This tutorial walks you through creating your first forecast with OpenSTEF. You'll learn how to prepare data, configure a forecasting model, train it, generate predictions, and evaluate the results. By the end, you'll understand the complete forecasting workflow and be ready to apply it to your own energy forecasting problems.

If you're looking for the absolute quickest path to a working forecast, see :doc:`quickstart`. This page provides more detailed explanations of what each step does and why.

Overview
--------

A typical OpenSTEF forecasting workflow consists of five main steps:

1. **Data preparation**: Load and structure your time series data
2. **Model configuration**: Set up preprocessing, forecaster, and postprocessing
3. **Training**: Fit the model to historical data
4. **Forecasting**: Generate predictions for future time periods
5. **Evaluation**: Assess model performance with metrics

Let's work through each step in detail.

Step 1: Preparing Your Data
----------------------------

OpenSTEF uses the ``TimeSeriesDataset`` class to represent time series data. This structure ensures your data has proper timestamps, a consistent sample interval, and the features needed for forecasting.

Creating a TimeSeriesDataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start with a pandas DataFrame containing your historical load data and features:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef.datasets import TimeSeriesDataset
   
   # Create sample data with 15-minute intervals
   timestamps = pd.date_range(
       start='2024-01-01',
       end='2024-12-31',
       freq='15min'
   )
   
   data = pd.DataFrame({
       'load': [100 + 20 * i % 50 for i in range(len(timestamps))],
       'temperature': [15 + 10 * (i % 96) / 96 for i in range(len(timestamps))],
       'hour': timestamps.hour,
       'dayofweek': timestamps.dayofweek,
   }, index=timestamps)
   
   # Wrap in TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=data,
       sample_interval=timedelta(minutes=15)
   )

The ``sample_interval`` parameter is critical—it tells OpenSTEF the time resolution of your data. This affects how lags, horizons, and forecast ranges are calculated.

For more complex scenarios with data versioning (useful for backtesting with realistic data arrival times), use ``VersionedTimeSeriesDataset``:

.. code-block:: python

   from openstef.datasets import VersionedTimeSeriesDataset
   
   # Create from DataFrame directly
   versioned_dataset = VersionedTimeSeriesDataset.from_dataframe(
       data=data,
       sample_interval=timedelta(minutes=15)
   )

Data Requirements
^^^^^^^^^^^^^^^^^

Your dataset should include:

- **Target variable**: The load or energy consumption you want to forecast (typically named ``load``)
- **Temporal features**: Hour of day, day of week, month, etc.
- **Weather features**: Temperature, wind speed, solar radiation (if available)
- **Sufficient history**: At least several weeks of data, preferably months or years

OpenSTEF will automatically use the DataFrame index as timestamps. Ensure your index is a ``DatetimeIndex`` with consistent intervals.

Step 2: Configuring Your Model
-------------------------------

OpenSTEF uses a pipeline architecture that chains together preprocessing, forecasting, and postprocessing steps. The ``CustomForecastingWorkflow`` class provides a high-level interface for configuring this pipeline.

Basic Configuration
^^^^^^^^^^^^^^^^^^^

Here's a complete configuration for a forecasting workflow:

.. code-block:: python

   from openstef.workflows import create_forecasting_workflow
   from openstef.workflows.config import ForecastingWorkflowConfig
   
   # Configure the workflow
   config = ForecastingWorkflowConfig(
       model_type="xgboost",
       target_column="load",
       horizons=[0.25, 24.0, 47.0],  # 15 min, 24 hours, 47 hours
       quantiles=[0.1, 0.5, 0.9],    # Prediction intervals
       add_holiday_features=True,
       add_lag_features=True,
       max_lag_hours=168,  # One week of lags
       train_split_fraction=0.8,
       verbosity=1
   )
   
   # Create the workflow
   workflow = create_forecasting_workflow(config)

Understanding Configuration Options
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Key configuration parameters:

- **model_type**: The forecasting algorithm (``"xgboost"``, ``"linear"``, ``"arima"``, etc.)
- **horizons**: Forecast lead times in hours. ``[0.25, 24.0, 47.0]`` means you'll get predictions for 15 minutes, 24 hours, and 47 hours ahead
- **quantiles**: Prediction intervals. ``[0.1, 0.5, 0.9]`` gives you the 10th percentile (lower bound), median (point forecast), and 90th percentile (upper bound)
- **add_holiday_features**: Automatically adds features for public holidays
- **add_lag_features**: Includes historical load values as features
- **max_lag_hours**: How far back to look for lag features

The workflow automatically handles feature engineering, data splitting, and model validation based on your configuration.

Step 3: Training the Model
---------------------------

Once configured, training is straightforward. The workflow handles data preprocessing, feature engineering, and model fitting:

.. code-block:: python

   # Train the model
   trained_workflow = workflow.train(
       data=dataset,
       forecaster_name="my_forecaster"
   )
   
   print(f"Training complete. Model stored as: my_forecaster")

What Happens During Training
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Behind the scenes, OpenSTEF:

1. **Validates data**: Checks for flat-liners, missing values, and data quality issues
2. **Engineers features**: Adds holiday indicators, lag features, and temporal encodings
3. **Splits data**: Separates training and validation sets based on ``train_split_fraction``
4. **Scales features**: Normalizes numeric features for better model performance
5. **Trains forecaster**: Fits the model (e.g., XGBoost) to the prepared data
6. **Validates performance**: Evaluates on the validation set and stores metrics

The trained model is stored within the workflow object and can be persisted to disk for later use.

Using Validation Data
^^^^^^^^^^^^^^^^^^^^^^

For better model evaluation, provide explicit validation data:

.. code-block:: python

   # Split your data manually
   train_data = dataset.slice(end='2024-10-31')
   val_data = dataset.slice(start='2024-11-01', end='2024-11-30')
   
   # Train with validation set
   trained_workflow = workflow.train(
       data=train_data,
       data_val=val_data,
       forecaster_name="my_forecaster"
   )

This gives you more control over the train/validation split and ensures realistic evaluation.

Step 4: Generating Forecasts
-----------------------------

After training, use the workflow to generate forecasts for future time periods:

.. code-block:: python

   # Create forecast for December 2024
   forecast_data = dataset.slice(start='2024-12-01', end='2024-12-31')
   
   # Generate predictions
   predictions = trained_workflow.predict(
       data=forecast_data,
       forecaster_name="my_forecaster"
   )
   
   # Access forecast DataFrame
   forecast_df = predictions.data
   print(forecast_df.head())

The returned ``ForecastDataset`` contains predictions for all configured horizons and quantiles. The DataFrame has a multi-level column structure:

.. code-block:: python

   # Example output structure:
   #                      quantile_0.1  quantile_0.5  quantile_0.9
   # 2024-12-01 00:00:00         95.2         105.3         115.8
   # 2024-12-01 00:15:00         96.1         106.5         117.2
   # ...

Understanding Forecast Horizons
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When you configured ``horizons=[0.25, 24.0, 47.0]``, you specified three forecast lead times. For each timestamp in your forecast range, OpenSTEF generates predictions at these lead times:

- **0.25 hours (15 min)**: Very short-term forecast
- **24.0 hours**: Day-ahead forecast
- **47.0 hours**: Two-day-ahead forecast

The workflow automatically handles the different feature sets needed for each horizon.

Step 5: Evaluating Performance
-------------------------------

Assess your model's accuracy using OpenSTEF's evaluation metrics:

.. code-block:: python

   from openstef.metrics import calculate_metrics
   
   # Get actual values
   actual = forecast_data.data['load']
   
   # Get predictions (median quantile)
   predicted = forecast_df['quantile_0.5']
   
   # Calculate metrics
   metrics = calculate_metrics(
       y_true=actual,
       y_pred=predicted
   )
   
   print(f"MAE: {metrics['mae']:.2f}")
   print(f"RMSE: {metrics['rmse']:.2f}")
   print(f"R²: {metrics['r2']:.3f}")

Common Evaluation Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides several metrics for forecast evaluation:

- **MAE (Mean Absolute Error)**: Average absolute difference between predictions and actuals
- **RMSE (Root Mean Squared Error)**: Square root of average squared errors (penalizes large errors more)
- **R² (Coefficient of Determination)**: Proportion of variance explained by the model (1.0 is perfect)
- **MAPE (Mean Absolute Percentage Error)**: Average percentage error
- **Skill Score**: Performance relative to a baseline model

For probabilistic forecasts with multiple quantiles, evaluate prediction interval coverage:

.. code-block:: python

   # Check if actuals fall within prediction intervals
   lower_bound = forecast_df['quantile_0.1']
   upper_bound = forecast_df['quantile_0.9']
   
   coverage = ((actual >= lower_bound) & (actual <= upper_bound)).mean()
   print(f"80% prediction interval coverage: {coverage:.1%}")

Ideally, your 80% prediction interval (10th to 90th percentile) should contain about 80% of actual values.

Next Steps
----------

You now understand the complete forecasting workflow in OpenSTEF. Here are some ways to build on this foundation:

- **Compare models**: Use :doc:`backtesting` to systematically evaluate different model configurations
- **Customize pipelines**: See :doc:`advanced_customization` for custom feature engineering and model architectures
- **Production deployment**: Learn about model persistence, monitoring, and retraining strategies

For working code examples, explore the ``examples/`` directory in the OpenSTEF repository, particularly ``configuring_model_pipeline_example.py`` which demonstrates a complete end-to-end workflow.