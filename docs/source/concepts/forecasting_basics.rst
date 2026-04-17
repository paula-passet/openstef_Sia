Forecasting Basics
==================

Short-term energy forecasting sits at the operational heart of grid management. This page explains what short-term forecasting means in the context of OpenSTEF, why the time dimension is so important, and how the library's core concepts — horizons, lead times, and forecast frequency — fit together.

.. note::

   This page covers the *what* and *why* of short-term forecasting. For the probabilistic
   side of forecasts (quantiles and confidence intervals), see :doc:`quantiles_and_confidence`.
   For the features that drive forecast accuracy, see :doc:`feature_engineering`.

What Is Short-Term Energy Forecasting?
---------------------------------------

Short-term energy forecasting is the task of predicting electricity load, generation, or related quantities over a window of minutes to a few days ahead. It is distinct from medium- and long-term forecasting in both purpose and method:

- **Long-term forecasting** (months to years) informs capacity planning and infrastructure investment. It relies on demographic trends, economic indicators, and climate projections. Accuracy at the individual-hour level is not the goal.
- **Short-term forecasting** (minutes to ~48 hours) drives real-time grid balancing, congestion management, and energy trading. Here, accuracy at the 15-minute or hourly resolution matters enormously, and forecasts must be refreshed continuously as new data arrives.

OpenSTEF is built exclusively for the short-term regime. Its data structures, model interfaces, and pipeline utilities all assume that forecasts are produced repeatedly, at high frequency, for a rolling window of future time steps.

Why Short-Term Forecasting Is Hard
------------------------------------

The difficulty is not just statistical — it is operational. A forecast that is technically accurate but arrives too late to act on is worthless. Three interacting factors make this challenging:

**Temporal resolution.** Grid operators need forecasts at 15-minute intervals, not daily averages. A model must capture intra-day patterns (morning ramp-up, evening peak) as well as day-of-week and seasonal effects simultaneously.

**Data latency.** Measurements from smart meters, weather stations, and SCADA systems do not arrive instantaneously. A reading timestamped at 10:00 may not be available in your database until 10:15 or later. Any model that ignores this will appear to perform well in backtesting but fail in production — a form of lookahead bias. OpenSTEF addresses this through its ``VersionedTimeSeriesDataset``, which tracks when each observation became available, not just when it was measured.

**Continuous re-forecasting.** Unlike a batch prediction job that runs once a day, a production short-term forecasting system must issue updated forecasts every 15 minutes (or every hour), incorporating the latest measurements. The library is designed around this update loop.

Horizons and Lead Times
------------------------

Two terms appear throughout OpenSTEF's API and deserve precise definitions.

A **horizon** (represented by the ``LeadTime`` type) is the gap between the moment a forecast is *issued* and the moment it is *valid for*. A horizon of ``PT1H`` means "predict what will happen one hour from now." A horizon of ``PT36H`` means "predict what will happen 36 hours from now."

A **lead time** is used interchangeably with horizon in OpenSTEF's type system. The ``LeadTime`` class wraps a ``timedelta`` and appears wherever the library needs to express how far ahead a prediction reaches.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

The table below summarises the typical horizons OpenSTEF is used for and their operational context:

.. list-table::
   :header-rows: 1
   :widths: 15 25 30 30

   * - Horizon
     - Typical use case
     - Update frequency
     - Key data constraint
   * - 15 min
     - Intra-hour grid balancing
     - Every 15 minutes
     - Near-real-time SCADA; very short lag features
   * - 1 h
     - Operational dispatch
     - Every 15–60 minutes
     - Latest metered values; 1–4 h weather forecasts
   * - 24 h
     - Day-ahead energy trading
     - 1–2 times per day
     - NWP weather forecasts; previous-day actuals
   * - 48 h
     - Extended operational planning
     - Once per day
     - Medium-range NWP; calendar features dominate

A single ``Forecaster`` instance in OpenSTEF can be configured to produce predictions for multiple horizons simultaneously. Models such as XGBoost handle this naturally because they can condition on horizon-specific lag features. Simpler linear models are typically restricted to a single horizon because they cannot handle the conditional feature structure that multi-horizon prediction requires.

Data Availability and Lookahead Bias
--------------------------------------

