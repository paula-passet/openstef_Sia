Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasts provide more than a single prediction—they quantify uncertainty by estimating a range of possible outcomes. OpenSTEF generates quantile forecasts that answer questions like "What's the 90% chance the load will be below?" rather than just "What will the load be?" This capability is essential for operational planning, where understanding risk is as important as the forecast itself.

What Are Quantiles?
-------------------

A quantile represents a threshold value below which a certain percentage of observations fall. In forecasting:

- **0.1 quantile (P10)**: 10% chance actual load will be below this value
- **0.5 quantile (P50)**: The median forecast—50% chance of being above or below
- **0.9 quantile (P90)**: 90% chance actual load will be below this value

OpenSTEF typically generates multiple quantiles simultaneously (e.g., 0.1, 0.3, 0.5, 0.7, 0.9) to provide a complete picture of forecast uncertainty. Each quantile is learned independently using quantile regression, which optimizes for different parts of the conditional distribution.

.. code-block:: python

   from openstef_core.types import Quantile
   import numpy as np
   
   # Define quantiles for forecasting
   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   
   # Interpret a forecast: [850 MW, 1000 MW, 1200 MW]
   # - 10% chance load < 850 MW
   # - 50% chance load < 1000 MW (median)
   # - 90% chance load < 1200 MW

Why Quantiles Matter for Operations
------------------------------------

Energy system operators face asymmetric costs: underestimating peak demand can cause blackouts, while overestimating wastes resources on unnecessary reserves. Quantile forecasts enable risk-aware decision making:

**Reserve planning**: Use P90 forecasts to ensure sufficient capacity for high-load scenarios without over-provisioning based on worst-case assumptions.

**Trading strategies**: P10 forecasts help identify low-load periods where excess generation might need market outlets.

**Balancing actions**: The spread between P10 and P90 quantifies uncertainty—wider spreads indicate higher risk periods requiring more conservative strategies.

**Maintenance scheduling**: Plan outages during periods with tight quantile ranges (high confidence) rather than wide uncertainty bands.

Confidence Intervals vs Prediction Intervals
---------------------------------------------

It's critical to distinguish between two types of intervals:

**Prediction intervals** describe where future observations will fall. A 80% prediction interval (P10 to P90) means 80% of actual loads should fall within this range. OpenSTEF generates prediction intervals through quantile forecasts.

**Confidence intervals** describe uncertainty about model parameters or mean predictions. These are not the same as prediction intervals and are less relevant for operational forecasting.

When you see P10 and P90 forecasts from OpenSTEF, you're working with prediction intervals that account for all sources of uncertainty: model error, weather forecast uncertainty, and inherent load variability.

Interpreting Quantile Forecasts
--------------------------------

The relationship between quantiles reveals forecast confidence:

.. code-block:: python

   # Example forecast for tomorrow at 18:00
   forecast = {
       Quantile(0.1): 950,   # MW
       Quantile(0.5): 1000,  # MW (median)
       Quantile(0.9): 1050,  # MW
   }
   
   # Narrow spread (1050 - 950 = 100 MW)
   # → High confidence forecast
   # → Typical for stable weather conditions
   
   # Compare to uncertain forecast:
   uncertain_forecast = {
       Quantile(0.1): 800,   # MW
       Quantile(0.5): 1000,  # MW
       Quantile(0.9): 1300,  # MW
   }
   
   # Wide spread (1300 - 800 = 500 MW)
   # → Low confidence forecast
   # → May occur during weather transitions

The interquantile range (e.g., P90 - P10) serves as a direct measure of forecast uncertainty. Operators can use this to adjust their risk tolerance: tighter ranges allow more aggressive optimization, while wider ranges warrant conservative buffers.

Calibration: Are Your Quantiles Trustworthy?
---------------------------------------------

A well-calibrated P90 forecast should have actual observations exceed it only 10% of the time. If actuals exceed P90 forecasts 30% of the time, the model is overconfident—its uncertainty estimates are too narrow.

