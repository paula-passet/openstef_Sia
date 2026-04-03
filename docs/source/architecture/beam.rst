BEAM Package
============

The ``openstef_beam`` package provides a complete framework for testing, evaluating, and analyzing energy forecasting models under realistic operational conditions. BEAM stands for **Backtesting, Evaluation, Analysis, and Metrics** — four interconnected components that work together to validate model performance with the same constraints faced in production deployments.

Unlike simple train-test splits that can leak future information, BEAM uses versioned data to ensure models only access information that would be available at prediction time. This approach prevents overly optimistic performance estimates and ensures evaluation results translate to real-world success.

BEAM orchestrates workflows that span multiple packages: it depends on ``openstef_core`` for data structures like ``VersionedTimeSeriesDataset`` and ``openstef_models`` for forecasting implementations, while providing the evaluation infrastructure that ties everything together.

.. note:: [DIAGRAM: BEAM workflow showing four stages: 1) Backtesting (generates predictions from versioned data), 2) Evaluation (computes metrics on predictions), 3) Analysis (creates visualizations), 4) Benchmarking (compares multiple runs). Arrows show data flow from VersionedTimeSeriesDataset through BacktestPipeline to EvaluationPipeline to AnalysisEngine, with dependencies on openstef_core and openstef_models packages.]

Backtesting: Realistic Model Testing
-------------------------------------

The backtesting module simulates how models perform in real operations by replaying historical data as if it were happening in real-time. Models are retrained periodically, predictions use only past data, and the entire process mirrors production deployment.

A backtest runs through a series of events — training windows where models learn from historical data, and prediction moments where models forecast future values. The ``BacktestPipeline`` orchestrates this process:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import datetime, timedelta
   
   # Configure backtesting parameters
   config = BacktestConfig(
       horizon=timedelta(hours=47),      # Forecast 47 hours ahead
       window_step=timedelta(days=1),    # Make predictions daily
       training_window=timedelta(days=90),  # Train on 90 days of data
       retrain_interval=timedelta(days=7)   # Retrain weekly
   )
   
   # Create pipeline with your model factory
   pipeline = BacktestPipeline(
       config=config,
       model_factory=my_model_factory,
       target_metadata=target_metadata
   )
   
   # Run backtest on versioned data
   predictions = pipeline.run(
       ground_truth=versioned_target_data,
       predictors=versioned_feature_data,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31)
   )

The ``BacktestConfig`` controls the simulation behavior. The ``horizon`` defines how far ahead to forecast, ``window_step`` determines prediction frequency, and ``retrain_interval`` specifies how often to update the model with new data. These parameters should match your production deployment to ensure evaluation results are meaningful.

The pipeline returns a ``VersionedTimeSeriesDataset`` containing all predictions with their timestamps and data versions. This versioned output preserves the information about when each prediction was made and what data was available, critical for downstream evaluation.

Evaluation: Structured Performance Reports
-------------------------------------------

After backtesting generates predictions, the evaluation module organizes them into structured performance reports. Evaluation calculates metrics across different time periods, filters for specific conditions, and handles the complexity of comparing predictions at multiple lead times.

The ``EvaluationPipeline`` takes backtest predictions and computes metrics according to your configuration:

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.evaluation.metric_providers import RMAEProvider, RCRPSProvider
   
   # Configure evaluation with custom metrics
   eval_config = EvaluationConfig(
       metric_providers=[
           RMAEProvider(),      # Relative Mean Absolute Error
           RCRPSProvider()      # Relative Continuous Ranked Probability Score
       ],
       lead_times=[1, 6, 12, 24, 47]  # Evaluate at specific forecast horizons
   )
   
   # Create evaluation pipeline
   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=[0.1, 0.5, 0.9],  # For probabilistic forecasts
       target_metadata=target_metadata
   )
   
   # Generate evaluation report
   report = eval_pipeline.run(
       predictions=predictions,
       ground_truth=versioned_target_data
   )

The ``EvaluationConfig`` specifies which metrics to compute and at which lead times. Metric providers are pluggable — you can use built-in providers like ``RMAEProvider`` for deterministic forecasts or ``RCRPSProvider`` for probabilistic forecasts, or implement custom providers for domain-specific metrics.

The evaluation pipeline handles time windows automatically, breaking down performance by day, week, or custom periods. It also supports data filtering to focus on specific conditions like peak hours or weekdays. The resulting ``EvaluationReport`` contains structured metric values organized by subset, making it easy to identify where models perform well or poorly.

Analysis: Visualization and Interpretation
-------------------------------------------

The analysis module transforms evaluation reports into visualizations and comparative summaries. While evaluation produces raw numbers, analysis helps you understand what those numbers mean through plots, tables, and statistical comparisons.

