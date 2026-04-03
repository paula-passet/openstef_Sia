Backtesting Models
==================

Backtesting evaluates how well your forecasting models would have performed on historical data. This tutorial shows you how to run backtests, compare different model configurations, and analyze performance using OpenSTEF's evaluation metrics.

Unlike testing on a single holdout set, backtesting simulates real operational conditions by repeatedly training and predicting as new data becomes available. This gives you a realistic picture of model performance over time.

What You'll Learn
-----------------

This guide covers:

- Running a backtest simulation with historical data
- Comparing multiple model configurations
- Evaluating performance with deterministic and probabilistic metrics
- Visualizing results to identify strengths and weaknesses

.. note::
   Before starting, make sure you've completed the :doc:`first_forecast` tutorial. This guide assumes you're familiar with basic forecasting workflows.

Understanding Backtesting
-------------------------

Backtesting simulates how a model performs in production by:

1. Starting at a point in historical data
2. Training a model on data available up to that point
3. Making predictions for future time periods
4. Moving forward in time and repeating

This process reveals how models handle concept drift, seasonal changes, and data quality issues that appear in real operations.

Running Your First Backtest
----------------------------

The ``BacktestPipeline`` class orchestrates the backtesting process. You provide historical data and a forecaster configuration, and it returns predictions across the entire time period.

.. code-block:: python

   from datetime import datetime
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_core.forecasters import XGBoostForecaster
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Configure the backtesting simulation
   backtest_config = BacktestConfig(
       prediction_sample_interval=15,  # 15-minute predictions
       train_horizons_back=[7, 14, 21],  # Training window sizes in days
       prediction_horizon_hours=48,  # Forecast 48 hours ahead
   )
   
   # Create a forecaster with your desired configuration
   forecaster = XGBoostForecaster(
       horizon_minutes=15,
       quantiles=[0.1, 0.5, 0.9],  # Probabilistic forecasts
   )
   
   # Initialize the backtest pipeline
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )
   
   # Run the backtest
   predictions = pipeline.run(
       ground_truth=historical_load_data,
       predictors=historical_features,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True,
   )

The ``run`` method returns a ``TimeSeriesDataset`` containing all predictions with their timestamps. This dataset includes both point forecasts and quantile predictions if you configured probabilistic forecasting.

Comparing Multiple Models
--------------------------

To compare different model configurations, run separate backtests and evaluate each one. Here's how to compare two XGBoost models with different hyperparameters:

.. code-block:: python

   from openstef_beam.metrics import mae, rmae, r2
   
   # Define model configurations to compare
   configs = {
       "conservative": {
           "max_depth": 3,
           "learning_rate": 0.05,
           "n_estimators": 100,
       },
       "aggressive": {
           "max_depth": 8,
           "learning_rate": 0.1,
           "n_estimators": 200,
       },
   }
   
   # Run backtests for each configuration
   results = {}
   for name, params in configs.items():
       forecaster = XGBoostForecaster(
           horizon_minutes=15,
           **params,
       )
       
       pipeline = BacktestPipeline(backtest_config, forecaster)
       predictions = pipeline.run(
           ground_truth=historical_load_data,
           predictors=historical_features,
           start=start_date,
           end=end_date,
       )
       
       results[name] = predictions

Now you have predictions from both models covering the same time period, ready for comparison.

Evaluating Performance
----------------------

OpenSTEF provides metrics specifically designed for energy forecasting. These metrics account for the unique challenges of load forecasting, such as varying scales between peak and off-peak periods.

Deterministic Metrics
^^^^^^^^^^^^^^^^^^^^^

For point forecasts, use deterministic metrics that measure prediction accuracy:

.. code-block:: python

   import numpy as np
   from openstef_beam.metrics import mae, rmae, r2, mape
   
   # Extract actual values and predictions
   y_true = historical_load_data["load"].values
   y_pred_conservative = results["conservative"]["forecast"].values
   y_pred_aggressive = results["aggressive"]["forecast"].values
   
   # Calculate metrics for each model
   for name, y_pred in [("conservative", y_pred_conservative), 
                        ("aggressive", y_pred_aggressive)]:
       print(f"\n{name.upper()} MODEL:")
       print(f"  MAE:  {mae(y_true, y_pred):.2f} MW")
       print(f"  rMAE: {rmae(y_true, y_pred):.2%}")
       print(f"  R²:   {r2(y_true, y_pred):.3f}")
       print(f"  MAPE: {mape(y_true, y_pred):.2%}")

The relative MAE (rMAE) is particularly useful because it normalizes errors by the data range, making it easier to compare performance across different load profiles or time periods.

Probabilistic Metrics
^^^^^^^^^^^^^^^^^^^^^

If your forecaster produces quantile predictions, evaluate the quality of uncertainty estimates:

.. code-block:: python

   from openstef_beam.metrics import crps, rcrps, mean_absolute_calibration_error
   
   # Extract quantile predictions
   quantiles = [0.1, 0.5, 0.9]
   y_pred_quantiles = np.stack([
       results["conservative"][f"forecast_q{int(q*100)}"].values
       for q in quantiles
   ], axis=1)
   
   # Evaluate probabilistic forecasts
   crps_score = crps(y_true, y_pred_quantiles, quantiles)
   rcrps_score = rcrps(y_true, y_pred_quantiles, quantiles)
   calibration_error = mean_absolute_calibration_error(
       y_true, y_pred_quantiles, quantiles
   )
   
   print(f"CRPS:  {crps_score:.2f}")
   print(f"rCRPS: {rcrps_score:.2%}")
   print(f"Calibration Error: {calibration_error:.3f}")

