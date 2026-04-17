Quantiles and Confidence Intervals
===================================

Energy forecasting is inherently uncertain. Weather changes unexpectedly, demand
patterns shift, and grid conditions evolve in ways no model can perfectly anticipate.
Rather than pretending otherwise with a single "best guess" value, OpenSTEF produces
*probabilistic forecasts* — a family of predictions that quantify how uncertain the
model is at every point in time. This page explains what those predictions mean,
how they are generated, and why they matter for real grid operations.

For background on what short-term forecasting is and why it is needed, see
:doc:`forecasting_basics`. For information on how model reliability is maintained in
production, see :doc:`reliability_and_fallback`.

.. contents:: On this page
   :local:
   :depth: 2


What Is a Quantile Forecast?
-----------------------------

A **quantile** is a threshold value below which a given fraction of outcomes are
expected to fall. The 10th percentile (P10) means the model expects the true load to
be *above* this value 90 % of the time. The 90th percentile (P90) means the true load
should fall *below* this value 90 % of the time. The 50th percentile (P50) is the
median — the model's best single-point estimate.

When OpenSTEF returns a probabilistic forecast it returns *all of these at once*, one
column per quantile. A typical set of quantiles looks like this:

.. code-block:: python

   from openstef_core.types import Q

   # A standard set of quantiles covering the full spread of uncertainty
   QUANTILES = [Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)]

The ``Q`` type (an alias for ``Quantile``) is OpenSTEF's first-class representation
of a quantile level. Using it rather than a bare float ensures that quantile values
are validated and handled consistently throughout the library.

Together, these seven values describe the *shape* of the forecast distribution at
every future timestamp: where the centre of mass sits (P50), how wide the spread is
(P05–P95), and how skewed it might be (asymmetry between the lower and upper halves).

[VISUALIZATION: A time-series chart showing a 48-hour load forecast with the P50 median line and shaded bands for P10–P90 and P05–P95 intervals, illustrating how uncertainty widens with forecast horizon]


Confidence Intervals vs. Prediction Intervals
----------------------------------------------

These two terms are often used interchangeably in practice, but they mean different
things:

- A **confidence interval** describes uncertainty about a *model parameter* — for
  example, how precisely the model has estimated the average load for a given hour.
  It shrinks as more training data is collected.

- A **prediction interval** describes uncertainty about a *future observation* — the
  range within which the actual measured load is expected to fall. It cannot shrink
  to zero no matter how much data you have, because the real world is irreducibly
  noisy.

OpenSTEF produces **prediction intervals**. The P10–P90 band around a forecast is
not a statement about model parameter uncertainty; it is a statement about the
expected spread of actual future measurements. This distinction matters operationally:
a narrow band does not mean the model is "confident" in a statistical-estimation
sense — it means the model has learned that this particular hour of the day tends to
be predictable.


How OpenSTEF Generates Quantile Predictions
--------------------------------------------

OpenSTEF uses two complementary mechanisms to attach quantile bands to a point
forecast.

**Hour-specific uncertainty learning**

The ``ConfidenceIntervalApplicator`` learns the typical forecast error for each hour
of the day (0–23) from validation data. After fitting, it stores a per-hour standard
deviation and uses it to derive quantile values by assuming a normal distribution:

.. code-block:: text

   P10 = median − 1.28 × σ(hour)
   P90 = median + 1.28 × σ(hour)

For multi-horizon forecasts the uncertainty grows with lead time. The applicator
models this growth with an exponential saturation curve:

.. code-block:: text

   σ(t) = a × (1 − exp(−t / τ)) + b

where *t* is hours ahead and *τ* = far_horizon / 4. This reflects the well-known
pattern that forecast errors grow quickly in the first few hours and then level off
as the model's skill approaches that of climatology.

**Isotonic quantile calibration**

Even a well-trained model can produce *miscalibrated* quantiles — for example, the
P90 band might contain the true value only 80 % of the time rather than 90 %. The
``IsotonicQuantileCalibrator`` corrects this by learning a monotonic mapping from
raw predicted quantile values to calibrated values on held-out validation data.

The following example shows how to build a forecasting pipeline that includes
calibration as a postprocessing step:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.mixins import TransformPipeline
   from openstef_core.types import Q, LeadTime
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.transforms.postprocessing import IsotonicQuantileCalibrator
   from openstef_models.workflows import CustomForecastingWorkflow

   QUANTILES = [Q(0.1), Q(0.5), Q(0.9)]

   model = ForecastingModel(
       forecaster=GBLinearForecaster(
           horizons=[LeadTime.from_string("PT1H")],
           quantiles=QUANTILES,
           hyperparams=GBLinearHyperParams(n_steps=100),
       ),
       postprocessing=TransformPipeline(
           transforms=[
               IsotonicQuantileCalibrator(
                   quantiles=QUANTILES,
                   use_local_quantile_estimation=True,
               ),
           ]
       ),
       target_column="load",
   )

   workflow = CustomForecastingWorkflow(model_id="my_forecaster", model=model)
   workflow.fit(dataset)          # dataset is a TimeSeriesDataset
   forecast = workflow.predict(dataset)

   # forecast is a ForecastDataset; inspect the quantile columns
   print(forecast.quantiles)
   print(forecast.data.tail())

