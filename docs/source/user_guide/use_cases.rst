Use Cases
=========

OpenSTEF is a general-purpose short-term energy forecasting library. While its origins lie in congestion
management for distribution system operators (DSOs), the library has grown to support a broad range of
forecasting applications across the energy domain. This page describes the most common use cases,
explains what makes each one distinct, and shows how to configure OpenSTEF for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

.. note::

   All use cases described here are driven by the same underlying library API. The differences lie in
   how you configure the ``ForecastingWorkflowConfig``, which quantiles you request, and what
   post-processing you apply to the probabilistic output.


Overview
--------

The table below summarises the six use cases at a glance.

.. list-table::
   :header-rows: 1
   :widths: 22 20 20 38

   * - Use Case
     - Aggregation Level
     - Key Metric
     - Primary Driver
   * - Congestion Management
     - Low–high (variable)
     - rMAE@peak, rCRPS
     - Peak load accuracy
   * - Free Space Estimation
     - Low (asset level)
     - rMAE@peak
     - Remaining capacity headroom
   * - Grid Losses
     - High (system level)
     - Cost-weighted rMAE
     - Market price optimisation
   * - Transport Forecasts
     - Medium
     - rMAE
     - Overall horizon accuracy
   * - District Heating
     - Medium–high
     - rMAE
     - Thermal demand patterns
   * - MV Route Congestion
     - Low (route level)
     - rMAE@peak, rCRPS
     - Topology-aware peak detection


Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case in OpenSTEF. Grid operators use these
forecasts to identify when a transformer or cable is likely to exceed its rated capacity, and to
trigger mitigation actions — such as calling customers in advance to reduce load — before an overload
occurs.

The defining challenge here is **peak accuracy at low aggregation levels**. A substation serving a
handful of industrial customers or a medium-voltage substation room (MSR) can exhibit highly
unpredictable behaviour; a single large customer switching a process on or off dominates the signal.
OpenSTEF addresses this by emphasising high-quantile accuracy and probabilistic output: rather than
predicting a single load value, you request upper quantiles (e.g. 0.9, 0.95) that represent the
plausible worst-case loading, which is what the grid operator actually needs to act on.

**When to use this configuration:**

- You are forecasting load at a substation, cable, or individual customer connection.
- You need to detect peak moments reliably, even at the cost of some average-case accuracy.
- You want probabilistic output to drive threshold-based alerting.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow import ForecastingWorkflowConfig, ForecastingWorkflow

   # Congestion management: emphasise upper quantiles for peak detection
   config = ForecastingWorkflowConfig(
       model_id="substation_hv_mv_001",
       model="xgboost",
       horizons=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT6H"),
           LeadTime.from_string("PT24H"),
       ],
       # Include high quantiles — these drive congestion alerts
       quantiles=[Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       rolling_aggregate_features=["mean", "max"],
   )

   workflow = ForecastingWorkflow(config=config, model_id=config.model_id)

The 0.9 and 0.95 quantile forecasts give the operator a conservative upper bound on expected loading.
Comparing these against the asset's rated capacity directly yields a congestion risk signal.


Free Space Estimation
---------------------

Free space estimation is a close relative of congestion management, but the question is inverted:
instead of asking *"will this asset overload?"*, you ask *"how much spare capacity is available?"*.
This headroom figure is used to decide whether new connections (e.g. solar installations, EV charging
points, heat pumps) can be accepted on a given part of the grid without reinforcement.

The output is typically derived from the **lower quantiles** of the load forecast. If even the
pessimistic (high-load) scenario leaves headroom below the rated capacity, a new connection can be
approved with confidence. Conversely, if the upper quantile already exceeds the rated capacity, the
operator knows reinforcement is needed regardless of the new connection.

**When to use this configuration:**

- You are evaluating connection requests or planning grid reinforcement.
- You need a conservative estimate of *minimum* available headroom over a planning horizon.
- Your forecast horizon is longer (days to weeks) rather than intra-day.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow import ForecastingWorkflowConfig

   # Free space: wide quantile band to bound the headroom estimate
   config = ForecastingWorkflowConfig(
       model_id="cable_ring_south_042",
       model="xgboost",
       horizons=[
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("P3D"),
       ],
       # Wide band: upper quantile = worst-case load, lower = best-case load
       quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       rolling_aggregate_features=["mean", "max", "min"],
   )

