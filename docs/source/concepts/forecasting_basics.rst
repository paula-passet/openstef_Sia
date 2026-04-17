Short-Term Energy Forecasting
==============================

Short-term energy forecasting is the practice of predicting energy load, generation, or price over
intervals ranging from minutes to a few days ahead. This page explains what short-term forecasting
means in the context of OpenSTEF, why it matters for grid operations, and how the key concepts of
**horizon**, **lead time**, and **forecast frequency** shape the way the library works.

.. note:: [DIAGRAM: Timeline showing forecast horizons and lead times. A horizontal time axis runs
   left to right. A vertical marker labelled "now (t₀)" sits near the left. Four coloured arrows
   extend rightward from t₀, labelled 15 min, 1 h, 24 h, and 48 h respectively, representing the
   forecast horizon for each use-case. Above each arrow a small annotation shows the typical update
   frequency (e.g. "updated every 15 min" for the shortest horizon, "updated every hour" for 1 h,
   "updated once or twice daily" for 24 h and 48 h). A shaded band to the left of t₀ represents
   historical data; a lighter shaded band to the right represents the forecast window.]


Why Short-Term Forecasting?
----------------------------

Grid operators, balance-responsible parties, and energy traders all need to know what load or
generation will look like in the near future. The decisions they make — dispatching flexible assets,
placing bids on intraday markets, scheduling maintenance — are only as good as the forecasts that
inform them. Errors that seem small in percentage terms translate directly into imbalance costs or
curtailed renewable output.

Short-term forecasting is distinct from long-term planning in both purpose and method:

- **Long-term forecasting** (months to years) answers strategic questions: how much capacity to
  build, where to invest in grid reinforcement. It relies on demographic trends, economic
  projections, and climate scenarios. Accuracy at the level of individual hours or days is neither
  expected nor required.

- **Short-term forecasting** (minutes to ~48 hours) answers operational questions: what will the
  net load on this substation be in the next quarter-hour? It must capture intraday patterns,
  weather-driven spikes, and the stochastic behaviour of distributed generation. Accuracy at the
  resolution of individual time steps is essential.

OpenSTEF is designed exclusively for the short-term regime. Its feature engineering, model
architectures, and evaluation tooling are all oriented around the operational timescales that matter
for real-time grid management.


Horizons and Lead Times
------------------------

Two terms appear throughout the OpenSTEF codebase and are worth distinguishing carefully.

**Horizon** is the distance into the future that a forecast covers — for example, 15 minutes,
1 hour, 24 hours, or 48 hours. A single trained model may produce predictions at multiple horizons
simultaneously; OpenSTEF represents each horizon as a ``LeadTime`` value.

**Lead time** is the gap between the moment a prediction is *generated* (or, more precisely, the
moment the input data used to generate it became available) and the timestamp being predicted. In
practice, lead time and horizon are closely related but not identical: a forecast nominally labelled
"24 h ahead" may actually be generated using data that was only available 26 hours before the target
timestamp, because measurement data arrives with a delay and goes through validation pipelines before
it can be used.

OpenSTEF makes this distinction explicit through its ``AvailableAt`` concept. Every versioned
dataset records *when* each observation became available, not just when it was measured. This
prevents lookahead bias: a model trained or evaluated on versioned data can only use information
that would genuinely have been in hand at prediction time.

