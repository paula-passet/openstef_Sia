Short-Term Forecasting Basics
=============================

Short-term energy forecasting is the practice of predicting electricity load or generation
over the next minutes to days. This page explains what that means in concrete terms:
the time horizons involved, how lead time and update frequency interact, and how OpenSTEF
models these concepts. For probabilistic output (quantiles and confidence intervals) see
:doc:`quantiles_and_confidence`. For the input features that drive accuracy see
:doc:`feature_engineering`.

What Is Short-Term Forecasting?
--------------------------------

A short-term energy forecast answers the question: *given everything observable right now,
what will the load or generation at a grid point be at some future moment?* "Short-term"
conventionally means up to 48–72 hours ahead. Beyond that, the dominant uncertainty shifts
from weather variability to structural changes in consumption patterns, and different
modelling approaches apply.

Short-term forecasts are consumed by grid operators for congestion management, by balance
responsible parties for imbalance settlement, and by trading desks for intraday and
day-ahead markets. Each use case imposes its own requirements on *how far ahead* the
forecast must reach and *how often* it must be refreshed.

Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three related but distinct concepts govern the temporal structure of a forecast:

- **Horizon** — the distance in time between when a forecast is *generated* and the
  moment it *describes*. A 36-hour horizon means the model is predicting 36 hours into
  the future.
- **Lead time** — used interchangeably with horizon in OpenSTEF's API (see
  ``openstef_core.types.LeadTime``). It explicitly accounts for data availability: a
  measurement taken at time *t* may only become available in the system at *t + Δ*, so
  the effective lead time includes that ingestion delay.
- **Update frequency** — how often a new forecast is issued. A model that runs every
  15 minutes produces 96 fresh forecasts per day for the same target timestamp, each
  one progressively more accurate as the horizon shrinks.

These three dimensions interact. A day-ahead market requires a forecast to be *available*
by 12:00 CET for delivery the following day — that is a hard deadline on the
``available_at`` time. An intraday balancing application may need a new forecast every
quarter-hour but only needs to look 2–4 hours ahead.

.. note:: [DIAGRAM: Timeline showing four forecast horizons (15 min, 1 h, 24 h, 48 h) on a horizontal time axis. For each horizon, an arrow originates at the "now" marker and points to the target timestamp. Alongside each arrow, annotate the typical update frequency (every 15 min, every 15 min, every hour, every 6 h) and the data availability delay (e.g. 5 min SCADA latency). Show how a 48 h horizon issued at T=0 and a 1 h horizon issued at T=47 h both describe the same target moment, illustrating convergence of forecasts over time.]

Short-Term vs. Long-Term Forecasting
--------------------------------------

The distinction is not merely about the number of hours on the axis. Short-term and
long-term forecasting differ in:

- **Dominant drivers.** Short-term load is driven by weather (temperature, irradiance,
  wind speed), time-of-day patterns, and recent observed load. Long-term forecasts are
  driven by economic growth, electrification trends, and demographic change — none of
  which are observable in real-time sensor data.
- **Model architecture.** Short-term models are trained on high-frequency time series
  (15-minute or hourly resolution) and rely heavily on lag features and weather
  forecasts. Long-term models use annual or monthly aggregates and regression against
  macro-economic indicators.
- **Error characteristics.** Short-term forecast error is dominated by weather forecast
  uncertainty and measurement noise. Long-term error is dominated by scenario
  uncertainty. OpenSTEF's probabilistic output (quantiles) is calibrated for the
  short-term regime; see :doc:`quantiles_and_confidence`.
- **Retraining cadence.** A short-term model may be retrained weekly or even daily as
  new observations arrive. A long-term model is typically retrained annually.

OpenSTEF is designed exclusively for the short-term regime.

How OpenSTEF Represents Horizons
----------------------------------

OpenSTEF uses ``LeadTime`` — a thin wrapper around ``datetime.timedelta`` — to express
horizons throughout the API. A ``LeadTime`` can be constructed from a timedelta directly
or from an ISO 8601 duration string:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime

    # Equivalent ways to express a 36-hour horizon
    h36 = LeadTime(timedelta(hours=36))
    h36_iso = LeadTime.from_string("PT36H")

    # A 15-minute horizon
    h15min = LeadTime.from_string("PT15M")

