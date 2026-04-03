Backtesting Energy Forecasts
=============================

Backtesting evaluates how well your forecasting models would have performed in real operational conditions. Unlike simple train-test splits, backtesting simulates the actual forecasting workflow: making predictions at regular intervals with only historical data available at that moment, periodically retraining models, and respecting the temporal constraints of production systems.

This page shows you how to run backtests, evaluate model performance using energy-specific metrics, and compare different modeling approaches using historical data.

Why Backtest?
-------------

Backtesting answers critical questions about model reliability:

- **Operational realism**: Does the model perform well when retrained weekly with limited historical data, just like in production?
- **Temporal stability**: Does accuracy degrade over time, indicating the need for more frequent retraining?
- **Model comparison**: Which modeling approach works best for your specific forecasting problem?
- **Peak detection**: Can the model identify high-load events that might cause grid congestion?

The backtesting pipeline prevents data leakage by ensuring predictions only use information that would have been available at prediction time.

Basic Backtesting Workflow
---------------------------

The core backtesting workflow involves three components: a ``BacktestConfig`` that defines the simulation parameters, a forecaster implementing the backtesting interface, and the ``BacktestPipeline`` that orchestrates the simulation.

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.backtesting import BacktestPipeline, BacktestConfig
   from openstef_beam.backtesting.forecasters import OpenSTEF4BacktestForecaster
   from openstef_models.presets import create_forecasting_workflow
   from openstef_core.datasets import VersionedTimeSeriesDataset
   
   # Configure the backtesting simulation
   config = BacktestConfig(
       prediction_interval=timedelta(hours=1),  # Make predictions every hour
       prediction_sample_interval=timedelta(minutes=15),  # 15-min resolution
       training_interval=timedelta(days=7),  # Retrain weekly
       training_horizon=timedelta(days=90),  # Use 90 days of history
   )
   
   # Create a forecaster with your chosen workflow
   workflow = create_forecasting_workflow("xgboost")
   forecaster = OpenSTEF4BacktestForecaster(
       config=config,
       workflow_template=workflow,
   )
   
   # Run the backtest
   pipeline = BacktestPipeline(config=config, forecaster=forecaster)
   predictions = pipeline.run(
       ground_truth=ground_truth_data,  # VersionedTimeSeriesDataset with actual values
       predictors=feature_data,  # VersionedTimeSeriesDataset with features
       start=datetime(2023, 1, 1),
       end=datetime(2023, 12, 31),
   )

The pipeline returns predictions as a ``VersionedTimeSeriesDataset`` containing forecasts at all requested quantiles, aligned with the ground truth for easy evaluation.

.. note::
   The ``BacktestConfig`` parameters should match your production environment. If you retrain models daily in production, use ``training_interval=timedelta(days=1)`` in your backtest for realistic results.

Evaluating Model Performance
-----------------------------

OpenSTEF provides energy-specific metrics that account for the operational challenges of forecasting: varying load scales, peak detection requirements, and probabilistic uncertainty quantification.

Computing Metrics
^^^^^^^^^^^^^^^^^

After running a backtest, evaluate predictions using the metrics module:

.. code-block:: python

   from openstef_beam.metrics import rmae, mae, crps, confusion_matrix
   from openstef_core.types import Quantile
   
   # Extract actual values and median predictions
   y_true = predictions["target"].values
   y_pred = predictions[Quantile(0.5)].values  # Median forecast
   
   # Deterministic metrics
   mae_score = mae(y_true, y_pred)
   rmae_score = rmae(y_true, y_pred)  # Relative MAE, normalized by data range
   
   # Probabilistic metrics (requires multiple quantiles)
   quantiles = [Quantile(q) for q in [0.1, 0.25, 0.5, 0.75, 0.9]]
   quantile_predictions = {q: predictions[q].values for q in quantiles}
   crps_score = crps(y_true, quantile_predictions, quantiles)
   
   # Peak detection performance
   threshold = 0.8 * y_true.max()  # Define "peak" as 80% of maximum load
   cm = confusion_matrix(y_true, y_pred, threshold=threshold)
   print(f"Peak detection - Precision: {cm.precision:.2f}, Recall: {cm.recall:.2f}")

**Key metrics for energy forecasting:**

