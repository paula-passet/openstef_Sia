BEAM Package
============

The ``openstef_beam`` package provides a complete framework for testing, evaluating, and comparing energy forecasting models under realistic operational conditions. BEAM stands for **Backtesting, Evaluation, Analysis and Metrics** - the four core capabilities that work together to ensure your forecasting models perform well in production.

Unlike simple train-test splits that can mislead, BEAM simulates real-world deployment by using versioned data, periodic retraining schedules, and strict temporal constraints. Models can only access information that would have been available at prediction time, preventing data leakage and producing reliable performance estimates.

.. note:: [DIAGRAM: BEAM workflow showing data flow from VersionedTimeSeriesDataset → BacktestPipeline (with periodic retraining) → predictions → EvaluationPipeline (metrics calculation) → EvaluationReport → Analysis (visualization) and BenchmarkPipeline (multi-model comparison). Show dependencies on openstef_core (datasets) and openstef_models (forecasters).]

The BEAM Workflow
-----------------

BEAM orchestrates a complete evaluation workflow through four distinct stages:

**Backtesting** simulates operational forecasting by replaying historical data as if it were happening in real-time. The ``BacktestPipeline`` manages prediction schedules, retraining intervals, and data access restrictions. It depends on ``openstef_core`` for versioned datasets and ``openstef_models`` for forecasting implementations.

**Evaluation** transforms raw predictions into structured performance reports. The ``EvaluationPipeline`` calculates metrics across different time windows, lead times, and filtering conditions. It organizes results into ``EvaluationReport`` objects that contain all the numerical data needed for analysis.

**Analysis** turns evaluation reports into actionable insights through visualization and interpretation. This stage provides tools for understanding model behavior, identifying failure modes, and communicating results to stakeholders.

**Benchmarking** extends the workflow to compare multiple models across many forecasting targets. The ``BenchmarkPipeline`` automates the entire process from training through analysis, making it practical to run large-scale comparison studies.

Backtesting: Realistic Model Testing
-------------------------------------

The backtesting module tests forecasting models by simulating how they would perform in actual operations. In real-world energy forecasting, you can't use future data to make predictions about the past. Backtesting enforces this constraint by "replaying" historical data with proper temporal boundaries.

Core Concepts
^^^^^^^^^^^^^

**Versioned data**: The ``RestrictedHorizonVersionedTimeSeries`` ensures models only access data available at prediction time. If a measurement arrives late or gets revised, the backtest reflects that reality.

**Event-driven execution**: The ``BacktestEventGenerator`` creates a schedule of prediction and retraining events. Models are retrained periodically (e.g., weekly) and make predictions at regular intervals (e.g., every 15 minutes), just like in production.

**Forecaster integration**: The ``BacktestForecasterMixin`` and ``BacktestBatchForecasterMixin`` provide interfaces for integrating your forecasting models. BEAM handles the orchestration while your forecaster focuses on making predictions.

Running a Backtest
^^^^^^^^^^^^^^^^^^

Here's how to run a basic backtest with the ``BacktestPipeline``:

.. code-block:: python

   from datetime import datetime, time, timedelta
   from openstef_beam.backtesting import BacktestPipeline
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Configure the backtest
   config = BacktestPipeline.Config(
       backtest_start=datetime(2023, 1, 1),
       backtest_end=datetime(2023, 12, 31),
       prediction_interval=timedelta(minutes=15),
       retraining_interval=timedelta(days=7),
       prediction_time=time(hour=9, minute=0),  # Daily predictions at 9 AM
       initial_training_days=365,
   )
   
   # Create pipeline with your forecaster and versioned data
   pipeline = BacktestPipeline(
       config=config,
       forecaster=my_forecaster,  # Implements BacktestForecasterMixin
       data=versioned_dataset,
   )
   
   # Run the backtest
   predictions = pipeline.run()

The pipeline returns a DataFrame containing all predictions with their timestamps, forecast horizons, and predicted values. This raw output feeds directly into the evaluation stage.

Evaluation: Structured Performance Reports
-------------------------------------------

After backtesting produces predictions, the evaluation module calculates metrics and organizes them into structured reports. This stage handles the complexity of comparing performance across different time periods, lead times, and filtering conditions.

The ``EvaluationPipeline`` takes predictions and actual values, then applies metric calculations according to your configuration. It produces an ``EvaluationReport`` containing all the numerical results organized for easy analysis.

Configuring Evaluation
^^^^^^^^^^^^^^^^^^^^^^^

Evaluation configuration defines what metrics to calculate, which time windows to analyze, and what filtering conditions to apply:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig, Window
   from openstef_beam.evaluation.metric_providers import rmse, mae, bias
   
   config = EvaluationConfig(
       metrics=[rmse, mae, bias],
       windows=[
           Window(name="full", start=None, end=None),
           Window(name="summer", start="2023-06-01", end="2023-08-31"),
           Window(name="winter", start="2023-12-01", end="2024-02-28"),
       ],
       lead_times=[1, 6, 12, 24, 48],  # Hours ahead
       filtering={
           "weekdays": lambda df: df[df.index.weekday < 5],
           "peak_hours": lambda df: df[df.index.hour.isin([8, 9, 10, 18, 19, 20])],
       }
   )
   
   # Run evaluation
   pipeline = EvaluationPipeline(config=config)
   report = pipeline.evaluate(predictions, actuals)

