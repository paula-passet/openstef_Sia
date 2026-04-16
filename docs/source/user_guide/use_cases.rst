Use Cases
=========

OpenSTEF is a general-purpose short-term energy forecasting library. While its origins lie in congestion management at Alliander, the same library — the same ``ForecastingWorkflowConfig``, the same model types, the same probabilistic output — applies across a wide range of grid and energy system problems. This page describes the most common use cases, what distinguishes each one, and how to configure OpenSTEF appropriately for each.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

The key insight is that OpenSTEF's probabilistic output — a set of quantile forecasts across a configurable horizon — is the common thread. What changes between use cases is primarily the *target variable*, the *aggregation level*, the *relevant features*, and the *metric you optimise for*.

----

Congestion Management Forecasts
---------------------------------

This is OpenSTEF's original and most mature use case. A grid operator needs to know, roughly 48 hours in advance, whether load at a specific transformer or cable will exceed its rated capacity. If a peak is forecast, the operator can call customers in advance and ask them to reduce consumption or generation in exchange for compensation — avoiding a physical overload without requiring immediate grid reinforcement.

**What makes this use case distinctive:**

- Aggregation levels vary enormously, from a single large industrial customer to a medium-voltage substation serving thousands of households.
- The cost of a missed peak (false negative) is much higher than the cost of an unnecessary call (false positive), so high-quantile accuracy matters more than median accuracy.
- Key metrics are precision and recall at peaks, rMAE at the 50th quantile during peak periods, and rCRPS.

**Configuration guidance:** Use a wide quantile set so that the upper tail (P90, P95) is well-calibrated. The ``xgboost`` or ``gblinear`` model types both work well; ``gblinear`` is preferred when you need the model to extrapolate beyond training data, which is important for rare peak events.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    congestion_config = ForecastingWorkflowConfig(
        model_id="transformer_hv_mv_001",
        model="gblinear",
        # 48-hour horizon covers the typical demand-response call window
        horizons=[LeadTime.from_string("PT48H")],
        # Wide quantile set — upper tail drives congestion decisions
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
        target_column="load",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "median", "max", "min"],
    )

    workflow = create_forecasting_workflow(config=congestion_config)

----

Free Space Estimation
----------------------

Free space estimation answers a related but different question: not "will we exceed capacity?" but "how much headroom remains?" This is used for connection planning — when a new customer (a solar farm, a factory, an EV charging hub) wants to connect to the grid, the operator needs to know whether the local cable or transformer can absorb the additional load at all times of day and year.

**What makes this use case distinctive:**

- The target is effectively the *complement* of the load forecast: ``rated_capacity - forecast_load``.
- The *lower* quantile tail (P05, P10) is what matters — you want a conservative estimate of the minimum available headroom.
- Aggregation is typically at the feeder or transformer level, similar to congestion management.
- Forecast horizons can be longer (days to weeks) when used for planning rather than real-time dispatch.

**Configuration guidance:** The model configuration is structurally identical to congestion management. The difference is downstream: after generating the load forecast, subtract from the known rated capacity to derive free space. Use the lower quantile columns (``quantile_P05``, ``quantile_P10``) as the conservative capacity estimate.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    free_space_config = ForecastingWorkflowConfig(
        model_id="feeder_capacity_zone_42",
        model="gblinear",
        horizons=[LeadTime.from_string("P3D")],  # 3-day horizon for planning
        # Lower tail drives the conservative free-space estimate
        quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
        target_column="load",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
    )

    workflow = create_forecasting_workflow(config=free_space_config)

    # After forecasting, derive free space from the lower quantile
    # rated_capacity_mw = 10.0  # example
    # forecast = workflow.predict(forecast_dataset)
    # free_space = rated_capacity_mw - forecast.data["quantile_P10"]

.. note::

   Free space estimation reuses the same load forecasting pipeline. The "free space" is a derived quantity computed after prediction, not a separate model type.

----

Grid Loss Forecasts
--------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses accurately matters for financial reasons: grid operators must purchase energy on the day-ahead market to cover losses, and errors in loss forecasts translate directly into imbalance costs.

**What makes this use case distinctive:**

