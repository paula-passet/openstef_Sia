Short-Term Forecasting Basics
=============================

Short-term energy forecasting is the practice of predicting electricity load or generation
over the next minutes to days. This page explains what "short-term" means in practice,
why the distinction matters, and how OpenSTEF models the key concepts of horizons, lead
times, and update frequency.

.. mermaid:: /diagrams/concepts/forecasting_basics_diagram_1.mmd

What Short-Term Forecasting Means
----------------------------------

Energy forecasting spans a wide range of time scales. Long-term forecasts — months to
years ahead — inform capacity planning and infrastructure investment. Medium-term
forecasts — days to weeks — support fuel procurement and maintenance scheduling.
Short-term forecasting covers the window from a few minutes to roughly 48 hours ahead,
and it serves a fundamentally different purpose: keeping the grid balanced in near
real-time.

At this timescale, the dominant drivers of load and generation are weather conditions,
time-of-day patterns, and recent observed behaviour. The forecast must be accurate enough
to schedule reserves, dispatch flexible assets, and settle imbalance markets — all of
which have hard deadlines measured in minutes or hours, not days.

OpenSTEF is built specifically for this operational window. Its data structures,
preprocessing transforms, and model interfaces are all designed around the assumption
that forecasts are produced repeatedly, on a rolling basis, and must be available before
a well-defined market or operational cut-off.

Horizons and Lead Times
-----------------------

The two most important time concepts in short-term forecasting are the **horizon** and
the **lead time**. In OpenSTEF these are represented by the ``LeadTime`` type, which
wraps a ``timedelta`` and carries additional semantics about data availability.

- **Lead time** is the distance between the moment a forecast is *generated* and the
  timestamp it is *predicting*. A lead time of ``PT36H`` means the model is predicting
  what will happen 36 hours from now.
- **Horizon** is used interchangeably with lead time in the OpenSTEF API. Each
  ``LeadTime`` value in a model's ``horizons`` list defines one prediction distance the
  model is trained and evaluated for.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime

    # Common operational horizons
    intraday   = LeadTime(timedelta(hours=1))   # next-hour dispatch
    day_ahead  = LeadTime(timedelta(hours=24))  # day-ahead market
    extended   = LeadTime(timedelta(hours=48))  # two-day outlook

    # String construction is also supported
    day_ahead_str = LeadTime.from_string("PT24H")

Typical operational horizons and their use cases are:

- **15 minutes** — real-time balancing, frequency regulation
- **1 hour** — intraday market re-dispatch, reserve scheduling
- **24 hours** — day-ahead market bidding, generation scheduling
- **48 hours** — extended outlook, maintenance planning

The accuracy achievable at each horizon differs substantially. Weather forecasts
degrade with lead time, and the statistical relationship between recent observations
and future values weakens as the gap grows. A model trained for 15-minute-ahead
prediction will use very different features — and will likely be a different model
architecture — than one trained for 48-hour-ahead prediction.

Single-Horizon vs. Multi-Horizon Models
----------------------------------------

OpenSTEF supports two modelling strategies, and the choice matters for how you
configure your ``Forecaster``.

A **single-horizon model** is trained once for a specific lead time. It is the simpler
approach and works well for linear models that cannot handle missing or conditional
features across different time gaps. Each horizon requires its own trained model.

