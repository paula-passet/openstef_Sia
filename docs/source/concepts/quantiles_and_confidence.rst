Quantiles and Confidence Intervals
===================================

Energy forecasting is inherently uncertain. Weather changes unexpectedly, consumer behavior varies, and grid conditions shift. A single point forecast—"we expect 150 MW at 14:00"—hides all of this uncertainty. Probabilistic forecasts, expressed as quantiles, make uncertainty explicit and actionable.

This page explains how OpenSTEF represents forecast uncertainty through quantiles, how to interpret them, and why they matter for grid operations.

What Are Quantiles?
-------------------

A **quantile** divides a probability distribution at a specific point. The 10th percentile quantile (P10) means there is a 10% chance the actual value will fall below this prediction. The 90th percentile (P90) means there is a 90% chance the actual value will fall below it.

In energy forecasting, quantiles answer questions like:

- "What is the *most likely* load at 14:00?" → P50 (the median)
- "What is a *conservative high estimate*?" → P90
- "What is a *conservative low estimate*?" → P10

.. note:: [DIAGRAM: A time series plot showing a central P50 forecast line with shaded bands for P10–P90 and P1–P99 intervals. The actual observed values should fall within the bands approximately the expected percentage of the time.]

OpenSTEF produces forecasts across multiple quantiles simultaneously. Rather than a single number, each forecast timestamp gets a full probabilistic profile:

.. list-table:: Example Probabilistic Forecast
   :header-rows: 1
   :widths: 25 15 15 15

   * - Timestamp
     - P10
     - P50
     - P90
   * - 2025-01-01 14:00
     - 135 MW
     - 150 MW
     - 168 MW
   * - 2025-01-01 15:00
     - 140 MW
     - 158 MW
     - 175 MW

The P50 is the median forecast—the "best guess." The gap between P10 and P90 represents the 80% prediction interval: we expect the actual value to land between these bounds roughly 80% of the time.

How OpenSTEF Represents Quantiles
----------------------------------

OpenSTEF uses the ``Quantile`` type from ``openstef_core.types`` to handle quantile values and their naming conventions. Quantile columns in forecast DataFrames follow the pattern ``quantile_PXX``, where ``XX`` is the percentile:

.. code-block:: python

   from openstef_core.types import Quantile

   # Define quantiles for your forecaster
   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

   # Quantiles format to column names automatically
   # Quantile(0.1)  -> "quantile_P10"
   # Quantile(0.5)  -> "quantile_P50"
   # Quantile(0.9)  -> "quantile_P90"

A ``ForecastDataset`` stores these quantile columns alongside the forecast index. You can inspect which quantiles are present:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import ForecastDataset

   # Forecast data with quantile columns
   forecast_data = pd.DataFrame({
       'quantile_P10': [135, 140],
       'quantile_P50': [150, 158],
       'quantile_P90': [168, 175],
   }, index=pd.date_range('2025-01-01 14:00', periods=2, freq='h'))

   dataset = ForecastDataset(forecast_data, timedelta(hours=1))

   # Inspect available quantiles
   print(len(dataset.quantiles))  # 3
   print(dataset.quantiles[1])    # 0.5

Prediction Intervals vs. Confidence Intervals
----------------------------------------------

These terms are often confused, but they mean different things:

**Prediction interval**
   A range that is expected to contain a *future observation* with a given probability. "There is an 80% chance tomorrow's load at 14:00 falls between 135 MW and 168 MW." This is what OpenSTEF produces.

**Confidence interval**
   A range that is expected to contain a *model parameter* (like the true mean) with a given probability. This describes uncertainty about the model itself, not about future observations.

In energy forecasting, prediction intervals are almost always what you want. They are wider than confidence intervals because they account for both model uncertainty *and* the inherent randomness of the system.

.. warning::

   Prediction intervals are only meaningful if they are **calibrated**. A nominal 80% interval should contain the actual value approximately 80% of the time. OpenSTEF includes calibration tools (see :ref:`calibration` below) to ensure this property holds.

Generating Probabilistic Forecasts
------------------------------------

Forecaster models in OpenSTEF declare which quantiles they predict through a ``quantiles`` property. When you build a forecaster, you specify the quantiles you need:

.. code-block:: python

   from openstef_core.types import Quantile

   class MyForecaster:
       def __init__(self):
           self._quantiles = [
               Quantile(0.1),
               Quantile(0.5),
               Quantile(0.9),
           ]

       @property
       def quantiles(self):
           return self._quantiles

       def predict(self, data):
           # Generate predictions for each quantile
           # Output columns: quantile_P10, quantile_P50, quantile_P90
           ...

For models that produce only a point forecast and standard deviation, OpenSTEF provides the ``ConfidenceIntervalApplicator`` transform. This post-processing step converts a point forecast into a full set of quantile predictions by learning hour-specific error distributions from validation data:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # Learn error patterns from validation data
   applicator.fit((validation_data, validation_predictions))

   # Apply to new forecasts
   result = applicator.transform((new_input_data, new_predictions))
   print(list(result.data.columns))
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

.. note::

   The ``ConfidenceIntervalApplicator`` assumes forecast errors follow a normal distribution. This is a reasonable assumption for aggregated energy loads but may be less accurate for individual solar installations or highly volatile loads.

.. _calibration:

Ensuring Quantile Quality
--------------------------

Two post-processing transforms help maintain the quality of quantile forecasts:

**Quantile sorting** ensures monotonic ordering. When quantiles are predicted independently (as in many ML models), it is possible for P10 to exceed P50 at some timestamps. The ``QuantileSorter`` corrects these violations:

.. code-block:: python

   from openstef_models.transforms.postprocessing.quantile_sorter import QuantileSorter

   sorter = QuantileSorter()
   corrected = sorter.transform(forecast_dataset)
   # Guarantees: P10 <= P50 <= P90 at every timestamp

**Isotonic quantile calibration** adjusts quantile predictions so that their empirical coverage matches their nominal coverage. If your P90 only captures 82% of observations instead of 90%, the ``IsotonicQuantileCalibrator`` learns a correction:

.. code-block:: python

   from openstef_models.transforms.postprocessing.isotonic_quantile_calibrator import (
       IsotonicQuantileCalibrator,
   )

   calibrator = IsotonicQuantileCalibrator()
   calibrator.fit(validation_forecast_dataset)
   calibrated = calibrator.transform(new_forecast_dataset)

Why Quantiles Matter for Grid Operations
------------------------------------------

Point forecasts are sufficient when the cost of over-prediction equals the cost of under-prediction. In energy systems, this is rarely the case:

**Reserve capacity planning**
   Grid operators size reserves based on worst-case scenarios. The P95 or P99 quantile tells them: "there is only a 5% or 1% chance load exceeds this value." This directly determines how much backup capacity to procure.

**Congestion management**
   When a transformer or cable approaches its thermal limit, operators need to know the *probability* of overload—not just the expected load. The upper quantiles (P90, P95) quantify this risk.

**Energy trading**
   Traders use asymmetric quantiles to manage risk. If buying too little energy is more expensive than buying too much, they might bid at P60 or P70 rather than P50.

**Renewable energy integration**
   Solar and wind forecasts are inherently more uncertain than load forecasts. Wide prediction intervals signal periods where flexible resources should be on standby.

Choosing Which Quantiles to Use
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The right set of quantiles depends on your use case:

- **Operational dashboards**: P10, P50, P90 — gives a clear central estimate with bounds
- **Risk-sensitive planning**: P1, P10, P25, P50, P75, P90, P99 — full distribution
- **Trading**: P50 plus one or two asymmetric quantiles tuned to your cost function
- **Minimum viable**: P50 alone if you only need a point forecast, but you lose all uncertainty information

.. note:: [DIAGRAM: Side-by-side comparison of a narrow prediction interval (low uncertainty, e.g., stable baseload) vs. a wide prediction interval (high uncertainty, e.g., solar generation on a partly cloudy day). Both show P10/P50/P90 bands.]

Related Topics
--------------

- For an introduction to short-term energy forecasting concepts, see :doc:`forecasting_basics`.
- To understand how different models handle quantile prediction, see :doc:`model_selection`.
- For how weather and other features affect forecast uncertainty, see :doc:`feature_engineering`.
- For what happens when quantile forecasts degrade in production, see :doc:`reliability_and_fallback`.