Quantiles and Confidence Intervals
===================================

When OpenSTEF generates a forecast, it does not simply produce a single number for each future
time step. Instead, it produces a *distribution* of plausible outcomes expressed as quantiles.
This page explains what quantiles are, how to read them, and why probabilistic forecasts are
essential for real-world energy grid operations.

.. note:: [DIAGRAM: Time-series plot showing a 24-hour ahead forecast with three shaded bands. The
   darkest central band spans P10–P90, a medium band spans P25–P75, and a thin line marks the P50
   (median) point forecast. Actual measured load values are overlaid as a solid line, falling inside
   the P10–P90 band most of the time but occasionally breaching it. The x-axis shows time of day;
   the y-axis shows load in MW.]

What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What load level will be exceeded only X% of the
time?"* The P10 quantile, for example, is the value below which the actual outcome is expected to
fall 10% of the time — and above which it is expected to fall 90% of the time. The P50 quantile
is the median: equally likely to be above or below the true outcome. P90 is the value that the
actual outcome is expected to exceed only 10% of the time.

Taken together, a set of quantiles — say P10, P50, and P90 — describes the *shape* of forecast
uncertainty at each future time step. The gap between P10 and P90 is wide when the model is
uncertain (e.g., far ahead in time, or during volatile weather) and narrow when the model is
confident.

OpenSTEF represents quantile levels using the ``Quantile`` type from ``openstef_core.types``.
Column names in forecast output follow the convention ``quantile_P10``, ``quantile_P50``,
``quantile_P90``, and so on:

.. code-block:: python

   import pandas as pd
   from openstef_core.types import Quantile

   # Quantile values are simple floats wrapped in a type alias
   q10 = Quantile(0.1)
   q50 = Quantile(0.5)
   q90 = Quantile(0.9)

   # A ForecastDataset produced by OpenSTEF will contain columns like:
   # quantile_P10, quantile_P50, quantile_P90
   print(q10)   # 0.1
   print(q90)   # 0.9

How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF supports two complementary strategies for producing quantile forecasts.

**Direct quantile regression** trains the model to minimise the *pinball loss* (also called the
quantile loss) for each target quantile simultaneously. Models such as ``GBLinearForecaster``
accept a ``quantiles`` argument at construction time and produce one output column per quantile
during prediction:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.forecasters.gb_linear import GBLinearForecaster

   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime(timedelta(hours=1))],
   )

   forecaster.fit(training_data)       # doctest: +SKIP
   forecast = forecaster.predict(test_data)  # doctest: +SKIP

   # forecast.data contains columns: quantile_P10, quantile_P50, quantile_P90
   print(forecast.quantiles)  # [0.1, 0.5, 0.9]   # doctest: +SKIP

**Post-hoc confidence interval application** is handled by ``ConfidenceIntervalApplicator``. This
transform learns hour-specific uncertainty from validation errors — fitting a normal distribution
to residuals for each hour of the day — and then applies those learned standard deviations to new
point predictions to derive quantile bands:

.. code-block:: python

   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )
   from openstef_core.types import Quantile

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # Fit on validation data to learn hour-specific uncertainty
   applicator.fit(validation_dataset)   # doctest: +SKIP

   # Apply to new predictions to add quantile columns
   forecast_with_intervals = applicator.transform(new_forecast_dataset)  # doctest: +SKIP

The ``ConfidenceIntervalApplicator`` assumes that forecast errors are approximately normally
distributed. This is a reasonable assumption for aggregated energy load, but may be less accurate
for highly volatile or low-aggregation time series such as individual customer connections.

Confidence Intervals vs. Prediction Intervals
-----------------------------------------------

These two terms are sometimes used interchangeably in practice, but they refer to different
statistical concepts:

- A **confidence interval** quantifies uncertainty about an estimated *parameter* (for example,
  the mean load at 09:00 on a Monday). It narrows as more training data is collected.
- A **prediction interval** quantifies uncertainty about a *single future observation*. It must
  account for both the model's parameter uncertainty and the inherent variability of the process
  being forecast.

In energy forecasting, the intervals shown in an OpenSTEF forecast are **prediction intervals**:
they describe the range within which the actual measured load is expected to fall with a given
probability. A well-calibrated P90 prediction interval should contain the true outcome 90% of the
time when evaluated over many forecasts.

Calibration: Are the Intervals Trustworthy?
--------------------------------------------

Generating quantile columns is not enough — those quantiles must be *calibrated*. A P90 interval
that only captures the true outcome 60% of the time is not a P90 interval in any meaningful sense.

