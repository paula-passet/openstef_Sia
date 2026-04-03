Backtesting Your Forecasts
===========================

Backtesting simulates how your forecasting model would have performed in real operations using historical data. This tutorial shows you how to run backtests, evaluate model performance, and compare different models to find the best approach for your use case.

Unlike simple train-test splits, OpenSTEF's backtesting pipeline respects temporal constraints: it generates forecasts at regular intervals with limited historical data availability, preventing data leakage and mimicking operational conditions.

What You'll Learn
-----------------

This page covers:

- Setting up and running a backtest simulation
- Understanding evaluation metrics for energy forecasting
- Comparing multiple models systematically
- Visualizing performance differences

For your first forecast, see :doc:`first_forecast`. For advanced customization of the backtesting process, see :doc:`advanced_customization`.

Running a Basic Backtest
-------------------------

The ``BacktestPipeline`` orchestrates the backtesting process. You provide historical data, a forecaster, and configuration parameters that define when predictions are made and how often the model retrains.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.forecasting import Forecaster, ForecasterConfig
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import datetime, timedelta
   
   # Configure the backtesting simulation
   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(hours=1),  # Make predictions every hour
       prediction_offset=timedelta(minutes=15),        # 15 minutes before the hour
       training_sample_interval=timedelta(days=7),     # Retrain weekly
       training_offset=timedelta(days=0),
   )
   
   # Set up your forecaster
   forecaster_config = ForecasterConfig(
       predict_sample_interval=timedelta(hours=1),
       predict_horizon=timedelta(hours=48),
   )
   forecaster = Forecaster(config=forecaster_config)
   
   # Create the backtest pipeline
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )
   
   # Run the backtest
   predictions = pipeline.run(
       ground_truth=historical_load_data,
       predictors=historical_feature_data,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True,
   )

The pipeline returns a ``VersionedTimeSeriesDataset`` containing all predictions with timestamps and availability information. Each prediction is made using only data that would have been available at that point in time.

Understanding Evaluation Metrics
---------------------------------

OpenSTEF provides specialized metrics for energy forecasting. These metrics account for the operational challenges of energy systems, such as peak detection and scale differences between high and low load periods.

Deterministic Metrics
^^^^^^^^^^^^^^^^^^^^^

For point forecasts (single predicted values):

**Relative Mean Absolute Error (rMAE)**
   Measures average prediction error normalized by the typical range of values. This makes errors comparable across different scales.

   .. code-block:: python

      from openstef_beam.metrics import rmae
      import numpy as np
      
      y_true = np.array([100, 150, 200, 175, 125])
      y_pred = np.array([105, 145, 210, 170, 130])
      
      error = rmae(y_true, y_pred)
      print(f"rMAE: {error:.3f}")  # Lower is better

**Mean Absolute Error (MAE)**
   Simple average of absolute errors. Easy to interpret in the original units.

   .. code-block:: python

      from openstef_beam.metrics import mae
      
      error = mae(y_true, y_pred)
      print(f"MAE: {error:.2f} MW")  # In original units

**R² Score**
   Measures how much variance your model explains. Values range from negative infinity to 1.0, where 1.0 is perfect.

   .. code-block:: python

      from openstef_beam.metrics import r2
      
      score = r2(y_true, y_pred)
      print(f"R²: {score:.3f}")  # Higher is better

Probabilistic Metrics
^^^^^^^^^^^^^^^^^^^^^

For quantile forecasts (prediction intervals):

**Relative Continuous Ranked Probability Score (rCRPS)**
   The primary metric for probabilistic forecasts. Evaluates both accuracy and calibration of prediction intervals.

   .. code-block:: python

      from openstef_beam.metrics import rcrps
      
      # Predictions at multiple quantiles
      quantiles = np.array([0.1, 0.25, 0.5, 0.75, 0.9])
      y_pred_quantiles = np.array([
          [80, 90, 100, 110, 120],    # Predictions for first timestep
          [120, 135, 150, 165, 180],  # Second timestep
          # ... more timesteps
      ])
      
      score = rcrps(y_true, y_pred_quantiles, quantiles)
      print(f"rCRPS: {score:.3f}")  # Lower is better

**Peak Detection Metrics**
   For identifying congestion events, use confusion matrix-based metrics:

   .. code-block:: python

      from openstef_beam.metrics import confusion_matrix, precision_recall
      
      # Define peak threshold (e.g., 80% of capacity)
      threshold = 0.8 * max_capacity
      
      cm = confusion_matrix(y_true, y_pred, threshold=threshold)
      pr = precision_recall(cm)
      
      print(f"Precision: {pr.precision:.2f}")
      print(f"Recall: {pr.recall:.2f}")

