Forecasting Basics
==================

Short-term energy forecasting is the practice of predicting electricity load, generation,
or related quantities over time horizons ranging from minutes to a few days ahead. This
page explains what short-term forecasting means in practice, why it matters for grid
operations, and how OpenSTEF models the key concepts of horizons, lead times, and
forecast frequency.

.. note::

   This page covers the *concepts* behind short-term forecasting. For guidance on
   choosing a model, see :doc:`model_selection`. For how OpenSTEF constructs the
   features that drive these forecasts, see :doc:`feature_engineering`.

What Is Short-Term Forecasting?
--------------------------------

A forecast is a prediction of a future value made at some point in the past. In energy
systems, the quantity being predicted is typically electrical load (demand) or renewable
generation at a specific substation, feeder, or portfolio level. *Short-term* forecasting
covers the window from a few minutes ahead up to roughly 48 hours ahead — the range that
directly informs operational decisions such as dispatch scheduling, congestion management,
and balancing.

Beyond 48 hours the problem changes character: weather uncertainty dominates, market
structures shift, and the relevant decision-makers (e.g., capacity planners) need
different information. OpenSTEF is designed specifically for the short-term window where
high temporal resolution and frequent updates are both feasible and valuable.

Why Short-Term Forecasts Matter
--------------------------------

Grid operators and energy traders need to act on forecasts continuously. A distribution
system operator balancing a local grid needs to know what load will look like in 15
minutes to avoid manual interventions. A day-ahead market participant needs a 24–48 hour
view to submit bids before the gate closure. These are fundamentally different use cases,
but both depend on the same underlying infrastructure: a system that ingests recent
measurements, runs a trained model, and produces a fresh forecast on a regular schedule.

Poor short-term forecasts translate directly into operational costs — either through
unnecessary reserve activation, missed congestion warnings, or suboptimal trading
positions. Accurate, well-calibrated forecasts reduce these costs. OpenSTEF's design
reflects this operational reality: it is built to run continuously, refresh forecasts
frequently, and produce probabilistic outputs so that operators can reason about
uncertainty, not just point estimates.

.. note:: [DIAGRAM: Timeline showing forecast horizons. A horizontal time axis runs left to right. The leftmost point is labelled "now (t₀)". Four coloured bands extend rightward: a narrow band to t₀+15 min labelled "intraday / real-time (15 min horizon)", a medium band to t₀+1 h labelled "intraday operational (1 h horizon)", a wide band to t₀+24 h labelled "day-ahead (24 h horizon)", and the widest band to t₀+48 h labelled "extended day-ahead (48 h horizon)". Below the axis, vertical tick marks indicate the forecast update frequency: every 15 min for the first two bands, every 1–6 h for the 24 h band, and once or twice daily for the 48 h band. A secondary axis above shows the corresponding lead time for each horizon endpoint.]

Horizons, Lead Times, and the Difference Between Them
------------------------------------------------------

These two terms are related but distinct, and confusing them leads to subtle bugs.

**Forecast horizon** is the furthest point in the future that a single forecast run
covers. If you ask OpenSTEF to produce a 24-hour forecast, the horizon is 24 hours.

**Lead time** is the time between *when a forecast is made available* and *the timestamp
it is predicting*. A forecast produced at 08:00 for the 20:00 slot has a lead time of
12 hours. A forecast produced at 19:45 for the same 20:00 slot has a lead time of only
15 minutes.

In OpenSTEF, lead time is a first-class concept represented by the ``LeadTime`` type.
Models are configured with a list of ``LeadTime`` values that define which future
timestamps they are responsible for predicting. This matters because model accuracy
typically degrades with increasing lead time — a model that is excellent at 15-minute
predictions may be mediocre at 48-hour predictions, and vice versa. OpenSTEF lets you
configure separate models (or separate horizon slices within one model) to handle
different parts of the lead-time spectrum.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile

   # Define the lead times this forecaster will produce predictions for
   short_horizons = [
       LeadTime(timedelta(minutes=15)),
       LeadTime(timedelta(minutes=30)),
       LeadTime(timedelta(hours=1)),
   ]

   day_ahead_horizons = [
       LeadTime(timedelta(hours=24)),
       LeadTime(timedelta(hours=36)),
       LeadTime(timedelta(hours=48)),
   ]

The ``LeadTime`` wrapper is not merely cosmetic. OpenSTEF's data pipeline uses it to
correctly align historical features with the target timestamp, ensuring that no
information from *after* the prediction point leaks into training. This is critical for
avoiding optimistic backtesting results.

Forecast Frequency and the Update Cycle
-----------------------------------------

Forecast frequency refers to how often a new forecast run is triggered. This is
independent of the horizon. You can produce a 24-hour forecast every 15 minutes (common
in intraday trading), or a 15-minute forecast once per hour (common in some operational
settings).

In practice, forecast frequency is constrained by:

- **Data availability** — new measurements must arrive before a fresh forecast can be
  computed. If your SCADA system delivers readings every 15 minutes, there is no benefit
  to running the forecaster more frequently than that.
- **Computational cost** — retraining a model is expensive; generating predictions from
  an already-trained model is cheap. OpenSTEF separates these two operations so that
  prediction can run at high frequency while retraining happens on a slower schedule.
- **Operational requirements** — some grid processes (e.g., imbalance settlement) have
  fixed gate closures that define the minimum useful update frequency.

OpenSTEF's backtesting infrastructure makes the update cycle explicit through the
``BacktestConfig`` object:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting.backtest_pipeline import BacktestConfig

   config = BacktestConfig(
       # Resolution of individual prediction samples in the output
       prediction_sample_interval=timedelta(minutes=15),

       # How often a new forecast is generated during the backtest
       predict_interval=timedelta(hours=6),

       # How often the model is retrained
       train_interval=timedelta(days=7),

       # Anchor time for aligning the schedule to regular clock intervals
       align_time=time.fromisoformat("00:00+00"),
   )

This separation — ``prediction_sample_interval``, ``predict_interval``, and
``train_interval`` — reflects real operational architecture. Predictions are produced at
fine resolution (15 min), forecasts are refreshed several times a day (every 6 hours),
and the underlying model is retrained weekly to incorporate recent patterns.

Short-Term vs. Long-Term Forecasting
--------------------------------------

The table below summarises the key differences. OpenSTEF addresses the short-term case
exclusively.

.. list-table::
   :header-rows: 1
   :widths: 25 37 38

   * - Dimension
     - Short-term (OpenSTEF's scope)
     - Long-term (out of scope)
   * - Typical horizon
     - 15 minutes – 48 hours
     - Days, weeks, months, years
   * - Primary drivers
     - Recent load history, weather, time-of-day patterns
     - Economic growth, policy, demographics, climate trends
   * - Update frequency
     - Minutes to hours
     - Daily to monthly
   * - Output resolution
     - 15 min – 1 hour
     - Daily, monthly, or annual
   * - Key challenge
     - Data latency, real-time reliability
     - Structural uncertainty, scenario modelling
   * - Typical use case
     - Grid dispatch, balancing, intraday trading
     - Capacity planning, investment decisions

Short-term forecasting relies heavily on *autocorrelation* — the fact that load right
now is a strong predictor of load in the near future — as well as on weather variables
and calendar effects. Long-term forecasting, by contrast, must model structural shifts
that are invisible in a 48-hour window. OpenSTEF's feature engineering is designed
around the short-term regime; see :doc:`feature_engineering` for details on which
predictors matter and why.

Data Versioning and Forecast Integrity
----------------------------------------

One subtlety that distinguishes production forecasting from offline analysis is *data
versioning*. In a live system, measurements are not always available immediately — they
may arrive late, be revised, or be temporarily missing. A forecast produced at 08:00
should only use data that was genuinely available at 08:00, not data that arrived at
09:00 but is timestamped earlier.

OpenSTEF's ``VersionedTimeSeriesDataset`` tracks when each observation became available
(the ``available_at`` timestamp) alongside when it was measured. This allows the library
to reconstruct the exact information set that existed at any past point in time, making
backtests realistic rather than optimistic.

.. code-block:: python

   from openstef_core.datasets import VersionedTimeSeriesDataset

   # Filter to only data that was available before a given forecast time
   forecast_time = ...  # datetime of the forecast run
   data_at_forecast_time = versioned_dataset.filter_by_available_before(forecast_time)

   # Select a specific lead-time slice for evaluation
   one_hour_ahead = data_at_forecast_time.filter_by_lead_time(
       LeadTime(timedelta(hours=1))
   )

Without this discipline, a model trained or evaluated on "future" data will appear far
more accurate than it will be in production. This is one of the most common sources of
over-optimistic results in energy forecasting research.

.. note::

   Forecast reliability in production involves more than data versioning. When a model
   cannot produce a forecast — due to missing inputs, stale data, or model errors —
   OpenSTEF provides fallback mechanisms to ensure continuity of service. See
   :doc:`reliability_and_fallback` for how to configure these safeguards.

Probabilistic Forecasts and Uncertainty
-----------------------------------------

Short-term forecasts in OpenSTEF are probabilistic by default. Rather than producing a
single point prediction, the library generates predictions at multiple quantile levels
(e.g., the 10th, 50th, and 90th percentiles). This gives downstream systems the
information they need to make risk-aware decisions — for example, sizing reserves to
cover the 90th-percentile scenario rather than just the median.

The relationship between horizons and uncertainty is direct: forecast uncertainty grows
with lead time. A 15-minute prediction is typically tight; a 48-hour prediction carries
substantially more spread. OpenSTEF's quantile outputs make this uncertainty explicit and
horizon-dependent. For a full treatment of how quantiles are interpreted and used, see
:doc:`quantiles_and_confidence`.