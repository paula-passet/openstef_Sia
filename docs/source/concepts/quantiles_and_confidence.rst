Quantiles and Confidence Intervals
===================================

Probabilistic forecasting goes beyond predicting a single number. Instead of
asking "what will the load be at 14:00 tomorrow?", it asks "what is the
*distribution* of likely loads at 14:00 tomorrow?" OpenSTEF answers that
question through **quantile forecasts** — a set of values that together
describe the uncertainty around every prediction.

This page explains what quantiles are, how OpenSTEF computes them, how to
interpret the resulting confidence bands, and why they matter for real-world
grid operations.

.. note::

   This page focuses on probabilistic output. For an introduction to how
   OpenSTEF produces point forecasts in the first place, see
   :doc:`forecasting_basics`. For information on what happens when the
   forecasting pipeline encounters errors, see :doc:`reliability_and_fallback`.


What Is a Quantile?
-------------------

A quantile is a threshold value associated with a probability. The **P10
quantile** (the 10th percentile) is the value below which 10 % of outcomes are
expected to fall. The **P90 quantile** is the value below which 90 % of
outcomes are expected to fall. Together, P10 and P90 define an **80 %
prediction interval** — a band that should contain the true outcome roughly
four times out of five.

OpenSTEF uses the following standard quantile set by default:

- ``quantile_P10`` — lower bound of the 80 % prediction interval
- ``quantile_P50`` — the median forecast (best single-value estimate)
- ``quantile_P90`` — upper bound of the 80 % prediction interval

The P50 value is the natural replacement for a traditional point forecast. The
P10 and P90 values bracket it with an honest statement about uncertainty.

.. note:: [DIAGRAM: A time-series chart showing a central P50 line with a
   shaded band between P10 and P90. The true measured load passes through the
   band most of the time, occasionally touching the edges.]


How OpenSTEF Computes Quantiles
--------------------------------

OpenSTEF learns uncertainty from historical forecast errors rather than
assuming a fixed noise level. The ``ConfidenceIntervalApplicator`` transform
(in ``openstef_models``) implements a two-phase approach:

**Fitting phase**
   During training, the applicator receives the validation split alongside the
   model's predictions on that split. It computes the forecast error for every
   timestamp and then groups those errors by **hour of day** (0–23). For each
   hour it calculates the standard deviation of the errors. If the dataset
   covers multiple forecast horizons, a separate standard deviation is stored
   per horizon as well.

**Prediction phase**
   At inference time, the applicator looks up the standard deviation that
   corresponds to the prediction hour (and horizon, if applicable). It then
   converts that standard deviation into quantile offsets by assuming that
   forecast errors follow a **normal distribution**:

   .. code-block:: text

      quantile_value = median + z_score × std

   For example:

   - P10 = median − 1.28 × std
   - P50 = median  (z = 0)
   - P90 = median + 1.28 × std

For multi-horizon forecasts the uncertainty grows with lead time. OpenSTEF
models this growth with an **exponential saturation curve**:

.. code-block:: text

   σ(t) = a × (1 − exp(−t / τ)) + b

where *t* is hours ahead and *τ* = far_horizon / 4. This reflects the
empirical observation that uncertainty rises quickly in the first few hours
and then levels off — a pattern common in energy load forecasting.

.. note::

   The normal-distribution assumption works well for aggregated energy loads
   but may be less accurate for highly intermittent generation (e.g., small
   solar installations). Always validate calibration on your own data.


Reading a Probabilistic Forecast
----------------------------------

After running a forecast workflow the output is a ``ForecastDataset`` whose
``data`` DataFrame contains one column per quantile, plus the target column:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import ForecastDataset
   from openstef_core.types import Quantile

   # Suppose `workflow.predict(forecast_dataset)` returned this:
   forecast: ForecastDataset = workflow.predict(forecast_dataset)

   # Inspect which quantiles are present
   print(forecast.quantiles)
   # [0.1, 0.5, 0.9]

   # Access the median series directly
   median = forecast.median_series
   print(median.head())

   # Access the full quantile DataFrame
   quantile_df = forecast.quantiles_data
   print(quantile_df.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

   # Compute the half-width of the prediction interval at each timestamp
   interval_width = quantile_df["quantile_P90"] - quantile_df["quantile_P10"]
   print(f"Mean interval width: {interval_width.mean():.1f} MW")

The ``ForecastDataset.median_series`` property is a convenience accessor for
``quantile_P50``. The ``quantiles_data`` property returns only the quantile
columns, making it easy to pass them directly to plotting utilities.


Visualising Forecast Uncertainty
----------------------------------

OpenSTEF ships with built-in plotting tools so you do not need to build
visualisations from scratch. The ``ForecastTimeSeriesPlotter`` (in
``openstef_beam``) renders an interactive Plotly figure with the measured load,
the median forecast, and the shaded prediction interval:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="MyModel",
           forecast=forecast.median_series,       # P50 line
           quantiles=forecast.quantiles_data,     # shaded P10–P90 band
       )
       .plot()
   )

   fig.update_layout(
       title="Load Forecast with 80 % Prediction Interval",
       yaxis_title="Load (MW)",
   )
   fig.show()

