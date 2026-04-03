Your First Forecast with OpenSTEF
==================================

This tutorial walks you through creating your first forecast with OpenSTEF, explaining each step in detail. You'll learn how to prepare data, configure a forecasting model, train it, generate predictions, and evaluate the results.

By the end of this tutorial, you'll understand the core workflow and be ready to apply OpenSTEF to your own forecasting problems.

.. note::
   If you just want to see a minimal working example, check out the :doc:`quickstart` page. This tutorial provides deeper explanations of what happens at each step and why.

Overview of the Forecasting Workflow
-------------------------------------

OpenSTEF follows a standard machine learning workflow:

1. **Data Preparation**: Load and structure your time series data
2. **Model Configuration**: Set up preprocessing, forecaster, and postprocessing
3. **Training**: Fit the model to historical data
4. **Forecasting**: Generate predictions for future time periods
5. **Evaluation**: Assess forecast quality with metrics

Each step builds on the previous one, and understanding this flow will help you customize OpenSTEF for your specific use case.

Step 1: Preparing Your Data
----------------------------

OpenSTEF uses the ``TimeSeriesDataset`` class to structure time series data. This dataset must have a datetime index and include both your target variable (what you want to forecast) and any predictor features.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data into a pandas DataFrame
   # Must have a datetime index and include your target column
   df = pd.read_csv("energy_data.csv", index_col="datetime", parse_dates=True)
   
   # Create a TimeSeriesDataset
   dataset = TimeSeriesDataset(data=df)

Your DataFrame should include:

- **Target column**: The variable you want to forecast (e.g., "load" for energy demand)
- **Predictor features**: Weather data, calendar features, or other relevant inputs
- **Datetime index**: Timestamps at regular intervals (e.g., 15-minute or hourly)

.. note::
   OpenSTEF expects data at regular intervals. If you have missing timestamps, you may need to resample or interpolate your data first.

Step 2: Configuring Your Model
-------------------------------

The ``ForecastingModel`` class orchestrates the complete forecasting pipeline. It combines three key components:

- **Preprocessing**: Feature engineering transforms (lags, holidays, scaling)
- **Forecaster**: The machine learning model that makes predictions
- **Postprocessing**: Optional transforms applied to predictions (e.g., clamping negative values)

Here's a complete configuration example:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster
   from openstef_models.preprocessing.feature_pipeline import FeaturePipeline
   from openstef_models.preprocessing.transforms import (
       AddHolidayFeatures,
       AddLagTransform,
       StandardScaler,
   )
   from openstef_core.types import LeadTime
   
   # Define preprocessing pipeline
   preprocessing = FeaturePipeline(
       transforms=[
           AddHolidayFeatures(country="NL"),  # Add Dutch holiday features
           AddLagTransform(lag=timedelta(days=7)),  # Add 7-day lag features
           StandardScaler(),  # Normalize features
       ],
       horizons=[LeadTime.from_string("PT48H")],  # 48-hour forecast horizon
   )
   
   # Create the forecasting model
   model = ForecastingModel(
       forecaster=LGBMForecaster(),
       preprocessing=preprocessing,
       target_column="load",
       cutoff_history=timedelta(days=14),  # Exclude first 14 days (lag warmup)
   )

**Why cutoff_history matters**: When you add lag transforms (like a 7-day lag), the first few days of your dataset will have NaN values because there's no historical data to look back to. The ``cutoff_history`` parameter tells OpenSTEF to exclude these incomplete rows from training. Set this to at least the maximum lag in your preprocessing pipeline.

Step 3: Training Your Model
----------------------------

Training fits the model to your historical data. Call the ``fit()`` method with your dataset:

.. code-block:: python

   # Train the model
   model.fit(dataset)

During training, OpenSTEF:

1. Applies preprocessing transforms to create features
2. Filters out incomplete data based on ``cutoff_history``
3. Trains the forecaster on the processed data
4. Stores the trained model internally for later prediction

The ``fit()`` method modifies the model in place, so you don't need to capture a return value.

