Backtesting Models
==================

Backtesting validates forecasting models by simulating how they would perform in real operational conditions. OpenSTEF's backtesting framework generates predictions at regular intervals using only historical data that would have been available at each prediction time, preventing data leakage and ensuring realistic performance estimates.

This tutorial shows how to backtest models, evaluate their performance using multiple metrics, and compare different model configurations to identify the best approach for your forecasting task.

Understanding Backtesting
-------------------------

Unlike simple train-test splits, backtesting simulates the operational forecasting environment:

- **Temporal consistency**: Predictions use only data available before the prediction time
- **Periodic retraining**: Models retrain at configurable intervals, mimicking production schedules
- **Realistic evaluation**: Performance metrics reflect what you'd see in deployment

The backtesting pipeline processes events chronologically, alternating between training and prediction operations while respecting data availability constraints.

Setting Up a Backtest
---------------------

Backtesting requires three components: historical data, a configured forecaster, and a backtest configuration that defines prediction and training schedules.

.. code-block:: python

   from datetime import datetime, timedelta
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.forecasting import Forecaster, ForecasterConfig
   from openstef_core.data import VersionedTimeSeriesDataset
   
   # Configure the forecaster
   forecaster_config = ForecasterConfig(
       predict_sample_interval=timedelta(hours=1),
       horizon=timedelta(hours=47),
       training_horizons=[timedelta(hours=0.25), timedelta(hours=47)],
   )
   forecaster = Forecaster(config=forecaster_config)
   
   # Configure the backtest
   backtest_config = BacktestConfig(
       prediction_sample_interval=timedelta(hours=1),
       prediction_interval=timedelta(hours=6),
       training_interval=timedelta(days=1),
   )
   
   # Create the pipeline
   pipeline = BacktestPipeline(
       config=backtest_config,
       forecaster=forecaster,
   )

The ``prediction_interval`` determines how often forecasts are generated (every 6 hours in this example), while ``training_interval`` controls retraining frequency (daily). The ``prediction_sample_interval`` must match the forecaster's configuration.

Running the Backtest
--------------------

Execute the backtest by providing ground truth data and predictors over your evaluation period:

.. code-block:: python

   # Prepare your data
   ground_truth = VersionedTimeSeriesDataset(...)  # Historical target values
   predictors = VersionedTimeSeriesDataset(...)    # Feature data
   
   # Run the backtest
   predictions = pipeline.run(
       ground_truth=ground_truth,
       predictors=predictors,
       start=datetime(2024, 1, 1),
       end=datetime(2024, 3, 31),
       show_progress=True,
   )

The pipeline returns a ``VersionedTimeSeriesDataset`` containing all predictions with timestamps and availability information. Each prediction includes forecasts for all horizons specified in the forecaster configuration.

Evaluating Performance
----------------------

OpenSTEF provides comprehensive metrics for evaluating forecast quality. The evaluation system supports both deterministic metrics (MAE, RMSE) and probabilistic metrics for quantile forecasts.

Basic Metrics
^^^^^^^^^^^^^

Calculate standard error metrics using the evaluation module:

.. code-block:: python

   from openstef_beam.evaluation.metrics import mae, rmae
   import numpy as np
   
   # Extract predictions for a specific horizon
   y_true = ground_truth.get_values()
   y_pred = predictions.get_values()
   
   # Calculate metrics
   mae_score = mae(y_true, y_pred)
   rmae_score = rmae(y_true, y_pred)
   
   print(f"MAE: {mae_score:.2f}")
   print(f"rMAE: {rmae_score:.3f}")

The relative MAE (rMAE) normalizes errors by the data range, making it easier to compare performance across different targets or time periods.

Comprehensive Evaluation Reports
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For detailed analysis, use metric providers to compute multiple metrics simultaneously:

.. code-block:: python

   from openstef_beam.evaluation import (
       MAEProvider,
       RMAEProvider,
       MAPEProvider,
       R2Provider,
   )
   
   # Define metrics to compute
   metric_providers = [
       MAEProvider(),
       RMAEProvider(),
       MAPEProvider(),
       R2Provider(),
   ]
   
   # Compute all metrics
   results = {}
   for provider in metric_providers:
       metrics = provider.compute_deterministic(
           y_true=y_true,
           y_pred=y_pred,
           quantile=0.5,  # For median forecast
       )
       results.update(metrics)
   
   # Display results
   for metric_name, value in results.items():
       print(f"{metric_name}: {value:.4f}")

This approach scales well when evaluating multiple models or configurations.

Comparing Multiple Models
-------------------------

To identify the best model, run backtests for different configurations and compare their performance:

.. code-block:: python

   from openstef_beam.analysis import WindowedMetricPlotter
   
   # Define model configurations to compare
   models = {
       "XGBoost": ForecasterConfig(
           predict_sample_interval=timedelta(hours=1),
           horizon=timedelta(hours=47),
       ),
       "LightGBM": ForecasterConfig(
           predict_sample_interval=timedelta(hours=1),
           horizon=timedelta(hours=47),
           # Different hyperparameters...
       ),
   }
   
   # Run backtests for each model
   model_predictions = {}
   for name, config in models.items():
       forecaster = Forecaster(config=config)
       pipeline = BacktestPipeline(
           config=backtest_config,
           forecaster=forecaster,
       )
       model_predictions[name] = pipeline.run(
           ground_truth=ground_truth,
           predictors=predictors,
           start=datetime(2024, 1, 1),
           end=datetime(2024, 3, 31),
       )
   
   # Calculate metrics for each model
   model_metrics = {}
   for name, preds in model_predictions.items():
       y_pred = preds.get_values()
       model_metrics[name] = {
           "MAE": mae(y_true, y_pred),
           "rMAE": rmae(y_true, y_pred),
       }

Visualizing Performance
-----------------------

OpenSTEF includes built-in visualization tools for analyzing backtest results. The ``WindowedMetricPlotter`` shows how performance evolves over time:

.. code-block:: python

   from datetime import datetime
   
   plotter = WindowedMetricPlotter()
   
   # Add each model's performance over time
   for model_name, preds in model_predictions.items():
       timestamps = preds.get_timestamps()
       y_pred = preds.get_values()
       
       # Calculate MAE for each time window
       mae_values = []
       for i in range(len(timestamps)):
           mae_values.append(mae(y_true[i], y_pred[i]))
       
       plotter.add_model(model_name, timestamps, mae_values)
   
   # Configure and generate plot
   plotter.set_window_size("1D")
   fig = plotter.plot(
       title="Model Performance Over Time",
       metric_name="MAE",
   )

This visualization reveals:

- Performance trends and stability over time
- Seasonal patterns affecting forecast accuracy
- Periods where specific models excel or struggle
- Optimal retraining intervals based on performance degradation

For grouped analysis across multiple targets, use ``GroupedTargetMetricVisualization`` to compare performance across different prediction scenarios or target categories.

Advanced Evaluation Strategies
-------------------------------

Peak Hours Analysis
^^^^^^^^^^^^^^^^^^^

Energy forecasting often requires special attention to peak demand periods. Evaluate performance during specific hours:

.. code-block:: python

   from openstef_beam.evaluation import RMAEPeakHoursProvider
   
   # Calculate metrics for peak hours only (8:00-20:00)
   peak_provider = RMAEPeakHoursProvider()
   peak_metrics = peak_provider.compute_deterministic(
       y_true=y_true,
       y_pred=y_pred,
       quantile=0.5,
   )

This helps ensure your model performs well during the most critical operational periods.

Windowed Evaluation
^^^^^^^^^^^^^^^^^^^

Analyze how performance changes over different time windows to identify when models need retraining:

.. code-block:: python

   from openstef_beam.evaluation import Window
   from datetime import timedelta
   
   # Define evaluation windows
   window = Window(size=timedelta(days=7))
   
   # Calculate metrics for each window
   window_metrics = []
   for start_time in window.iterate(start, end):
       window_end = start_time + window.size
       
       # Extract data for this window
       mask = (timestamps >= start_time) & (timestamps < window_end)
       window_true = y_true[mask]
       window_pred = y_pred[mask]
       
       # Calculate metrics
       window_metrics.append({
           "start": start_time,
           "mae": mae(window_true, window_pred),
           "rmae": rmae(window_true, window_pred),
       })

This rolling window analysis identifies performance degradation patterns and optimal retraining schedules.

Best Practices
--------------

**Choose appropriate backtest periods**: Use at least several months of data to capture seasonal variations and different operational conditions.

**Match operational constraints**: Configure prediction and training intervals to match your production deployment schedule.

**Evaluate multiple metrics**: No single metric tells the whole story. Use MAE for absolute errors, rMAE for relative performance, and R² for explained variance.

**Consider computational cost**: Frequent retraining improves accuracy but increases computational requirements. Balance performance gains against operational constraints.

**Validate across different periods**: Test on multiple time ranges to ensure consistent performance across different seasons and conditions.

Next Steps
----------

Now that you understand backtesting, explore:

- :doc:`advanced_customization` for custom model architectures and feature engineering
- The evaluation API reference for detailed metric documentation
- The visualization guide for advanced plotting options

For questions about specific metrics or evaluation strategies, consult the API reference or the OpenSTEF community resources.