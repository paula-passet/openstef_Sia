Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasting provides more than just a single predicted value—it quantifies uncertainty by predicting a range of possible outcomes. This page explains how OpenSTEF uses quantiles to represent forecast uncertainty, how to interpret them for operational decisions, and the difference between confidence and prediction intervals.

What Are Quantiles?
-------------------

A quantile represents a threshold where a certain percentage of outcomes fall below that value. In forecasting, quantiles describe the probability distribution of future energy demand or generation.

Common quantiles used in energy forecasting:

- **0.1 (P10)**: 10% of outcomes fall below this value; 90% fall above
- **0.5 (P50)**: The median—half of outcomes fall below, half above
- **0.9 (P90)**: 90% of outcomes fall below this value; 10% fall above

For example, if a P90 forecast predicts 500 MW, there's only a 10% chance demand will exceed 500 MW. This helps operators plan for high-demand scenarios while avoiding over-provisioning.

.. note::
   OpenSTEF models predict multiple quantiles simultaneously using quantile regression. The P50 (median) serves as the primary point forecast, while other quantiles define uncertainty bands.

Why Quantiles Matter for Operations
------------------------------------

Point forecasts alone don't capture the risk of forecast errors. Quantiles enable risk-aware decision-making:

**Capacity planning**: Use P90 forecasts to ensure sufficient capacity for high-demand scenarios without excessive over-provisioning.

**Trading and scheduling**: Balance expected outcomes (P50) against worst-case scenarios (P10/P90) to optimize bidding strategies.

**Reliability assessment**: Monitor whether actual outcomes fall within predicted quantile ranges to validate model calibration.

**Fallback triggering**: Set thresholds based on quantile spread—when uncertainty is too high, trigger fallback strategies (see :doc:`reliability_and_fallback`).

Prediction Intervals vs Confidence Intervals
---------------------------------------------

These terms are often confused but represent fundamentally different concepts:

**Prediction intervals** describe where future observations will fall. A 90% prediction interval (from P05 to P95) means 90% of future measurements should fall within this range. This accounts for both model uncertainty and natural variability in the data.

**Confidence intervals** describe uncertainty about model parameters or the mean prediction. They answer "how confident are we about the average outcome?" rather than "where will individual outcomes fall?"

For operational energy forecasting, **prediction intervals are what matter**. Operators need to know the range of possible demand values, not the uncertainty about the average demand.

OpenSTEF focuses on prediction intervals through quantile forecasting. Each quantile prediction represents a boundary of the prediction interval at a specific confidence level.

Interpreting Quantile Forecasts
--------------------------------

When you generate forecasts with OpenSTEF, you receive predictions for multiple quantiles. Here's how to interpret them:

.. code-block:: python

   from openstef_core.model import QuantileOpenstfRegressor
   from openstef_core.datasets import ForecastInputDataset
   import pandas as pd
   
   # Train a quantile forecasting model
   model = QuantileOpenstfRegressor(
       quantiles=[0.1, 0.25, 0.5, 0.75, 0.9],
       learner="XGBRegressor"
   )
   
   # After fitting and predicting (see model_selection for details)
   # predictions is a DataFrame with columns for each quantile
   
   # The P50 (median) is your primary point forecast
   point_forecast = predictions["quantile_0.5"]
   
   # The P10-P90 range gives an 80% prediction interval
   lower_bound = predictions["quantile_0.1"]
   upper_bound = predictions["quantile_0.9"]
   uncertainty_range = upper_bound - lower_bound
   
   # Wide intervals indicate high uncertainty
   # Narrow intervals indicate confident predictions

The width of the quantile spread reveals forecast confidence. During stable conditions with good historical data, quantiles cluster tightly. During volatile periods or with limited training data, quantiles spread wider.

Visualizing Uncertainty
------------------------

OpenSTEF provides built-in visualization tools for quantile forecasts. The ``ForecastTimeSeriesPlotter`` displays forecasts with shaded uncertainty bands:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter
   import pandas as pd
   
   # Create plotter and add measurements
   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(actual_load_series)
   
   # Add model forecasts with quantiles
   # quantile_data is a DataFrame with columns: quantile_0.1, quantile_0.5, quantile_0.9
   plotter.add_model(
       model_name="XGBoost",
       forecast=quantile_data["quantile_0.5"],  # median forecast
       quantiles=quantile_data  # all quantiles for uncertainty bands
   )
   
   # Generate interactive plot
   fig = plotter.plot(title="Load Forecast with Uncertainty")
   fig.show()

