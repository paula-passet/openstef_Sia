Forecasting Basics
==================

Short-term energy forecasting is the practice of predicting electricity load or generation over the next minutes to days. This page explains what that means in concrete terms: what horizons are involved, how lead times and update frequency interact, and how OpenSTEF models these concepts.

For probabilistic output (quantiles and confidence intervals), see :doc:`quantiles_and_confidence`. For the features that drive these forecasts, see :doc:`feature_engineering`.

What Is Short-Term Forecasting?
--------------------------------

A short-term energy forecast answers the question: *given everything we know right now, what will the load (or generation) be at some future point?* "Short-term" typically means anything from a few minutes ahead up to roughly 48 hours. Beyond that window, the problem shifts to medium- and long-term planning, which relies on different data sources, model architectures, and operational workflows.

Short-term forecasts are operationally critical. Grid operators use them to schedule reserves, balance supply and demand in near-real-time, and avoid costly imbalances. A forecast for tomorrow morning's peak load, produced the evening before, is a fundamentally different product from a capacity plan for next winter — even though both involve predicting energy consumption.

The key distinction from long-term forecasting is **what drives the uncertainty**. Over days and weeks, weather uncertainty dominates. Over months and years, structural factors — economic growth, electrification trends, building stock — matter more. Short-term models therefore invest heavily in weather features and recent load patterns, while long-term models lean on demographic and economic signals.

Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three concepts define the temporal structure of any forecast:

- **Horizon** (or lead time): how far ahead the forecast looks from the moment it is generated. A 36-hour horizon means the model predicts load 36 hours into the future.
- **Available-at time**: the wall-clock moment when a forecast is produced and ready for consumption. This accounts for data ingestion delays — measured values are rarely available the instant they are recorded.
- **Update frequency**: how often a new forecast is generated. A model that runs every 15 minutes produces 96 forecasts per day for the same target timestamp, each with progressively shorter lead times and (usually) lower uncertainty.

These three dimensions interact. A forecast produced at 06:00 for 18:00 the same day has a 12-hour lead time. If the same model runs again at 12:00, the new forecast for 18:00 has only a 6-hour lead time and will typically be more accurate because it incorporates six additional hours of observed data and a fresher weather update.

.. note:: [DIAGRAM: Timeline showing four forecast horizons (15 min, 1 h, 24 h, 48 h) on a horizontal time axis. For each horizon, an arrow spans from the "available-at" moment to the target timestamp, illustrating lead time. A repeating bracket below the axis shows the update frequency (e.g., every 15 min for the short horizon, every hour for the 24 h and 48 h horizons). Annotations highlight how uncertainty grows with lead time and shrinks as the available-at time approaches the target.]

In OpenSTEF, horizons are first-class objects represented by ``LeadTime``. A ``LeadTime`` wraps a ``timedelta`` and carries semantic meaning throughout the library — from training data selection to forecast output labelling.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime

    # Construct lead times explicitly
    horizon_15min = LeadTime(timedelta(minutes=15))
    horizon_1h    = LeadTime(timedelta(hours=1))
    horizon_36h   = LeadTime(timedelta(hours=36))

    # Or parse from an ISO 8601 duration string
    horizon_24h = LeadTime.from_string("PT24H")
    horizon_48h = LeadTime.from_string("PT48H")

Why Multiple Horizons Matter
-----------------------------

A single model trained on one horizon will not generalise well to others. The statistical relationship between features and load changes with lead time:

- At **15 minutes**, the most recent measured load is the strongest predictor. Weather barely matters because conditions cannot change much in a quarter-hour.
- At **1–6 hours**, recent trends still dominate, but weather forecasts start contributing meaningfully.
- At **24–48 hours**, the day-of-week pattern, calendar effects, and weather forecasts become the primary drivers. The last observed value is far less informative.

