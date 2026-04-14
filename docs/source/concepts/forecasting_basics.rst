Forecasting Basics
==================

Short-term energy forecasting sits at the operational heart of grid management, trading, and asset control. This page explains what short-term forecasting means in practice, why it differs fundamentally from long-term forecasting, and how OpenSTEF structures the key concepts of horizons, lead times, and update frequency that govern every forecast it produces.

What Is Short-Term Forecasting?
--------------------------------

Short-term energy forecasting predicts power consumption or generation over intervals ranging from a few minutes to a few days ahead. Unlike long-term forecasting — which projects annual demand growth or capacity needs over years — short-term forecasting must be *operationally accurate*: a grid operator balancing supply and demand in real time cannot act on a forecast that is directionally correct but off by an hour.

The distinction is not merely one of time scale. Long-term forecasts tolerate uncertainty because their purpose is planning; they inform investment decisions where a ±5% error over a decade is acceptable. Short-term forecasts drive *dispatch decisions* — which generators to commit, how much reserve capacity to hold, when to charge or discharge a battery. Here, a 10% error in the next 15 minutes can mean imbalance penalties or grid instability.

OpenSTEF is designed exclusively for the short-term regime. Its data structures, feature engineering conventions, and model pipelines all assume that forecasts will be refreshed frequently, that weather data is a primary driver, and that the gap between *when a forecast is made* and *what it predicts* is a first-class concern.

Horizons and Lead Times
------------------------

Two concepts govern every forecast OpenSTEF produces:

- **Horizon** — how far ahead the forecast looks. A 24-hour horizon means the model predicts load or generation values for each interval over the next 24 hours.
- **Lead time** — the gap between the moment the forecast becomes available and the timestamp it predicts. A forecast published at 06:00 for 18:00 the same day has a lead time of 12 hours.

These are related but not identical. A single forecast *run* produces predictions across many horizons simultaneously; each individual prediction within that run has its own lead time. OpenSTEF represents this distinction explicitly through the ``LeadTime`` and ``AvailableAt`` types in ``VersionedTimeSeriesDataset``.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

Typical operational horizons in the energy sector, and how OpenSTEF addresses each:

- **15 minutes** — intra-hour balancing and automatic frequency restoration. Forecasts must be available within seconds of the previous interval closing. OpenSTEF's ``LeadTime`` can be set to ``PT15M`` and the pipeline refreshed on a cron schedule matching the market interval.
- **1 hour** — hour-ahead markets and congestion management. A common default in distribution grid applications.
- **24 hours** — day-ahead electricity markets. Gate closure is typically the evening before, so the ``AvailableAt`` for these forecasts is often ``D-1T18:00`` or ``D-1T06:00``.
- **48 hours** — two-day planning for maintenance scheduling and reserve procurement. Accuracy degrades with horizon length, so probabilistic outputs (see :doc:`quantiles_and_confidence`) become especially important here.

How OpenSTEF Models Horizons
-----------------------------

OpenSTEF's ``VersionedTimeSeriesDataset`` treats the relationship between forecast availability time and target timestamp as a first-class property of the data, not an afterthought. Every row in a versioned dataset carries either a ``horizon`` column (the lead time as a ``timedelta``) or an ``available_at`` column (the wall-clock time when the forecast was published).

This design prevents *lookahead bias* — the subtle error of training a model on features that would not have been available at prediction time. When you call ``select_version()``, the dataset returns a point-in-time snapshot: only data that was genuinely available at or before the ``available_at`` timestamp is included.

.. code-block:: python

    import pandas as pd
    from datetime import timedelta
    from openstef.dataset import VersionedTimeSeriesDataset  # illustrative import path

    # Build a dataset versioned by forecast horizon
    data = pd.DataFrame(
        {"load_mw": [210.5, 215.3, 208.1, 212.7]},
        index=pd.date_range("2024-06-01 00:00", periods=4, freq="15min"),
    )
    data["horizon"] = [
        timedelta(hours=1),
        timedelta(hours=2),
        timedelta(hours=3),
        timedelta(hours=4),
    ]

    dataset = VersionedTimeSeriesDataset(
        data=data,
        sample_interval=timedelta(minutes=15),
    )

    # Inspect available horizons
    print(dataset.horizons())

    # Select only data available with at least a 2-hour lead time
    from openstef.dataset import LeadTime
    two_hour_view = dataset.filter_by_lead_time(LeadTime.from_string("PT2H"))

    # Produce a point-in-time snapshot (no lookahead)
    snapshot = two_hour_view.select_version()