The resulting plot shows:

- Actual measurements as a line
- Median forecast (P50) as the central prediction
- Shaded bands representing quantile ranges (darker shading = higher confidence)
- Interactive hover information for detailed inspection

This visualization immediately reveals whether uncertainty bands contain actual outcomes and where models struggle with accuracy.

Validating Quantile Calibration
--------------------------------

Well-calibrated quantiles are crucial for reliable decision-making. A calibrated P90 forecast should be exceeded by actual values only 10% of the time. If actual values exceed P90 predictions 30% of the time, the model underestimates uncertainty.

OpenSTEF provides the ``QuantileProbabilityPlotter`` to validate calibration:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   from openstef_core.types import Quantile
   
   plotter = QuantileProbabilityPlotter()
   
   # Compare forecasted quantiles to observed frequencies
   # forecasted: the quantiles you predicted (e.g., [0.1, 0.5, 0.9])
   # observed: the actual empirical quantiles from validation data
   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.9)]
   observed = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.88)]
   
   plotter.add_model("XGBoost", forecasted, observed)
   
   fig = plotter.plot(title="Forecast Calibration Analysis")
   fig.show()

The calibration plot shows forecasted probabilities versus observed frequencies. Points near the diagonal line indicate good calibration. Systematic deviations reveal bias:

- Points above the diagonal: model underestimates uncertainty (too confident)
- Points below the diagonal: model overestimates uncertainty (too conservative)

Improving Quantile Predictions
-------------------------------

If your quantile forecasts are poorly calibrated or too wide, consider:

**Feature engineering**: Better predictors reduce uncertainty. Weather forecasts, calendar features, and recent load patterns significantly improve quantile accuracy. See :doc:`feature_engineering` for guidance.

**Model selection**: Some algorithms handle uncertainty better than others. Gradient boosting models (XGBoost, LightGBM) typically produce well-calibrated quantiles. See :doc:`model_selection` for comparisons.

**Quantile calibration**: OpenSTEF includes ``IsotonicQuantileCalibrationTransform`` to post-process quantile predictions, ensuring they match empirical frequencies in validation data. This learns a monotonic mapping from predicted to calibrated quantiles.

**More training data**: Quantile accuracy improves with more historical observations, especially for extreme quantiles like P05 and P95.

Quantiles in the Forecasting Pipeline
--------------------------------------

OpenSTEF models generate quantile predictions throughout the forecasting workflow:

1. **Training**: Models learn to predict multiple quantiles simultaneously using quantile regression loss functions
2. **Prediction**: Each forecast generates values for all configured quantiles
3. **Evaluation**: Metrics like quantile score assess both accuracy and calibration
4. **Visualization**: Built-in plotters display uncertainty bands alongside point forecasts
5. **Decision-making**: Downstream systems use quantiles for risk-aware operational decisions

For the complete forecasting workflow, see :doc:`forecasting_basics`. For production considerations around forecast reliability, see :doc:`reliability_and_fallback`.

Practical Considerations
-------------------------

**Quantile selection**: Choose quantiles based on operational needs. Common choices include [0.1, 0.5, 0.9] for basic uncertainty or [0.05, 0.25, 0.5, 0.75, 0.95] for detailed distributions.

**Computational cost**: Predicting more quantiles increases training and prediction time roughly linearly. Balance detail against performance requirements.

**Quantile crossing**: Ensure P10 < P50 < P90 in predictions. OpenSTEF models enforce this monotonicity, but post-processing can violate it. The isotonic calibration transform preserves monotonicity.

**Extreme quantiles**: P01 and P99 require substantial training data for reliable estimation. Start with moderate quantiles (P10-P90) unless you have extensive historical data.

Summary
-------

Quantile forecasting transforms single-point predictions into rich probability distributions, enabling risk-aware operational decisions. OpenSTEF's quantile regression models, built-in visualization tools, and calibration utilities provide a complete framework for probabilistic forecasting.

Key takeaways:

- Quantiles describe prediction intervals, not confidence intervals
- Wider quantile spreads indicate higher forecast uncertainty
- Well-calibrated quantiles match empirical frequencies in validation data
- OpenSTEF provides visualization and validation tools for quantile forecasts
- Choose quantiles based on operational risk tolerance and decision-making needs