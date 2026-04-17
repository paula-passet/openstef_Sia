Common Use Cases
================

This page describes the main forecasting scenarios that OpenSTEF is designed to handle. Each use case has distinct characteristics — different aggregation levels, dominant predictors, accuracy targets, and model configurations. Understanding these differences helps you choose the right setup from the start rather than discovering mismatches after training.

.. note:: [DIAGRAM: Use case overview showing the six forecasting scenarios (Congestion Management, Free Space Estimation, Grid Losses, Transport, District Heating, MV Route Congestion) as nodes, each annotated with their primary input data types (load measurements, weather, topology, market prices) and output applications (peak alerts, capacity headroom, cost optimisation, TSO reporting, thermal demand, route loading)]

----

Congestion Management
---------------------

Congestion management is the original and most mature OpenSTEF use case. The goal is to predict peak load at specific grid assets — transformers, medium-voltage substations (MSRs), or individual cable feeders — so that grid operators can act before an overload occurs. Actions range from calling customers to reduce consumption, to dispatching flexible assets or rerouting power flows.

What makes this use case technically demanding is the combination of **low aggregation** and **peak sensitivity**. At a single MSR or feeder, individual customer behaviour introduces high variability that cancels out at higher aggregation levels. The model must be accurate precisely where it matters most: near the capacity limit. This means optimising for high-quantile accuracy rather than average error.

**Key characteristics:**

- Aggregation level: low to medium (individual assets, MSRs, substations)
- Dominant predictors: weather (temperature, solar irradiance), time-of-day, day-of-week patterns
- Primary metrics: rMAE at the 50th quantile during peaks, precision/recall for threshold exceedance, rCRPS
- Model focus: peak detection, high-quantile calibration

A typical congestion forecast produces a probabilistic output — a set of quantiles (e.g., P10 through P90) for each forecast horizon. The P90 quantile is used as a conservative estimate of peak load; if P90 exceeds the asset's rated capacity, an alert is triggered.

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=1001,
       name="transformer_hv_mv_001",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=2880,          # 48-hour horizon
       resolution_minutes=15,
       quantiles=[0.1, 0.3, 0.5, 0.7, 0.9],
       lat=52.37,
       lon=4.89,
   )

   # train_data is a DataFrame with a DatetimeIndex and a "load" column
   model, report = train_model_pipeline(pj, train_data)

The quantile outputs let downstream systems implement risk-based thresholds rather than binary on/off alerts. See :doc:`deployment` for patterns that operationalise these forecasts at scale.

----

Free Space Estimation
---------------------

Free space estimation answers a related but distinct question: *how much remaining capacity does a grid asset have right now, and how much will it have over the coming hours?* Rather than predicting raw load, the output is the headroom between forecast load and the asset's rated capacity.

This is a derived use case built on top of a congestion forecast. Once you have a probabilistic load forecast, free space is simply:

.. code-block:: python

   rated_capacity_mw = 10.0  # asset nameplate rating

   # forecast_df has columns like "quantile_P10", "quantile_P50", "quantile_P90"
   forecast_df["free_space_P10"] = rated_capacity_mw - forecast_df["quantile_P90"]
   forecast_df["free_space_P50"] = rated_capacity_mw - forecast_df["quantile_P50"]
   forecast_df["free_space_P90"] = rated_capacity_mw - forecast_df["quantile_P10"]

The sign convention matters: a negative free space value at P10 means there is a meaningful probability of overload. Grid operators use this to prioritise which assets need intervention and to communicate available capacity to flexibility providers or EV charging operators.

.. note::

   Free space estimation reuses the same model and training pipeline as congestion management. The difference is entirely in how the forecast output is interpreted and consumed downstream.

----

Grid Loss Forecasts
-------------------

Grid losses — the energy dissipated as heat in cables and transformers during transmission — are a financial cost that grid operators must purchase on the day-ahead electricity market. Forecasting losses accurately reduces procurement costs: buying too little means buying expensive balancing energy; buying too much means holding unnecessary inventory.

This use case operates at a **high aggregation level** (system-wide or regional totals), which changes the modelling dynamics significantly compared to congestion management:

- Weather predictors have diminished influence. At high aggregation, individual weather effects average out.
- Temporal and cyclic patterns dominate: time of day, day of week, seasonal cycles.
- The loss function is asymmetric and price-weighted. An error during a high-price hour costs more than the same error during a low-price hour.

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=2001,
       name="grid_losses_region_north",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=60,         # hourly resolution matches market intervals
       quantiles=[0.1, 0.5, 0.9],
       lat=52.9,
       lon=5.1,
   )

   model, report = train_model_pipeline(pj, train_data)

When EPEX day-ahead prices are available as a feature, the model can implicitly learn to weight errors by market price. The benchmark dataset included with OpenSTEF contains historical EPEX prices alongside load measurements and weather, making it straightforward to prototype this use case locally.

----

Transport Forecasts
-------------------

Transport forecasts serve a coordination function between network operators. A distribution system operator (DSO) like Alliander must report expected energy flows to the transmission system operator (TSO) — in the Netherlands, TenneT — so that the TSO can balance the national grid. The DSO simultaneously receives similar forecasts from its own large customers.

The accuracy target here is **overall reliability across the full forecast horizon**, not just at peaks. A transport forecast that is consistently accurate at all hours is more useful for TSO coordination than one that is excellent at peaks but noisy elsewhere.

