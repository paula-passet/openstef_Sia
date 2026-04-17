Short-Term Energy Forecasting
==============================

This page explains what short-term energy forecasting is, why it matters for grid
operations, and how the concepts of *horizon*, *lead time*, and *update frequency*
shape the way OpenSTEF models are configured and used. If you are new to the library,
reading this page first will make the rest of the documentation much easier to follow.

What Is Short-Term Forecasting?
--------------------------------

Short-term energy forecasting is the practice of predicting electrical load or
generation over a window that spans minutes to a few days ahead. The defining
characteristic is that the forecast must be *actionable in near real-time*: grid
operators, balance responsible parties, and trading desks all need predictions that
are fresh enough to influence decisions that are minutes or hours away.

This is fundamentally different from medium- or long-term forecasting, which projects
demand weeks, months, or years into the future for capacity planning and investment
decisions. Long-term forecasts tolerate coarser resolution and larger uncertainty
bands because the decisions they inform are themselves coarse. Short-term forecasts,
by contrast, must be precise enough to schedule individual assets, commit reserves,
and settle imbalance markets — tasks that are sensitive to errors measured in
megawatts and minutes.

OpenSTEF is a library purpose-built for the short-term regime. Its data structures,
model abstractions, and pipeline utilities all assume that you are working with
time series sampled at sub-hourly to hourly resolution and that forecasts need to be
regenerated frequently as new observations arrive.

.. note::

   Long-term and short-term forecasting are not competing approaches — they answer
   different questions. A utility might use a long-term model to plan network
   reinforcement years in advance while simultaneously running OpenSTEF to balance
   the grid today.

Key Concepts: Horizon, Lead Time, and Update Frequency
-------------------------------------------------------

Three terms appear throughout the OpenSTEF API and documentation. Understanding them
precisely will prevent confusion when configuring models.

**Horizon (or lead time)**
   The distance in time between the moment a forecast is *issued* and the moment it
   is *valid for*. A horizon of 24 hours means the model is predicting what will
   happen 24 hours from now. In OpenSTEF, horizons are represented by the
   ``LeadTime`` type, which wraps a standard ``datetime.timedelta``.

**Available-at time**
   The timestamp at which a forecast becomes available — i.e., when the model
   finished computing it. This is distinct from the valid time of the forecast.
   OpenSTEF's ``ForecastDataset`` tracks both dimensions explicitly, which matters
   when you need to reconstruct what information was available at any historical
   point in time (for backtesting, for example).

**Update frequency**
   How often a new forecast run is triggered. A model might produce a 48-hour
   forecast every 15 minutes as new SCADA measurements arrive, or it might produce
   a day-ahead forecast once per hour. Update frequency is an operational concern
   rather than a model parameter, but it interacts with horizon: there is little
   value in updating a 48-hour forecast every 15 seconds.

.. note::

   [DIAGRAM: Timeline showing forecast horizons (15min, 1h, 24h, 48h) with lead times and update frequency. The horizontal axis is wall-clock time. Four horizontal arrows of increasing length originate from a common "now" point, labelled 15 min, 1 h, 24 h, and 48 h. Below the axis, vertical tick marks indicate typical update frequencies for each horizon: every 15 min for the short horizons, every 15–60 min for day-ahead, and every 1–4 h for the 48 h horizon. An "available_at" marker sits slightly to the left of "now" to illustrate data latency.]

Typical Horizon Ranges in Practice
------------------------------------

The table below summarises the horizons most commonly encountered in grid operations
and the decisions they support.

.. list-table::
   :header-rows: 1
   :widths: 15 20 30 35

   * - Horizon
     - Typical resolution
     - Use case
     - Update frequency
   * - 15 min
     - 15 min
     - Frequency regulation, real-time dispatch
     - Every 15 min or faster
   * - 1 h
     - 15 min
     - Intraday trading, reserve activation
     - Every 15–30 min
   * - 24 h
     - 15 min or 1 h
     - Day-ahead market bidding
     - Every 15–60 min
   * - 48 h
     - 15 min or 1 h
     - Maintenance scheduling, reserve planning
     - Every 1–4 h

None of these ranges are hard limits. OpenSTEF accepts any ``timedelta`` as a horizon,
so you can configure a 6-hour or 36-hour horizon just as easily as the canonical
values above.

How OpenSTEF Represents Horizons
----------------------------------

In the library, a horizon is expressed as a ``LeadTime`` value — a thin wrapper
around ``datetime.timedelta`` that carries semantic meaning in the API. When you
configure a forecaster, you pass a list of ``LeadTime`` objects to declare which
horizons the model should learn to predict.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime

   # Define the horizons you care about
   horizon_15min = LeadTime(timedelta(minutes=15))
   horizon_1h    = LeadTime(timedelta(hours=1))
   horizon_24h   = LeadTime(timedelta(hours=24))
   horizon_48h   = LeadTime(timedelta(hours=48))

   horizons = [horizon_15min, horizon_1h, horizon_24h, horizon_48h]

