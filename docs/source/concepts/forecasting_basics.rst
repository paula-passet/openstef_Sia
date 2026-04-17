Short-Term Forecasting Basics
=============================

Short-term energy forecasting is the practice of predicting electricity load, generation, or related quantities over a window of minutes to a few days ahead. This page explains what that means in practice: how forecast horizons are defined, what lead time and update frequency mean, and how short-term forecasting differs fundamentally from longer-range planning approaches. The concepts here underpin everything OpenSTEF does as a library, so it is worth understanding them clearly before diving into configuration or code.

.. note::

   This page covers the *what* and *why* of short-term forecasting. For the probabilistic side of forecasts (quantiles and confidence intervals), see :doc:`quantiles_and_confidence`. For the features that drive forecast accuracy, see :doc:`feature_engineering`.

----

What Is Short-Term Energy Forecasting?
---------------------------------------

A short-term energy forecast answers the question: *given everything we know right now, what will the load (or generation) be at some future point in time?* The defining characteristic is that the forecast horizon — the distance into the future being predicted — is short enough that the dominant drivers of variability are weather, time-of-day patterns, and recent load behaviour, rather than structural changes in the grid or economy.

In practice, "short-term" in the power sector typically means anything from the next 15 minutes up to about 48 hours. Beyond that, medium- and long-term forecasting takes over, relying on different models, different data sources, and different accuracy expectations.

Short-term forecasts are operationally critical. Grid operators use them to schedule reserves, balance supply and demand in near-real-time, and plan intraday trading. Distribution system operators use them to anticipate congestion on local feeders. Aggregators use them to optimise battery dispatch and demand-response programmes. In all of these cases, a forecast that is even a few percentage points more accurate translates directly into cost savings or avoided curtailment.

----

Forecast Horizons
-----------------

A **forecast horizon** (also called a *lead time*) is the time offset between the moment a forecast is made and the moment being predicted. OpenSTEF represents horizons using the ``LeadTime`` type, which wraps a ``timedelta`` and can be constructed from ISO 8601 duration strings.

Common horizons in short-term energy forecasting are:

- **15 minutes** — intraday balancing and real-time control
- **1 hour** — intraday market gate closures and operational planning
- **24 hours** — day-ahead market bidding (the most common single horizon)
- **48 hours** — two-day-ahead planning, often used alongside day-ahead

These are not arbitrary choices. Each horizon corresponds to a decision that must be made at a specific time, with a specific data availability constraint. A day-ahead market closes at noon for delivery the following day, so the 24-hour forecast must be ready by then — and must be built only from data that is actually available at noon.

.. note::

   [DIAGRAM: Timeline showing forecast horizons and their operational context. The horizontal axis represents wall-clock time. At "now" (T=0), four forecast arrows extend forward: 15 min (intraday balancing), 1 h (intraday gate closure), 24 h (day-ahead market), and 48 h (two-day-ahead planning). Each arrow is annotated with its typical update frequency (every 15 min, every hour, every hour, twice daily) and the decision it supports. A shaded region behind each arrow represents the training data window used to build that forecast.]

----

Lead Time and Data Availability
---------------------------------

Lead time and data availability are two sides of the same coin. When you train a model to predict 24 hours ahead, the features you use must be features that will genuinely be available 24 hours before delivery — not features that only become available after the fact.

This is a subtle but important distinction. Consider metered load data: it is typically available with a delay of 15–60 minutes. If you naively train a 24-hour model using the most recent metered value as a feature, you are implicitly assuming that value will be available at prediction time — which it will be, because 24 hours is far longer than the 60-minute delay. But if you train a 15-minute-ahead model using the same feature, you must be careful: the "most recent" metered value may not yet be available when the forecast is needed.

OpenSTEF handles this through the ``VersionedTimeSeriesDataset``, which tracks an ``available_at`` timestamp for each observation. When you call ``select_version()`` or ``filter_by_available_before()``, the library automatically restricts the dataset to only those observations that would have been available at the time the forecast was made. This prevents data leakage and ensures that backtests reflect real operational conditions.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import LeadTime

   # Define two horizons: 15 minutes and 24 hours ahead
   horizon_15min = LeadTime(timedelta(minutes=15))
   horizon_24h   = LeadTime(timedelta(hours=24))

   # Select only the data that would have been available
   # when making a 24-hour-ahead forecast
   data_for_24h = dataset.filter_by_lead_time(lead_time=horizon_24h).select_version()

   # The 15-minute horizon sees more recent data
   data_for_15min = dataset.filter_by_lead_time(lead_time=horizon_15min).select_version()

----

Multi-Horizon Forecasting
--------------------------

Rather than training a separate model for each horizon, OpenSTEF supports **multi-horizon forecasting**: a single model that produces predictions at several lead times simultaneously. This is efficient when the underlying patterns are shared across horizons — for example, a gradient-boosted model that learns that load at T+1h and load at T+24h are both influenced by temperature, but with different lag structures.

