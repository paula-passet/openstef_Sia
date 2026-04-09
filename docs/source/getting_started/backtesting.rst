Backtesting Models
==================

Backtesting evaluates how well your forecasting models would have performed on historical data. Unlike simple train-test splits, OpenSTEF's backtesting pipeline simulates realistic operational conditions: forecasts are generated at regular intervals with limited historical data, and models are periodically retrained—just as they would be in production.

This tutorial shows you how to backtest models, compare their performance using evaluation metrics, and visualize results to identify the best approach for your use case.

Why Backtest?
-------------

Backtesting answers critical questions before deploying a model:

- How accurate are predictions across different time periods?
- Does performance degrade over time, indicating the need for retraining?
- Which model configuration works best for your specific data?
- How well do uncertainty estimates capture actual forecast errors?

The key advantage of OpenSTEF's backtesting is temporal consistency: it prevents data leakage by respecting the constraints of real-time forecasting, where future data is never available during prediction.

Basic Backtesting Workflow
---------------------------

The backtesting process involves three main steps: configure the backtest parameters, run the simulation with your forecaster, and evaluate the results.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.forecasting import Forecaster, ForecasterConfig
   from openstef_core.datasets import TimeSeriesDataset
   from datetime import datetime, timedelta
   import pandas as pd

   # Load your historical data
   ground_truth = TimeSeriesDataset(...)  # Target values
   predictors = TimeSeriesDataset(...)    # Feature data

   # Configure the backtesting simulation
   backtest_config = BacktestConfig(
       prediction_interval=timedelta(hours=1),      # Generate forecasts every hour
       prediction_sample_interval=timedelta(minutes=15),  # 15-min resolution
       training_interval=timedelta(days=7),         # Retrain weekly
       training_horizon=timedelta(days=90),         # Use 90 days of history
   )

   # Set up your forecaster
   forecaster_config = ForecasterConfig(
       predict_sample_interval=timedelta(minutes=15),
       predict_horizon=timedelta(hours=47),
       target_column="load",
   )
   forecaster = Forecaster(config=forecaster_config)

   # Run the backtest
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )
   
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
       show_progress=True,
   )

The ``BacktestPipeline`` orchestrates the entire simulation. It generates forecasts at regular intervals (``prediction_interval``), retrains the model periodically (``training_interval``), and ensures that only data available up to each forecast time is used for training.

Understanding Backtest Configuration
-------------------------------------

The ``BacktestConfig`` controls how the simulation runs:

- **prediction_interval**: How often to generate new forecasts (e.g., every hour)
- **prediction_sample_interval**: Time resolution of predictions (must match forecaster config)
- **training_interval**: How often to retrain the model (e.g., weekly)
- **training_horizon**: How much historical data to use for each training run

Choosing appropriate values depends on your operational requirements. Shorter prediction intervals produce more forecasts for evaluation but increase computation time. Longer training horizons provide more data for learning but may include outdated patterns.

.. note::

   The ``prediction_sample_interval`` in ``BacktestConfig`` must match the ``predict_sample_interval`` in your forecaster's configuration, or the pipeline will raise a ``ValueError``.

Evaluating Backtest Results
----------------------------

After running a backtest, you need to quantify model performance. OpenSTEF provides a comprehensive evaluation framework with metrics tailored for energy forecasting.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import MAE, RMSE, MAPE
   from datetime import timedelta

   # Configure evaluation
   eval_config = EvaluationConfig(
       available_ats=[],  # Evaluate all predictions
       lead_times=[timedelta(hours=1), timedelta(hours=24)],  # Check 1h and 24h ahead
   )

   # Set up evaluation pipeline with desired metrics
   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[10, 50, 90],  # For probabilistic forecasts
       global_metric_providers=[MAE(), RMSE(), MAPE()],
   )

   # Run evaluation
   evaluation_result = eval_pipeline.run_for_subset(
       filtering=timedelta(hours=24),  # Focus on 24-hour ahead forecasts
       predictions=predictions,
   )

   # Access metrics
   global_metrics = evaluation_result.get_global_metric()
   print(f"MAE: {global_metrics.metrics['MAE']:.2f}")
   print(f"RMSE: {global_metrics.metrics['RMSE']:.2f}")

Common Evaluation Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF includes several metrics designed for energy forecasting:

- **MAE (Mean Absolute Error)**: Average absolute difference between predictions and actual values. Easy to interpret in the same units as your target variable.
- **RMSE (Root Mean Squared Error)**: Penalizes large errors more heavily than MAE. Useful when large deviations are particularly costly.
- **rMAE (Relative MAE)**: MAE normalized by the data range, making it easier to compare performance across different scales.
- **MAPE (Mean Absolute Percentage Error)**: Percentage-based error metric. Be cautious with low values where division can cause instability.

