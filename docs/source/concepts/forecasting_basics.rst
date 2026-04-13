Forecasting Basics
==================

Short-term energy forecasting is the practice of predicting electricity load or generation
over the next minutes to days. This page explains what that means in concrete terms:
the time horizons involved, how lead time and update frequency interact, and why
short-term forecasting is a fundamentally different problem from its long-term counterpart.
For probabilistic output (quantiles and confidence intervals), see
:doc:`quantiles_and_confidence`. For the models that produce those forecasts, see
:doc:`model_selection`.

What Is Short-Term Forecasting?
--------------------------------

A short-term energy forecast answers a simple question: *how much power will flow through
this asset in the next few hours or days?* Grid operators, balance responsible parties,
and energy traders all need this answer continuously — not once a week, but every quarter-hour
or every hour, updated as new information arrives.

OpenSTEF is a library purpose-built for this operational context. It does not produce
annual energy budgets or decade-scale capacity plans. Instead, it targets the window
between roughly **15 minutes and 48 hours ahead**, where weather forecasts are still
skillful, where historical load patterns are the dominant signal, and where the cost
of a bad prediction is measured in real-time balancing charges.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three related but distinct concepts govern how a short-term forecast is specified:

**Horizon**
   The furthest point in time the forecast covers, measured from the moment the forecast
   is issued. A 24-hour horizon means the model produces predictions for every time step
   from *now* up to 24 hours from now.

**Lead time**
   The distance between the time a forecast was *issued* and the time step it is
   *predicting*. A forecast issued at 08:00 for the 14:00 interval has a lead time of
   6 hours. OpenSTEF tracks lead time explicitly in its dataset structures via the
   ``horizon`` column, allowing you to evaluate model skill separately at each lead time.

**Update frequency**
   How often a fresh forecast is produced. In operational settings this is typically
   every 15 minutes, matching the settlement resolution of most European electricity
   markets. A model with a 48-hour horizon that is updated every 15 minutes will
   therefore issue 96 new forecasts per day, each covering the next 48 hours.

These three dimensions are independent. You can have a 48-hour horizon updated every
15 minutes, or a 1-hour horizon updated once per hour. The right combination depends on
your use case and the latency of your input data.

Typical operational horizons in OpenSTEF:

- **15 minutes** — near-real-time corrections, used where measurement data arrives with
  minimal delay and the model can exploit very recent observations.
- **1 hour** — intra-day trading and redispatch decisions.
- **24 hours** — day-ahead market bidding, the most common operational horizon.
- **48 hours** — extended planning, often used alongside day-ahead to cover the full
  next-day-plus-one window.

How OpenSTEF Represents Horizons
---------------------------------

