Forecasting Basics
==================

Short-term energy forecasting sits at the operational heart of grid management. This page explains what short-term forecasting means in the context of OpenSTEF, why it differs fundamentally from long-term planning forecasts, and how the key concepts of horizons, lead times, and forecast frequency shape the way you use the library.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

What Short-Term Forecasting Means
----------------------------------

Short-term energy forecasting is the practice of predicting electricity load, generation, or net exchange over a window of minutes to a few days. The defining characteristic is that the forecast must be *actionable* — it feeds directly into decisions such as dispatch scheduling, congestion management, and balancing market bids, all of which have hard deadlines measured in minutes or hours.

OpenSTEF is a library purpose-built for this operational regime. It does not try to answer questions like "how much capacity will we need in 2035?" That is the domain of long-term planning models, which operate on annual or decadal horizons, rely on scenario assumptions, and are run infrequently. Short-term forecasting, by contrast, runs continuously, ingests live data streams, and must produce fresh predictions on a schedule that matches the market or grid operator's needs.

The practical consequence is that every design decision in OpenSTEF — how models are structured, how data is versioned, how uncertainty is expressed — is shaped by the demands of operational forecasting.

Horizons and Lead Times
-----------------------

Two terms appear throughout the OpenSTEF API and are worth distinguishing carefully.

A **horizon** (also called a *lead time*) is the distance in time between the moment a forecast is generated and the moment being predicted. A horizon of ``PT36H`` means the model is predicting what will happen 36 hours from now. In OpenSTEF, horizons are represented by the ``LeadTime`` type, which wraps a ``timedelta``:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime

   # A single 36-hour horizon
   horizon_36h = LeadTime(timedelta(hours=36))

   # Parsed from an ISO 8601 duration string
   horizon_36h = LeadTime.from_string("PT36H")

   # Common operational horizons
   intraday   = LeadTime(timedelta(minutes=15))
   one_hour   = LeadTime(timedelta(hours=1))
   day_ahead  = LeadTime(timedelta(hours=24))
   two_day    = LeadTime(timedelta(hours=48))

A model can be configured with multiple horizons simultaneously. OpenSTEF distinguishes between two forecaster architectures for this:

- **Multi-horizon forecasters** (e.g. tree-based models like XGBoost and LightGBM) train a single model that handles all configured horizons internally. They can exploit relationships between horizons and tolerate missing or conditional features.
- **Single-horizon forecasters** (e.g. linear models) train one model per horizon. They are simpler but cannot share information across prediction distances.

The ``horizons`` field on any forecaster configuration controls which lead times the model will produce predictions for:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="load_forecast_v1",
           model="gblinear",
           # Predict at three distinct horizons
           horizons=[
               LeadTime(timedelta(hours=1)),
               LeadTime(timedelta(hours=24)),
               LeadTime(timedelta(hours=48)),
           ],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           target_column="load",
       )
   )

The ``max_horizon`` property on a configured forecaster returns the furthest lead time, which the library uses internally to determine how much historical context is needed for feature construction.

How Forecast Frequency Works
-----------------------------

Forecast frequency — how often a new forecast is generated — is independent of the horizon. A 48-hour forecast can be refreshed every 15 minutes as new measurements arrive, or it can be refreshed once per day. The right choice depends on how quickly conditions change and how often downstream systems can consume updated predictions.

In OpenSTEF's backtesting framework, ``predict_interval`` controls how frequently predictions are generated during a simulation:

.. code-block:: python

   from datetime import timedelta, time
   from openstef_beam.backtesting.pipeline import BacktestPipeline, BacktestPipelineConfig

   config = BacktestPipelineConfig(
       # Resolution of individual prediction samples
       prediction_sample_interval=timedelta(minutes=15),

       # How often a fresh forecast is generated
       predict_interval=timedelta(hours=6),

       # How often the model is retrained on new data
       train_interval=timedelta(days=7),

       # Align forecast generation to a fixed clock time
       align_time=time.fromisoformat("00:00+00"),
   )

This separation between ``prediction_sample_interval``, ``predict_interval``, and ``train_interval`` reflects a real operational pattern:

