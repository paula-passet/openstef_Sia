Short-Term Forecasting Basics
==============================

Short-term energy forecasting is the practice of predicting electrical load, generation, or grid quantities over a window ranging from minutes to a few days ahead. This page explains what that means in concrete terms: the time horizons involved, how lead time and update frequency interact, and why this problem is fundamentally different from longer-range energy planning.

If you are looking for how OpenSTEF selects and trains models, see :doc:`model_selection`. For the features that drive forecast accuracy, see :doc:`feature_engineering`.

.. contents:: On this page
   :local:
   :depth: 2


What Is Short-Term Forecasting?
--------------------------------

A *forecast* is a prediction of a future value made at a specific point in time. In energy systems, the quantity being predicted is typically electrical load (consumption) or renewable generation at a substation, feeder, or asset level. "Short-term" means the forecast horizon — the furthest point into the future being predicted — spans **minutes to roughly seven days**.

Beyond seven days, two things break down simultaneously: weather forecast resolution drops below the 15-minute granularity that grid operators need, and the inherent variability of solar and wind generation makes probabilistic bounds too wide to be operationally useful. OpenSTEF is designed squarely within this short-term window.

.. note::

   Short-term forecasting is not the same as *scheduling* or *planning*. A forecast tells you what is likely to happen; it does not decide what action to take. Grid operators, trading desks, and congestion management systems consume forecasts as inputs to their own decision processes.


Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three related but distinct concepts govern how a forecast is defined:

- **Horizon** — how far ahead the forecast extends (e.g., 48 hours).
- **Lead time** — the time between *now* (when the forecast is produced) and a specific predicted timestamp. A forecast produced at 08:00 for 14:00 has a lead time of 6 hours.
- **Update frequency** — how often a new forecast is produced. A system that re-runs every 15 minutes always has a fresh forecast, but the horizon of each run may still be 24 or 48 hours.

These three dimensions are independent. A system can have a 48-hour horizon, update every 15 minutes, and produce predictions at 15-minute resolution throughout that window. Equally, a day-ahead market application might update once per day with a 24-hour horizon at hourly resolution.

.. note:: [DIAGRAM: Timeline showing forecast horizons. A horizontal time axis runs left to right. "Now" is marked at the origin. Four forecast runs are shown as colored bands extending rightward: (1) 15-minute horizon — a narrow band updated every 15 min, used for real-time balancing; (2) 1-hour horizon — updated every 15 min, used for intra-day dispatch; (3) 24-hour horizon — updated every hour, used for day-ahead scheduling; (4) 48-hour horizon — updated every hour, used for congestion management and trading. Each band is annotated with its typical lead time range and update cadence. Arrows beneath the axis indicate that accuracy degrades as lead time increases.]

In OpenSTEF, the horizon is expressed as a ``timedelta`` and is part of the dataset structure. The ``VersionedTimeSeriesDataset`` tracks which forecast horizon each row belongs to, so a single dataset can hold predictions produced at many different lead times side by side — enabling backtesting and accuracy analysis across the full horizon range.


Why Short-Term Differs from Long-Term Forecasting
--------------------------------------------------

Long-term energy forecasting (months to years) is primarily a *trend and growth* problem. Analysts ask: how will total consumption change as the economy grows, buildings become more efficient, or electric vehicles proliferate? Statistical regression on annual totals, scenario analysis, and demographic models are the right tools.

Short-term forecasting is a *pattern and deviation* problem. The dominant signals are:

- **Diurnal cycles** — load rises in the morning, peaks in the evening, drops overnight, every day.
- **Weekly cycles** — weekday versus weekend profiles differ substantially.
- **Weather sensitivity** — temperature drives heating and cooling loads; irradiance drives solar generation; wind speed drives wind generation.
- **Calendar effects** — public holidays, school terms, and major events shift load profiles away from the typical weekly pattern.

These signals repeat with high regularity, which is why machine learning models trained on historical patterns can achieve low forecast error. But they also interact: a cold Monday public holiday has a profile unlike any weekday or weekend, and the model must have seen enough similar examples to generalise.

The practical consequence is that short-term forecasting requires **high-frequency, high-quality historical data** — typically at 15-minute resolution going back at least one year to capture all seasonal combinations. Long-term forecasting can work with monthly or annual aggregates.


Forecast Resolution and the 15-Minute Standard
------------------------------------------------

