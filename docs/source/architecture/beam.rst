BEAM: Backtesting, Evaluation, Analysis and Metrics
====================================================

The ``openstef_beam`` package provides a complete framework for evaluating energy forecasting models under realistic operational conditions. BEAM orchestrates the entire evaluation workflow—from backtesting through analysis—ensuring that model performance metrics reflect real-world deployment scenarios rather than optimistic validation results.

BEAM solves a critical problem in forecasting evaluation: preventing data leakage. Simple train-test splits can mislead because they don't account for how models are actually used in production. BEAM simulates real operational constraints by using versioned data, periodic retraining schedules, and strict temporal boundaries that ensure models only access information available at prediction time.

What BEAM Does
--------------

BEAM coordinates four interconnected components that work together to evaluate forecasting models:

**Backtesting** simulates how models perform in real operations by replaying historical data as if it were happening in real-time. Models are retrained on schedule, predictions are made with only past data, and the entire process mirrors production deployment.

**Evaluation** organizes the raw predictions and actuals from backtesting into structured performance reports. It calculates metrics across different time periods, filters for specific conditions (weekends, peak hours), and aggregates results at various levels.

**Analysis** transforms evaluation reports into actionable insights through visualizations and comparisons. It generates plots, tables, and statistical summaries that help you understand model behavior and identify performance patterns.

**Metrics** provides the measurement functions used throughout the workflow. BEAM includes standard forecasting metrics (MAE, RMSE, MAPE) plus specialized energy forecasting metrics (rMAE, rCRPS) and supports custom metric implementations.

.. note::
   [DIAGRAM: BEAM workflow showing: Versioned Data → Backtesting (with periodic retraining) → Predictions → Evaluation (metrics calculation) → Analysis (visualizations) → Insights. Show dependencies on openstef_core (TimeSeriesDataset, VersionedTimeSeriesDataset) and openstef_models (transforms, forecasters).]

Architecture and Dependencies
------------------------------

BEAM sits at the top of the OpenSTEF architecture and depends on both the core and models packages:

- **openstef_core** provides the data structures (``TimeSeriesDataset``, ``VersionedTimeSeriesDataset``) that BEAM uses to manage temporal constraints and versioned data access
- **openstef_models** supplies the forecasting models and feature transforms that BEAM evaluates during backtesting

This dependency structure means BEAM can evaluate any forecasting approach that implements the expected interfaces. You can plug in custom models, use different transform pipelines, or integrate external forecasting libraries—BEAM handles the evaluation orchestration regardless of the underlying forecasting implementation.

Backtesting: Realistic Model Testing
-------------------------------------

Backtesting is where BEAM ensures evaluation matches reality. The backtesting pipeline generates events that trigger predictions and retraining operations, just like in production systems.

A backtest event represents a specific moment in time when the forecasting system needs to make predictions. The event includes:

- The current timestamp (when predictions are being made)
- The prediction horizon (how far ahead to forecast)
- Whether this event triggers model retraining
- Access to versioned data up to the current timestamp

The backtesting pipeline processes these events sequentially, maintaining strict temporal ordering. Models can only access data that would have been available at each event's timestamp—no future information leaks into past predictions.

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import datetime, timedelta
   
   # Create versioned dataset with historical data
   versioned_data = VersionedTimeSeriesDataset(...)
   
   # Configure backtesting pipeline
   pipeline = BacktestPipeline(
       start_time=datetime(2024, 1, 1),
       end_time=datetime(2024, 3, 31),
       prediction_interval=timedelta(hours=1),  # Make predictions every hour
       retrain_interval=timedelta(days=7),      # Retrain weekly
       forecast_horizon=timedelta(hours=48),    # Predict 48 hours ahead
   )
   
   # Run backtest with your forecaster
   results = pipeline.run(
       forecaster=my_forecaster,
       data=versioned_data,
   )

The pipeline handles all the complexity of scheduling, data access restrictions, and result collection. You provide the forecaster and data; BEAM ensures the evaluation is realistic.

Evaluation: From Predictions to Metrics
----------------------------------------

After backtesting produces predictions, the evaluation component organizes them into structured reports. Evaluation calculates metrics at different aggregation levels—by lead time, by time of day, by season—giving you multiple perspectives on model performance.

