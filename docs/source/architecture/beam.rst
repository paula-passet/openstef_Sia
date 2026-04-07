BEAM Package (``openstef_beam``)
================================

The ``openstef_beam`` package — **B**\ acktesting, **E**\ valuation, **A**\ nalysis, and **M**\ etrics — provides a complete framework for testing energy forecasting models under realistic conditions. Rather than relying on simple train/test splits that can give misleading results, BEAM simulates real-world operational scenarios using versioned data, ensuring that models only access information that would have been available at prediction time.

BEAM builds on top of the :doc:`core <core>` and :doc:`models <models>` packages, using ``VersionedTimeSeriesDataset`` from core and forecaster implementations from models to orchestrate end-to-end evaluation workflows.

.. note:: [DIAGRAM: BEAM workflow pipeline showing four stages in sequence: Backtesting (generates predictions) → Evaluation (computes metrics per subset) → Analysis (creates visualizations) → Benchmarking (compares models across targets). Arrows show data flow: BacktestPipeline produces predictions, EvaluationPipeline produces EvaluationReport, AnalysisPipeline produces visualizations, BenchmarkPipeline orchestrates all stages. Dependencies on openstef_core (VersionedTimeSeriesDataset) and openstef_models (forecaster implementations) feed into the Backtesting stage.]


The Four Stages
---------------

BEAM's workflow is organized into four sequential stages, each with its own pipeline class and configuration:

1. **Backtesting** — Replay historical data to generate predictions as if in real-time
2. **Evaluation** — Segment predictions by lead time, time window, and availability, then compute metrics
3. **Analysis** — Transform numerical results into visualizations and reports
4. **Benchmarking** — Orchestrate the full workflow across multiple models and targets for comparison

Each stage can be used independently, but they are designed to compose naturally into a complete evaluation workflow.


Backtesting
-----------

The backtesting module simulates how a forecasting model would have performed in production. It "replays" historical data chronologically, retraining the model at configurable intervals and generating predictions using only data that would have been available at each point in time.

This approach prevents **data leakage** — the most common source of overly optimistic evaluation results in time series forecasting.

The two central classes are ``BacktestConfig`` and ``BacktestPipeline``:

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_beam.backtesting import BacktestConfig, BacktestPipeline

   config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),
       training_interval=timedelta(days=7),
       prediction_horizon=timedelta(hours=48),
       training_history=timedelta(days=365),
   )

   pipeline = BacktestPipeline(config=config, forecaster=my_forecaster)

   # Run backtesting over a historical period using versioned data
   results = pipeline.run(
       ground_truth=versioned_ground_truth,
       predictors=versioned_predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 6, 30),
       show_progress=True,
   )

The ``forecaster`` must implement the ``BacktestForecasterMixin`` (or ``BacktestBatchForecasterMixin`` for batch prediction). The pipeline validates that the forecaster's prediction sample interval matches the configuration before running.

.. note::

   The ``ground_truth`` and ``predictors`` arguments are ``VersionedTimeSeriesDataset`` instances from ``openstef_core``. Versioned datasets track when each data point became available, which is what enables BEAM to enforce temporal consistency. See :doc:`core` for details on this data structure.


Evaluation
----------

Once backtesting produces predictions, the evaluation module segments them across multiple dimensions and computes performance metrics for each subset. This gives a much richer picture than a single aggregate score.

The evaluation module segments data along three axes:

- **Time windows** — Compare performance across days, weeks, or seasons
- **Lead times** — Measure how accuracy degrades from 1-hour to 48-hour ahead forecasts
- **Data filtering** — Focus on specific conditions such as peak hours or weekdays

.. code-block:: python

   from openstef_beam.evaluation import (
       EvaluationConfig,
       EvaluationPipeline,
       EvaluationReport,
   )

   eval_config = EvaluationConfig(
       windows=[...],          # Time-based segmentation
       filterings=[...],       # Conditional data filtering
       lead_time_groups=[...], # Lead time segmentation
   )

   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=my_quantiles,
       window_metric_providers=window_metrics,
       global_metric_providers=global_metrics,
   )

   # Evaluate backtest results
   report: EvaluationReport = eval_pipeline.run(backtest_results)

The ``EvaluationPipeline`` accepts pluggable **metric providers** — functions that compute specific metrics on each data subset. This lets you define custom metrics tailored to your operational requirements (e.g., peak load accuracy, ramp detection) alongside standard metrics like MAE and RMSE.

