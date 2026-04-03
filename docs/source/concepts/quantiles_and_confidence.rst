Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasts provide more than just a single predicted value—they quantify uncertainty by predicting multiple outcomes with different confidence levels. This page explains what quantiles are, how to interpret them, and why they matter for operational energy forecasting.

What Are Quantiles?
-------------------

A quantile represents a threshold in a probability distribution. In forecasting, quantiles tell you: "There is an X% chance the actual value will be below this prediction."

For example:

- **Quantile 0.1 (10th percentile)**: There's a 10% chance the actual load will be below this value
- **Quantile 0.5 (50th percentile, median)**: The most likely prediction—50% chance actual is above or below
- **Quantile 0.9 (90th percentile)**: There's a 90% chance the actual load will be below this value (or 10% chance it exceeds)

OpenSTEF models generate predictions for multiple quantiles simultaneously, providing a complete picture of forecast uncertainty:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import ForecastDataset
   
   # Example forecast with multiple quantiles
   forecast_data = pd.DataFrame({
       'forecast': [100, 110],
       'quantile_P10': [85, 95],
       'quantile_P50': [100, 110],
       'quantile_P90': [115, 125]
   }, index=pd.date_range('2025-01-01', periods=2, freq='h'))
   
   dataset = ForecastDataset(forecast_data, timedelta(hours=1))
   print(f"Available quantiles: {dataset.quantiles}")
   # Output: [0.1, 0.5, 0.9]

In this example, for the first hour, the model predicts a median load of 100 MW, but acknowledges there's a 10% chance it could be as low as 85 MW and a 10% chance it could exceed 115 MW.

Confidence Intervals vs Prediction Intervals
---------------------------------------------

It's important to distinguish between two types of intervals:

**Prediction Intervals** (what OpenSTEF provides):
   Quantify uncertainty in individual future observations. They answer: "Where will the actual load fall?" These intervals are wider because they account for both model uncertainty and natural variability in the system.

**Confidence Intervals** (statistical concept):
   Quantify uncertainty in model parameters or mean predictions. They answer: "How confident are we in the model's average behavior?" These are typically narrower and less relevant for operational forecasting.

For energy system operations, prediction intervals are what matters. You need to know the range of possible outcomes for a specific hour, not the theoretical average across many scenarios.

OpenSTEF generates prediction intervals through quantile regression, where models directly learn to predict different percentiles of the target distribution. The interval between quantile 0.1 and quantile 0.9 forms an 80% prediction interval—you expect the actual value to fall within this range 80% of the time.

How Quantile Forecasts Are Generated
-------------------------------------

OpenSTEF supports two approaches for generating quantile predictions:

**1. Native Quantile Regression**

Models like XGBoost can be trained to predict multiple quantiles simultaneously using specialized objective functions. Each quantile represents a confidence level that the model learns during training:

.. code-block:: python

   from openstef_models.forecasters import XGBQuantileForecaster
   from openstef_core.types import Quantile
   
   # Configure forecaster with multiple quantiles
   forecaster = XGBQuantileForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(hours=1)]
   )
   
   # Train the model - it learns to predict all quantiles
   forecaster.fit(train_data)
   
   # Generate probabilistic forecast
   forecast = forecaster.predict(input_data)
   
   # Access different quantiles
   median_forecast = forecast.data['quantile_P50']
   lower_bound = forecast.data['quantile_P10']
   upper_bound = forecast.data['quantile_P90']

The quantile regression objective function penalizes over-predictions and under-predictions asymmetrically based on the target quantile. For the 90th percentile, the model is penalized more heavily for under-predicting (which would happen more than 10% of the time) than for over-predicting.

**2. Post-Processing with Learned Uncertainty**

For models that don't natively support quantile regression, OpenSTEF can add quantile predictions by learning hour-specific uncertainty patterns from validation errors:

.. code-block:: python

   from openstef_models.transforms.postprocessing import ConfidenceIntervalApplicator
   
   # This transform learns uncertainty patterns from validation data
   confidence_applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )
   
   # Fit learns hour-specific error distributions
   confidence_applicator.fit(validation_forecast, validation_actual)
   
   # Apply learned uncertainty to new point forecasts
   probabilistic_forecast = confidence_applicator.transform(point_forecast)

