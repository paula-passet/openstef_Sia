Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was built — and is used in production — against a specific set of recurring problems in grid operations. This page describes those use cases in detail: what each one is, what makes it distinct from the others, and how to configure OpenSTEF's library components to address it.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

If you are new to OpenSTEF's configuration model, the ``ForecastingWorkflowConfig`` and ``create_forecasting_workflow`` factory are the entry points for all use cases described here. See the :doc:`data_integration` page for how to feed data into these workflows from S3, Databricks, or InfluxDB.

----

Congestion Management Forecasts
--------------------------------

Congestion management is the original and primary use case for OpenSTEF. A distribution grid operator connects customers despite capacity limits, then uses load forecasts to identify peak moments 24–48 hours ahead. When a forecast predicts that load will exceed equipment ratings, the operator contacts flexible customers in advance to reduce consumption or generation.

**What makes this use case distinctive:**

- Accuracy near peak load periods matters far more than average accuracy. A forecast that is excellent at median load but poor at the 90th percentile is not useful here.
- Aggregation levels vary enormously — from highly aggregated substations down to individual medium-voltage customers, where behavioural variability is high.
- The key metrics are precision and recall at peaks, rMAE at the 50th quantile during peak hours, and rCRPS.

**Configuration pattern:**

Congestion forecasts require wide quantile bands so that the operator can reason about worst-case load. A 48-hour horizon is typical, matching the advance notice needed for demand response calls.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_models.presets.forecasting_workflow import LocationConfig

    config = ForecastingWorkflowConfig(
        model_id="substation_hv_mv_001",
        model="xgboost",
        # Wide quantile bands for peak risk assessment
        quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
        target_column="load",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        location=LocationConfig(
            name="Substation Noord",
            country_code="NL",
        ),
    )

    workflow = create_forecasting_workflow(config=config)

.. note::

   At low aggregation levels (individual customers or small MSRs), load is highly unpredictable. Widen your quantile bands and consider ensemble models to capture behavioural variability. See the ensemble configuration example under `Transport Forecasts`_ below.

----

Free Space Estimation
---------------------

Free space estimation answers a different question: *how much remaining capacity does a grid asset have right now and over the coming days?* Rather than forecasting raw load, this use case derives a capacity headroom signal — typically by subtracting the load forecast (including its upper quantile) from the rated equipment limit.

**What makes this use case distinctive:**

- The output is a derived quantity, not a direct model target. OpenSTEF produces the load forecast; your application layer computes ``free_space = rated_capacity - forecast_upper_quantile``.
- Upper quantile accuracy is critical. An underestimated peak leads to an overestimated free space, which is the dangerous failure mode.
- This use case is often applied to cables and transformers simultaneously, requiring one forecast per asset.

**Configuration pattern:**

The configuration is structurally identical to congestion management, but you should emphasise the upper tail. Using ``Q(0.95)`` or ``Q(0.99)`` as your planning quantile gives a conservative (safe) free space estimate.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    config = ForecastingWorkflowConfig(
        model_id="cable_route_42",
        model="lgbm",
        # Conservative upper tail for safe capacity headroom
        quantiles=[Q(0.5), Q(0.9), Q(0.95), Q(0.99)],
        horizons=[LeadTime.from_string("PT72H")],
        sample_interval=timedelta(minutes=15),
        target_column="load",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
    )

    workflow = create_forecasting_workflow(config=config)

    # After prediction, derive free space in your application layer:
    # free_space = rated_capacity_mw - predictions["load_quantile_0.95"]

----

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated in cables and transformers during transmission. Forecasting losses accurately has direct financial consequences: grid operators procure energy on the wholesale market to cover losses, and procurement errors are settled at real-time market prices.

**What makes this use case distinctive:**

- The target is highly aggregated (system-level losses), so weather predictors have diminished impact compared to congestion forecasts. Temporal and cyclic patterns dominate.
- Error weighting by market price is important. A forecast error during a high-price hour costs more than the same error during a low-price hour.
- The ``energy_price_column`` field in ``ForecastingWorkflowConfig`` exists specifically for this use case — it allows the model to incorporate real-time price signals as a feature.
- Key metrics are rMAE (same as transport) plus total error cost minimisation.

**Configuration pattern:**

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    config = ForecastingWorkflowConfig(
        model_id="grid_losses_region_west",
        model="gblinear",
        # Median forecast is primary; cost weighting handles tail risk
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
        target_column="losses_mw",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        # Market price column enables price-aware feature engineering
        energy_price_column="EPEX_NL",
    )

    workflow = create_forecasting_workflow(config=config)

----

Transport Forecasts
-------------------

Transport forecasts report planned energy flows to upstream network operators and receive equivalent forecasts from downstream customers. For example, a distribution system operator provides transport forecasts to the transmission system operator (TSO) for capacity planning and grid balancing.

**What makes this use case distinctive:**

- Overall accuracy across the full forecast horizon matters equally — there is no special emphasis on peaks.
- Aggregation is medium: more predictable than individual customers, less smooth than system-level losses.
- Some operators require forecasts split into components (solar, wind, residual load). OpenSTEF provides ``ComponentSplitter`` for this purpose.
- The primary metric is rMAE.

**Configuration pattern (with component splitting):**

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_models.models.component_splitting import ComponentSplitter, ComponentSplitterConfig

    # Total load forecast
    config = ForecastingWorkflowConfig(
        model_id="transport_point_tso_feed",
        model="lgbm",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
        target_column="load",
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
    )

    workflow = create_forecasting_workflow(config=config)

    # Component splitter decomposes total load into solar, wind, residual
    splitter_config = ComponentSplitterConfig(
        source_column="load",
    )

