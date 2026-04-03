Backtesting Models
==================

Backtesting evaluates how well your forecasting models would have performed in real operational conditions using historical data. Unlike simple train-test splits, OpenSTEF's backtesting pipeline simulates the actual constraints of production forecasting: limited data availability at prediction time, periodic model retraining, and realistic prediction schedules.

This tutorial shows you how to backtest models, compare their performance using evaluation metrics, and visualize results to identify the best approach for your use case.

Why Backtest?
-------------

Backtesting answers critical questions about model performance:

- How accurate are predictions across different time periods?
- Does model performance degrade over time, requiring retraining?
- Which model configuration works best for your specific data?
- How do different models compare on the same historical data?

The key difference from simple validation is temporal realism. The backtesting pipeline ensures your model only sees data that would have been available at each prediction time, preventing data leakage that would artificially inflate performance metrics.

Setting Up a Backtest
---------------------

Backtesting requires three components: a configured forecaster, historical data, and a backtest configuration that defines the simulation parameters.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.forecasting import Forecaster, ForecasterConfig
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import datetime, timedelta

   # Configure your forecaster
   forecaster_config = ForecasterConfig(
       predict_sample_interval=timedelta(hours=1),
       training_horizons=[timedelta(hours=h) for h in [1, 6, 12, 24, 48]],
   )
   forecaster = Forecaster(config=forecaster_config)

   # Configure the backtest simulation
   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(hours=1),
       training_interval=timedelta(days=7),  # Retrain weekly
       training_history=timedelta(days=90),  # Use 90 days of history
   )

   # Create the pipeline
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )

The ``BacktestConfig`` controls simulation behavior:

- ``prediction_sample_interval``: How often forecasts are generated (must match forecaster configuration)
- ``training_interval``: How frequently the model is retrained
- ``training_history``: How much historical data is used for each training run

Running a Backtest
------------------

Execute the backtest by providing historical data and the time period to simulate:

.. code-block:: python

   # Prepare your historical data
   ground_truth = VersionedTimeSeriesDataset(...)  # Target values
   predictors = VersionedTimeSeriesDataset(...)    # Feature data

   # Run the backtest
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True,
   )

The pipeline returns a ``TimeSeriesDataset`` containing all predictions made during the simulation. Each prediction includes timestamps and availability information, allowing you to analyze when forecasts were generated and what data was available at that time.

The backtest respects operational constraints:

- Models are trained only with data available before each training event
- Predictions use only features available at prediction time
- Training occurs at regular intervals as configured
- The simulation processes events in chronological order

Evaluating Performance
----------------------

After running a backtest, evaluate model performance using metrics that quantify forecast accuracy. OpenSTEF provides both deterministic metrics (MAE, RMSE) and probabilistic metrics (quantile losses, CRPS) for comprehensive evaluation.

.. code-block:: python

   from openstef_beam.evaluation import evaluate_predictions
   from openstef_core.metrics import mae, rmse, quantile_loss

   # Evaluate predictions against ground truth
   results = evaluate_predictions(
       predictions=predictions,
       ground_truth=ground_truth,
       metrics={
           "MAE": mae,
           "RMSE": rmse,
           "rMAE": lambda y_true, y_pred: mae(y_true, y_pred) / y_true.mean(),
       }
   )

   # Access metric values
   print(f"Mean Absolute Error: {results['MAE']:.2f}")
   print(f"Root Mean Squared Error: {results['RMSE']:.2f}")
   print(f"Relative MAE: {results['rMAE']:.2%}")

Common evaluation metrics:

- **MAE** (Mean Absolute Error): Average magnitude of prediction errors
- **RMSE** (Root Mean Squared Error): Penalizes larger errors more heavily
- **rMAE** (Relative MAE): MAE normalized by mean actual value, useful for comparing across different scales
- **rCRPS** (Relative CRPS): Overall probabilistic forecast quality for quantile predictions

Comparing Multiple Models
-------------------------

To identify the best model, run backtests for different configurations and compare their performance. The analysis framework provides tools for systematic comparison across models and targets.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline
   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       GroupedTargetMetricVisualization,
       SummaryTableVisualization,
   )
   from openstef_beam.benchmarking.storage import LocalBenchmarkStorage

   # Configure analysis with visualizations
   analysis_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="model_comparison",
               metric="rCRPS",
           ),
           SummaryTableVisualization(
               name="performance_summary",
           ),
       ]
   )

   # Set up comparison pipeline
   comparison = BenchmarkComparisonPipeline(
       analysis_config=analysis_config,
       target_provider=your_target_provider,
       storage=your_storage,
   )

   # Compare multiple model versions
   run_data = {
       "baseline": LocalBenchmarkStorage("results/baseline"),
       "improved": LocalBenchmarkStorage("results/improved"),
       "experimental": LocalBenchmarkStorage("results/experimental"),
   }

   comparison.compare_runs(run_data)

This generates comparative visualizations showing which model performs best across different metrics and targets.

Visualizing Results
-------------------

Visualization helps identify patterns in model performance that raw metrics might miss. OpenSTEF provides several visualization types for different analysis needs.

**Time Series Performance**

Track how model accuracy evolves over time to identify degradation patterns or seasonal effects:

.. code-block:: python

   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window
   from datetime import timedelta

   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="MAE",
               window=Window(size=timedelta(days=7)),
           ),
       ]
   )

This creates a time series plot showing how MAE changes over rolling 7-day windows, revealing when model performance degrades and retraining might be needed.

**Target Comparison**

Compare performance across different prediction targets to identify which are hardest to forecast:

.. code-block:: python

   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from openstef_core.types import Quantile

   analysis_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="target_comparison",
               metric="rMAE",
               quantile=Quantile(0.5),  # Median forecast
           ),
       ]
   )

Bar charts and box plots show performance distribution across targets, helping prioritize optimization efforts.

**Summary Tables**

Generate comprehensive tables comparing all metrics across models and targets:

.. code-block:: python

   from openstef_beam.analysis.visualizations import SummaryTableVisualization

   analysis_config = AnalysisConfig(
       visualization_providers=[
           SummaryTableVisualization(name="full_comparison"),
       ]
   )

Summary tables provide a complete overview of model performance, making it easy to identify the best configuration at a glance.

Best Practices
--------------

Follow these guidelines for effective backtesting:

**Choose Appropriate Time Periods**

- Use at least several months of data to capture seasonal patterns
- Include periods with unusual conditions (holidays, extreme weather) if relevant
- Ensure the test period represents conditions you'll encounter in production

**Configure Realistic Retraining**

- Match production retraining frequency in your backtest configuration
- Use training history lengths that balance data availability and computational cost
- Test different retraining intervals to find the optimal balance

**Select Meaningful Metrics**

- Use relative metrics (rMAE, rCRPS) when comparing across different scales
- Include both deterministic and probabilistic metrics for quantile forecasts
- Choose metrics that align with your business objectives (e.g., cost of over/under prediction)

**Validate Temporal Consistency**

- Verify that the pipeline prevents data leakage by checking prediction timestamps
- Ensure feature data availability matches what you'll have in production
- Test edge cases like missing data or gaps in historical records

Next Steps
----------

Now that you understand backtesting, explore related topics:

- :doc:`first_forecast` - Learn the basics of creating forecasts before backtesting
- :doc:`advanced_customization` - Customize forecasters and backtesting behavior for specific needs
- See the API documentation for detailed parameter descriptions and advanced options

Backtesting provides the foundation for confident model deployment by proving performance on historical data under realistic conditions.