Evaluation reports contain:

- Calculated metrics (both deterministic and probabilistic)
- Temporal aggregations (hourly, daily, weekly patterns)
- Conditional filters (weekends vs weekdays, peak vs off-peak)
- Target metadata (location, energy type, capacity)

The evaluation system is flexible about what metrics to calculate and how to aggregate results. You can focus on specific lead times that matter for your use case, filter for conditions where accuracy is critical, or create custom aggregation schemes.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationConfig, evaluate_backtest
   from openstef_beam.metrics import MAE, RMSE, MAPE
   
   # Configure evaluation
   eval_config = EvaluationConfig(
       metrics=[MAE(), RMSE(), MAPE()],
       lead_times=[1, 6, 12, 24, 48],  # Hours ahead
       aggregate_by_hour=True,
       aggregate_by_weekday=True,
   )
   
   # Generate evaluation reports from backtest results
   reports = evaluate_backtest(
       predictions=results,
       config=eval_config,
   )
   
   # Access metrics at different aggregations
   overall_mae = reports.overall.metrics["MAE"]
   weekend_performance = reports.by_weekday[5:7]  # Saturday, Sunday
   long_horizon_error = reports.by_lead_time[48]

Evaluation reports provide the structured data that analysis components use to generate visualizations and comparisons.

Analysis: Visualizations and Insights
--------------------------------------

The analysis component transforms evaluation reports into visual insights. BEAM includes several built-in visualization providers that generate common plots and tables for forecasting evaluation.

Built-in visualizations include:

- **Time series plots** showing predictions vs actuals over time
- **Grouped target comparisons** using bar charts and box plots to compare performance across multiple forecasting targets
- **Windowed metrics** displaying how accuracy changes over time
- **Quantile calibration** visualizing probabilistic forecast quality
- **Summary tables** presenting key metrics in tabular format