Analysis works with the ``AnalysisEngine`` that applies visualizations to evaluation reports:

.. code-block:: python

   from openstef_beam.analysis import AnalysisEngine, AnalysisConfig
   from openstef_beam.analysis.visualizations import (
       SummaryTableVisualization,
       LeadTimeVisualization
   )
   
   # Configure analysis with desired visualizations
   analysis_config = AnalysisConfig(
       visualizations=[
           SummaryTableVisualization(),  # Tabular metric summary
           LeadTimeVisualization()       # Performance vs forecast horizon
       ]
   )
   
   # Create analysis engine
   engine = AnalysisEngine(config=analysis_config)
   
   # Generate visualizations from evaluation report
   results = engine.run(
       reports=[("model_v1", report, target_metadata)],
       storage=storage
   )

Visualizations are modular components that implement specific analysis patterns. ``SummaryTableVisualization`` creates tables comparing metrics across targets or model runs. ``LeadTimeVisualization`` plots how accuracy degrades as forecast horizon increases — critical for understanding operational limitations.

The analysis engine supports grouping by target, by model run, or by custom categories. This flexibility allows you to answer questions like "which model performs best on residential loads?" or "how does performance vary by season?"

Benchmarking: Complete Workflow Orchestration
----------------------------------------------

The benchmarking module ties everything together, orchestrating complete workflows from data loading through analysis. Benchmarking handles multiple targets, multiple model configurations, and parallel execution while managing storage and error recovery.

A ``BenchmarkPipeline`` coordinates the full BEAM workflow:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline
   from openstef_beam.benchmarking.storage.local_storage import LocalBenchmarkStorage
   from pathlib import Path
   
   # Configure storage for results
   storage = LocalBenchmarkStorage(base_path=Path("./benchmark_results"))
   
   # Create benchmark pipeline with all components
   benchmark = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=eval_config,
       analysis_config=analysis_config,
       storage=storage,
       model_factory=my_model_factory
   )
   
   # Run benchmark across multiple targets
   benchmark.run(
       targets=target_list,
       data_provider=my_data_provider,
       run_name="baseline_model_v2"
   )

The benchmark pipeline handles the complete workflow: loading data for each target, running backtests, computing evaluations, generating analysis, and storing results. It supports parallel execution to process large target sets efficiently and provides callbacks for monitoring progress.

Storage backends are pluggable — use ``LocalBenchmarkStorage`` for filesystem storage or implement custom backends for cloud storage or databases. Results are persisted with metadata that allows comparing different model runs or tracking performance over time.

Integration with Core and Models
---------------------------------

BEAM depends heavily on both ``openstef_core`` and ``openstef_models`` packages. From core, it uses ``VersionedTimeSeriesDataset`` to maintain data versioning throughout the workflow and ``TimeSeriesDataset`` for non-versioned operations. The versioning ensures backtests never leak future information.

From models, BEAM uses forecaster implementations and the transform pipeline. Your model factory should return forecasters that implement the expected interface — typically created using the factory pattern from ``openstef_models``. See the :doc:`models` page for details on forecaster implementation and the :doc:`core` page for information on dataset structures.

BEAM provides the evaluation infrastructure but remains agnostic to specific model implementations. This separation allows you to test any forecasting approach — from simple baselines to complex ensemble methods — using the same evaluation framework.

Practical Considerations
-------------------------

When designing backtests, match your configuration to production deployment. If you retrain models weekly in production, use the same interval in backtests. If you make predictions every hour, set ``window_step`` accordingly. Mismatched configurations produce evaluation results that don't reflect real performance.

Versioned data is critical for meaningful evaluation. Standard train-test splits often leak information because they assume all data is available simultaneously. In reality, weather forecasts get updated, measurements arrive with delays, and models must work with whatever data exists at prediction time. BEAM's versioned approach captures these real-world constraints.

Metric selection matters. Energy forecasting has unique characteristics — peak errors are often more costly than off-peak errors, probabilistic forecasts need different metrics than point forecasts, and relative metrics (like RMAE) are more interpretable than absolute metrics when comparing across targets with different scales. Choose metrics that align with your operational objectives.

For large-scale benchmarking across many targets, consider computational resources carefully. Backtesting is computationally intensive because it trains and evaluates models repeatedly. Use parallel execution where possible and consider sampling strategies for initial exploration before running full benchmarks.

Further Reading
---------------

For details on the data structures BEAM operates on, see :doc:`core`. For information about implementing and configuring forecasting models, see :doc:`models`. The API reference provides complete documentation of all BEAM classes and functions.