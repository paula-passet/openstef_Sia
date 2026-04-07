BEAM Package
============

The ``openstef_beam`` package provides a complete framework for validating forecasting models under realistic operational conditions. BEAM stands for **Backtesting, Evaluation, Analysis and Metrics** — the four stages that transform raw predictions into actionable insights about model performance.

Unlike simple train-test splits that can mislead, BEAM simulates real-world deployment by using versioned data to prevent data leakage. Models are retrained periodically and can only access information that would have been available at prediction time, ensuring evaluation results accurately reflect production performance.

BEAM orchestrates a complete workflow that depends on both the core and models packages: it uses ``openstef_core`` for versioned datasets and time series handling, and ``openstef_models`` for the actual forecasting implementations. This makes BEAM the integration layer that brings everything together for comprehensive model validation.

Workflow Overview
-----------------

BEAM follows a four-stage pipeline:

1. **Backtesting**: Simulate operational forecasting by replaying historical data chronologically, retraining models at realistic intervals, and generating predictions with only past information available.

2. **Evaluation**: Organize backtest results into structured reports by computing metrics across different time windows, lead times, and data subsets (weekends, peak hours, seasons).

3. **Analysis**: Transform numerical evaluation results into visualizations and comparative reports that reveal model strengths, weaknesses, and operational characteristics.

4. **Benchmarking**: Compare multiple forecasting approaches across different energy targets, storing results for long-term performance tracking and model selection.

.. note::

   [DIAGRAM: BEAM workflow showing: VersionedTimeSeriesDataset → BacktestPipeline (with periodic retraining) → Predictions → EvaluationPipeline (metrics by window/lead time) → AnalysisConfig (visualizations) → BenchmarkPipeline (multi-target comparison)]

Backtesting: Realistic Simulation
----------------------------------

The backtesting module creates realistic test scenarios by replaying historical data as if it were happening in real-time. This prevents the common pitfall of using future information to make predictions about the past.

Core concepts:

- **Events**: The backtest generates chronological events (training, prediction) that drive the simulation
- **Versioned data**: Only data available at each event's timestamp can be used
- **Periodic retraining**: Models are retrained at configured intervals, just like in production
- **Horizon and windows**: Define how far ahead to predict and how often to step forward

Example backtest configuration:

.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import timedelta, datetime
   
   # Configure the backtest simulation
   config = BacktestConfig(
       horizon=timedelta(hours=24),      # Predict 24 hours ahead
       window_step=timedelta(days=1),    # Step forward daily
       retrain_interval=timedelta(days=7) # Retrain weekly
   )
   
   # Create pipeline with your forecaster
   pipeline = BacktestPipeline(
       config=config,
       forecaster=my_forecaster  # Your model implementing the forecaster interface
   )
   
   # Run simulation on versioned historical data
   predictions = pipeline.run(
       ground_truth=versioned_targets,
       predictors=versioned_features,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31)
   )

The ``BacktestPipeline.run()`` method returns a ``VersionedTimeSeriesDataset`` containing all predictions with their forecast timestamps, enabling proper evaluation that accounts for when predictions were made.

Evaluation: Structured Performance Reports
------------------------------------------

After backtesting produces predictions, the evaluation module organizes them into structured reports. This goes beyond simple accuracy metrics by analyzing performance across different conditions and time periods.

The evaluation pipeline handles:

- **Time windows**: Compare performance across days, weeks, or custom periods
- **Lead times**: Evaluate how accuracy degrades from 1-hour to 48-hour forecasts
- **Data filtering**: Focus on specific conditions like peak hours or weekends
- **Metric calculation**: Apply appropriate metrics (RMAE, CRPS, bias) to each subset
- **Report structure**: Organize results for easy analysis and comparison

Example evaluation setup:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, EvaluationPipeline, Window
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   from datetime import timedelta
   
   # Configure evaluation windows and metrics
   config = EvaluationConfig(
       windows=[
           Window(lag=timedelta(0), size=timedelta(days=7)),   # Last week
           Window(lag=timedelta(days=7), size=timedelta(days=30))  # Previous month
       ],
       lead_times=[1, 6, 12, 24, 48]  # Hours ahead to analyze
   )
   
   # Create pipeline with metric providers
   pipeline = EvaluationPipeline(
       config=config,
       quantiles=[0.1, 0.5, 0.9],  # For probabilistic forecasts
       metric_providers=[
           RMAEProvider(),   # Relative Mean Absolute Error
           RCRPSProvider()   # Relative Continuous Ranked Probability Score
       ]
   )
   
   # Generate evaluation report from backtest predictions
   report = pipeline.evaluate(
       predictions=predictions,
       ground_truth=versioned_targets
   )

