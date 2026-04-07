Backtesting Models
==================

Backtesting evaluates how forecasting models would have performed in real operational conditions by simulating their behavior on historical data. This tutorial shows you how to compare different models, understand their strengths and weaknesses, and choose the best approach for your use case.

Unlike simple train-test splits, backtesting simulates the operational environment where forecasts are generated at regular intervals with limited historical data availability. This prevents data leakage and provides realistic performance estimates.

What You'll Learn
-----------------

This page covers:

- Setting up backtesting pipelines with realistic operational constraints
- Running backtests on historical data
- Evaluating model performance with standard metrics
- Comparing multiple models to find the best performer
- Visualizing results to understand model behavior

For your first forecast without backtesting, see :doc:`first_forecast`. For advanced model customization, see :doc:`advanced_customization`.

Understanding Backtesting
-------------------------

Backtesting simulates how a model would perform in production by:

1. **Generating predictions at regular intervals** - Just like in production, forecasts are created every few hours
2. **Retraining periodically** - Models are retrained on a schedule (e.g., weekly) using only data available at that time
3. **Respecting data availability** - Only historical data that would have been available at prediction time is used
4. **Collecting all predictions** - Results are aggregated for comprehensive evaluation

This approach reveals how models handle concept drift, seasonal patterns, and data quality issues that emerge over time.

Setting Up a Backtest
---------------------

The ``BacktestPipeline`` orchestrates the entire backtesting process. You configure it with operational parameters that match your production environment.

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.forecasting import XGBForecaster, XGBForecasterConfig
   
   # Configure the forecaster
   forecaster_config = XGBForecasterConfig(
       predict_sample_interval=timedelta(minutes=15),
       max_horizon=timedelta(hours=47),
   )
   forecaster = XGBForecaster(config=forecaster_config)
   
   # Configure backtesting parameters
   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),  # Must match forecaster
       predict_interval=timedelta(hours=6),  # Generate forecasts every 6 hours
       train_interval=timedelta(days=7),  # Retrain weekly
       align_time=time(0, 0),  # Align predictions to midnight
   )
   
   # Create the pipeline
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )

The ``predict_interval`` controls how often forecasts are generated. Setting it to 6 hours means the model creates a new 47-hour forecast every 6 hours, just like in production. The ``train_interval`` determines retraining frequency - weekly retraining balances model freshness with computational cost.

.. warning::
   The ``prediction_sample_interval`` in ``BacktestConfig`` must match the ``predict_sample_interval`` in your forecaster configuration. Mismatched intervals will raise a ``ValueError``.

Running the Backtest
--------------------

Once configured, run the backtest on your historical data:

.. code-block:: python

   from datetime import datetime
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Prepare your data
   ground_truth = VersionedTimeSeriesDataset(
       data=historical_load_data,  # DataFrame with DatetimeIndex and target column
       available_at=datetime(2024, 1, 1),  # When this data became available
   )
   
   predictors = VersionedTimeSeriesDataset(
       data=historical_features,  # DataFrame with DatetimeIndex and feature columns
       available_at=datetime(2024, 1, 1),
   )
   
   # Run the backtest
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True,
   )

The pipeline returns a ``VersionedTimeSeriesDataset`` containing all predictions with their timestamps and availability information. This dataset includes both the predicted values and the actual ground truth, enabling comprehensive evaluation.

The ``show_progress`` parameter displays a progress bar during execution, useful for long backtests that may take several minutes.

Evaluating Performance
----------------------

OpenSTEF provides metrics specifically designed for energy forecasting. These metrics help you understand both overall accuracy and performance on critical events like peak loads.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import (
       MAE,
       RMSE,
       SkillScore,
       PeakLoadMetric,
   )
   
   # Configure evaluation
   eval_config = EvaluationConfig(
       available_ats=[],  # Evaluate all predictions
       lead_times=[timedelta(hours=1), timedelta(hours=24), timedelta(hours=47)],
   )
   
   # Set up metrics
   evaluation_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=None,  # For deterministic forecasts
       window_metric_providers=[],
       global_metric_providers=[
           MAE(),
           RMSE(),
           SkillScore(baseline="persistence"),
           PeakLoadMetric(threshold_quantile=0.95),
       ],
   )
   
   # Run evaluation
   results = evaluation_pipeline.run_for_subset(
       filtering=timedelta(hours=24),  # Evaluate 24-hour ahead forecasts
       predictions=predictions,
   )
   
   # Access metrics
   global_metrics = results.get_global_metric()
   print(f"MAE: {global_metrics.metrics['mae']:.2f}")
   print(f"RMSE: {global_metrics.metrics['rmse']:.2f}")
   print(f"Skill Score: {global_metrics.metrics['skill_score']:.3f}")

Key metrics for energy forecasting:

- **MAE (Mean Absolute Error)** - Average absolute difference between predictions and actual values. Easy to interpret in the same units as your target variable.
- **RMSE (Root Mean Squared Error)** - Penalizes large errors more heavily than MAE. Useful when large errors are particularly costly.
- **Skill Score** - Measures improvement over a baseline (e.g., persistence or climatology). A score of 0.2 means your model is 20% better than the baseline.
- **Peak Load Metric** - Evaluates performance specifically on high-load events, critical for grid operators managing congestion.

The ``lead_times`` parameter lets you evaluate performance at specific forecast horizons. Short-term forecasts (1-6 hours) typically have higher accuracy than long-term forecasts (24-47 hours).

Comparing Multiple Models
--------------------------

To find the best model, run backtests with different configurations and compare their metrics:

.. code-block:: python

   from openstef_beam.forecasting import LinearForecaster, LinearForecasterConfig
   
   # Define models to compare
   models = {
       "xgb": XGBForecaster(config=XGBForecasterConfig(
           predict_sample_interval=timedelta(minutes=15),
           max_horizon=timedelta(hours=47),
       )),
       "linear": LinearForecaster(config=LinearForecasterConfig(
           predict_sample_interval=timedelta(minutes=15),
           max_horizon=timedelta(hours=47),
       )),
   }
   
   # Run backtests for each model
   results = {}
   for name, forecaster in models.items():
       pipeline = BacktestPipeline(
           config=backtest_config,
           forecaster=forecaster,
       )
       
       predictions = pipeline.run(
           ground_truth=ground_truth,
           predictors=predictors,
           start=datetime(2023, 1, 1),
           end=datetime(2023, 12, 31),
           show_progress=True,
       )
       
       # Evaluate
       eval_results = evaluation_pipeline.run_for_subset(
           filtering=timedelta(hours=24),
           predictions=predictions,
       )
       
       results[name] = eval_results.get_global_metric()
   
   # Compare results
   for name, metrics in results.items():
       print(f"\n{name.upper()} Model:")
       print(f"  MAE: {metrics.metrics['mae']:.2f}")
       print(f"  RMSE: {metrics.metrics['rmse']:.2f}")
       print(f"  Skill Score: {metrics.metrics['skill_score']:.3f}")

This comparison reveals which model performs best for your specific use case. XGBoost often excels at capturing complex patterns, while linear models provide faster training and more interpretable results.

Visualizing Results
-------------------

Visual analysis helps identify systematic errors and understand model behavior across different conditions:

.. code-block:: python

   import matplotlib.pyplot as plt
   import pandas as pd
   
   # Extract predictions and actuals
   pred_df = predictions.data
   
   # Plot time series comparison
   fig, axes = plt.subplots(2, 1, figsize=(12, 8))
   
   # Full time series
   axes[0].plot(pred_df.index, pred_df['actual'], label='Actual', alpha=0.7)
   axes[0].plot(pred_df.index, pred_df['predicted'], label='Predicted', alpha=0.7)
   axes[0].set_ylabel('Load (MW)')
   axes[0].set_title('Forecast vs Actual')
   axes[0].legend()
   axes[0].grid(True, alpha=0.3)
   
   # Residuals
   residuals = pred_df['predicted'] - pred_df['actual']
   axes[1].scatter(pred_df['actual'], residuals, alpha=0.3)
   axes[1].axhline(y=0, color='r', linestyle='--')
   axes[1].set_xlabel('Actual Load (MW)')
   axes[1].set_ylabel('Residual (MW)')
   axes[1].set_title('Residual Plot')
   axes[1].grid(True, alpha=0.3)
   
   plt.tight_layout()
   plt.show()

Residual plots reveal systematic biases. If residuals increase with load magnitude, the model may struggle with high-demand periods. If residuals show temporal patterns, the model may miss seasonal or weekly cycles.

.. note::
   [DIAGRAM: Example residual plot showing well-calibrated model (random scatter around zero) vs biased model (systematic pattern)]

Best Practices
--------------

**Choose realistic intervals** - Match your ``predict_interval`` and ``train_interval`` to production schedules. Testing with 6-hour prediction intervals and weekly retraining simulates realistic operational constraints.

**Use sufficient history** - Ensure your backtest period covers multiple seasonal cycles (at least one year). This reveals how models handle seasonal patterns and concept drift.

**Evaluate multiple horizons** - Performance often degrades at longer horizons. Evaluate at 1-hour, 6-hour, 24-hour, and 47-hour horizons to understand the full accuracy profile.

**Consider computational cost** - Backtesting with frequent retraining can be slow. Start with longer intervals (e.g., weekly retraining) and refine based on results.

**Test on recent data** - Models trained on old data may not perform well on recent patterns. Use the most recent year or two for backtesting when possible.

Next Steps
----------

Now that you understand backtesting, you can:

- Explore :doc:`advanced_customization` to create custom models and metrics
- Review the evaluation metrics API documentation for detailed metric descriptions
- Experiment with different model configurations to optimize performance

For questions about backtesting workflows or interpreting results, consult the OpenSTEF community forums or GitHub discussions.