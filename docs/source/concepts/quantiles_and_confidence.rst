Quantiles and Confidence Intervals
===================================

Probabilistic forecasts don't just predict a single value—they predict a range of possible outcomes with associated likelihoods. This page explains what quantiles are, how to interpret them, and why they matter for operational decision-making in energy systems.

What are Quantiles?
-------------------

A quantile represents a threshold in a probability distribution. The 0.5 quantile (also called P50 or the median) is the value where 50% of outcomes are expected to be lower and 50% higher. The 0.9 quantile (P90) is the value where 90% of outcomes are expected to be lower.

In energy forecasting, quantiles answer questions like:

- What load level will we exceed only 10% of the time? (P90)
- What's our best single estimate? (P50, the median)
- What's a conservative lower bound for planning? (P10)

OpenSTEF models can predict multiple quantiles simultaneously using quantile regression. Instead of predicting just one value, the model learns to predict different points in the distribution:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_core.forecasters import GBLinearForecaster
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

   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)

The resulting predictions will contain columns like ``quantile_P10``, ``quantile_P50``, and ``quantile_P90``, each representing a different point in the forecast distribution.

Confidence Intervals vs Prediction Intervals
---------------------------------------------

It's important to distinguish between two types of intervals:

**Prediction intervals** describe the range where future observations are likely to fall. A 80% prediction interval (bounded by P10 and P90) means that 80% of actual outcomes should fall within this range. This is what OpenSTEF quantiles provide.

**Confidence intervals** describe uncertainty about a parameter estimate (like a model coefficient). They answer "how certain are we about this number?" rather than "where will the next observation fall?"

For operational energy forecasting, prediction intervals are what matter. You need to know the range of possible load values, not the uncertainty in your model's parameters.

Why Quantiles Matter for Operations
------------------------------------

Different operational decisions require different quantiles:

**Capacity planning** typically uses high quantiles (P90 or P95). Grid operators need to ensure sufficient capacity for high-load scenarios. Using the median (P50) would leave you unprepared half the time.

**Energy trading** often uses the median (P50) for expected value calculations. When optimizing bids across many periods, the median provides the best single-point estimate.

**Congestion management** needs both tails of the distribution. You want to know both when load might exceed capacity (high quantiles) and when there's room for additional load (low quantiles).

**Risk assessment** uses the full quantile range. The width of the prediction interval (P90 - P10) tells you how uncertain the forecast is. Wide intervals signal high uncertainty and may warrant conservative decisions.

Here's how you might access different quantiles from forecast results:

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import ForecastDataset
   from datetime import timedelta

   # Assuming you have forecast data with multiple quantiles
   forecast_data = pd.DataFrame({
       'quantile_P10': [95, 105],
       'quantile_P50': [100, 110],
       'quantile_P90': [115, 125]
   }, index=pd.date_range('2025-01-01', periods=2, freq='h'))

   dataset = ForecastDataset(forecast_data, timedelta(hours=1))
   
   # Access quantile values
   print(f"Number of quantiles: {len(dataset.quantiles)}")
   print(f"Median quantile: {dataset.quantiles[1]}")
   
   # Calculate prediction interval width (uncertainty)
   interval_width = forecast_data['quantile_P90'] - forecast_data['quantile_P10']
   print(f"Forecast uncertainty: {interval_width.mean():.1f} MW")

Evaluating Quantile Quality
----------------------------

Unlike point forecasts where you can simply compare predicted vs actual values, quantile forecasts require specialized metrics. OpenSTEF provides several:

**Pinball Loss** (also called Quantile Loss) measures how well individual quantiles perform. It penalizes over-predictions and under-predictions asymmetrically based on the quantile level:

.. code-block:: python

   from openstef_beam.metrics import relative_pinball_loss

   # Evaluate P90 quantile performance
   loss = relative_pinball_loss(
       y_true=actual_values,
       y_pred=predicted_p90,
       quantile=0.9,
       lower_quantile=0.1,
       upper_quantile=0.9
   )

**Calibration** checks whether your quantiles are reliable. A well-calibrated P90 should have actual values exceeding it about 10% of the time. The ``mean_absolute_calibration_error`` metric measures this:

.. code-block:: python

   from openstef_beam.metrics import mean_absolute_calibration_error

   # Check if quantiles are properly calibrated
   mace = mean_absolute_calibration_error(
       y_true=actual_values,
       y_pred=predicted_quantiles,  # All quantiles as 2D array
       quantiles=[0.1, 0.5, 0.9]
   )

**CRPS** (Continuous Ranked Probability Score) evaluates the entire probabilistic forecast at once, considering all quantiles together:

.. code-block:: python

   from openstef_beam.metrics import crps

   # Evaluate overall probabilistic forecast quality
   score = crps(
       y_true=actual_values,
       y_pred=predicted_quantiles,
       quantiles=[0.1, 0.5, 0.9]
   )

Lower scores indicate better forecasts. The relative version (rCRPS) normalizes by the typical range of values, making it easier to compare across different prediction locations or time periods.

Visualizing Quantile Forecasts
-------------------------------

Quantile forecasts are best understood visually. A typical visualization shows:

- The median forecast (P50) as a central line
- Prediction intervals as shaded regions (e.g., P10-P90)
- Actual observations as points or a line
- Forecast horizon on the x-axis

.. note:: [DIAGRAM: Time series plot showing median forecast line, shaded 80% prediction interval (P10-P90), and actual load observations. Some actuals fall outside the interval (roughly 20%), demonstrating proper calibration.]

When actual values consistently fall outside your prediction intervals more often than expected, your quantiles are under-confident. If actuals almost never leave the intervals, you're over-confident and the forecasts are less useful for decision-making.

Common Pitfalls
---------------

**Using too few quantiles**: Predicting only P50 gives you no uncertainty information. Predicting only P10 and P90 misses the median. A typical minimum is three quantiles (P10, P50, P90), but more provides richer information.

**Ignoring quantile crossing**: In theory, P10 should always be ≤ P50 ≤ P90. Some models can produce crossed quantiles (P90 < P50) which are logically inconsistent. OpenSTEF's quantile regression approach naturally avoids this, but be aware when combining forecasts from multiple sources.

**Confusing quantiles with percentiles**: A 0.9 quantile is the same as the 90th percentile. The terms are interchangeable, but be consistent in your communication to avoid confusion.

**Over-interpreting narrow intervals**: A tight prediction interval doesn't necessarily mean your forecast is accurate—it means your model is confident. Always validate calibration to ensure confidence matches reality.

Next Steps
----------

Now that you understand quantiles, you might want to explore:

- :doc:`forecasting_basics` for how quantile forecasts fit into the overall forecasting workflow
- :doc:`model_selection` to learn which models support quantile prediction
- :doc:`reliability_and_fallback` for handling cases where quantile forecasts aren't available

The OpenSTEF API documentation provides detailed information on quantile-related functions in ``openstef_beam.metrics`` and quantile handling in ``openstef_core.datasets.ForecastDataset``.