**Key characteristics:**

- Aggregation level: medium (regional or substation aggregates)
- Primary metric: rMAE across the full horizon
- Model focus: balanced performance, no special peak weighting
- Optional: split-component forecasts (solar, wind, residual load as separate outputs)

Some operators require the transport forecast to be decomposed into generation components. This requires training separate models for solar and wind generation and subtracting them from the total load forecast, or using a multi-output model configuration.

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=3001,
       name="transport_substation_south",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=2880,
       resolution_minutes=15,
       quantiles=[0.1, 0.5, 0.9],
       lat=51.55,
       lon=5.08,
   )

   model, report = train_model_pipeline(pj, train_data)

----

District Heating Demand
-----------------------

District heating is an example of OpenSTEF being applied outside the electricity domain. The target variable is thermal demand (heat load in MW or GJ/h) rather than electrical load, but the forecasting problem is structurally identical: a time series with weather dependence, daily and seasonal cycles, and the need for probabilistic outputs.

The main modelling difference is that **outdoor temperature is the dominant predictor** for heat demand, whereas for electricity it is one of several. Solar irradiance matters less (or inversely — solar gain reduces heating demand in buildings). Wind speed can matter for heat loss in poorly insulated buildings.

Because OpenSTEF treats the target variable generically, switching from electricity to heat demand requires no code changes — only the input data and feature engineering change:

.. code-block:: python

   from openstef.pipeline.train_model import train_model_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   pj = PredictionJobDataClass(
       id=4001,
       name="district_heating_zone_a",
       forecast_type="demand",
       model="xgb",
       horizon_minutes=1440,          # 24-hour horizon typical for heat dispatch
       resolution_minutes=60,
       quantiles=[0.1, 0.5, 0.9],
       lat=52.08,
       lon=4.31,
   )

   # train_data["load"] contains heat demand in MW
   # train_data includes temperature, wind_speed, and optionally solar_irradiance
   model, report = train_model_pipeline(pj, train_data)

.. note::

   District heating support in OpenSTEF 4.0 is an active development area. The core pipeline works today; domain-specific feature engineering guidance will be added as community experience accumulates.

----

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most structurally complex use case. A single MV feeder serves multiple load points connected in a radial or meshed topology. Congestion can occur at any segment of the route, not just at the substation head. Identifying *which* cable segment is at risk requires combining load forecasts with network topology.

OpenSTEF handles the forecasting side — producing load forecasts at individual measurement points along the route. The topology-aware power flow calculation is handled by `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, a separate library developed alongside OpenSTEF at Alliander. The two are used together:

1. OpenSTEF produces probabilistic load forecasts at each measurement point on the MV route.
2. ``power-grid-model`` runs a power flow calculation using those forecasts as nodal injections, propagating load through the network topology.
3. The resulting cable loading percentages identify which segments are at risk of congestion.

.. code-block:: python

   import pandas as pd
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   from openstef.data_classes.prediction_job import PredictionJobDataClass

   # One prediction job per measurement point on the MV route
   measurement_points = [
       {"id": 5001, "name": "mv_route_7_node_a", "lat": 52.10, "lon": 4.50},
       {"id": 5002, "name": "mv_route_7_node_b", "lat": 52.11, "lon": 4.51},
       {"id": 5003, "name": "mv_route_7_node_c", "lat": 52.12, "lon": 4.52},
   ]

   forecasts = {}
   for point in measurement_points:
       pj = PredictionJobDataClass(
           id=point["id"],
           name=point["name"],
           forecast_type="demand",
           model="xgb",
           horizon_minutes=1440,
           resolution_minutes=15,
           quantiles=[0.1, 0.5, 0.9],
           lat=point["lat"],
           lon=point["lon"],
       )
       # load_data[point["name"]] is the historical load DataFrame for this node
       forecasts[point["name"]] = create_forecast_pipeline(pj, load_data[point["name"]], model)

   # forecasts now contains per-node probabilistic forecasts
   # pass these as nodal injections to power-grid-model for route-level congestion analysis

.. note::

   ``power-grid-model`` integration is outside the scope of OpenSTEF itself. The library's role is to produce accurate nodal forecasts; the topology calculation is a separate step. Refer to the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for the network calculation side.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration differences across use cases:

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 20 25

   * - Use Case
     - Aggregation
     - Resolution
     - Key Metric
     - Model Focus
   * - Congestion management
     - Low–medium
     - 15 min
     - rMAE@peaks, rCRPS
     - High-quantile accuracy
   * - Free space estimation
     - Low–medium
     - 15 min
     - Headroom reliability
     - Derived from congestion model
   * - Grid losses
     - High
     - 60 min
     - rMAE + cost-weighted error
     - Temporal patterns, price weighting
   * - Transport
     - Medium
     - 15 min
     - rMAE (full horizon)
     - Balanced across all hours
   * - District heating
     - Medium
     - 60 min
     - rMAE
     - Temperature sensitivity
   * - MV route congestion
     - Low (per node)
     - 15 min
     - Per-segment loading %
     - Nodal accuracy + topology

----

Related Pages
-------------

- :doc:`data_integration` — how to feed each use case with data from S3, Databricks, or InfluxDB
- :doc:`deployment` — production patterns for running multiple prediction jobs at scale
- :doc:`migration_v3_v4` — if you are migrating an existing congestion or transport pipeline from V3