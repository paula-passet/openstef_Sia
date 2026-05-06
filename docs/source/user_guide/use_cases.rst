Common Use Cases
================

This page describes the main forecasting scenarios that OpenSTEF is designed to handle. Each use case has distinct characteristics — different aggregation levels, accuracy priorities, and model configurations — so understanding which one applies to your situation will help you configure the library correctly from the start.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

---

Congestion Management
---------------------

Congestion management is the original and most widely deployed use case. The goal is to predict peak load at a specific grid asset — a transformer, cable, or medium-voltage substation (MSR) — so that a grid operator can intervene before the asset is overloaded. Alliander currently runs this in production across more than 10,000 grid locations.

What makes this use case distinctive is that **accuracy near peak periods matters far more than average accuracy**. A model that is excellent at predicting off-peak hours but misses the top 5 % of load events is operationally useless. The relevant metrics are therefore precision and recall on peak events, rMAE at the 50th quantile during peaks, and rCRPS for the full predictive distribution.

Aggregation levels vary enormously: a high-voltage substation aggregates thousands of customers and is relatively predictable, while an individual MSR or a single commercial customer can be highly volatile. For low-aggregation points you should expect wider prediction intervals and should tune your quantile configuration accordingly.

A typical configuration for a congestion management forecast emphasises high-quantile accuracy and probabilistic output:

.. code-block:: python

    from datetime import timedelta
    from openstef.model.serializer import MLflowSerializer
    from openstef.pipeline.train_model import train_model_pipeline
    from openstef.data_classes.prediction_job import PredictionJobDataClass

    pj = PredictionJobDataClass(
        id=1001,
        model="xgb",
        forecast_type="demand",
        name="Transformer_A_HV",
        quantiles=[0.05, 0.10, 0.50, 0.90, 0.95],  # wide interval for peak detection
        horizon_minutes=2880,   # 48-hour horizon
        resolution_minutes=15,
        lat=52.37,
        lon=4.89,
    )

    train_model_pipeline(pj, input_data, MLflowSerializer())

.. note::

   For low-aggregation assets (individual customers, small MSRs) consider increasing the number of
   training samples and enabling outlier-robust preprocessing. High behavioural variability means
   the model will naturally produce wider intervals — this is correct behaviour, not a bug.

---

Free Space Estimation
---------------------

Free space estimation answers a related but different question: *how much remaining capacity does a grid asset have right now, and how much will it have over the coming hours?* Rather than predicting raw load, the output is the headroom between the forecast load and the asset's rated capacity.

In practice this is computed as a post-processing step on top of a congestion management forecast:

.. code-block:: python

    import pandas as pd

    # `forecast` is a DataFrame with columns for each quantile, indexed by timestamp
    rated_capacity_mw = 12.5

    free_space = rated_capacity_mw - forecast[["quantile_P50"]]
    free_space.columns = ["free_space_mw"]

    # Flag periods where even the P90 forecast exceeds capacity
    congestion_risk = forecast["quantile_P90"] > rated_capacity_mw

The same ``ForecastingWorkflowConfig`` used for congestion management applies here. The distinction is entirely in how the downstream application consumes the output. Free space estimates are commonly used to decide whether to accept new grid connections or to schedule flexible loads.

---

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated in cables and transformers during transmission. Forecasting them accurately has direct financial consequences because losses must be purchased on the energy market, and market prices fluctuate. A forecast that is systematically wrong in the direction of expensive hours costs money.

This use case operates at a **highly aggregated level** — typically the entire distribution network or a large region. At this scale, weather predictors (solar irradiance, wind speed) have diminished influence compared to temporal and cyclic patterns: time of day, day of week, seasonal load curves. The model optimisation therefore shifts toward cost-weighted error minimisation rather than peak detection.

.. code-block:: python

    pj = PredictionJobDataClass(
        id=2001,
        model="xgb",
        forecast_type="demand",
        name="GridLoss_Region_West",
        quantiles=[0.50],          # point forecast is often sufficient here
        horizon_minutes=1440,      # 24-hour horizon aligned with day-ahead market
        resolution_minutes=60,     # hourly resolution matches market settlement
        lat=52.20,
        lon=4.65,
    )

.. note::

   If your organisation uses real-time market prices to weight forecast errors, you can pass a
   price series as a sample-weight column during training. This steers the model to be more
   accurate during expensive hours.

---

Transport Forecasts
-------------------

Transport forecasts describe the total energy flow across a grid boundary over a planning horizon. Grid operators use them to report planned usage to upstream transmission system operators (TSOs) and to receive equivalent forecasts from downstream customers. The key difference from congestion management is that **accuracy must be uniform across the entire forecast horizon**, not just at peaks.

Because transport forecasts are often shared externally, some operators also require the forecast to be decomposed into components: solar generation, wind generation, and residual load. This requires training separate component models and summing them, rather than forecasting the net load directly.

