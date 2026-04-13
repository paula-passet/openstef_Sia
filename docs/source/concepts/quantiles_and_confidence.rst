Quantiles and Confidence Intervals
===================================

When a forecasting model produces a single number — "load will be 142 MW at 14:00" — it tells you
*what to expect* but nothing about *how confident to be*. OpenSTEF addresses this by producing
**probabilistic forecasts**: instead of one value, each forecast horizon carries a set of quantile
predictions that together describe the full uncertainty envelope around the expected outcome.

This page explains what those quantiles mean, how OpenSTEF generates them, and why they matter
for operational decision-making.

.. note:: [DIAGRAM: Time-series chart showing 24–48 hours of forecast output. Three shaded bands are drawn over the timeline: a wide outer band between P10 and P90 (light blue), a narrower inner band between P25 and P75 (medium blue), and a central line for P50 (the median forecast). Actual measured load is overlaid as a solid dark line. Annotations call out that ~80% of actual values fall within the P10–P90 band, and that the P50 line tracks the central tendency of the actuals.]

What a Quantile Forecast Is
----------------------------

A **quantile** at level *q* is the value below which a fraction *q* of outcomes are expected to
fall. In the context of energy load forecasting:

- **P10** (the 10th percentile) is a *low* estimate — only 10 % of outcomes should fall below it.
- **P50** (the median) is the central estimate — half of outcomes should fall below and half above.
- **P90** (the 90th percentile) is a *high* estimate — 90 % of outcomes should fall below it.

Together, P10 and P90 define an **80 % prediction interval**: under a well-calibrated model, the
true load will land inside this band roughly 80 times out of 100. This is a *prediction interval*,
not a confidence interval — it describes where future observations will fall, not where a
parameter estimate lies. The distinction matters: energy system operators care about individual
future events, so prediction intervals are the right tool.

OpenSTEF stores quantile columns in a ``ForecastDataset`` using the naming convention
``quantile_P10``, ``quantile_P50``, ``quantile_P90``, and so on for any additional quantile
levels requested. You can inspect which quantiles a dataset carries through its ``quantiles``
attribute:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import ForecastDataset

   # Suppose `forecast_df` is a DataFrame returned by a trained pipeline
   # with columns: quantile_P10, quantile_P50, quantile_P90
   dataset = ForecastDataset(forecast_df, sample_interval=timedelta(minutes=15))

   print(dataset.quantiles)   # [0.1, 0.5, 0.9]
   print(dataset.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF uses a post-processing approach rather than native quantile regression for most models.
The core component is ``ConfidenceIntervalApplicator``, a ``Transform`` that learns
**hour-of-day uncertainty patterns** from historical validation errors and then applies those
patterns to new point forecasts.

The process has two phases:

1. **Fit** — the applicator is given a ``ForecastDataset`` of validation-period predictions
   alongside the corresponding actuals. It computes the per-hour standard deviation of forecast
   errors, building a table of typical uncertainty for each hour of the day.

2. **Transform** — for a new forecast, the applicator looks up the hour-specific standard
   deviation and, assuming normally distributed errors, derives the requested quantile levels
   from that standard deviation.

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   # Define which quantiles you want in the output
   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
   )

   # Learn uncertainty from validation data
   # validation_dataset is a ForecastDataset covering the held-out period
   applicator.fit(validation_dataset)

   # Apply to a new forecast
   probabilistic_forecast = applicator.transform(new_forecast_dataset)

   # The result carries quantile columns
   print(probabilistic_forecast.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

The applicator enforces a key invariant: quantile ordering is always preserved
(P10 ≤ P50 ≤ P90). A companion transform, ``QuantileSorter``, can be added to any
post-processing pipeline to correct ordering violations that can arise when individual quantile
estimates are produced independently.

For cases where the normality assumption is too restrictive, ``IsotonicQuantileCalibrator``
provides a non-parametric alternative that recalibrates raw quantile predictions using isotonic
regression, adjusting them until the empirical coverage matches the nominal levels.

.. note::

   ``ConfidenceIntervalApplicator`` assumes forecast errors follow a normal distribution.
   This is a reasonable approximation for most grid-connected load forecasting tasks, but may
   underestimate tail risk for highly volatile or weather-sensitive assets.

Calibration: Are the Intervals Trustworthy?
--------------------------------------------

Generating quantile bands is only useful if they are **calibrated** — meaning a stated 80 %
interval actually contains the true outcome 80 % of the time. An over-confident model produces
intervals that are too narrow (coverage below the nominal level); an under-confident model
produces intervals that are too wide (coverage above the nominal level).

OpenSTEF provides ``QuantileProbabilityPlotter`` in the ``openstef-beam`` analysis package to
visualise calibration directly. It compares *forecasted probabilities* (the quantile levels you
requested) against *observed frequencies* (the fraction of actuals that actually fell below each
quantile threshold). A perfectly calibrated model traces the diagonal of this plot:

.. code-block:: python

   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )

   plotter = QuantileProbabilityPlotter()

   # `evaluation_report` is an EvaluationSubsetReport produced by the
   # openstef-beam evaluation pipeline
   fig = plotter.plot(
       observed_probs=evaluation_report.observed_probabilities,
       forecasted_probs=evaluation_report.forecasted_probabilities,
   )
   fig.show()