- **Sample interval** (e.g. 15 minutes): the temporal resolution of each individual forecast output — how finely the predicted time series is discretised.
- **Predict interval** (e.g. 6 hours): how often the model is invoked to produce a fresh forecast. More frequent updates capture rapidly changing conditions but increase computational load.
- **Train interval** (e.g. 7 days): how often the model is retrained on accumulated data. Retraining is expensive and typically happens on a slower cadence than prediction.

Data Availability and Versioning
---------------------------------

A subtlety that catches many practitioners is the difference between *when a measurement describes* and *when that measurement is actually available*. Meter readings, weather observations, and SCADA data all arrive with some delay. A forecast generated at 14:00 cannot use a meter reading timestamped 13:55 if that reading only arrives at 14:10.

OpenSTEF models this explicitly through the ``available_at`` concept on datasets. Every data point carries not just its timestamp but also the time at which it became available for use. The ``filter_by_available_before`` method on ``ForecastDataset`` enforces this boundary, ensuring that backtests and live forecasts use exactly the same data that would have been available in production:

.. code-block:: python

   from datetime import datetime, timezone
   from openstef_core.datasets import ForecastDataset

   # Simulate what data was available at 14:00 UTC
   cutoff = datetime(2024, 6, 1, 14, 0, tzinfo=timezone.utc)
   available_data = dataset.filter_by_available_before(cutoff)

Ignoring data availability is one of the most common sources of optimistic bias in backtests. OpenSTEF's explicit versioning makes it straightforward to avoid this mistake.

Why Short-Term Differs from Long-Term Forecasting
--------------------------------------------------

The differences between short-term and long-term forecasting are not merely a matter of scale. They reflect fundamentally different problem structures:

**Signal sources.** Short-term forecasts rely heavily on recent measurements — the last few hours of load, current weather observations, and calendar effects like time of day and day of week. Long-term forecasts rely on structural drivers: population growth, electrification rates, and policy scenarios. OpenSTEF's feature engineering is designed around the former; see :doc:`feature_engineering` for details on the predictors the library supports.

**Uncertainty character.** Over a 15-minute horizon, uncertainty is dominated by measurement noise and small behavioural fluctuations. Over 48 hours, weather forecast uncertainty becomes the primary driver. OpenSTEF expresses this through quantile predictions that widen as the horizon grows. The probabilistic output is covered in depth in :doc:`quantiles_and_confidence`.

**Model refresh rate.** Long-term planning models may be updated annually. Short-term operational models must track seasonal shifts, load growth, and changes in the generation mix on a rolling basis. OpenSTEF's ``train_interval`` configuration and its backtesting infrastructure are designed to support continuous retraining.

**Failure modes.** When a long-term model is wrong, the consequence is a planning error discovered months later. When a short-term operational forecast fails, the consequence can be a grid imbalance within the hour. This is why OpenSTEF includes explicit fallback strategies — covered in :doc:`reliability_and_fallback` — that activate when a primary model cannot produce a valid prediction.

.. note::

   The practical horizon ceiling for OpenSTEF is around 48–72 hours. Beyond that, the weather forecast uncertainty that drives load and renewable generation becomes large enough that a different modelling approach — one that explicitly represents meteorological ensemble uncertainty — is typically more appropriate.

Summary
-------

Short-term forecasting in OpenSTEF is defined by three interlocking concepts:

- **Horizon (lead time):** how far ahead each prediction reaches, expressed as a ``LeadTime`` and typically ranging from 15 minutes to 48 hours.
- **Forecast frequency:** how often a fresh forecast is generated, configured independently of the horizon via ``predict_interval``.
- **Data availability:** the explicit tracking of when each measurement became usable, preventing look-ahead bias in both backtests and live systems.

Together these concepts determine the operational envelope of a forecasting deployment. The pages in this section build on these foundations: :doc:`feature_engineering` explains what inputs drive short-term predictions, :doc:`quantiles_and_confidence` covers how uncertainty is quantified across horizons, and :doc:`reliability_and_fallback` addresses what happens when the primary forecast cannot be produced.