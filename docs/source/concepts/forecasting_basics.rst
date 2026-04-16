Short-Term Energy Forecasting
==============================

Short-term energy forecasting is the practice of predicting power load or generation
over intervals ranging from a few minutes to a few days ahead. This page explains what
short-term forecasting means in the context of OpenSTEF, why it matters for grid
operations, and how the key concepts of horizon, lead time, and forecast frequency
shape the way the library is designed.

What Is Short-Term Forecasting?
---------------------------------

A *forecast* is a prediction of a future value. In energy systems, the quantity being
predicted is typically electrical load (demand) or renewable generation at a specific
point in the grid — a substation, a feeder, or a portfolio of assets. Short-term
forecasting covers the window from the next few minutes out to roughly 48 hours ahead.
Beyond that window, the problem changes character: medium- and long-term forecasting
deals with seasonal planning, capacity investment, and tariff setting, where the
dominant drivers are economic growth, demographics, and climate trends rather than
today's weather or the current state of the grid.

Short-term forecasts are operationally critical. Grid operators use them to schedule
reserves, balance supply and demand in near-real-time markets, and decide when to
activate flexibility assets. A forecast that is 10 % too low at peak demand can trigger
unnecessary emergency measures; one that is 10 % too high wastes money on over-procured
reserves. The value of a good short-term forecast is therefore measured in direct
operational cost, not just statistical accuracy.

OpenSTEF is a Python library built specifically for this operational context. It
provides the modelling primitives — forecasters, feature pipelines, datasets, and
workflows — that practitioners need to build, train, and deploy short-term forecasting
systems at scale.

.. note:: [DIAGRAM: Timeline showing forecast horizons. A horizontal time axis runs
   from "now" (t=0) to t+48h. Four coloured bands are marked: 15-minute horizon
   (t+0 to t+0:15, updated every 15 min), 1-hour horizon (t+0 to t+1h, updated
   hourly), 24-hour day-ahead horizon (t+0 to t+24h, updated once or twice daily),
   and 48-hour horizon (t+0 to t+48h, updated daily). Each band is annotated with
   its typical use case: real-time balancing, intra-day trading, day-ahead market,
   and medium-term scheduling respectively. Lead time arrows show the gap between
   when the forecast is issued and the start of the predicted interval.]

Horizons and Lead Times
------------------------

Two terms appear throughout OpenSTEF's API and deserve precise definitions.

**Horizon** is the distance into the future that a forecast covers, measured from the
moment the forecast is produced. A 24-hour horizon means the model outputs predictions
for every time step in the next 24 hours.

**Lead time** is the time between when a forecast is *issued* and the specific future
time step being predicted. For a forecast issued at 08:00 that covers 08:15 through
08:00 the next day, the lead times range from 15 minutes to 24 hours. In OpenSTEF,
lead time is represented by the ``LeadTime`` type, which wraps a standard
``datetime.timedelta``:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime

   # A single lead time of one hour
   one_hour = LeadTime(timedelta(hours=1))

   # A set of lead times covering a 48-hour horizon at hourly resolution
   horizons = [LeadTime(timedelta(hours=h)) for h in range(1, 49)]

Lead time matters because the *information available* to the model changes with it.
At a 15-minute lead time you can use very recent measurements; at a 24-hour lead time
those measurements are stale and you must rely on weather forecasts, calendar features,
and historical patterns instead. This is why OpenSTEF's ``Forecaster`` base class
accepts a ``horizons`` list rather than a single scalar: different lead times may
require different feature sets or even different model architectures.

Multi-Horizon vs. Single-Horizon Models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF distinguishes between two modelling strategies:

- **Single-horizon models** train one model per lead time. Each model is optimised for
  exactly one prediction distance and can use the full feature set appropriate for that
  distance. Linear models typically fall into this category because they cannot handle
  the conditional or missing features that arise when the same model must serve many
  different lead times.

- **Multi-horizon models** train a single model that predicts across all configured lead
  times simultaneously. Tree-based models such as XGBoost and LightGBM handle this
  well because they can learn to ignore irrelevant features for a given lead time.
  Multi-horizon models are more efficient to train and deploy, and they can share
  statistical strength across lead times.

The ``Forecaster`` abstract base class in ``openstef_core`` is designed for the
multi-horizon case. When you configure a forecaster, you pass the full list of lead
times you need:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_core.forecasters import XGBForecaster  # example tree-based forecaster

   forecaster = XGBForecaster(
       horizons=[
           LeadTime(timedelta(minutes=15)),
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=24)),
           LeadTime(timedelta(hours=48)),
       ],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )

The ``max_horizon`` property is a convenience that returns the furthest lead time in
the list — useful when preparing training data to ensure you include enough historical
context.

Forecast Frequency and Resolution
-----------------------------------

Two more concepts are worth separating clearly.

**Resolution** is the granularity of individual predictions — the time step between
consecutive forecast values. A resolution of 15 minutes means the model outputs one
value every quarter-hour across the horizon. Resolution is determined by the resolution
of your input time series data.