The resulting ``EvaluationReport`` contains metrics broken down by all specified dimensions. You can access specific results or pass the entire report to analysis tools.

Custom Metrics
^^^^^^^^^^^^^^

BEAM's metric system is extensible. Create custom metrics by implementing the metric provider interface:

.. code-block:: python

   from openstef_beam.evaluation.metric_providers import MetricProvider
   import numpy as np
   
   class WeightedMAPE(MetricProvider):
       name = "weighted_mape"
       
       def calculate(self, y_true, y_pred, weights=None):
           """Calculate weighted mean absolute percentage error."""
           if weights is None:
               weights = np.ones_like(y_true)
           
           percentage_errors = np.abs((y_true - y_pred) / y_true) * 100
           return np.average(percentage_errors, weights=weights)
   
   # Use in evaluation config
   config = EvaluationConfig(metrics=[WeightedMAPE()])

Analysis: Insights from Results
--------------------------------

The analysis module transforms evaluation reports into visualizations and insights. While evaluation produces raw numbers, analysis helps you understand what those numbers mean for your forecasting system.

Analysis tools work directly with ``EvaluationReport`` objects, providing consistent interfaces for exploring results. The module includes utilities for common analysis tasks like comparing metrics across time windows, visualizing error distributions, and identifying problematic forecast horizons.

.. note::
   For visualization capabilities, see the OpenSTEF built-in analysis tools. The analysis module integrates with evaluation reports to provide domain-specific visualizations for energy forecasting.

Benchmarking: Large-Scale Comparisons
--------------------------------------

The benchmarking module automates complete model comparison studies across multiple forecasting targets. Instead of manually running backtests and evaluations for each model-target combination, the ``BenchmarkPipeline`` orchestrates the entire workflow.

Setting Up a Benchmark
^^^^^^^^^^^^^^^^^^^^^^^

Benchmarks require defining the models to compare, the forecasting targets to test, and the evaluation criteria:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkContext
   
   # Define forecaster factories
   def create_xgboost_forecaster(context):
       return XGBoostForecaster(config=context.model_config)
   
   def create_linear_forecaster(context):
       return LinearForecaster(config=context.model_config)
   
   # Configure benchmark
   context = BenchmarkContext(
       forecaster_factories={
           "xgboost": create_xgboost_forecaster,
           "linear": create_linear_forecaster,
       },
       targets=["solar_park_1", "solar_park_2", "wind_farm_1"],
       backtest_config=backtest_config,
       evaluation_config=evaluation_config,
   )
   
   # Run benchmark
   pipeline = BenchmarkPipeline(context)
   results = pipeline.run()

The benchmark pipeline handles training each model on each target, running backtests, calculating metrics, and organizing results for comparison. It produces a structured report showing which models perform best under different conditions.

Benchmark Callbacks
^^^^^^^^^^^^^^^^^^^

The benchmarking system supports callbacks for monitoring progress, saving intermediate results, or implementing custom logic:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkCallback
   
   class ProgressLogger(BenchmarkCallback):
       def on_target_start(self, target_id, model_name):
           print(f"Starting {model_name} on {target_id}")
       
       def on_target_complete(self, target_id, model_name, report):
           rmse = report.get_metric("rmse", window="full")
           print(f"Completed: RMSE = {rmse:.2f}")
   
   # Use callback in pipeline
   pipeline = BenchmarkPipeline(context, callbacks=[ProgressLogger()])

Dependencies and Integration
-----------------------------

The BEAM package depends on both ``openstef_core`` and ``openstef_models``:

**openstef_core** provides the foundational data structures. BEAM uses ``VersionedTimeSeriesDataset`` for backtesting, ``TimeSeriesDataset`` for evaluation, and the configuration system for pipeline setup.

**openstef_models** supplies forecasting implementations. BEAM's backtesting system integrates with any forecaster that implements the required interface, whether it's a built-in model or your custom implementation.

This architecture keeps BEAM focused on evaluation workflows while leveraging the specialized capabilities of the core and models packages. See the :doc:`core` and :doc:`models` pages for details on those packages.

Practical Considerations
-------------------------

**Memory management**: Backtesting large datasets with frequent retraining can consume significant memory. Use batch processing or limit the backtest period if you encounter memory constraints.

**Computation time**: Realistic backtesting with periodic retraining takes time. For rapid iteration during development, consider shorter backtest periods or longer retraining intervals, then run full evaluations before deployment.

**Result storage**: Evaluation reports and benchmark results should be saved for later analysis and comparison. BEAM provides utilities for serializing reports to disk and loading them for subsequent analysis.

**Reproducibility**: Set random seeds in your forecaster configuration to ensure reproducible results. BEAM's event-driven execution is deterministic given the same data and configuration.

Next Steps
----------

- See :doc:`core` for details on ``VersionedTimeSeriesDataset`` and data handling
- See :doc:`models` for information on forecaster implementations and the transform pipeline
- Explore the API reference for complete details on BEAM classes and functions