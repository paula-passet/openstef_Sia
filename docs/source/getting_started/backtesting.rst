Backtesting Models
==================

Backtesting is the process of evaluating how your forecasting models would have performed on historical data. This tutorial shows you how to use OpenSTEF's backtesting tools to compare different models, understand their performance characteristics, and make informed decisions about which approach works best for your use case.

What is Backtesting?
--------------------

In energy forecasting, you need confidence that your models will perform well in production. Backtesting simulates the operational environment by:

- Generating forecasts at regular intervals using only data that would have been available at that time
- Preventing data leakage by respecting temporal boundaries
- Supporting periodic model retraining to reflect real-world workflows
- Collecting predictions alongside ground truth for comprehensive evaluation

This realistic simulation helps you understand model behavior before deployment and compare different modeling approaches on equal footing.

Setting Up a Backtest
---------------------

OpenSTEF provides the ``BacktestPipeline`` class to orchestrate backtesting workflows. You'll need three components: a configuration, a forecaster, and your historical data.

First, configure the backtesting parameters:

.. code-block:: python

   from openstef_beam.backtesting import BacktestConfig
   from datetime import timedelta
   
   config = BacktestConfig(
       prediction_sample_interval=timedelta(hours=1),  # Generate forecasts hourly
       training_sample_interval=timedelta(days=7),     # Retrain weekly
       training_horizon=timedelta(days=90),            # Use 90 days of history
   )

The ``prediction_sample_interval`` determines how often forecasts are generated, while ``training_sample_interval`` controls retraining frequency. The ``training_horizon`` specifies how much historical data to use for each training cycle.

Next, create a forecaster compatible with backtesting. OpenSTEF provides adapters for its standard workflows:

.. code-block:: python

   from openstef_beam.benchmarking import create_openstef4_preset_backtest_forecaster
   from openstef.workflow.config import ForecastingWorkflowConfig
   from pathlib import Path
   
   # Configure your forecasting workflow
   workflow_config = ForecastingWorkflowConfig(
       model_type="xgboost",
       horizon=timedelta(hours=48),
       resolution=timedelta(minutes=15),
       quantiles=[0.1, 0.5, 0.9],
   )
   
   # Create a backtest-compatible forecaster factory
   forecaster_factory = create_openstef4_preset_backtest_forecaster(
       workflow_config=workflow_config,
       cache_dir=Path("backtest_cache"),
   )

Running the Backtest
--------------------

With configuration and forecaster ready, initialize the pipeline and run the backtest:

.. code-block:: python

   from openstef_beam.backtesting import BacktestPipeline
   from datetime import datetime
   
   # Assume you have prepared your data
   # ground_truth: VersionedTimeSeriesDataset with actual load values
   # predictors: VersionedTimeSeriesDataset with weather and other features
   
   # Create a forecaster instance for your target
   forecaster = forecaster_factory(target_metadata)
   
   # Initialize the pipeline
   pipeline = BacktestPipeline(config=config, forecaster=forecaster)
   
   # Run the backtest
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True,
   )

The ``run`` method returns a ``TimeSeriesDataset`` containing all predictions made during the backtest period. Each prediction includes timestamp information and availability metadata, allowing you to analyze when forecasts were generated and what data was available.

.. note::

   The backtest pipeline automatically handles temporal consistency, ensuring that each forecast uses only data that would have been available at prediction time. This prevents data leakage and provides realistic performance estimates.

Evaluating Model Performance
-----------------------------

Once you have predictions, evaluate performance using OpenSTEF's metrics. The library provides both deterministic metrics (for point forecasts) and probabilistic metrics (for quantile forecasts).

Common deterministic metrics include:

- **MAE (Mean Absolute Error)**: Average absolute difference between predictions and actuals
- **RMSE (Root Mean Squared Error)**: Square root of average squared errors, penalizing large errors more heavily
- **MAPE (Mean Absolute Percentage Error)**: Relative errors as percentages
- **R² (Coefficient of Determination)**: Proportion of variance explained by the model

For probabilistic forecasts, you can evaluate:

- **Quantile Loss**: Measures accuracy at specific quantiles
- **CRPS (Continuous Ranked Probability Score)**: Overall probabilistic forecast quality
- **Calibration**: Whether prediction intervals contain actual values at the expected rate

OpenSTEF provides metric providers that compute these automatically:

.. code-block:: python

   from openstef_beam.metrics import MAEProvider, RMSEProvider, MAPEProvider
   from openstef_beam.evaluation import evaluate_forecast
   
   # Define which metrics to compute
   metric_providers = [
       MAEProvider(),
       RMSEProvider(),
       MAPEProvider(),
   ]
   
   # Evaluate the backtest results
   evaluation_report = evaluate_forecast(
       predictions=predictions,
       ground_truth=ground_truth,
       metric_providers=metric_providers,
   )

The evaluation report contains computed metrics that you can analyze or visualize.

Comparing Multiple Models
--------------------------

A key use case for backtesting is comparing different modeling approaches. You might want to compare:

- Different model types (XGBoost vs. LightGBM vs. ensemble)
- Different feature sets or preprocessing approaches
- Different hyperparameter configurations
- Different training horizons or retraining frequencies

To compare models, run separate backtests for each configuration and collect the results:

.. code-block:: python

   # Run backtests for different models
   results = {}
   
   for model_name, model_config in model_configurations.items():
       forecaster_factory = create_openstef4_preset_backtest_forecaster(
           workflow_config=model_config,
           cache_dir=Path(f"cache/{model_name}"),
       )
       
       forecaster = forecaster_factory(target_metadata)
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       
       predictions = pipeline.run(
           ground_truth=ground_truth,
           predictors=predictors,
           start=start_date,
           end=end_date,
       )
       
       results[model_name] = evaluate_forecast(
           predictions=predictions,
           ground_truth=ground_truth,
           metric_providers=metric_providers,
       )

With evaluation reports for each model, you can systematically compare performance characteristics and identify the best approach for your use case.

Visualizing Backtest Results
-----------------------------

OpenSTEF includes built-in visualization tools specifically designed for backtesting analysis. These visualizations help you understand model performance across different dimensions.

**Grouped Target Metric Visualization** compares metrics across different targets or model runs:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   from openstef_beam.analysis.visualizations import GroupedTargetMetricVisualization
   from openstef_core.types import Quantile
   
   analysis_config = AnalysisConfig(
       visualization_providers=[
           GroupedTargetMetricVisualization(
               name="rmae_comparison",
               metric="rMAE",
               quantile=Quantile(0.5),
           ),
           GroupedTargetMetricVisualization(
               name="rcrps_comparison",
               metric="rCRPS",
           ),
       ],
   )

This creates bar charts showing metric values for each model or target, with color-coded grouping for easy identification.

**Windowed Metric Visualization** shows how performance evolves over time:

.. code-block:: python

   from openstef_beam.analysis.visualizations import WindowedMetricVisualization
   from openstef_beam.evaluation import Window
   from datetime import timedelta
   
   analysis_config = AnalysisConfig(
       visualization_providers=[
           WindowedMetricVisualization(
               name="mae_evolution",
               metric="MAE",
               window=Window(size=timedelta(days=30)),
           ),
       ],
   )

This creates time series plots showing metric values computed over sliding windows, revealing performance trends, seasonal patterns, and periods where accuracy degrades.

**Precision-Recall Curves** evaluate event detection performance, useful for congestion management:

.. code-block:: python

   from openstef_beam.analysis.visualizations import PrecisionRecallCurveVisualization
   
   analysis_config = AnalysisConfig(
       visualization_providers=[
           PrecisionRecallCurveVisualization(
               name="precision_recall",
               threshold_column="congestion_threshold",
           ),
       ],
   )

These visualizations help you identify which models perform best, understand performance stability, and communicate results to stakeholders.

Interpreting Results
--------------------

When analyzing backtest results, consider multiple dimensions:

**Accuracy**: Lower MAE and RMSE indicate better point forecast accuracy. However, no single metric tells the whole story—use multiple metrics to get a complete picture.

**Stability**: Check how performance varies over time using windowed visualizations. Models that maintain consistent accuracy are often preferable to those with occasional excellent performance but frequent failures.

**Calibration**: For probabilistic forecasts, verify that prediction intervals are well-calibrated. A 90% prediction interval should contain the actual value approximately 90% of the time.

**Operational Relevance**: Consider which errors matter most for your use case. Peak detection might be more important than average accuracy if you're managing grid congestion.

Next Steps
----------

Now that you understand backtesting, you can:

- Experiment with different model configurations to find optimal settings
- Use backtesting to validate models before production deployment
- Set up automated backtesting pipelines for continuous model evaluation

For more advanced workflows, see :doc:`advanced_customization` to learn how to customize forecasting pipelines with your own components.

To understand the complete forecasting workflow from data preparation through deployment, refer back to :doc:`first_forecast` for step-by-step guidance.