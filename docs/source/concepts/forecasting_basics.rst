Forecasting Basics
==================

Short-term energy forecasting sits at the operational heart of grid management, energy trading, and demand response. This page explains what short-term forecasting means in practice, why it differs fundamentally from long-term forecasting, and how the key concepts of **horizons**, **lead times**, and **forecast frequency** shape how OpenSTEF is used as a library.

.. note::

   This page covers the conceptual foundations. For probabilistic outputs (quantiles and confidence intervals), see :doc:`quantiles_and_confidence`. For choosing the right model for your horizon, see :doc:`model_selection`.


What Is Short-Term Energy Forecasting?
---------------------------------------

Short-term energy forecasting predicts power consumption or generation over a window ranging from minutes to a few days ahead. The defining characteristic is that the forecast must be **actionable in near real-time**: grid operators dispatch assets, traders submit bids, and balancing mechanisms respond — all within tight time constraints.

OpenSTEF is a Python library built specifically for this operational context. Rather than producing a single annual outlook, it continuously generates fresh forecasts as new observations arrive, feeding downstream systems that need up-to-date predictions to make decisions.

The distinction from long-term forecasting is not merely one of scale. Long-term forecasts (months to years) are primarily driven by structural trends — population growth, policy changes, technology adoption. Short-term forecasts are dominated by **cyclical and meteorological patterns**: the daily load curve, the week-day/weekend rhythm, cloud cover reducing solar output, or wind speed ramping up overnight. These patterns are highly predictable with the right features, but they change rapidly enough that a forecast made 48 hours ago may already be significantly stale.


Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three related but distinct concepts govern how a short-term forecast is defined:

**Horizon**
   How far into the future the forecast extends from the moment of prediction. A 24-hour horizon means the model produces predictions for every time step across the next 24 hours.

**Lead time**
   The gap between when a specific predicted timestamp is generated and when that timestamp actually occurs. Within a single forecast run, different predicted points have different lead times. A forecast generated at 06:00 for the period 06:00–30:00 has lead times ranging from near-zero (the 06:05 slot) up to 24 hours (the 06:00 slot the following day).

**Update frequency**
   How often a new forecast run is triggered. A system might regenerate forecasts every 15 minutes, every hour, or once per day, depending on operational requirements and data availability.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

In OpenSTEF, horizons are expressed as ``LeadTime`` objects backed by ``timedelta`` values. A forecaster configuration declares which horizons it should produce, and the library handles the mechanics of slicing, versioning, and filtering data accordingly:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster, LGBMForecasterConfig
   from openstef_models.data_classes.lead_time import LeadTime
   from openstef_models.data_classes.quantile import Quantile

   # Configure a forecaster that predicts at two distinct horizons:
   # 1 hour ahead (intraday) and 24 hours ahead (day-ahead)
   config = LGBMForecasterConfig(
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=24)),
       ],
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
   )

   forecaster = LGBMForecaster(config=config)

The ``max_horizon`` property gives you the furthest lead time in the configuration, which the library uses internally to determine how much historical context is needed for feature construction.


Why Horizon Choice Matters
---------------------------

The horizon is not a free parameter — it is tightly coupled to the **data availability** at prediction time and to the **accuracy you can realistically expect**.

At a 15-minute horizon, very recent meter readings and SCADA data are typically available, making the forecast largely a smoothing and correction problem. Accuracy is high, and even simple models perform well.

At a 24–48 hour horizon, the dominant uncertainty shifts to **weather**: solar irradiance, wind speed, and temperature forecasts from numerical weather prediction (NWP) models become the primary inputs. The model must learn how load or generation responds to those meteorological drivers. Accuracy degrades with lead time, but the forecast is still far more useful than a naive persistence baseline.

This is why OpenSTEF supports **multiple simultaneous horizons** within a single forecaster configuration. Different downstream consumers (e.g., a real-time balancing controller versus a day-ahead market bidding system) can each consume the horizon most appropriate to their decision window, all produced by the same trained model.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.data_classes.lead_time import LeadTime

   # Retrieve predictions for a specific horizon from a multi-horizon dataset
   predictions = forecaster.predict(data)

   if predictions is not None:
       # Filter to only the 24-hour-ahead predictions
       day_ahead = predictions.filter_by_lead_time(
           lead_time=LeadTime(timedelta(hours=24))
       )
       df = day_ahead.to_pandas()
       print(df.head())