.. note::

   ``use_local_quantile_estimation=True`` enables a windowed approach that adapts
   calibration to local data density. The window size is chosen adaptively as
   ``max(MIN_WINDOW_SIZE, n_samples // 10)``, which works well for typical
   operational datasets of several months.


Reading a Probabilistic Forecast
----------------------------------

Once you have a ``ForecastDataset`` in hand, the key attributes are:

- ``forecast.quantiles`` — the list of ``Quantile`` levels present in the forecast.
- ``forecast.median_series`` — a ``pd.Series`` of P50 values, the best single-point
  estimate.
- ``forecast.quantiles_data`` — a ``pd.DataFrame`` with one column per quantile,
  indexed by timestamp.

To visualise the result, OpenSTEF provides ``ForecastTimeSeriesPlotter``:

.. code-block:: python

   from openstef_beam.analysis.plots import ForecastTimeSeriesPlotter

   fig = (
       ForecastTimeSeriesPlotter()
       .add_measurements(measurements=dataset.data["load"])
       .add_model(
           model_name="GBLinear",
           forecast=forecast.median_series,
           quantiles=forecast.quantiles_data,
       )
       .plot()
   )
   fig.show()

The plotter renders the median as a line and the quantile bands as shaded areas,
making it straightforward to see both the central prediction and the uncertainty
envelope at a glance.

[VISUALIZATION: Screenshot of ForecastTimeSeriesPlotter output showing actual measurements overlaid with the P50 line and P10–P90 shaded band]


Why Quantiles Matter for Grid Operations
-----------------------------------------

A single-point forecast forces operators to make an implicit assumption about
uncertainty — usually a conservative one. Quantile forecasts make that assumption
explicit and allow it to be tuned to the actual cost structure of the decision at
hand.

**Congestion management**

Grid operators need to know not just the expected load but the *worst credible case*.
Using P90 or P95 as the planning value means the grid is sized to handle 90–95 % of
scenarios without intervention, while avoiding the cost of over-building for the
extreme tail.

**Reserve procurement**

Balancing reserves are procured to cover forecast errors. The width of the P10–P90
band is a direct measure of how much reserve is needed. A narrow band on a calm
weekday night means less reserve is required; a wide band during a storm means more.
Quantile forecasts allow reserve volumes to be *dynamic* rather than fixed at a
conservative worst-case level.

**Renewable integration**

Solar and wind generation are highly variable. Quantile forecasts of net load (demand
minus renewables) let operators see not only the expected residual load but also the
range of outcomes they must be prepared to balance. This is especially important at
high renewable penetration where the distribution of net load can be strongly
asymmetric.

**Threshold-based alerts**

Automated monitoring systems can trigger alerts when the P90 forecast exceeds a
capacity limit, even if the P50 is still within bounds. This gives operators advance
warning of *possible* congestion rather than reacting only when it is already
occurring.

.. note::

   Choosing which quantile to act on is a business decision, not a modelling one.
   OpenSTEF provides the full distribution; the operator or downstream system decides
   which percentile is appropriate for each use case.


Quantile Ordering and the ``QuantileSorter``
---------------------------------------------

A mathematical property that any valid set of quantile forecasts must satisfy is
*monotonic ordering*: P10 ≤ P30 ≤ P50 ≤ P70 ≤ P90 at every timestamp. Individual
quantile regression models can occasionally violate this — a phenomenon called
*quantile crossing* — especially at the tails or for unusual input conditions.

OpenSTEF addresses this with ``QuantileSorter``, a postprocessing transform that
enforces the ordering constraint by sorting quantile values at each timestamp. It can
be composed in the same ``TransformPipeline`` as the calibrator:

.. code-block:: python

   from openstef_models.transforms.postprocessing import (
       IsotonicQuantileCalibrator,
   )
   from openstef_models.transforms.postprocessing.quantile_sorter import (
       QuantileSorter,
   )

   postprocessing = TransformPipeline(
       transforms=[
           IsotonicQuantileCalibrator(quantiles=QUANTILES),
           QuantileSorter(),   # always apply after calibration
       ]
   )

Applying ``QuantileSorter`` after calibration ensures that the final forecast
delivered to downstream systems is always internally consistent.


Summary
--------

Probabilistic forecasts in OpenSTEF are built around the concept of quantiles: each
forecast timestamp carries a full set of percentile values rather than a single
number. The P50 is the median prediction; the surrounding bands describe how wide the
uncertainty is and how it grows with lead time. OpenSTEF learns this uncertainty
from validation data (``ConfidenceIntervalApplicator``), corrects for miscalibration
(``IsotonicQuantileCalibrator``), and enforces internal consistency
(``QuantileSorter``). Operationally, these bands enable smarter decisions about
reserves, congestion management, and renewable integration — turning forecast
uncertainty from a nuisance into actionable information.

For details on the features that drive forecast accuracy (and therefore the width of
these bands), see :doc:`feature_engineering`. For ensemble approaches that combine
multiple models into a single probabilistic output, see :doc:`meta_ensembles`.