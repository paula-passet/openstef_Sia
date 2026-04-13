Quantiles and Confidence Intervals
===================================

Short-term energy forecasting rarely benefits from a single number. Grid operators, energy traders,
and balancing teams need to know not just *what* is expected to happen, but *how uncertain* that
expectation is. OpenSTEF addresses this by producing **probabilistic forecasts** — sets of quantile
predictions that describe the full range of likely outcomes rather than a single point estimate.

This page explains what quantiles are, how OpenSTEF generates and calibrates them, and why they
matter for day-to-day operational decisions.

.. note:: [DIAGRAM: Time-series chart showing a 48-hour forecast horizon. The x-axis is time, the y-axis is power (MW). Three shaded bands are drawn: a wide outer band between P10 and P90 (light blue), a narrower inner band between P25 and P75 (medium blue), and a central line for P50 (dark blue). Actual observed outcomes are overlaid as a black line. The bands widen as the forecast horizon increases, illustrating growing uncertainty further into the future.]

What Quantiles Are
------------------

A **quantile** at probability level *p* is a threshold value such that the true outcome falls below
that threshold with probability *p*. In energy forecasting:

- **P10** (the 10th percentile) means there is a 10 % chance the actual load will be *below* this
  value — it represents the lower bound of a plausible range.
- **P50** (the median) is the central estimate: the actual outcome is equally likely to be above or
  below it.
- **P90** (the 90th percentile) means there is a 10 % chance the actual load will *exceed* this
  value — it represents the upper bound.

Together, P10 and P90 form a **prediction interval** that should contain the true outcome 80 % of
the time. The width of this interval is a direct measure of forecast uncertainty: a narrow band
signals high confidence; a wide band signals high uncertainty.

OpenSTEF uses the ``Quantile`` type from ``openstef_core`` to represent these probability levels
throughout the library:

.. code-block:: python

   from openstef_core.types import Quantile

   p10 = Quantile(0.1)
   p50 = Quantile(0.5)
   p90 = Quantile(0.9)

   print(p50)  # 0.5

You specify which quantiles you want when you instantiate a forecaster. The library then produces
a separate prediction column for each requested level:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=6))],
   )

   forecaster.fit(training_data)       # doctest: +SKIP
   predictions = forecaster.predict(test_data)  # doctest: +SKIP
   # predictions.data contains columns: quantile_P10, quantile_P50, quantile_P90

How OpenSTEF Generates Quantiles
---------------------------------

OpenSTEF uses two complementary strategies to produce well-calibrated quantile predictions.

**Strategy 1 — Native quantile regression**

Tree-based models such as ``XGBoostForecaster`` and ``LGBMForecaster`` support native quantile
regression: each quantile is trained as a separate objective, directly minimising the pinball loss
for that probability level. This approach captures asymmetric uncertainty naturally and requires no
distributional assumptions.

**Strategy 2 — Uncertainty learned from validation errors**

The ``ConfidenceIntervalApplicator`` transform learns hour-specific uncertainty from residuals
observed on a held-out validation set. It fits a standard deviation for each hour of the day (0–23)
and, for multi-horizon forecasts, models how uncertainty grows with lead time using an exponential
decay curve:

.. math::

   \sigma(t) = a \cdot (1 - e^{-t/\tau}) + b

where *t* is hours ahead and *τ* = far_horizon / 4. This reflects the well-known pattern that
forecast uncertainty grows quickly at first and then levels off. Once the standard deviation is
known, quantiles are derived assuming normally distributed errors:

.. code-block:: text

   P10 = median − 1.28 × σ
   P90 = median + 1.28 × σ

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   applicator.fit((validation_data, validation_predictions))  # doctest: +SKIP
   result = applicator.transform((new_input_data, new_predictions))  # doctest: +SKIP

   # result.data now contains: quantile_P10, quantile_P50, quantile_P90

.. note::

   The ``ConfidenceIntervalApplicator`` assumes normally distributed forecast errors. This
   assumption holds well for aggregated energy loads but may be less appropriate for highly
   intermittent or low-aggregation series such as individual customer connections.

Calibration: Are the Intervals Honest?
----------------------------------------

Generating quantiles is only half the job. A P90 interval is only useful if the actual outcome
really does exceed it roughly 10 % of the time — a property called **calibration**.

OpenSTEF provides the ``IsotonicQuantileCalibrator`` transform to correct systematic biases in raw
quantile predictions. It learns a monotonic mapping from predicted quantile values to empirically
observed quantile values using isotonic regression:

