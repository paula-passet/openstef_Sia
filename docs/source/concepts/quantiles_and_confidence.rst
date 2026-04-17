Quantiles and Confidence Intervals
===================================

Short-term energy forecasts in OpenSTEF are *probabilistic*: rather than
producing a single number, the library outputs a set of quantile predictions
that together describe the full uncertainty of the forecast. This page explains
what those quantiles mean, how they are produced, and why they matter for
day-to-day grid operations.

For background on what a forecast is and why it is needed, see
:doc:`forecasting_basics`. For information on how model reliability is
maintained in production, see :doc:`reliability_and_fallback`.

What a Quantile Forecast Is
----------------------------

A **quantile** at level *p* is the value below which a fraction *p* of
outcomes are expected to fall. When OpenSTEF returns a ``quantile_P10``
column, it is saying: "we expect the true load to be *below* this value 10 %
of the time." Symmetrically, ``quantile_P90`` is the value that should be
exceeded only 10 % of the time.

The median forecast — ``quantile_P50`` — is the value that is equally likely
to be an over- or under-estimate. It is the closest equivalent to a
traditional "point forecast", but it arrives alongside the rest of the
distribution rather than in isolation.

A typical OpenSTEF forecast dataset contains several quantile columns at once:

.. code-block:: python

   from openstef_core.types import Q

   QUANTILES = [Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)]

The resulting ``ForecastDataset`` will have columns named
``quantile_P05``, ``quantile_P10``, …, ``quantile_P95``, plus the median
``quantile_P50``.

.. note:: [VISUALIZATION: Time-series plot showing actual load as a line, P50 as a second line, and shaded bands between P10–P90 and P05–P95 illustrating widening uncertainty at longer horizons]

Prediction Intervals vs. Confidence Intervals
----------------------------------------------

These two terms are often confused, and the distinction matters in practice.

A **prediction interval** covers where the *next individual observation* will
land. If the P10–P90 band is a prediction interval, roughly 80 % of future
measurements should fall inside it.

A **confidence interval** covers uncertainty about a *model parameter* — for
example, the true mean load at a given hour. Confidence intervals are narrower
because averaging reduces noise.

OpenSTEF produces **prediction intervals**. The goal is to bound the actual
measured load, not to characterise the model's parameter uncertainty. When you
see a shaded band on an OpenSTEF forecast plot, you are looking at the region
where the meter reading is expected to land with the stated probability.

How Quantiles Are Generated
----------------------------

OpenSTEF uses two complementary mechanisms to attach uncertainty to a
point forecast.

**Hour-specific standard deviations (ConfidenceIntervalApplicator)**

After training, the ``ConfidenceIntervalApplicator`` examines validation
errors grouped by hour of day (0–23). It computes the standard deviation of
errors for each hour and, for multi-horizon forecasts, models how uncertainty
grows with lead time using an exponential saturation curve:

.. math::

   \sigma(t) = a \cdot (1 - e^{-t/\tau}) + b

where *t* is hours ahead and *τ = far_horizon / 4*. This captures the
well-known pattern that uncertainty grows quickly in the first few hours and
then levels off.

