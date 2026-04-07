BEAM Package
============

The ``openstef_beam`` package provides a complete framework for testing energy forecasting models under realistic operational conditions. BEAM stands for **Backtesting, Evaluation, Analysis and Metrics** — the four stages of a rigorous model validation workflow.

Unlike simple train-test splits that can mislead, BEAM simulates real-world scenarios where models are retrained periodically and predictions are made with only historical data available. This prevents data leakage and ensures evaluation results match production performance.

BEAM orchestrates workflows that depend on both the ``openstef_core`` package (for data handling via ``TimeSeriesDataset``) and the ``openstef_models`` package (for forecasting implementations). See :doc:`core` and :doc:`models` for details on those components.

The BEAM Workflow
-----------------

BEAM follows a four-stage pipeline:

1. **Backtesting**: Simulate operational forecasting by replaying historical data as if it were happening in real-time
2. **Evaluation**: Calculate performance metrics across different time periods and conditions
3. **Analysis**: Generate visualizations and reports to understand model behavior
4. **Benchmarking**: Compare multiple models or configurations across different targets

.. note::
   [DIAGRAM: BEAM workflow showing data flow from versioned historical data → BacktestPipeline → predictions → EvaluationPipeline → metrics → AnalysisPipeline → visualizations/reports, with arrows showing dependencies on openstef_core (TimeSeriesDataset) and openstef_models (forecasters)]

Each stage produces structured outputs that feed into the next, creating a reproducible evaluation process.

Backtesting: Realistic Model Testing
-------------------------------------

The backtesting module simulates how forecasting models perform in real operations. Models are retrained at regular intervals (e.g., weekly) and generate predictions at scheduled times (e.g., every 15 minutes), using only data that would have been available at that moment.

Core Components
^^^^^^^^^^^^^^^

**BacktestPipeline** orchestrates the simulation process:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from datetime import datetime, timedelta
   
   # Configure backtesting parameters
   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),  # Forecast every 15 min
       training_interval=timedelta(days=7),  # Retrain weekly
       training_horizon=timedelta(days=90),  # Use 90 days of history
       prediction_horizons=[
           timedelta(minutes=15),
           timedelta(hours=1),
           timedelta(hours=24),
           timedelta(hours=47)
       ]
   )
   
   # Create pipeline with your forecaster
   pipeline = BacktestPipeline(
       config=config,
       forecaster=my_forecaster  # Must implement BacktestForecasterMixin
   )
   
   # Run backtest for a specific period
   predictions = pipeline.run(
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31)
   )

**BacktestForecasterMixin** defines the interface your forecasting model must implement:

.. code-block:: python

   from openstef_beam.backtesting import BacktestForecasterMixin
   from openstef_core import TimeSeriesDataset
   
   class MyForecaster(BacktestForecasterMixin):
       @property
       def prediction_sample_interval(self) -> timedelta:
           return timedelta(minutes=15)
       
       @property
       def quantiles(self) -> list[float]:
           return [0.1, 0.5, 0.9]  # Predict 10th, 50th, 90th percentiles
       
       def train(self, data: TimeSeriesDataset, prediction_time: datetime) -> None:
           """Train model using only data available before prediction_time."""
           # Your training logic here
           pass
       
       def predict(
           self,
           data: TimeSeriesDataset,
           prediction_time: datetime,
           horizons: list[timedelta]
       ) -> pd.DataFrame:
           """Generate predictions for specified horizons."""
           # Your prediction logic here
           pass

The pipeline ensures temporal consistency: during training and prediction, your model only receives data with timestamps before ``prediction_time``. This prevents the common mistake of accidentally using future information.

Temporal Consistency
^^^^^^^^^^^^^^^^^^^^

BEAM's versioned data approach is critical for realistic evaluation. In production, you make predictions with incomplete information — yesterday's data might still be arriving, and you don't know tomorrow's weather forecast. Backtesting must respect these same constraints.

The pipeline tracks when data becomes available and only provides it to your model at the appropriate time. Models are retrained periodically with the latest available data, simulating operational retraining schedules.

Evaluation: Structured Performance Reports
------------------------------------------

After backtesting generates predictions, the evaluation module calculates metrics and organizes results into structured reports. You can filter for specific conditions (weekends, peak hours, high-load periods) and aggregate metrics across different time periods.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   
   # Configure evaluation
   eval_config = EvaluationConfig(
       metrics=["mae", "rmse", "bias", "r2"],
       lead_times=[
           timedelta(hours=1),
           timedelta(hours=6),
           timedelta(hours=24)
       ],
       filters={
           "weekends": lambda df: df.index.dayofweek >= 5,
           "peak_hours": lambda df: df.index.hour.isin([8, 9, 17, 18, 19])
       }
   )
   
   # Run evaluation
   eval_pipeline = EvaluationPipeline(config=eval_config)
   report = eval_pipeline.evaluate(predictions, actuals)
   
   # Access structured results
   print(f"1-hour MAE: {report.get_metric('mae', timedelta(hours=1))}")
   print(f"Weekend performance: {report.filter('weekends').summary()}")

