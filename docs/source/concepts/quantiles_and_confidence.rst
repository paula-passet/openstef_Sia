Probabilistic Forecasts and Quantiles
=====================================

Short-term energy forecasts in OpenSTEF are *probabilistic*: rather than
producing a single number for each future timestamp, the library outputs a
range of quantile predictions that describe the full distribution of likely
outcomes. This page explains what those quantiles mean, how OpenSTEF
constructs them, and how to use them in practice.

For background on what is being forecast and why, see
:doc:`forecasting_basics`. For how model reliability is maintained in
production, see :doc:`reliability_and_fallback`.

What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What load level will not be
exceeded with probability p?"* The 90th percentile (P90) is the value below
which 90 % of actual outcomes are expected to fall; the 10th percentile (P10)
is the value below which only 10 % of outcomes are expected to fall. The
median (P50) is the best single-number estimate — half the outcomes should
fall above it, half below.

Together, a set of quantiles traces out the *predictive distribution* for
each forecast horizon. A symmetric pair such as P10/P90 defines an 80 %
prediction interval: on average, 80 % of real measurements should land inside
that band.

.. note:: [DIAGRAM: Fan chart showing P10, P30, P50, P70, P90 quantile bands widening over a 48-hour forecast horizon, with actual load overlaid]

Prediction Intervals vs. Confidence Intervals
----------------------------------------------

These two terms are often confused, and the distinction matters for grid
operations:

- A **prediction interval** covers where the *next individual measurement*
  will fall. This is what OpenSTEF produces. It accounts for both model
  uncertainty and the inherent variability of the load itself.
- A **confidence interval** covers where the *true mean* of the process lies.
  It shrinks as more data is collected and is not directly useful for
  operational decisions about a single future timestamp.

OpenSTEF's quantile outputs are prediction intervals. When you see P10–P90
in a forecast, you should read it as: *"We expect the actual load to land
inside this band 80 % of the time."*

How OpenSTEF Generates Quantiles
----------------------------------

Quantile generation happens in two stages after the point forecast (P50) is
produced.

**Stage 1 — Hour-specific uncertainty estimation**

The ``ConfidenceIntervalApplicator`` learns the standard deviation of
validation errors for each hour of the day (0–23). Uncertainty is not
constant: a Monday morning peak hour is harder to forecast than a quiet
Sunday night. For multi-horizon forecasts the uncertainty also grows with
lead time, following an exponential saturation curve:

.. code-block:: python

   # sigma grows quickly at first, then levels off
   # sigma(t) = a * (1 - exp(-t / tau)) + b
   # where tau = far_horizon / 4

Once the per-hour standard deviation is known, each quantile is derived by
multiplying the z-score for that quantile level by the standard deviation and
adding it to the median:

.. code-block:: python

   # P10 = median - 1.28 * std   (z-score for 10th percentile)
   # P90 = median + 1.28 * std   (z-score for 90th percentile)

This assumes a locally normal error distribution. The assumption is
reasonable for typical grid loads but may underestimate tail risk during
unusual events.

**Stage 2 — Isotonic calibration**

Raw quantile estimates can be systematically too wide or too narrow. The
``IsotonicQuantileCalibrator`` corrects this by learning a monotonic mapping
from predicted quantile values to calibrated values using isotonic regression
on held-out validation data. The result is that the stated coverage
probability matches the empirically observed coverage.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.types import LeadTime, Q
   from openstef_models.transforms.postprocessing import IsotonicQuantileCalibrator
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   QUANTILES = [Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)]

   # --- Stage 1: fit uncertainty from validation errors ---
   ci_applicator = ConfidenceIntervalApplicator(quantiles=QUANTILES)
   ci_applicator.fit(validation_dataset)          # learns per-hour std
   forecast_with_bands = ci_applicator.transform(point_forecast_dataset)

   # --- Stage 2: calibrate so coverage matches stated levels ---
   calibrator = IsotonicQuantileCalibrator(quantiles=QUANTILES)
   calibrator.fit(validation_dataset)             # learns monotonic correction
   calibrated_forecast = calibrator.transform(forecast_with_bands)

Both transforms implement the ``Transform`` interface and can be composed
into a ``TransformPipeline`` alongside other postprocessing steps.

Choosing Which Quantiles to Request
-------------------------------------

OpenSTEF lets you specify exactly which quantile levels to produce. A
typical operational configuration uses seven quantiles:

.. code-block:: python

   from openstef_core.types import Q
   from openstef_models.workflows import ForecastingWorkflowConfig
   from openstef_core.types import LeadTime

   PREDICTION_QUANTILES = [Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)]

   config = ForecastingWorkflowConfig(
       model_id="substation_42",
       model="gblinear",
       horizons=[LeadTime.from_string("P3D")],
       quantiles=PREDICTION_QUANTILES,
   )

