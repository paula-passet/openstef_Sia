Forecasting Basics
==================

Short-term energy forecasting is the practice of predicting electrical load, generation,
or related quantities over time horizons ranging from minutes to a few days ahead. This
page explains what short-term forecasting means in the context of OpenSTEF, how horizons
and lead times work, and how forecast frequency fits into a production workflow.

For probabilistic aspects of forecasts (quantiles, confidence intervals), see
:doc:`quantiles_and_confidence`. For choosing a model, see :doc:`model_selection`.

What Is Short-Term Forecasting?
--------------------------------

Short-term energy forecasting sits at the operational end of the forecasting spectrum.
Grid operators, energy traders, and balance-responsible parties need accurate predictions
of load and generation over the next minutes to days in order to dispatch assets, balance
supply and demand, and avoid costly imbalances. These forecasts are not strategic
planning tools — they feed directly into automated control systems and trading decisions,
often with latency requirements measured in seconds.

OpenSTEF is a Python library purpose-built for this operational context. It provides the
data structures, model abstractions, and workflow primitives needed to train, update, and
serve short-term forecasts at scale, without prescribing a particular deployment
architecture.

.. note:: [DIAGRAM: Timeline showing forecast horizons. A horizontal time axis runs left
   to right. The leftmost point is labelled "now (t₀)". Four coloured arrows extend
   rightward from t₀, representing the four common horizons: 15 min (intra-hour
   dispatch), 1 h (intra-day scheduling), 24 h (day-ahead market), and 48 h (extended
   day-ahead / balancing). Below each arrow the typical update frequency is shown:
   every 15 min for the 15-min horizon, every 15–30 min for the 1-h horizon, every
   hour for the 24-h horizon, and every 1–6 h for the 48-h horizon. A second axis
   below the main one shows "lead time" as the distance from t₀ to the target
   timestamp, illustrating that a single forecast run produces predictions at many
   lead times simultaneously.]

How Short-Term Differs from Long-Term Forecasting
--------------------------------------------------

Long-term forecasts (weeks to years) are primarily used for capacity planning and
infrastructure investment. They tolerate higher uncertainty, rely heavily on
climatological averages and economic growth models, and are typically produced once a
day or less frequently.

Short-term forecasts have fundamentally different requirements:

- **Accuracy over uncertainty tolerance.** A 5 % error in a 10-year capacity forecast
  is acceptable; the same error in a 15-minute dispatch forecast can trigger balancing
  penalties.
- **Recency matters.** The most recent observations — the last hour of metered load,
  the latest weather update — carry disproportionate weight. Models must be able to
  incorporate fresh data quickly.
- **Temporal resolution.** Short-term forecasts are produced at the same granularity
  as the control system: typically 15-minute or hourly intervals.
- **Continuous operation.** A long-term model might be retrained quarterly. A
  short-term model runs every 15 minutes and must degrade gracefully when inputs are
  late or missing (see :doc:`reliability_and_fallback`).

Horizons, Lead Times, and Update Frequency
-------------------------------------------

Three related but distinct concepts govern the temporal structure of a short-term
forecast.

**Horizon** is the furthest point in the future that a single forecast run covers. A
48-hour horizon means the model produces predictions for every 15-minute interval
between *now* and *now + 48 h*.

**Lead time** is the distance from the moment the forecast is produced to a specific
target timestamp within that horizon. If a forecast is produced at 09:00 and covers
09:15, 09:30, …, 33:00, then the lead times range from 15 minutes to 24 hours. Models
often perform differently at short versus long lead times: short lead times benefit from
recent observations, while long lead times rely more on calendar and weather patterns.

**Update frequency** (sometimes called the *forecast cycle*) is how often a new
forecast is produced. Producing a fresh 24-hour forecast every 15 minutes means that at
any given moment the system holds 96 overlapping forecast runs, each offset by 15
minutes. Consumers can always retrieve the most recently produced forecast for any
target timestamp.

In OpenSTEF, these concepts map directly to the ``LeadTime`` type and the
``horizons`` field on a forecasting configuration:

.. code-block:: python

   from datetime import timedelta
   from openstef.data_classes.lead_time import LeadTime
   from openstef.data_classes.forecasting_model import ForecastingModelConfig

   # Define the lead times you want the model to predict
   horizons = [
       LeadTime.from_string("PT15M"),   # 15 minutes ahead
       LeadTime.from_string("PT1H"),    # 1 hour ahead
       LeadTime.from_string("PT24H"),   # 24 hours ahead
       LeadTime.from_string("PT48H"),   # 48 hours ahead
   ]

   config = ForecastingModelConfig(
       horizons=horizons,
       quantiles=[...],  # see quantiles_and_confidence page
   )

   # Inspect the furthest horizon the model must cover
   print(config.max_horizon)  # LeadTime equivalent to PT48H

