BEAM Package
============

The ``openstef_beam`` package provides the complete framework for testing, evaluating, and comparing energy forecasting models under realistic operational conditions. BEAM stands for **Backtesting, Evaluation, Analysis and Metrics** — a workflow that ensures your model validation results actually reflect real-world performance.

Unlike simple train-test splits that can mislead, BEAM uses versioned data to simulate how models perform in production. Models are retrained periodically and can only access information available at prediction time, preventing data leakage that inflates performance metrics.

Why BEAM Matters
----------------

Energy forecasting models often look great in validation but disappoint in production. The problem? Traditional validation doesn't account for:

- **Temporal constraints**: Models trained on all historical data, then tested on held-out periods
- **Retraining schedules**: Real systems retrain periodically with only past data available
- **Data versioning**: Historical data gets revised, but predictions use whatever was available at forecast time
- **Lead time degradation**: Forecast quality changes dramatically from 1-hour to 48-hour predictions

BEAM solves these problems by replaying historical data as if it were happening in real-time, respecting all operational constraints that affect production systems.

The BEAM Workflow
-----------------

BEAM orchestrates four interconnected stages:

**1. Backtesting** — Simulate realistic forecasting scenarios by replaying historical data. Models are retrained on schedule and make predictions using only information available at forecast time.

**2. Evaluation** — Organize backtest results into structured performance reports. Calculate metrics across different time periods, filter for specific conditions (weekends, peak hours), and aggregate results.

**3. Analysis** — Generate visualizations and detailed reports to understand model behavior. Examine how performance varies by lead time, season, or operational conditions.

**4. Benchmarking** — Compare multiple forecasting approaches across many targets. Automate the complete workflow from training through analysis for systematic model comparison.

.. note:: [DIAGRAM: BEAM workflow showing data flow from VersionedTimeSeriesDataset → Backtesting (with periodic retraining) → Evaluation (metrics calculation) → Analysis (visualization) → Benchmarking (multi-target comparison). Show dependencies on openstef_core (datasets) and openstef_models (transforms, forecasters).]

Package Architecture
--------------------

BEAM depends on both ``openstef_core`` and ``openstef_models`` to orchestrate complete evaluation workflows:

- **openstef_core**: Provides ``VersionedTimeSeriesDataset`` for temporal data management and ``TimeSeriesDataset`` for training data
- **openstef_models**: Supplies forecasting models and feature transforms
- **openstef_beam**: Orchestrates backtesting, evaluation, analysis, and benchmarking

This separation keeps data handling (core), modeling (models), and evaluation (beam) cleanly separated while enabling BEAM to coordinate the complete workflow.

Backtesting Module
------------------

The backtesting module simulates realistic forecasting operations by replaying historical data with proper temporal constraints.

Key components:

- ``BacktestPipeline``: Orchestrates the complete backtesting workflow
- ``BacktestEventGenerator``: Creates prediction and retraining events on schedule
- ``RestrictedHorizonVersionedTimeSeries``: Enforces temporal constraints to prevent data leakage
- ``BacktestForecasterMixin``: Interface for integrating forecasting models

The pipeline generates events (predictions, retraining) based on your schedule, executes them with only historically-available data, and collects results for evaluation.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import datetime, time, timedelta
   
   # Configure backtesting schedule
   pipeline = BacktestPipeline(
       start_date=datetime(2023, 1, 1),
       end_date=datetime(2023, 12, 31),
       prediction_time=time(9, 0),  # Make predictions at 9 AM daily
       retrain_schedule=timedelta(days=7),  # Retrain weekly
       forecast_horizons=[1, 6, 12, 24, 48],  # Lead times in hours
   )
   
   # Run backtest with versioned data
   results = pipeline.run(
       versioned_data=versioned_dataset,
       forecaster=your_forecaster,
   )

The ``RestrictedHorizonVersionedTimeSeries`` ensures models only access data available at prediction time, accounting for data arrival delays and revisions.

Evaluation Module
-----------------

After backtesting generates predictions, the evaluation module organizes results into structured performance reports.

The evaluation workflow:

1. **Collect predictions**: Gather forecast and actual values from backtest results
2. **Calculate metrics**: Compute MAE, RMSE, bias, and custom metrics
3. **Filter conditions**: Segment by time period, day type, or operational conditions
4. **Aggregate results**: Organize metrics by lead time, season, or other dimensions