OpenSTEF provides calibration analysis tools to validate probabilistic forecasts:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   from openstef_core.types import Quantile
   
   # Compare forecasted vs observed probabilities
   plotter = QuantileProbabilityPlotter()
   
   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.9)]
   observed = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.88)]
   
   plotter.add_model("XGBoost", forecasted, observed)
   fig = plotter.plot(title="Forecast Calibration Analysis")

Perfect calibration produces points along the diagonal: forecasted probability equals observed frequency. Systematic deviations indicate:

- **Points below diagonal**: Overconfident (uncertainty too narrow)
- **Points above diagonal**: Underconfident (uncertainty too wide)
- **S-shaped curve**: Non-linear calibration issues

Improving Quantile Forecast Quality
------------------------------------

OpenSTEF includes post-processing transforms to enhance quantile forecasts:

**Isotonic calibration** corrects systematic calibration errors by learning a monotonic mapping from predicted to calibrated quantiles:

.. code-block:: python

   from openstef_models.transforms.postprocessing import IsotonicQuantileCalibrator
   
   calibrator = IsotonicQuantileCalibrator(
       quantiles=[0.1, 0.5, 0.9],
       y_min=0.0  # Enforce non-negative forecasts
   )
   
   # Learn calibration from validation data
   calibrator.fit(validation_forecasts)
   
   # Apply to new forecasts
   calibrated_forecasts = calibrator.transform(test_forecasts)

**Quantile sorting** enforces monotonic ordering (P10 ≤ P50 ≤ P90), correcting cases where models produce crossed quantiles:

.. code-block:: python

   from openstef_models.transforms.postprocessing import QuantileSorter
   
   sorter = QuantileSorter()
   sorted_forecasts = sorter.transform(raw_forecasts)

**Adaptive uncertainty** adjusts quantile spreads based on recent forecast errors, widening intervals during periods of poor model performance:

.. code-block:: python

   from openstef_models.transforms.postprocessing import AdaptiveUncertaintyAdjuster
   
   adjuster = AdaptiveUncertaintyAdjuster()
   adjuster.fit(historical_forecasts)  # Learn error patterns
   adjusted_forecasts = adjuster.transform(new_forecasts)

Quantile Metrics
----------------

Evaluating quantile forecast quality requires specialized metrics beyond standard MAE or RMSE:

**Quantile loss** (pinball loss) penalizes errors asymmetrically based on the quantile level. For a 0.9 quantile, underestimation (missing high loads) is penalized more heavily than overestimation.

**Coverage** measures whether the actual percentage of observations falling below a quantile matches the target. Ideal P90 coverage is 90%.

**Sharpness** quantifies the width of prediction intervals—narrower is better, but only if calibration is maintained.

OpenSTEF computes these metrics automatically during model evaluation, helping you assess both the accuracy and reliability of probabilistic forecasts.

.. code-block:: python

   # Metrics are computed per quantile
   # Example output from evaluation:
   # {
   #   'quantile_0.1_mae': 45.2,
   #   'quantile_0.5_mae': 38.7,
   #   'quantile_0.9_mae': 52.1,
   #   'coverage_0.9': 0.89  # Close to ideal 0.90
   # }

Visualization Best Practices
-----------------------------

When presenting quantile forecasts to stakeholders:

**Fan charts** show all quantiles as shaded bands, with darker shades for higher-confidence regions (P30-P70) and lighter shades for tails (P10, P90).

**Spaghetti plots** display multiple quantiles as individual lines, making it easy to see the full range of possibilities.

**Exceedance curves** show the probability of exceeding different load levels, useful for capacity planning.

.. note::
   [DIAGRAM: Fan chart showing quantile forecasts as shaded probability bands over time, with historical actuals overlaid to demonstrate calibration]

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting fundamentals
- :doc:`model_selection` - Choosing models that produce well-calibrated quantiles
- :doc:`feature_engineering` - Features that improve uncertainty quantification
- :doc:`reliability_and_fallback` - Handling cases when quantile forecasts fail