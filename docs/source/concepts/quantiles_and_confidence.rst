Quantiles and Confidence Intervals
===================================

OpenSTEF produces *probabilistic* forecasts: rather than a single predicted
value, the library outputs a set of quantile predictions that together describe
the full range of likely outcomes. This page explains what those quantiles mean,
how OpenSTEF generates them, and how to use them effectively in grid operations.

For background on why short-term forecasting matters in the first place, see
:doc:`forecasting_basics`. For information on how input features influence
forecast uncertainty, see :doc:`feature_engineering`.

.. note:: [DIAGRAM: A time-series chart showing a central P50 forecast line with
   progressively wider shaded bands for P30–P70 and P10–P90 intervals, plus
   actual measured load overlaid.]


What Is a Quantile Forecast?
-----------------------------

A quantile forecast answers the question: *"What load level will not be
exceeded with probability p?"* The P10 quantile, for example, is the value
below which the actual load is expected to fall 10 % of the time. The P90
quantile is the value below which actual load is expected to fall 90 % of the
time.

OpenSTEF represents quantiles as values between 0 and 1 using the
``openstef_core.types.Quantile`` type. A typical forecast configuration
includes seven quantiles that span the distribution:

.. code-block:: python

   from openstef_core.types import Quantile as Q

   PREDICTION_QUANTILES = [
       Q(0.05),  # 5th percentile  — very low load scenario
       Q(0.10),  # 10th percentile
       Q(0.30),  # 30th percentile
       Q(0.50),  # median forecast  — best single-point estimate
       Q(0.70),  # 70th percentile
       Q(0.90),  # 90th percentile
       Q(0.95),  # 95th percentile — very high load scenario
   ]

The P50 (median) is the natural replacement for a traditional point forecast.
The symmetric pairs around it — P10/P90, P05/P95 — form *prediction intervals*
of 80 % and 90 % coverage respectively.

In the ``ForecastDataset`` that OpenSTEF returns, each quantile is stored as a
named column following the convention ``quantile_P10``, ``quantile_P50``,
``quantile_P90``, and so on:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import ForecastDataset

   # Illustrative: construct a ForecastDataset from model output
   data = pd.DataFrame(
       {
           "quantile_P10": [95.0, 98.0],
           "quantile_P50": [110.0, 113.0],
           "quantile_P90": [125.0, 129.0],
       },
       index=pd.date_range("2025-06-01 08:00", periods=2, freq="h"),
   )

   forecast = ForecastDataset(data, sample_interval=timedelta(hours=1))

   print(forecast.quantiles)          # [0.1, 0.5, 0.9]
   print(forecast.median_series)      # pd.Series of P50 values
   print(forecast.quantiles_data)     # DataFrame of all quantile columns


How OpenSTEF Generates Quantiles
----------------------------------

OpenSTEF offers two complementary mechanisms for producing quantile predictions.

**Native quantile regression**

Gradient-boosted models such as GBLinear can be trained directly with a
quantile loss function. Each quantile is predicted as a separate output of the
model, so the uncertainty is learned end-to-end from the training data. This
approach captures non-linear, feature-dependent uncertainty — for instance, the
model can learn that forecasts are wider on windy days when renewable generation
is harder to predict.

**Post-hoc confidence interval applicator**

The ``ConfidenceIntervalApplicator`` transform in
``openstef_models.transforms.postprocessing`` takes an existing point-forecast
model and wraps it with learned uncertainty bands. During fitting it computes
validation errors for each hour of the day (0–23) and stores the standard
deviation per hour. At prediction time it looks up the appropriate standard
deviation and converts it to quantiles assuming a normal distribution:

.. code-block:: text

   quantile_value = median + z_score × σ_hour

   e.g.  P10 = median − 1.28 × σ
         P90 = median + 1.28 × σ

For multi-horizon forecasts the uncertainty grows with lead time following an
exponential saturation curve:

.. code-block:: text

   σ(t) = a × (1 − exp(−t / τ)) + b,   where τ = far_horizon / 4