.. code-block:: python

    # Component-based transport forecast: train one model per component
    components = {
        "solar":    solar_input_data,
        "wind":     wind_input_data,
        "residual": residual_input_data,
    }

    trained_models = {}
    for component_name, data in components.items():
        pj = PredictionJobDataClass(
            id=3000 + i,
            model="xgb",
            forecast_type="demand",
            name=f"Transport_Border_X_{component_name}",
            quantiles=[0.50],
            horizon_minutes=2880,
            resolution_minutes=60,
        )
        trained_models[component_name] = train_model_pipeline(pj, data, serializer)

    # Combine at inference time
    total_transport = sum(model.predict(features) for model in trained_models.values())

The primary metric for transport forecasts is rMAE across all hours, which reflects the balanced accuracy requirement.

---

District Heating Demand
-----------------------

District heating is an example of OpenSTEF being applied outside electricity networks. The target variable is thermal demand (heat load in MW or GJ/h) rather than electrical load, but the forecasting problem is structurally identical: a time series of demand driven by weather, time patterns, and customer behaviour.

The main practical difference is in the feature set. Outdoor temperature is the dominant predictor for heat demand (replacing solar irradiance and wind speed as the primary weather drivers), and the seasonal pattern is inverted relative to electricity — demand peaks in winter rather than summer.

.. code-block:: python

    pj = PredictionJobDataClass(
        id=4001,
        model="xgb",
        forecast_type="demand",
        name="DistrictHeating_Zone_3",
        quantiles=[0.10, 0.50, 0.90],
        horizon_minutes=1440,
        resolution_minutes=60,
        lat=52.08,
        lon=5.12,
    )

    # Input data should include outdoor temperature as a feature column.
    # OpenSTEF's weather feature pipeline will handle this automatically
    # if the location coordinates are set correctly.

.. note::

   District heating support in OpenSTEF 4.0 is an active area of development. The core
   forecasting pipeline works today, but domain-specific feature engineering (e.g., heating
   degree days, return temperature) may need to be added as custom transforms.

---

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most complex use case. Rather than forecasting load at a single measurement point, the goal is to determine whether a specific cable *route* in the MV grid will be overloaded — accounting for the fact that load flows through a network topology, not just a single asset.

This use case combines OpenSTEF's load forecasting with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, a library for power flow calculations. The workflow has three stages:

1. **Forecast load** at each measurement point on the route using standard OpenSTEF pipelines.
2. **Run a power flow calculation** using ``power-grid-model`` with the forecasted loads as injections, using the actual network topology.
3. **Evaluate congestion** by comparing the resulting cable loading against rated capacities.

.. code-block:: python

    from openstef.pipeline.create_forecast import create_forecast_pipeline
    # power-grid-model is a separate package: pip install power-grid-model
    from power_grid_model import PowerGridModel, initialize_array

    # Step 1: Produce load forecasts for each node on the route
    node_forecasts = {}
    for node_pj in route_prediction_jobs:
        node_forecasts[node_pj.id] = create_forecast_pipeline(
            node_pj, input_data[node_pj.id], serializer
        )

    # Step 2: Assemble power flow input from forecasted P50 values
    # (topology definition — buses, lines, transformers — comes from your GIS/asset system)
    load_profile = build_pgm_load_profile(node_forecasts, topology)

    pgm = PowerGridModel(input_data=topology)
    power_flow_result = pgm.calculate_power_flow(update_data=load_profile)

    # Step 3: Check cable loading
    line_loading = power_flow_result["line"]["loading"]
    congested_lines = line_loading[line_loading > 1.0]  # > 100 % rated capacity

.. note::

   The ``build_pgm_load_profile`` helper above is illustrative. You will need to map OpenSTEF
   forecast output (indexed by prediction job ID) to the node IDs in your ``power-grid-model``
   topology. This mapping is specific to your asset data model.

This use case requires the most infrastructure: accurate topology data, a power flow solver, and forecasts at every relevant injection point. Start with the simpler single-asset use cases first and add topology-aware analysis once the base forecasts are validated.

---

Choosing the Right Use Case
----------------------------

The table below summarises the key differences to help you decide which configuration to start with:

.. list-table::
   :header-rows: 1
   :widths: 22 18 18 22 20

   * - Use Case
     - Aggregation Level
     - Primary Metric
     - Key Feature Drivers
     - Typical Horizon
   * - Congestion Management
     - Low to high
     - rMAE@peaks, rCRPS
     - Weather, load history
     - 24–48 h
   * - Free Space Estimation
     - Low to high
     - Same as congestion
     - Same as congestion
     - 24–48 h
   * - Grid Losses
     - Very high
     - Cost-weighted rMAE
     - Temporal patterns
     - 24 h
   * - Transport
     - Medium
     - rMAE (all hours)
     - Weather, load history
     - 24–48 h
   * - District Heating
     - Medium
     - rMAE
     - Temperature
     - 24 h
   * - MV Route Congestion
     - Low (per node)
     - Line loading %
     - Weather + topology
     - 24–48 h

If you are just getting started, congestion management or transport forecasts are the best entry points — they are the most mature, have the most community examples, and cover the widest range of grid operator needs.

---

.. note::

   For information on how to load input data from S3, Databricks, or InfluxDB for any of these
   use cases, see :doc:`data_integration`. For running these pipelines in production, including
   scheduling and containerisation, see :doc:`deployment`.