Forecast Frequency and Data Versioning
----------------------------------------

How often you regenerate a forecast depends on how quickly the operational situation changes and how frequently fresh input data arrives. OpenSTEF models this through the concept of ``AvailableAt`` — the point in time at which a forecast *becomes available* to downstream consumers.

A typical day-ahead electricity market workflow might look like this:

- **06:00 daily**: NWP weather data for the next 48 hours is ingested.
- **06:15 daily**: A new forecast run is triggered, producing predictions for every 15-minute interval across the next 48 hours.
- **Consumers**: The market bidding system reads the 24–48 h horizon; the intraday desk reads the 1–6 h horizon from the same run.

In contrast, a real-time balancing application might trigger a new forecast every 15 minutes, consuming only the shortest-horizon predictions from each run and discarding the rest.

OpenSTEF's ``EvaluationConfig`` captures this explicitly:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.pipelines.evaluation_pipeline import EvaluationConfig
   from openstef_models.data_classes.available_at import AvailableAt
   from openstef_models.data_classes.lead_time import LeadTime
   from openstef_models.data_classes.window import Window

   config = EvaluationConfig(
       # Forecasts are generated once per day at 06:00
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       # Evaluate at both intraday and day-ahead lead times
       lead_times=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT36H"),
       ],
       # Evaluate over a rolling 21-day window
       windows=[Window(lag=timedelta(hours=0), size=timedelta(days=21))],
   )

Separating *when a forecast is generated* from *which lead time it targets* is a deliberate design choice. It allows the library to correctly reconstruct what information was available at each prediction moment during backtesting, preventing data leakage from future observations into historical evaluation.


Short-Term vs. Long-Term: A Practical Comparison
--------------------------------------------------

The table below summarises the practical differences that shape how you use OpenSTEF:

.. list-table::
   :header-rows: 1
   :widths: 25 37 38

   * - Dimension
     - Short-term (OpenSTEF's domain)
     - Long-term
   * - Horizon
     - Minutes to ~48 hours
     - Weeks to years
   * - Primary drivers
     - Weather, time-of-day, day-of-week patterns
     - Structural trends, policy, demographics
   * - Update cadence
     - Minutes to hours
     - Monthly or annually
   * - Key input data
     - NWP forecasts, recent observations, calendar features
     - Economic indicators, installed capacity projections
   * - Accuracy metric
     - MAE, RMSE, pinball loss per horizon
     - Annual energy totals, peak demand estimates
   * - Operational use
     - Dispatch, intraday trading, balancing
     - Infrastructure planning, long-term contracts

OpenSTEF does not attempt to address long-term forecasting. Its feature engineering, model architectures, and evaluation pipelines are all designed around the short-term regime where recency, weather responsiveness, and continuous retraining matter most. See :doc:`feature_engineering` for detail on the predictors that make short-term models work.


Key Takeaways
--------------

- Short-term forecasting is defined by **operational immediacy**: forecasts must be fresh, frequent, and tied to specific lead times that match downstream decision windows.
- **Horizon**, **lead time**, and **update frequency** are distinct concepts; OpenSTEF models all three explicitly through ``LeadTime``, ``AvailableAt``, and dataset versioning.
- Accuracy degrades with lead time, and the dominant uncertainty source shifts from recent observations (short horizons) to weather (longer horizons).
- OpenSTEF supports **multiple simultaneous horizons** from a single model, allowing different consumers to read the lead time relevant to their use case.
- Correct handling of data availability timestamps is essential for honest backtesting — the library enforces this through its versioned dataset abstractions.

For the next step, :doc:`quantiles_and_confidence` explains how OpenSTEF expresses forecast uncertainty across all horizons, and :doc:`reliability_and_fallback` covers what happens when a model cannot produce a prediction in time.