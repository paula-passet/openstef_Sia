Short-Term Forecasting Basics
=============================

This page explains what short-term energy forecasting is, why it matters for grid
operations, and how the key concepts of horizons, lead times, and update frequency
shape the way OpenSTEF models are structured and evaluated.

What Is Short-Term Forecasting?
--------------------------------

Short-term energy forecasting is the practice of predicting electricity load, generation,
or related quantities over intervals ranging from a few minutes to a few days ahead.
Unlike long-term forecasting — which projects annual demand growth or capacity needs
over years or decades — short-term forecasting is concerned with *operational* decisions:
balancing supply and demand in near real time, scheduling flexible assets, and managing
grid congestion.

The defining characteristic of short-term forecasting is that it must be *actionable*
within the operational window of the power system. A forecast that arrives too late, or
that covers too coarse a time resolution, is of limited use to a grid operator who needs
to dispatch a battery or curtail a wind farm in the next quarter-hour.

OpenSTEF is designed specifically for this operational context. Its data structures,
model interfaces, and evaluation tools are all built around the idea that forecasts are
produced repeatedly, at regular intervals, for a set of defined lead times ahead of the
current moment.

Why Short-Term Forecasting Is Difficult
----------------------------------------

Long-term forecasts can rely on slowly changing trends — population growth, economic
activity, seasonal patterns. Short-term forecasts must capture rapid fluctuations driven
by weather, human behaviour, and the increasing penetration of variable renewable
generation. A cloud passing over a solar farm, a factory starting its morning shift, or
an unexpected cold snap can each cause load swings that dwarf the signal visible in
long-term data.

This volatility means that:

- **Recency matters.** A model trained on data from six months ago may perform poorly
  today if the grid topology or consumer mix has changed.
- **Weather is central.** Temperature, irradiance, and wind speed are among the strongest
  predictors of short-term load and generation. See :doc:`feature_engineering` for how
  OpenSTEF incorporates these signals.
- **Uncertainty must be quantified.** A single point forecast is rarely sufficient;
  operators need to know how confident the model is. OpenSTEF produces probabilistic
  forecasts expressed as quantiles. See :doc:`quantiles_and_confidence` for details.

Horizons and Lead Times
------------------------

Two terms appear throughout OpenSTEF's API and deserve precise definitions.

A **lead time** is the interval between the moment a forecast is *generated* and the
timestamp it is *predicting*. If a forecast is produced at 09:00 and predicts the load
at 11:00, the lead time is two hours. In OpenSTEF, lead times are represented by the
``LeadTime`` type, which wraps a ``timedelta``.

A **horizon** is the maximum lead time covered by a single forecast run. A 48-hour
horizon means the model produces predictions for every sample interval from now up to
48 hours ahead.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

The practical implication is that **accuracy degrades with lead time**. A 15-minute-ahead
forecast can exploit very recent measurements and has little time for conditions to
change. A 48-hour-ahead forecast must rely on numerical weather prediction models and
broader statistical patterns. OpenSTEF models are therefore trained and evaluated
*per lead time*, not as a single aggregate.

In the ``EvaluationConfig``, you specify which lead times you care about:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.evaluation.pipeline import EvaluationConfig
    from openstef_models.evaluation.types import AvailableAt, LeadTime, Window

    config = EvaluationConfig(
        available_ats=[
            AvailableAt.from_string("D-1T06:00"),  # day-ahead forecast available at 06:00
        ],
        lead_times=[
            LeadTime.from_string("PT1H"),   # 1-hour ahead
            LeadTime.from_string("PT6H"),   # 6-hours ahead
            LeadTime.from_string("PT24H"),  # day-ahead
            LeadTime.from_string("PT48H"),  # two-days ahead
        ],
        windows=[
            Window(lag=timedelta(hours=0), size=timedelta(days=21)),
        ],
    )

The ``available_at`` field is equally important: it records *when* a forecast became
usable, accounting for the time needed to collect input data, run the model, and
distribute results. A forecast nominally generated at midnight may not be available to
downstream systems until 06:00 if weather data ingestion takes several hours.

Forecast Frequency and the Update Cycle
-----------------------------------------

