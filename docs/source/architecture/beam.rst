BEAM Package
============

The ``openstef_beam`` package provides a complete framework for testing energy forecasting models under realistic operational conditions. BEAM stands for Backtesting, Evaluation, Analysis, and Metrics—the four pillars of rigorous model validation.

Unlike simple train-test splits that can mislead, BEAM simulates real-world scenarios where models are retrained periodically and predictions are made with only historical data available. This prevents data leakage and ensures evaluation results match production performance.

BEAM orchestrates a complete workflow from backtesting through analysis, depending on both the ``openstef_core`` package (for data structures like ``VersionedTimeSeriesDataset``) and the ``openstef_models`` package (for forecasting model implementations). See :doc:`core` and :doc:`models` for details on those components.

The Four Components
-------------------

BEAM organizes model validation into four sequential stages:

**Backtesting** simulates operational forecasting by replaying historical data chronologically. Models are retrained at configured intervals and generate predictions using only information available at that point in time. This creates realistic test scenarios that mirror production deployment.

**Evaluation** transforms raw predictions into structured performance reports. It calculates metrics across different time windows, lead times, and data subsets (like weekends or peak hours), organizing results for systematic analysis.

**Analysis** generates visualizations and comparative reports from evaluation metrics. It creates plots, tables, and statistical summaries that help interpret model performance and identify patterns.

**Benchmarking** coordinates the entire workflow across multiple models and energy targets. It handles parallel execution, manages storage of results, and provides a consistent framework for comparing different forecasting approaches.

.. note:: [DIAGRAM: BEAM workflow showing: VersionedTimeSeriesDataset → Backtesting (with periodic retraining) → Predictions → Evaluation (metrics calculation) → Analysis (visualizations) → Benchmarking (comparison across models/targets). Show dependencies on openstef_core for data structures and openstef_models for forecasters.]

Backtesting: Realistic Simulation
----------------------------------

The backtesting module creates realistic test scenarios by treating historical data as if it were arriving in real-time. This prevents the data leakage that occurs when models have access to future information during validation.

Core concepts:

- **Events**: Discrete points in time when training or prediction occurs
- **Versioned data**: Each prediction uses only data available at that timestamp
- **Periodic retraining**: Models are retrained at configured intervals, just like production
- **Chronological processing**: Events are processed in time order to maintain causality

Basic backtesting workflow:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import timedelta
   
   # Configure backtesting parameters
   config = BacktestConfig(
       horizon=timedelta(hours=24),  # Forecast 24 hours ahead
       window_step=timedelta(days=1),  # Generate predictions daily
       retrain_interval=timedelta(days=7)  # Retrain weekly
   )
   
   # Create pipeline with your forecaster
   pipeline = BacktestPipeline(
       config=config,
       forecaster=your_forecaster_instance
   )
   
   # Run backtest with versioned data
   predictions = pipeline.run(
       ground_truth=versioned_target_data,
       predictors=versioned_feature_data,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31)
   )

The ``BacktestPipeline.run()`` method returns a ``VersionedTimeSeriesDataset`` containing all predictions with their associated timestamps and version information. This ensures you can trace exactly what data was available when each prediction was made.

Evaluation: Structured Performance Reports
-------------------------------------------

After backtesting generates predictions, the evaluation module calculates performance metrics and organizes them into structured reports. It handles time windows, lead time analysis, and data filtering to provide comprehensive performance insights.

Key capabilities:

- **Time windows**: Evaluate performance across different periods (days, weeks, seasons)
- **Lead time analysis**: Track how accuracy changes from 1-hour to 48-hour forecasts
- **Data filtering**: Focus on specific conditions like weekends, peak hours, or weather events
- **Multiple metrics**: Apply different metrics to different aspects of forecast quality
- **Subset reporting**: Organize results by data characteristics for targeted analysis

Example evaluation setup:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig, Window
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   from datetime import timedelta
   
   # Configure evaluation windows and metrics
   config = EvaluationConfig(
       windows=[
           Window(lag=timedelta(0), size=timedelta(days=7)),  # Last week
           Window(lag=timedelta(days=7), size=timedelta(days=30))  # Previous month
       ],
       lead_times=[
           timedelta(hours=1),
           timedelta(hours=6),
           timedelta(hours=24)
       ]
   )
   
   # Create evaluation pipeline with metric providers
   pipeline = EvaluationPipeline(
       config=config,
       quantiles=[0.1, 0.5, 0.9],  # For probabilistic forecasts
       metric_providers=[
           RMAEProvider(),  # Relative Mean Absolute Error
           RCRPSProvider()  # Relative Continuous Ranked Probability Score
       ]
   )
   
   # Generate evaluation report
   report = pipeline.evaluate(
       predictions=backtest_predictions,
       ground_truth=actual_values,
       metadata=target_metadata
   )

