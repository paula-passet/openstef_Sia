Forecasting Basics
==================

Short-term energy forecasting sits at the heart of what OpenSTEF is built for. This page explains what short-term forecasting means in the energy domain, why it matters, and how the key concepts of horizons, lead times, and update frequency shape the way you use the library.

What Is Short-Term Energy Forecasting?
---------------------------------------

Short-term energy forecasting is the practice of predicting electricity load, generation, or grid state over a period ranging from a few minutes to roughly seven days into the future. It is distinct from medium- and long-term forecasting, which concerns itself with seasonal planning, capacity investment, and multi-year demand growth.

OpenSTEF is a Python library specifically designed for this short-term regime. Its models, feature engineering pipelines, and evaluation tools are all calibrated to the statistical properties of energy time series at sub-hourly to multi-day resolutions—where weather, human behaviour, and calendar effects dominate the signal.

Why Short-Term Forecasting Matters
------------------------------------

Grid operators, energy traders, and distribution system operators all need accurate near-future load and generation estimates to make decisions that cannot wait for long-range analysis:

- **Congestion management** — identifying whether a grid section will be overloaded in the next few hours so that remedial actions can be scheduled in time.
- **Balancing and dispatch** — scheduling flexible assets (batteries, demand response) to keep supply and demand in balance across the next 24–48 hours.
- **Renewable integration** — anticipating solar and wind output over the next day so that conventional generation can be ramped up or down efficiently.
- **Intraday trading** — updating position estimates as new weather data arrives throughout the day.

In each case the value of a forecast degrades rapidly as the horizon extends, and the required resolution is typically 15 minutes to one hour. Long-term forecasting tools are simply not designed for this operating environment.

.. note::

   Short-term forecasting quality degrades significantly beyond roughly seven days. Weather forecast products with 15-minute resolution are not reliably available beyond that window, and the statistical patterns that drive solar and wind peaks become unpredictable. OpenSTEF is designed for this sub-seven-day regime.

Horizons, Lead Times, and Update Frequency
--------------------------------------------

Three concepts govern how a short-term forecast is specified and consumed. Understanding their relationship is essential before configuring any pipeline in OpenSTEF.

**Forecast horizon** is the distance in time between *now* and the furthest point being predicted. A 48-hour horizon means the forecast covers the period from the current moment up to 48 hours ahead.

**Lead time** is the time between when a specific prediction was *generated* and the timestamp it refers to. If a forecast is produced at 06:00 and covers 18:00 the same day, the lead time for that 18:00 value is 12 hours. A single forecast run produces a sequence of values, each with a different lead time.

**Update frequency** (sometimes called the *available_at* cadence) is how often the forecast is refreshed with new information. An intraday forecast might be updated every 15 minutes as new SCADA measurements and weather model runs arrive. A day-ahead forecast is typically produced once per day, often the evening before.

These three dimensions interact: a high update frequency with a short horizon is appropriate for real-time balancing, while a once-daily update with a 48-hour horizon suits day-ahead scheduling.

.. mermaid:: diagrams/concepts/forecasting_basics_diagram_1.mmd

The Four Practical Horizons
-----------------------------

Energy system operations typically organise around four operational horizons, each with different accuracy expectations and data requirements.

**15-minute (near-real-time)**
  Used for automatic frequency restoration and very short-term balancing. The model has access to the most recent measurements and can exploit strong autocorrelation in the load signal. Accuracy is highest here. Features are dominated by recent history and current weather observations rather than forecasts.

**1-hour (intraday)**
  Covers the next one to a few hours. Still benefits from recent measurements but begins to rely more heavily on numerical weather prediction (NWP) data. Used for intraday redispatch and short-horizon trading.

**24-hour (day-ahead)**
  The workhorse horizon for most grid operators. Produced the day before, typically using a morning NWP run, it covers the full operating day. Calendar features (hour of day, day of week, public holidays) become important at this range because the autocorrelation signal from recent measurements has largely decayed.

