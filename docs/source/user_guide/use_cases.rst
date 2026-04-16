Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was designed with a concrete set of real-world problems in mind. This page describes the primary use cases the library supports, what distinguishes each one technically, and how to configure OpenSTEF appropriately for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

All use cases share the same core library workflow: you configure a ``ForecastingWorkflowConfig``, supply a time-indexed ``DataFrame`` of historical measurements and predictors, and receive probabilistic forecasts across a set of quantiles. What changes between use cases is which predictors matter, which quantiles you care about, how you weight errors, and — in the topology-aware case — what post-processing you apply to the raw forecasts.

----

Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case in OpenSTEF. The problem is straightforward: a transformer or cable segment has a rated capacity, and when load exceeds that capacity the equipment is at risk. Grid operators need to know *when* a peak will occur — ideally 24–48 hours ahead — so they can contact flexible customers and ask them to reduce consumption or generation.

This use case is characterised by **high variability at low aggregation levels**. A single medium-voltage substation (MSR) or individual customer connection can behave very differently from day to day, making the forecast inherently noisy. The business value is concentrated at the tail of the distribution: a forecast that is accurate on average but misses the peak is useless for congestion management. This drives the choice of metrics and model configuration.

**Key characteristics:**

- Aggregation level: low to medium (individual customers, MSRs, substations)
- Primary metric: rMAE at the 50th quantile during peak periods, precision/recall of peak detection, rCRPS
- Model emphasis: high-quantile accuracy, peak detection
- Typical horizon: 24–48 hours ahead (``P2D``)
- Essential predictors: weather (temperature, solar radiation, wind), calendar features, historical load

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow.create_forecast import ForecastingWorkflowConfig

   # Congestion management: emphasise tail quantiles for peak detection
   congestion_config = ForecastingWorkflowConfig(
       model_id="substation_A47_congestion",
       run_name="congestion_v1",
       model="xgboost",
       horizons=[LeadTime.from_string("P2D")],
       # Wide quantile spread to capture peak uncertainty
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       model_reuse_enable=True,
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

The upper quantiles (Q90, Q95) are what the congestion management system actually acts on: if the 95th-percentile forecast exceeds the cable rating, a demand-response event is triggered. Providing the full quantile spread lets downstream systems tune their risk tolerance.

----

Free Space Estimation
---------------------

Free space estimation is the inverse of congestion management: instead of asking "will we exceed capacity?", it asks "how much headroom remains on this asset, and for how long?". This is used for connection planning — a new customer wants to connect to the grid, and the operator needs to know whether the local transformer or cable can accommodate the additional load without reinforcement.

The forecast itself is identical to a congestion management forecast. The difference is entirely in the post-processing step: you subtract the forecast load (typically the upper quantile, to be conservative) from the rated capacity of the asset.

.. code-block:: python

   import pandas as pd

   # Assume `forecast_df` is the output of a congestion management forecast
   # with columns like "forecast_P0.9", "forecast_P0.5", etc.
   ASSET_CAPACITY_MW = 10.0  # rated capacity of the transformer

   # Conservative free space: use the 90th-percentile forecast
   forecast_df["free_space_mw"] = ASSET_CAPACITY_MW - forecast_df["forecast_P0.9"]
   forecast_df["congested"] = forecast_df["free_space_mw"] < 0.0

   # Minimum free space over the planning horizon
   min_free_space = forecast_df["free_space_mw"].min()
   print(f"Minimum free space over horizon: {min_free_space:.2f} MW")

Because free space estimation reuses the congestion forecast directly, the configuration is the same. The only decision is which quantile to use as the "effective load" when computing headroom — a more risk-averse operator will use Q95, a less risk-averse one might use Q50.

----

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses accurately has direct financial value: grid operators buy energy on the wholesale market to cover losses, and buying at the wrong time (or in the wrong quantity) is costly.

This use case operates at a **much higher aggregation level** than congestion management — losses are typically measured and forecast at the regional or national level. At this scale, individual customer behaviour averages out, and the dominant patterns are temporal (time of day, day of week, season) and system-wide. Weather predictors have diminished impact compared to lower-aggregation forecasts.

The distinguishing feature of grid loss forecasting is **cost-weighted error minimisation**. A forecast error at a high-price hour is more expensive than the same error at a low-price hour, so the model should be penalised accordingly. This is achieved by incorporating energy market prices as a predictor and, where supported, by weighting training samples by the price at each timestamp.

**Key characteristics:**

- Aggregation level: high (regional or system-wide)
- Primary metric: rMAE, total error cost (forecast error × market price)
- Model emphasis: balanced accuracy across the full horizon, cost-weighted optimisation
- Typical horizon: 24–48 hours ahead
- Essential predictors: historical losses, calendar features, energy market prices

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow.create_forecast import ForecastingWorkflowConfig

   # Grid loss: include energy price as a predictor for cost-aware forecasting
   grid_loss_config = ForecastingWorkflowConfig(
       model_id="region_north_grid_loss",
       run_name="grid_loss_v1",
       model="gblinear",   # linear model suits the smoother, aggregated signal
       horizons=[LeadTime.from_string("P2D")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       model_reuse_enable=True,
       energy_price_column="EPEX_NL",   # market price column in your input data
       temperature_column="temperature_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

.. note::

   The ``gblinear`` model (gradient-boosted linear) is often a better fit for grid loss forecasting than
   tree-based models. At high aggregation levels the load signal is smoother and more linear, and
   ``gblinear`` avoids the extrapolation artefacts that XGBoost trees can produce when the signal drifts
   outside the training range.

----

Transport Forecasts
-------------------

Transport forecasts answer the question: "how much energy will flow across this grid connection over the next 24–72 hours?" They are used for two related purposes. First, a distribution system operator (DSO) must report planned energy flows to the transmission system operator (TSO) above it. Second, large customers must report their expected consumption to the DSO below them. OpenSTEF is used on both sides of this exchange.

Transport forecasts operate at a **medium aggregation level** — typically a high-voltage/medium-voltage substation serving a town or industrial area. The signal is more predictable than individual-customer forecasts but still exhibits meaningful weather sensitivity. Some operators require the forecast to be decomposed into components (solar generation, wind generation, residual load), which requires training separate models for each component and summing them.

**Key characteristics:**

- Aggregation level: medium (HV/MV substations, regional connections)
- Primary metric: rMAE across the full forecast horizon
- Model emphasis: balanced accuracy, reliability, optional component decomposition
- Typical horizon: 24–72 hours ahead (``P3D``)
- Essential predictors: weather, calendar, historical load; optionally solar/wind generation data

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow.create_forecast import ForecastingWorkflowConfig

   # Transport forecast: balanced accuracy over a 3-day horizon
   transport_config = ForecastingWorkflowConfig(
       model_id="substation_HV_transport",
       run_name="transport_v1",
       model="xgboost",
       horizons=[LeadTime.from_string("P3D")],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       model_reuse_enable=True,
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

For component decomposition, train one ``ForecastingWorkflowConfig`` per component (solar, wind, residual) and combine the resulting forecasts. Each component model should be trained on the corresponding measured generation or load series, not on the aggregate.

----

District Heating Demand
-----------------------

District heating is an example of OpenSTEF being applied **outside the electricity domain entirely**. A district heating network distributes hot water from a central plant to residential and commercial buildings. The plant operator needs to forecast thermal demand to schedule boiler output and avoid both under-supply (cold buildings) and over-supply (wasted energy).

The forecasting problem is structurally identical to electricity load forecasting: a time series of past demand, weather predictors (outdoor temperature is the dominant driver of heating demand), and calendar features. OpenSTEF's built-in feature engineering handles all of these. The only adaptation required is that your input ``DataFrame`` contains thermal demand (in MW or GJ/h) rather than electrical load.

**Key characteristics:**

- Domain: thermal energy (not electricity)
- Aggregation level: varies (district, building cluster, individual building)
- Primary metric: rMAE
- Essential predictors: outdoor temperature (dominant), solar radiation, wind speed, calendar
- No electricity-specific configuration needed — standard weather columns apply

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow.create_forecast import ForecastingWorkflowConfig

   # District heating: temperature is the dominant predictor
   heating_config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_3",
       run_name="heating_v1",
       model="xgboost",
       horizons=[LeadTime.from_string("P2D")],
       quantiles=[Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9)],
       model_reuse_enable=True,
       temperature_column="temperature_2m",       # primary driver
       radiation_column="shortwave_radiation",    # solar gain reduces heating demand
       wind_speed_column="wind_speed_80m",        # wind chill effect
       rolling_aggregate_features=["mean", "median", "max", "min"],
       # energy_price_column not needed for thermal demand
   )

.. note::

   District heating demand is typically **negatively correlated** with temperature and solar radiation —
   warm sunny days reduce heating demand. OpenSTEF's feature engineering captures this automatically
   through lagged and rolling features, but you should verify the sign of feature importances after
   training to confirm the model has learned the expected relationships.

----

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most complex use case because it combines OpenSTEF's probabilistic load forecasting with **topology-aware power flow calculations** using the ``power-grid-model`` library. A single MV cable route may serve multiple substations, and the load on any segment of the route depends on the combined load of all downstream nodes — not just the load at a single measurement point.

The workflow has two stages:

1. **Forecast stage** — Run a standard OpenSTEF congestion management forecast for each individual node (substation or customer connection) on the MV route. Each node gets its own ``ForecastingWorkflowConfig`` and produces a probabilistic forecast.

2. **Power flow stage** — Feed the per-node forecasts into ``power-grid-model`` along with the network topology (cable impedances, transformer ratings, network connectivity). The power flow solver computes the resulting current and voltage at every segment of the route, identifying which segments are at risk of congestion.

This separation of concerns is deliberate: OpenSTEF handles the statistical forecasting problem, and ``power-grid-model`` handles the physics. Neither library needs to know about the internals of the other.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile as Q
   from openstef.workflow.create_forecast import ForecastingWorkflowConfig

   # Step 1: configure a forecast for each node on the MV route.
   # Use the same config template and vary only model_id per node.
   node_config_template = ForecastingWorkflowConfig(
       model_id="mv_route_7_node_{node_id}",   # formatted per node
       run_name="mv_congestion_v1",
       model="xgboost",
       horizons=[LeadTime.from_string("P2D")],
       # Include upper quantiles — power flow uses Q90/Q95 for worst-case analysis
       quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
       model_reuse_enable=True,
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   # Step 2: collect per-node forecasts into a dict keyed by node ID,
   # then pass to your power-grid-model integration layer.
   # (power-grid-model integration is outside the scope of this page.)
   node_forecasts = {}
   for node_id, node_data in mv_route_nodes.items():
       config = node_config_template  # copy and set model_id per node
       # ... run forecast pipeline, store result ...
       node_forecasts[node_id] = forecast_result

.. note::

   ``power-grid-model`` is a separate open-source library maintained by Alliander. It is not part of
   OpenSTEF. See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for
   details on topology input format and power flow solver configuration.

The key insight for MV route congestion is that **you should use a conservative quantile** (Q90 or Q95) as the input to the power flow calculation, not the median. The median forecast will underestimate peak load on roughly half of all days by definition. Using an upper quantile gives the power flow solver a realistic worst-case scenario to evaluate.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case.

.. list-table:: Use case configuration summary
   :header-rows: 1
   :widths: 25 15 20 20 20

   * - Use case
     - Aggregation
     - Recommended model
     - Key quantiles
     - Distinguishing predictor
   * - Congestion management
     - Low–medium
     - ``xgboost``
     - Q90, Q95 (peak detection)
     - Weather + calendar
   * - Free space estimation
     - Low–medium
     - ``xgboost``
     - Q90 (conservative headroom)
     - Same as congestion
   * - Grid loss
     - High
     - ``gblinear``
     - Q50 (cost minimisation)
     - Energy market price
   * - Transport
     - Medium
     - ``xgboost``
     - Q50 (reliability)
     - Weather + calendar
   * - District heating
     - Varies
     - ``xgboost``
     - Q50 (demand planning)
     - Temperature (dominant)
   * - MV route congestion
     - Low (per node)
     - ``xgboost``
     - Q90, Q95 (power flow input)
     - Weather + topology

----

Related Pages
-------------

- :doc:`data_integration` — How to load historical measurements and weather data from S3, Databricks, InfluxDB, and other sources into the ``DataFrame`` format OpenSTEF expects.
- :doc:`deployment` — Production deployment patterns for running OpenSTEF forecasting pipelines at scale across thousands of grid locations.
- :doc:`migration_v3_v4` — If you have existing V3 pipelines for any of these use cases, see the migration guide for the changes required to move to V4.