OpenSTEF provides ``IsotonicQuantileCalibrator`` to correct systematic miscalibration after
training, and ``QuantileSorter`` to enforce the monotonic ordering constraint
(P10 ≤ P50 ≤ P90) that can be violated by independent quantile regression models:

.. code-block:: python

   from openstef_models.transforms.postprocessing.isotonic_quantile_calibrator import (
       IsotonicQuantileCalibrator,
   )
   from openstef_models.transforms.postprocessing.quantile_sorter import QuantileSorter

   calibrator = IsotonicQuantileCalibrator()
   calibrator.fit(validation_forecast_dataset)           # doctest: +SKIP
   calibrated = calibrator.transform(raw_forecast_dataset)  # doctest: +SKIP

   sorter = QuantileSorter()
   ordered = sorter.transform(calibrated)  # doctest: +SKIP

To *visualise* calibration quality, use ``QuantileProbabilityPlotter`` from
``openstef_beam``. It compares the forecasted quantile levels against the fraction of actual
outcomes that fell below each quantile — a perfectly calibrated model produces a diagonal line:

.. code-block:: python

   from openstef_beam.analysis.plots.quantile_probability_plotter import (
       QuantileProbabilityPlotter,
   )
   from openstef_core.types import Quantile

   plotter = QuantileProbabilityPlotter()
   plotter.add_model(
       model_name="GBLinear",
       forecasted_probs=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       observed_probs=[Quantile(0.08), Quantile(0.49), Quantile(0.88)],
   )
   fig = plotter.plot(title="Quantile calibration — GBLinear vs. baseline")
   fig.show()  # doctest: +SKIP

A model whose curve bows above the diagonal is *over-confident* (intervals are too narrow); one
that bows below is *under-confident* (intervals are unnecessarily wide).

.. note::

   ``QuantileProbabilityPlotter`` supports multiple models on the same axes via repeated
   ``add_model()`` calls, making it straightforward to compare calibration across model variants.

Why Quantiles Matter for Grid Operations
-----------------------------------------

A point forecast tells operators what is *most likely* to happen. A quantile forecast tells them
what the *range of plausible outcomes* looks like — and that distinction drives several critical
operational decisions.

**Congestion management.** Grid operators managing capacity constraints need to know not just the
expected peak load, but the probability that load will exceed a thermal limit. The P90 quantile
directly answers this: if P90 exceeds the cable rating, there is a 10% chance of congestion even
if the median forecast looks safe. OpenSTEF's congestion management use case explicitly optimises
for high-quantile accuracy near peak periods.

**Reserve procurement.** Balancing responsible parties and transmission system operators use
upper-bound quantiles to size operating reserves. Procuring reserves based only on the P50
forecast would leave the system exposed in adverse but plausible scenarios.

**Asymmetric cost functions.** The cost of under-forecasting (unexpected congestion, emergency
re-dispatch) is often much higher than the cost of over-forecasting (unnecessary reserve
activation). Quantile forecasts let operators choose the quantile that minimises their specific
cost function rather than always using the median.

**Communicating uncertainty to stakeholders.** Presenting a single number implies false precision.
Quantile bands make it transparent that forecasts carry inherent uncertainty, which is especially
important when communicating with upstream network operators such as transmission system operators.

Choosing Which Quantiles to Request
-------------------------------------

OpenSTEF does not impose a fixed set of quantiles. You specify them at model construction time,
and the library will produce one output column per quantile. Common choices are:

- **P10, P50, P90** — a minimal set that captures the median and a symmetric 80% prediction
  interval. Suitable for most operational dashboards.
- **P5, P25, P50, P75, P95** — a richer set that allows shaded fan charts and finer risk
  analysis.
- **P50 only** — equivalent to a point forecast; useful during initial model development before
  adding uncertainty quantification.

There is a computational cost to requesting many quantiles with direct quantile regression
models, since each quantile requires its own loss term. Post-hoc methods like
``ConfidenceIntervalApplicator`` add quantiles at negligible extra cost once the standard
deviation has been learned.

.. note::

   The ordering invariant P10 ≤ P25 ≤ P50 ≤ P75 ≤ P90 is not guaranteed by all model backends.
   Always apply ``QuantileSorter`` in production pipelines to prevent quantile crossing, which
   would make the forecast logically inconsistent.

Related Topics
---------------

- :doc:`forecasting_basics` — introduces the overall forecasting workflow and how point forecasts
  are produced before uncertainty is added.
- :doc:`model_selection` — compares available forecasting models and their native support for
  quantile regression.
- :doc:`feature_engineering` — covers the input features that drive both point forecast accuracy
  and the width of prediction intervals.
- :doc:`reliability_and_fallback` — explains what happens to quantile forecasts when a model
  fails and a fallback strategy is activated.