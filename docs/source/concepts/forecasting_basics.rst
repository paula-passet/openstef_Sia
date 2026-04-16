Short-Term Energy Forecasting Basics
=====================================

Short-term energy forecasting is the practice of predicting electricity load, generation,
or related quantities over a window of minutes to a few days ahead. This page explains
what short-term forecasting means in practice, why it matters for grid operations, and
how the key concepts of **horizon**, **lead time**, and **forecast frequency** shape the
way OpenSTEF models are configured and evaluated.

For probabilistic aspects of forecasts (quantiles, confidence intervals) see
:doc:`quantiles_and_confidence`. For the predictors that drive forecast accuracy see
:doc:`feature_engineering`. For what happens when a model fails in production see
:doc:`reliability_and_fallback`.

.. contents:: On this page
   :local:
   :depth: 2


Why Short-Term Forecasting?
----------------------------

Grid operators, balance responsible parties, and energy traders all need to act on
information about the near future. Scheduling reserves, submitting day-ahead bids,
dispatching flexible assets, and managing congestion all require a reliable picture of
what demand and generation will look like over the next few hours or days.

Long-term forecasting — months to years ahead — answers questions about infrastructure
investment and capacity planning. Short-term forecasting answers operational questions:
*How much power will this substation draw in the next 15 minutes? What will the solar
output be at noon tomorrow?* The two disciplines differ not just in horizon length but
in the signals they rely on. Long-term forecasts lean on demographic and economic
trends; short-term forecasts are dominated by weather, time-of-day patterns, and recent
load behaviour.

OpenSTEF is designed specifically for the short-term operational case. Its data
structures, feature engineering pipeline, and evaluation tooling all assume that
forecasts are produced repeatedly — often every 15 minutes — and that each forecast
covers a window of up to 48 hours ahead.


Horizons, Lead Times, and Availability
----------------------------------------

Three related but distinct concepts govern how a short-term forecast is structured:

**Forecast horizon**
   The target timestamp being predicted, expressed as a duration from the moment the
   forecast is made. A horizon of ``timedelta(hours=24)`` means "predict the value
   24 hours from now." OpenSTEF represents horizons with the ``LeadTime`` type, which
   wraps a ``timedelta``.

**Lead time**
   The gap between when input data *became available* and the timestamp being predicted.
   Lead time is what actually constrains which features a model can use. If a weather
   forecast is only published six hours before the target time, the effective lead time
   for that feature is six hours, regardless of how far ahead you are trying to predict.

**Data availability (``available_at``)**
   The wall-clock time at which a particular observation or forecast was published.
   OpenSTEF's ``VersionedTimeSeriesDataset`` tracks ``available_at`` for every row,
   making it possible to reconstruct exactly what information was on hand at any past
   moment. This is essential for honest backtesting — without it, a model trained on
   "future" data will appear far more accurate than it really is.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd


Typical Horizon Ranges
-----------------------

Short-term energy forecasting in OpenSTEF covers four broad operating ranges, each
with different use cases and modelling considerations:

- **Intra-hour (≤ 15 min ahead)** — Used for real-time balancing and automatic
  frequency restoration. At this range the most recent metered values are the
  dominant signal; weather barely changes between now and the target time.

- **Intra-day (15 min – 6 h ahead)** — Covers manual reserve activation, congestion
  management, and intraday trading. Weather forecasts start to matter, and recent
  trend information remains highly informative.

- **Day-ahead (6 – 36 h ahead)** — The primary horizon for day-ahead market bidding
  and unit commitment. NWP (Numerical Weather Prediction) forecasts are the main
  exogenous driver. Calendar features (hour of day, day of week, public holidays)
  become critical.

- **Extended short-term (36 – 48 h ahead)** — Bridges into medium-term territory.
  Useful for maintenance scheduling and two-day-ahead market products. Forecast
  uncertainty grows substantially; probabilistic outputs (see
  :doc:`quantiles_and_confidence`) are especially valuable here.

A single OpenSTEF ``ForecastingModel`` can be configured to produce predictions at
multiple horizons simultaneously, each potentially using a different feature set
reflecting what data is realistically available at that lead time.


How Forecast Frequency Works
------------------------------

In operational settings a forecast is not produced once and discarded — it is
re-issued continuously as new information arrives. A typical deployment issues a
fresh set of predictions every 15 minutes, rolling the horizon window forward each
time.

This rolling update pattern has two important consequences for model design:

1. **Features must respect the availability window.** A feature that is only available
   with a 30-minute delay cannot be used for a 15-minute-ahead prediction. OpenSTEF
   enforces this through ``filter_by_available_before`` and ``filter_by_lead_time``
   on the dataset, ensuring that training data mirrors the constraints that will apply
   at inference time.

