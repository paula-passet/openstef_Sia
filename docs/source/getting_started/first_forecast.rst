Your First Forecast
====================

This tutorial walks you through creating your first forecast with OpenSTEF. You'll learn how to prepare data, configure a model, train it, generate predictions, and evaluate the results. By the end, you'll understand the complete forecasting workflow and be ready to apply it to your own energy data.

If you're looking for the absolute fastest path to a working forecast, see :doc:`quickstart`. This page provides more detailed explanations of each step and why it matters.

Overview of the Forecasting Workflow
-------------------------------------

OpenSTEF's forecasting workflow consists of five key steps:

1. **Data preparation**: Load and format your time series data
2. **Model configuration**: Choose a forecasting algorithm and preprocessing steps
3. **Training**: Fit the model to historical data
4. **Prediction**: Generate forecasts for future time periods
5. **Evaluation**: Assess forecast quality with metrics

Each step builds on the previous one, creating a complete pipeline from raw data to actionable forecasts.

Step 1: Preparing Your Data
----------------------------

OpenSTEF expects time series data in a specific format. Your data should be a pandas DataFrame with:

- A datetime index (timezone-aware recommended)
- A target column containing the values you want to forecast (e.g., energy load)
- Feature columns that help predict the target (e.g., weather data, calendar features)

Here's how to prepare a basic dataset:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   
   # Load your data (example with CSV)
   df = pd.read_csv('energy_data.csv', parse_dates=['datetime'])
   df = df.set_index('datetime')
   
   # Ensure timezone awareness
   if df.index.tz is None:
       df.index = df.index.tz_localize('UTC')
   
   # Create a TimeSeriesDataset
   data = TimeSeriesDataset(df)

Your DataFrame should include a target column (the value to forecast) and feature columns. Common features for energy forecasting include:

- Temperature, wind speed, solar radiation
- Hour of day, day of week, month
- Lagged values of the target (added automatically by preprocessing)
- Holiday indicators

**Why this matters**: OpenSTEF's preprocessing pipeline expects standardized input. The ``TimeSeriesDataset`` wrapper validates your data structure and ensures compatibility with all model components.

Step 2: Configuring Your Model
-------------------------------

OpenSTEF provides a ``ForecastingModel`` class that combines a forecasting algorithm with preprocessing and postprocessing pipelines. You need to specify:

- A **forecaster**: The machine learning algorithm (e.g., XGBoost, LightGBM)
- A **preprocessing pipeline**: Transforms raw data into model-ready features
- **Cutoff history**: How much historical data to retain for creating lag features

Here's a basic configuration:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models import ForecastingModel
   from openstef_models.forecasters import XGBQuantileForecaster
   from openstef_models.preprocessing import StandardPreprocessingPipeline
   
   # Configure the forecasting algorithm
   forecaster = XGBQuantileForecaster(
       quantiles=[0.1, 0.5, 0.9],  # Predict 10th, 50th, 90th percentiles
       max_horizon=timedelta(hours=47),  # Forecast up to 47 hours ahead
   )
   
   # Create the model with preprocessing
   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=StandardPreprocessingPipeline(),
       cutoff_history=timedelta(days=14),  # Keep 14 days for lag features
   )

**Understanding the components**:

- **Quantiles**: OpenSTEF produces probabilistic forecasts. Quantiles represent uncertainty—the 10th percentile is a conservative estimate, the 90th is optimistic, and the 50th (median) is the central prediction.
- **Max horizon**: How far into the future you want to forecast. Energy systems typically need 1-2 day ahead forecasts.
- **Preprocessing pipeline**: Automatically creates features like lag values, rolling statistics, and temporal encodings. The ``StandardPreprocessingPipeline`` handles common transformations.
- **Cutoff history**: Determines the window of historical data used for lag features. If you create a 24-hour lag, you need at least 24 hours of history. Set this to match your maximum lag.

Step 3: Training the Model
---------------------------

Training fits the model to your historical data. The model learns patterns like daily cycles, weather dependencies, and seasonal trends.

.. code-block:: python

   # Train on historical data
   result = model.fit(data)
   
   # Inspect training results
   print(f"Training completed in {result.duration}")
   print(f"Feature importance: {result.feature_importance}")

The ``fit()`` method:

1. Splits data into training, validation, and test sets
2. Applies preprocessing transformations (creating lag features, scaling, etc.)
3. Trains the underlying forecaster on the processed data
4. Returns a ``ModelFitResult`` with training metrics and metadata