.. code-block:: python

   from openstef_beam.evaluation import evaluate_backtest_results
   
   # Evaluate backtest results with standard metrics
   report = evaluate_backtest_results(
       predictions=backtest_results.predictions,
       actuals=backtest_results.actuals,
       metrics=['mae', 'rmse', 'bias', 'skill_score'],
       group_by=['lead_time', 'day_type'],
   )
   
   # Access structured results
   print(report.metrics_by_lead_time)
   print(report.weekend_vs_weekday_performance)

The evaluation module produces structured reports that feed into analysis and benchmarking stages.

Analysis Module
---------------

The analysis module generates visualizations and detailed reports to understand model behavior. This is where you discover why models perform well or poorly under different conditions.

Common analysis tasks:

- **Lead time degradation**: How forecast quality changes from short to long horizons
- **Seasonal patterns**: Performance differences across seasons or weather conditions
- **Error distribution**: Understanding when and why models make large errors
- **Feature importance**: Which inputs drive forecast accuracy

BEAM provides built-in analysis tools, but you can also create custom visualizations using the structured evaluation reports.

Benchmarking Module
-------------------

The benchmarking module automates complete model comparison studies across multiple forecasting targets. This is essential for energy system operators who need to evaluate forecasting approaches across diverse equipment types, regions, and operational scenarios.

The benchmarking workflow:

1. **Define targets**: Specify forecasting targets (substations, solar parks, wind farms)
2. **Configure models**: Set up forecasting approaches to compare
3. **Run backtests**: Execute backtesting for all model-target combinations
4. **Evaluate results**: Calculate metrics across all scenarios
5. **Compare performance**: Generate comparison reports and rankings

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkContext
   from openstef_beam.benchmarking import LocalBenchmarkStorage
   
   # Configure benchmark study
   context = BenchmarkContext(
       targets=target_provider,  # Provides forecasting targets
       forecaster_factory=forecaster_factory,  # Creates model instances
       storage=LocalBenchmarkStorage(path='./benchmark_results'),
   )
   
   # Run complete benchmark
   pipeline = BenchmarkPipeline(context=context)
   results = pipeline.run(
       start_date=datetime(2023, 1, 1),
       end_date=datetime(2023, 12, 31),
   )
   
   # Compare model performance
   comparison = results.compare_forecasters(
       metric='mae',
       group_by='target_type',
   )

The benchmarking module handles storage, parallelization, and result aggregation, making it practical to compare models across hundreds of forecasting targets.

Integration with Core and Models
---------------------------------

BEAM orchestrates components from across OpenSTEF:

**From openstef_core:**

- ``VersionedTimeSeriesDataset``: Manages temporal data with versioning for realistic backtesting
- ``TimeSeriesDataset``: Provides training data for model retraining during backtests

See the :doc:`core` page for details on dataset management.

**From openstef_models:**

- Forecasting models that implement the ``BacktestForecasterMixin`` interface
- Feature transforms applied during backtesting and evaluation

See the :doc:`models` page for details on transforms and forecasting models.

BEAM coordinates these components to ensure evaluation workflows maintain temporal integrity and operational realism.

Custom Metrics and Callbacks
-----------------------------

BEAM supports custom metrics and callbacks for specialized evaluation needs:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkCallback
   
   class CustomMetricCallback(BenchmarkCallback):
       """Calculate domain-specific metrics during benchmarking."""
       
       def on_backtest_complete(self, context, results):
           # Calculate custom metrics
           custom_score = self.calculate_operational_cost(
               predictions=results.predictions,
               actuals=results.actuals,
           )
           
           # Add to results
           results.metrics['operational_cost'] = custom_score
   
   # Use in benchmark pipeline
   pipeline = BenchmarkPipeline(
       context=context,
       callbacks=[CustomMetricCallback()],
   )

Callbacks enable integration with external systems, custom logging, or specialized analysis without modifying BEAM's core workflow.

Storage and Result Management
------------------------------

BEAM provides flexible storage backends for benchmark results:

- ``InMemoryBenchmarkStorage``: For testing and small studies
- ``LocalBenchmarkStorage``: File-based storage for local development
- ``S3BenchmarkStorage``: Cloud storage for production deployments

Results are stored in a structured format that enables:

- Incremental benchmarking (resume interrupted studies)
- Result sharing across teams
- Historical comparison (track model improvements over time)
- Reproducible research (archive complete evaluation results)

Next Steps
----------

- Learn about data management in :doc:`core`
- Explore feature engineering in :doc:`models`
- See the API reference for detailed component documentation