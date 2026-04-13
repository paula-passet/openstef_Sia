Quantiles and Confidence Intervals
===================================

Probabilistic forecasting goes beyond a single "best guess" by expressing
*how uncertain* a forecast is. This page explains what quantile forecasts are,
how OpenSTEF generates them, and why they matter for day-to-day grid operations.

.. note::

   This page focuses on probabilistic output. For the underlying point-forecast
   mechanics see :doc:`forecasting_basics`, and for model selection considerations
   see :doc:`model_selection`.

What Is a Quantile Forecast?
-----------------------------

A deterministic forecast answers the question *"how much load will there be at
14:00?"* with a single number. A quantile forecast answers a richer question:
*"what is the full distribution of likely outcomes at 14:00?"*

A **quantile** at level *p* is the value below which *p × 100 %* of outcomes
are expected to fall. The three quantiles most commonly used in energy
forecasting are:

- **P10** (10th percentile) — a low-end estimate; actual load should be *above*
  this value 90 % of the time.
- **P50** (50th percentile) — the median; the "central" forecast, equally likely
  to be above or below the actual outcome.
- **P90** (90th percentile) — a high-end estimate; actual load should be *below*
  this value 90 % of the time.

Together, P10 and P90 form an **80 % prediction interval**: you expect the true
value to land inside the band on roughly 8 out of 10 occasions. Narrower bands
(e.g. P25–P75) express higher confidence; wider bands express more uncertainty.

.. note:: [DIAGRAM: Time-series chart spanning 48 hours showing three shaded bands. The darkest inner band runs between P25 and P75, a medium band spans P10 to P90, and a thin outer band covers P05 to P95. The P50 median forecast is drawn as a solid line through the centre. Observed actuals are plotted as dots; most fall inside the P10–P90 band, a few fall outside, illustrating the probabilistic guarantee. The x-axis shows time-of-day; the y-axis shows load in MW. Uncertainty visibly widens during the evening peak and narrows overnight, reflecting the hour-specific standard deviations learned by the ConfidenceIntervalApplicator.]

Confidence Intervals vs. Prediction Intervals
----------------------------------------------

The terms *confidence interval* and *prediction interval* are sometimes used
interchangeably in operational contexts, but they mean different things
statistically:

- A **confidence interval** quantifies uncertainty about a *model parameter*
  (e.g. the mean load at 14:00 across many days).
- A **prediction interval** quantifies uncertainty about a *single future
  observation* — which is what grid operators actually need.

OpenSTEF generates **prediction intervals** expressed as quantiles. When the
documentation or API refers to a "confidence interval", it means the same
thing: a pair of quantile bounds that bracket the expected range of a single
future measurement.

How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF uses a post-processing approach implemented in
``ConfidenceIntervalApplicator``. The process has two phases.

**Fit phase**

