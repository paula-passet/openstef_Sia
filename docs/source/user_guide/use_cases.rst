Use Cases
=========

OpenSTEF is a general-purpose short-term energy forecasting library, but its design has been shaped by a set of recurring real-world problems faced by distribution system operators (DSOs). This page describes the most common use cases, explains what distinguishes each one, and shows how to configure OpenSTEF appropriately for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

---

Introduction
------------

Each use case in this page represents a distinct forecasting problem with its own accuracy requirements, aggregation characteristics, and downstream applications. While OpenSTEF's ``ForecastingWorkflowConfig`` and model API are the same across all of them, the right choice of model, quantiles, horizon, and feature set varies considerably. Understanding these differences will help you configure the library correctly from the start.

---

Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case for OpenSTEF. When grid capacity is fully utilised, a DSO cannot simply connect new customers — instead, it must predict *when* load will exceed equipment limits and coordinate demand response in advance.

**What makes it different:** The forecast must be accurate near *peak load periods*, not uniformly across the day. A model that is excellent on average but misses the top 5 % of load events is not useful here. This drives the choice of high quantiles (e.g., Q(0.9), Q(0.95)) and metrics such as rMAE at the 50th quantile during peaks and rCRPS.

**Aggregation:** Highly variable. Congestion can occur at a substation serving thousands of customers or at a single medium-voltage connection point. At low aggregation levels, individual customer behaviour introduces significant noise, so the model must be robust to high variability.

**Typical forecast horizon:** 24–48 hours ahead, giving operators enough lead time to contact customers.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Congestion management: emphasise high quantiles and a 48-hour horizon
   congestion_workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="substation_A_congestion",
           model="gblinear",
           horizons=[LeadTime.from_string("PT48H")],
           # Include high quantiles to capture peak load uncertainty
           quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
           target_column="load",
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_10m",
           relative_humidity_column="relative_humidity_2m",
           pressure_column="surface_pressure",
           rolling_aggregate_features=["mean", "median", "max", "min"],
       )
   )

The ``gblinear`` model is preferred here because it avoids the extrapolation artefacts that tree-based models can produce when load reaches levels not seen during training — exactly the scenario that matters most for congestion.

---

Free Space Estimation
---------------------

Free space estimation answers a related but distinct question: *how much remaining capacity exists on a cable or transformer right now, and how much will remain over the next hours or days?* Rather than predicting raw load, the output is framed as available headroom relative to the thermal limit of the asset.

**What makes it different:** The forecast is derived from a congestion forecast, but the framing shifts from "what will the load be?" to "will there be enough room for a new connection or a planned action?" This makes it particularly useful for grid planning teams and for automated connection-request workflows.

**Practical approach:** Train a load forecast for the asset, then subtract the predicted load (at a chosen quantile) from the known thermal rating. Using a high quantile (e.g., Q(0.9)) for the load gives a conservative estimate of free space, which is appropriate for safety-critical decisions.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Free space: same setup as congestion, but downstream logic uses
   # thermal_limit - predicted_load_q90 to derive headroom
   free_space_workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="cable_XY_free_space",
           model="gblinear",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
           target_column="load",
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_10m",
           relative_humidity_column="relative_humidity_2m",
           pressure_column="surface_pressure",
       )
   )

   # After calling workflow.predict(data), derive free space:
   # free_space_mw = thermal_limit_mw - forecast["q_0.90"]

.. note::

   The thermal rating of an asset may itself vary with ambient temperature (dynamic line rating). If your organisation uses dynamic ratings, incorporate the temperature-adjusted limit rather than a fixed value when computing headroom.

---

Grid Loss Forecasts
-------------------

Grid losses — the energy dissipated as heat in cables and transformers during transmission — must be purchased on the energy market to balance the grid. Forecasting losses accurately reduces procurement costs and supports financial optimisation.

**What makes it different:** At the system level where losses are aggregated, weather predictors have diminished impact. Temporal patterns (time of day, day of week, seasonal cycles) and system-wide behavioural trends dominate. Additionally, the cost of a forecast error is not symmetric: over-purchasing losses when market prices are high is more expensive than under-purchasing when prices are low. This motivates weighting errors by real-time market prices.

**Key inputs:** Historical load (aggregated), energy market prices (e.g., EPEX spot prices), calendar features.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Grid loss: include market price column; weather features are less critical
   grid_loss_workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="grid_loss_region_north",
           model="gblinear",
           horizons=[LeadTime.from_string("P1D")],
           quantiles=[Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)],
           target_column="grid_loss_mwh",
           energy_price_column="EPEX_NL",
           temperature_column="temperature_2m",
           rolling_aggregate_features=["mean", "median", "max", "min"],
       )
   )

**Key metric:** rMAE plus total error cost minimisation weighted by market prices. Evaluate both to get a complete picture of model quality.

---

Transport Forecasts
-------------------

Transport forecasts serve a coordination function: a DSO must report its expected energy throughput to the upstream transmission system operator (TSO), and in turn receives similar forecasts from large downstream customers. The goal is reliable, balanced accuracy across the entire forecast horizon — not just at peaks.

