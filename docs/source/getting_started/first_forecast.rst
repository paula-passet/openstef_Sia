Your First Forecast with OpenSTEF
==================================

This tutorial walks you through creating your first energy forecast using OpenSTEF. You'll learn how to prepare data, configure a forecasting model, train it, generate predictions, and evaluate the results. Each step includes explanations of what's happening and why.

By the end of this tutorial, you'll understand the core workflow for building forecasting models with OpenSTEF.

.. note::
   Looking for the fastest path to a working forecast? See :doc:`quickstart` for a minimal example. This page provides more detailed explanations of each step.

Overview of the Forecasting Workflow
-------------------------------------

OpenSTEF follows a standard machine learning workflow:

1. **Data preparation**: Load and structure your time series data
2. **Model configuration**: Choose a forecaster and configure preprocessing
3. **Training**: Fit the model to historical data
4. **Forecasting**: Generate predictions for future time periods
5. **Evaluation**: Assess model performance with metrics

The library handles the complexity of feature engineering, model training, and prediction generation, letting you focus on your forecasting problem.

Step 1: Preparing Your Data
----------------------------

OpenSTEF expects time series data in a specific format. The core data structure is ``TimeSeriesDataset``, which wraps a pandas DataFrame with a datetime index.

Your input data should include:

- A datetime index with regular intervals (e.g., 15-minute or hourly)
- A target column (the variable you want to forecast, typically named ``"load"``)
- Optional feature columns (weather data, calendar features, etc.)

Here's how to create a dataset from a pandas DataFrame:

.. code-block:: python

   import pandas as pd
   from openstef.data_classes.model_specifications import TimeSeriesDataset
   
   # Load your data (example with CSV)
   df = pd.read_csv("energy_data.csv", parse_dates=["datetime"])
   df = df.set_index("datetime")
   
   # Ensure regular time intervals
   df = df.asfreq("15T")  # 15-minute intervals
   
   # Create TimeSeriesDataset
   dataset = TimeSeriesDataset(data=df)

Your DataFrame should look something like this:

.. code-block:: text

   datetime            load  temperature  windspeed
   2024-01-01 00:00    450.2  5.3         12.1
   2024-01-01 00:15    445.8  5.2         12.3
   2024-01-01 00:30    442.1  5.1         12.5
   ...

**Key points:**

- The datetime index must be sorted and have consistent intervals
- Missing values should be handled before creating the dataset (forward fill, interpolation, or removal)
- The target column name (default ``"load"``) will be referenced in your model configuration

Step 2: Configuring Your Model
-------------------------------

OpenSTEF provides a ``ForecastingModel`` class that combines three components:

- **Preprocessing pipeline**: Feature engineering transforms
- **Forecaster**: The machine learning algorithm
- **Postprocessing pipeline**: Output transforms (optional)

Let's configure a model using LightGBM, one of the most effective forecasters for energy data:

.. code-block:: python

   from datetime import timedelta
   from openstef.model.forecasting_model import ForecastingModel
   from openstef.model.forecaster.lgbm import LGBMForecaster
   from openstef.pipeline.transform_pipeline import TransformPipeline
   from openstef.model.transforms.holiday_features import AddHolidayFeatures
   from openstef.model.transforms.lag_features import AddLagFeatures
   from openstef.model.quantile import Q
   
   # Configure the forecaster
   forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # Predict multiple quantiles
       max_horizon=timedelta(hours=48),      # Forecast up to 48 hours ahead
   )
   
   # Configure preprocessing pipeline
   preprocessing = TransformPipeline([
       AddHolidayFeatures(country="NL"),     # Add Dutch holiday indicators
       AddLagFeatures(                        # Add historical lag features
           lags=[timedelta(hours=h) for h in [1, 24, 168]],  # 1h, 1d, 1w
       ),
   ])
   
   # Create the complete model
   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=14),    # Use 14 days of history
   )

**Configuration choices explained:**

- **Quantiles**: Predicting multiple quantiles (0.1, 0.5, 0.9) gives you probabilistic forecasts with uncertainty bands. The 0.5 quantile is the median prediction.
- **Max horizon**: Defines how far into the future the model can predict. For short-term energy forecasting, 24-48 hours is typical.
- **Holiday features**: Energy consumption patterns change on holidays. This transform adds binary indicators for holidays in your specified country.
- **Lag features**: Past values are strong predictors. This adds features like "load 1 hour ago", "load 1 day ago", etc.
- **Cutoff history**: Limits how much historical data is used for training to keep the model focused on recent patterns.

For available model types and their use cases, see the model selection guide in :doc:`../user_guide/models`.

Step 3: Training Your Model
----------------------------

Training fits both the preprocessing pipeline and the forecaster to your historical data:

.. code-block:: python

   # Split your data into training and validation sets
   split_date = pd.Timestamp("2024-06-01")
   train_data = TimeSeriesDataset(
       data=dataset.data[dataset.data.index < split_date]
   )
   val_data = TimeSeriesDataset(
       data=dataset.data[dataset.data.index >= split_date]
   )
   
   # Train the model
   fit_result = model.fit(
       data=train_data,
       data_val=val_data,  # Optional: used for early stopping
   )
   
   print(f"Training completed in {fit_result.training_duration}")
   print(f"Model is fitted: {model.is_fitted}")