Not all model types are equally suited to this. Linear models, for instance, struggle with the missing-data patterns that arise when different horizons have different feature availability windows. Tree-based models like XGBoost handle these gaps naturally. OpenSTEF's ``Forecaster`` base class documents this distinction explicitly, and the library's model zoo reflects it in which models accept a list of horizons versus a single horizon.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Configure a workflow that forecasts at three horizons simultaneously
   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="load_forecast_v1",
           model="gblinear",
           horizons=[
               LeadTime(timedelta(hours=1)),
               LeadTime(timedelta(hours=24)),
               LeadTime(timedelta(hours=48)),
           ],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           target_column="load",
           temperature_column="temperature_2m",
           wind_speed_column="wind_speed_10m",
           radiation_column="shortwave_radiation",
       )
   )

.. note::

   Quantiles like ``Q(0.1)`` and ``Q(0.9)`` give you a probabilistic forecast rather than a single point estimate. See :doc:`quantiles_and_confidence` for a full explanation of how OpenSTEF represents forecast uncertainty.

----

Update Frequency
-----------------

A forecast horizon tells you *how far ahead* you are predicting. Update frequency tells you *how often* you refresh that prediction. These are independent dimensions, and confusing them is a common source of misconfiguration.

A 24-hour-ahead forecast might be updated:

- **Once per day** — sufficient for day-ahead market participation, where the gate closes at a fixed time
- **Every hour** — useful for intraday trading, where a more recent 24-hour forecast can improve bids
- **Every 15 minutes** — appropriate when the forecast feeds a real-time control loop

Higher update frequency means more compute, but it also means the forecast incorporates more recent observations. For short horizons (15 minutes, 1 hour), frequent updates are almost always worthwhile because recent load behaviour is highly predictive. For longer horizons (24–48 hours), the marginal value of updating every 15 minutes is smaller, since the dominant driver at that range is weather, which changes slowly.

In OpenSTEF, update frequency is a deployment concern rather than a model concern. The library provides the forecasting primitives; your orchestration layer (a scheduler, a workflow engine, or a simple cron job) determines how often ``predict()`` is called.

----

How Short-Term Differs from Long-Term Forecasting
---------------------------------------------------

The differences between short-term and long-term forecasting are not merely a matter of scale — they reflect fundamentally different problem structures.

**Dominant drivers change with horizon.** At 15 minutes ahead, the best predictor of load is the load right now. At 24 hours ahead, weather forecasts and calendar effects dominate. At one month ahead, economic activity and temperature normals matter more than any individual weather event. OpenSTEF is designed specifically for the short-term regime, where high-frequency time series features and numerical weather prediction (NWP) data are the primary inputs.

**Accuracy expectations are different.** A short-term model that achieves 2–3% mean absolute percentage error (MAPE) on a distribution feeder is considered good. A long-term capacity planning model might accept 10–15% error as perfectly adequate, because the decisions it informs have different tolerances.

**Data freshness matters acutely.** Long-term models are typically retrained infrequently on historical data. Short-term models must be retrained regularly — often daily or weekly — to track seasonal shifts, new loads connecting to the grid, and changes in consumer behaviour. OpenSTEF's training pipelines are designed with this operational cadence in mind.

**Probabilistic output is more actionable.** At short horizons, a narrow confidence interval around the forecast directly informs how much reserve capacity to hold. At long horizons, uncertainty is so large that point forecasts and wide intervals are both used differently. OpenSTEF's native support for quantile forecasting is most valuable in the short-term operational context.

----

Sample Intervals and Resolution
---------------------------------

Closely related to horizon and update frequency is the **sample interval** — the temporal resolution of the time series being forecast. OpenSTEF works with any regular sample interval, but the most common in the energy sector are:

- **15 minutes** — the standard settlement period in many European electricity markets
- **1 hour** — common for aggregated national or regional load data
- **5 minutes** — used in some real-time balancing contexts

The sample interval is a property of the dataset, not the model. When you construct a ``TimeSeriesDataset``, you specify ``sample_interval`` explicitly. The library uses this to validate that your data is regular, to compute lag features at the correct offsets, and to ensure that horizon definitions are consistent with the data resolution.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd

   # A 15-minute resolution dataset
   dataset = TimeSeriesDataset(
       data=df,                                  # pd.DataFrame with DatetimeIndex
       sample_interval=timedelta(minutes=15),
   )

   print(dataset.sample_interval)   # datetime.timedelta(seconds=900)
   print(dataset.horizons())        # list of LeadTime objects present in the data

----

Putting It Together
--------------------

Short-term energy forecasting in OpenSTEF is built around three interlocking concepts:

- **Horizon** — how far ahead you predict, represented as a ``LeadTime``
- **Data availability** — what observations are genuinely available at prediction time, enforced by ``VersionedTimeSeriesDataset``
- **Update frequency** — how often you refresh the forecast, controlled by your deployment schedule

Getting these right is the foundation of a reliable forecasting system. A model trained without respecting data availability will appear accurate in backtests but fail in production. A model updated too infrequently will miss intraday load shifts. A model configured with the wrong sample interval will produce features at incorrect offsets.

The rest of this concepts section builds on these foundations. :doc:`feature_engineering` explains which predictors matter most at different horizons and how OpenSTEF constructs them automatically. :doc:`quantiles_and_confidence` covers how the library expresses forecast uncertainty. :doc:`reliability_and_fallback` describes what happens when a model cannot produce a forecast and how OpenSTEF degrades gracefully.