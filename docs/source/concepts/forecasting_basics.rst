Short-Term Energy Forecasting
==============================

Short-term energy forecasting is the practice of predicting power consumption or generation over a window of minutes to a few days ahead. This page explains what that means in practice, why the energy sector depends on it, and how the concepts of **horizon**, **lead time**, and **forecast frequency** shape the way OpenSTEF works as a library.

Why Short-Term Forecasting Matters
------------------------------------

Grid operators, balance-responsible parties, and energy traders all need to know what load or generation will look like in the near future—not to satisfy curiosity, but because every imbalance between supply and demand has a financial and physical cost. Scheduling generation assets, placing bids on intraday markets, and activating reserves all require forecasts that are accurate *and* available well before the delivery moment.

Long-term forecasts (months to years ahead) answer questions about capacity planning and investment. Short-term forecasts answer the operational question: *what will happen in the next few hours?* The two disciplines share some statistical foundations but differ fundamentally in the features that drive accuracy, the models that work best, and the cadence at which forecasts must be refreshed.

Short-Term vs. Long-Term Forecasting
--------------------------------------

The table below summarises the key differences that motivate a dedicated library like OpenSTEF:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Dimension
     - Short-term (OpenSTEF's domain)
     - Long-term
   * - Typical horizon
     - 15 minutes to 48 hours
     - Weeks, months, years
   * - Primary drivers
     - Weather, recent load patterns, time-of-day
     - Economic growth, demographics, policy
   * - Update cadence
     - Every 15 minutes to every few hours
     - Monthly or quarterly
   * - Model family
     - Gradient boosting, neural networks, statistical
     - Econometric, scenario-based
   * - Accuracy metric
     - RMSE / MAE on individual intervals
     - Annual energy totals, peak estimates

Because short-term forecasts are regenerated continuously and must be ready before market gate closures, the library is designed around the idea of a **pipeline** that can be triggered on a schedule and that always produces a forecast even when data quality is imperfect. See :doc:`reliability_and_fallback` for how OpenSTEF handles degraded conditions.

Core Concepts
--------------

Horizon
^^^^^^^^

The **horizon** is how far into the future a forecast reaches from the moment it is generated. OpenSTEF represents horizons as ``LeadTime`` objects, which wrap a ``timedelta``. A single forecasting run can produce predictions at multiple horizons simultaneously, so you can ask for 15-minute-ahead, 1-hour-ahead, and 24-hour-ahead values in one call.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.domain import LeadTime

    # Common horizons used in practice
    fifteen_min = LeadTime(timedelta(minutes=15))
    one_hour    = LeadTime(timedelta(hours=1))
    day_ahead   = LeadTime(timedelta(hours=24))
    two_days    = LeadTime(timedelta(hours=48))

Longer horizons are inherently less accurate because uncertainty accumulates over time. A well-calibrated model will express this through wider prediction intervals at longer horizons—see :doc:`quantiles_and_confidence` for how OpenSTEF represents uncertainty.

Lead Time
^^^^^^^^^^

**Lead time** is the gap between the moment a forecast *becomes available* and the target timestamp it is predicting. Lead time and horizon are closely related but not identical: a forecast generated at 06:00 for 18:00 the same day has a lead time of 12 hours. If that same forecast is regenerated at 12:00 for 18:00, the lead time has shrunk to 6 hours.

In OpenSTEF's data model, every prediction row carries both an ``available_at`` timestamp (when the forecast was made) and a ``horizon`` value (the lead time at generation time). This allows downstream consumers—and the evaluation pipeline—to filter forecasts by exactly how far in advance they were produced:

.. code-block:: python

    from openstef_models.domain import LeadTime, AvailableAt
    from datetime import timedelta

    # AvailableAt uses the DnTHHMM format:
    # D-1T0600 means "06:00 on the day before the target date"
    morning_run = AvailableAt.from_string("D-1T0600")

    # Filter a dataset to only the 36-hour-ahead predictions
    # made available at 06:00 the previous day
    subset = dataset.filter_by_available_at(morning_run)
    subset_36h = subset.filter_by_lead_time(LeadTime(timedelta(hours=36)))

Forecast Frequency
^^^^^^^^^^^^^^^^^^^

**Forecast frequency** (also called update cadence) is how often a new forecast is produced. In operational settings, forecasts are typically regenerated every 15 minutes to align with settlement periods, though some use cases only require hourly or twice-daily runs.

Higher frequency means fresher information feeds into each forecast—particularly important for intraday corrections as actual measurements arrive. The trade-off is computational cost and the complexity of managing many overlapping forecast versions.

.. note:: [DIAGRAM: Timeline showing forecast horizons and lead times. The horizontal axis represents wall-clock time. Three forecast runs are shown at T=00:00, T=06:00, and T=12:00. Each run emits prediction bands extending 15 min, 1 h, 24 h, and 48 h into the future. Arrows between the run time and each target timestamp are labelled with the corresponding lead time. A secondary axis shows update frequency markers at 15-minute intervals, illustrating how successive runs progressively shorten the lead time to any given target moment.]

Resolution and Sample Interval
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Distinct from the horizon is the **resolution** (or sample interval): the granularity of each individual prediction. A 48-hour forecast at 15-minute resolution produces 192 individual values. OpenSTEF's ``TimeSeriesDataset`` carries a ``sample_interval`` attribute that records this granularity and uses it when filtering and aligning data:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.data import TimeSeriesDataset

    # Inspect the resolution of a loaded dataset
    print(dataset.sample_interval)          # e.g. timedelta(minutes=15)

    # Select predictions for a specific horizon
    horizon_24h = LeadTime(timedelta(hours=24))
    day_ahead_predictions = dataset.select_horizon(horizon_24h)

How These Concepts Fit Together
---------------------------------

A typical operational workflow looks like this:

1. **Every 15 minutes**, new meter readings arrive and weather forecasts are updated.
2. The forecasting pipeline is triggered and generates predictions at multiple horizons (e.g., 15 min, 1 h, 24 h, 48 h ahead).
3. Each prediction row is stamped with ``available_at`` (now) and ``horizon`` (the lead time).
4. Downstream systems consume the horizon they need: a real-time balancing controller uses the 15-minute forecast; a day-ahead market bidder uses the 24–48-hour forecast.
5. After delivery, the evaluation pipeline compares predictions against actuals, grouped by ``available_at`` and ``lead_time``, to track how accuracy degrades with horizon.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.domain import LeadTime, AvailableAt
    from openstef_models.evaluation import EvaluationConfig

    # Configure evaluation across multiple lead times and availability windows
    eval_config = EvaluationConfig(
        available_ats=[
            AvailableAt.from_string("D-1T0600"),   # day-ahead morning run
            AvailableAt.from_string("D-1T1800"),   # day-ahead evening run
        ],
        lead_times=[
            LeadTime(timedelta(hours=12)),
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=36)),
            LeadTime(timedelta(hours=48)),
        ],
    )

