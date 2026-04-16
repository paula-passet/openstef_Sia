Quantiles and Confidence Intervals
===================================

Energy forecasts are never perfectly certain. A grid operator who receives only a single
predicted load value has no way of knowing whether that number is a confident estimate
backed by stable historical patterns, or a rough guess made under highly uncertain
conditions. **Probabilistic forecasts** solve this problem by expressing uncertainty
explicitly, and quantiles are the primary language OpenSTEF uses to do so.

This page explains what quantiles are, how OpenSTEF produces them, how to read and
visualise them, and why they matter for day-to-day grid operations.

.. note::

   This page focuses on uncertainty quantification. For an introduction to the
   forecasting workflow itself, see :doc:`forecasting_basics`. For the input features
   that drive forecast accuracy (and therefore interval width), see
   :doc:`feature_engineering`.


What Is a Quantile?
-------------------

A quantile at level *p* is a threshold value such that the true outcome falls below
that threshold with probability *p*. In plain terms:

- **P10 (10th percentile)** — there is a 10 % chance the actual load will be *below*
  this value, and a 90 % chance it will be *above* it.
- **P50 (50th percentile, the median)** — the model considers values above and below
  equally likely. This is the central forecast.
- **P90 (90th percentile)** — there is a 90 % chance the actual load will be *below*
  this value, and only a 10 % chance it will exceed it.

Together, P10 and P90 form a **prediction interval** that is expected to contain the
true value 80 % of the time. Wider intervals mean more uncertainty; narrower intervals
mean the model is more confident.

.. note:: [DIAGRAM: A time-series chart showing a central P50 forecast line with a
   shaded band between P10 and P90, and a handful of actual measurements scattered
   inside and outside the band. Annotations point to the lower bound (P10), median
   (P50), and upper bound (P90).]

OpenSTEF works with a configurable set of quantiles. A typical configuration covers
the full spread of uncertainty:

.. code-block:: python

   from openstef_core.types import Quantile

   # A representative set of quantiles for probabilistic forecasting
   QUANTILES = [
       Quantile(0.05),   # P05 – extreme lower bound
       Quantile(0.10),   # P10 – lower bound
       Quantile(0.30),   # P30 – lower-central
       Quantile(0.50),   # P50 – median (central forecast)
       Quantile(0.70),   # P70 – upper-central
       Quantile(0.90),   # P90 – upper bound
       Quantile(0.95),   # P95 – extreme upper bound
   ]

The ``Quantile`` type is a validated scalar from ``openstef_core.types``. Passing a
value outside [0, 1] raises an error at construction time, preventing silent mistakes
in downstream pipelines.


How OpenSTEF Generates Quantiles
---------------------------------

OpenSTEF derives quantile forecasts from a **learned uncertainty model** rather than
running a separate model for every quantile level. The
``ConfidenceIntervalApplicator`` transform encapsulates this logic:

1. **Fit phase** — the transform is fitted on validation data (held-out observations
   paired with model predictions). For each hour of the day (0–23) it computes the
   standard deviation of the forecast errors. When multiple forecast horizons are
   present, a separate standard deviation is stored per horizon.

2. **Transform phase** — for a new prediction, the applicator looks up the
   hour-appropriate standard deviation and converts it to quantile offsets by assuming
   that forecast errors follow a normal distribution:

   .. code-block:: text

      quantile_value = median + z_score × σ_hour

   For example, P10 uses a z-score of −1.28 and P90 uses +1.28. The median (P50) is
   the raw model prediction unchanged.

3. **Multi-horizon interpolation** — uncertainty grows with forecast horizon. For
   longer-range forecasts the applicator interpolates standard deviations using an
   exponential-decay curve:

   .. code-block:: text

      σ(t) = a × (1 − exp(−t / τ)) + b

   where *t* is hours ahead and *τ* = far_horizon / 4. This reflects the empirical
   observation that uncertainty rises quickly in the first few hours and then levels
   off.

.. note::

   The normal-distribution assumption works well for energy load forecasting, where
   errors tend to be symmetric and unimodal. It may not be appropriate for highly
   skewed targets such as renewable generation during intermittent weather events.

The applicator is used as a postprocessing step inside a forecasting pipeline:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.transforms.postprocessing.confidence_interval_applicator import (
       ConfidenceIntervalApplicator,
   )

   applicator = ConfidenceIntervalApplicator(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
   )

   # Fit on (validation_data, validation_predictions) tuple
   applicator.fit((validation_data, validation_predictions))

   # Apply to new forecast data – returns a ForecastDataset with quantile columns
   result = applicator.transform((new_input_data, new_predictions))

   # The result DataFrame now contains quantile columns
   print(result.data.columns.tolist())
   # ['quantile_P10', 'quantile_P50', 'quantile_P90']

The output columns follow the naming convention ``quantile_P<percentile>``, so P50 is
stored as ``quantile_P50``, P90 as ``quantile_P90``, and so on.


Prediction Intervals vs. Confidence Intervals
----------------------------------------------

These two terms are often used interchangeably in practice, but they mean different
things statistically:

- A **prediction interval** covers a *single future observation*. If you ask "where
  will the actual load at 14:00 tomorrow fall?", a prediction interval answers that
  question. This is what OpenSTEF's quantile bands represent.

- A **confidence interval** covers an *estimated parameter* (such as the mean of a
  distribution). It expresses uncertainty about the model itself, not about a
  specific future value.

For grid operations, prediction intervals are almost always the right tool. You care
about whether the actual MW value on the cable will exceed a thermal limit, not about
the average behaviour of the model across many hypothetical datasets.