This approach analyzes how forecast errors vary by hour of day and day of week, then applies these learned patterns to convert point forecasts into probabilistic ones.

Interpreting Quantile Predictions
----------------------------------

Understanding quantile predictions requires thinking probabilistically:

**Wide intervals indicate high uncertainty**:
   If quantile 0.1 is 50 MW and quantile 0.9 is 150 MW, the model is uncertain about the outcome. This often happens during volatile weather conditions or periods with limited historical data.

**Narrow intervals indicate confidence**:
   If quantile 0.1 is 95 MW and quantile 0.9 is 105 MW, the model is confident the load will be near 100 MW. This typically occurs during stable, predictable conditions.

**Asymmetric intervals reveal skewed distributions**:
   If the median (quantile 0.5) is closer to the lower bound than the upper bound, the distribution is right-skewed—there's potential for occasional high values but a more constrained lower range.

.. note::
   [DIAGRAM: Visualization showing a time series with quantile bands (0.1, 0.5, 0.9) overlaid on actual values. Show periods where actuals fall outside the 80% interval to illustrate calibration.]

Why Quantiles Matter for Operations
------------------------------------

Probabilistic forecasts enable better operational decisions:

**Balancing Risk and Cost**

Grid operators must balance the cost of over-preparing (reserving too much capacity) against the risk of under-preparing (potential shortages). Different quantiles support different operational strategies:

- Use quantile 0.9 for reserve capacity planning—ensures you have enough capacity 90% of the time
- Use quantile 0.5 for expected energy procurement—minimizes average cost
- Use quantile 0.1 for minimum load scenarios—helps avoid over-generation

**Quantifying Forecast Reliability**

By comparing predicted quantiles against actual outcomes, you can validate model calibration. A well-calibrated model's 90th percentile should be exceeded by actuals approximately 10% of the time. OpenSTEF includes tools for this validation:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   
   # Validate probabilistic forecast calibration
   plotter = QuantileProbabilityPlotter()
   calibration_plot = plotter.create_calibration_plot(
       forecasts=forecast_data,
       actuals=actual_data,
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

This creates plots comparing predicted probabilities with observed frequencies, revealing whether your model over-estimates or under-estimates uncertainty.

**Scenario Planning**

Quantiles enable "what-if" analysis without running multiple simulations. Instead of asking "What if conditions are worse than expected?", you can directly use the 90th percentile forecast to understand high-load scenarios.

**Optimization Under Uncertainty**

Advanced optimization algorithms can use quantile forecasts to make decisions that are robust to uncertainty. For example, unit commitment optimization can consider the full distribution of possible loads rather than just a point forecast.

Practical Considerations
-------------------------

**Choosing Quantiles**

Common choices include:

- **[0.1, 0.5, 0.9]**: Provides 80% prediction interval with median
- **[0.05, 0.25, 0.5, 0.75, 0.95]**: More detailed uncertainty quantification
- **[0.01, 0.1, 0.5, 0.9, 0.99]**: Captures extreme scenarios for risk management

More quantiles provide finer detail but increase computational cost and storage requirements.

**Quantile Crossing**

In theory, quantile predictions should be ordered: quantile 0.1 ≤ quantile 0.5 ≤ quantile 0.9. Some models may occasionally produce crossed quantiles (e.g., predicting quantile 0.9 < quantile 0.5). OpenSTEF's native quantile regressors are designed to minimize this issue, but post-processing approaches may require additional constraints.

**Computational Cost**

Predicting multiple quantiles requires more computation than point forecasts. XGBoost quantile regression trains a single model that outputs all quantiles, which is more efficient than training separate models per quantile.

Next Steps
----------

- See :doc:`forecasting_basics` for an introduction to short-term energy forecasting concepts
- See :doc:`model_selection` to understand which models support native quantile regression
- See :doc:`reliability_and_fallback` for strategies when probabilistic forecasts are unavailable

For API details on working with quantile forecasts, see the :doc:`../api/core/datasets` documentation for ``ForecastDataset`` and the :doc:`../api/models/forecasters` documentation for quantile-capable forecasters.