Quantiles and Confidence in Forecasting
========================================

Energy forecasting is inherently uncertain. Weather predictions change, consumption patterns vary, and unexpected events occur. Rather than providing a single point estimate that will almost certainly be wrong, OpenSTEF generates **probabilistic forecasts** that quantify this uncertainty through quantiles.

This page explains what quantiles are, how to interpret them, and why they matter for operational decision-making in energy systems.

What Are Quantiles?
-------------------

A quantile represents a threshold value with a specific probability. The **P50 quantile** (also called the median) is the value that actual load has a 50% chance of exceeding. The **P90 quantile** means there's only a 10% chance the actual load will exceed this value.

In OpenSTEF, forecasts typically include multiple quantiles:

- **P10**: Conservative lower bound (90% chance actual load exceeds this)
- **P50**: Median forecast (50% chance of exceedance)
- **P90**: Conservative upper bound (10% chance actual load exceeds this)

These quantiles form a probabilistic forecast that captures the full range of likely outcomes, not just a single prediction.

.. note:: [DIAGRAM: Bell curve showing probability distribution with P10, P50, P90 marked as vertical lines, shaded areas showing probability regions]

Confidence Intervals vs Prediction Intervals
---------------------------------------------

It's critical to distinguish between two types of intervals:

**Prediction intervals** (what OpenSTEF provides) capture uncertainty in future observations. They answer: "Where will the actual load likely fall?" These intervals are wide because they include both model uncertainty and natural variability in the system.

**Confidence intervals** capture uncertainty in model parameters. They answer: "How certain are we about the model's average prediction?" These are typically much narrower and less relevant for operational decisions.

OpenSTEF's quantile forecasts represent prediction intervals. When you see P10 to P90, you're looking at the range where you expect 80% of actual observations to fall, accounting for all sources of uncertainty.

Working with Quantile Forecasts
--------------------------------

OpenSTEF models output quantile predictions in a structured format. Here's how to access and work with them:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset
   import pandas as pd
   
   # Forecast data includes multiple quantiles
   forecast_data = pd.DataFrame({
       'forecast': pd.date_range('2025-01-01', periods=48, freq='15min'),
       'quantile_P10': [95, 98, 102, ...],
       'quantile_P50': [110, 115, 120, ...],
       'quantile_P90': [125, 132, 138, ...],
   })
   
   # Create a ForecastDataset
   dataset = ForecastDataset(
       forecast_data,
       sample_interval=pd.Timedelta(minutes=15)
   )
   
   # Access quantile information
   print(f"Available quantiles: {dataset.quantiles}")
   # Output: [0.1, 0.5, 0.9]
   
   # Extract specific quantile for analysis
   median_forecast = forecast_data['quantile_P50']
   upper_bound = forecast_data['quantile_P90']

The quantile columns follow the naming convention ``quantile_PXX`` where XX is the percentile (10, 50, 90, etc.).

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different quantiles. Using the wrong quantile can lead to costly mistakes:

**Capacity planning and reserve scheduling**: Use P90 or higher quantiles. The cost of insufficient capacity (load shedding, emergency purchases) far exceeds the cost of slight over-preparation. Grid operators typically plan for high quantiles to maintain reliability.

**Energy trading and market bidding**: Use P50 (median) forecasts. Over time, the median minimizes average forecast error. Consistently bidding too high or too low based on extreme quantiles leads to systematic losses.

**Renewable integration**: Use multiple quantiles to assess risk. Solar and wind forecasts with wide P10-P90 ranges indicate high uncertainty, signaling the need for additional reserves or flexible backup generation.

**Maintenance scheduling**: Use lower quantiles (P10-P30) to identify low-demand periods. Scheduling maintenance during periods that are likely to have low load reduces the risk of capacity shortfalls.

.. code-block:: python

   # Example: Risk-based decision making
   import pandas as pd
   
   def assess_maintenance_window(forecast_df, capacity_limit):
       """Identify safe maintenance windows using quantile forecasts."""
       
       # Use P90 to be conservative - only 10% chance of exceeding this
       high_confidence_forecast = forecast_df['quantile_P90']
       
       # Find periods where even the P90 is below capacity limit
       safe_windows = forecast_df[high_confidence_forecast < capacity_limit * 0.8]
       
       # Calculate uncertainty width
       forecast_df['uncertainty'] = (
           forecast_df['quantile_P90'] - forecast_df['quantile_P10']
       )
       
       # Prefer windows with low uncertainty
       best_windows = safe_windows.nsmallest(10, 'uncertainty')
       
       return best_windows

