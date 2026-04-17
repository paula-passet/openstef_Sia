Quantiles and Confidence Intervals
===================================

When OpenSTEF produces a forecast, it does not return a single number. It returns
a *distribution* of possible outcomes expressed as a set of quantiles. This page
explains what that means, how to read and use those values, and why probabilistic
forecasts are more useful than point forecasts for energy operations.

If you are new to the idea of short-term energy forecasting in general, start with
:doc:`forecasting_basics` first. For details on how model reliability and fallback
behaviour interact with forecast quality, see :doc:`reliability_and_fallback`.

.. note::

   Throughout this page, quantile levels are written as decimals (``0.1``, ``0.5``,
   ``0.9``) and as their equivalent percentile shorthand (``P10``, ``P50``, ``P90``).
   OpenSTEF uses both conventions in its API and column names.


What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What load value will not be exceeded
with probability p?"* More precisely, the q-th quantile of a forecast distribution
is the value x such that the true outcome falls below x with probability q.

A few concrete examples for energy load forecasting:

- **P10 (0.1)** — there is a 10 % chance the actual load will be below this value.
  In other words, 90 % of the time the load will be at or above it. This is the
  *low* end of the uncertainty band.
- **P50 (0.5)** — the median prediction. Half of all outcomes are expected to fall
  below this value, half above. This is the closest equivalent to a traditional
  point forecast.
- **P90 (0.9)** — there is a 90 % chance the actual load will be below this value.
  Only 10 % of the time will load exceed it. This is the *high* end of the
  uncertainty band.

Together, a set of quantiles traces out the shape of the forecast distribution
without assuming any particular parametric form. OpenSTEF typically produces seven
quantiles by default:

.. code-block:: python

   from openstef_core.types import Quantile as Q

   PREDICTION_QUANTILES = [
       Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)
   ]

These seven levels give you both the central estimate (P50) and progressively
wider uncertainty bands (P10/P90 and P05/P95) that capture rare but plausible
deviations.

**[DIAGRAM: Fan chart showing how seven quantile levels fan out from a single forecast origin, with P50 as the central line and symmetric shaded bands for P30/P70, P10/P90, and P05/P95]**


How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF uses two complementary mechanisms to attach uncertainty estimates to a
forecast.

**Native quantile regression** — gradient-boosted models such as GBLinear can be
trained directly to minimise the *pinball loss* for each quantile level. The model
learns a separate mapping from features to each quantile, so the uncertainty
structure is baked into the model itself rather than added as a post-processing
step.

**Learned confidence intervals** — the ``ConfidenceIntervalApplicator`` transform
takes a median forecast and enriches it with quantile columns by learning
hour-specific uncertainty from historical validation errors. During fitting it
computes the standard deviation of forecast errors for each hour of the day (0–23).
At prediction time it looks up the appropriate standard deviation, applies an
exponential-decay interpolation across forecast horizons, and converts the result
to quantile values assuming normally distributed errors:

.. code-block:: text

   quantile_value = median + z_score * std
   e.g.  P10 = median − 1.28 × std
         P90 = median + 1.28 × std

The exponential decay model for multi-horizon uncertainty is:

.. code-block:: text

   σ(t) = a × (1 − exp(−t / τ)) + b

where *t* is hours ahead and *τ = far_horizon / 4*. This captures the intuitive
behaviour that uncertainty grows quickly in the first few hours and then levels off
as the forecast horizon extends.

A minimal example of using ``ConfidenceIntervalApplicator`` directly:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # Fit on a (validation_input, validation_predictions) tuple
   applicator.fit((validation_data, validation_predictions))

   # Enrich new predictions with quantile columns
   result = applicator.transform((new_input_data, new_predictions))

   # result.data now contains columns: quantile_P10, quantile_P50, quantile_P90
   print(result.data.columns.tolist())

.. note::

   ``ConfidenceIntervalApplicator`` assumes forecast errors are approximately
   normally distributed. This holds well for aggregated energy load but may be
   less accurate for highly intermittent generation sources such as small-scale
   solar PV.


Reading Quantile Output from a Forecast
-----------------------------------------

When you call ``workflow.predict()``, the returned ``ForecastDataset`` contains
one column per quantile, named with the ``quantile_P<nn>`` convention:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   forecast: ForecastDataset = workflow.predict(forecast_dataset)

   # Inspect which quantiles are present
   print(forecast.quantiles)
   # [0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95]

   # Access the median series directly
   median = forecast.median_series

   # Access all quantile columns as a DataFrame
   bands = forecast.quantiles_data
   print(bands.columns.tolist())
   # ['quantile_P05', 'quantile_P10', 'quantile_P30',
   #  'quantile_P50', 'quantile_P70', 'quantile_P90', 'quantile_P95']

The ``quantiles_data`` property returns a ``DataFrame`` indexed by timestamp, with
each column representing one quantile level. You can slice any pair of columns to
form an interval:

.. code-block:: python

   # 80 % prediction interval (P10 to P90)
   lower = bands["quantile_P10"]
   upper = bands["quantile_P90"]
   interval_width = upper - lower

**[VISUALIZATION: Time-series plot showing actual load measurements as a solid line, P50 forecast as a dashed line, and shaded bands for the P10–P90 and P05–P95 intervals over a 48-hour forecast window]**