Understanding lead times is inseparable from understanding data availability. For a forecast issued at time *t* with horizon *h*, the prediction is valid at time *t + h*. But the features used to make that prediction can only include data that was *available* at time *t* — not data measured at *t* that hasn't yet been transmitted.

OpenSTEF models this with the ``AvailableAt`` type. When you filter a ``VersionedTimeSeriesDataset`` by ``available_at``, you get a point-in-time snapshot of the data as it would have existed at that moment. This is essential for honest backtesting: without it, your offline metrics will be optimistic and your production model will underperform.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime, AvailableAt

   # Suppose `df` is a DataFrame with columns:
   #   timestamp (index), load, available_at
   # where available_at records when each measurement was ingested.

   dataset = VersionedTimeSeriesDataset.from_pandas(df, sample_interval=timedelta(minutes=15))

   # Simulate what data would have been available at 06:00 on the target day,
   # then select only rows reachable with a 36-hour lead time.
   snapshot = (
       dataset
       .filter_by_available_at(AvailableAt.from_string("D-1T06:00"))
       .filter_by_lead_time(LeadTime(timedelta(hours=36)))
       .select_version()
   )

   print(snapshot.horizons)   # list of LeadTime values present in the snapshot

The call to ``select_version()`` is the key step: it selects the latest available version of each timestamp, preventing any future data from leaking into the feature set.

Configuring Horizons in a Forecaster
--------------------------------------

When you instantiate a forecaster through OpenSTEF, you declare the horizons it should produce. The library then ensures that training data, lag features, and predictions are all aligned to those horizons.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q

   # Define the horizons you need
   horizons = [
       LeadTime(timedelta(minutes=15)),
       LeadTime(timedelta(hours=1)),
       LeadTime(timedelta(hours=24)),
       LeadTime(timedelta(hours=47, minutes=45)),  # ~48 h at 15-min resolution
   ]

   # Q is a convenience constructor for Quantile
   quantiles = [Q(0.1), Q(0.5), Q(0.9)]

   # Pass horizons and quantiles when building your forecasting model.
   # The exact model class depends on your pipeline configuration;
   # see the full pipeline example in the tutorials.
   print(f"Forecasting {len(horizons)} horizons, "
         f"from {horizons[0].value} to {horizons[-1].value} ahead.")

.. note::

   The ``max_horizon`` property on any forecaster returns the furthest ``LeadTime``
   in its configuration. Pipeline utilities use this to determine how much historical
   data to fetch when preparing training sets.

How Forecast Frequency Relates to Horizon
-------------------------------------------

Forecast frequency (how often you re-run the model) and forecast horizon (how far ahead you predict) are independent but related choices.

A common pattern in grid operations is to run the model every 15 minutes and produce forecasts for all horizons from 15 minutes to 48 hours in a single pass. This means that at any given moment, every future 15-minute slot up to 48 hours ahead has a current best estimate. As time advances, each slot's forecast is refreshed with newer data, so the uncertainty naturally decreases as the horizon shrinks.

This continuous update loop is why OpenSTEF's data structures carry ``available_at`` metadata. The library needs to know not just *what* was measured, but *when it became known*, so that each refresh of the forecast uses only the information that was genuinely available at that moment.

Short-Term vs. Long-Term: A Practical Summary
-----------------------------------------------

The distinction is worth restating concisely:

- **Short-term forecasting** (OpenSTEF's domain): sub-hourly to ~48 h, high update frequency, driven by recent measurements and numerical weather prediction, evaluated on point-in-time accuracy.
- **Long-term forecasting**: weeks to years, low update frequency, driven by structural trends, evaluated on aggregate accuracy.

The two regimes call for different models, different features, and different evaluation strategies. OpenSTEF makes no attempt to cover the long-term regime; its design choices — versioned datasets, multi-horizon lead times, probabilistic quantile outputs — are all optimised for the operational short-term use case.

Further Reading
----------------

- :doc:`quantiles_and_confidence` — How OpenSTEF expresses forecast uncertainty through quantiles and what confidence intervals mean in practice.
- :doc:`feature_engineering` — The predictors that matter most at each horizon: weather variables, calendar features, and lag transforms.
- :doc:`reliability_and_fallback` — What happens when a model cannot produce a forecast and how the library handles fallback strategies in production.