**48-hour (two-day-ahead)**
  Extends the day-ahead forecast by one additional day. Accuracy is lower, particularly for solar and wind, but the forecast is valuable for maintenance scheduling and capacity reservation. NWP uncertainty is the dominant error source at this range.

How OpenSTEF Represents These Concepts
----------------------------------------

OpenSTEF encodes horizons and lead times as first-class objects throughout the library. The ``LeadTime`` type and the ``available_at`` metadata on forecast datasets make it straightforward to filter, compare, and evaluate predictions at specific points in the forecast timeline.

A ``BacktestForecasterConfig`` captures the key temporal parameters for a forecasting pipeline:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.models.forecasting.backtest_forecaster import BacktestForecasterConfig

   config = BacktestForecasterConfig(
       # How far ahead the model predicts
       predict_length=timedelta(hours=48),
       # Minimum acceptable prediction window
       predict_min_length=timedelta(hours=24),
       # How much recent history the model sees at prediction time
       predict_context_length=timedelta(days=7),
       # Minimum fraction of context that must be present
       predict_context_min_coverage=0.8,
       # How much history is used for training
       training_context_length=timedelta(days=365),
       training_context_min_coverage=0.9,
       # Native resolution of the time series
       predict_sample_interval=timedelta(minutes=15),
   )

The ``predict_sample_interval`` parameter sets the native resolution—15 minutes is the default and the most common choice in European grid operations. The ``predict_length`` directly encodes the forecast horizon, and ``predict_context_length`` controls how much recent data the model can use as features at inference time.

When evaluating forecasts, OpenSTEF tracks the ``available_at`` timestamp (when the forecast was generated) and the ``lead_time`` (how far ahead each value reaches). This allows you to slice evaluation metrics by lead time and understand how accuracy degrades as the horizon extends:

.. code-block:: python

   from openstef_models.evaluation.config import EvaluationConfig, AvailableAt, LeadTime
   from datetime import timedelta

   eval_config = EvaluationConfig(
       # Forecast was produced at 06:00 the day before (D-1T06:00)
       available_ats=[AvailableAt.from_string("D-1T06:00")],
       # Evaluate accuracy at 12h, 24h, and 48h lead times
       lead_times=[
           LeadTime.from_string("PT12H"),
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
   )

This separation between *when a forecast was made* and *what it predicted* is what allows OpenSTEF to produce lead-time-stratified accuracy reports—an essential diagnostic for understanding where a model's skill degrades.

Short-Term vs. Long-Term Forecasting
--------------------------------------

It is worth being explicit about what makes short-term forecasting a distinct problem, not just a scaled-down version of long-term forecasting.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Dimension
     - Short-term (OpenSTEF's domain)
     - Long-term
   * - Horizon
     - Minutes to ~7 days
     - Months to years
   * - Dominant signal drivers
     - Weather, recent load history, time-of-day
     - Economic growth, demographic change, policy
   * - Update frequency
     - Every 15 min to once daily
     - Monthly or annually
   * - Primary data source
     - SCADA measurements, NWP weather forecasts
     - Macroeconomic indicators, population data
   * - Model type
     - Gradient boosting, neural networks on time series
     - Regression on aggregated statistics
   * - Accuracy metric
     - RMSE, MAE at 15-min resolution
     - Annual energy volume error

Long-term forecasting tools are not appropriate substitutes for short-term ones—they lack the temporal resolution, the feature pipelines for NWP data, and the update mechanisms that short-term operations require.

What Comes Next
----------------

This page has covered the conceptual foundations. The sibling pages in this section go deeper on the practical aspects of building a forecasting pipeline with OpenSTEF:

- :doc:`feature_engineering` — which predictors matter most at each horizon, and how OpenSTEF constructs features from weather data, calendar information, and load history.
- :doc:`quantiles_and_confidence` — how OpenSTEF produces probabilistic forecasts rather than single point estimates, and what quantile outputs mean for operational decision-making.
- :doc:`model_selection` — how to choose between the available model types depending on your horizon, data availability, and accuracy requirements.
- :doc:`reliability_and_fallback` — how to keep forecasts flowing in production when models fail or input data is missing.