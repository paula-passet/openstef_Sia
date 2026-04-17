Use Cases
=========

OpenSTEF is a general-purpose short-term energy forecasting library, but its design was shaped by a
concrete set of operational problems faced by grid operators. This page describes the main forecasting
use cases the library supports, explains what makes each one distinct in terms of data, model
configuration, and accuracy requirements, and provides example configurations you can adapt for your
own deployment.

.. note::

   [DIAGRAM: Use case overview — flowchart showing six forecasting scenarios (Congestion Management,
   Transport, Grid Loss, Free Space Estimation, District Heating, MV Route Congestion) with their
   primary input data types (load history, weather, energy prices, grid topology) on the left and
   their downstream applications (demand response, capacity planning, financial optimisation,
   connection decisions, thermal scheduling, route-level overload detection) on the right. Arrows
   connect inputs through the OpenSTEF library to outputs.]

---

Introduction
------------

Every use case in OpenSTEF follows the same fundamental pattern: historical time-series measurements
are combined with weather forecasts and other contextual features, a model is trained, and probabilistic
forecasts are produced for a configurable horizon. What differs between use cases is *which* accuracy
characteristics matter most, *how aggregated* the measurement point is, and *which downstream decision*
the forecast feeds into. Getting these details right — choosing the correct model, quantiles, and
optimisation target — is what separates a useful forecast from a technically correct but operationally
irrelevant one.

---

Congestion Management
---------------------

Congestion management is the original motivation for OpenSTEF and remains its most mature use case.
The core problem: electricity grid equipment (transformers, cables) has a rated capacity, and when
load exceeds that capacity the equipment risks damage or must be switched off. Grid reinforcement
takes years; in the meantime, operators need to know *in advance* when a congestion point will be
overloaded so they can call flexible customers and ask them to reduce consumption or generation.

This means the forecast must be accurate specifically near **peak load moments**. A model that
achieves low average error but systematically underestimates peaks is useless for congestion
management. The relevant metrics are therefore precision and recall on peak events, rMAE at the
50th quantile during peak periods, and the Continuous Ranked Probability Score (rCRPS) to evaluate
the full predictive distribution.

Aggregation levels vary widely in this use case — from high-voltage substations serving thousands
of customers down to individual medium-voltage substations (MSRs) or even single large customers.
At low aggregation levels, individual behavioural variability dominates and forecasts are inherently
noisier. The library handles this through probabilistic output: rather than a single load value,
OpenSTEF produces a full quantile forecast so that operators can reason about the probability that
load will exceed a threshold.

**Typical configuration:**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Congestion management: emphasise high-quantile accuracy over 48-hour horizon
   config = ForecastingWorkflowConfig(
       model_id="substation_hv_amsterdam_001",
       model="xgboost",                        # XGBoost handles non-linear peak behaviour well
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.5), Q(0.7), Q(0.9), Q(0.95)],  # Upper tail matters most
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       sample_interval=timedelta(minutes=15),
   )

   workflow = create_forecasting_workflow(config=config)

.. note::

   The upper quantiles (Q90, Q95) are what operators act on. A forecast that the 95th-percentile
   load will exceed transformer capacity tomorrow afternoon is the trigger for a demand-response call.
   Configure your quantiles to match the risk threshold your operations team uses.

---

Free Space Estimation
---------------------

Free space estimation is a closely related but subtly different problem. Rather than asking "will
load exceed capacity?", it asks "how much *remaining* capacity is available at this connection
point?". This is the key question when a new customer (a factory, a solar park, a charging hub)
wants to connect to the grid and the operator needs to decide whether a connection is feasible
without reinforcement.

The forecast target is effectively ``capacity - load``, and the relevant quantile is the *lower*
tail: operators want to know the worst-case remaining capacity, not the average. A Q05 or Q10
forecast of free space tells you that 90–95% of the time there will be at least this much headroom.

Because the decision is about future connection feasibility rather than imminent overload, the
forecast horizon is often longer — days to weeks — and the aggregation level is typically a
substation or cable segment rather than an individual customer.

**Typical configuration:**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Free space: forecast load, then derive remaining capacity in post-processing
   config = ForecastingWorkflowConfig(
       model_id="cable_segment_free_space_042",
       model="lgbm",
       horizons=[LeadTime.from_string("PT72H")],
       quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],  # Lower tail for worst-case headroom
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       sample_interval=timedelta(minutes=15),
   )

   workflow = create_forecasting_workflow(config=config)