Interpreting Forecast Uncertainty
----------------------------------

The width of the quantile range tells you about forecast confidence. A narrow range (P90 close to P10) indicates high confidence. A wide range indicates high uncertainty.

Several factors drive forecast uncertainty:

**Weather forecast uncertainty**: When weather models disagree or conditions are unstable, quantile ranges widen. This is especially pronounced for renewable energy forecasts.

**Limited historical data**: Forecasts for new systems or unusual conditions have wider quantile ranges because the model has less training data to learn from.

**Forecast horizon**: Uncertainty typically increases with horizon. A 1-hour-ahead forecast is more confident than a 48-hour-ahead forecast.

**Time of day and season**: Quantile ranges often narrow during stable periods (e.g., overnight baseload) and widen during volatile periods (e.g., evening peak with variable weather).

.. code-block:: python

   # Analyzing forecast uncertainty over time
   import matplotlib.pyplot as plt
   
   def plot_forecast_uncertainty(forecast_df):
       """Visualize forecast with uncertainty bands."""
       
       fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
       
       # Plot forecast with uncertainty bands
       ax1.fill_between(
           forecast_df.index,
           forecast_df['quantile_P10'],
           forecast_df['quantile_P90'],
           alpha=0.3,
           label='80% prediction interval (P10-P90)'
       )
       ax1.plot(
           forecast_df.index,
           forecast_df['quantile_P50'],
           label='Median forecast (P50)',
           linewidth=2
       )
       ax1.set_ylabel('Load (MW)')
       ax1.legend()
       ax1.set_title('Probabilistic Forecast')
       
       # Plot uncertainty width over time
       uncertainty = forecast_df['quantile_P90'] - forecast_df['quantile_P10']
       ax2.plot(forecast_df.index, uncertainty, color='red')
       ax2.set_ylabel('Uncertainty Width (MW)')
       ax2.set_xlabel('Time')
       ax2.set_title('Forecast Uncertainty Over Time')
       
       plt.tight_layout()
       return fig

Quantile Calibration
---------------------

Well-calibrated quantiles are essential for reliable decision-making. A calibrated P90 quantile should be exceeded by actual values approximately 10% of the time—no more, no less.

OpenSTEF includes calibration tools to ensure quantile forecasts are reliable. The ``IsotonicQuantileRegressor`` transform learns a monotonic mapping from raw model quantiles to calibrated values:

.. code-block:: python

   from openstef_core.transforms import IsotonicQuantileRegressor
   
   # Calibrate quantile forecasts using validation data
   calibrator = IsotonicQuantileRegressor(
       quantiles=[0.1, 0.5, 0.9],
       y_min=0,  # Physical constraint: load cannot be negative
   )
   
   # Fit on validation data
   calibrator.fit(validation_predictions, validation_actuals)
   
   # Apply to new forecasts
   calibrated_forecasts = calibrator.transform(raw_forecasts)

Calibration is particularly important when:

- Models are trained on limited historical data
- The system characteristics have changed since training
- You're using ensemble methods that may not be naturally calibrated

Evaluating Quantile Quality
----------------------------

OpenSTEF provides metrics specifically designed for probabilistic forecasts. Unlike point forecast metrics (MAE, RMSE), these evaluate whether quantiles accurately represent uncertainty:

**Quantile score**: Asymmetric loss function that penalizes over- and under-prediction differently based on the quantile level. Lower is better.

**Calibration plots**: Compare forecasted probabilities to observed frequencies. Points should fall along the diagonal for well-calibrated forecasts.

**Coverage analysis**: Check whether the actual values fall within the predicted intervals at the expected rate (e.g., 80% of actuals should fall between P10 and P90).

.. code-block:: python

   from openstef_beam.evaluation import EvaluationSubsetReport
   
   # Evaluation report includes quantile metrics
   report = EvaluationSubsetReport(
       predictions=forecast_df,
       target_series=actual_load,
       quantiles=[0.1, 0.5, 0.9]
   )
   
   # Extract quantile predictions for analysis
   quantile_preds = report.get_quantile_predictions()
   
   # Metrics are computed per quantile
   # Check if P90 is exceeded ~10% of the time
   p90_exceedances = (actual_load > quantile_preds['quantile_P90']).mean()
   print(f"P90 exceedance rate: {p90_exceedances:.1%}")
   # Target: ~10%

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting fundamentals
- :doc:`model_selection` - Choosing models that provide good quantile estimates
- :doc:`reliability_and_fallback` - Handling cases when quantile forecasts fail

For API details on working with quantile data structures, see the :doc:`../api/index` reference.