.. note::
   Training time depends on your dataset size and model complexity. LightGBM models typically train in seconds to minutes for datasets with thousands of rows.

Step 4: Generating Forecasts
-----------------------------

Once trained, use the ``predict()`` method to generate forecasts:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset
   
   # Generate predictions
   forecast: ForecastDataset = model.predict(dataset)
   
   # Access the median forecast
   median_forecast = forecast.median_series
   print(median_forecast.head())
   
   # Access quantile forecasts (if configured)
   if forecast.quantiles_data is not None:
       print(forecast.quantiles_data.head())

The ``ForecastDataset`` returned by ``predict()`` contains:

- **median_series**: The point forecast (typically the 50th percentile)
- **quantiles_data**: Probabilistic forecasts at different quantiles (if your forecaster supports them)

By default, OpenSTEF generates forecasts starting from the end of your input data and extending for the configured horizon (e.g., 48 hours ahead).

Step 5: Evaluating Your Forecast
---------------------------------

To assess forecast quality, compare predictions against actual values using evaluation metrics:

.. code-block:: python

   from openstef_models.evaluation.metrics import calculate_metrics
   
   # Split your data into train and test sets
   split_point = len(dataset.data) - 96  # Reserve last 96 periods for testing
   train_data = TimeSeriesDataset(data=dataset.data.iloc[:split_point])
   test_data = TimeSeriesDataset(data=dataset.data.iloc[split_point:])
   
   # Train on training data
   model.fit(train_data)
   
   # Predict on test data
   test_forecast = model.predict(test_data)
   
   # Calculate metrics
   metrics = calculate_metrics(
       y_true=test_data.data["load"],
       y_pred=test_forecast.median_series,
   )
   
   print(f"R²: {metrics['R2']:.3f}")
   print(f"MAE: {metrics['MAE']:.3f}")
   print(f"RMSE: {metrics['RMSE']:.3f}")

Common evaluation metrics include:

- **R² (coefficient of determination)**: Measures how well predictions explain variance (1.0 is perfect)
- **MAE (mean absolute error)**: Average absolute difference between predictions and actuals
- **RMSE (root mean squared error)**: Penalizes large errors more than MAE

.. note::
   For more sophisticated evaluation including backtesting across multiple time periods, see the :doc:`backtesting` tutorial.

Understanding What Happens Under the Hood
------------------------------------------

When you call ``model.predict(dataset)``, OpenSTEF:

1. **Preprocesses the data**: Applies the same transforms used during training (holidays, lags, scaling)
2. **Restores the target column**: Ensures the target isn't accidentally transformed
3. **Filters by cutoff**: Removes incomplete rows based on ``cutoff_history``
4. **Generates predictions**: Passes processed features to the trained forecaster
5. **Applies postprocessing**: Runs any postprocessing transforms (if configured)
6. **Returns a ForecastDataset**: Packages predictions with metadata

This pipeline ensures consistency between training and prediction, which is critical for model performance.

Customizing Your Forecast
--------------------------

You can customize many aspects of the forecasting pipeline:

**Change the forecaster**: Swap ``LGBMForecaster`` for ``XGBForecaster``, ``GBLinearForecaster``, or other forecasters.

**Add more preprocessing**: Include additional transforms like ``AddTimeFeatures``, ``AddWeatherFeatures``, or custom transforms.

**Configure quantiles**: Specify which quantiles to predict for probabilistic forecasting.

**Adjust hyperparameters**: Pass hyperparameter dictionaries to forecasters for fine-tuning.

For advanced customization examples, see the :doc:`advanced_customization` tutorial.

Next Steps
----------

Now that you understand the basic forecasting workflow, you can:

- Explore the :doc:`backtesting` tutorial to compare different model configurations
- Learn about :doc:`advanced_customization` for power users
- Check the API reference for detailed parameter documentation

The core workflow you've learned here—prepare data, configure model, train, forecast, evaluate—applies to all OpenSTEF use cases, from simple experiments to production forecasting systems.