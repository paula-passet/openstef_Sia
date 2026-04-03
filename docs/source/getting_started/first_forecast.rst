Your First Forecast
====================

This tutorial walks you through creating your first forecast with OpenSTEF, explaining each step in detail. You'll learn how to prepare data, configure a model, train it, generate forecasts, and evaluate the results.

If you're looking for the fastest path to a working example, see :doc:`quickstart`. This page provides deeper explanations of what happens at each step and why.

Overview
--------

A typical forecasting workflow in OpenSTEF involves five key steps:

1. **Data preparation**: Load and format your time series data
2. **Model configuration**: Set up preprocessing, forecaster, and postprocessing
3. **Training**: Fit the model to historical data
4. **Forecasting**: Generate predictions for future time periods
5. **Evaluation**: Assess forecast quality with metrics

We'll work through each step with a practical example, building a complete forecasting pipeline.

Step 1: Preparing Your Data
----------------------------

OpenSTEF expects time series data in a specific format. The library uses ``TimeSeriesDataset`` objects that wrap pandas DataFrames with additional metadata.

Your input data should have:

- A datetime index (timezone-aware recommended)
- A target column (the variable you want to forecast, e.g., "load")
- Feature columns (weather data, calendar features, etc.)

Here's how to prepare your data:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data (example with CSV)
   df = pd.read_csv("energy_data.csv", parse_dates=["datetime"])
   df = df.set_index("datetime")
   
   # Ensure timezone awareness
   if df.index.tz is None:
       df.index = df.index.tz_localize("Europe/Amsterdam")
   
   # Create a TimeSeriesDataset
   dataset = TimeSeriesDataset(
       data=df,
       target_column="load"
   )

The ``target_column`` parameter tells OpenSTEF which column contains the values you want to forecast. Common target columns include "load" for energy consumption or "generation" for renewable energy production.

**Why this matters**: The ``TimeSeriesDataset`` structure allows OpenSTEF to track metadata about your data throughout the pipeline, ensuring consistent handling of time zones, sample intervals, and column roles.

Step 2: Configuring Your Model
-------------------------------

OpenSTEF models consist of three main components:

- **Preprocessing pipeline**: Transforms raw data into model-ready features
- **Forecaster**: The core machine learning algorithm
- **Postprocessing pipeline**: Transforms model outputs into final predictions

The simplest way to configure a model is using the workflow pattern:

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.workflows.forecasting import (
       create_forecasting_workflow,
       ForecastingWorkflowConfig
   )
   from openstef_core.metrics import Q
   from openstef_core.time import LeadTime
   
   # Configure the workflow
   config = ForecastingWorkflowConfig(
       model_type="lgbm",  # LightGBM forecaster
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # Predict multiple quantiles
       horizons=[LeadTime.from_string("PT48H")],  # 48-hour ahead forecast
       sample_interval=timedelta(minutes=15),  # 15-minute data
       target_column="load"
   )
   
   # Create the workflow
   workflow = create_forecasting_workflow(config)

**Model type options**: OpenSTEF supports several forecasters:

- ``"lgbm"``: LightGBM gradient boosting (recommended for most use cases)
- ``"xgboost"``: XGBoost gradient boosting
- ``"lgbmlinear"``: Linear LightGBM model
- ``"gblinear"``: Linear gradient boosting
- ``"flatliner"``: Simple baseline using recent history
- ``"median"``: Constant median baseline

**Quantiles**: Instead of just point forecasts, OpenSTEF produces probabilistic forecasts. Quantile 0.5 is the median (typical "best guess"), while 0.1 and 0.9 give you prediction intervals for uncertainty quantification.

**Horizons**: The forecast horizon defines how far ahead you're predicting. ``PT48H`` means 48 hours in ISO 8601 duration format.

Step 3: Training the Model
---------------------------

Training fits the model to your historical data. OpenSTEF automatically handles preprocessing, feature engineering, and forecaster training:

.. code-block:: python

   # Train the model
   result = workflow.fit(dataset)
   
   # Check training results
   print(f"Training completed: {result.success}")
   print(f"Training metrics: {result.metrics}")

The ``fit()`` method:

1. Applies preprocessing transforms (lag features, holiday indicators, scaling)
2. Trains the forecaster on the processed features
3. Fits postprocessing transforms (if any)
4. Returns a ``ModelFitResult`` with training metrics

**What's happening under the hood**: The preprocessing pipeline automatically generates useful features like:

- Lag features (recent historical values)
- Time-based features (hour of day, day of week)
- Holiday indicators (if location is configured)
- Weather feature transformations

You don't need to manually create these features—OpenSTEF handles feature engineering automatically based on best practices for energy forecasting.

Step 4: Generating Forecasts
-----------------------------

Once trained, use the model to generate forecasts for new data:

.. code-block:: python

   from datetime import datetime
   
   # Prepare forecast input data
   # This should include recent history plus any available future features
   forecast_data = TimeSeriesDataset(
       data=recent_df,  # DataFrame with recent history
       target_column="load"
   )
   
   # Generate forecasts
   forecast_start = datetime(2024, 1, 15, 0, 0, tzinfo=df.index.tz)
   forecasts = workflow.predict(forecast_data, forecast_start=forecast_start)
   
   # Access forecast results
   forecast_df = forecasts.data
   print(forecast_df[["forecast", "quantile_P10", "quantile_P90"]])

The ``predict()`` method:

1. Preprocesses the input data using the fitted pipeline
2. Generates predictions from the trained forecaster
3. Applies postprocessing transforms
4. Returns a ``ForecastDataset`` with predictions for all configured quantiles

**Forecast start time**: This parameter defines when your forecast begins. The model uses all data before this time as history and predicts values after it.

**Required history**: The model needs sufficient historical data to compute lag features. If your preprocessing uses 14-day lags, ensure your ``forecast_data`` includes at least 14 days before the ``forecast_start``.

Step 5: Evaluating Forecast Quality
------------------------------------

Assess your forecast quality using standard metrics:

.. code-block:: python

   from openstef_core.metrics import calculate_metrics
   
   # Compare forecasts to actual values
   # (Assuming you have actual values for the forecast period)
   metrics = calculate_metrics(
       y_true=actual_values,
       y_pred=forecast_df["forecast"],
       quantile=Q(0.5)
   )
   
   print(f"MAE: {metrics['MAE']:.2f}")
   print(f"RMSE: {metrics['RMSE']:.2f}")
   print(f"R²: {metrics['R2']:.3f}")

Common metrics for energy forecasting:

- **MAE** (Mean Absolute Error): Average forecast error in the same units as your target
- **RMSE** (Root Mean Squared Error): Penalizes larger errors more heavily
- **R²**: Proportion of variance explained (1.0 is perfect, 0.0 is no better than mean)

For probabilistic forecasts, also evaluate quantile coverage and sharpness. See the evaluation documentation for more details on probabilistic metrics.

Putting It All Together
------------------------

Here's a complete example combining all steps:

.. code-block:: python

   import pandas as pd
   from datetime import datetime, timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.metrics import Q
   from openstef_core.time import LeadTime
   from openstef_beam.workflows.forecasting import (
       create_forecasting_workflow,
       ForecastingWorkflowConfig
   )
   
   # 1. Load and prepare data
   df = pd.read_csv("energy_data.csv", parse_dates=["datetime"])
   df = df.set_index("datetime").tz_localize("Europe/Amsterdam")
   
   # Split into training and test sets
   split_date = datetime(2024, 1, 1, tzinfo=df.index.tz)
   train_df = df[df.index < split_date]
   test_df = df[df.index >= split_date]
   
   train_data = TimeSeriesDataset(data=train_df, target_column="load")
   
   # 2. Configure model
   config = ForecastingWorkflowConfig(
       model_type="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       horizons=[LeadTime.from_string("PT48H")],
       sample_interval=timedelta(minutes=15),
       target_column="load"
   )
   workflow = create_forecasting_workflow(config)
   
   # 3. Train
   result = workflow.fit(train_data)
   print(f"Training R²: {result.metrics.get('R2', 'N/A')}")
   
   # 4. Forecast
   forecast_data = TimeSeriesDataset(data=test_df, target_column="load")
   forecasts = workflow.predict(forecast_data, forecast_start=split_date)
   
   # 5. Evaluate
   print(f"Generated {len(forecasts.data)} forecast points")
   print(f"Forecast range: {forecasts.data.index[0]} to {forecasts.data.index[-1]}")

Saving and Loading Models
--------------------------

To reuse trained models without retraining:

.. code-block:: python

   from openstef_beam.storage import LocalModelStorage
   from pathlib import Path
   
   # Save the trained model
   storage = LocalModelStorage(base_path=Path("./models"))
   storage.save(model=workflow, model_id="my_first_model")
   
   # Load it later
   loaded_workflow = storage.load(model_id="my_first_model")
   forecasts = loaded_workflow.predict(new_data, forecast_start=datetime.now())

Model storage preserves the entire pipeline state, including fitted preprocessing transforms and trained forecaster parameters.

Next Steps
----------

Now that you understand the basic forecasting workflow:

- **Compare models**: See :doc:`backtesting` to evaluate different model types and configurations
- **Customize pipelines**: Learn :doc:`advanced_customization` for custom preprocessing and postprocessing
- **Production deployment**: Check the deployment guide for operationalizing your forecasts

For troubleshooting installation issues, refer to :doc:`installation`.