Points above the diagonal indicate that the model is *over-confident* for those quantile levels
(the true coverage is higher than claimed, so the intervals are too wide). Points below the
diagonal indicate *under-confidence* (intervals are too narrow). Use these plots after retraining
or when deploying a model to a new asset to verify that uncertainty estimates remain valid.

Operational Relevance
----------------------

Probabilistic forecasts translate directly into better operational decisions. Some concrete
examples:

- **Congestion management** — a transmission operator can use the P90 band to identify hours
  where peak load *might* exceed a cable rating, even if the P50 forecast stays within limits.
  Acting on the P50 alone would systematically underestimate risk.

- **Reserve procurement** — balancing responsible parties size spinning reserve based on forecast
  uncertainty. A narrow P10–P90 band on a calm weekday night calls for less reserve than a wide
  band during a storm.

- **Imbalance cost reduction** — energy traders can bid closer to the P50 when uncertainty is
  low and shift bids toward the P70 or P80 when the model signals high uncertainty, reducing
  expected imbalance penalties.

- **Alerting thresholds** — monitoring systems can trigger alerts when the P90 forecast exceeds
  a threshold rather than waiting for the P50 to cross it, giving operators more lead time.

In each case, the key insight is that **the width of the interval is itself a forecast** — it
tells you how much the situation might deviate from the central expectation, and that information
has independent operational value.

Choosing Quantile Levels
-------------------------

OpenSTEF does not impose a fixed set of quantiles. You specify which levels you need when
configuring the ``ConfidenceIntervalApplicator`` or the broader model pipeline. Common choices:

- **P10, P50, P90** — the minimum useful set; gives an 80 % interval and a central estimate.
- **P05, P25, P50, P75, P95** — finer granularity; useful when downstream systems need to
  distinguish between moderate and extreme uncertainty.
- **P50 only** — equivalent to a point forecast; valid when only the central estimate is needed
  and downstream systems do not consume uncertainty information.

Adding more quantile levels increases the richness of the uncertainty description but also
increases the storage footprint of the ``ForecastDataset``. For most operational use cases,
three to five quantile levels are sufficient.

.. note::

   Quantile levels are specified as ``Quantile`` typed values (floats in the range (0, 1)).
   The column naming convention ``quantile_P10``, ``quantile_P50``, etc. is derived
   automatically from the numeric level by multiplying by 100 and zero-padding to two digits.

Summary
--------

- A quantile forecast replaces a single point estimate with a set of percentile values that
  describe the probability distribution of future outcomes.
- OpenSTEF generates quantiles through post-processing: ``ConfidenceIntervalApplicator`` learns
  hour-specific uncertainty from validation errors and applies it to new forecasts.
- Calibration — whether stated coverage matches observed coverage — can be verified with
  ``QuantileProbabilityPlotter``.
- The width of the prediction interval is operationally meaningful: it drives reserve sizing,
  congestion risk assessment, and trading strategy.

For background on how the underlying point forecast is produced, see :doc:`forecasting_basics`.
For guidance on which model architecture to use for a given asset type, see :doc:`model_selection`.
If you are concerned about what happens when the model itself is unavailable, see
:doc:`reliability_and_fallback`.