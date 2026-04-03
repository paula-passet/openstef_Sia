Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasts provide more than a single prediction—they quantify uncertainty by estimating the full distribution of possible outcomes. OpenSTEF generates quantile forecasts that tell you not just what load to expect, but how confident you should be in that expectation.

This page explains what quantiles are, how to interpret them, and why they matter for operational decision-making in energy systems.

What Are Quantiles?
-------------------

A quantile represents a threshold in a probability distribution. The 0.5 quantile (P50) is the median—half of outcomes fall below it, half above. The 0.9 quantile (P90) is higher—only 10% of outcomes exceed it.

In energy forecasting, quantiles answer questions like:

- What load level will be exceeded only 10% of the time? (P90)
- What's the most likely load? (P50)
- What's a conservative lower bound? (P10)

OpenSTEF typically forecasts three quantiles: P10, P50, and P90. These provide a practical range of uncertainty without overwhelming operators with too many numbers.

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.models.forecasting import XGBoostForecaster
   
   # Configure a forecaster to predict three quantiles
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
   )
   
   # After training and prediction, you get three forecasts per timestamp
   # forecast_data will contain columns: quantile_P10, quantile_P50, quantile_P90

The P50 forecast is your best point estimate. The gap between P10 and P90 tells you how uncertain that estimate is. Wide gaps mean high uncertainty; narrow gaps mean high confidence.

Confidence Intervals vs Prediction Intervals
---------------------------------------------

It's important to distinguish between two types of intervals:

**Prediction intervals** estimate where future observations will fall. A 80% prediction interval (P10 to P90) means that 80% of actual load values should fall within this range. This is what OpenSTEF provides—intervals that capture the uncertainty in the physical process being forecasted.

**Confidence intervals** estimate uncertainty in model parameters or statistics. They tell you how precisely you've estimated something, not where future values will land. These are less useful for operational forecasting.

When you see P10 and P90 forecasts from OpenSTEF, think of them as defining a prediction interval. If your P90 forecast is 1000 MW, you're saying there's only a 10% chance actual load will exceed 1000 MW.

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different quantiles. Using only the P50 forecast means ignoring valuable uncertainty information.

**Capacity planning**: Use P90 to ensure you have enough generation capacity. You want to be conservative—undersupplying power has severe consequences.

**Economic dispatch**: Use P50 for cost optimization. It balances the risk of over- and under-forecasting.

**Reserve requirements**: Use the width of the P10-P90 interval to set spinning reserves. Wider intervals mean more uncertainty and thus more reserves needed.

**Risk management**: Use P10 to understand downside scenarios. What if demand is much lower than expected? How does that affect revenue?

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import ForecastDataset
   from datetime import timedelta
   
   # Assume we have forecast data with quantiles
   forecast_df = pd.DataFrame({
       'quantile_P10': [850, 920, 980],
       'quantile_P50': [950, 1020, 1080],
       'quantile_P90': [1050, 1120, 1180],
   }, index=pd.date_range('2025-01-01', periods=3, freq='h'))
   
   dataset = ForecastDataset(forecast_df, timedelta(hours=1))
   
   # Operational decisions based on quantiles
   capacity_needed = forecast_df['quantile_P90'].max()  # Conservative planning
   expected_load = forecast_df['quantile_P50'].mean()   # Economic dispatch
   uncertainty = forecast_df['quantile_P90'] - forecast_df['quantile_P10']
   reserve_margin = uncertainty * 0.5  # Reserve sizing based on uncertainty

Interpreting Quantile Forecasts
--------------------------------

When evaluating quantile forecasts, check whether they're well-calibrated. A well-calibrated P90 forecast should be exceeded by actual values about 10% of the time—no more, no less.

If actual load exceeds your P90 forecast 30% of the time, your model is overconfident. It's underestimating uncertainty. If actual load exceeds P90 only 2% of the time, you're being too conservative—your intervals are too wide.

OpenSTEF includes calibration analysis tools that plot observed frequencies against forecasted probabilities. Perfect calibration shows points along the diagonal. Points below the diagonal indicate overconfidence; points above indicate underconfidence.

.. note::
   [DIAGRAM: Calibration plot showing observed vs forecasted probabilities. Diagonal line represents perfect calibration. Example points showing overconfident (below diagonal) and underconfident (above diagonal) predictions.]

Quantile Regression in Practice
--------------------------------

OpenSTEF uses quantile regression to generate these forecasts. Unlike standard regression that predicts the mean, quantile regression predicts specific quantiles of the conditional distribution.

The library trains separate models for each quantile, each optimized with a quantile-specific loss function. This allows the model to learn different relationships for different parts of the distribution. For example, extreme high loads (P90) might be more sensitive to temperature than typical loads (P50).

.. code-block:: python

   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.types import Quantile, LeadTime
   
   # The forecaster trains separate models for each quantile
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime.from_string("PT1H")],
   )
   
   # During training, each quantile gets its own model
   forecaster.fit(training_data)
   
   # Prediction returns all quantiles
   predictions = forecaster.predict(input_data)
   # predictions contains columns: quantile_P10, quantile_P50, quantile_P90

The models property exposes the underlying quantile models if you need to inspect them individually. Each model is a standard scikit-learn compatible estimator.

Handling Quantile Violations
-----------------------------

Sometimes quantile forecasts can violate logical ordering—P90 might be predicted lower than P50. This shouldn't happen theoretically, but can occur in practice due to model limitations or extreme conditions.

OpenSTEF includes post-processing to enforce monotonicity. The ``IsotonicQuantileCalibrator`` transform ensures that quantiles are properly ordered and calibrated to match empirical frequencies in validation data.

The calibrator learns a monotonic mapping from predicted quantiles to calibrated values, ensuring higher quantiles always produce higher predictions while improving calibration.

When to Use Point Forecasts vs Quantiles
-----------------------------------------

If you're integrating OpenSTEF into a system that expects a single number, use the P50 quantile. It's the median forecast and serves as the best point estimate.

But whenever possible, pass quantile information downstream. Even if your current operations only use point forecasts, having quantiles available enables better decision-making as your systems evolve. Uncertainty quantification is valuable information—don't throw it away.

For reliability and fallback strategies when forecasts fail entirely, see :doc:`reliability_and_fallback`. For understanding which features drive forecast uncertainty, see :doc:`feature_engineering`.

Next Steps
----------

Now that you understand quantiles, you can:

- Explore how different models handle uncertainty in :doc:`model_selection`
- Learn about the fundamentals of short-term forecasting in :doc:`forecasting_basics`
- Understand which features contribute most to forecast uncertainty in :doc:`feature_engineering`