OpenSTEF uses ``LeadTime`` objects (backed by ``timedelta``) to represent horizons
throughout the library. A forecaster is configured with a list of horizons it must
produce predictions for, and the resulting ``ForecastDataset`` carries a ``horizon``
column so that downstream consumers can filter to the lead time they care about.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.models.forecasting.lgbm_forecaster import (
        LGBMForecaster,
        LGBMForecasterConfig,
    )
    from openstef_models.data_classes.lead_time import LeadTime
    from openstef_models.data_classes.quantile import Quantile

    # Configure a forecaster that produces predictions at two lead times
    config = LGBMForecasterConfig(
        horizons=[
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
    )

Once predictions are available, you can isolate a specific lead time using
``select_horizon``:

.. code-block:: python

    from openstef_models.data_classes.lead_time import LeadTime
    from datetime import timedelta

    # Assume `forecast_dataset` is a ForecastDataset returned by predict()
    day_ahead = forecast_dataset.select_horizon(LeadTime(timedelta(hours=24)))
    df = day_ahead.to_pandas()
    print(df.head())

The dataset also exposes ``horizons()`` as a property, which returns the list of
distinct lead times present in the data — useful for iterating over all available
horizons programmatically:

.. code-block:: python

    for horizon in forecast_dataset.horizons():
        subset = forecast_dataset.select_horizon(horizon)
        print(f"Lead time {horizon}: {len(subset.to_pandas())} rows")

Short-Term vs. Long-Term Forecasting
--------------------------------------

Understanding why short-term forecasting is a distinct discipline helps you make better
modelling decisions.

**Signal sources differ.** At horizons beyond a few days, weather forecast skill
degrades rapidly and the dominant signal shifts to seasonal patterns, economic activity,
and structural trends. Short-term forecasting can exploit high-resolution numerical
weather prediction (NWP) data — wind speed, solar irradiance, temperature — as
first-class features, because those forecasts are still reliable within the 48-hour
window. Feature engineering for these inputs is covered in :doc:`feature_engineering`.

**Error characteristics differ.** Long-term forecasts are evaluated on annual or monthly
aggregates where random errors cancel out. Short-term forecasts are evaluated at every
15-minute interval, so the distribution of errors matters as much as the mean. This is
why OpenSTEF produces *probabilistic* forecasts by default — see
:doc:`quantiles_and_confidence` for details.

**Data freshness matters.** A long-term model can be retrained monthly. A short-term
operational model must handle stale inputs, sensor outages, and delayed data gracefully.
OpenSTEF's fallback mechanisms address this directly; see :doc:`reliability_and_fallback`.

**Temporal resolution is fine-grained.** The default ``sample_interval`` in OpenSTEF
datasets is 15 minutes (``timedelta(minutes=15)``), matching the standard metering
resolution for grid-connected assets. Long-term models typically operate on daily or
monthly aggregates and would discard most of this information.

The Role of Data Versioning
-----------------------------

One subtlety unique to operational short-term forecasting is *data versioning*: the
fact that the value of a measurement at time *t* may not be available until some time
after *t*. Metering data is often delayed by 15–60 minutes; weather reanalysis data
arrives even later. A model trained without accounting for this will appear accurate in
backtesting but fail in production because it used data that would not have been
available at forecast time.

OpenSTEF addresses this through the ``available_at`` column in its dataset structures.
Every observation carries a timestamp indicating when it became available, and the
library's ``filter_by_available_before`` method lets you reconstruct exactly what a
model would have seen at any historical forecast time:

.. code-block:: python

    from datetime import datetime, timezone

    # Simulate what data was available at 08:00 on a given day
    cutoff = datetime(2024, 6, 1, 8, 0, tzinfo=timezone.utc)
    available_data = versioned_dataset.filter_by_available_before(cutoff)

This makes backtesting honest and is a prerequisite for reliable model evaluation.
The interplay between data versioning and model selection is discussed further in
:doc:`model_selection`.

Practical Implications for Model Configuration
------------------------------------------------

A few rules of thumb follow directly from the concepts above:

- **Match your horizon to your use case.** If you are bidding in a day-ahead market,
  configure a 24-hour or 48-hour horizon. If you are doing intra-day corrections,
  a 1-hour horizon with high update frequency is more appropriate.

- **Shorter horizons are generally more accurate.** Forecast error increases with lead
  time. If your application only needs the next hour, do not request a 48-hour forecast
  and discard most of it — configure the model for the horizon you actually need so
  that training and evaluation reflect the correct difficulty.

- **Update frequency should match data latency.** There is no benefit to re-issuing a
  forecast every 15 minutes if your input weather data only refreshes hourly. Align
  update frequency with the refresh rate of your slowest critical input.

- **Use ``max_horizon`` to size your context window.** OpenSTEF forecaster configs
  expose a ``max_horizon`` property that returns the furthest lead time in the
  configured list. Use this when computing how much historical context the model
  needs during training.

.. code-block:: python

    # max_horizon is derived automatically from the horizons list
    print(f"Furthest lead time: {config.max_horizon}")

.. note::

   The ``sample_interval`` of your dataset must be consistent with your horizon
   granularity. A 15-minute ``sample_interval`` with a 24-hour horizon produces
   96 forecast steps. Changing ``sample_interval`` to 1 hour reduces this to 24 steps
   and will affect which lag features are meaningful. See :doc:`feature_engineering`
   for guidance on aligning features with resolution.

Summary
-------

Short-term energy forecasting in OpenSTEF operates over horizons from 15 minutes to
48 hours, with forecasts updated as frequently as every 15 minutes. The key concepts
to keep in mind are:

- **Horizon** — how far ahead the forecast extends.
- **Lead time** — the distance from issue time to a specific predicted interval,
  tracked explicitly in every ``ForecastDataset``.
- **Update frequency** — how often a fresh forecast is issued, driven by data latency
  and operational requirements.
- **Data versioning** — the ``available_at`` mechanism that makes backtesting honest
  by respecting what data would have existed at forecast time.

From here, the natural next steps are understanding how OpenSTEF expresses uncertainty
across those horizons (:doc:`quantiles_and_confidence`) and choosing the right model
for your specific horizon and asset type (:doc:`model_selection`).