Quantile values are then derived from the median prediction and the
hour-specific standard deviation, assuming normally distributed errors:

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.transforms.postprocessing import ConfidenceIntervalApplicator

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # fit on (validation_input, validation_predictions) pair
   applicator.fit(validation_data)

   # transform adds quantile_P10, quantile_P50, quantile_P90 columns
   forecast_with_bands = applicator.transform(forecast_data)
   print(forecast_with_bands.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

The normality assumption works well for energy load forecasting but may not
hold in all domains.

**Isotonic calibration (IsotonicQuantileCalibrator)**

Even well-trained models can produce *miscalibrated* quantiles — for example,
the P90 band might actually contain 95 % of observations rather than 90 %.
The ``IsotonicQuantileCalibrator`` corrects this by learning a monotonic
mapping from raw predicted quantile values to calibrated values, using
isotonic regression on a held-out validation set:

.. code-block:: python

   from openstef_models.transforms.postprocessing import IsotonicQuantileCalibrator
   from openstef_core.mixins import TransformPipeline

   # Combine both postprocessing steps in a pipeline
   postprocessing = TransformPipeline([
       ConfidenceIntervalApplicator(
           quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
       ),
       IsotonicQuantileCalibrator(),
   ])

   postprocessing.fit(validation_data)
   calibrated_forecast = postprocessing.transform(forecast_data)

After calibration, if the model says P90 it should genuinely mean that 90 %
of observations fall below that line. You can verify this by plotting
*expected coverage* (the quantile level) against *observed coverage* (the
fraction of actuals below the predicted quantile) — a well-calibrated model
produces a diagonal line.

.. note:: [VISUALIZATION: Calibration reliability diagram (reliability plot) showing expected quantile coverage on the x-axis vs. observed coverage on the y-axis, with a diagonal reference line and two curves — one before and one after isotonic calibration]

Interpreting the Forecast in Practice
---------------------------------------

Reading a probabilistic forecast correctly is as important as generating one.
A few rules of thumb:

- **P50 is not a "safe" operating point.** By definition, the true load
  exceeds P50 half the time. For capacity planning, use a higher quantile.
- **The width of the band reflects model confidence.** A narrow P10–P90 band
  at a given timestamp means the model is confident; a wide band signals high
  uncertainty — perhaps because of unusual weather or a public holiday.
- **Quantile ordering is guaranteed.** OpenSTEF enforces
  ``quantile_P10 ≤ quantile_P50 ≤ quantile_P90`` as an invariant. You will
  never see a crossing of quantile lines in the output.
- **Uncertainty grows with lead time.** A forecast 48 hours ahead will have
  wider bands than one 1 hour ahead, reflecting the exponential decay model
  described above.

Operational Use Cases
----------------------

Different quantiles serve different operational decisions:

- **Grid congestion management** — Use P90 or P95 as a conservative upper
  bound when deciding whether a cable or transformer is at risk of overload.
  Acting on P50 would underestimate the risk half the time.
- **Renewable curtailment scheduling** — Use P10 as a lower bound on expected
  solar or wind generation to ensure minimum dispatch commitments can be met.
- **Imbalance cost minimisation** — Traders can select the quantile that
  minimises expected cost given their asymmetric penalty structure. If the
  cost of being short is twice the cost of being long, the optimal bid
  corresponds to the P67 quantile.
- **Alarm thresholds** — Trigger an alert only when the P95 forecast exceeds
  a safety limit, reducing false positives compared to using the median.

Visualising Forecast Uncertainty
----------------------------------

OpenSTEF provides ``ForecastTimeSeriesPlotter`` for interactive visualisation
of the full quantile output:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,      # P50
           quantiles=forecast.quantiles_data,    # full band data
       )
       .plot()
   )
   fig.update_layout(
       title="Energy Load Forecast with Prediction Intervals",
       yaxis_title="Load (MW)",
   )
   fig.show()

.. note:: [VISUALIZATION: Interactive Plotly chart with actual measurements as a solid line, P50 forecast as a dashed line, and two shaded regions for the P10–P90 and P05–P95 bands, with a legend and hover tooltips showing all quantile values at each timestamp]

Checking Calibration Quality
-----------------------------

After deploying a model, it is good practice to periodically verify that the
quantile bands remain calibrated against real observations. A simple check
computes the *empirical coverage* for each quantile level — the fraction of
actuals that fell below the predicted quantile:

.. code-block:: python

   import pandas as pd

   def empirical_coverage(actuals: pd.Series, quantile_forecasts: pd.DataFrame) -> pd.Series:
       """Compute observed coverage for each quantile column."""
       coverage = {}
       for col in quantile_forecasts.columns:
           level = float(col.replace("quantile_P", "")) / 100
           coverage[level] = (actuals <= quantile_forecasts[col]).mean()
       return pd.Series(coverage, name="observed_coverage")

   coverage = empirical_coverage(
       actuals=validation_actuals,
       quantile_forecasts=calibrated_forecast.data,
   )
   print(coverage)
   # 0.10    0.101
   # 0.50    0.498
   # 0.90    0.903
   # dtype: float64

Values close to the diagonal (observed ≈ expected) indicate a well-calibrated
model. Systematic deviations — for example, P90 covering 97 % of actuals —
suggest the bands are too wide and the ``IsotonicQuantileCalibrator`` should
be re-fitted on more recent validation data.

.. note::

   Calibration can drift over time as load patterns change. Re-fitting the
   ``IsotonicQuantileCalibrator`` on a rolling validation window is a
   lightweight way to keep uncertainty estimates accurate without retraining
   the full model. See :doc:`reliability_and_fallback` for broader strategies
   on keeping production forecasts healthy.