The Continuous Ranked Probability Score (CRPS) measures both accuracy and sharpness of probabilistic forecasts. Lower scores indicate better performance. The calibration error tells you whether your prediction intervals are reliable—values near zero mean the intervals contain the actual values at the expected frequency.

Peak Detection Performance
^^^^^^^^^^^^^^^^^^^^^^^^^^

Energy system operators care especially about predicting peak loads that could cause congestion. Evaluate this with confusion matrix metrics:

.. code-block:: python

   from openstef_beam.metrics import confusion_matrix, precision_recall, fbeta
   
   # Define peak threshold (e.g., 90th percentile of load)
   peak_threshold = np.percentile(y_true, 90)
   
   # Calculate confusion matrix
   cm = confusion_matrix(
       y_true, 
       y_pred_conservative,
       threshold=peak_threshold,
   )
   
   # Get precision and recall
   pr = precision_recall(cm)
   
   # Calculate F-beta score (beta=2 weights recall higher)
   f2_score = fbeta(pr, beta=2.0)
   
   print(f"Peak Detection (threshold={peak_threshold:.1f} MW):")
   print(f"  Precision: {pr.precision:.2%}")
   print(f"  Recall:    {pr.recall:.2%}")
   print(f"  F2 Score:  {f2_score:.2%}")

For grid operations, recall (catching all peaks) is often more important than precision (avoiding false alarms), which is why we use an F2 score that weights recall more heavily.

Analyzing Results Over Time
----------------------------

Aggregate metrics hide important patterns. Break down performance by time period to identify when models struggle:

.. code-block:: python

   import pandas as pd
   
   # Create DataFrame with predictions and actuals
   df = pd.DataFrame({
       "timestamp": historical_load_data.index,
       "actual": y_true,
       "predicted": y_pred_conservative,
   })
   df["error"] = df["actual"] - df["predicted"]
   df["abs_error"] = df["error"].abs()
   
   # Analyze by month
   monthly_mae = df.groupby(df["timestamp"].dt.month)["abs_error"].mean()
   print("\nMAE by Month:")
   print(monthly_mae)
   
   # Analyze by hour of day
   hourly_mae = df.groupby(df["timestamp"].dt.hour)["abs_error"].mean()
   print("\nMAE by Hour:")
   print(hourly_mae)
   
   # Analyze by day of week
   daily_mae = df.groupby(df["timestamp"].dt.dayofweek)["abs_error"].mean()
   print("\nMAE by Day of Week:")
   print(daily_mae)

This temporal analysis often reveals that models perform worse during specific seasons, times of day, or days of week—insights that can guide feature engineering or model improvements.

Visualizing Performance
-----------------------

Visual analysis helps identify systematic errors and edge cases. Here are common visualizations for backtest results:

.. code-block:: python

   import matplotlib.pyplot as plt
   
   # Time series plot: predictions vs actuals
   fig, ax = plt.subplots(figsize=(12, 6))
   ax.plot(df["timestamp"], df["actual"], label="Actual", alpha=0.7)
   ax.plot(df["timestamp"], df["predicted"], label="Predicted", alpha=0.7)
   ax.set_xlabel("Time")
   ax.set_ylabel("Load (MW)")
   ax.legend()
   ax.set_title("Backtest: Predictions vs Actuals")
   plt.tight_layout()
   plt.show()
   
   # Scatter plot: predicted vs actual
   fig, ax = plt.subplots(figsize=(8, 8))
   ax.scatter(df["actual"], df["predicted"], alpha=0.3)
   ax.plot([df["actual"].min(), df["actual"].max()], 
           [df["actual"].min(), df["actual"].max()], 
           'r--', label="Perfect prediction")
   ax.set_xlabel("Actual Load (MW)")
   ax.set_ylabel("Predicted Load (MW)")
   ax.legend()
   ax.set_title("Predicted vs Actual Load")
   plt.tight_layout()
   plt.show()
   
   # Residual plot: errors over time
   fig, ax = plt.subplots(figsize=(12, 4))
   ax.scatter(df["timestamp"], df["error"], alpha=0.3)
   ax.axhline(y=0, color='r', linestyle='--')
   ax.set_xlabel("Time")
   ax.set_ylabel("Error (Actual - Predicted)")
   ax.set_title("Prediction Errors Over Time")
   plt.tight_layout()
   plt.show()

Look for patterns in the residual plot—systematic over- or under-prediction at certain times suggests missing features or model limitations.

Choosing the Best Model
------------------------

With backtest results and metrics in hand, select the model that best fits your operational needs. Consider:

- **Accuracy**: Which model has the lowest MAE or RMSE overall?
- **Peak detection**: Which model best identifies critical high-load periods?
- **Stability**: Which model has consistent performance across seasons?
- **Uncertainty quality**: For probabilistic forecasts, which has the best calibration?

The "best" model depends on your use case. A distribution system operator focused on preventing overloads might prioritize peak detection recall over overall MAE, while a market participant might optimize for accuracy across all hours.

Next Steps
----------

Now that you can backtest and compare models, you might want to:

- Explore :doc:`advanced_customization` to fine-tune model behavior
- Learn about feature engineering to improve model performance
- Set up automated backtesting to continuously monitor model quality

Backtesting is essential for building confidence in your forecasting models before deploying them to production. Regular backtesting helps you catch performance degradation and validate improvements.