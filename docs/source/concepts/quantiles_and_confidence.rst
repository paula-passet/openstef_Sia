Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasting goes beyond single-point predictions to quantify uncertainty. Instead of predicting "tomorrow's load will be 100 MW," OpenSTEF models predict "there's a 90% chance the load will be below 115 MW and a 10% chance it will be below 85 MW." This uncertainty quantification is essential for operational planning in energy systems.

What Are Quantiles?
-------------------

A quantile represents a threshold below which a certain percentage of outcomes are expected to fall. The 0.1 quantile (10th percentile) means there's a 10% probability the actual value will be below this forecast, while the 0.9 quantile (90th percentile) means there's a 90% probability the actual value will be below this forecast.

OpenSTEF models typically predict multiple quantiles simultaneously:

- **0.1 (P10)**: Lower bound - only 10% of outcomes fall below this
- **0.5 (P50)**: Median prediction - the most likely central value
- **0.9 (P90)**: Upper bound - 90% of outcomes fall below this

The median (0.5 quantile) is often the best single-point forecast, while the spread between quantiles indicates forecast uncertainty. A wide gap between P10 and P90 signals high uncertainty; a narrow gap indicates confidence.

Confidence vs Prediction Intervals
-----------------------------------

It's crucial to distinguish between two types of intervals:

**Prediction intervals** describe where future observations are likely to fall. The interval between the 0.1 and 0.9 quantiles is an 80% prediction interval - we expect 80% of actual outcomes to fall within this range.

**Confidence intervals** (common in statistics) describe uncertainty about model parameters themselves. OpenSTEF focuses on prediction intervals because operational decisions require knowing where actual load or generation will be, not uncertainty about model coefficients.

When you see a forecast with P10 = 85 MW and P90 = 115 MW, you're looking at a prediction interval: there's an 80% chance the actual value will fall between 85 and 115 MW.

How OpenSTEF Generates Quantile Forecasts
------------------------------------------

OpenSTEF uses quantile regression to train models that predict multiple quantiles directly. Each quantile gets its own model instance, all trained on the same historical data but optimized for different probability levels.

.. code-block:: python

   from openstef_core.model.regressors.multi_quantile_regressor import MultiQuantileRegressor
   from xgboost import XGBRegressor
   
   # Create a multi-quantile regressor
   model = MultiQuantileRegressor(
       base_learner=XGBRegressor,
       quantile_param='quantile',
       quantiles=[0.1, 0.5, 0.9],
       hyperparams={
           'n_estimators': 100,
           'max_depth': 5,
           'learning_rate': 0.1
       }
   )
   
   # Train on historical data
   model.fit(X_train, y_train)
   
   # Predict all quantiles at once
   predictions = model.predict(X_test)
   # Returns array with shape (n_samples, 3) - one column per quantile

The ``MultiQuantileRegressor`` wrapper manages separate model instances for each quantile, ensuring consistent feature handling and efficient batch prediction.

Working with Forecast Datasets
-------------------------------

OpenSTEF's ``ForecastDataset`` class structures quantile predictions with proper metadata:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset
   from datetime import timedelta
   import pandas as pd
   
   # Create forecast data with quantile columns
   forecast_data = pd.DataFrame({
       'quantile_P10': [85, 88, 90],
       'quantile_P50': [100, 103, 105],
       'quantile_P90': [115, 118, 120]
   }, index=pd.date_range('2025-01-01', periods=3, freq='h'))
   
   # Wrap in ForecastDataset
   dataset = ForecastDataset(
       forecast_data,
       sample_interval=timedelta(hours=1),
       target_column='load'
   )
   
   # Access quantile information
   print(f"Number of quantiles: {len(dataset.quantiles)}")
   print(f"Quantile values: {[float(q) for q in dataset.quantiles]}")

The dataset automatically detects quantile columns (formatted as ``quantile_PXX``) and provides structured access to uncertainty information.

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different quantiles:

**Capacity planning** uses high quantiles (P90, P95) to ensure sufficient reserves. Grid operators need to handle peak scenarios, so they plan for the 90th percentile rather than the median.

**Energy trading** often uses the median (P50) for expected value calculations. Traders want the most likely outcome for portfolio optimization.

**Reserve activation** uses low quantiles (P10, P05) to prepare for shortfalls. Knowing when demand might exceed typical forecasts helps schedule backup generation.

**Risk assessment** examines the full quantile range. The spread between P10 and P90 quantifies risk exposure - wider spreads mean more volatile conditions requiring more flexible resources.

Validating Probabilistic Forecasts
-----------------------------------

A well-calibrated model produces quantiles that match observed frequencies. If your P90 forecast is truly the 90th percentile, then 90% of actual observations should fall below it. OpenSTEF provides built-in tools to check calibration:

.. code-block:: python

   from openstef_beam.analysis.plots.quantile_probability_plotter import QuantileProbabilityPlotter
   from openstef_core.types import Quantile
   
   # Create calibration plotter
   plotter = QuantileProbabilityPlotter()
   
   # Add model results (forecasted vs observed probabilities)
   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.9)]
   observed = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.88)]
   plotter.add_model("XGBoost", forecasted, observed)
   
   # Generate calibration plot
   fig = plotter.plot(title="Forecast Calibration Analysis")
   fig.show()

The calibration plot shows forecasted probabilities on the x-axis and observed frequencies on the y-axis. Points near the diagonal line indicate good calibration. If points fall above the diagonal, the model is overconfident (predicting narrower intervals than warranted). Points below the diagonal indicate underconfidence (intervals too wide).

Systematic deviations from perfect calibration suggest model improvements are needed. Over-confident models risk operational failures because they underestimate uncertainty. Under-confident models waste resources by over-preparing for unlikely scenarios.

Interpreting Quantile Spreads
------------------------------

The distance between quantiles reveals forecast uncertainty patterns:

**Narrow spreads** during stable conditions indicate the model is confident. For example, overnight baseload periods with consistent weather typically show P90 - P10 spreads of 5-10% of the median forecast.

**Wide spreads** during volatile conditions signal uncertainty. Morning ramp-up periods, weather transitions, or unusual calendar events (holidays) often show spreads of 20-30% or more.

**Asymmetric spreads** reveal skewed risk. If P90 - P50 is much larger than P50 - P10, the model sees more upside risk than downside risk. This matters for renewable generation forecasts where cloud cover can suddenly reduce output but clear skies have a natural ceiling (installed capacity).

Practical Considerations
-------------------------

When using quantile forecasts in production systems:

**Choose quantiles strategically**. More quantiles provide finer uncertainty resolution but increase computational cost. Most applications work well with 3-5 quantiles (0.1, 0.3, 0.5, 0.7, 0.9).

**Monitor calibration continuously**. Forecast quality degrades over time as conditions change. Regular calibration checks catch problems before they impact operations.

**Communicate uncertainty clearly**. Operators need to understand that P90 forecasts will be exceeded 10% of the time - this is expected behavior, not forecast failure.

**Combine with domain knowledge**. Quantile forecasts capture statistical patterns but may miss rare events. Supplement model outputs with expert judgment during unusual conditions.

See Also
--------

- :doc:`forecasting_basics` - Introduction to short-term energy forecasting concepts
- :doc:`model_selection` - Choosing models that provide well-calibrated quantile predictions
- :doc:`reliability_and_fallback` - Handling cases when probabilistic forecasts aren't available