After generating the load forecast, subtract the Q95 load from the rated capacity of the asset to
obtain a conservative free-space estimate. The probabilistic output of OpenSTEF makes this
straightforward: each quantile of the load forecast maps directly to a corresponding quantile of
available headroom.

---

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. They
are a real cost — grid operators must purchase this energy on the wholesale market — and forecasting
them accurately enables better procurement decisions.

Grid loss forecasting differs from the previous use cases in two important ways. First, the
measurement point is highly aggregated: losses are computed at the system level by comparing
metered injection with metered offtake across a large network. At this aggregation level, individual
customer behaviour averages out and **temporal and cyclic patterns dominate** — time of day, day of
week, and seasonal load cycles are the strongest predictors. Weather features have less influence
than in substation-level forecasts.

Second, the optimisation target is financial rather than operational. Errors are not equally costly:
buying too little energy on the day-ahead market and having to buy the remainder on the more
expensive intraday market is worse than buying slightly too much. This motivates **cost-weighted
error minimisation**, where the loss function is weighted by real-time market prices.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Grid loss: aggregated system-level, include energy price for cost-weighted optimisation
   config = ForecastingWorkflowConfig(
       model_id="grid_loss_region_north",
       model="gblinear",                        # Linear model suits the smooth, aggregated signal
       horizons=[LeadTime.from_string("PT36H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       target_column="load",
       energy_price_column="EPEX_NL",           # Market price used for cost-weighted features
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       sample_interval=timedelta(hours=1),      # Hourly resolution matches market settlement
   )

   workflow = create_forecasting_workflow(config=config)

.. note::

   The ``energy_price_column`` field enables price-aware feature engineering inside the pipeline.
   Providing day-ahead market prices as an input feature allows the model to learn the relationship
   between price signals and grid behaviour, which is particularly valuable for loss forecasting
   where the cost of errors is price-dependent.

---

Transport Forecasts
-------------------

Transport forecasts answer a different question: what is the total energy flow across a grid
boundary over the coming hours and days? Grid operators use these forecasts to communicate planned
usage to upstream transmission system operators (TSOs) and to receive corresponding forecasts from
downstream customers. For example, a distribution system operator (DSO) provides transport forecasts
to the national TSO for balancing purposes, while simultaneously receiving forecasts from large
industrial customers connected to its network.

The accuracy requirement here is **balanced across the entire forecast horizon** rather than
concentrated at peaks. The primary metric is rMAE over all time steps. Some operators also require
transport forecasts decomposed into components — solar generation, wind generation, and residual
load — which requires running separate models for each component and combining them.

Transport forecasting points are typically at medium aggregation levels: a regional substation or
grid boundary rather than an individual asset. This makes them more predictable than low-aggregation
congestion points but more granular than system-level grid loss measurements.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Transport forecast: balanced accuracy, medium aggregation
   config = ForecastingWorkflowConfig(
       model_id="transport_boundary_west_region",
       model="lgbm",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       sample_interval=timedelta(minutes=15),
   )

   workflow = create_forecasting_workflow(config=config)

For split-component transport forecasts, run separate ``ForecastingWorkflowConfig`` instances for
solar, wind, and residual load, each with its own ``model_id`` and ``target_column``, then sum the
component forecasts in your application layer.

---

District Heating Demand
-----------------------

District heating is a community-contributed use case that extends OpenSTEF beyond electricity into
thermal energy. A district heating network distributes hot water from a central plant to residential
and commercial buildings; the plant operator needs to forecast heat demand to schedule production
efficiently and avoid over- or under-heating the network.

The forecasting problem is structurally similar to electricity load forecasting: a time series of
thermal demand measurements, combined with weather features (outdoor temperature is the dominant
driver of heating demand), is used to train a model that predicts future demand. The key difference
is that **temperature is far more dominant** than in electricity forecasting, and solar radiation
plays a secondary role through passive solar heating of buildings.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # District heating: temperature-dominated demand signal
   config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_a",
       model="xgboost",
       horizons=[LeadTime.from_string("PT24H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       target_column="heat_demand_mw",          # Rename to match your measurement column
       temperature_column="temperature_2m",     # Primary driver
       radiation_column="shortwave_radiation",  # Secondary: passive solar reduces heating demand
       wind_speed_column="wind_speed_10m",      # Wind chill increases heating demand
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       sample_interval=timedelta(hours=1),
   )

   workflow = create_forecasting_workflow(config=config)

.. note::

   District heating is a non-electricity use case. OpenSTEF's feature engineering pipeline is
   domain-agnostic at the model level — the ``target_column`` can be any continuous time series.
   However, some built-in features (PV generation estimates, grid-specific transforms) are
   electricity-specific and will simply have no predictive value for thermal demand; the model
   will learn to ignore them.

---

MV Route Congestion with Grid Topology
---------------------------------------

Medium-voltage (MV) route congestion is the most technically complex use case. A single MV cable
route connects multiple substations in sequence; congestion on the route depends not just on the
load at each individual substation but on the *sum of loads* along the route, which is determined
by the network topology.

OpenSTEF addresses this by combining its standard forecasting pipeline with
`power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, an open-source library
for power flow calculations. The workflow is:

1. Forecast load at each individual substation on the route using OpenSTEF.
2. Pass the per-substation forecasts into power-grid-model along with the network topology.
3. power-grid-model computes the resulting current and voltage at each cable segment.
4. Segments where the computed current exceeds the rated capacity are flagged as congested.

This topology-aware approach is more accurate than simply summing substation loads because it
accounts for the actual electrical characteristics of the cable (impedance, voltage drop) and the
physical layout of the route.

**[VISUALIZATION: Diagram of an MV cable route with four substations connected in series, showing
per-substation load forecasts feeding into a power flow calculation that produces cable loading
percentages for each segment, with a congested segment highlighted in red.]**

From an OpenSTEF perspective, the forecasting step is identical to standard congestion management:
one ``ForecastingWorkflowConfig`` per substation, with quantiles covering the upper tail. The
topology integration happens in your application layer after the forecasts are generated.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # One config per substation on the MV route
   substation_ids = ["msr_route7_node1", "msr_route7_node2", "msr_route7_node3"]

   workflows = {}
   for substation_id in substation_ids:
       config = ForecastingWorkflowConfig(
           model_id=substation_id,
           model="xgboost",
           horizons=[LeadTime.from_string("PT48H")],
           quantiles=[Q(0.5), Q(0.9), Q(0.95)],
           target_column="load",
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_80m",
           pressure_column="surface_pressure",
           relative_humidity_column="relative_humidity_2m",
           sample_interval=timedelta(minutes=15),
       )
       workflows[substation_id] = create_forecasting_workflow(config=config)

   # After training and predicting with each workflow, pass the per-substation
   # Q95 forecasts into power-grid-model for topology-aware congestion detection.

---

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case:

+---------------------------+-------------+----------------------------+----------------------------+---------------------------+
| Use Case                  | Model       | Key Quantiles              | Primary Metric             | Aggregation Level         |
+===========================+=============+============================+============================+===========================+
| Congestion management     | xgboost     | Q70, Q90, Q95              | rMAE@peaks, rCRPS          | Low to medium             |
+---------------------------+-------------+----------------------------+----------------------------+---------------------------+
| Free space estimation     | lgbm        | Q05, Q10 (lower tail)      | rMAE@troughs               | Medium (cable/substation) |
+---------------------------+-------------+----------------------------+----------------------------+---------------------------+
| Grid loss                 | gblinear    | Q10, Q50, Q90              | rMAE + cost-weighted error | High (system level)       |
+---------------------------+-------------+----------------------------+----------------------------+---------------------------+
| Transport                 | lgbm        | Q10, Q50, Q90              | rMAE (all periods)         | Medium (boundary)         |
+---------------------------+-------------+----------------------------+----------------------------+---------------------------+
| District heating          | xgboost     | Q10, Q50, Q90              | rMAE                       | Medium (zone/district)    |
+---------------------------+-------------+----------------------------+----------------------------+---------------------------+
| MV route congestion       | xgboost     | Q50, Q90, Q95 per node     | rMAE@peaks + power flow    | Low (per substation)      |
+---------------------------+-------------+----------------------------+----------------------------+---------------------------+

A few rules of thumb:

- **Use upper-tail quantiles** (Q90+) when the downstream decision is about preventing overload.
- **Use lower-tail quantiles** (Q05–Q10) when the downstream decision is about available headroom.
- **Use gblinear** for highly aggregated, smooth signals where linear relationships dominate.
- **Use xgboost or lgbm** for lower-aggregation points with non-linear peak behaviour.
- **Include ``energy_price_column``** only for grid loss forecasting where cost-weighted optimisation
  is relevant.

---

Related Pages
-------------

- For instructions on connecting OpenSTEF to your data sources (InfluxDB, S3, Databricks), see
  :doc:`data_integration`.
- For running these workflows in production, including scheduling and containerisation, see
  :doc:`deployment`.
- If you are migrating an existing V3 prediction job configuration to V4 ``ForecastingWorkflowConfig``,
  see :doc:`migration_v3_v4`.