To visualise the full fan chart interactively, use the built-in
``ForecastTimeSeriesPlotter``:

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
   fig.show()

**[VISUALIZATION: Interactive Plotly fan chart produced by ForecastTimeSeriesPlotter, showing shaded confidence bands around the median forecast line]**


Confidence Intervals vs. Prediction Intervals
-----------------------------------------------

These two terms are often used interchangeably in practice, but they describe
different things:

**Prediction interval** — a range that is expected to contain the *next individual
observation* with a stated probability. A 90 % prediction interval formed from
P05 to P95 should contain the actual measured load 90 % of the time. This is what
OpenSTEF's quantile columns represent.

**Confidence interval** — a range that describes uncertainty about a *model
parameter* (for example, the true mean load at a given hour). Confidence intervals
narrow as you collect more data; prediction intervals do not, because individual
observations always carry irreducible noise.

For operational energy forecasting, prediction intervals are almost always what
you want. When a grid operator asks "how much capacity should I reserve to cover
demand with 95 % certainty?", the answer comes from the P95 quantile of the
forecast, not from a confidence interval around the mean.

.. note::

   OpenSTEF's documentation and API use the term *confidence interval* loosely to
   mean the shaded band between two quantile levels. Technically these are
   prediction intervals. The distinction matters when communicating with
   statisticians but is not operationally significant for most use cases.


Why Quantiles Matter for Operations
-------------------------------------

A single point forecast (the median) is sufficient for reporting average expected
demand, but it is inadequate for most operational decisions, which are inherently
asymmetric:

**Grid congestion management** — a transmission system operator needs to know the
*worst plausible* load, not the average. Scheduling based on P50 will lead to
congestion roughly half the time. Scheduling based on P90 or P95 provides a
quantifiable safety margin.

**Reserve procurement** — balancing responsible parties purchase upward and
downward reserves. The width of the P10–P90 interval directly informs how much
reserve is needed: a narrow band means the system is predictable and little reserve
is required; a wide band signals high uncertainty and the need for more buffer.

**Renewable integration** — solar and wind generation are highly variable. The
asymmetric shape of their forecast distributions (generation cannot go below zero)
means that the P10 and P90 quantiles carry very different operational implications.
Quantile forecasts make this asymmetry explicit.

**Risk-aware dispatch** — energy traders and asset managers can use quantile
forecasts to construct cost-optimal strategies that explicitly trade off the
probability of under- or over-supply against the cost of imbalance.

In all these cases, the operational value of the forecast comes not from the median
alone but from the *spread* of the distribution. A forecast that is accurate on
average but poorly calibrated in its uncertainty bands can be worse than useless
for risk management.


Calibration: Are the Quantiles Trustworthy?
---------------------------------------------

A quantile forecast is *calibrated* if the stated coverage probabilities match
observed frequencies. Concretely, the P90 quantile should be exceeded by actual
measurements roughly 10 % of the time. If it is exceeded 30 % of the time, the
model is *under-confident* (bands are too narrow). If it is exceeded only 2 % of
the time, the model is *over-confident* (bands are too wide).

OpenSTEF provides ``QuantileCalibrationBoxPlotter`` to visualise calibration error
distributions across multiple targets and quantile levels:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_beam.analysis.plots.quantile_calibration_box_plotter import (
       QuantileCalibrationBoxPlotter,
   )

   plotter = QuantileCalibrationBoxPlotter()
   # calibration_results is a DataFrame with columns per quantile
   # and rows per target, containing (observed_frequency - quantile_level)
   fig = plotter.plot(calibration_results)
   fig.show()

Well-calibrated forecasts produce boxplots centred near zero for every quantile
level. Systematic positive bias at P90 means the model is too conservative at the
high end; systematic negative bias means it is too aggressive.

**[VISUALIZATION: QuantileCalibrationBoxPlotter output showing boxplots for each quantile level (P05 through P95) across multiple grid connection targets, with a horizontal reference line at zero calibration error]**

Calibration should be monitored continuously in production. Seasonal shifts in
load patterns, changes in the connected asset mix, or model drift can all degrade
calibration over time even when median accuracy remains acceptable.


Configuring Quantiles in a Workflow
-------------------------------------

You specify which quantile levels to produce when constructing the workflow
configuration. Any subset of ``[0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 0.95]`` is valid,
but the set must always include ``0.5`` (the median):

.. code-block:: python

   from openstef_core.types import Quantile as Q, LeadTime
   from openstef_models.workflows.config import ForecastingWorkflowConfig

   config = ForecastingWorkflowConfig(
       model_id="my_substation",
       model="gblinear",
       horizons=[LeadTime.from_string("P2D")],
       # Narrow set: just the 80 % prediction interval plus the median
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

Requesting fewer quantiles reduces computation time and output size, which can
matter when forecasting hundreds of grid connections simultaneously. Requesting
more quantiles gives a finer picture of the distribution tail, which is valuable
when the cost of tail events is high.

----

For a broader introduction to how forecasts are produced and consumed, see
:doc:`forecasting_basics`. To understand how OpenSTEF handles situations where
the primary model fails to produce a forecast, see :doc:`reliability_and_fallback`.
For details on the ensemble approach that combines multiple models before quantiles
are applied, see :doc:`meta_ensembles`.