During training, the applicator examines validation-set residuals (the
differences between the model's point forecasts and the observed values). It
computes the standard deviation of those residuals for each of the 24 hours of
the day, capturing the fact that uncertainty is typically higher during morning
and evening ramps than during stable overnight periods. For multi-horizon
forecasts it also stores a separate standard deviation per forecast horizon.

**Transform phase**

At inference time, the applicator looks up the appropriate standard deviation
for the prediction's hour-of-day (and horizon, if applicable) and converts it
to quantile offsets by assuming a normal distribution:

.. code-block:: python

   # Conceptual illustration — simplified from ConfidenceIntervalApplicator
   # quantile_value = median + z_score * std
   # e.g. P10 = median - 1.28 * std
   #      P90 = median + 1.28 * std

For multi-horizon forecasts, uncertainty does not grow linearly with lead time.
OpenSTEF models the growth with an exponential saturation curve:

.. code-block:: python

   # sigma(t) = a * (1 - exp(-t / tau)) + b
   # where t is hours ahead and tau = far_horizon / 4

This reflects the empirical observation that uncertainty increases quickly in
the first few hours and then levels off — a 36-hour forecast is not three times
as uncertain as a 12-hour forecast.

After the quantile offsets are computed, a ``QuantileSorter`` enforces strict
monotonic ordering (P10 ≤ P25 ≤ P50 ≤ P75 ≤ P90) to prevent crossing bands
that can arise from independent quantile estimates. An optional
``IsotonicQuantileCalibrator`` can then recalibrate the quantiles using
isotonic regression when empirical coverage deviates from the nominal level.

Working with Quantile Output
-----------------------------

When you run a forecast pipeline that has quantiles enabled, the returned
``ForecastDataset`` contains one column per quantile alongside the median:

.. code-block:: python

   import pandas as pd
   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   # Specify which quantiles you want in the output
   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

   applicator = ConfidenceIntervalApplicator(quantiles=quantiles)

   # fit() learns hour-specific uncertainty from a validation ForecastDataset
   applicator.fit(validation_dataset)

   # transform() adds quantile columns to the point-forecast dataset
   probabilistic_forecast = applicator.transform(point_forecast_dataset)

   # The resulting DataFrame has columns like "quantile_P10", "quantile_P50", "quantile_P90"
   df = probabilistic_forecast.data
   print(df.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

   # Compute the width of the 80 % prediction interval at each timestep
   interval_width = df["quantile_P90"] - df["quantile_P10"]
   print(interval_width.describe())

.. note::

   If ``quantiles=None`` is passed to ``ConfidenceIntervalApplicator``, the
   transform returns the dataset unchanged — useful when you want to disable
   probabilistic output without restructuring the pipeline.

Validating Calibration
-----------------------

A quantile forecast is only useful if it is *calibrated*: P90 should be
exceeded by actual outcomes roughly 10 % of the time, not 5 % or 30 %. OpenSTEF
provides ``QuantileProbabilityPlotter`` in the ``openstef-beam`` package to
check this visually.

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )

   plotter = QuantileProbabilityPlotter()

   # forecasted_probs: the quantile levels your model predicted
   # observed_probs:   the empirical frequencies at which actuals fell below those levels
   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.9)]
   observed   = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.88)]

   plotter.add_model("XGBoost", forecasted, observed)
   fig = plotter.plot(title="Forecast Calibration Analysis")
   fig.show()

The resulting chart plots forecasted probability on the x-axis and observed
frequency on the y-axis. A perfectly calibrated model lies on the diagonal.
Points above the diagonal indicate that the model is **over-confident** (the
bands are too narrow); points below indicate **under-confidence** (the bands
are wider than necessary).

For fleet-level analysis across many substations, ``QuantileCalibrationBoxPlotter``
shows the distribution of calibration errors as boxplots — one box per quantile
level — making it easy to spot systematic bias across an entire portfolio.

Why Quantiles Matter for Operations
-------------------------------------

Grid operators and trading desks use probabilistic forecasts differently from
point forecasts:

**Congestion management**
  A transmission operator managing a line near its thermal limit cares about
  P90, not P50. If P90 exceeds the line rating, action is warranted even if
  the median forecast is safely below the limit.

**Reserve sizing**
  Balancing reserves are sized to cover forecast errors. Knowing the P10–P90
  spread directly informs how much upward and downward reserve to procure,
  replacing rules of thumb with data-driven estimates.

**Renewable integration**
  Solar and wind output are inherently variable. Quantile forecasts let
  operators express the uncertainty of net load (demand minus renewables) in
  a form that feeds directly into stochastic unit-commitment models.

**Risk-aware scheduling**
  Energy trading strategies can be optimised against the full quantile
  distribution rather than a single scenario, improving expected profit while
  controlling tail risk.

.. note::

   The value of a probabilistic forecast depends entirely on its calibration.
   An over-confident P90 that is exceeded 25 % of the time provides false
   assurance and can lead to under-provisioning of reserves. Always validate
   calibration on held-out data before using quantile outputs in operational
   decisions.

Choosing Which Quantiles to Request
-------------------------------------

OpenSTEF lets you specify an arbitrary set of quantiles. Common choices are:

- ``[0.1, 0.5, 0.9]`` — compact three-band output suitable for dashboards and
  simple reserve sizing.
- ``[0.05, 0.25, 0.5, 0.75, 0.95]`` — five-band output that distinguishes
  "normal" uncertainty (P25–P75) from tail risk (P05/P95).
- ``[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]`` — nine quantiles for
  stochastic optimisation models that consume the full distribution.

Requesting more quantiles adds negligible computational cost because they are
all derived from the same underlying standard-deviation estimate. The only
practical constraint is that downstream consumers must be able to handle the
additional columns.

Related Pages
--------------

- :doc:`forecasting_basics` — how the point forecast (P50) is produced before
  quantile bands are added.
- :doc:`model_selection` — how model choice affects forecast accuracy and,
  indirectly, the width of prediction intervals.
- :doc:`reliability_and_fallback` — what happens to quantile output when the
  primary model is unavailable.