**What makes it different:** The aggregation level is typically medium (a regional substation or a group of substations), which makes the load more predictable than individual connection points. The primary metric is rMAE across all time steps, not peak-focused metrics. Some operators also require the forecast to be decomposed into components — solar generation, wind generation, and residual load — which requires separate component models.

**Typical horizon:** 24–72 hours, aligned with TSO reporting schedules.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Transport forecast: balanced quantiles, medium horizon
   transport_workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="transport_region_south",
           model="gblinear",
           horizons=[LeadTime.from_string("P3D")],
           quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
           target_column="load",
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_10m",
           relative_humidity_column="relative_humidity_2m",
           pressure_column="surface_pressure",
           rolling_aggregate_features=["mean", "median", "max", "min"],
       )
   )

For split-component transport forecasts (solar, wind, residual), instantiate a separate ``ForecastingWorkflowConfig`` for each component and combine the outputs downstream.

---

District Heating Demand
-----------------------

District heating is a community use case that extends OpenSTEF beyond electricity. Here the target variable is thermal demand (heat load in MW or GJ/h) rather than electrical load, but the forecasting problem is structurally identical: predict demand ahead of time to optimise supply.

**What makes it different:** The dominant weather driver shifts from solar radiation (less relevant) to outdoor temperature and wind chill. Demand is strongly anti-correlated with temperature — cold snaps drive sharp demand spikes. Seasonal patterns are more pronounced than in electricity forecasting.

**Practical configuration:** Use temperature and wind speed as primary features. Radiation is less important and can be omitted or given lower weight by excluding it from the config. A longer training context (e.g., two or more heating seasons) improves seasonal generalisation.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # District heating: temperature-driven, no radiation needed
   heating_workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="district_heat_network_1",
           model="gblinear",
           horizons=[LeadTime.from_string("PT48H")],
           quantiles=[Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)],
           target_column="heat_load_mw",
           temperature_column="temperature_2m",
           wind_speed_column="wind_speed_10m",
           relative_humidity_column="relative_humidity_2m",
           pressure_column="surface_pressure",
           # Omit radiation_column — not a significant driver for heat demand
           rolling_aggregate_features=["mean", "median", "max", "min"],
       )
   )

.. note::

   District heating is a community-contributed use case. The core OpenSTEF library is domain-agnostic — the same pipeline that forecasts electrical load works for thermal demand with only configuration changes.

---

MV Route Congestion with Topology Awareness
--------------------------------------------

Medium-voltage (MV) route congestion is the most complex use case. A single MV cable route may carry load from multiple substations, and congestion on the route depends on the *combined* flow through the network topology — not just the load at any single point. This requires integrating OpenSTEF's forecasting output with a power flow solver such as ``power-grid-model``.

**What makes it different:** The forecast itself is a standard load forecast at each node in the network. The congestion assessment happens *after* forecasting, by running a power flow calculation over the predicted loads using the network topology. This two-stage approach means OpenSTEF handles the time-series prediction while ``power-grid-model`` handles the physics.

**Workflow:**

1. Forecast load at each relevant node using OpenSTEF (one workflow per node, or a batched approach).
2. Pass the predicted load profiles into ``power-grid-model`` as input to a time-series power flow calculation.
3. Identify time steps where cable or transformer loading exceeds rated capacity.
4. Use the congestion timestamps to trigger demand response or re-routing decisions.

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Step 1: Forecast load at each MV node
   # Repeat this configuration for each node in the route
   node_workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="mv_node_<node_id>",
           model="gblinear",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.5), Q(0.9)],  # Median + conservative upper bound
           target_column="load",
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_10m",
           relative_humidity_column="relative_humidity_2m",
           pressure_column="surface_pressure",
       )
   )

   # Step 2: After prediction, collect node forecasts into a DataFrame
   # and pass them to power-grid-model for topology-aware power flow.
   # See the power-grid-model documentation for the power flow API.

.. note::

   ``power-grid-model`` is a separate open-source library maintained by Alliander. OpenSTEF does not depend on it directly — the integration is a pattern, not a built-in feature. See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for details on constructing the network model and running time-series power flow calculations.

---

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case:

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Use Case
     - Typical Horizon
     - Key Quantiles
     - Primary Drivers
   * - Congestion management
     - 24–48 h
     - Q(0.9), Q(0.95)
     - Weather, solar, time-of-day
   * - Free space estimation
     - 24–48 h
     - Q(0.9), Q(0.95)
     - Same as congestion; post-process with thermal limit
   * - Grid loss
     - 24 h
     - Q(0.1)–Q(0.9)
     - Temporal patterns, market prices
   * - Transport
     - 24–72 h
     - Full range
     - Weather, balanced accuracy
   * - District heating
     - 24–48 h
     - Q(0.1)–Q(0.9)
     - Temperature, wind chill
   * - MV route congestion
     - 24–36 h
     - Q(0.5), Q(0.9)
     - Per-node load + topology (power-grid-model)

---

Related Pages
-------------

- For instructions on loading data from S3, Databricks, or InfluxDB into the formats these workflows expect, see :doc:`data_integration`.
- For running these workflows in production — scheduling, containerisation, and scaling to thousands of grid locations — see :doc:`deployment`.
- If you are migrating an existing V3 pipeline to use the new ``ForecastingWorkflowConfig`` API, see :doc:`migration_v3_v4`.