.. note::

   OpenSTEF's documentation and code sometimes use "confidence interval" as a
   colloquial shorthand for the quantile band. In all cases the underlying quantity is
   a **prediction interval** in the statistical sense described above.


Visualising Probabilistic Forecasts
-------------------------------------

OpenSTEF ships with built-in plotting utilities so you do not need to build
visualisations from scratch.

**Time-series view with shaded bands**

The ``ForecastTimeSeriesPlotter`` renders the median forecast as a line and the
quantile bands as layered shaded areas:

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

   fig.update_layout(
       title="Energy Load Forecast with Prediction Intervals",
       yaxis_title="Load (MW)",
   )
   fig.show()

.. note:: [DIAGRAM: Interactive time-series plot showing a blue P50 forecast line,
   a medium-shaded band for P30–P70, and a lighter outer band for P10–P90. Actual
   measurements are overlaid as a darker line. The x-axis is time; the y-axis is
   load in MW.]

**Calibration plot**

A calibration plot answers the question: *are the stated probabilities actually
correct?* A perfectly calibrated model will have its P90 band contain the true value
exactly 90 % of the time. The ``QuantileProbabilityPlotter`` produces a scatter plot
of forecasted probability vs. observed frequency, with a diagonal reference line for
perfect calibration:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileProbabilityPlotter
   import pandas as pd

   plotter = QuantileProbabilityPlotter()

   fig = plotter.plot(
       observed_probs=observed_probabilities,    # list[Quantile]
       forecasted_probs=forecasted_probabilities, # list[Quantile]
       model_name="GBLinear",
   )
   fig.show()

Points close to the diagonal indicate good calibration. Points above the diagonal
mean the model is **over-confident** (intervals are too narrow); points below mean it
is **under-confident** (intervals are unnecessarily wide).

**Calibration box plot across multiple targets**

When evaluating a model fleet across many grid connections, the
``QuantileCalibrationBoxPlotter`` shows the distribution of calibration errors per
quantile level:

.. code-block:: python

   from openstef_beam.analysis.plots import QuantileCalibrationBoxPlotter
   from openstef_core.types import Quantile
   import pandas as pd

   plotter = QuantileCalibrationBoxPlotter()

   calibration_data = pd.DataFrame({
       "target": ["substation_A", "substation_A", "substation_B", "substation_B"],
       "quantile": [Quantile(0.1), Quantile(0.9), Quantile(0.1), Quantile(0.9)],
       "calibration_error": [0.02, -0.03, 0.05, 0.01],
   })

   fig = plotter.plot(calibration_data)
   fig.show()

Boxplots centred around zero with tight distributions indicate consistent, unbiased
uncertainty estimates across the fleet.


Why Quantiles Matter for Grid Operations
-----------------------------------------

A point forecast tells an operator what to *expect*; a probabilistic forecast tells
them what to *prepare for*. The practical implications are significant:

**Congestion management**
   Thermal limits on cables and transformers are hard constraints. Knowing that the
   P95 load forecast stays below a cable's rating gives an operator confidence that
   no intervention is needed. A point forecast alone cannot provide this assurance.

**Reserve scheduling**
   Balancing responsible parties use upper quantiles (P80, P90) to size upward
   reserves and lower quantiles (P10, P20) to size downward reserves. Symmetric
   reserve sizing based only on the median leads to systematic under- or
   over-procurement.

**Risk-aware dispatch**
   Battery storage and flexible demand assets can be dispatched more efficiently when
   the operator knows the probability distribution of net load, not just its expected
   value.

**Anomaly detection**
   When an actual measurement falls outside the P05–P95 band, it is a strong signal
   that something unusual is happening — a sensor fault, an unexpected large consumer
   connecting, or a model that has drifted. See :doc:`reliability_and_fallback` for
   how OpenSTEF handles such situations.

**Interval width as a quality signal**
   Narrow intervals on a sunny weekday afternoon (stable, predictable conditions) and
   wide intervals during a storm (high uncertainty) are both correct behaviour. If
   intervals are uniformly wide regardless of conditions, the model has not learned
   the structure of uncertainty and should be retrained.


Checking Calibration in Practice
----------------------------------

Calibration should be monitored continuously in production, not just at training time.
A well-calibrated model satisfies:

.. code-block:: text

   For every quantile level p:
       fraction of actuals below quantile_p ≈ p

OpenSTEF provides the ``MeanAbsoluteCalibrationError`` metric to quantify this:

.. code-block:: python

   import numpy as np
   from openstef_core.types import Quantile

   # y_true: 1-D array of observed values
   # y_pred: 2-D array of shape (n_samples, n_quantiles)
   # quantiles: 1-D array of quantile levels, e.g. [0.1, 0.5, 0.9]

   quantiles = np.array([0.1, 0.5, 0.9])

   # For each quantile q, the observed probability should equal q
   # A MACE close to 0 indicates good calibration
   for i, q in enumerate(quantiles):
       observed_prob = np.mean(y_true < y_pred[:, i])
       calibration_error = abs(observed_prob - q)
       print(f"P{int(q*100):02d}: observed={observed_prob:.3f}, "
             f"target={q:.3f}, error={calibration_error:.3f}")

If calibration degrades over time — for example, because the load profile of a
substation has changed — the ``ConfidenceIntervalApplicator`` should be refitted on
more recent validation data.

.. note::

   Calibration and sharpness (interval width) are complementary goals. A model that
   always outputs very wide intervals can be perfectly calibrated but operationally
   useless. Aim for the *narrowest* intervals that are still calibrated.