Short-term forecasts are not produced once and forgotten. They are regenerated
continuously as new observations arrive. The **update frequency** — how often a new
forecast run is triggered — is a design choice that balances computational cost against
accuracy.

Typical patterns in grid operations:

- **15-minute updates** for intraday balancing, where the most recent metering data
  can materially improve a near-term prediction.
- **Hourly or 6-hourly updates** for day-ahead scheduling, where the dominant input
  is a numerical weather forecast that itself updates every few hours.
- **Daily updates** for 48-hour outlooks used in maintenance planning or congestion
  management.

In OpenSTEF's backtesting framework, the ``predict_interval`` and ``train_interval``
parameters in ``BacktestConfig`` mirror this operational reality:

.. code-block:: python

    from datetime import timedelta, time
    from openstef_beam.backtesting.pipeline import BacktestConfig

    config = BacktestConfig(
        prediction_sample_interval=timedelta(minutes=15),  # resolution of output forecast
        predict_interval=timedelta(hours=6),               # how often a new forecast is generated
        train_interval=timedelta(days=7),                  # how often the model is retrained
        align_time=time.fromisoformat("00:00+00"),         # anchor for scheduling
    )

Here ``prediction_sample_interval`` controls the *resolution* of each forecast (the
spacing between predicted timestamps), while ``predict_interval`` controls how often
the whole forecast is regenerated. These are independent: you can produce a 15-minute-
resolution forecast every 6 hours, or a 1-hour-resolution forecast every 15 minutes,
depending on operational needs.

Short-Term vs. Long-Term Forecasting: A Practical Comparison
--------------------------------------------------------------

The table below summarises the key differences that motivate a dedicated short-term
forecasting library like OpenSTEF.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Dimension
     - Short-term (OpenSTEF focus)
     - Long-term
   * - Horizon
     - Minutes to ~48 hours
     - Weeks, months, years
   * - Primary drivers
     - Weather, time-of-day, recent load
     - Economic growth, policy, demographics
   * - Update frequency
     - Minutes to hours
     - Monthly or annual
   * - Output resolution
     - 15 min – 1 hour
     - Daily, monthly, or annual
   * - Uncertainty expression
     - Quantile forecasts per lead time
     - Scenario ranges or confidence intervals
   * - Model retraining
     - Weekly or more frequent
     - Infrequent, often manual

How Lead Time Shapes Model Design
-----------------------------------

Because accuracy varies with lead time, OpenSTEF supports **multi-horizon forecasting**:
a single model can be trained to produce predictions simultaneously for several lead
times, with the model architecture and feature set adapted to each horizon.

For short lead times (under one hour), lag features derived from recent measurements
are highly informative — the load five minutes ago is a strong predictor of the load
five minutes from now. For longer lead times, those same lag features become stale and
weather-based features dominate.

.. note::

   When using lag-based features, the ``cutoff_history`` parameter in
   ``ForecastingModel`` must be set to exclude the initial rows where lags produce
   ``NaN`` values. For example, a 14-day lag requires at least 14 days of warm-up data
   before the first usable training sample.

The ``LeadTime`` type in OpenSTEF encodes this awareness directly into the data
structures. Datasets can be filtered or selected by lead time:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.data.types import LeadTime

    # Select only the 24-hour-ahead slice of a multi-horizon dataset
    horizon_24h = LeadTime(timedelta(hours=24))
    subset = dataset.filter_by_lead_time(horizon_24h)

This makes it straightforward to train separate models per horizon, evaluate them
independently, or combine them in an ensemble. See :doc:`meta_ensembles` for how
OpenSTEF's ensemble layer exploits this structure.

Reliability in Production
--------------------------

Operational forecasting systems must keep producing outputs even when a model fails,
input data is delayed, or a sensor goes offline. Short-term forecasts are particularly
sensitive to data gaps because recent observations are their most valuable input.
OpenSTEF addresses this through fallback strategies described in
:doc:`reliability_and_fallback`.

For probabilistic aspects of short-term forecasts — how to interpret the quantile
outputs that OpenSTEF produces alongside point predictions — see
:doc:`quantiles_and_confidence`.