This reflects the physical reality that uncertainty accumulates quickly in the
first few hours and then levels off as the forecast approaches climatological
variability.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)]
   )

   # fit expects (validation_input_dataset, validation_predictions)
   applicator.fit((validation_data, validation_predictions))

   # transform adds quantile_P10, quantile_P50, quantile_P90 columns
   probabilistic_forecast = applicator.transform((new_input_data, new_predictions))
   print(probabilistic_forecast.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

.. note::

   The ``ConfidenceIntervalApplicator`` assumes normally distributed forecast
   errors. This is a reasonable approximation for energy load forecasting but
   may not suit all use cases. Validation data must span multiple days to
   produce reliable hourly statistics.


Confidence Intervals vs. Prediction Intervals
-----------------------------------------------

These terms are often used interchangeably in practice, but they have distinct
meanings worth understanding.

A **prediction interval** covers where a *single future observation* will fall
with a given probability. A **confidence interval** covers where a *population
parameter* (such as the mean) will fall. In energy forecasting, what operators
care about is where the actual measured load will land — so the correct term is
*prediction interval*, and that is what OpenSTEF's quantile pairs represent.

When OpenSTEF reports a P10–P90 band, it is asserting: *"We expect the actual
load to fall inside this band 80 % of the time."* Whether that assertion is
accurate depends on calibration — see `Checking Calibration`_ below.


Why Quantiles Matter for Grid Operations
-----------------------------------------

A single point forecast forces operators to make implicit assumptions about
uncertainty. Quantile forecasts make that uncertainty explicit and actionable:

- **Congestion management** — Use P90 as a conservative upper bound when
  deciding whether to pre-emptively curtail generation or activate flexibility.
  A P90 exceedance means only a 10 % chance of underestimating peak load.

- **Reserve sizing** — The width of the P10–P90 interval is a direct measure
  of forecast uncertainty. Wider bands on a given hour signal that more
  operating reserve should be held.

- **Imbalance cost reduction** — Trading desks can optimise bids by choosing
  the quantile that minimises expected cost given the asymmetric penalties of
  over- and under-delivery.

- **Maintenance scheduling** — Low-uncertainty windows (narrow bands) are
  preferable for planned outages because the risk of unexpected demand spikes
  is smaller.

.. note:: [DIAGRAM: Two side-by-side panels. Left: a narrow prediction band on
   a stable weekday afternoon — suitable for maintenance scheduling. Right: a
   wide prediction band on a stormy winter morning — high reserve requirement.]


Visualising Probabilistic Forecasts
-------------------------------------

OpenSTEF ships with dedicated plotting utilities so you do not need to build
visualisations from scratch.

**Time-series view with shaded bands**

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=forecast_dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,      # P50 line
           quantiles=forecast.quantiles_data,    # shaded P10–P90 band
       )
       .plot()
   )
   fig.update_layout(title="Energy Load Forecast", yaxis_title="Load (MW)")
   fig.show()

The resulting interactive Plotly chart shows the actual measurements as a solid
line, the P50 forecast as a second line, and the prediction interval as a
shaded region.

**Calibration scatter plot**

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_beam.analysis.plots import QuantileProbabilityPlotter

   plotter = QuantileProbabilityPlotter()

   forecasted = [Quantile(0.1), Quantile(0.3), Quantile(0.5), Quantile(0.7), Quantile(0.9)]
   observed   = [Quantile(0.12), Quantile(0.29), Quantile(0.51), Quantile(0.68), Quantile(0.88)]

   plotter.add_model("GBLinear", forecasted, observed)
   fig = plotter.plot(title="Forecast Calibration Analysis")
   fig.show()

**Calibration box plot across multiple targets**

When evaluating a model fleet across many grid nodes, the
``QuantileCalibrationBoxPlotter`` shows the *distribution* of calibration
errors per quantile level:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_beam.analysis.plots import QuantileCalibrationBoxPlotter

   plotter = QuantileCalibrationBoxPlotter()
   plotter.add_model(
       model_name="GBLinear",
       forecasted_probs=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       observed_probs=[Quantile(0.11), Quantile(0.49), Quantile(0.92)],
   )
   fig = plotter.plot(title="Quantile Calibration Boxplot")
   fig.show()


.. _checking-calibration:

Checking Calibration
---------------------

A probabilistic forecast is *calibrated* when its stated coverage matches
observed coverage: if you claim P90, the actual load should fall below that
value roughly 90 % of the time. Systematic deviations indicate bias in the
uncertainty model.

.. note:: [DIAGRAM: A calibration scatter plot with a diagonal "perfect
   calibration" reference line. One model's points cluster above the diagonal
   (over-confident — intervals too narrow); another model's points cluster
   below (under-confident — intervals too wide).]

The ``QuantileProbabilityPlotter`` visualises this directly. Points close to
the diagonal indicate a well-calibrated model. Deviations have clear
operational interpretations:

- **Points above the diagonal** (observed frequency > forecasted probability)
  — the model is *over-confident*. Intervals are too narrow; actual load
  escapes the band more often than expected. Increase reserve margins.

- **Points below the diagonal** (observed frequency < forecasted probability)
  — the model is *under-confident*. Intervals are unnecessarily wide, leading
  to over-procurement of reserves.

When the ``ConfidenceIntervalApplicator`` is retrained regularly on fresh
validation data, calibration tends to remain stable because the hour-specific
standard deviations track seasonal changes in forecast difficulty.


Summary
--------

- OpenSTEF forecasts are probabilistic: each prediction is a set of quantile
  values, not a single number.
- The P50 column is the median forecast and the natural point-estimate
  replacement.
- Symmetric quantile pairs (P10/P90, P05/P95) form prediction intervals with
  80 % and 90 % nominal coverage.
- Quantiles are generated either natively by quantile-regression models or
  post-hoc by ``ConfidenceIntervalApplicator``.
- Calibration — whether stated coverage matches observed coverage — can be
  inspected with ``QuantileProbabilityPlotter`` and
  ``QuantileCalibrationBoxPlotter``.
- Operationally, quantiles enable risk-aware decisions for congestion
  management, reserve sizing, and maintenance scheduling.

For information on what happens when a model fails to produce a forecast at
all, see :doc:`reliability_and_fallback`.