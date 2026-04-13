Quantiles and Confidence Intervals
===================================

Short-term energy forecasts are never perfect. Weather changes unexpectedly, consumption
patterns shift, and grid behaviour has inherent variability. A single-number forecast — the
expected load at 14:00 tomorrow — tells an operator *what to plan for*, but it says nothing
about *how confident to be*. Probabilistic forecasts address this gap by expressing uncertainty
directly in the forecast output, and quantiles are the primary language OpenSTEF uses to do so.

This page explains what quantiles are, how OpenSTEF produces them, and why they matter for
real-world grid operations.

.. note::

   This page focuses on probabilistic forecast outputs. For an introduction to the forecasting
   workflow itself, see :doc:`forecasting_basics`. For guidance on choosing a model that
   supports quantile output, see :doc:`model_selection`.


What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What value will not be exceeded X% of the time?"*
The 10th percentile (P10) is a value the actual outcome will fall below only 10% of the time.
The 90th percentile (P90) is a value the actual outcome will fall below 90% of the time. The
50th percentile (P50) is the median — the middle of the distribution, and typically the closest
to what most people think of as "the forecast".

Together, P10, P50, and P90 define a **prediction band**: a range that should contain the true
outcome 80% of the time. This band is sometimes called an 80% prediction interval.

OpenSTEF represents quantiles using the ``Quantile`` type from ``openstef_core.types``. Forecast
output columns are named according to this convention — ``quantile_P10``, ``quantile_P50``,
``quantile_P90`` — making them easy to identify and process downstream.

.. mermaid:: /diagrams/concepts/quantiles_and_confidence_diagram_1.mmd


How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF produces quantile forecasts through a post-processing step that sits after the core
point-forecast model. The ``ConfidenceIntervalApplicator`` transform learns hour-specific
uncertainty patterns from validation data and applies them to new predictions.

The process has two phases:

**Fitting (learning uncertainty):** During training, the applicator computes forecast errors on
a held-out validation set. It calculates the standard deviation of those errors separately for
each hour of the day (hours 0–23). This captures the fact that uncertainty is not uniform across
the day — early morning hours may be more predictable than peak-demand afternoons, for example.
For multi-horizon forecasts, separate standard deviations are stored per lead time.

**Transforming (applying uncertainty):** At inference time, the applicator looks up the
appropriate standard deviation for each prediction's hour and lead time. It then converts that
standard deviation to quantile values assuming a normal distribution:

.. code-block:: python

   # Conceptually, for a given prediction hour:
   # P10 = median - 1.28 * std
   # P50 = median
   # P90 = median + 1.28 * std

For multi-horizon forecasts, uncertainty grows with lead time following an exponential decay
model: ``sigma(t) = a * (1 - exp(-t/tau)) + b``. This reflects the empirical observation that
forecast uncertainty increases quickly over the first few hours and then levels off.

.. note::

   The normal-distribution assumption works well for aggregated energy load forecasting. For
   highly asymmetric or heavy-tailed distributions — such as individual customer forecasts with
   rare large spikes — consider whether this assumption holds for your use case.


Working with Quantile Forecasts in Code
-----------------------------------------

The following example shows how to configure a forecaster with quantile output and apply the
``ConfidenceIntervalApplicator`` post-processing transform.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   # Define the quantiles you want in your forecast output
   quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]

   # Instantiate the applicator
   applicator = ConfidenceIntervalApplicator(quantiles=quantiles)

   # Fit on validation data (ForecastDataset containing validation predictions)
   applicator.fit(validation_forecast_dataset)

   # Apply to new predictions — output columns: quantile_P10, quantile_P50, quantile_P90
   probabilistic_forecast = applicator.transform(new_forecast_dataset)

   # Access the learned per-hour standard deviations
   print(applicator.standard_deviation)

The resulting ``ForecastDataset`` contains a column for each requested quantile. The ordering
invariant is always maintained: ``quantile_P10 <= quantile_P50 <= quantile_P90``. If a model
produces quantile outputs that violate this ordering (which can happen with some regression
approaches), the ``QuantileSorter`` transform corrects this automatically.

For cases where quantile outputs need further refinement, the ``IsotonicQuantileCalibrator``
applies isotonic regression to ensure that the empirical coverage of each quantile matches its
nominal level. See the section on calibration below.