Post-processing then computes ``rated_capacity - forecast[Q(0.95)]`` as the conservative free space
estimate. A negative value flags the asset for review.


Grid Loss Forecasts
-------------------

Grid losses are the difference between energy injected into the network and energy consumed by
end-users — the remainder is dissipated as heat in cables and transformers. Forecasting losses
accurately matters because grid operators must purchase this energy on the wholesale market in
advance. Buying too little means expensive last-minute top-ups; buying too much means selling surplus
at a loss.

At the high aggregation levels typical of grid loss forecasting, weather predictors have less
influence than at the substation level. Instead, **temporal and cyclic patterns** (time of day, day
of week, seasonal trends) dominate, and the model benefits from knowing current market prices so that
forecast errors can be weighted by their financial cost.

**When to use this configuration:**

- You are forecasting system-level or regional energy losses, not individual asset load.
- You want to minimise the financial cost of forecast errors, not just their magnitude.
- You have access to market price data (e.g. EPEX spot prices) to use as a feature.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow import ForecastingWorkflowConfig

   # Grid losses: include market price as a feature; linear model often performs
   # well at high aggregation levels where relationships are more linear
   config = ForecastingWorkflowConfig(
       model_id="grid_losses_region_north",
       model="gblinear",          # Linear model suits high-aggregation patterns
       horizons=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT24H"),
       ],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       temperature_column="temperature_2m",
       energy_price_column="EPEX_NL",   # Market price drives cost-weighted errors
       rolling_aggregate_features=["mean", "median"],
   )

.. note::

   The ``gblinear`` model is often a strong choice for grid losses because the relationship between
   system load and losses is approximately quadratic — a linear model in log-space or with engineered
   squared features can capture this well while remaining interpretable.


Transport Forecasts
-------------------

Transport forecasts describe the total energy flow across a network boundary — for example, the
aggregate load that a regional DSO draws from the national transmission grid. These forecasts serve
two audiences simultaneously: the DSO's own planning teams, and the upstream transmission system
operator (TSO) who needs to balance the national grid.

Unlike congestion management, transport forecasts must be accurate **across the entire forecast
horizon**, not just at peak moments. The aggregation level is medium: individual customer noise
averages out, but regional weather effects and large industrial loads still matter. Some operators
also require the forecast to be decomposed into components — solar generation, wind generation, and
residual demand — which requires separate component models that are then combined.

**When to use this configuration:**

- You are reporting planned energy usage to an upstream TSO or receiving forecasts from downstream customers.
- You need reliable accuracy across all hours, not just peaks.
- Optionally, you need component-level breakdowns (solar, wind, other).

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow import ForecastingWorkflowConfig

   # Transport forecast: balanced quantiles, medium horizon, all weather features
   config = ForecastingWorkflowConfig(
       model_id="transport_region_central",
       model="xgboost",
       horizons=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT6H"),
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("P3D"),
       ],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

For component-level transport forecasts, train separate ``ForecastingWorkflow`` instances for solar
and wind generation, then subtract their median forecasts from the total transport forecast to derive
the residual demand component.


District Heating Demand
-----------------------

District heating is a non-electricity use case: the target variable is **thermal demand** (heat
consumed by a district heating network) rather than electrical load. Despite this difference, the
forecasting problem is structurally identical — you have a time series of measured demand, weather
covariates, and a need to predict future demand over a short horizon.

OpenSTEF's library design makes it straightforward to apply to thermal demand. The key differences
from electricity forecasting are:

- **Temperature is the dominant predictor.** Heating demand drops sharply as outdoor temperature
  rises above a threshold (typically around 15–18 °C). Including a heating degree day (HDD) feature
  or a non-linear temperature term is often beneficial.
- **Solar radiation matters less** (unless the network also serves cooling demand in summer).
- **Seasonal patterns are stronger** and more predictable than in electricity forecasting.

**When to use this configuration:**

- You are forecasting heat demand for a district heating network or individual heat substation.
- Your measured variable is thermal power (MW) or energy (MWh) rather than electrical load.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow import ForecastingWorkflowConfig

   # District heating: temperature-heavy feature set, longer horizons useful
   config = ForecastingWorkflowConfig(
       model_id="district_heating_amsterdam_west",
       model="xgboost",
       horizons=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("P3D"),
       ],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       temperature_column="temperature_2m",
       # Radiation less important for heating; wind contributes to heat loss
       wind_speed_column="wind_speed_80m",
       rolling_aggregate_features=["mean", "median", "max"],
   )

