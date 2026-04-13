Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was designed with a concrete set of real-world problems in mind. This page describes the most common use cases the library supports, what distinguishes each one technically, and how to configure OpenSTEF appropriately for each scenario.

.. mermaid:: diagrams/user_guide/use_cases_diagram_1.mmd

Introduction
------------

All six use cases described here share the same fundamental OpenSTEF workflow: prepare a time-series dataset, configure a forecaster with appropriate quantiles and horizons, train, and predict. What differs between them is the **aggregation level** of the measurement point, the **accuracy metric** that matters most, the **external features** that carry predictive signal, and the **downstream consumer** of the forecast. Getting these details right for your specific use case is what separates a working proof-of-concept from a production-grade forecast.

.. note::

   OpenSTEF is a Python library. It provides the forecasting components — models, feature engineering, pipelines — but does not prescribe how you schedule jobs, store results, or expose forecasts to consumers. See :doc:`deployment` for patterns that wire the library into a production system.


Congestion Management Forecasts
--------------------------------

Congestion management is the original motivation for OpenSTEF. A distribution system operator (DSO) must anticipate when a transformer or cable will be loaded beyond its rated capacity so that demand-response actions — calling customers, curtailing generation, or activating flexibility contracts — can be triggered in advance.

**What makes this use case distinctive:**

- The measurement point is often a single substation or medium-voltage (MV) substation room (MSR), so the load signal can be highly variable and noisy.
- Accuracy near **peak load** matters far more than accuracy during low-load periods. A model that is excellent on average but misses the top-5% of load events is not useful here.
- Probabilistic forecasts are essential: the operator needs to know not just the expected load but also the probability that the thermal limit will be exceeded.

**Key metrics:** rMAE at the 50th quantile during peak periods, precision/recall of threshold-crossing events, rCRPS.

**Recommended configuration:** Use wide quantile coverage (e.g., 0.1 through 0.9) so that the upper tail of the distribution is well-characterised. Shorter horizons (1–24 hours) are most actionable for demand response.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # Congestion forecast: wide quantile range to capture peak uncertainty
   forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.1),
           Quantile(0.25),
           Quantile(0.5),
           Quantile(0.75),
           Quantile(0.9),
           Quantile(0.95),
       ],
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=4)),
           LeadTime(timedelta(hours=24)),
       ],
       hyperparams=XGBoostHyperParams(n_estimators=200, max_depth=6),
   )

   forecaster.fit(training_data)
   predictions = forecaster.predict(test_data)

The upper quantiles (0.9, 0.95) directly answer the question "what is the worst-case load we should plan for?" — which is exactly what a congestion management system needs to decide whether to issue a flexibility call.


Free Space Estimation
---------------------

Free space estimation is the inverse of congestion forecasting: rather than predicting absolute load, the goal is to estimate the **remaining capacity** on a cable or transformer — the headroom available before a thermal limit is reached.

In practice this is derived from a congestion forecast: ``free_space = rated_capacity - predicted_load``. However, the use case has a different operational character. Free space estimates are typically consumed by systems that want to offer capacity to new connections, EV charging sessions, or flexibility markets. The question is not "will we overload?" but "how much additional load can we safely absorb right now?"

**What makes this use case distinctive:**

- The forecast consumer is often an automated system (e.g., a smart charging controller) rather than a human dispatcher, so the output format and latency requirements may differ.
- Accuracy at **low-load periods** matters more here than at peaks, because that is when free space is largest and most likely to be allocated.
- A conservative (lower-quantile) estimate of free space is safer than an optimistic one: it is better to under-allocate capacity than to cause an overload.

**Recommended configuration:** Use the same forecaster as congestion management, but consume the **lower quantiles** of the load forecast to derive a conservative free-space estimate.

.. code-block:: python

   import pandas as pd

   rated_capacity_mw = 10.0  # transformer rating

   # predictions is a DataFrame with columns named by quantile, e.g. "q0.1", "q0.5", "q0.9"
   # Use the upper load quantile to get a conservative (lower) free-space estimate
   free_space = rated_capacity_mw - predictions["q0.9"]
   free_space = free_space.clip(lower=0.0)  # capacity cannot be negative