Confidence Intervals vs. Prediction Intervals
-----------------------------------------------

These two terms are often used interchangeably in practice, but they have distinct meanings:

- A **prediction interval** covers where a *single future observation* will fall, with a given
  probability. This is what OpenSTEF's quantile bands represent: "the actual load measurement
  will fall between P10 and P90 approximately 80% of the time."

- A **confidence interval** covers where the *true mean* of a process lies, given uncertainty
  in the model parameters. This is a statistical concept more relevant to model evaluation than
  to operational forecasting.

When operators talk about "confidence" in the context of energy forecasting, they almost always
mean prediction intervals. OpenSTEF's documentation and API use "confidence interval" in this
operational sense — as a synonym for the quantile band that bounds likely outcomes.


Calibration: Are the Quantiles Trustworthy?
---------------------------------------------

A quantile forecast is *calibrated* if its stated probabilities match observed frequencies.
A well-calibrated P90 should be exceeded by actual outcomes roughly 10% of the time — no more,
no less. If the P90 is exceeded 30% of the time, the model is underestimating uncertainty
(overconfident). If it is exceeded only 1% of the time, the bands are too wide (underconfident).

OpenSTEF provides the ``QuantileProbabilityPlotter`` for visualising calibration:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )

   plotter = QuantileProbabilityPlotter()

   # forecasted_probs: the quantile levels your model predicted
   # observed_probs: the empirical frequencies at which those levels were actually hit
   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.7), Quantile(0.9)]
   observed   = [Quantile(0.12), Quantile(0.28), Quantile(0.52), Quantile(0.71), Quantile(0.88)]

   plotter.add_model("GBLinear", forecasted, observed)
   fig = plotter.plot(title="Quantile Calibration — Substation A")
   fig.show()

The resulting plot shows each model's calibration curve against the ideal diagonal. Points
close to the diagonal indicate a well-calibrated model. Systematic deviation above the diagonal
means the model is overconfident; deviation below means it is underconfident.

For comparing calibration across many forecast targets simultaneously, the
``QuantileCalibrationBoxPlotter`` produces boxplots of calibration error distributions per
quantile level, making it easy to spot systematic biases across a fleet of substations.


Why Quantiles Matter for Grid Operations
------------------------------------------

A point forecast tells an operator what to expect. A quantile forecast tells them how much to
hedge. This distinction has direct operational consequences:

**Congestion management.** Grid operators managing congestion need to know not just the expected
load, but the probability that load will exceed a safe threshold. A P90 forecast that crosses
the thermal limit of a cable is an actionable signal even if the P50 does not. OpenSTEF's
quantile outputs are designed with this use case in mind — the rMAE at the 50th quantile during
peak periods and the rCRPS (continuous ranked probability score) are key metrics for congestion
management models.

**Energy balancing and procurement.** Traders and balance-responsible parties use quantile
forecasts to optimise procurement under uncertainty. Buying to the P50 minimises expected cost;
buying to a higher quantile provides a buffer against upward surprises. The optimal quantile
depends on the asymmetry of imbalance costs.

**Communicating uncertainty to stakeholders.** A shaded band on a forecast chart is far more
informative than a single line. Quantile outputs make it straightforward to communicate
forecast confidence to control room operators, asset managers, and upstream network operators.

**Fallback and anomaly detection.** When actual measurements fall outside the expected quantile
band, this is a signal worth investigating — it may indicate a sensor fault, an unusual event,
or model degradation. See :doc:`reliability_and_fallback` for how OpenSTEF handles these
situations in production.


Summary
--------

Quantile forecasts express uncertainty as a set of percentile bounds rather than a single
predicted value. OpenSTEF generates these bounds through the ``ConfidenceIntervalApplicator``,
which learns hour-specific uncertainty from validation errors and applies it at inference time.
The ``IsotonicQuantileCalibrator`` and ``QuantileSorter`` transforms ensure that outputs are
well-ordered and empirically calibrated. Built-in plotting tools make it straightforward to
validate calibration before deploying a model to production.

For the next step, see :doc:`model_selection` to understand which OpenSTEF models support
native quantile regression versus post-hoc uncertainty estimation.