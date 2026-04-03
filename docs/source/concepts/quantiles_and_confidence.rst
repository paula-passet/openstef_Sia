Quantiles and Confidence in Forecasting
========================================

Energy forecasting isn't just about predicting a single number—it's about understanding uncertainty. When a model predicts 500 MW of load at 2 PM tomorrow, how confident should you be? Will it be 480 MW? 520 MW? Understanding this uncertainty is critical for operational decisions like reserve capacity planning, congestion management, and grid balancing.

This page explains probabilistic forecasting in OpenSTEF: what quantiles are, how to interpret them, and why they matter for energy operations.

What are Quantiles?
-------------------

A quantile represents a threshold in a probability distribution. The 0.5 quantile (P50) is the median—half the time, actual values will be below this prediction, and half the time above. The 0.9 quantile (P90) means there's a 90% chance the actual value will be below this prediction.

In energy forecasting, we typically predict multiple quantiles simultaneously:

- **P10 (0.1 quantile)**: Conservative lower bound—90% of actual values will be above this
- **P50 (0.5 quantile)**: Median prediction—the most likely central value
- **P90 (0.9 quantile)**: Conservative upper bound—90% of actual values will be below this

OpenSTEF models use quantile regression to predict these values directly, rather than assuming a specific distribution shape (like a normal distribution). This flexibility is important because energy load distributions often have asymmetric tails and varying spread depending on conditions.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import Quantile, LeadTime
   from openstef_core.models import GBLinearForecaster
   from openstef_core.hyperparams import GBLinearHyperParams

   # Configure forecaster to predict three quantiles
   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
       hyperparams=GBLinearHyperParams(
           learning_rate=0.1,
           reg_alpha=0.1,
           reg_lambda=1.0,
       ),
   )

   # After training, predictions contain all three quantiles
   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)
   
   # predictions contains columns: quantile_P10, quantile_P50, quantile_P90

The resulting forecast dataset contains separate columns for each quantile, allowing you to access the full uncertainty range for any prediction horizon.

Confidence vs Prediction Intervals
-----------------------------------

It's important to distinguish between two types of intervals:

**Prediction intervals** describe where future observations will fall. A 80% prediction interval (P10 to P90) means that 80% of future actual values should fall within this range. This is what OpenSTEF quantiles provide.

**Confidence intervals** describe uncertainty about model parameters or the mean prediction itself. These are narrower and less relevant for operational decisions—you care about where the actual load will be, not about statistical properties of the model.

OpenSTEF focuses on prediction intervals because they directly support operational decisions. When planning reserve capacity, you need to know the range of possible load values, not the precision of a parameter estimate.

The width of prediction intervals varies with conditions. During stable weather with consistent load patterns, intervals are narrow. During volatile conditions or periods with limited training data, intervals widen appropriately. This adaptive uncertainty is a strength of quantile forecasting.

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different quantiles:

**Congestion management**: Use P90 or higher to ensure sufficient capacity. If you plan for P90 and actual load exceeds it, you'll only be caught short 10% of the time. The cost of under-capacity (outages, emergency measures) typically far exceeds the cost of slight over-capacity.

**Reserve capacity planning**: Balance costs by using multiple quantiles. P50 for base planning, P90 for reserve requirements. The spread between them tells you how much uncertainty exists.

**Market bidding**: Use P50 for balanced bidding when over- and under-prediction have symmetric costs. Use asymmetric quantiles when penalties differ.

**Maintenance scheduling**: Use P10 to identify safe low-load periods. If even the P10 prediction is below maintenance thresholds, you can proceed with high confidence.

Here's how to extract and use quantiles from forecast results:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset
   
   # Assuming you have forecast results
   forecast_dataset = ForecastDataset(
       forecast_data,
       sample_interval=timedelta(hours=1),
       forecast_start=datetime(2025, 1, 1),
   )
   
   # Access specific quantiles
   p50_forecast = forecast_data['quantile_P50']
   p90_forecast = forecast_data['quantile_P90']
   
   # Calculate prediction interval width
   interval_width = forecast_data['quantile_P90'] - forecast_data['quantile_P10']
   
   # Identify high-uncertainty periods (wide intervals)
   high_uncertainty = interval_width > interval_width.quantile(0.9)
   
   # Use P90 for capacity planning decisions
   required_capacity = p90_forecast.max()