This configuration tells the evaluation pipeline to separately score the morning and evening forecast runs, and to report accuracy at each of the four lead times. You can see how accuracy typically degrades as lead time grows—a pattern that motivates the probabilistic output described in :doc:`quantiles_and_confidence`.

Practical Implications for Model Choice
-----------------------------------------

The short-term regime has several properties that constrain which models work well:

- **Autocorrelation is strong at short lags.** What happened in the last 15 minutes is highly predictive of the next 15 minutes. Models that can exploit lag features—gradient boosted trees in particular—tend to outperform simpler approaches.
- **Weather drives the medium term.** Beyond a few hours, temperature, irradiance, and wind speed become the dominant signals. Incorporating numerical weather prediction (NWP) data is almost always worthwhile for horizons beyond 1 hour.
- **Periodicity matters.** Daily and weekly cycles are strong and consistent. Features encoding time-of-day and day-of-week give models a substantial head start.

:doc:`feature_engineering` covers how to construct these features within OpenSTEF's preprocessing pipeline, and :doc:`model_selection` compares the model families available in the library and when to prefer each one.

.. note::

   Short-term forecasting accuracy degrades non-linearly with horizon. The jump in uncertainty between a 1-hour and a 24-hour forecast is typically much larger than the jump between 24 hours and 48 hours, because the first few hours are dominated by autocorrelation while the day-ahead window is dominated by weather uncertainty—which is already substantial at 24 hours.

Summary
--------

Short-term energy forecasting operates over horizons from 15 minutes to 48 hours, with forecasts regenerated continuously to incorporate fresh observations. OpenSTEF models these concepts explicitly through ``LeadTime``, ``AvailableAt``, and ``sample_interval``, making it straightforward to build pipelines that serve multiple consumers—each with different lead-time requirements—from a single forecasting run. The library's evaluation tools track accuracy as a function of lead time, giving you a clear picture of where your models are reliable and where uncertainty grows.