Each visualization provider implements specific aggregation logic and plot generation. You configure which visualizations to generate and BEAM handles the data routing and plot creation.

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig, run_analysis
   from openstef_beam.analysis.visualizations import (
       TimeSeriesVisualization,
       GroupedTargetMetricVisualization,
       WindowedMetricVisualization,
   )
   from openstef_core.types import Quantile
   
   # Configure analysis with multiple visualizations
   analysis_config = AnalysisConfig(
       visualization_providers=[
           TimeSeriesVisualization(
               name="forecast_comparison",
               quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
           ),
           GroupedTargetMetricVisualization(
               name="target_comparison",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           WindowedMetricVisualization(
               name="accuracy_over_time",
               metric="RMSE",
               window_size="7D",
           ),
       ],
   )
   
   # Generate all configured visualizations
   outputs = run_analysis(
       reports=reports,
       config=analysis_config,
   )
   
   # Save or display visualizations
   for name, output in outputs.items():
       output.figure.write_html(f"{name}.html")

The visualization system is extensible—you can implement custom visualization providers by subclassing ``VisualizationProvider`` and implementing the aggregation methods that match your needs.

Metrics and Measurement
------------------------

BEAM's metrics system provides the measurement functions used throughout evaluation and analysis. Metrics calculate performance scores from predictions and actuals, supporting both deterministic forecasts (point predictions) and probabilistic forecasts (quantile predictions).

Standard metrics include:

- **MAE** (Mean Absolute Error): Average absolute difference between predictions and actuals
- **RMSE** (Root Mean Squared Error): Square root of average squared errors
- **MAPE** (Mean Absolute Percentage Error): Average percentage error
- **rMAE** (relative MAE): MAE normalized by mean actual value
- **rCRPS** (relative Continuous Ranked Probability Score): Probabilistic forecast accuracy

All metrics implement a common interface, making them interchangeable in evaluation and analysis configurations. You can create custom metrics by implementing the same interface.

.. code-block:: python

   from openstef_beam.metrics import MetricProvider, MetricResult
   import numpy as np
   
   class CustomWeightedMAE(MetricProvider):
       """MAE with higher weight on peak hours."""
       
       name = "Weighted_MAE"
       
       def calculate(self, predictions, actuals, timestamps):
           # Weight peak hours (9-17) more heavily
           hours = timestamps.hour
           weights = np.where((hours >= 9) & (hours <= 17), 2.0, 1.0)
           
           errors = np.abs(predictions - actuals)
           weighted_error = np.average(errors, weights=weights)
           
           return MetricResult(value=weighted_error)
   
   # Use custom metric in evaluation
   eval_config = EvaluationConfig(
       metrics=[CustomWeightedMAE(), MAE(), RMSE()],
   )

Custom metrics integrate seamlessly with the rest of BEAM's evaluation and analysis workflow.

Complete Workflow Example
--------------------------

Here's how the BEAM components work together in a complete evaluation workflow:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline
   from openstef_beam.evaluation import EvaluationConfig, evaluate_backtest
   from openstef_beam.analysis import AnalysisConfig, run_analysis
   from openstef_beam.metrics import MAE, RMSE, rMAE
   from openstef_beam.analysis.visualizations import (
       TimeSeriesVisualization,
       SummaryTableVisualization,
   )
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from datetime import datetime, timedelta
   
   # 1. Prepare versioned data
   versioned_data = VersionedTimeSeriesDataset.from_dataframe(
       df=historical_data,
       version_column="data_version",
   )
   
   # 2. Run backtest
   pipeline = BacktestPipeline(
       start_time=datetime(2024, 1, 1),
       end_time=datetime(2024, 3, 31),
       prediction_interval=timedelta(hours=1),
       retrain_interval=timedelta(days=7),
       forecast_horizon=timedelta(hours=48),
   )
   
   backtest_results = pipeline.run(
       forecaster=my_forecaster,
       data=versioned_data,
   )
   
   # 3. Evaluate predictions
   eval_config = EvaluationConfig(
       metrics=[MAE(), RMSE(), rMAE()],
       lead_times=[1, 6, 12, 24, 48],
   )
   
   reports = evaluate_backtest(
       predictions=backtest_results,
       config=eval_config,
   )
   
   # 4. Generate analysis visualizations
   analysis_config = AnalysisConfig(
       visualization_providers=[
           TimeSeriesVisualization(name="predictions_vs_actuals"),
           SummaryTableVisualization(name="performance_summary"),
       ],
   )
   
   visualizations = run_analysis(
       reports=reports,
       config=analysis_config,
   )
   
   # 5. Export results
   for name, output in visualizations.items():
       output.save(f"results/{name}")

This workflow demonstrates BEAM's design: each component has a clear responsibility, and they compose together to provide complete evaluation capabilities.

Integration with Core and Models
---------------------------------

BEAM's effectiveness depends on proper integration with the other OpenSTEF packages:

**From openstef_core**, BEAM uses:

- ``VersionedTimeSeriesDataset`` to enforce temporal constraints during backtesting
- ``TimeSeriesDataset`` for managing prediction and actual value data
- Type definitions (``Quantile``, ``Horizon``) for consistent interfaces

See :doc:`core` for details on these data structures.

**From openstef_models**, BEAM evaluates:

- Forecasting models that implement the expected prediction interface
- Transform pipelines that prepare features for modeling
- Model training and updating logic during backtesting

See :doc:`models` for information on the forecasting models and transforms that BEAM evaluates.

BEAM provides the orchestration layer that makes these components work together in realistic evaluation scenarios. The versioned data from core ensures temporal correctness, the models from models provide forecasting capabilities, and BEAM coordinates the entire evaluation workflow.

When to Use BEAM
-----------------

Use BEAM when you need to:

- Evaluate forecasting models under realistic operational constraints
- Compare multiple forecasting approaches with confidence that results reflect real-world performance
- Generate comprehensive performance reports with multiple metrics and aggregations
- Visualize model behavior across different time periods and conditions
- Ensure evaluation results will translate to production deployment

BEAM is particularly valuable when moving from research to production. The versioned data approach and realistic backtesting prevent the common problem where models perform well in validation but poorly in deployment.

For quick model prototyping or simple validation, you might use simpler evaluation approaches. But when evaluation results matter—when they inform deployment decisions or model selection—BEAM provides the rigor needed to trust those results.