Evaluating Quantile Quality
----------------------------

How do you know if your quantile predictions are reliable? OpenSTEF provides several metrics:

**Calibration**: A well-calibrated P90 should have actual values exceed it approximately 10% of the time. If actuals exceed P90 30% of the time, your model is overconfident (intervals too narrow). The ``mean_absolute_calibration_error`` metric measures this:

.. code-block:: python

   from openstef_beam.metrics import mean_absolute_calibration_error
   
   # Check if quantiles are well-calibrated
   mace = mean_absolute_calibration_error(
       y_true=actual_values,
       y_pred=predicted_quantiles,
       quantiles=np.array([0.1, 0.5, 0.9])
   )
   
   # Lower MACE means better calibration
   # MACE near 0 indicates quantiles match empirical frequencies

**Sharpness**: Well-calibrated intervals should be as narrow as possible while maintaining coverage. The ``riqd`` (relative inter-quantile distance) metric measures interval width relative to the prediction scale:

.. code-block:: python

   from openstef_beam.metrics import riqd
   
   # Measure prediction interval width
   interval_quality = riqd(
       y_true=actual_values,
       y_pred_lower_q=p10_predictions,
       y_pred_upper_q=p90_predictions,
       quantile_lower=0.1,
       quantile_upper=0.9
   )

**Overall probabilistic skill**: The Continuous Ranked Probability Score (CRPS) combines calibration and sharpness into a single metric. Lower CRPS indicates better probabilistic forecasts:

.. code-block:: python

   from openstef_beam.metrics import crps
   
   # Evaluate overall probabilistic forecast quality
   score = crps(
       y_true=actual_values,
       y_pred=all_quantile_predictions,
       quantiles=np.array([0.1, 0.5, 0.9])
   )

Regular monitoring of these metrics helps ensure your quantile forecasts remain reliable as conditions change.

Quantile Calibration
---------------------

Even well-trained models can produce poorly calibrated quantiles, especially when conditions shift from training data. OpenSTEF provides post-processing calibration through isotonic regression, which learns a monotonic mapping from predicted quantiles to calibrated values.

The calibration process:

1. **Learning phase**: For each quantile, fit an isotonic regression that maps predictions to actual empirical quantiles in validation data
2. **Prediction phase**: Apply the learned mapping to new predictions, ensuring monotonicity

This ensures predicted quantiles match observed frequencies without retraining the entire model. Calibration is particularly valuable when deploying models to new locations or time periods where the base model's uncertainty estimates may be miscalibrated.

.. note::

   Quantile calibration requires representative validation data covering the range of conditions you'll encounter in production. Calibration learned on summer data may not transfer well to winter conditions.

Visualizing Uncertainty
------------------------

Effective visualization helps communicate forecast uncertainty to operators and decision-makers. Common approaches include:

**Fan charts**: Plot multiple quantiles as shaded bands, with darker shades for more likely ranges (P40-P60) and lighter shades for extremes (P10-P90). This shows both the central forecast and uncertainty at a glance.

**Spaghetti plots**: When using ensemble forecasts, plot individual ensemble members as thin lines. The density of lines shows probability—where lines cluster, outcomes are more likely.

**Exceedance probability**: For critical thresholds (like capacity limits), plot the probability that load will exceed the threshold over time. This directly supports go/no-go decisions.

.. note::

   [DIAGRAM: Fan chart showing P10, P25, P50, P75, P90 quantiles as shaded bands over time, with actual values plotted as a line showing how they move through the bands]

Related Topics
--------------

- :doc:`forecasting_basics` - Understanding short-term energy forecasting fundamentals
- :doc:`model_selection` - Choosing models that support quantile prediction
- :doc:`reliability_and_fallback` - Handling cases when probabilistic forecasts fail

For detailed API documentation on quantile-related functions, see the :doc:`../api/index` reference, particularly the metrics module for evaluation and the forecaster classes for quantile configuration.