A **multi-horizon model** trains across several lead times simultaneously. Models such
as gradient-boosted trees (XGBoost, GBLinear) can share parameters and features across
horizons, which reduces training overhead and can improve generalisation when horizons
are closely related.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    # Multi-horizon workflow: one model covers 1 h through 48 h
    config = ForecastingWorkflowConfig(
        model_id="load_forecast_v1",
        model="gblinear",
        horizons=[
            LeadTime(timedelta(hours=1)),
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
    )

    workflow = create_forecasting_workflow(config=config)

.. note::

   Linear models are restricted to a single entry in ``horizons`` because they cannot
   handle the conditional feature structure that multi-horizon training requires.
   XGBoost-based models handle multiple horizons natively.

The ``max_horizon`` property on any fitted ``BaseForecastingModel`` returns the largest
lead time the model supports, which is useful for filtering input data before calling
``predict``.

Data Availability and the ``available_at`` Concept
----------------------------------------------------

A subtlety that distinguishes operational forecasting from offline analysis is **data
availability**. When a forecast is generated at, say, 06:00 on a given day, not all
historical observations are yet available — metering data arrives with a lag, SCADA
systems have reporting delays, and weather observations are published on their own
schedules.

OpenSTEF models this explicitly through the ``available_at`` field on datasets. Each
row in a ``ForecastInputDataset`` carries a timestamp indicating when that data point
became available, not just when it was measured. The ``filter_by_available_before``
method on dataset objects lets you simulate the information state at any past moment,
which is essential for realistic backtesting.

.. code-block:: python

    from datetime import datetime, timezone
    from openstef_core.datasets import TimeSeriesDataset

    # Simulate what data was available at 06:00 on a specific day
    cutoff = datetime(2024, 6, 1, 6, 0, tzinfo=timezone.utc)
    available_data = dataset.filter_by_available_before(cutoff)

This design means that when you call ``workflow.fit(dataset)``, the model is trained
only on data that would have been available at each historical forecast point — avoiding
the look-ahead bias that inflates performance in naive backtests.

Forecast Update Frequency
--------------------------

Short-term forecasts are not produced once and left unchanged. They are refreshed
continuously as new observations arrive and as the forecast horizon shortens. A typical
operational setup might:

- Produce a 48-hour outlook once per day at gate closure (e.g. 12:00 for the following
  day).
- Refresh the 1-hour-ahead forecast every 15 minutes as new metering data arrives.
- Re-run the 15-minute-ahead forecast every 5 minutes for real-time balancing.

Each refresh is a call to ``model.predict(new_data)``. The model itself does not change
between refreshes — only the input data window advances. Retraining (calling
``model.fit``) happens on a slower cycle, typically daily or weekly, to incorporate
recent load patterns without overfitting to short-term noise.

The ``EvaluationConfig`` in OpenSTEF captures this operational rhythm through its
``available_ats`` and ``lead_times`` fields, allowing you to evaluate model performance
separately for each combination of generation time and prediction distance.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, AvailableAt
    from openstef_models.evaluation import EvaluationConfig

    config = EvaluationConfig(
        available_ats=[
            AvailableAt.from_string("D-1T06:00"),  # day-ahead gate closure
            AvailableAt.from_string("D-1T12:00"),  # midday update
        ],
        lead_times=[
            LeadTime.from_string("PT1H"),
            LeadTime.from_string("PT24H"),
            LeadTime.from_string("PT48H"),
        ],
    )

How Short-Term Differs from Long-Term Forecasting
--------------------------------------------------

The practical differences between short-term and long-term forecasting go beyond the
obvious difference in horizon length:

**Feature set.** Short-term models rely heavily on recent observations (lags), numerical
weather predictions for the next 1–2 days, and calendar features (hour of day, day of
week). Long-term models use economic indicators, demographic trends, and seasonal
climate patterns. See :doc:`feature_engineering` for how OpenSTEF constructs the
short-term feature set.

**Model architecture.** Gradient-boosted trees and neural networks dominate short-term
forecasting because they capture non-linear interactions between weather and load
efficiently. Long-term forecasting often uses econometric or statistical models that
extrapolate trends.

**Uncertainty representation.** At short horizons, uncertainty is relatively small and
well-characterised by weather forecast uncertainty. At long horizons, structural
uncertainty (will a new factory open? will EV adoption accelerate?) dominates and is
harder to quantify. OpenSTEF produces probabilistic forecasts via quantile regression
at all horizons — see :doc:`quantiles_and_confidence` for details.

**Failure modes.** Short-term models can fail suddenly when a sensor goes offline, a
weather feed is delayed, or an unusual event (public holiday, extreme weather) falls
outside the training distribution. Long-term models fail more gradually through model
drift. Operational resilience strategies for short-term systems are covered in
:doc:`reliability_and_fallback`.

**Decomposition.** Short-term forecasting of aggregate grid load often benefits from
splitting the signal into interpretable components (solar, wind, base load) before
modelling each separately. This is described in :doc:`component_splitting`.

Summary
-------

Short-term energy forecasting in OpenSTEF is built around three interlocking ideas:

- **Lead time** defines how far ahead each prediction reaches, from 15 minutes to
  48 hours.
- **Data availability** is modelled explicitly so that training and evaluation reflect
  the information state at each forecast generation time.
- **Rolling updates** mean that ``predict`` is called frequently with advancing data
  windows, while ``fit`` runs on a slower retraining schedule.

These concepts are encoded directly in the ``LeadTime`` type, the ``available_at``
metadata on datasets, and the ``horizons`` configuration of every forecaster. The
remaining pages in this section build on these foundations: probabilistic outputs
(:doc:`quantiles_and_confidence`), the features that drive short-term accuracy
(:doc:`feature_engineering`), and how ensemble approaches combine multiple models
(:doc:`meta_ensembles`).