Once a model has been trained and has produced a ``ForecastDataset``, you can
retrieve or filter predictions for a specific horizon:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   # Assume `forecast_ds` is a ForecastDataset returned by model.predict(...)
   # Inspect which horizons are present
   print(forecast_ds.horizons())

   # Work with only the 24-hour horizon
   day_ahead = forecast_ds.filter_by_lead_time(lead_time=horizon_24h)

   # Convert to a pandas DataFrame for downstream processing
   df = day_ahead.to_pandas()

The ``filter_by_lead_time`` and ``select_horizon`` methods make it straightforward
to slice a multi-horizon forecast result without any manual index manipulation.

Single-Horizon vs. Multi-Horizon Models
-----------------------------------------

OpenSTEF supports two modelling strategies, and the right choice depends on the
horizons you need and the features available at each horizon.

**Single-horizon models** train a separate model for each lead time. This is the
simpler approach and works well when the feature set changes significantly between
horizons (for example, weather forecast accuracy degrades at longer lead times, so
you might use different feature sets for 1-hour and 48-hour models).

**Multi-horizon models** train a single model that predicts across all configured
lead times simultaneously. This is more efficient when the horizons share most of
their features and when the model architecture can naturally handle the varying
prediction distances — gradient-boosted tree models such as XGBoost are well suited
to this pattern. Linear models, by contrast, are generally restricted to a single
horizon because they cannot handle the conditional feature structure that
multi-horizon data introduces.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime
   from openstef_models.models.forecasting.constant_median_forecaster import (
       ConstantMedianForecaster,
       ConstantMedianForecasterHyperParams,
   )

   # A single-horizon forecaster configured for day-ahead prediction
   forecaster = ConstantMedianForecaster(
       horizons=[LeadTime(timedelta(hours=24))],
       hyperparams=ConstantMedianForecasterHyperParams(),
   )

   # fit() and predict() follow the same interface regardless of horizon count
   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)

.. note::

   ``ConstantMedianForecaster`` is used here as a minimal, self-contained example.
   Real deployments typically use gradient-boosted or neural-network forecasters.
   The interface is identical regardless of the underlying algorithm.

Why Short-Term Forecasting Is Hard
------------------------------------

Several properties of the short-term regime make it genuinely challenging compared
to longer horizons:

- **Non-stationarity at short scales.** Load patterns shift with weather, human
  behaviour, and economic activity in ways that are difficult to capture with a
  single static model. A Monday morning in January looks very different from a
  Sunday afternoon in August, even at the same clock time.

- **Data latency.** Measurements from smart meters and SCADA systems arrive with
  delays ranging from seconds to several minutes. A model predicting 15 minutes
  ahead must account for the fact that the most recent observation it can use may
  already be 5 minutes old. OpenSTEF's ``available_at`` metadata is designed
  specifically to handle this: the library tracks when each data point became
  available, not just when it was measured.

- **Forecast refresh rate.** Producing a fresh forecast every 15 minutes across
  hundreds of grid nodes is computationally demanding. OpenSTEF's batching
  abstractions help amortise this cost.

- **Uncertainty quantification.** A point forecast is rarely sufficient for
  operational decisions. Grid operators need to know not just the expected load but
  also the range of plausible outcomes. See :doc:`quantiles_and_confidence` for how
  OpenSTEF handles probabilistic forecasts.

The Role of Features
---------------------

Short-term forecasts are only as good as the features fed into the model. Weather
variables (temperature, irradiance, wind speed) are the most important external
drivers for most grid nodes. Calendar features — hour of day, day of week, public
holidays — capture the rhythmic patterns in human behaviour. Lag features encode
recent history and are especially valuable at short horizons where the autocorrelation
of load is high.

Feature engineering is a large topic in its own right. See
:doc:`feature_engineering` for a detailed treatment of which predictors matter most
and how OpenSTEF's preprocessing pipeline constructs them.

Relationship to Other Concepts
--------------------------------

Short-term forecasting in OpenSTEF does not exist in isolation. Several related
concepts build directly on the foundations described here:

- **Probabilistic forecasts** — Rather than a single predicted value, OpenSTEF
  produces a distribution of outcomes expressed as quantiles. See
  :doc:`quantiles_and_confidence`.

- **Component splitting** — Aggregate load can be decomposed into sub-components
  (solar, wind, base load) before forecasting. See :doc:`component_splitting`.

- **Reliability and fallback** — When a model fails or produces implausible output,
  OpenSTEF's fallback mechanisms keep operations running. See
  :doc:`reliability_and_fallback`.

- **Meta-ensembles** — Multiple models can be combined to improve accuracy and
  robustness across different horizon ranges. See :doc:`meta_ensembles`.