.. note::

   ``ComponentSplitter`` is an abstract base class. Concrete implementations apply known generation ratios or train separate sub-models per component. Refer to ``openstef_models.models.component_splitting`` for available implementations.

----

District Heating Demand
-----------------------

District heating is a community-contributed use case that extends OpenSTEF beyond electricity into thermal demand forecasting. A district heating operator forecasts heat demand (in MW thermal) to schedule boiler dispatch and avoid under- or over-production.

**What makes this use case distinctive:**

- The target is thermal load, not electrical load. The feature engineering pipeline still applies: outdoor temperature is the dominant predictor, and cyclic time features (hour of day, day of week) capture behavioural patterns.
- There is no solar radiation or wind power component, so those columns can be omitted or set to zero.
- Holiday calendars remain relevant — heating demand drops on public holidays.
- This use case demonstrates OpenSTEF's domain-agnostic design: the library does not assume the target is electrical energy.

**Configuration pattern:**

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
    from openstef_models.presets.forecasting_workflow import LocationConfig

    config = ForecastingWorkflowConfig(
        model_id="district_heat_zone_a",
        model="xgboost",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT24H")],
        sample_interval=timedelta(minutes=60),
        target_column="heat_demand_mw",
        # Temperature is the primary driver for heating demand
        temperature_column="temperature_2m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        # Radiation and wind are less relevant but can be included
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        location=LocationConfig(
            name="District Heat Zone A",
            country_code="NL",
        ),
    )

    workflow = create_forecasting_workflow(config=config)

----

MV Route Congestion with Topology Awareness
-------------------------------------------

Medium-voltage (MV) route congestion is the most complex use case. A single MV cable route may serve multiple substations, and the load on the route is the sum of loads at all downstream nodes. Topology changes — switching operations, fault isolation — alter which nodes are connected to which route, making a purely point-based forecast insufficient.

**What makes this use case distinctive:**

- OpenSTEF is inherently point-based: it trains one model per grid location independently. For MV routes, you need to aggregate forecasts across nodes according to the current network topology.
- The ``power-grid-model`` library (a separate LF Energy project) provides the topology engine. OpenSTEF produces per-node load forecasts; power-grid-model performs the power flow calculation to derive route loading.
- This is the only use case where OpenSTEF is used as a component inside a larger topology-aware pipeline rather than as a standalone forecasting tool.
- A peer-reviewed paper has been published on this combined approach.

**Architectural pattern:**

.. mermaid:: /diagrams/user_guide/use_cases_diagram_2.mmd

The integration pattern is:

1. Train one ``ForecastingWorkflowConfig`` per MV node (transformer or load point).
2. At forecast time, retrieve the current network topology from your asset management system.
3. Pass per-node probabilistic forecasts and the topology to ``power-grid-model`` for power flow calculation.
4. Derive route loading and congestion probability from the power flow results.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Q
    from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

    # One config per MV node — repeat for each node on the route
    def make_node_config(node_id: str) -> ForecastingWorkflowConfig:
        return ForecastingWorkflowConfig(
            model_id=f"mv_node_{node_id}",
            model="xgboost",
            # Probabilistic output is essential for route-level risk aggregation
            quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
            horizons=[LeadTime.from_string("PT48H")],
            sample_interval=timedelta(minutes=15),
            target_column="load",
            temperature_column="temperature_2m",
            radiation_column="shortwave_radiation",
            wind_speed_column="wind_speed_80m",
            pressure_column="surface_pressure",
            relative_humidity_column="relative_humidity_2m",
        )

    node_ids = ["node_101", "node_102", "node_103"]
    node_workflows = {nid: create_forecasting_workflow(make_node_config(nid)) for nid in node_ids}

    # After training and prediction:
    # node_forecasts = {nid: workflow.predict(data[nid]) for nid, workflow in node_workflows.items()}
    # Pass node_forecasts + topology to power-grid-model for route aggregation

.. note::

   ``power-grid-model`` is a separate library and is not bundled with OpenSTEF. See the `LF Energy power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for topology setup.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration decisions for each use case:

+----------------------------+------------------+-----------------------------+---------------------+---------------------------+
| Use case                   | Typical model    | Quantiles emphasis          | Horizon             | Special fields            |
+============================+==================+=============================+=====================+===========================+
| Congestion management      | xgboost / lgbm   | Wide tails (0.05–0.95)      | 48 h                | —                         |
+----------------------------+------------------+-----------------------------+---------------------+---------------------------+
| Free space estimation      | lgbm             | High upper tail (0.95–0.99) | 48–72 h             | —                         |
+----------------------------+------------------+-----------------------------+---------------------+---------------------------+
| Grid loss                  | gblinear         | Median + moderate tails     | 48 h                | ``energy_price_column``   |
+----------------------------+------------------+-----------------------------+---------------------+---------------------------+
| Transport                  | lgbm / ensemble  | Balanced (0.1–0.9)          | 48 h                | ``ComponentSplitter``     |
+----------------------------+------------------+-----------------------------+---------------------+---------------------------+
| District heating           | xgboost          | Balanced (0.1–0.9)          | 24 h                | Non-electrical target     |
+----------------------------+------------------+-----------------------------+---------------------+---------------------------+
| MV route congestion        | xgboost          | Wide tails (0.05–0.95)      | 48 h                | power-grid-model topology |
+----------------------------+------------------+-----------------------------+---------------------+---------------------------+

----

Related Pages
-------------

- :doc:`data_integration` — How to read load measurements and weather data from S3, Databricks, and InfluxDB into the workflows described here.
- :doc:`deployment` — Production deployment patterns for running these workflows at scale (10,000+ grid locations).
- :doc:`migration_v3_v4` — If you have existing V3 prediction jobs, this page maps the old ``PredictionJob`` fields to the new ``ForecastingWorkflowConfig`` parameters.