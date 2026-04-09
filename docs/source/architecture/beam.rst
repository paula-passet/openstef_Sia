BEAM Package
============

The ``openstef_beam`` package provides a complete framework for evaluating energy forecasting models under realistic conditions. BEAM stands for **Backtesting, Evaluation, Analysis and Metrics** - the four pillars of rigorous model testing.

Unlike simple train/test splits that can mislead, BEAM simulates real-world operational scenarios. It uses versioned data to ensure models only access information available at prediction time, retrains models on realistic schedules, and evaluates performance across multiple dimensions like lead time, time of day, and seasonal patterns.

The BEAM Workflow
-----------------

BEAM orchestrates a complete evaluation workflow that depends on both the core and models packages:

1. **Backtesting**: Simulate operational forecasting by replaying historical data as if it were happening in real-time
2. **Evaluation**: Calculate performance metrics across different time periods and conditions
3. **Analysis**: Visualize results and identify patterns in model performance
4. **Benchmarking**: Compare multiple models systematically across different targets

Each stage builds on the previous one, creating a comprehensive picture of model performance.

Backtesting: Realistic Model Testing
-------------------------------------

The backtesting module tests forecasting models by simulating how they would perform in actual operations. This prevents data leakage - the common mistake of using future information to make predictions about the past.

Key features:

- **Versioned data handling**: Models only see data available at prediction time
- **Periodic retraining**: Simulates operational training schedules
- **Realistic constraints**: Honors data availability and processing delays
- **Fair comparison**: All models tested under identical conditions

The ``BacktestPipeline`` class orchestrates the entire backtesting process:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_core import TimeSeriesDataset
   
   # Configure backtesting parameters
   config = BacktestConfig(
       start_date="2023-01-01",
       end_date="2023-12-31",
       retrain_interval_days=7,  # Retrain weekly
       forecast_horizons=[1, 6, 24, 47],  # Lead times in hours
   )
   
   # Create pipeline
   pipeline = BacktestPipeline(config)
   
   # Run backtest with your forecaster
   results = pipeline.run(
       forecaster=my_forecaster,
       dataset=historical_data,
       target_column="load"
   )

The backtest results contain predictions made at each forecast horizon, along with metadata about when each prediction was made and what data was available.

Evaluation: Structured Performance Reports
------------------------------------------

After backtesting generates predictions, the evaluation module organizes them into structured performance reports. This module calculates metrics across different dimensions and filters results for specific conditions.

The ``EvaluationPipeline`` provides comprehensive evaluation capabilities:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   
   # Configure evaluation
   eval_config = EvaluationConfig(
       metrics=["mae", "rmse", "skill_score"],
       lead_times=[1, 6, 24, 47],
       time_windows=["all", "peak_hours", "weekends"],
   )
   
   # Create evaluation pipeline
   eval_pipeline = EvaluationPipeline(eval_config)
   
   # Evaluate backtest results
   report = eval_pipeline.run(
       predictions=backtest_results,
       ground_truth=actual_values,
       target_column="load"
   )
   
   # Access metrics for specific conditions
   peak_hour_mae = report.get_metric("mae", time_window="peak_hours")
   weekend_rmse = report.get_metric("rmse", time_window="weekends")

The evaluation pipeline segments data across multiple dimensions:

- **Lead times**: How does accuracy change with forecast horizon?
- **Time windows**: Performance during peak hours vs. off-peak
- **Availability times**: When was the forecast made?
- **Seasonal patterns**: Summer vs. winter performance

This multi-dimensional view reveals patterns that aggregate metrics would hide.

Metrics and Custom Evaluation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

BEAM includes standard forecasting metrics (MAE, RMSE, MAPE, skill scores) but also supports custom metrics through the ``MetricProvider`` interface:

.. code-block:: python

   from openstef_beam.evaluation.metric_providers import MetricProvider
   
   class CustomMetricProvider(MetricProvider):
       def compute_metrics(self, predictions, ground_truth):
           # Your custom metric logic
           return {
               "custom_score": calculate_custom_score(predictions, ground_truth)
           }
   
   # Use in evaluation pipeline
   eval_config = EvaluationConfig(
       metric_providers=[CustomMetricProvider()]
   )

This extensibility allows you to evaluate models using domain-specific criteria relevant to your use case.

Analysis: Understanding Model Behavior
---------------------------------------

The analysis module helps you understand *why* models perform the way they do. It provides tools for visualizing results, identifying failure modes, and comparing different approaches.

Analysis capabilities include:

- **Performance visualization**: Plot metrics across lead times and time periods
- **Error analysis**: Identify systematic biases and failure patterns
- **Feature importance**: Understand which inputs drive predictions
- **Residual analysis**: Detect patterns in prediction errors

The analysis module integrates with OpenSTEF's built-in visualization tools to create publication-ready charts and reports.

Benchmarking: Systematic Model Comparison
------------------------------------------

The benchmarking module brings everything together to compare multiple models across different targets. The ``BenchmarkPipeline`` coordinates the entire workflow:

1. Acquire targets from configurable providers
2. Run backtesting for each model and target
3. Evaluate all results with consistent metrics
4. Analyze and visualize comparative performance
5. Store results for future reference

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline, BenchmarkConfig
   
   # Configure benchmark
   benchmark_config = BenchmarkConfig(
       models=["xgboost", "linear", "naive"],
       targets=["load_1", "load_2", "solar_1"],
       backtest_config=backtest_config,
       evaluation_config=eval_config,
   )
   
   # Run comprehensive benchmark
   benchmark = BenchmarkPipeline(benchmark_config)
   results = benchmark.run()
   
   # Compare models across all targets
   comparison = results.compare_models()
   best_model = results.get_best_model(metric="mae")

The benchmark pipeline handles parallel execution, result storage, and provides tools for analyzing results across the entire experiment.

Dependencies on Core and Models
--------------------------------

BEAM depends heavily on both the ``openstef_core`` and ``openstef_models`` packages:

**From openstef_core**:

- ``TimeSeriesDataset``: Container for versioned time series data used in backtesting
- Data validation and quality checks
- Time series utilities for handling forecast horizons

**From openstef_models**:

- Transform pipeline: Feature engineering applied during backtesting
- Model interfaces: Standard API for plugging in different forecasters
- Serialization: Saving and loading trained models

See the :doc:`core` and :doc:`models` pages for details on these dependencies.

Preventing Data Leakage
------------------------

The most critical feature of BEAM is preventing data leakage - using future information to make predictions about the past. This is surprisingly easy to do accidentally:

- Using the entire dataset to compute normalization parameters
- Training on data that includes the forecast period
- Using features that wouldn't be available at prediction time

BEAM prevents these mistakes by:

- Enforcing strict time boundaries in backtesting
- Using versioned data that reflects information availability
- Validating that features don't leak future information
- Simulating realistic data processing delays

This ensures that backtest results accurately reflect operational performance.

Practical Considerations
-------------------------

When using BEAM for model evaluation, consider:

**Computational cost**: Backtesting with periodic retraining is expensive. Use parallel execution and cache intermediate results.

**Data requirements**: You need sufficient historical data to simulate realistic operational conditions. At minimum, several months of data with appropriate versioning.

**Metric selection**: Choose metrics that align with business objectives. MAE might be more interpretable than RMSE for stakeholders.

**Time windows**: Evaluate performance during operationally critical periods (peak hours, extreme weather) not just overall averages.

**Lead time focus**: Different use cases care about different forecast horizons. Day-ahead trading needs 24-hour forecasts; real-time dispatch needs 1-hour forecasts.

Next Steps
----------

- See the API reference for detailed class and function documentation
- Check the examples directory for complete workflow demonstrations
- Explore :doc:`core` for details on ``TimeSeriesDataset`` and data handling
- Review :doc:`models` for information on the transform pipeline and model interfaces