**Forecast frequency** (or *update frequency*) is how often a new forecast is issued.
A day-ahead forecast might be issued once every 24 hours, while a real-time balancing
forecast might be reissued every 15 minutes as new measurements arrive. These are
independent dimensions: you can have a 24-hour horizon forecast that is updated every
hour, producing a rolling window of predictions.

In practice, the combination of horizon, resolution, and update frequency defines the
operational regime:

+--------------------+------------+------------------+----------------------------+
| Use case           | Horizon    | Resolution       | Update frequency           |
+====================+============+==================+============================+
| Real-time balance  | 15 min     | 15 min           | Every 15 min               |
+--------------------+------------+------------------+----------------------------+
| Intra-day trading  | 1–6 h      | 15 min or 1 h    | Hourly                     |
+--------------------+------------+------------------+----------------------------+
| Day-ahead market   | 24–36 h    | 15 min or 1 h    | Once or twice daily        |
+--------------------+------------+------------------+----------------------------+
| Medium-term plan   | 48 h       | 1 h              | Daily                      |
+--------------------+------------+------------------+----------------------------+

OpenSTEF does not enforce a particular update frequency — that is the responsibility of
the scheduling layer that calls the library. What the library does enforce is internal
consistency: the ``horizons`` you configure must be compatible with the resolution of
the dataset you provide for training and prediction.

Why Short-Term Forecasting Is Hard
------------------------------------

Long-term energy forecasting can rely on slowly-changing structural variables. Short-
term forecasting must contend with rapid, hard-to-predict fluctuations:

- **Weather sensitivity.** Load and solar generation respond strongly to temperature,
  cloud cover, and wind speed, all of which are uncertain even a few hours ahead.
- **Behavioural patterns.** Human activity creates sharp intra-day and intra-week
  cycles that interact with weather in non-linear ways (e.g., cold Monday mornings
  produce a different load shape than cold Saturday mornings).
- **Data latency.** Measurements from smart meters and SCADA systems arrive with
  delays and occasional gaps. At short lead times, the model must work with the most
  recent *available* data, which may be several minutes old.
- **Non-stationarity.** The underlying load profile changes over months and years as
  new loads connect, buildings are retrofitted, and electric vehicles proliferate.
  Models need periodic retraining to stay accurate.

OpenSTEF addresses these challenges through its feature engineering pipeline (which
encodes weather, calendar, and lag features automatically) and its support for
probabilistic forecasts via quantiles, which communicate uncertainty to downstream
decision-makers rather than hiding it behind a single point estimate.

.. note::

   Probabilistic forecasts — where the model outputs a distribution of possible future
   values rather than a single number — are particularly valuable at short horizons
   because uncertainty is asymmetric and operationally consequential. See
   :doc:`quantiles_and_confidence` for a full treatment of how OpenSTEF represents and
   produces probabilistic forecasts.

Putting It Together: A Minimal Example
----------------------------------------

The following snippet shows how the horizon and resolution concepts map directly onto
OpenSTEF's API. It creates a synthetic dataset, configures a forecasting model with
two horizons, and runs a training workflow:

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_core.testing import create_synthetic_forecasting_dataset
   from openstef_core.types import LeadTime, Q
   from openstef_core.models import ForecastingModel
   from openstef_core.feature_engineering import FeaturePipeline
   from openstef_core.storage import LocalModelStorage
   from openstef_core.workflows import CustomForecastingWorkflow

   # 1. Create synthetic training data at 15-minute resolution
   dataset = create_synthetic_forecasting_dataset(
       resolution=timedelta(minutes=15),
       n_periods=4 * 24 * 90,  # 90 days of quarter-hourly data
   )

   # 2. Define the horizons we want to forecast
   horizons = [
       LeadTime(timedelta(hours=1)),   # intra-day
       LeadTime(timedelta(hours=24)),  # day-ahead
   ]

   # 3. Configure the forecasting model
   model = ForecastingModel(
       horizons=horizons,
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       feature_pipeline=FeaturePipeline.default(),
   )

   # 4. Train via a workflow
   storage = LocalModelStorage(Path("./models"))
   workflow = CustomForecastingWorkflow(model=model, storage=storage)
   workflow.train(dataset)

.. note::

   This example uses ``create_synthetic_forecasting_dataset`` from
   ``openstef_core.testing``, which generates realistic-looking load data without
   requiring a live data connection. Replace it with your own
   ``VersionedTimeSeriesDataset`` when working with real measurements.

Relationship to Other Concepts
--------------------------------

Short-term forecasting as described here is the foundation on which the rest of the
OpenSTEF concepts build:

- The features that make short-horizon forecasting possible — weather variables, lag
  transforms, calendar encodings — are covered in :doc:`feature_engineering`.
- The probabilistic output format (quantiles and confidence intervals) that makes
  forecasts actionable under uncertainty is explained in
  :doc:`quantiles_and_confidence`.
- What happens when a model fails to produce a forecast in production — fallback
  strategies and reliability mechanisms — is described in
  :doc:`reliability_and_fallback`.