The output is an ``EvaluationReport`` containing ``EvaluationSubsetReport`` objects, each holding the computed ``SubsetMetric`` values for a particular combination of window, filtering, and lead time.


Analysis
--------

Raw metrics are difficult to interpret at scale. The analysis module transforms ``EvaluationReport`` data into visualizations and summary reports that support decision-making.

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig, AnalysisPipeline
   from openstef_beam.analysis.visualizations import VisualizationProvider

   analysis_config = AnalysisConfig(
       visualization_providers=[
           my_lead_time_chart_provider,
           my_seasonal_heatmap_provider,
       ],
   )

   analysis_pipeline = AnalysisPipeline(config=analysis_config)

   # Generate visualizations for a single target
   outputs = analysis_pipeline.run_single(report, target_metadata)

   # Generate comparative visualizations across multiple targets
   outputs = analysis_pipeline.run_group(reports, group_metadata)

The ``AnalysisPipeline`` processes reports at two aggregation levels:

- **Individual targets** — Detailed visualizations for a single forecasting target
- **Target groups** — Comparative visualizations across multiple targets within a group

Visualization providers are pluggable: you implement the ``VisualizationProvider`` interface to create any chart or report format your organization needs.


Benchmarking
------------

The benchmarking module ties everything together. ``BenchmarkPipeline`` orchestrates the complete workflow — backtesting, evaluation, and analysis — across multiple forecasting targets and models, managing parallel execution and result storage.

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkPipeline

   benchmark = BenchmarkPipeline(
       backtest_config=backtest_config,
       evaluation_config=eval_config,
       analysis_config=analysis_config,
       target_provider=my_target_provider,
       forecaster_factory=my_forecaster_factory,
       storage=my_storage,
   )

   benchmark.run()

The benchmark pipeline follows this workflow for each target:

1. Retrieve targets from a configurable ``TargetProvider`` (with optional filtering)
2. Create target-specific forecasters via a factory pattern
3. Run backtesting to generate predictions
4. Evaluate predictions against ground truth
5. Generate analysis visualizations
6. Store all results via ``BenchmarkStorage``

For comparing multiple model variants, ``BenchmarkComparisonPipeline`` analyzes results from multiple benchmark runs side-by-side:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkComparisonPipeline

   comparison = BenchmarkComparisonPipeline(
       run_names=["baseline_v1", "improved_v2"],
       storage=my_storage,
       analysis_config=comparison_analysis_config,
   )

   comparison.run()

This is particularly useful for:

- Comparing model variants with different hyperparameters or algorithms
- Evaluating performance before and after model updates
- A/B testing of forecasting approaches
- Cross-validation analysis across different time periods

The comparison pipeline operates on existing benchmark results, so you can perform retrospective analysis without re-running expensive backtests.


Dependencies on Core and Models
-------------------------------

BEAM is intentionally separated from the core data structures and model implementations, depending on them through well-defined interfaces:

- **From** ``openstef_core``: ``VersionedTimeSeriesDataset`` provides the temporal versioning that makes realistic backtesting possible. ``BaseConfig`` (via Pydantic) is used for all configuration classes. See :doc:`core` for details.

- **From** ``openstef_models``: Forecaster implementations that satisfy the ``BacktestForecasterMixin`` interface. The transforms and model architectures described in :doc:`models` are what BEAM evaluates.

This separation means you can use BEAM to evaluate *any* forecasting model — not just those built with ``openstef_models`` — as long as it implements the required mixin interface.

.. warning::

   BEAM's backtesting relies on ``VersionedTimeSeriesDataset`` to enforce temporal consistency. Using regular (non-versioned) datasets bypasses this protection and can lead to data leakage, producing evaluation results that do not reflect real-world performance.


Key Design Decisions
--------------------

**Pluggable providers everywhere.** Metric providers, visualization providers, target providers, and forecaster factories are all interfaces you implement. BEAM provides the orchestration; you provide the domain-specific logic.

**Separation of computation and presentation.** Evaluation produces raw numerical data. Analysis transforms it into visual outputs. This separation means you can re-analyze existing results with new visualizations without re-running backtests.

**Versioned data as a first-class concept.** By building on ``VersionedTimeSeriesDataset``, BEAM ensures that temporal consistency is enforced at the data layer rather than relying on careful coding practices.

**Configuration via Pydantic models.** All configuration classes (``BacktestConfig``, ``EvaluationConfig``, ``AnalysisConfig``) inherit from ``BaseConfig``, providing validation, serialization, and clear documentation of available options.