Quantiles and Confidence in Forecasting
========================================

Probabilistic forecasts don't just predict a single value—they quantify uncertainty by providing a range of possible outcomes with associated confidence levels. OpenSTEF uses quantile regression to generate these probabilistic forecasts, enabling energy system operators to make risk-aware decisions.

This page explains what quantiles are, how to interpret them, and why they matter for operational planning in energy systems.

What Are Quantiles?
-------------------

A quantile represents a threshold value in a probability distribution. In forecasting, each quantile tells you: "There's an X% chance the actual value will be below this forecast."

Common quantiles used in energy forecasting:

- **0.1 (P10)**: 10% chance actual load is below this value (90% chance it's higher)
- **0.5 (P50)**: The median forecast—50% chance actual is above or below
- **0.9 (P90)**: 90% chance actual load is below this value (10% chance it's higher)

OpenSTEF typically generates predictions for multiple quantiles simultaneously, providing a complete picture of forecast uncertainty:

.. code-block:: python

   from openstef_core.types import Quantile
   
   # Standard quantile set for energy forecasting
   quantiles = [
       Quantile(0.1),   # Lower bound for planning
       Quantile(0.5),   # Median forecast
       Quantile(0.9),   # Upper bound for capacity planning
   ]

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different risk tolerances:

**Capacity planning**: Use P90 (0.9 quantile) to ensure sufficient capacity 90% of the time. This conservative approach prevents overloads but may result in excess capacity.

**Economic dispatch**: Use P50 (median) for balanced cost optimization. This minimizes systematic over- or under-forecasting.

**Reserve requirements**: Use the spread between P10 and P90 to quantify uncertainty and set appropriate reserve margins.

Consider a distribution grid operator planning maintenance: scheduling during a predicted low-load period based only on the median forecast (P50) might be risky. Checking the P90 forecast ensures the actual load is unlikely to exceed safe operating limits during maintenance.

Prediction Intervals vs Confidence Intervals
---------------------------------------------

These terms are often confused but represent different concepts:

**Prediction intervals** describe where future observations will fall. A 90% prediction interval (P10 to P90) means 90% of future actual values should fall within this range. This is what OpenSTEF quantiles provide.

**Confidence intervals** describe uncertainty about model parameters or the mean prediction. These are typically narrower and less relevant for operational forecasting.

For energy forecasting, prediction intervals are what matter—you need to know where the actual load will be, not just the uncertainty in the average.

Visualizing Quantile Forecasts
-------------------------------

OpenSTEF provides built-in visualization tools for quantile forecasts. The ``ForecastTimeSeriesPlotter`` displays forecasts with shaded uncertainty bands:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter
   import pandas as pd
   
   # Create plotter and add measurements
   plotter = ForecastTimeSeriesPlotter()
   plotter.add_measurements(actual_load_series)
   
   # Add model forecasts with quantiles
   # forecast_df should have columns for each quantile
   plotter.add_model(
       "XGBoost",
       forecast=forecast_df["quantile_0.5"],  # Median
       quantiles=forecast_df[["quantile_0.1", "quantile_0.9"]]
   )
   
   # Generate interactive plot
   fig = plotter.plot(title="Load Forecast with Uncertainty")

The resulting plot shows:

- Actual measurements as a line
- Median forecast (P50) as the central prediction
- Shaded bands between P10 and P90 showing the prediction interval
- Darker shading indicates higher confidence regions

.. note::
   [DIAGRAM: Time series plot showing actual load (solid line), median forecast (dashed line), and shaded uncertainty bands (P10-P90). The actual values should fall within the bands approximately 80% of the time.]

Calibration: Are Your Quantiles Trustworthy?
---------------------------------------------

A well-calibrated model produces quantiles that match reality. If your P90 forecast claims "90% chance actual is below this," then actual values should indeed fall below that forecast 90% of the time.

OpenSTEF includes calibration validation through the ``QuantileProbabilityPlotter``:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   from openstef_core.types import Quantile
   
   plotter = QuantileProbabilityPlotter()
   
   # Add calibration data for a model
   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.9)]
   observed = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.88)]
   
   plotter.add_model("XGBoost", forecasted, observed)
   fig = plotter.plot(title="Forecast Calibration Analysis")

This calibration plot shows:

- **Perfect calibration**: Points fall on the diagonal line
- **Over-confident**: Points below diagonal (predicted P90 is actually P85)
- **Under-confident**: Points above diagonal (predicted P90 is actually P95)

Systematic deviations indicate the model's uncertainty estimates need recalibration. OpenSTEF provides isotonic regression transforms to correct miscalibrated quantiles while preserving monotonicity.

.. note::
   [DIAGRAM: Calibration plot with diagonal "perfect calibration" line and scattered points showing forecasted vs observed quantile probabilities. Include annotations showing over-confident and under-confident regions.]

Quantile Regression in OpenSTEF Models
---------------------------------------

OpenSTEF models generate quantile forecasts natively. When you configure a forecasting model, you specify which quantiles to predict:

.. code-block:: python

   from openstef_core.model.configs import XGBQuantileForecasterConfig
   from openstef_core.types import Quantile, LeadTime
   
   config = XGBQuantileForecasterConfig(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(0.25)],  # 15-minute ahead forecast
   )

The model trains separate quantile regressors for each specified quantile. During prediction, it generates all quantile forecasts simultaneously, ensuring they maintain proper ordering (P10 ≤ P50 ≤ P90).

Evaluating Quantile Forecast Quality
-------------------------------------

Standard metrics like MAE or RMSE only evaluate the median forecast. For quantile forecasts, use specialized probabilistic metrics:

**Quantile loss**: Asymmetric loss function that penalizes over- and under-prediction differently based on the quantile level.

**Pinball loss**: Another name for quantile loss, commonly used in probabilistic forecasting literature.

**Coverage**: Percentage of actual values falling within prediction intervals. An 80% prediction interval (P10 to P90) should contain actual values 80% of the time.

OpenSTEF's evaluation framework automatically computes these metrics for each quantile:

.. code-block:: python

   from openstef_core.evaluation import Evaluator
   
   evaluator = Evaluator()
   metrics = evaluator.compute_probabilistic(
       y_true=actual_values,
       y_pred=quantile_predictions,
       quantiles=np.array([0.1, 0.5, 0.9])
   )

The returned metrics dictionary contains separate evaluations for each quantile, helping you identify which parts of the uncertainty distribution are well-modeled.

Practical Considerations
-------------------------

**Quantile crossing**: Ensure P10 < P50 < P90 in all predictions. OpenSTEF models enforce this during training, but post-processing transforms should preserve monotonicity.

**Extreme quantiles**: Very low (P01) or high (P99) quantiles are harder to estimate accurately due to limited training data in the tails. Stick to moderate quantiles (P10-P90) unless you have extensive historical data.

**Temporal variation**: Forecast uncertainty isn't constant—it varies with weather conditions, time of day, and forecast horizon. Models automatically learn these patterns from training data.

**Computational cost**: Generating multiple quantiles increases training time roughly linearly with the number of quantiles. Three to five quantiles typically provide sufficient information without excessive overhead.

Next Steps
----------

- Learn about :doc:`model_selection` to choose forecasters that support quantile regression
- Understand :doc:`reliability_and_fallback` strategies when quantile forecasts indicate high uncertainty
- Explore :doc:`feature_engineering` to improve both point forecasts and uncertainty estimates