A forecaster is configured with one or more horizons at construction time. Single-horizon
forecasters (such as ``ConstantMedianForecaster``) accept exactly one lead time; multi-
horizon forecasters (such as gradient-boosted tree models) accept a list and handle the
complexity of varying feature availability internally.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_core.testing import create_synthetic_forecasting_dataset

    # Build a 90-day synthetic dataset at hourly resolution
    dataset = create_synthetic_forecasting_dataset(
        length=timedelta(days=90),
        wind_influence=-10.0,
        temp_influence=5.0,
        radiation_influence=-7.0,
        stochastic_influence=2.0,
        sample_interval=timedelta(hours=1),
    )

    # Configure a workflow targeting a 36-hour horizon
    workflow = create_forecasting_workflow(
        config=ForecastingWorkflowConfig(
            model_id="my_gblinear_model",
            model="gblinear",
            horizons=[LeadTime.from_string("PT36H")],
            quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        )
    )

    fit_result = workflow.fit(dataset)
    forecasts = workflow.predict(dataset)

The ``horizons`` list in ``ForecastingWorkflowConfig`` directly controls which lead times
the trained model will produce predictions for. Requesting multiple horizons from a
capable model is more efficient than training separate models, because the model can share
learned patterns across horizons.

Multi-Horizon Considerations
------------------------------

Not all model architectures handle multiple horizons equally well. OpenSTEF's
documentation distinguishes two cases:

- **Multi-horizon models** (e.g. XGBoost, GBLinear) accept a list of lead times and
  train a single model that predicts across all of them. Features that are unavailable
  at short lead times (such as a lag-1 feature when predicting 15 minutes ahead) are
  handled internally through masking or conditional feature sets.
- **Single-horizon models** (e.g. linear models, ``ConstantMedianForecaster``) are
  trained independently for each lead time. They are simpler but require one model
  instance per horizon, which increases storage and inference overhead.

When choosing horizons, consider data availability. If your SCADA system delivers
measurements with a 10-minute delay, a 5-minute horizon is physically impossible: the
model would need to predict a timestamp for which the most recent observation is already
older than the target. OpenSTEF's ``LeadTime`` concept encodes this constraint explicitly
— the horizon is measured from the moment data *becomes available*, not from wall-clock
time.

Filtering Forecasts by Horizon
--------------------------------

Once a model has produced a ``ForecastDataset``, you can slice it by lead time to inspect
or evaluate predictions at a specific horizon:

.. code-block:: python

    from openstef_core.types import LeadTime

    # Retrieve only the 36-hour-ahead predictions
    h36 = LeadTime.from_string("PT36H")
    forecasts_36h = forecasts.filter_by_lead_time(lead_time=h36)

    # Inspect available horizons in the dataset
    print(forecasts.horizons())

The ``ForecastDataset`` also exposes ``available_at_series()`` and ``lead_time_series()``
properties, which are useful when diagnosing whether forecasts were generated at the
expected times.

.. note::

   For a complete treatment of how forecast uncertainty varies with horizon — and how
   to interpret the quantile bands that widen as lead time grows — see
   :doc:`quantiles_and_confidence`.

Practical Horizon Selection
-----------------------------

Choosing the right set of horizons is an operational decision, not a modelling one.
A few rules of thumb:

- **Match your settlement period.** If your balancing market settles in 15-minute
  intervals, you need forecasts at 15-minute resolution. If it settles hourly, hourly
  resolution is sufficient.
- **Cover your operational lead time.** A transmission operator who needs 2 hours to
  re-dispatch generation should request forecasts at horizons of at least 2–3 hours.
  Day-ahead market participants need at least a 24-hour horizon available by gate closure.
- **Don't over-specify.** Each additional horizon increases training time and, for
  single-horizon models, storage. Start with the horizons your downstream process
  actually consumes.
- **Account for data latency.** If upstream measurements arrive with a 15-minute delay,
  your shortest meaningful horizon is ``PT15M``. Shorter horizons will silently degrade
  to persistence-like behaviour without this constraint being explicit.

For production reliability — including what happens when a model fails to produce a
forecast within the required window — see :doc:`reliability_and_fallback`. For the
feature engineering that makes short-term forecasts accurate across different horizons,
see :doc:`feature_engineering`.