The resulting figure shows:

- A solid line for the actual measurements
- A solid line for the P50 (median) forecast
- A shaded area between P10 and P90

This makes it immediately obvious whether the model is over- or under-confident
for a given period.


Calibration: Are the Intervals Honest?
----------------------------------------

A prediction interval is only useful if it is **calibrated** — meaning that an
80 % interval actually contains the true value 80 % of the time. OpenSTEF
provides the ``QuantileProbabilityPlotter`` to check this:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter

   fig = QuantileProbabilityPlotter().plot(
       observed_probs=[0.08, 0.48, 0.87],    # fraction of actuals below each quantile
       forecasted_probs=[0.10, 0.50, 0.90],  # the quantile levels themselves
       model_name="MyModel",
   )
   fig.show()

The plot draws a diagonal **perfect-calibration line**. Points above the
diagonal mean the model is *over-confident* (intervals are too narrow — the
true value escapes the band more often than expected). Points below the
diagonal mean the model is *under-confident* (intervals are unnecessarily wide).

.. note:: [DIAGRAM: A calibration scatter plot with forecasted probability on
   the x-axis and observed frequency on the y-axis. A dashed diagonal line
   represents perfect calibration. Two example curves show an over-confident
   model (above the diagonal) and an under-confident model (below it).]

Well-calibrated quantiles are a prerequisite for using prediction intervals in
operational decisions. If calibration is poor, re-examine the size and
representativeness of the validation set used to fit the
``ConfidenceIntervalApplicator``.


Why Quantiles Matter for Grid Operations
-----------------------------------------

A single point forecast forces operators to choose an implicit safety margin.
Quantile forecasts make that margin **explicit and data-driven**:

- **Congestion management** — Use P90 as a conservative upper-bound estimate
  when assessing whether a cable or transformer will be overloaded. Acting on
  the median alone would underestimate risk half the time.

- **Reserve scheduling** — The width of the P10–P90 band directly indicates
  how much balancing reserve is needed. A narrow band on a calm weekday means
  less reserve is required; a wide band during a storm means more.

- **Imbalance cost reduction** — Energy traders can optimise bids by
  integrating over the full predictive distribution rather than committing to
  a single number.

- **Anomaly detection** — When a measured value falls outside the P10–P90
  band, it is a statistically meaningful signal that something unusual has
  happened — a sensor fault, an unexpected large consumer, or a grid event.

The key insight is that **uncertainty is not a failure of the model** — it is
genuine information about the physical system. Quantile forecasts surface that
information in a form that decision-makers can act on.


Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are sometimes confused:

- A **confidence interval** describes uncertainty about a *model parameter*
  (e.g., the true mean load for a given hour). It narrows as you collect more
  data.

- A **prediction interval** describes uncertainty about a *future individual
  observation*. It does not shrink to zero even with infinite data, because
  the physical process itself is variable.

OpenSTEF produces **prediction intervals**. The P10–P90 band will always have
non-zero width because load is genuinely uncertain — no model can eliminate
that. What a better model can do is produce a *narrower* band that is still
correctly calibrated, giving operators more precise guidance.


Configuring Quantile Output
----------------------------

The set of quantiles to generate is specified when constructing the
``ConfidenceIntervalApplicator``:

.. code-block:: python

   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )
   from openstef_core.types import Quantile

   # Request a tighter 60 % interval (P20–P80) in addition to the median
   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.2), Quantile(0.5), Quantile(0.8)],
   )

   # Fit on validation data
   applicator.fit((validation_dataset, validation_predictions))

   # Apply to new forecasts
   result = applicator.transform((new_input_dataset, new_predictions))
   print(result.data.columns.tolist())
   # ['quantile_P20', 'quantile_P50', 'quantile_P80']

.. note::

   The ``ConfidenceIntervalApplicator`` requires that the validation dataset
   spans **multiple days** to produce reliable hour-of-day statistics. A
   validation set covering only a few hours will yield unstable standard
   deviations and poorly calibrated intervals.

You can also disable quantile generation entirely by passing
``quantiles=None``, in which case the transform returns predictions unchanged.
This is useful during development when you only need the point forecast.


Summary
-------

- Quantile forecasts describe the *distribution* of future load, not just a
  single value.
- OpenSTEF learns hour-specific uncertainty from validation errors and applies
  it via the ``ConfidenceIntervalApplicator``.
- Uncertainty grows with forecast horizon following an exponential saturation
  curve.
- Use ``ForecastTimeSeriesPlotter`` to visualise prediction intervals and
  ``QuantileProbabilityPlotter`` to verify calibration.
- Prediction intervals are distinct from confidence intervals — they represent
  irreducible physical variability, not model parameter uncertainty.
- Operationally, quantiles enable risk-aware decisions for congestion
  management, reserve scheduling, and anomaly detection.