The resulting ``EvaluationReport`` contains ``SubsetMetric`` objects for each combination of window, lead time, and filter condition. This structured format enables systematic analysis of where and when models perform well or poorly.

Analysis: Visualizations and Insights
--------------------------------------

The analysis module transforms numerical evaluation results into visualizations that reveal model behavior and performance patterns. Rather than staring at tables of metrics, analysts get charts and reports tailored to their needs.

Analysis capabilities include:

- **Summary tables**: Compare metrics across models, targets, or time periods
- **Lead time curves**: Visualize how accuracy changes with forecast horizon
- **Time series plots**: Show predictions versus actuals with confidence intervals
- **Custom visualizations**: Implement your own visualization classes

The analysis system uses a flexible callback architecture where visualizations are created based on grouping dimensions (by target, by run, by group).

Example analysis configuration:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import SummaryTableVisualization
   
   # Configure visualizations
   config = AnalysisConfig(
       visualizations=[
           SummaryTableVisualization(
               metrics=["rmae", "rcrps"],
               group_by="target"
           )
       ]
   )
   
   # Analysis pipeline processes evaluation reports
   # and generates configured visualizations

Visualizations implement specific methods like ``create_by_target()`` or ``create_by_run_and_group()`` that receive filtered evaluation reports and produce outputs (plots, tables, HTML reports).

Benchmarking: Multi-Model Comparison
-------------------------------------

The benchmarking module ties everything together by running complete BEAM workflows across multiple models and targets. This enables systematic comparison of forecasting approaches and long-term performance tracking.

Key features:

- **Parallel execution**: Process multiple targets efficiently
- **Pluggable storage**: Save results to local filesystem, cloud storage, or memory
- **Callback system**: Monitor progress and customize processing
- **Consistent results**: Automatic handling of data dependencies and validation

Example benchmark setup:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from pathlib import Path
   
   # Configure storage for results
   storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))
   
   # Create benchmark pipeline with all configurations
   benchmark = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
       analysis_config=analysis_config,
       storage=storage
   )
   
   # Run benchmark across multiple targets
   results = benchmark.run(
       targets=target_list,
       model_factory=my_model_factory
   )

The benchmark pipeline executes the complete workflow for each target: fetch data → backtest → evaluate → analyze → store results. This produces a comprehensive performance database that enables model selection and ongoing monitoring.

Dependencies and Integration
-----------------------------

BEAM depends on both core and models packages:

- **openstef_core**: Provides ``VersionedTimeSeriesDataset`` for proper temporal handling, ensuring backtests only use data available at prediction time. See :doc:`core` for details on versioned datasets.

- **openstef_models**: Supplies the actual forecasting implementations that BEAM tests. Models must implement the forecaster interface expected by the backtest pipeline. See :doc:`models` for transform and model details.

This architecture keeps concerns separated: core handles data structures, models implements forecasting algorithms, and BEAM orchestrates realistic validation workflows.

Practical Considerations
-------------------------

When using BEAM for model validation:

**Versioned data is essential**: Without proper versioning, backtests can accidentally use future information, producing overly optimistic results that don't match production performance.

**Retraining intervals matter**: Set ``retrain_interval`` to match your production deployment. More frequent retraining improves accuracy but increases computational cost.

**Choose appropriate windows**: Evaluation windows should align with operational needs. Energy markets often care about weekly patterns, seasonal effects, and peak hour performance.

**Lead time analysis reveals operational limits**: Understanding how accuracy degrades with forecast horizon helps operators know when to trust predictions and when to apply additional safety margins.

**Storage strategy affects scalability**: For large-scale benchmarks across many targets, choose storage backends that support your infrastructure (local for development, cloud for production).

Next Steps
----------

- Learn about versioned datasets in :doc:`core`
- Explore forecasting models and transforms in :doc:`models`
- See the benchmarking guide for multi-model comparison workflows
- Review the API reference for detailed class and method documentation