OpenSTEF handles this through two complementary strategies. A ``Forecaster`` subclass can be **single-horizon** (one model per lead time, each specialised) or **multi-horizon** (one model that learns across all lead times simultaneously). Tree-based models such as XGBoost handle multi-horizon training well because they tolerate missing lag features at long horizons. Linear models are typically restricted to a single horizon because missing lag values require imputation that can distort the fit.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_models.integrations.mlflow import MLFlowStorage

    # Configure a workflow that forecasts 36 hours ahead
    config = ForecastingWorkflowConfig(
        model_id="day_ahead_forecaster_v1",
        model="gblinear",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        mlflow_storage=MLFlowStorage(
            tracking_uri="./mlflow_tracking",
            local_artifacts_path="./mlflow_artifacts",
        ),
    )

    workflow = create_forecasting_workflow(config=config)

To cover multiple operational horizons — for example, a 15-minute intraday product and a day-ahead product — configure separate workflows with the appropriate ``horizons`` list, or use a multi-horizon forecaster that accepts several ``LeadTime`` values at once.

.. code-block:: python

    from openstef_core.types import LeadTime

    # Multi-horizon configuration: one model, several lead times
    horizons = [
        LeadTime.from_string("PT1H"),
        LeadTime.from_string("PT6H"),
        LeadTime.from_string("PT24H"),
        LeadTime.from_string("PT48H"),
    ]

The ``ForecastDataset`` returned by ``predict()`` carries a ``horizon`` column so downstream consumers always know which lead time each row corresponds to. You can filter to a specific horizon using ``filter_by_lead_time``:

.. code-block:: python

    from openstef_core.types import LeadTime

    # Assume `forecast_dataset` is a ForecastDataset returned by workflow.predict(...)
    day_ahead = forecast_dataset.filter_by_lead_time(LeadTime.from_string("PT24H"))

How Forecast Frequency Affects Model Design
--------------------------------------------

Update frequency is an operational choice, but it has direct consequences for model design. Running a model every 15 minutes means training data must be structured so that features are available with the same 15-minute cadence. A feature derived from a weather forecast that is only updated hourly will appear constant within each hour — which is fine, but the model must be trained on data that reflects this reality.

OpenSTEF's ``available_at`` concept captures this. Each row in a ``TimeSeriesDataset`` is tagged with the time at which it *became available*, not just the time it *describes*. This prevents the model from accidentally using data that would not have existed at prediction time — a form of look-ahead bias that is easy to introduce and hard to detect.

.. note::

   Look-ahead bias is one of the most common sources of over-optimistic backtesting results in energy forecasting. Always verify that your training data respects the ``available_at`` timestamps before trusting evaluation metrics.

Short-Term vs. Long-Term: A Practical Summary
----------------------------------------------

+---------------------+-------------------------------+-------------------------------+
| Dimension           | Short-term (this library)     | Long-term (out of scope)      |
+=====================+===============================+===============================+
| Horizon             | Minutes to ~48 hours          | Weeks to years                |
+---------------------+-------------------------------+-------------------------------+
| Primary drivers     | Recent load, weather NWP      | Demographics, policy, climate |
+---------------------+-------------------------------+-------------------------------+
| Update frequency    | Minutes to hours              | Days to months                |
+---------------------+-------------------------------+-------------------------------+
| Uncertainty source  | Weather, measurement noise    | Structural change             |
+---------------------+-------------------------------+-------------------------------+
| Typical output      | Probabilistic time series     | Scenario ranges               |
+---------------------+-------------------------------+-------------------------------+

OpenSTEF is designed exclusively for the short-term regime. Its feature engineering, model presets, and evaluation tooling all assume horizons measured in hours, not months.

Related Topics
--------------

- :doc:`feature_engineering` — which predictors matter at which horizons, and how lag features encode recent history
- :doc:`quantiles_and_confidence` — how OpenSTEF expresses forecast uncertainty as quantile distributions
- :doc:`reliability_and_fallback` — what happens when a model cannot produce a forecast in time
- :doc:`component_splitting` — decomposing aggregate load into interpretable sub-components before forecasting