Transport Forecasts
-------------------

Transport forecasts serve a different operational purpose: they are exchanged between network operators at different voltage levels to coordinate capacity planning. A DSO like Alliander provides transport forecasts to a transmission system operator (TSO) like TenneT, and simultaneously receives forecasts from its own large customers.

**What makes this use case distinctive:**

- Measurement points are typically **medium-aggregation** — a high-voltage/medium-voltage (HV/MV) substation serving many customers — which makes the load signal smoother and more predictable than a single MSR.
- Accuracy is required **across the entire forecast horizon**, not just at peaks. The TSO uses the full profile for scheduling generation and transmission capacity.
- Some operators require transport forecasts **split by component** (solar generation, wind generation, residual load), which requires separate models per component that are later summed.

**Key metrics:** rMAE across the full forecast horizon.

**Recommended configuration:** A balanced quantile set and longer horizons. The GBLinear forecaster can be a good fit here when linear relationships dominate at high aggregation levels.

.. code-block:: python

   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   # Transport forecast: longer horizons, balanced quantiles
   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=6)),
           LeadTime(timedelta(hours=24)),
           LeadTime(timedelta(hours=48)),
       ],
       hyperparams=GBLinearHyperParams(
           learning_rate=0.05,
           reg_alpha=0.1,
           reg_lambda=1.0,
       ),
   )

For split-component transport forecasts, train one forecaster per component (solar, wind, residual) on the corresponding measured component time series, then sum the median predictions for the total transport forecast.


Grid Loss Forecasts
-------------------

Grid losses — the energy dissipated as heat in cables and transformers during transmission — must be purchased on the energy market to balance the grid. Forecasting losses accurately reduces the cost of this procurement.

**What makes this use case distinctive:**

- Grid losses are computed at a **highly aggregated** level (entire grid sections or the full network), so the signal is dominated by system-wide temporal patterns: time of day, day of week, seasonal cycles.
- Weather features (temperature, irradiance) have **less predictive value** here than in substation-level forecasts, because individual weather effects average out at high aggregation.
- The error metric is **cost-weighted**: an overestimate on a high-price day is more expensive than the same overestimate on a low-price day. The model should be optimised to minimise total procurement cost, not just raw forecast error.

**Key metrics:** rMAE, total error cost (forecast error × market price).

**Recommended configuration:** Include market price as a feature or use it as an error weight during training. Temporal features (hour, weekday, month) carry most of the signal.

.. code-block:: python

   # Grid loss forecast: include market price as a feature in your training DataFrame
   # training_data should have columns: load_mw, price_eur_mwh, plus standard
   # time-based features (hour_of_day, day_of_week, etc.)

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=24)),
       ],
       hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=4),
   )

   forecaster.fit(training_data)

.. note::

   Cost-weighted training (weighting samples by market price) requires a custom training loop. The standard ``fit()`` call uses uniform sample weights. Implementing price-weighted loss is an extension point — see the ``Forecaster`` base class for the interface.


District Heating Demand
-----------------------

District heating is a non-electrical use case: the goal is to forecast **thermal demand** (heat consumption) in a district heating network so that the heat plant can be dispatched efficiently. OpenSTEF's time-series forecasting machinery transfers directly to this domain because thermal demand exhibits the same kinds of temporal patterns as electrical load — daily cycles, weather sensitivity, holiday effects.

**What makes this use case distinctive:**

- The target variable is heat demand (MW thermal) rather than electrical load, but the modelling approach is identical.
- **Outdoor temperature** is the dominant weather feature; irradiance and wind speed matter less.
- The forecast horizon is typically short (1–12 hours) to support plant dispatch decisions.
- This use case sits outside the DSO/TSO domain, demonstrating that OpenSTEF is a general energy forecasting library, not an electricity-only tool.

.. code-block:: python

   # District heating: temperature is the primary weather feature
   # training_data columns: heat_demand_mw, temperature_c, hour_of_day, day_of_week, ...

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[
           LeadTime(timedelta(hours=1)),
           LeadTime(timedelta(hours=4)),
           LeadTime(timedelta(hours=12)),
       ],
       hyperparams=XGBoostHyperParams(n_estimators=100, max_depth=5),
   )

   forecaster.fit(training_data)
   heat_forecast = forecaster.predict(forecast_input)