The evaluation module produces ``EvaluationSubsetReport`` objects that organize metrics by lead time, time period, and custom filters. This structured format makes it easy to compare performance across different conditions.

Analysis: Visualizations and Insights
--------------------------------------

The analysis module transforms evaluation reports into visualizations and summary statistics. You can create custom analysis functions or use built-in templates for common energy forecasting use cases.

.. code-block:: python

   from openstef_beam.analysis import AnalysisPipeline, AnalysisConfig
   
   # Configure analysis
   analysis_config = AnalysisConfig(
       visualizations=[
           "lead_time_performance",  # How accuracy degrades with horizon
           "temporal_patterns",  # Performance by hour/day/month
           "quantile_calibration"  # Are probabilistic forecasts well-calibrated?
       ],
       aggregations=["by_month", "by_weekday", "by_hour"]
   )
   
   # Generate analysis
   analysis_pipeline = AnalysisPipeline(config=analysis_config)
   results = analysis_pipeline.analyze(report)
   
   # Save outputs
   results.save_plots("output/figures/")
   results.save_summary("output/summary.json")

Analysis outputs help you understand not just how well your model performs, but *why* it performs that way. Lead time analysis reveals how forecast quality degrades from 1-hour to 48-hour predictions. Temporal pattern analysis shows whether your model struggles with specific times of day or seasons.

Benchmarking: Multi-Model Comparison
-------------------------------------

The benchmarking module extends the workflow to compare multiple models or configurations across different energy targets. This is essential when you need to select the best approach for a diverse portfolio of forecasting problems.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkRunner
   
   # Define models to compare
   models = {
       "xgboost": XGBoostForecaster(),
       "linear": LinearForecaster(),
       "ensemble": EnsembleForecaster()
   }
   
   # Define targets (e.g., different substations)
   targets = load_targets_from_config()
   
   # Run benchmark
   runner = BenchmarkRunner(
       models=models,
       targets=targets,
       backtest_config=backtest_config,
       evaluation_config=eval_config
   )
   
   comparison = runner.run()
   
   # Compare models across all targets
   print(comparison.summary_table())
   comparison.plot_model_comparison()

The benchmark runner executes the complete BEAM workflow for each model-target combination, then aggregates results for easy comparison. This reveals which models work best for different types of load patterns or geographic regions.

Dependencies and Integration
-----------------------------

BEAM depends on both ``openstef_core`` and ``openstef_models``:

- **openstef_core**: Provides ``TimeSeriesDataset`` for handling time series data with versioning support. BEAM uses this to ensure temporal consistency during backtesting.

- **openstef_models**: Provides forecasting model implementations and the transform pipeline. Your forecasters typically use transforms from this package for feature engineering.

When implementing a forecaster for BEAM, you'll typically:

1. Use ``TimeSeriesDataset`` from ``openstef_core`` to handle input data
2. Apply transforms from ``openstef_models`` for feature engineering
3. Implement ``BacktestForecasterMixin`` to integrate with BEAM's pipeline
4. Return predictions in the format expected by BEAM's evaluation module

This separation of concerns keeps the architecture clean: ``openstef_core`` handles data, ``openstef_models`` handles forecasting logic, and ``openstef_beam`` handles evaluation workflows.

Key Advantages
--------------

BEAM's approach offers several advantages over simpler validation methods:

**Prevents data leakage**: By using versioned data and respecting temporal constraints, BEAM ensures models only use information available at prediction time. This prevents the common mistake of accidentally training on future data.

**Simulates operational conditions**: Periodic retraining, scheduled predictions, and limited data availability match real-world deployment scenarios. Evaluation results translate directly to production performance.

**Flexible and extensible**: Plug in custom forecasters, metrics, visualizations, and filters. BEAM provides the orchestration framework while letting you define the specifics for your use case.

**Reproducible workflows**: Structured configuration and output formats make it easy to reproduce evaluations, compare experiments, and track model performance over time.

For energy forecasting, where models must perform reliably in operational settings, BEAM's rigorous approach to validation is essential. Simple train-test splits can give misleadingly optimistic results that don't hold up in production. BEAM's simulation-based approach provides confidence that evaluation results reflect real-world performance.