The ``EvaluationReport`` contains ``SubsetMetric`` objects for each combination of time window, lead time, and data filter. This structured format makes it easy to identify performance patterns and compare results across different conditions.

Analysis: Visualization and Interpretation
-------------------------------------------

The analysis module transforms evaluation metrics into visualizations and reports that help interpret model performance. It provides flexible visualization classes that can be customized for different use cases.

Visualization types include:

- **Summary tables**: Aggregate metrics across models and targets
- **Time series plots**: Show prediction accuracy over time
- **Lead time curves**: Visualize how performance degrades with forecast horizon
- **Distribution plots**: Compare forecast distributions against actuals
- **Error analysis**: Identify systematic biases and patterns

Example analysis configuration:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   
   # Configure analysis with custom visualizations
   config = AnalysisConfig(
       visualizations=[
           SummaryTableVisualization(
               metrics=["rmae", "rcrps"],
               aggregation="mean"
           )
       ]
   )

Visualizations implement a consistent interface with methods for different grouping strategies: by target, by run, by group, or combinations thereof. This flexibility allows you to create the exact views needed for your analysis.

Benchmarking: Complete Workflow Orchestration
----------------------------------------------

The benchmarking module coordinates the entire BEAM workflow across multiple models and energy targets. It handles parallel execution, manages result storage, and provides a consistent framework for comparing forecasting approaches.

Key features:

- **Parallel execution**: Process multiple targets efficiently
- **Storage backends**: Pluggable storage for local filesystem, cloud, or in-memory
- **Callback system**: Monitor progress and customize processing
- **Error handling**: Automatic recovery and consistent error reporting
- **Result management**: Persistent storage for future analysis and comparison

Complete benchmark example:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from openstef_beam.backtesting import BacktestConfig
   from openstef_beam.evaluation import EvaluationConfig
   from openstef_beam.analysis import AnalysisConfig
   from pathlib import Path
   from datetime import timedelta
   
   # Configure storage
   storage = LocalBenchmarkStorage(base_path=Path("./results"))
   
   # Configure each stage
   backtest_config = BacktestConfig(
       horizon=timedelta(hours=24),
       window_step=timedelta(days=1),
       retrain_interval=timedelta(days=7)
   )
   
   evaluation_config = EvaluationConfig(
       windows=[Window(lag=timedelta(0), size=timedelta(days=30))],
       lead_times=[timedelta(hours=h) for h in [1, 6, 12, 24]]
   )
   
   analysis_config = AnalysisConfig(
       visualizations=[SummaryTableVisualization()]
   )
   
   # Create and run benchmark
   benchmark = BenchmarkPipeline(
       storage=storage,
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config
   )
   
   # Execute across multiple targets
   results = benchmark.run(
       targets=target_list,
       forecaster_factory=your_forecaster_factory,
       data_provider=your_data_provider
   )

The ``BenchmarkPipeline`` handles all the complexity of coordinating backtesting, evaluation, and analysis across multiple targets. It manages data dependencies, ensures consistent processing, and stores results for future comparison.

Integration with Core and Models
---------------------------------

BEAM depends on both ``openstef_core`` and ``openstef_models`` packages:

**From openstef_core**:

- ``VersionedTimeSeriesDataset``: Ensures predictions use only historically available data
- ``TimeSeriesDataset``: Base data structure for time series operations
- Data validation and transformation utilities

**From openstef_models**:

- Forecaster implementations (XGBoost, LightGBM, etc.)
- Transform pipelines for feature engineering
- Model persistence and serialization

This separation of concerns keeps BEAM focused on evaluation workflows while leveraging robust implementations from the core and models packages. See :doc:`core` for data structure details and :doc:`models` for forecaster implementations.

When to Use BEAM
----------------

Use BEAM when you need to:

- **Validate models realistically**: Ensure evaluation matches production performance
- **Compare approaches**: Benchmark different models or configurations systematically
- **Analyze performance**: Understand how accuracy varies across time, lead times, and conditions
- **Prevent data leakage**: Guarantee models use only historically available information
- **Generate reports**: Create consistent, reproducible performance documentation

BEAM's versioned data approach and complete workflow orchestration make it the reliable choice for energy forecasting model validation that translates to production success.