**What's happening during training**: The preprocessing pipeline analyzes your data to determine appropriate transformations. For example, it identifies which columns need scaling, creates lag features based on your target column, and encodes temporal patterns. The forecaster then learns relationships between these features and the target values.

**Training data requirements**: You typically need at least several weeks of historical data for reliable forecasts. More data helps the model learn seasonal patterns and rare events. Ensure your data covers diverse conditions (different weather, load patterns, etc.).

Step 4: Generating Forecasts
-----------------------------

Once trained, use the model to generate forecasts for new data. The input data should have the same structure as training data but can extend into the future (with features but no target values).

.. code-block:: python

   # Prepare forecast input data (features for the forecast period)
   forecast_data = TimeSeriesDataset(new_df)
   
   # Generate forecasts
   forecasts = model.predict(forecast_data)
   
   # Access predictions
   print(forecasts.df)  # DataFrame with forecast quantiles

The ``predict()`` method:

1. Applies the same preprocessing transformations used during training
2. Generates predictions for each quantile
3. Returns a ``ForecastDataset`` with forecast values indexed by time

**Forecast output structure**: The resulting DataFrame contains columns for each quantile (e.g., ``q0.1``, ``q0.5``, ``q0.9``) and metadata columns. Each row represents a forecast for a specific time point.

**Handling missing features**: If your forecast period extends beyond available feature data (e.g., you have weather forecasts for only 48 hours), predictions will only cover the period with complete features. OpenSTEF won't extrapolate missing feature values.

Step 5: Evaluating Forecast Quality
------------------------------------

Evaluation compares your forecasts against actual observed values to measure accuracy. OpenSTEF provides comprehensive metrics for probabilistic forecasts.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.evaluation.metric_providers import (
       MAEProvider, RMSEProvider, QuantileLossProvider
   )
   
   # Configure evaluation
   eval_config = EvaluationConfig()
   
   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[0.1, 0.5, 0.9],
       window_metric_providers=[MAEProvider(), RMSEProvider()],
       global_metric_providers=[QuantileLossProvider()],
   )
   
   # Run evaluation (requires ground truth data)
   report = eval_pipeline.run(
       ground_truth=actual_values,
       predictions=forecasts,
       target_column='load',
   )
   
   # Inspect metrics
   print(report.global_metrics)

**Key metrics to understand**:

- **MAE (Mean Absolute Error)**: Average magnitude of forecast errors. Lower is better. Measured in the same units as your target (e.g., MW).
- **RMSE (Root Mean Squared Error)**: Similar to MAE but penalizes large errors more heavily.
- **Quantile Loss**: Evaluates probabilistic forecast quality. Checks if the predicted quantiles match the observed distribution.

**Why evaluation matters**: Metrics tell you whether your model is production-ready. They help you compare different configurations, identify problematic time periods (e.g., poor performance during extreme weather), and track model degradation over time.

For more advanced evaluation techniques, including comparing multiple models systematically, see :doc:`backtesting`.

Putting It All Together
------------------------

Here's a complete example combining all steps:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.models import ForecastingModel
   from openstef_models.forecasters import XGBQuantileForecaster
   from openstef_models.preprocessing import StandardPreprocessingPipeline
   
   # 1. Prepare data
   df = pd.read_csv('energy_data.csv', parse_dates=['datetime'])
   df = df.set_index('datetime').tz_localize('UTC')
   data = TimeSeriesDataset(df)
   
   # 2. Configure model
   forecaster = XGBQuantileForecaster(
       quantiles=[0.1, 0.5, 0.9],
       max_horizon=timedelta(hours=47),
   )
   
   model = ForecastingModel(
       forecaster=forecaster,
       preprocessing=StandardPreprocessingPipeline(),
       cutoff_history=timedelta(days=14),
   )
   
   # 3. Train
   result = model.fit(data)
   print(f"Training completed: {result.duration}")
   
   # 4. Forecast
   forecast_data = TimeSeriesDataset(future_df)
   forecasts = model.predict(forecast_data)
   
   # 5. Save or use forecasts
   forecasts.df.to_csv('forecasts.csv')

Next Steps
----------

Now that you understand the basic workflow, you can:

- Explore :doc:`advanced_customization` to tailor preprocessing and model behavior
- Learn about :doc:`backtesting` to systematically compare model configurations
- Review the API documentation for detailed parameter options

The key to effective forecasting is iteration: train a model, evaluate it, adjust your configuration, and repeat. OpenSTEF's modular design makes this experimentation straightforward.