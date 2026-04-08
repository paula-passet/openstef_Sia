Your First Forecast with OpenSTEF
==================================

This tutorial walks you through creating your first energy load forecast using OpenSTEF. You'll learn how to prepare data, configure a forecasting workflow, train a model, generate predictions, and evaluate forecast quality.

By the end of this tutorial, you'll understand the complete forecasting lifecycle and have a working example you can adapt to your own data.

What You'll Learn
-----------------

- How to structure your data for OpenSTEF
- What the ``CustomForecastingWorkflow`` does and how to configure it
- How to train a model on historical data
- How to generate forecasts for future time periods
- How to evaluate forecast quality using standard metrics

Prerequisites
-------------

Make sure you've installed OpenSTEF following the :doc:`installation` guide. You'll also need historical energy load data and weather forecasts. If you want to jump straight to a minimal working example, see the :doc:`quickstart` guide.

Understanding the Workflow
---------------------------

OpenSTEF organizes forecasting into a clear workflow:

1. **Data Preparation**: Load and structure your time series data
2. **Model Configuration**: Set up the forecasting workflow with your preferences
3. **Training**: Fit the model to historical data
4. **Forecasting**: Generate predictions for future time periods
5. **Evaluation**: Measure forecast quality with metrics

The ``CustomForecastingWorkflow`` class orchestrates this entire process, handling feature engineering, model training, and prediction generation automatically.

Step 1: Prepare Your Data
--------------------------

OpenSTEF expects data in a ``TimeSeriesDataset`` object with a datetime index. Your dataset should include:

- **Target variable**: The energy load you want to forecast (default column name: ``load``)
- **Weather predictors**: Temperature, wind speed, radiation, etc.
- **Optional features**: Energy prices, calendar features, or custom predictors

Here's how to load and prepare your data:

.. code-block:: python

    import pandas as pd
    from openstef.data.dataset import TimeSeriesDataset
    from datetime import datetime

    # Load your data from CSV, database, or other source
    df = pd.read_csv("energy_load_data.csv", parse_dates=["datetime"])
    df = df.set_index("datetime")

    # Create a TimeSeriesDataset
    # This validates the data structure and prepares it for OpenSTEF
    dataset = TimeSeriesDataset(df)

    # Split into training and validation sets
    split_date = datetime(2023, 10, 1)
    training_data = dataset[dataset.index < split_date]
    validation_data = dataset[dataset.index >= split_date]

Your data should have columns like ``load``, ``temperature``, ``windspeed``, ``radiation``, etc. The exact column names can be configured in the workflow (see Step 2).

.. note::

   OpenSTEF handles missing values and performs automatic feature engineering during training. However, ensure your datetime index is regular (e.g., hourly or 15-minute intervals) for best results.

Step 2: Configure the Workflow
-------------------------------

The ``CustomForecastingWorkflow`` requires a configuration object that defines how forecasting should work. This includes which columns to use, how much historical data to consider, and model-specific settings:

.. code-block:: python

    from openstef.workflow.config import ForecastingWorkflowConfig
    from openstef.workflow.forecasting import CustomForecastingWorkflow
    from datetime import timedelta

    # Configure the forecasting workflow
    config = ForecastingWorkflowConfig(
        target_column="load",  # Column containing energy load
        temperature_column="temperature",
        windspeed_column="windspeed",
        radiation_column="radiation",
        predict_history=timedelta(days=14),  # Use 14 days of history for predictions
    )

    # Create the workflow
    workflow = CustomForecastingWorkflow(config=config)

The configuration controls many aspects of forecasting behavior. Key parameters include:

- ``target_column``: Name of the variable you're forecasting
- ``predict_history``: How much historical context to use when making predictions
- Weather column names: Tell OpenSTEF which columns contain weather data
- ``selected_features``: Control which features to include (default: all available)

For more advanced configuration options, see :doc:`advanced_customization`.

Step 3: Train the Model
------------------------

Training fits the model to your historical data. OpenSTEF automatically handles feature engineering, model selection, and hyperparameter tuning:

.. code-block:: python

    # Train the model
    fit_result = workflow.fit(data=training_data, data_val=validation_data)

    # Check if training succeeded
    if fit_result is not None:
        print("Model trained successfully!")
    else:
        print("Training failed - check for data quality issues")

During training, OpenSTEF:

- Engineers time-based features (hour of day, day of week, holidays)
- Creates lag features from historical load data
- Trains an XGBoost model with optimized hyperparameters
- Validates the model on your validation set (if provided)