2. **Models are evaluated on a rolling basis.** Backtesting should simulate the same
   rolling update cycle used in production. The ``select_version()`` method on
   ``VersionedTimeSeriesDataset`` creates a point-in-time snapshot for each evaluation
   step, preventing any look-ahead bias.


Configuring Horizons in OpenSTEF
----------------------------------

The following example shows how to configure a ``ForecastingModel`` with multiple
horizons and inspect the resulting dataset structure. It uses
``create_synthetic_forecasting_dataset`` from ``openstef_core.testing`` to generate
realistic sample data without needing a live data source.

.. code-block:: python

   from datetime import timedelta

   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime

   # Define the horizons you want the model to cover.
   # Each LeadTime wraps a timedelta and represents one forecast horizon.
   horizons = [
       LeadTime(timedelta(minutes=15)),
       LeadTime(timedelta(hours=1)),
       LeadTime(timedelta(hours=24)),
       LeadTime(timedelta(hours=48)),
   ]

   # Create a synthetic versioned dataset sampled at 15-minute intervals.
   dataset = create_synthetic_forecasting_dataset(
       sample_interval=timedelta(minutes=15),
       n_horizons=len(horizons),
   )

   # Inspect which horizons are present in the dataset.
   print(dataset.horizons())
   # [LeadTime(0:15:00), LeadTime(1:00:00), LeadTime(1 day, 0:00:00), LeadTime(2 days, 0:00:00)]

   # Filter to a single horizon for analysis or single-horizon model training.
   dataset_24h = dataset.filter_by_lead_time(LeadTime(timedelta(hours=24)))
   print(dataset_24h.lead_time_series().unique())
   # [Timedelta('1 days 00:00:00')]

The ``filter_by_available_before`` method is equally important when simulating what a
model would have seen at a specific wall-clock time:

.. code-block:: python

   from datetime import datetime, timezone

   # Simulate the data that would have been available at a specific moment —
   # for example, when running a backtest for the 06:00 UTC forecast cycle.
   cutoff = datetime(2024, 6, 1, 6, 0, tzinfo=timezone.utc)
   snapshot = dataset.filter_by_available_before(available_before=cutoff)

   # Only rows with available_at < cutoff are retained — no look-ahead.
   print(snapshot.available_at_series().max())
   # 2024-06-01 05:45:00+00:00


Short-Term vs. Long-Term: A Practical Comparison
--------------------------------------------------

+---------------------------+-----------------------------+-----------------------------+
| Aspect                    | Short-term (OpenSTEF scope) | Long-term                   |
+===========================+=============================+=============================+
| Horizon                   | 15 min – 48 h               | Weeks to years              |
+---------------------------+-----------------------------+-----------------------------+
| Primary drivers           | Weather, recent load, time  | Demographics, economics,    |
|                           | patterns, holidays          | installed capacity          |
+---------------------------+-----------------------------+-----------------------------+
| Update frequency          | Every 15 min – 1 h          | Daily to monthly            |
+---------------------------+-----------------------------+-----------------------------+
| Key accuracy metric       | MAE / RMSE per horizon      | MAPE over seasonal cycles   |
+---------------------------+-----------------------------+-----------------------------+
| Lookahead risk            | High — strict data          | Lower — slower-moving       |
|                           | versioning required         | signals                     |
+---------------------------+-----------------------------+-----------------------------+
| Probabilistic output      | Essential for balancing     | Useful for scenario         |
|                           | and trading                 | planning                    |
+---------------------------+-----------------------------+-----------------------------+

The strict data-versioning discipline enforced by OpenSTEF's ``VersionedTimeSeriesDataset``
is a direct response to the high lookahead risk in short-term forecasting. Small
amounts of future information leaking into training data can produce optimistic
evaluation metrics that completely fail to materialise in production.

.. note::

   OpenSTEF is a **library**, not a scheduled application. It provides the building
   blocks — data structures, models, feature pipelines — that you assemble into a
   forecasting system. The update frequency and horizon configuration are choices you
   make when integrating OpenSTEF into your own workflow or pipeline orchestrator.


Summary
--------

Short-term energy forecasting operates over horizons from 15 minutes to 48 hours,
is re-issued on a rolling cycle (typically every 15 minutes), and is dominated by
weather and time-pattern signals rather than structural trends. The three concepts
that govern every OpenSTEF forecast are:

- **Horizon** — how far ahead you are predicting (expressed as a ``LeadTime``).
- **Lead time** — the realistic data availability gap that constrains your features.
- **Forecast frequency** — how often the full horizon window is re-issued.

Getting these three things right is the foundation of a reliable short-term forecasting
system. The next step is understanding which features carry the most predictive signal
at each horizon — covered in :doc:`feature_engineering` — and how to express forecast
uncertainty across the horizon window, covered in :doc:`quantiles_and_confidence`.