Requesting more quantiles gives a finer picture of the distribution but
increases compute time. For most grid-operations use cases, five to seven
quantiles (P05, P10, P30, P50, P70, P90, P95) strike a good balance.

.. note::

   P50 is always the primary point forecast. All other quantiles are
   derived relative to it. If you only need a point forecast, you can
   pass ``quantiles=[Q(0.5)]``.

Reading Forecast Output
------------------------

After calling ``workflow.predict()``, the returned ``ForecastDataset``
exposes quantile columns alongside the median:

.. code-block:: python

   forecast = workflow.predict(forecast_dataset)

   # Inspect available quantile columns
   print(forecast.quantiles)          # e.g. [0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95]
   print(forecast.data.tail())        # DataFrame with one column per quantile

   # Access the median series directly
   median = forecast.median_series    # pd.Series of P50 values

   # Access all quantile bands for plotting
   bands = forecast.quantiles_data    # DataFrame of all quantile columns

Column names follow the pattern ``quantile_P<level>``, for example
``quantile_P10`` and ``quantile_P90``.

Visualising the Forecast Distribution
---------------------------------------

The ``ForecastTimeSeriesPlotter`` renders quantile bands as shaded areas
around the median, making it easy to see how uncertainty evolves over the
forecast horizon:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.update_layout(title="Energy Load Forecast", yaxis_title="Load (MW)")
   fig.show()

.. note:: [VISUALIZATION: Interactive Plotly chart showing actual load as a solid line, P50 forecast as a dashed line, and P10–P90 shaded band around it over a 72-hour window]

Why Quantiles Matter for Grid Operations
-----------------------------------------

A single-number forecast is rarely sufficient for operational decisions:

- **Congestion management** — a grid operator needs to know the *worst
  plausible* load (P90 or P95), not just the expected load, to decide
  whether to pre-position reserves.
- **Renewable curtailment** — the *best plausible* generation (P10 of load,
  P90 of solar) determines how much renewable output can safely be absorbed.
- **Balancing markets** — bidding strategies that account for forecast
  uncertainty outperform point-forecast strategies because they price in the
  cost of imbalance.
- **Anomaly detection** — a measurement that falls outside the P05–P95 band
  is a strong signal of a sensor fault or an unusual event, independent of
  whether the median forecast was accurate.

In all these cases the *width* of the prediction interval is as informative
as its centre. A narrow band on a calm summer night and a wide band during a
storm front are both correct and useful signals.

Calibration: Are the Intervals Reliable?
------------------------------------------

A well-calibrated 80 % prediction interval (P10–P90) should contain the
actual measurement 80 % of the time — no more, no less. Intervals that are
too wide waste operational headroom; intervals that are too narrow give false
confidence.

OpenSTEF's ``IsotonicQuantileCalibrator`` is designed specifically to enforce
this property. After fitting on validation data, you can check calibration
quality by comparing expected coverage to observed coverage across quantile
levels:

.. code-block:: python

   import numpy as np
   import pandas as pd

   actuals = validation_dataset.data["load"]

   coverage = {}
   for q in [0.1, 0.3, 0.5, 0.7, 0.9]:
       col = f"quantile_P{int(q * 100)}"
       # Fraction of actuals below this quantile should equal q
       coverage[q] = float((actuals <= calibrated_forecast.data[col]).mean())

   calibration_df = pd.DataFrame(
       {"expected": list(coverage.keys()), "observed": list(coverage.values())}
   )
   print(calibration_df)

.. note:: [VISUALIZATION: Calibration reliability diagram — scatter plot of expected quantile level (x-axis) vs observed coverage fraction (y-axis), with a diagonal reference line representing perfect calibration]

A perfect calibration plot is a straight diagonal line. Points above the
diagonal mean the intervals are too wide (conservative); points below mean
they are too narrow (overconfident).

.. note::

   Calibration quality degrades when the forecast period is structurally
   different from the validation period — for example, after a major change
   in grid topology or a prolonged heat wave. Re-fitting the calibrator on
   recent data restores reliability. See :doc:`reliability_and_fallback` for
   strategies to detect and respond to such degradation.

Summary
--------

- OpenSTEF forecasts are probabilistic: each prediction is a set of quantile
  values, not a single number.
- Quantile pairs define prediction intervals; P10–P90 is an 80 % interval.
- Uncertainty grows with lead time and varies by hour of day.
- The ``ConfidenceIntervalApplicator`` derives quantiles from learned
  per-hour standard deviations; the ``IsotonicQuantileCalibrator`` corrects
  systematic over- or under-confidence.
- Well-calibrated intervals are operationally valuable for congestion
  management, balancing, and anomaly detection.