The ``fit()`` method returns a ``ModelFitResult`` object containing training metrics and model information. If training fails (e.g., due to insufficient data or flatline detection), it returns ``None``.

.. note::

   Training can take several minutes depending on your data size. OpenSTEF includes automatic flatliner detection - if your data shows no variation, training will be skipped with a warning.

Step 4: Generate Forecasts
---------------------------

Once trained, use the workflow to generate forecasts for future time periods:

.. code-block:: python

    from datetime import datetime

    # Prepare data for forecasting
    # This should include historical context + the forecast period
    forecast_start = datetime(2023, 10, 1)
    forecast_data = dataset[dataset.index >= forecast_start - timedelta(days=14)]

    # Generate forecasts
    forecasts = workflow.predict(
        data=forecast_data,
        forecast_start=forecast_start
    )

    # Access the predictions
    predictions = forecasts.to_dataframe()
    print(predictions.head())

The ``predict()`` method returns a ``ForecastDataset`` containing:

- Point forecasts (expected values)
- Quantile forecasts (uncertainty estimates)
- Feature importance information

The ``forecast_start`` parameter tells OpenSTEF where historical data ends and the forecast period begins. This is crucial for preventing data leakage - the model only uses information available before this timestamp.

Step 5: Evaluate Forecast Quality
----------------------------------

Evaluate your forecasts using standard energy forecasting metrics. OpenSTEF provides several built-in metrics optimized for energy load forecasting:

.. code-block:: python

    from openstef.metrics.metrics import rmae, mae
    import numpy as np

    # Extract actual and predicted values
    y_true = validation_data.to_dataframe()["load"].values
    y_pred = predictions["forecast"].values[:len(y_true)]

    # Calculate metrics
    mae_score = mae(y_true, y_pred)
    rmae_score = rmae(y_true, y_pred, lower_quantile=0.05, upper_quantile=0.95)

    print(f"Mean Absolute Error: {mae_score:.2f} kW")
    print(f"Relative MAE: {rmae_score:.2%}")

**Key Metrics:**

- **MAE (Mean Absolute Error)**: Average absolute difference between predictions and actuals. Easy to interpret in the same units as your target variable.
- **rMAE (Relative MAE)**: MAE normalized by the data range (using quantiles). Makes errors comparable across different load scales. Lower is better.

The rMAE metric is particularly useful in energy forecasting because it accounts for the natural variability in load data. A rMAE below 5% is generally considered excellent, while 5-10% is good.

Putting It All Together
------------------------

Here's a complete example combining all the steps:

.. code-block:: python

    import pandas as pd
    from openstef.data.dataset import TimeSeriesDataset
    from openstef.workflow.config import ForecastingWorkflowConfig
    from openstef.workflow.forecasting import CustomForecastingWorkflow
    from openstef.metrics.metrics import rmae, mae
    from datetime import datetime, timedelta

    # 1. Load and prepare data
    df = pd.read_csv("energy_load_data.csv", parse_dates=["datetime"])
    df = df.set_index("datetime")
    dataset = TimeSeriesDataset(df)

    # 2. Split data
    split_date = datetime(2023, 10, 1)
    training_data = dataset[dataset.index < split_date]
    validation_data = dataset[dataset.index >= split_date]

    # 3. Configure and create workflow
    config = ForecastingWorkflowConfig(
        target_column="load",
        temperature_column="temperature",
        windspeed_column="windspeed",
        radiation_column="radiation",
        predict_history=timedelta(days=14),
    )
    workflow = CustomForecastingWorkflow(config=config)

    # 4. Train the model
    workflow.fit(data=training_data, data_val=validation_data)

    # 5. Generate forecasts
    forecast_data = dataset[dataset.index >= split_date - timedelta(days=14)]
    forecasts = workflow.predict(data=forecast_data, forecast_start=split_date)

    # 6. Evaluate
    y_true = validation_data.to_dataframe()["load"].values
    y_pred = forecasts.to_dataframe()["forecast"].values[:len(y_true)]
    print(f"rMAE: {rmae(y_true, y_pred):.2%}")

Next Steps
----------

Now that you understand the basic forecasting workflow, you can:

- **Compare models**: See :doc:`backtesting` to systematically evaluate different configurations
- **Customize behavior**: Explore :doc:`advanced_customization` for feature selection, custom callbacks, and model tuning
- **Deploy in production**: Use the trained workflow to generate operational forecasts

The workflow you've created can be saved and reused for operational forecasting. OpenSTEF handles model persistence automatically when you use callbacks with MLflow integration.