Configuring Horizons in a Forecasting Model
--------------------------------------------

When you configure a forecasting pipeline in OpenSTEF, the ``horizons`` field on the forecaster config tells the model which lead times to produce predictions for. The ``max_horizon`` property is used internally during data preparation to ensure that enough historical context is loaded.

.. code-block:: python

    from openstef_models.models.forecasting import ForecastingModel
    from openstef_models.config import ForecastingConfig
    from openstef.dataset import LeadTime, Quantile

    config = ForecastingConfig(
        horizons=[
            LeadTime.from_string("PT15M"),   # 15-minute ahead
            LeadTime.from_string("PT1H"),    # 1-hour ahead
            LeadTime.from_string("PT24H"),   # day-ahead
            LeadTime.from_string("PT48H"),   # two-day ahead
        ],
        quantiles=[
            Quantile(0.1),
            Quantile(0.5),
            Quantile(0.9),
        ],
    )

    # The pipeline will produce predictions at all four horizons,
    # each with three quantile levels.
    print(f"Furthest horizon: {config.max_horizon}")

.. note::

   Accuracy degrades as horizon length increases. A model that performs well at 1-hour lead times will typically show higher errors at 48 hours. OpenSTEF supports multi-horizon models that learn this degradation explicitly, as well as separate single-horizon models tuned for each lead time. See :doc:`model_selection` for guidance on choosing the right approach.

Update Frequency and Gate Closures
------------------------------------

Forecast *update frequency* is distinct from forecast *horizon*. A 48-hour forecast might be refreshed twice daily (at 06:00 and 18:00) to align with day-ahead and intraday market gate closures, while a 15-minute forecast is refreshed continuously. OpenSTEF does not prescribe a scheduling mechanism — it is a library, and the calling application controls when ``predict()`` is invoked — but the ``AvailableAt`` type is designed to express these operational patterns cleanly.

.. code-block:: python

    from openstef.dataset import AvailableAt

    # Day-ahead gate closure: forecast available at 06:00 the day before delivery
    day_ahead = AvailableAt.from_string("D-1T06:00")

    # Intraday: forecast available 36 hours before delivery
    intraday = AvailableAt.from_string("PT36H")

The ``EvaluationConfig`` in OpenSTEF's evaluation pipeline accepts a list of ``available_ats`` so you can assess model performance separately for each gate closure time — a critical step before deploying a model into production.

Why Short-Term Forecasting Is Hard
------------------------------------

Several properties of short-term energy data make this problem genuinely difficult:

- **Weather sensitivity.** Load and renewable generation respond non-linearly to temperature, irradiance, and wind speed. A 2 °C temperature spike on a hot day can shift peak load by several percent. Feature engineering for weather inputs is covered in :doc:`feature_engineering`.
- **Temporal patterns at multiple scales.** Demand follows daily, weekly, and annual cycles simultaneously. A model must learn that Monday morning at 08:00 in January is different from Monday morning at 08:00 in July, and different again from a public holiday.
- **Data latency.** Metering data from substations or smart meters often arrives with a delay. A forecast nominally issued at T+0 may be working with measurements that are 15–30 minutes stale. The ``VersionedTimeSeriesDataset`` versioning mechanism exists precisely to model this reality.
- **Distributional shift.** Energy consumption patterns change over time as building stock improves, electric vehicles proliferate, or industrial customers change behaviour. Models need periodic retraining, and fallback strategies are needed when a model's predictions become unreliable. See :doc:`reliability_and_fallback`.

Short-term forecasting is also probabilistic in nature: a single point prediction is rarely sufficient for operational decisions. A grid operator needs to know not just the expected load but the range of plausible outcomes. OpenSTEF produces quantile forecasts by default; the interpretation of those quantiles is covered in :doc:`quantiles_and_confidence`.

Summary
--------

Short-term energy forecasting in OpenSTEF is built around three interlocking concepts:

- **Horizon** — the target lead time a prediction covers, from 15 minutes to 48 hours.
- **Lead time / available_at** — the point-in-time constraint that prevents lookahead bias and reflects real operational data latency.
- **Update frequency** — how often the calling application refreshes forecasts, driven by market gate closures or operational requirements.

OpenSTEF's data structures make these concepts explicit rather than implicit, which is what allows the library to produce backtests and evaluations that faithfully replicate production conditions. The next step is understanding how the library represents forecast uncertainty — continue to :doc:`quantiles_and_confidence`.