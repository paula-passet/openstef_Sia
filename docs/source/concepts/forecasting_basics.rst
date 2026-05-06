Short-Term Forecasting Basics
=============================

Short-term energy forecasting sits at the heart of what OpenSTEF is built for. This page explains what "short-term" means in practice, why the energy sector needs it, and how the key concepts of *horizon*, *lead time*, and *forecast frequency* relate to one another. If you are new to OpenSTEF, reading this page first will make the rest of the documentation considerably easier to follow.

What Is Short-Term Energy Forecasting?
---------------------------------------

Short-term energy forecasting is the task of predicting electricity load, generation, or net exchange over a window that spans minutes to roughly seven days into the future. The predictions are made repeatedly — often every 15 minutes — so that grid operators, balance-responsible parties, and trading desks always have a fresh view of what the near future looks like.

OpenSTEF focuses exclusively on this short-term regime. Beyond roughly seven days, the 15-minute-resolution weather forecasts that drive solar and wind predictions no longer exist, and peak events become essentially unpredictable. Long-term forecasting (months to years) is a different discipline with different data sources, different models, and different business uses; OpenSTEF does not target it.

Why Short-Term Forecasts Matter
--------------------------------

The electricity grid must be balanced in real time: generation must equal consumption at every moment. Imbalance is expensive and, at extremes, dangerous. Short-term forecasts feed directly into the decisions that keep the grid balanced:

- **Congestion management** — transmission system operators use 24–48 h ahead forecasts to identify overloaded cables and activate remedial actions before the problem occurs.
- **Intraday trading** — balance-responsible parties update their positions on intraday markets using forecasts with horizons of 1–6 h.
- **Real-time dispatch** — control rooms use 15–60 min ahead forecasts to fine-tune generator set-points and demand-response activations.

Each use case has a different tolerance for error and a different requirement for how far ahead the forecast must reach. OpenSTEF models are designed to serve all of them from a single training pipeline by producing predictions at multiple horizons simultaneously.

Key Concepts
-------------

Horizon
^^^^^^^

The **horizon** (also called *lead time* in OpenSTEF's API) is the distance in time between the moment a forecast is *generated* and the moment it is *valid for*. A horizon of ``PT1H`` means the model is predicting what will happen one hour from now.

In OpenSTEF, horizons are represented by the ``LeadTime`` type, which wraps a standard ``timedelta``:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime

    # A 15-minute horizon
    h15min = LeadTime(timedelta(minutes=15))

    # A 24-hour horizon
    h24h = LeadTime(timedelta(hours=24))

    # A 48-hour horizon — typical day-ahead planning window
    h48h = LeadTime(timedelta(hours=48))

A single model can be trained to produce forecasts at several horizons at once. This is called *multi-horizon forecasting* and is the default approach in OpenSTEF.

Lead Time vs. Available-At
^^^^^^^^^^^^^^^^^^^^^^^^^^^

These two concepts are easy to confuse:

- **Lead time** is how far ahead the forecast looks (e.g., 36 hours).
- **Available-at** is the wall-clock moment when the forecast is published and usable (e.g., every day at 06:00).

A day-ahead forecast published at 06:00 for delivery the following day has an *available-at* of ``D-1T06:00`` and a *lead time* that ranges from roughly 18 h (for the first interval of the delivery day) to 42 h (for the last interval). OpenSTEF's ``AvailableAt`` and ``LeadTime`` types capture both dimensions so that evaluation and backtesting can slice results along either axis.

.. code-block:: python

    from openstef_core.types import AvailableAt, LeadTime
    from datetime import timedelta

    # Forecast published the day before at 06:00
    available_at = AvailableAt.from_string("D-1T06:00")

    # Lead time of 36 hours (midpoint of a typical day-ahead window)
    lead_time = LeadTime.from_string("PT36H")

Forecast Frequency
^^^^^^^^^^^^^^^^^^

Forecast frequency is how often a new forecast is generated. In most grid-connected applications this matches the measurement resolution — typically 15 minutes. Generating a fresh forecast every 15 minutes means the model always incorporates the latest metered data, weather update, and any corrections from the previous interval.

Higher frequency is not always better: it increases computational load and may not improve accuracy if the underlying weather forecast is only updated hourly. OpenSTEF pipelines are designed to be triggered by a scheduler (a cron job, Dagster, or a cloud workflow) at whatever cadence the use case demands.

The Forecasting Timeline
-------------------------

The diagram below shows how the four common horizons relate to each other, when forecasts are published, and how frequently they are updated.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

The 15-minute and 1-hour horizons are the most sensitive to real-time data: a new meter reading can shift the prediction meaningfully. The 24-hour and 48-hour horizons are dominated by weather forecasts and calendar effects (day of week, public holidays), so updating them more than once or twice a day yields diminishing returns.

Putting It Together: A Multi-Horizon Forecaster
------------------------------------------------

The following example shows how to configure a forecaster that covers three horizons simultaneously — a common setup for a distribution grid substation:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.gb_linear_forecaster import (
        GBLinearForecaster,
        GBLinearHyperParams,
    )

    forecaster = GBLinearForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[
            LeadTime(timedelta(minutes=15)),   # real-time dispatch
            LeadTime(timedelta(hours=1)),       # intraday trading
            LeadTime(timedelta(hours=24)),      # day-ahead planning
        ],
        hyperparams=GBLinearHyperParams(
            learning_rate=0.05,
            reg_alpha=0.1,
            reg_lambda=1.0,
        ),
    )

    # Train on historical data
    forecaster.fit(training_data)  # training_data is a VersionedTimeSeries

    # Produce probabilistic forecasts at all three horizons
    predictions = forecaster.predict(test_data)