Grid operations in most European markets settle on 15-minute imbalance periods, making 15-minute forecast resolution the de facto standard for short-term work. OpenSTEF is built around this cadence: the ``sample_interval`` parameter on ``TimeSeriesDataset`` enforces a consistent sampling frequency, and the library raises a ``ValueError`` if the data frequency does not match the declared interval.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef.data_classes.time_series_dataset import TimeSeriesDataset

   # Build a simple 15-minute time series
   index = pd.date_range("2024-01-15 00:00", periods=96, freq="15min")
   data = pd.DataFrame(
       {
           "load": [150.0 + 30.0 * (i % 24) / 24 for i in range(96)],
           "temperature": [5.0 + 2.0 * (i % 48) / 48 for i in range(96)],
       },
       index=index,
   )

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))
   print(f"Sample interval: {dataset.sample_interval}")
   print(f"Feature columns: {dataset.feature_names}")

Nothing prevents using hourly resolution — simply set ``sample_interval=timedelta(hours=1)`` — but accuracy at the 15-minute level will be lost. For applications that only need hourly dispatch decisions, hourly resolution is perfectly adequate and reduces data volume by a factor of four.


Versioned Forecasts and Backtesting
-------------------------------------

A key concept in operational forecasting is that the *same future timestamp* will be predicted many times, once per forecast run. At 06:00 you predict 18:00 with a 12-hour lead time; at 12:00 you predict 18:00 again with a 6-hour lead time; at 17:45 you predict 18:00 with a 15-minute lead time. All three are valid forecasts for the same timestamp, but they carry different uncertainty and are used for different decisions.

OpenSTEF's ``VersionedTimeSeriesDataset`` captures this structure explicitly. When a ``horizon`` column is present, each row is tagged with the lead time at which it was produced. This makes it straightforward to evaluate how forecast error varies with lead time — a critical diagnostic for understanding where a model needs improvement.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef.data_classes.time_series_dataset import VersionedTimeSeriesDataset

   # Simulate forecasts produced at two different lead times for the same window
   future_index = pd.date_range("2024-01-16 00:00", periods=4, freq="15min")

   # Forecast produced 24 hours ahead
   df_24h = pd.DataFrame(
       {"load": [148.0, 152.0, 155.0, 153.0], "horizon": [timedelta(hours=24)] * 4},
       index=future_index,
   )

   # Forecast produced 1 hour ahead (typically more accurate)
   df_1h = pd.DataFrame(
       {"load": [150.5, 151.0, 154.5, 152.5], "horizon": [timedelta(hours=1)] * 4},
       index=future_index,
   )

   versioned_data = pd.concat([df_24h, df_1h]).sort_index()
   dataset = VersionedTimeSeriesDataset(
       versioned_data,
       sample_interval=timedelta(minutes=15),
       horizon_column="horizon",
   )
   print(f"Is versioned: {dataset.is_versioned}")

This versioned structure is the foundation for backtesting: by replaying historical forecast runs and comparing predictions to actuals, you can measure accuracy at each lead time without ever contaminating the model with future information. See :doc:`reliability_and_fallback` for how OpenSTEF handles the cases where a forecast run fails entirely.


Accuracy Degrades with Lead Time — and That Is Normal
-------------------------------------------------------

A well-functioning short-term forecasting system will always show higher error at longer lead times. This is not a defect; it reflects genuine uncertainty about the future. Weather forecasts become less precise, load patterns become less predictable, and unexpected events accumulate.

What matters operationally is that the error at each lead time is *calibrated* — that is, the stated confidence intervals actually contain the true value at the declared frequency. OpenSTEF produces probabilistic forecasts (quantile predictions) rather than single point estimates, so consumers can make risk-aware decisions at every lead time. The mechanics of quantile forecasts are covered in :doc:`quantiles_and_confidence`.

A practical rule of thumb for load forecasting at substation level:

- **15-minute lead time**: Mean Absolute Percentage Error (MAPE) of 1–3 % is achievable.
- **1-hour lead time**: MAPE of 2–5 % is typical.
- **24-hour lead time**: MAPE of 3–8 % depending on weather sensitivity.
- **48-hour lead time**: MAPE of 5–12 %, dominated by weather forecast uncertainty.

These ranges vary significantly with the load type (residential versus industrial), the presence of behind-the-meter solar, and data quality. The Alliander 2021 benchmark, runnable via ``openstef-beam``, provides a concrete reference point for your own data.


Summary
--------

Short-term energy forecasting operates over horizons of minutes to seven days, at resolutions as fine as 15 minutes, and is updated continuously as new observations arrive. Its accuracy is governed by repeating temporal patterns, weather, and calendar effects — not by long-run trends. OpenSTEF is a library that provides the building blocks — data structures, feature pipelines, model wrappers, and workflow orchestration — to construct and operate short-term forecasting systems at production scale.

The next logical step is understanding what features drive forecast accuracy. Continue to :doc:`feature_engineering` for a detailed treatment of weather variables, lag features, and calendar encodings. If you are ready to compare model types, see :doc:`model_selection`.