.. note::

   District heating demand often shows a sharp non-linear response to temperature. If forecast
   accuracy is poor in mild weather (the transition season), consider engineering a heating degree
   day feature — ``max(0, threshold_temp - outdoor_temp)`` — and passing it as an additional
   input column.


MV Route Congestion with Topology Awareness
-------------------------------------------

Medium-voltage (MV) route congestion is the most complex use case. A single MV feeder cable serves
multiple substations in sequence; the load on any segment of the cable is the *sum* of all loads
downstream of that segment. Congestion can occur at any point along the route, not just at the
substation level.

This use case combines OpenSTEF's probabilistic load forecasting with **power-grid-model**, an
open-source library for power flow calculations. The workflow is:

1. Forecast load at each individual substation or connection point on the route using OpenSTEF.
2. Feed the resulting probabilistic load scenarios into power-grid-model to compute power flows
   along each cable segment.
3. Compare segment-level flows against cable ratings to identify congestion risk at each point
   in the topology.

This topology-aware approach is necessary because a substation-level forecast alone cannot tell
you *which cable segment* will be overloaded — you need the network topology to propagate loads
through the grid.

**When to use this configuration:**

- You are managing congestion on MV feeders with multiple downstream connection points.
- You have access to network topology data (cable ratings, connectivity).
- You want to identify the specific cable segment at risk, not just the aggregate feeder load.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow import ForecastingWorkflowConfig

   # MV route: one config per substation on the route; upper quantiles for
   # worst-case power flow calculations
   def make_substation_config(substation_id: str) -> ForecastingWorkflowConfig:
       return ForecastingWorkflowConfig(
           model_id=f"mv_route_substation_{substation_id}",
           model="xgboost",
           horizons=[
               LeadTime.from_string("PT1H"),
               LeadTime.from_string("PT6H"),
               LeadTime.from_string("PT24H"),
           ],
           # Upper quantiles feed into worst-case power flow scenarios
           quantiles=[Q(0.5), Q(0.9), Q(0.95)],
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_80m",
           rolling_aggregate_features=["mean", "max"],
       )

   # Create one workflow per substation on the MV route
   substation_ids = ["A1", "A2", "A3", "A4"]
   configs = {sid: make_substation_config(sid) for sid in substation_ids}

After collecting forecasts from all substations, the upper-quantile scenarios (e.g. Q(0.95) for
all substations simultaneously) are passed to power-grid-model as a load scenario. The resulting
cable currents are compared against rated ampacity to produce a congestion probability per segment.

.. note::

   The power-grid-model integration is external to OpenSTEF. OpenSTEF's role is to produce
   calibrated probabilistic load forecasts at each node; power-grid-model handles the network
   physics. This separation of concerns keeps both libraries focused on what they do best.


Choosing the Right Configuration
---------------------------------

The use cases above share the same API surface — the primary levers are the **model type**,
**quantile selection**, and **feature columns**. The following rules of thumb help you choose:

- **Model type:** Use ``xgboost`` as the default. Switch to ``gblinear`` when the aggregation level
  is high and relationships are approximately linear (grid losses, highly aggregated transport).
  Use ``lgbm`` when training data is large and you want faster iteration.

- **Quantiles:** Always include Q(0.5) as your point forecast. Add Q(0.9) and Q(0.95) whenever
  you need to detect or bound peak events (congestion, free space). Add Q(0.05) and Q(0.1) when
  you need a lower bound (free space estimation, conservative capacity planning).

- **Features:** Temperature and radiation are almost always useful. Market price (``energy_price_column``)
  is specifically valuable for grid loss forecasting. For district heating, lean heavily on
  temperature and consider engineered degree-day features.

- **Horizons:** Short horizons (1–6 hours) suit real-time congestion management. Longer horizons
  (24 hours to 3 days) are needed for transport reporting to TSOs and connection planning.

For guidance on how to integrate data sources into these workflows, see :doc:`data_integration`.
For production deployment patterns — scheduling, model storage, and monitoring — see :doc:`deployment`.