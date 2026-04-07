Backtesting Models
==================

Backtesting evaluates how well your forecasting models would have performed on historical data. This tutorial shows you how to run backtests, compare different models, and interpret performance metrics using OpenSTEF's backtesting framework.

Unlike simple train-test splits, OpenSTEF's backtesting simulates the operational environment where forecasts are generated at regular intervals with limited historical data availability. This realistic approach prevents data leakage and respects the temporal constraints of real-time forecasting systems.

What You'll Learn
-----------------

- How to configure and run backtests that simulate operational conditions
- Which evaluation metrics to use for energy forecasting
- How to compare multiple models systematically
- How to visualize and interpret backtest results

Before starting, make sure you've completed the :doc:`first_forecast` tutorial. You'll need historical data and a basic understanding of OpenSTEF's forecasting workflow.

Understanding Backtesting
-------------------------

A backtest simulates how your model would perform in production by:

1. **Generating predictions at regular intervals** - Just like in production, forecasts are created on a schedule (e.g., every 6 hours)
2. **Limiting available training data** - The model only sees data that would have been available at that point in time
3. **Retraining periodically** - Models are retrained at specified intervals to adapt to changing patterns
4. **Collecting predictions** - All forecasts are gathered for comprehensive evaluation

This approach reveals how models perform across different seasons, load patterns, and market conditions.

Running Your First Backtest
----------------------------

The ``BacktestPipeline`` orchestrates the entire backtesting process. You need three components: a configuration, a forecaster, and your historical data.

.. code-block:: python

   from datetime import datetime, timedelta, time
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.forecasting import XGBForecaster, ForecasterConfig
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Configure the backtesting schedule
   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(minutes=15),  # Output resolution
       predict_interval=timedelta(hours=6),  # Generate forecasts every 6 hours
       train_interval=timedelta(days=7),  # Retrain weekly
       align_time=time(0, 0)  # Align predictions to midnight
   )
   
   # Create a forecaster
   forecaster_config = ForecasterConfig(
       predict_horizon=timedelta(hours=47),
       predict_sample_interval=timedelta(minutes=15),
       target_column="load"
   )
   forecaster = XGBForecaster(config=forecaster_config)
   
   # Initialize the backtest pipeline
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster
   )
   
   # Run the backtest
   predictions = pipeline.run(
       ground_truth=historical_load_data,
       predictors=historical_features,
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
       show_progress=True
   )

The ``predictions`` object contains all forecasts generated during the backtest period, along with timestamps indicating when each forecast was created.

.. note::
   The ``prediction_sample_interval`` in your backtest config must match the ``predict_sample_interval`` in your forecaster config. OpenSTEF validates this to prevent configuration mismatches.

Evaluating Backtest Results
----------------------------

Once you have predictions, use the ``EvaluationPipeline`` to compute performance metrics. OpenSTEF provides metrics specifically designed for energy forecasting.

.. code-block:: python

   from openstef_beam.evaluation import EvaluationPipeline, EvaluationConfig
   from openstef_beam.metrics import mae, rmse, bias
   
   # Configure evaluation
   eval_config = EvaluationConfig(
       available_ats=[],  # Use all available predictions
       lead_times=[timedelta(hours=1), timedelta(hours=24), timedelta(hours=47)]
   )
   
   # Define metrics to compute
   metric_providers = [mae, rmse, bias]
   
   # Create evaluation pipeline
   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=None,  # For deterministic forecasts
       window_metric_providers=metric_providers,
       global_metric_providers=metric_providers
   )
   
   # Compute metrics
   evaluation_report = eval_pipeline.run(
       ground_truth=historical_load_data,
       predictions=predictions,
       target_column="load"
   )

Understanding Evaluation Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF provides several metrics for assessing forecast quality:

**Mean Absolute Error (MAE)**
   Measures average prediction error in the same units as your data. A MAE of 5.0 MW means predictions are off by 5 MW on average. Easy to interpret and robust to outliers.

**Root Mean Squared Error (RMSE)**
   Penalizes large errors more heavily than MAE. Useful when large forecast errors are particularly costly in your application.

**Bias**
   Shows systematic over- or under-prediction. Positive bias means the model consistently predicts too high, negative bias means too low.

**Skill Score**
   Compares your model against a baseline (often persistence or climatology). A skill score of 0.2 means your model is 20% better than the baseline.

The evaluation report contains metrics computed at different lead times and aggregation windows, allowing you to understand how performance varies across the forecast horizon.

Comparing Multiple Models
--------------------------

To find the best model for your use case, run backtests for multiple configurations and compare their performance.