.. note::

   The ``LeadTime`` type in ``openstef_core.types`` encodes a ``timedelta`` and is used throughout
   the library wherever a horizon must be specified. ``AvailableAt`` encodes the daily schedule at
   which a data source becomes usable (e.g. ``D-1T06:00`` means "the day before the target date at
   06:00").

The practical consequence is that different horizons may draw on different versions of the same
underlying measurement. A 1-hour-ahead forecast can use near-real-time SCADA readings; a 36-hour-
ahead forecast must rely on the validated day-ahead data release. OpenSTEF's versioned dataset
infrastructure handles this automatically when you filter by lead time:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.types import LeadTime

   # Load a versioned measurement dataset
   dataset = VersionedTimeSeriesDataset.read_parquet(
       path="measurements.parquet",
       sample_interval=timedelta(minutes=15),
   )

   # Retrieve only data that was available at least 36 hours before each target timestamp
   # — appropriate for a day-ahead forecast
   day_ahead_horizon = LeadTime(timedelta(hours=36))
   day_ahead_data = dataset.filter_by_lead_time(lead_time=day_ahead_horizon).select_version()

   # Retrieve data available at least 1 hour before each target timestamp
   # — appropriate for an intraday forecast
   intraday_horizon = LeadTime(timedelta(hours=1))
   intraday_data = dataset.filter_by_lead_time(lead_time=intraday_horizon).select_version()


Typical Horizon Ranges in Grid Operations
------------------------------------------

Different operational processes require forecasts at different horizons. The table below summarises
the most common use-cases that OpenSTEF is designed to support.

+-------------------+---------------------+----------------------------------+-----------------------------+
| Horizon           | Update frequency    | Primary use-case                 | Key input data              |
+===================+=====================+==================================+=============================+
| 15 min            | Every 15 min        | Real-time balancing, AGC         | Near-real-time SCADA        |
+-------------------+---------------------+----------------------------------+-----------------------------+
| 1 h               | Every 15–60 min     | Intraday market bids             | SCADA + NWP updates         |
+-------------------+---------------------+----------------------------------+-----------------------------+
| 24 h              | 1–2 times daily     | Day-ahead market, scheduling     | NWP day-ahead, smart-meter  |
+-------------------+---------------------+----------------------------------+-----------------------------+
| 48 h              | Once daily          | Outage planning, reserves        | NWP extended, calendar      |
+-------------------+---------------------+----------------------------------+-----------------------------+

The shorter the horizon, the more frequently the forecast must be refreshed and the more it can
rely on recent measurements. The longer the horizon, the more it depends on weather forecasts and
calendar features. OpenSTEF's feature engineering layer is designed to supply the right predictors
for each regime — see :doc:`feature_engineering` for details.


Multi-Horizon Forecasting in OpenSTEF
---------------------------------------

OpenSTEF supports two strategies for covering multiple horizons.

**Multi-horizon models** train a single model that produces predictions for all configured horizons
at once. This is the preferred approach when the model architecture can handle the varying data
availability that comes with different lead times. Tree-based models such as XGBoost and LightGBM
fall into this category.

**Single-horizon models** train one model per horizon. This is appropriate for architectures that
cannot gracefully handle missing or conditionally available features — for example, linear models
that require a complete, dense feature matrix.

The ``Forecaster`` base class in ``openstef_core`` exposes a ``horizons`` field that accepts a list
of ``LeadTime`` values. Passing multiple horizons activates multi-horizon mode; passing a single
value restricts the model to that horizon only:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgb_forecaster import XGBForecaster

   # A multi-horizon XGBoost model covering intraday through day-ahead
   forecaster = XGBForecaster(
       horizons=[
           LeadTime(timedelta(minutes=15)),
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=24)),
           LeadTime(timedelta(hours=48)),
       ],
       quantiles=[
           Quantile(0.1),
           Quantile(0.5),
           Quantile(0.9),
       ],
   )

   # fit() and predict() operate across all horizons simultaneously
   # forecaster.fit(training_dataset)
   # predictions = forecaster.predict(input_dataset)

The ``max_horizon`` property on any forecaster returns the largest configured ``LeadTime``, which
is used internally to determine how much historical context is needed when preparing input data.


Forecast Frequency and Rolling Updates
----------------------------------------

In production, short-term forecasts are not generated once and forgotten — they are refreshed
continuously as new observations arrive. A 24-hour-ahead forecast issued at 06:00 is superseded by
a fresher one issued at 07:00, which has access to one additional hour of real measurements and
possibly an updated numerical weather prediction (NWP) run.

This rolling update pattern has two implications for how OpenSTEF models are built and evaluated.

First, **training data must be versioned**. A model trained naively on a flat historical dataset
will inadvertently learn from data that would not have been available at prediction time, producing
optimistic evaluation metrics that do not hold in production. OpenSTEF's ``VersionedTimeSeriesDataset``
and its ``select_version()`` method enforce point-in-time correctness throughout the training and
backtesting workflow.

Second, **evaluation must respect the update schedule**. The ``AvailableAt`` configuration in the
evaluation pipeline specifies the exact times at which predictions are assumed to be generated.
Metrics computed at ``D-1T06:00`` (day-ahead, 06:00 release) are meaningfully different from
metrics computed at ``D-1T18:00``, because the later release has access to more recent NWP data
and a shorter effective lead time for the early hours of the target day.

.. code-block:: python

   from openstef_beam.evaluation.pipeline import EvaluationConfig, EvaluationPipeline
   from openstef_core.types import LeadTime, AvailableAt
   from datetime import timedelta

   config = EvaluationConfig(
       available_ats=[
           AvailableAt.from_string("D-1T06:00"),
           AvailableAt.from_string("D-1T18:00"),
       ],
       lead_times=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=24)),
           LeadTime(timedelta(hours=48)),
       ],
   )

This configuration tells the evaluation pipeline to score predictions separately for each
combination of availability time and lead time, giving a clear picture of how forecast quality
degrades as the horizon grows and how much value later data releases add.

.. note::

   Choosing the right ``available_ats`` for your evaluation should reflect the actual release
   schedule of your input data sources. If your NWP provider publishes a new run at 00:00 and
   12:00 UTC, those are the natural candidates.


Relationship to Probabilistic Forecasts
-----------------------------------------

The horizons and lead times discussed on this page define *when* a forecast is made and *how far
ahead* it looks. They say nothing about the uncertainty attached to that forecast. In practice,
forecast uncertainty grows with horizon: a 15-minute-ahead prediction is far more certain than a
48-hour-ahead one, and that uncertainty should be communicated explicitly rather than hidden inside
a single point estimate.

OpenSTEF addresses this through quantile forecasting. Every model is configured with a list of
``Quantile`` values that it must predict, and the resulting ``ForecastDataset`` carries a full
probability distribution for each future timestamp. See :doc:`quantiles_and_confidence` for a
detailed treatment of how to interpret and use these probabilistic outputs.

For information on the weather and calendar features that drive forecast quality at longer horizons,
see :doc:`feature_engineering`. For guidance on what happens when a model cannot produce a reliable
forecast — for example, because input data is missing — see :doc:`reliability_and_fallback`.