- The target is highly aggregated — system-level losses across an entire grid region. At this aggregation level, individual customer behaviour averages out, and temporal and cyclic patterns (time of day, day of week, season) dominate.
- Weather predictors have diminished impact compared to congestion forecasts. Energy market prices become an important additional feature.
- The optimisation objective is cost-weighted: an error during a high-price hour costs more than the same error during a low-price hour.
- Key metrics are rMAE (similar to transport) plus total error cost minimised against market prices.

**Configuration guidance:** Include the ``energy_price_column`` to allow the model to weight errors by market conditions. The ``gblinear`` model's linear extrapolation is useful here because loss curves are approximately quadratic in load, and the model can learn this relationship.

.. code-block:: python

    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    grid_loss_config = ForecastingWorkflowConfig(
        model_id="grid_loss_region_north",
        model="gblinear",
        horizons=[LeadTime.from_string("PT36H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        target_column="load",  # target is measured grid loss in MW
        temperature_column="temperature_2m",
        # Energy price is a key feature for cost-weighted optimisation
        energy_price_column="EPEX_NL",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "median"],
    )

    workflow = create_forecasting_workflow(config=grid_loss_config)

----

Transport Forecasts
--------------------

Transport forecasts are used to communicate expected energy flows between network operators. A distribution system operator (DSO) like Alliander provides transport forecasts to the transmission system operator (TenneT) so that TenneT can plan balancing capacity. Simultaneously, the DSO receives forecasts from its large customers to plan its own operations.

**What makes this use case distinctive:**

- Aggregation is at a medium level — typically a high-voltage/medium-voltage substation serving a whole district or town. This makes the signal more predictable than individual customer forecasts.
- Accuracy across the *entire* forecast horizon matters equally, not just at peaks. The primary metric is rMAE.
- Some operators require transport forecasts decomposed into components (solar generation, wind generation, residual load). This requires separate models per component, which are then summed.
- Reliability and consistency are paramount — downstream operators depend on these forecasts for their own planning.

**Configuration guidance:** A balanced quantile set centred on the median is appropriate. For component decomposition, train a separate ``ForecastingWorkflowConfig`` per component (solar, wind, other) and aggregate the outputs.

.. code-block:: python

    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    # Example: residual load component (total minus solar and wind)
    transport_config = ForecastingWorkflowConfig(
        model_id="transport_substation_hv_007_residual",
        model="xgboost",
        horizons=[LeadTime.from_string("PT48H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        target_column="load",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "median", "max"],
    )

    workflow = create_forecasting_workflow(config=transport_config)

----

District Heating Demand
------------------------

District heating is a community use case that extends OpenSTEF beyond electricity. A district heating operator needs to forecast thermal demand — how much hot water the network must deliver — to schedule boiler output and avoid both under-supply (cold buildings) and over-supply (wasted energy).

**What makes this use case distinctive:**

- The target variable is thermal load (e.g., GJ/h or MW thermal) rather than electrical load.
- Temperature is by far the dominant predictor. Wind speed and solar radiation also matter (wind chill, solar gains reducing heating demand).
- Demand patterns are strongly seasonal and respond sharply to weather changes, making short-term forecasts (6–24 hours) particularly valuable for scheduling.
- This is a non-DSO/TSO application — OpenSTEF's domain-agnostic library design means the same pipeline works without modification, simply by pointing ``target_column`` at thermal measurements.

**Configuration guidance:** Reduce the feature set to weather-dominant inputs. A shorter horizon (24 hours) is typically sufficient for operational scheduling. The ``xgboost`` model handles the nonlinear temperature-demand relationship well.

.. code-block:: python

    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    district_heating_config = ForecastingWorkflowConfig(
        model_id="district_heating_zone_centrum",
        model="xgboost",
        horizons=[LeadTime.from_string("PT24H")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        # target_column points at thermal load measurements
        target_column="thermal_load_mw",
        # Temperature is the dominant driver for heating demand
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_10m",
        radiation_column="shortwave_radiation",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "min"],
    )

    workflow = create_forecasting_workflow(config=district_heating_config)

.. note::

   District heating support in OpenSTEF V4 is actively evolving. The configuration above reflects the current library API; domain-specific transforms for thermal systems are planned for future releases.

----

MV Route Congestion with Topology
-----------------------------------

Medium-voltage (MV) route congestion is the most complex use case. Rather than forecasting load at a single point, the goal is to determine whether a *path* through the MV grid — a sequence of cables connecting a substation to a set of customers — will become congested. This requires combining OpenSTEF's load forecasts with a power flow calculation using the network topology.

**What makes this use case distinctive:**

- Load forecasts are generated for individual nodes or feeders along the MV route using the standard OpenSTEF pipeline.
- These forecasts are then fed into a power-grid-model (the open-source power flow library) to compute cable loading along each route segment.
- The congestion signal is derived from the power flow result, not directly from the load forecast.
- This is a two-stage pipeline: OpenSTEF handles the forecasting stage; power-grid-model handles the physics stage.

**Configuration guidance:** Each node on the MV route needs its own ``ForecastingWorkflowConfig`` with a ``model_id`` that maps to the corresponding node in the topology. Forecast horizons should match the operational window for congestion intervention (typically 24–48 hours).

.. code-block:: python

    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    # Configure one workflow per MV node; model_id maps to topology node ID
    def make_mv_node_config(node_id: str) -> ForecastingWorkflowConfig:
        return ForecastingWorkflowConfig(
            model_id=f"mv_node_{node_id}",
            model="gblinear",
            horizons=[LeadTime.from_string("PT48H")],
            quantiles=[Q(0.05), Q(0.5), Q(0.95)],
            target_column="load",
            temperature_column="temperature_2m",
            radiation_column="shortwave_radiation",
            wind_speed_column="wind_speed_80m",
            pressure_column="surface_pressure",
            relative_humidity_column="relative_humidity_2m",
        )

    # Build a workflow for each node in the route
    node_ids = ["node_A1", "node_A2", "node_A3"]
    node_workflows = {nid: create_forecasting_workflow(make_mv_node_config(nid)) for nid in node_ids}

    # After forecasting each node, pass the median forecasts to power-grid-model
    # for power flow calculation to determine cable loading per route segment.

.. note::

   The power-grid-model integration is handled outside OpenSTEF. OpenSTEF's role is to produce the per-node load forecasts; the topology-aware congestion calculation is the responsibility of the downstream power flow engine.

----

Choosing the Right Configuration
----------------------------------

The table below summarises the key configuration choices for each use case:

+---------------------------+----------------+---------------------------+---------------------+-------------------------+
| Use Case                  | Model          | Horizon                   | Critical Quantiles  | Key Extra Feature       |
+===========================+================+===========================+=====================+=========================+
| Congestion management     | gblinear       | 48 h                      | P90, P95            | Rolling aggregates      |
+---------------------------+----------------+---------------------------+---------------------+-------------------------+
| Free space estimation     | gblinear       | 48 h – 3 days             | P05, P10            | Rolling aggregates      |
+---------------------------+----------------+---------------------------+---------------------+-------------------------+
| Grid loss                 | gblinear       | 36 h                      | P50                 | Energy price            |
+---------------------------+----------------+---------------------------+---------------------+-------------------------+
| Transport                 | xgboost        | 48 h                      | P10, P50, P90       | Component decomposition |
+---------------------------+----------------+---------------------------+---------------------+-------------------------+
| District heating          | xgboost        | 24 h                      | P10, P50, P90       | Temperature (dominant)  |
+---------------------------+----------------+---------------------------+---------------------+-------------------------+
| MV route congestion       | gblinear       | 48 h                      | P05, P50, P95       | Topology (external)     |
+---------------------------+----------------+---------------------------+---------------------+-------------------------+

The model types listed are starting points, not hard requirements. OpenSTEF supports ``xgboost``, ``gblinear``, ``lgbm``, ``lgbmlinear``, ``flatliner``, and ``median`` — benchmarking on your own data is always recommended.

----

Related Pages
--------------

- For connecting OpenSTEF to your data sources (InfluxDB, S3, Databricks), see :doc:`data_integration`.
- For running these workflows in production at scale, see :doc:`deployment`.
- If you are migrating an existing V3 prediction job configuration to V4, see :doc:`migration_v3_v4`.