.. code-block:: python

   # Define model configurations to compare
   models = {
       "xgb_default": XGBForecaster(config=ForecasterConfig(
           predict_horizon=timedelta(hours=47),
           predict_sample_interval=timedelta(minutes=15),
           target_column="load"
       )),
       "xgb_tuned": XGBForecaster(config=ForecasterConfig(
           predict_horizon=timedelta(hours=47),
           predict_sample_interval=timedelta(minutes=15),
           target_column="load",
           # Add custom hyperparameters
       )),
       "lgbm": LGBMForecaster(config=ForecasterConfig(
           predict_horizon=timedelta(hours=47),
           predict_sample_interval=timedelta(minutes=15),
           target_column="load"
       ))
   }
   
   # Run backtests for all models
   results = {}
   for name, forecaster in models.items():
       pipeline = BacktestPipeline(
           config=backtest_config,
           forecaster=forecaster
       )
       predictions = pipeline.run(
           ground_truth=historical_load_data,
           predictors=historical_features,
           start=datetime(2023, 1, 1),
           end=datetime(2023, 12, 31)
       )
       evaluation = eval_pipeline.run(
           ground_truth=historical_load_data,
           predictions=predictions,
           target_column="load"
       )
       results[name] = evaluation

Now you can compare metrics across models to identify the best performer.

Analyzing Performance Over Time
--------------------------------

Performance often varies across seasons, days of the week, or load conditions. Use windowed metrics to understand temporal patterns in forecast accuracy.

.. code-block:: python

   from openstef_beam.evaluation import Window
   
   # Configure evaluation with time windows
   eval_config = EvaluationConfig(
       available_ats=[],
       lead_times=[timedelta(hours=24)],
       windows=[
           Window(size=timedelta(days=7), step=timedelta(days=1))
       ]
   )
   
   eval_pipeline = EvaluationPipeline(
       config=eval_config,
       quantiles=None,
       window_metric_providers=metric_providers,
       global_metric_providers=metric_providers
   )
   
   evaluation_report = eval_pipeline.run(
       ground_truth=historical_load_data,
       predictions=predictions,
       target_column="load"
   )

The windowed metrics reveal how accuracy changes over time. You might discover that:

- Performance degrades in certain seasons
- Accuracy drops after several weeks without retraining
- Specific weather patterns challenge your model
- Weekend forecasts differ in quality from weekday forecasts

Visualizing Results
-------------------

While OpenSTEF focuses on computation rather than visualization, you can easily plot backtest results using standard Python libraries.

.. code-block:: python

   import matplotlib.pyplot as plt
   import pandas as pd
   
   # Extract predictions and ground truth
   pred_df = predictions.to_pandas()
   truth_df = historical_load_data.to_pandas()
   
   # Plot a sample period
   fig, ax = plt.subplots(figsize=(12, 6))
   ax.plot(truth_df.index, truth_df["load"], label="Actual", alpha=0.7)
   ax.plot(pred_df.index, pred_df["load"], label="Predicted", alpha=0.7)
   ax.set_xlabel("Time")
   ax.set_ylabel("Load (MW)")
   ax.set_title("Backtest Results: January 2023")
   ax.legend()
   plt.show()
   
   # Plot metric evolution over time
   windowed_metrics = evaluation_report.get_windowed_metrics()
   mae_over_time = [m.metrics["MAE"] for m in windowed_metrics]
   timestamps = [m.timestamp for m in windowed_metrics]
   
   fig, ax = plt.subplots(figsize=(12, 6))
   ax.plot(timestamps, mae_over_time)
   ax.set_xlabel("Time")
   ax.set_ylabel("MAE (MW)")
   ax.set_title("Forecast Accuracy Over Time")
   plt.show()

For more sophisticated analysis and visualization capabilities, see the ``AnalysisPipeline`` in the API documentation.

Best Practices
--------------

**Choose appropriate backtest periods**
   Use at least one full year of data to capture seasonal patterns. For critical applications, test across multiple years to ensure robustness.

**Match operational constraints**
   Set ``predict_interval`` and ``train_interval`` to match your production schedule. Testing with different intervals than you'll use in production gives misleading results.

**Evaluate at multiple lead times**
   Accuracy typically degrades with longer lead times. Evaluate performance at the specific horizons that matter for your application.

**Consider computational cost**
   Backtesting is computationally intensive. Start with shorter periods or fewer models when experimenting, then run comprehensive backtests for final model selection.

**Use versioned datasets**
   The ``VersionedTimeSeriesDataset`` ensures that backtesting respects data availability constraints, preventing unrealistic look-ahead bias.

Troubleshooting Common Issues
------------------------------

**ValueError: prediction sample intervals don't match**
   The ``prediction_sample_interval`` in ``BacktestConfig`` must equal the ``predict_sample_interval`` in ``ForecasterConfig``. Check both configurations.

**Backtest runs slowly**
   Reduce the backtest period, increase ``predict_interval``, or increase ``train_interval``. Each prediction and training operation takes time.

**Metrics are NaN**
   Check that your predictions and ground truth overlap in time and contain valid (non-NaN) values. Use ``allow_nan=True`` in metric functions if you want to skip missing values.

**Memory issues with large backtests**
   Process results in chunks or reduce the output resolution by increasing ``prediction_sample_interval``.

Next Steps
----------

Now that you understand backtesting, you can:

- Explore :doc:`advanced_customization` to create custom metrics or forecasters
- Review the API documentation for ``BacktestPipeline`` and ``EvaluationPipeline`` for advanced options
- Integrate backtesting into your model development workflow to systematically evaluate improvements

Backtesting is essential for building confidence in your forecasting models before deploying them to production. By simulating operational conditions and measuring performance across diverse scenarios, you ensure your models will perform reliably when it matters.