For peak detection scenarios (e.g., identifying grid congestion), confusion matrix metrics like precision and recall are also available.

Comparing Multiple Models
--------------------------

Backtesting truly shines when comparing different model configurations or algorithms. Run separate backtests for each model, then evaluate them side by side.

.. code-block:: python

   # Backtest first model
   forecaster_xgb = Forecaster(config=config_xgb)
   pipeline_xgb = BacktestPipeline(config=backtest_config, forecaster=forecaster_xgb)
   predictions_xgb = pipeline_xgb.run(ground_truth, predictors, start, end)

   # Backtest second model
   forecaster_lgb = Forecaster(config=config_lgb)
   pipeline_lgb = BacktestPipeline(config=backtest_config, forecaster=forecaster_lgb)
   predictions_lgb = pipeline_lgb.run(ground_truth, predictors, start, end)

   # Evaluate both
   eval_xgb = eval_pipeline.run_for_subset(timedelta(hours=24), predictions_xgb)
   eval_lgb = eval_pipeline.run_for_subset(timedelta(hours=24), predictions_lgb)

   # Compare
   metrics_xgb = eval_xgb.get_global_metric().metrics
   metrics_lgb = eval_lgb.get_global_metric().metrics
   
   print("XGBoost MAE:", metrics_xgb['MAE'])
   print("LightGBM MAE:", metrics_lgb['MAE'])

This approach lets you objectively determine which model performs best on your specific data and forecasting task.

Visualizing Backtest Performance
---------------------------------

OpenSTEF provides built-in visualization tools to help you understand model behavior beyond summary statistics.

Time Series Comparison
^^^^^^^^^^^^^^^^^^^^^^^

The ``ForecastTimeSeriesPlotter`` displays predictions alongside actual measurements, making it easy to spot systematic biases or periods of poor performance.

.. code-block:: python

   from openstef_beam.analysis.visualizations import ForecastTimeSeriesPlotter

   # Create plotter
   plotter = ForecastTimeSeriesPlotter()
   
   # Add actual measurements
   plotter.add_measurements(ground_truth.data["load"])
   
   # Add model forecasts
   plotter.add_model("XGBoost", forecast=predictions_xgb.data["forecast"])
   plotter.add_model("LightGBM", forecast=predictions_lgb.data["forecast"])
   
   # Generate interactive plot
   fig = plotter.plot(title="Model Comparison: XGBoost vs LightGBM")
   fig.show()

The resulting plot includes interactive hover information, zoom capabilities, and color-coded models for easy visual comparison. Shaded confidence bands (when using probabilistic forecasts) show forecast uncertainty.

Performance Over Time
^^^^^^^^^^^^^^^^^^^^^

To understand how model accuracy evolves, use ``WindowedMetricVisualization`` to plot metrics across sliding time windows.

.. code-block:: python

   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.evaluation import Window

   # Configure windowed metric visualization
   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_over_time",
               metric="MAE",
               window=Window(size=timedelta(days=7)),
           ),
       ]
   )

This reveals performance trends, seasonal patterns, and helps identify optimal retraining intervals. If you see degradation over time, you may need more frequent retraining or additional features.

Best Practices
--------------

**Choose realistic backtest periods**: Use at least several months of data to capture seasonal variations and different operating conditions.

**Match operational constraints**: Configure prediction and training intervals to mirror your actual deployment scenario. Backtesting with daily retraining won't reflect reality if you plan to retrain weekly in production.

**Evaluate multiple horizons**: Short-term forecasts (1-6 hours) often behave differently than longer horizons (24-48 hours). Use the ``lead_times`` parameter in ``EvaluationConfig`` to assess performance across the forecast horizon.

**Consider computational cost**: Backtesting can be expensive, especially with short prediction intervals and long evaluation periods. Use the ``show_progress`` parameter to monitor execution.

**Validate temporal consistency**: The pipeline prevents data leakage by design, but verify that your custom forecaster implementations respect temporal boundaries when accessing training data.

Next Steps
----------

Now that you understand backtesting, you might want to:

- Explore :doc:`advanced_customization` to implement custom forecasters or evaluation metrics
- Review the evaluation metrics API documentation for specialized metrics
- Learn about feature engineering techniques to improve model performance

For questions about specific backtesting scenarios or troubleshooting, consult the API reference for ``BacktestPipeline`` and ``BacktestConfig``.