The ``LeadTime.from_string`` method accepts ISO 8601 duration strings (``PT15M``,
``PT1H``, ``PT24H``, ``PT48H``), making configurations readable and portable.

Versioned Forecasts and the ``available_at`` Column
----------------------------------------------------

A subtlety that distinguishes operational forecasting from offline modelling is
*forecast versioning*. Because forecasts are produced repeatedly, a dataset of
historical forecasts contains many predictions for the same target timestamp — one from
each forecast cycle. The ``available_at`` column in a ``TimeSeriesDataset`` records
when each prediction was produced, allowing you to reconstruct exactly what the model
knew at any point in time.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef.data_classes.time_series_dataset import TimeSeriesDataset

   # A small versioned dataset: two forecast cycles, each covering two steps
   data = pd.DataFrame(
       {
           "load": [105.2, 108.7, 104.9, 107.3],
           "available_at": pd.to_datetime([
               "2025-06-01 08:00", "2025-06-01 08:00",  # first cycle
               "2025-06-01 08:15", "2025-06-01 08:15",  # second cycle, 15 min later
           ], utc=True),
           "horizon": pd.to_timedelta(["PT15M", "PT30M", "PT15M", "PT30M"]),
       },
       index=pd.to_datetime([
           "2025-06-01 08:15", "2025-06-01 08:30",
           "2025-06-01 08:30", "2025-06-01 08:45",
       ], utc=True),
   )
   data.index.name = "timestamp"

   dataset = TimeSeriesDataset(data, sample_interval=timedelta(minutes=15))

   # Retrieve only the most recent version of each target timestamp
   latest = dataset.select_version()

   # Work with a specific lead time only
   one_step = dataset.select_horizon(LeadTime.from_string("PT15M"))

This versioning model is what makes it possible to perform honest backtesting: by
filtering on ``available_at``, you ensure that evaluation uses only information that
would have been available at prediction time, avoiding look-ahead bias.

Typical Horizon Configurations in Practice
-------------------------------------------

Different use cases call for different horizon configurations. The table below
summarises common patterns:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 40

   * - Use case
     - Horizon
     - Update frequency
     - Notes
   * - Intra-hour dispatch
     - 15 min – 1 h
     - Every 15 min
     - Relies heavily on recent metered load; weather less important
   * - Intra-day scheduling
     - 4 h – 12 h
     - Every 15–30 min
     - Balance of recency and weather signals
   * - Day-ahead market
     - 24 h – 36 h
     - Every 1 h
     - Weather forecasts become the dominant driver
   * - Extended day-ahead
     - 48 h
     - Every 1–6 h
     - Higher uncertainty; probabilistic outputs especially valuable

A single OpenSTEF model can cover multiple horizons simultaneously by including all
desired ``LeadTime`` values in its configuration. The library will train and evaluate
the model across each horizon, and the resulting ``TimeSeriesDataset`` will contain
predictions labelled by both target timestamp and lead time.

.. note::

   Forecast accuracy typically degrades with increasing lead time. When evaluating
   model performance, always report metrics separately per horizon rather than
   averaging across all lead times — a good 15-minute forecast and a poor 48-hour
   forecast can produce a misleadingly average aggregate score.

The Role of Temporal Resolution
---------------------------------

The ``sample_interval`` of a ``TimeSeriesDataset`` defines the granularity of both
input data and output predictions. OpenSTEF defaults to 15-minute intervals
(``timedelta(minutes=15)``), matching the standard settlement period used in many
European electricity markets. Hourly resolution is common for gas networks and some
distribution use cases.

Changing the resolution affects feature engineering significantly: a 15-minute model
can exploit within-hour load ramps that are invisible to an hourly model. See
:doc:`feature_engineering` for a detailed treatment of how temporal resolution
interacts with lag features and calendar encodings.

What Comes Next
----------------

With the core concepts of horizons, lead times, and update frequency established, the
natural next steps are:

- :doc:`quantiles_and_confidence` — how OpenSTEF expresses forecast uncertainty through
  quantile predictions, and how to interpret confidence intervals in an operational
  setting.
- :doc:`feature_engineering` — the predictors that drive short-term forecast accuracy,
  including weather variables, calendar features, and lag constructions.
- :doc:`model_selection` — guidance on choosing between the available forecasting
  models for different horizon and resolution combinations.
- :doc:`reliability_and_fallback` — how to keep a production forecasting system
  running when data feeds are late, models fail, or predictions fall outside expected
  bounds.