The ``quantiles`` argument means each horizon produces not just a point forecast but a full probability distribution. This is covered in depth on the :doc:`quantiles_and_confidence` page.

How OpenSTEF Handles Data Availability
----------------------------------------

A subtle but important aspect of short-term forecasting is that the features available to the model depend on the horizon. For a 15-minute-ahead forecast you can use the most recent meter reading; for a 48-hour-ahead forecast that reading is not yet available — it lies in the future relative to the forecast generation time.

OpenSTEF enforces this through its ``VersionedTimeSeries`` data structure. When the model is trained or evaluated, each row is tagged with an ``available_at`` timestamp. The training pipeline automatically restricts each horizon's view to only the features that would have been observable at that moment, preventing any lookahead bias from contaminating the model.

.. code-block:: python

    from openstef_core.datasets import VersionedTimeSeries

    # Filter to only data that was available at a specific wall-clock time
    available_view = dataset.filter_by_available_at(available_at)

    # Or select only the rows relevant to a specific lead time
    horizon_view = dataset.filter_by_lead_time(LeadTime(timedelta(hours=24)))

This design means the same model object can be evaluated fairly across all horizons without any manual data-splitting gymnastics.

Short-Term vs. Long-Term: A Practical Boundary
------------------------------------------------

+---------------------+---------------------------+---------------------------+
| Dimension           | Short-term (OpenSTEF)     | Long-term (out of scope)  |
+=====================+===========================+===========================+
| Horizon range       | 15 min – ~7 days          | Weeks, months, years      |
+---------------------+---------------------------+---------------------------+
| Primary drivers     | Weather, recent load      | Demographics, policy,     |
|                     | history, calendar         | economic growth           |
+---------------------+---------------------------+---------------------------+
| Typical resolution  | 15 min                    | Daily, monthly            |
+---------------------+---------------------------+---------------------------+
| Update frequency    | Every 15 min – hourly     | Weekly or less            |
+---------------------+---------------------------+---------------------------+
| Uncertainty source  | Weather forecast error,   | Structural change,        |
|                     | measurement noise         | scenario uncertainty      |
+---------------------+---------------------------+---------------------------+

The seven-day ceiling is not arbitrary. Beyond that point, numerical weather prediction models no longer provide 15-minute-resolution output, solar and wind generation become essentially unpredictable at the interval level, and the accuracy of any model degrades to the point where it offers little operational value.

Where to Go Next
-----------------

This page has introduced the vocabulary and structure of short-term forecasting in OpenSTEF. The sibling pages in this section go deeper on specific aspects:

- :doc:`feature_engineering` — which predictors matter most (weather, calendar, lag features) and how OpenSTEF builds them automatically.
- :doc:`quantiles_and_confidence` — how probabilistic forecasts are expressed as quantiles and what confidence intervals mean operationally.
- :doc:`component_splitting` — how aggregate load measurements are decomposed into interpretable components before forecasting.
- :doc:`reliability_and_fallback` — what happens when a model fails in production and how OpenSTEF's fallback strategies keep the system running.
- :doc:`meta_ensembles` — how multiple models are combined into a meta-ensemble to improve robustness across different grid conditions.