.. code-block:: python

   from openstef_models.transforms.postprocessing.isotonic_quantile_calibrator import (
       IsotonicQuantileCalibrator,
   )

   calibrator = IsotonicQuantileCalibrator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   calibrator.fit(validation_dataset)   # doctest: +SKIP
   calibrated = calibrator.transform(raw_predictions)  # doctest: +SKIP

The calibrator also enforces **monotonic ordering** across quantiles — that is, it guarantees
P10 ≤ P50 ≤ P90 at every time step. If the raw model produces crossing quantiles (a common
artefact of independent quantile regression), the ``QuantileSorter`` post-processing transform
corrects this automatically.

Validating Calibration with the Probability Plotter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's built-in ``QuantileProbabilityPlotter`` produces calibration plots that compare
*predicted* probabilities against *observed* frequencies. A perfectly calibrated model produces a
diagonal line: if you predict P90, the actual outcome should exceed that threshold exactly 10 % of
the time.

.. code-block:: python

   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )

   plotter = QuantileProbabilityPlotter()
   fig = plotter.plot(forecast_df, actuals_df)  # doctest: +SKIP
   fig.show()  # doctest: +SKIP

Use these plots to answer questions such as:

- Are 90 % prediction intervals too wide or too narrow?
- Does the model over-estimate uncertainty at night and under-estimate it during morning ramps?
- Which of two candidate models provides better-calibrated uncertainty?

Why Quantiles Matter for Operations
-------------------------------------

A point forecast answers "what do we expect?" A probabilistic forecast additionally answers "how
wrong could we be, and in which direction?" This distinction is critical in energy systems.

**Congestion management**
  Grid operators managing congestion need to know the *worst plausible case*, not just the expected
  load. Acting on P90 rather than P50 provides a safety margin against unexpected peaks. OpenSTEF's
  documentation on use cases describes how rMAE at the 50th quantile and rCRPS are used as key
  metrics for congestion forecasts.

**Energy trading and balancing**
  Traders with asymmetric cost structures — where over-procurement is cheaper than under-procurement,
  or vice versa — should not minimise mean squared error. They should act on the quantile that
  matches their cost ratio. A P70 forecast, for instance, is the rational decision threshold when
  the cost of being short is twice the cost of being long.

**Communicating uncertainty to stakeholders**
  Presenting a shaded confidence band alongside a central forecast line communicates uncertainty
  intuitively to non-technical audiences. The width of the band at a glance tells operators whether
  a forecast is reliable enough to act on.

**Detecting model degradation**
  When prediction intervals become systematically too narrow (actual outcomes fall outside them more
  often than expected), this is an early warning that the model's uncertainty estimates are stale —
  even if the point forecast accuracy has not yet deteriorated visibly.

Prediction Intervals vs. Confidence Intervals
-----------------------------------------------

These two terms are often confused, and the distinction matters:

- A **confidence interval** quantifies uncertainty about a *model parameter* — for example, the
  true mean load at a given hour. It shrinks as you collect more data.
- A **prediction interval** quantifies uncertainty about a *future individual observation*. It does
  not shrink to zero even with infinite data, because individual outcomes are inherently variable.

OpenSTEF produces **prediction intervals**. The P10–P90 band around a forecast tells you where a
single future measurement is likely to fall, not where the long-run average will be. This is the
correct framing for operational decisions that depend on what will actually happen at a specific
time step.

.. note::

   The term "confidence interval" is used colloquially in the energy industry to mean prediction
   interval. OpenSTEF's ``ConfidenceIntervalApplicator`` follows this convention in its name, but
   its output is a prediction interval in the statistical sense.

Choosing Which Quantiles to Request
-------------------------------------

There is no universal set of quantiles that suits every application. Some guidelines:

- **Always include P50.** It is the central estimate and the reference point for all other
  quantiles.
- **P10 and P90** give an 80 % prediction interval — a common default for operational dashboards.
- **P05 and P95** give a 90 % interval, appropriate when the cost of being caught outside the
  interval is high.
- **Fine-grained sets** (e.g., P10, P25, P50, P75, P90) allow downstream consumers to choose their
  own risk threshold without re-running the forecast.

Adding more quantiles increases computation time roughly linearly when using native quantile
regression, so balance granularity against pipeline performance.

.. code-block:: python

   from openstef_core.types import Quantile

   # Fine-grained quantile set for a trading application
   quantiles = [Quantile(q) for q in [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]]

Related Topics
--------------

- :doc:`forecasting_basics` — Introduction to short-term forecasting and how point forecasts are
  produced before quantiles are added.
- :doc:`model_selection` — Comparison of available forecasters and their native support for
  quantile regression.
- :doc:`feature_engineering` — How input features influence both point accuracy and the width of
  prediction intervals.
- :doc:`reliability_and_fallback` — What happens to quantile outputs when a model falls back to a
  simpler strategy.