**What happens during training:**

1. The preprocessing pipeline learns parameters from the training data (e.g., feature means for scaling)
2. The preprocessing transforms are applied to create model-ready features
3. The forecaster trains on the transformed features
4. If validation data is provided, it's used for early stopping to prevent overfitting

The ``fit_result`` object contains training metadata like duration and performance metrics.

Step 4: Generating Forecasts
-----------------------------

Once trained, use the model to generate predictions:

.. code-block:: python

   # Prepare input data for forecasting
   # This should include recent history up to your forecast start time
   forecast_start = pd.Timestamp("2024-07-01 00:00")
   input_data = TimeSeriesDataset(
       data=dataset.data[dataset.data.index < forecast_start]
   )
   
   # Generate forecasts
   forecasts = model.predict(input_data)
   
   # The result is a ForecastDataset with predictions
   print(forecasts.data.head())

The output ``ForecastDataset`` contains:

- A datetime index for forecast timestamps
- Columns for each quantile you configured (e.g., ``forecast_q0.1``, ``forecast_q0.5``, ``forecast_q0.9``)
- The forecast horizon for each prediction

Example output:

.. code-block:: text

   datetime            forecast_q0.1  forecast_q0.5  forecast_q0.9
   2024-07-01 00:15    420.5          455.2          490.8
   2024-07-01 00:30    418.2          452.7          488.1
   ...

**Important**: The model needs sufficient historical data before the forecast start time to compute lag features. Ensure your input data includes at least the maximum lag duration you configured.

Step 5: Evaluating Model Performance
-------------------------------------

OpenSTEF provides evaluation metrics to assess forecast quality:

.. code-block:: python

   from openstef.metrics.metrics import calculate_metrics
   
   # Get actual values for the forecast period
   actual_data = dataset.data[dataset.data.index >= forecast_start]
   
   # Calculate metrics
   metrics = calculate_metrics(
       y_true=actual_data["load"],
       y_pred=forecasts.data["forecast_q0.5"],  # Use median forecast
   )
   
   print(f"R²: {metrics['R2']:.3f}")
   print(f"MAE: {metrics['MAE']:.2f}")
   print(f"RMSE: {metrics['RMSE']:.2f}")

Common metrics for energy forecasting:

- **R² (R-squared)**: Proportion of variance explained (1.0 is perfect, higher is better)
- **MAE (Mean Absolute Error)**: Average absolute difference between predictions and actuals
- **RMSE (Root Mean Squared Error)**: Penalizes larger errors more heavily than MAE

For probabilistic forecasts, you can also evaluate quantile-specific metrics to assess uncertainty calibration.

Complete Example
----------------

Here's the full workflow in one script:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef.data_classes.model_specifications import TimeSeriesDataset
   from openstef.model.forecasting_model import ForecastingModel
   from openstef.model.forecaster.lgbm import LGBMForecaster
   from openstef.pipeline.transform_pipeline import TransformPipeline
   from openstef.model.transforms.holiday_features import AddHolidayFeatures
   from openstef.model.transforms.lag_features import AddLagFeatures
   from openstef.model.quantile import Q
   from openstef.metrics.metrics import calculate_metrics
   
   # 1. Load and prepare data
   df = pd.read_csv("energy_data.csv", parse_dates=["datetime"])
   df = df.set_index("datetime").asfreq("15T")
   dataset = TimeSeriesDataset(data=df)
   
   # 2. Configure model
   forecaster = LGBMForecaster(
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       max_horizon=timedelta(hours=48),
   )
   preprocessing = TransformPipeline([
       AddHolidayFeatures(country="NL"),
       AddLagFeatures(lags=[timedelta(hours=h) for h in [1, 24, 168]]),
   ])
   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=preprocessing,
       cutoff_history=timedelta(days=14),
   )
   
   # 3. Train model
   split_date = pd.Timestamp("2024-06-01")
   train_data = TimeSeriesDataset(data=df[df.index < split_date])
   val_data = TimeSeriesDataset(data=df[df.index >= split_date])
   model.fit(data=train_data, data_val=val_data)
   
   # 4. Generate forecasts
   forecast_start = pd.Timestamp("2024-07-01")
   input_data = TimeSeriesDataset(data=df[df.index < forecast_start])
   forecasts = model.predict(input_data)
   
   # 5. Evaluate
   actual = df.loc[forecasts.data.index, "load"]
   metrics = calculate_metrics(
       y_true=actual,
       y_pred=forecasts.data["forecast_q0.5"],
   )
   print(f"R²: {metrics['R2']:.3f}, MAE: {metrics['MAE']:.2f}")

Next Steps
----------

Now that you understand the basic workflow, explore these topics:

- **Model selection**: Learn about different forecaster types and when to use them in the user guide
- **Backtesting**: Evaluate model performance over multiple time periods with :doc:`backtesting`
- **Advanced customization**: Create custom transforms and forecasters with :doc:`advanced_customization`
- **Production deployment**: Save and load trained models for operational forecasting

For working with real-world data sources and more complex scenarios, see the examples in the ``examples/`` directory of the OpenSTEF repository.