- **rMAE (relative MAE)**: Normalizes error by the data range, enabling comparison across different load scales
- **CRPS**: Evaluates the entire probabilistic forecast distribution, not just point predictions
- **Confusion matrix**: Measures how well the model detects high-load events that might require operational intervention

Comparing Multiple Models
--------------------------

To identify the best modeling approach, run backtests with different configurations and compare their performance:

.. code-block:: python

   from openstef_models.presets import create_forecasting_workflow
   
   # Define models to compare
   model_configs = {
       "xgboost": create_forecasting_workflow("xgboost"),
       "lightgbm": create_forecasting_workflow("lightgbm"),
       "linear": create_forecasting_workflow("linear"),
   }
   
   # Run backtests for each model
   results = {}
   for name, workflow in model_configs.items():
       forecaster = OpenSTEF4BacktestForecaster(
           config=config,
           workflow_template=workflow,
       )
       pipeline = BacktestPipeline(config=config, forecaster=forecaster)
       predictions = pipeline.run(
           ground_truth=ground_truth_data,
           predictors=feature_data,
           start=start_date,
           end=end_date,
       )
       
       # Compute metrics
       y_true = predictions["target"].values
       y_pred = predictions[Quantile(0.5)].values
       results[name] = {
           "MAE": mae(y_true, y_pred),
           "rMAE": rmae(y_true, y_pred),
           "CRPS": crps(y_true, {q: predictions[q].values for q in quantiles}, quantiles),
       }
   
   # Compare results
   import pandas as pd
   comparison = pd.DataFrame(results).T
   print(comparison.sort_values("rMAE"))

This comparison reveals which model architecture performs best for your specific forecasting problem and data characteristics.

Visualizing Performance Over Time
----------------------------------

Model performance often varies across seasons, times of day, or other temporal patterns. Analyze these trends by computing metrics over sliding windows:

.. code-block:: python

   import pandas as pd
   import matplotlib.pyplot as plt
   
   # Create time-indexed series
   df = pd.DataFrame({
       "actual": y_true,
       "predicted": y_pred,
       "timestamp": predictions.index,
   }).set_index("timestamp")
   
   # Compute rolling MAE (7-day window)
   df["absolute_error"] = (df["actual"] - df["predicted"]).abs()
   rolling_mae = df["absolute_error"].rolling("7D").mean()
   
   # Plot performance over time
   plt.figure(figsize=(12, 4))
   plt.plot(rolling_mae.index, rolling_mae.values)
   plt.xlabel("Date")
   plt.ylabel("7-Day Rolling MAE")
   plt.title("Model Performance Over Time")
   plt.grid(True, alpha=0.3)
   plt.show()

This visualization helps identify:

- **Performance degradation**: Increasing error over time suggests more frequent retraining is needed
- **Seasonal patterns**: Higher errors in certain seasons may indicate missing features or insufficient training data
- **Anomalous periods**: Sudden spikes in error often correspond to unusual events (holidays, weather extremes)

Advanced: Custom Forecasters
-----------------------------

For specialized modeling approaches, implement the ``BacktestForecasterMixin`` interface:

.. code-block:: python

   from openstef_beam.backtesting import BacktestForecasterMixin, BacktestForecasterConfig
   from openstef_core.base_model import BaseModel
   
   class CustomForecaster(BaseModel, BacktestForecasterMixin):
       """Custom forecaster for backtesting."""
       
       config: BacktestForecasterConfig
       
       def fit(self, data, target_metadata):
           """Train the model on historical data."""
           # Your training logic here
           pass
       
       def predict(self, data, target_metadata):
           """Generate predictions for the forecast horizon."""
           # Your prediction logic here
           return predictions  # VersionedTimeSeriesDataset

The backtesting pipeline will call ``fit()`` at each retraining interval and ``predict()`` at each prediction interval, simulating the operational workflow.

See the :doc:`advanced_customization` page for detailed examples of custom forecaster implementations.

Next Steps
----------

Now that you understand backtesting fundamentals:

- Explore :doc:`advanced_customization` for custom model architectures and feature engineering
- Review the API documentation for detailed metric definitions and configuration options
- Consider implementing automated backtesting in your CI/CD pipeline to catch performance regressions

Backtesting provides the confidence that your models will perform reliably when deployed to production systems.