Comparing Multiple Models
--------------------------

The ``BenchmarkComparisonPipeline`` enables systematic comparison of different model configurations. This is essential for A/B testing, evaluating improvements, or selecting the best model variant.

Setting Up a Comparison
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.benchmarking.storage import LocalBenchmarkStorage
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       GroupedTargetMetricVisualization,
       SummaryTableVisualization,
       TimeSeriesVisualization,
   )
   from pathlib import Path
   
   # Configure analysis and visualizations
   analysis_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="model_comparison",
               metric="rCRPS"  # Primary metric for comparison
           ),
           SummaryTableVisualization(name="performance_summary"),
           TimeSeriesVisualization(name="prediction_quality"),
       ]
   )
   
   # Set up comparison pipeline
   comparison = BenchmarkComparisonPipeline(
       analysis_config=analysis_config,
       target_provider=your_target_provider,
       storage=your_storage_backend,
   )
   
   # Compare multiple model versions
   run_data = {
       "baseline_v1": LocalBenchmarkStorage("results/baseline"),
       "improved_v2": LocalBenchmarkStorage("results/improved"),
       "experimental_v3": LocalBenchmarkStorage("results/experimental"),
   }
   
   comparison.run(run_data)

Multi-Level Analysis
^^^^^^^^^^^^^^^^^^^^

The comparison pipeline automatically generates analysis at three aggregation levels:

**Global Level**
   Overall performance across all runs and targets. Use this to identify which model performs best on average.

**Group Level**
   Performance within target groups (e.g., residential vs. industrial loads). Reveals whether improvements are consistent across different load types.

**Target Level**
   Individual target performance across runs. Identifies specific cases where a model excels or struggles.

This hierarchical approach helps you understand whether improvements are universal or specific to certain conditions.

Interpreting Results
^^^^^^^^^^^^^^^^^^^^^

When comparing models, look for:

1. **Consistent improvement**: Does the new model perform better across most targets and groups?
2. **Trade-offs**: Does better average performance come at the cost of worse worst-case performance?
3. **Operational relevance**: Focus on metrics that matter for your use case (e.g., peak detection for congestion management).

.. code-block:: python

   # Example: Selecting the best model based on rCRPS
   def select_best_model(comparison_results):
       """Select model with lowest average rCRPS."""
       avg_scores = {}
       for run_name, metrics in comparison_results.items():
           avg_scores[run_name] = metrics["rCRPS"].mean()
       
       best_model = min(avg_scores, key=avg_scores.get)
       print(f"Best model: {best_model} (rCRPS: {avg_scores[best_model]:.3f})")
       return best_model

Visualizing Performance
-----------------------

Visualization helps identify patterns and communicate results. OpenSTEF provides several built-in visualization types:

**Summary Tables**
   Tabular comparison of key metrics across models. Quick overview of relative performance.

**Time Series Plots**
   Show predictions vs. actuals over time. Reveals systematic biases or seasonal patterns in errors.

**Grouped Metric Visualizations**
   Compare performance across target groups. Identifies which types of loads are easier or harder to forecast.

The visualization providers integrate with the comparison pipeline and automatically generate outputs in your specified format (HTML, PNG, etc.).

Best Practices
--------------

**Choose appropriate time periods**
   Backtest over periods that represent operational conditions: include seasonal variations, different weather patterns, and edge cases.

**Respect temporal constraints**
   Always use the ``BacktestPipeline`` rather than simple train-test splits. This ensures your evaluation reflects real operational performance.

**Focus on relevant metrics**
   If peak detection matters for your application, prioritize precision/recall over MAE. If uncertainty quantification is critical, focus on rCRPS and calibration metrics.

**Compare fairly**
   When comparing models, use identical backtest configurations and evaluation periods. Different data availability can significantly impact results.

**Validate on multiple targets**
   A model that works well for one load profile may fail on others. Always evaluate across your full portfolio of targets.

Next Steps
----------

- Learn about :doc:`advanced_customization` to customize the backtesting pipeline with callbacks and custom metrics
- Explore the full API documentation for ``openstef_beam.backtesting`` and ``openstef_beam.metrics``
- See :doc:`first_forecast` for a complete end-to-end forecasting workflow