MV Route Congestion with Topology Awareness
-------------------------------------------

MV route congestion is the most technically complex use case. A medium-voltage route is a chain of cables connecting multiple substations; congestion can occur at any segment along the route. Forecasting whether a specific cable segment will be overloaded requires knowing not just the aggregate load at the route head, but how that load is distributed across the network topology.

This is where `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_ integrates with OpenSTEF. The workflow is:

1. **Forecast load** at each measurement point along the MV route using OpenSTEF.
2. **Run a power flow calculation** using power-grid-model with the forecasted loads as inputs.
3. **Extract cable loading** (current as a fraction of rated capacity) for each segment from the power flow result.
4. **Flag congestion** where loading exceeds a threshold (e.g., 80% of rated current).

.. mermaid:: diagrams/user_guide/use_cases_diagram_2.mmd

**What makes this use case distinctive:**

- A single OpenSTEF forecaster is trained per measurement point on the route; the topology integration happens *after* forecasting.
- The power flow calculation propagates uncertainty: errors in individual load forecasts combine to produce uncertainty in cable loading. Running power flow on multiple quantile scenarios (e.g., the 10th, 50th, and 90th quantile forecasts) gives a probabilistic view of congestion risk.
- Network topology changes (switching operations, new connections) must be reflected in the power-grid-model input, not in the OpenSTEF model.

.. code-block:: python

   # Step 1: forecast load at each measurement point
   route_forecasts = {}
   for point_id, (forecaster, input_data) in route_forecasters.items():
       route_forecasts[point_id] = forecaster.predict(input_data)

   # Step 2: assemble power-grid-model input from median forecasts
   # (power-grid-model integration is outside OpenSTEF's scope;
   #  this illustrates the handoff pattern)
   import pandas as pd

   load_injections = pd.DataFrame(
       {point_id: fc["q0.5"] for point_id, fc in route_forecasts.items()}
   )

   # Step 3: run power flow (power-grid-model API)
   # pgm_output = power_flow_model.calculate_power_flow(load_injections)

   # Step 4: repeat for q0.9 to assess worst-case congestion risk
   load_injections_p90 = pd.DataFrame(
       {point_id: fc["q0.9"] for point_id, fc in route_forecasts.items()}
   )

.. note::

   OpenSTEF provides the load forecasts; power-grid-model provides the network physics. The two libraries are complementary and independently maintained. Consult the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for the power flow API.


Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case.

.. list-table:: Use case configuration summary
   :header-rows: 1
   :widths: 22 20 20 20 18

   * - Use case
     - Aggregation level
     - Key metric
     - Recommended quantiles
     - Primary features
   * - Congestion management
     - Low (single MSR)
     - rMAE@peak, rCRPS
     - 0.1 – 0.95
     - Weather, calendar, lag
   * - Free space estimation
     - Low (single MSR)
     - rMAE at low load
     - 0.1 – 0.9 (consume upper)
     - Same as congestion
   * - Transport
     - Medium (HV/MV substation)
     - rMAE full horizon
     - 0.1, 0.5, 0.9
     - Calendar, lag, components
   * - Grid loss
     - High (grid section)
     - rMAE, cost-weighted error
     - 0.1, 0.5, 0.9
     - Temporal, market price
   * - District heating
     - Medium (district)
     - rMAE
     - 0.1, 0.5, 0.9
     - Temperature, calendar
   * - MV route congestion
     - Low (per-segment)
     - Cable loading exceedance
     - 0.1, 0.5, 0.9 per point
     - Weather, lag + topology


Related Pages
-------------

- :doc:`data_integration` — how to feed measurement data from InfluxDB, S3, or Databricks into the forecasting pipeline for any of these use cases.
- :doc:`deployment` — patterns for scheduling and operationalising forecasts in production environments.
- :doc:`logging` — configuring log levels and structured logging when running multiple forecasters in parallel (common in MV route congestion workflows).