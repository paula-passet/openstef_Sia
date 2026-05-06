Common Use Cases
----------------

Use Cases
=========

OpenSTEF was built around a concrete operational problem — predicting peak loads on electricity grid assets — but has since grown to cover a range of related forecasting problems. This page describes the main use cases, what distinguishes each one, and how to configure OpenSTEF appropriately for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

---

Congestion Management
---------------------

Congestion management is the original use case that motivated OpenSTEF's development. A grid operator needs to know *when* a transformer or cable is likely to approach or exceed its rated capacity, so that demand-response actions — calling customers to reduce consumption — can be triggered in advance.

The defining characteristic of this use case is that **accuracy near peak load periods matters far more than average accuracy**. A forecast that is excellent on quiet Tuesday afternoons but misses Friday evening peaks is operationally useless. This shapes every modelling choice: quantile selection, evaluation metrics, and model optimisation all focus on the upper tail of the load distribution.

Aggregation levels vary widely. A high-voltage substation serving thousands of customers is relatively predictable; a single medium-voltage substation (MSR) serving a small industrial estate is not. OpenSTEF handles both, but you should expect higher uncertainty intervals at lower aggregation levels.

**Key metrics:** rMAE at the 50th quantile during peak periods, precision/recall for congestion events, rCRPS.

**Typical configuration:**

.. code-block:: python

    from datetime import timedelta
    from openstef.workflow.create_forecast import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    congestion_config = ForecastingWorkflowConfig(
        model_id="transformer_hv_amsterdam_west",
        model="xgboost",
        # Wide quantile range to capture peak uncertainty
        quantiles=[Q(0.05), Q(0.25), Q(0.5), Q(0.75), Q(0.90), Q(0.95)],
        # 48-hour horizon gives enough lead time for demand response
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_80m",
        radiation_column="shortwave_radiation",
    )

The high quantiles (0.90, 0.95) are what the congestion alarm logic consumes. The median forecast is used for planning; the upper quantiles trigger operational decisions.

---

Free Space Estimation
---------------------

Free space estimation is the inverse of congestion management: rather than asking "will we exceed capacity?", it asks "how much headroom remains on this asset?". This is used for capacity planning — deciding whether a new large customer connection can be accommodated, or whether a grid reinforcement project can be deferred.

The calculation is straightforward once you have a probabilistic load forecast: free space at time *t* is the asset's rated capacity minus the upper-quantile forecast. The challenge is that free space must be estimated over a planning horizon of days to weeks, not just the next few hours.

.. code-block:: python

    from datetime import timedelta
    from openstef.workflow.create_forecast import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    free_space_config = ForecastingWorkflowConfig(
        model_id="cable_mv_route_14",
        model="lgbm",
        # Upper quantiles are the primary output for free space calculation
        quantiles=[Q(0.5), Q(0.75), Q(0.90), Q(0.95), Q(0.99)],
        # Longer horizon for capacity planning decisions
        horizons=[LeadTime.from_string("P7D")],
        sample_interval=timedelta(hours=1),
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
    )

    # After generating a forecast, compute free space:
    RATED_CAPACITY_MW = 12.5

    forecast = pipeline.predict(dataset)
    # free_space is the gap between rated capacity and the 95th-percentile load
    forecast["free_space_mw"] = RATED_CAPACITY_MW - forecast["forecast_0.95"]

.. note::

   Free space estimates are only as reliable as the upper quantiles of your model. Evaluate quantile calibration explicitly — see the evaluation utilities in ``openstef.evaluation`` — before using these values for investment decisions.

---

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses matters for two reasons: procurement (buying the right amount of energy on the day-ahead market to cover losses) and financial optimisation (losses are more expensive when market prices are high).

This use case has a different character from congestion management. Losses are measured at a highly aggregated level — typically the entire distribution network — so individual customer behaviour averages out. **Temporal and cyclic patterns dominate**: day-of-week, time-of-day, and seasonal effects are the strongest predictors. Weather features have less influence than in substation-level forecasting.

The key modelling difference is **cost-weighted error minimisation**. A forecast error of 1 MWh at €200/MWh is ten times more costly than the same error at €20/MWh. OpenSTEF supports this through the ``energy_price_column`` feature, which allows the model to learn the relationship between load, price, and loss.

.. code-block:: python

    from datetime import timedelta
    from openstef.workflow.create_forecast import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    grid_loss_config = ForecastingWorkflowConfig(
        model_id="grid_losses_region_north",
        model="gblinear",
        # Median forecast is primary; symmetric quantiles for uncertainty
        quantiles=[Q(0.1), Q(0.25), Q(0.5), Q(0.75), Q(0.9)],
        horizons=[LeadTime.from_string("PT36H")],
        sample_interval=timedelta(hours=1),
        # Market price as a feature — losses are more costly at high prices
        energy_price_column="EPEX_NL",
        temperature_column="temperature_2m",
    )

**Key metric:** rMAE, plus total error cost (sum of \|forecast - actual\| × market price over the horizon).

A linear model (``gblinear``) often performs competitively here because the dominant patterns are additive and cyclic. Tree-based models can overfit to noise at this aggregation level.

---

Transport Forecasts
-------------------

Transport forecasts serve a coordination function between grid operators at different voltage levels. A distribution system operator (DSO) like Alliander must report expected energy flows to the transmission system operator (TenneT) for the following day. Conversely, large industrial customers provide transport forecasts to the DSO so it can plan accordingly.

The accuracy target is **uniform across the entire forecast horizon** — there is no special emphasis on peaks. The forecast must be reliable at 2 AM as well as at 6 PM. This makes transport forecasting closer to a standard time-series regression problem.

Some operators require transport forecasts decomposed into components: solar generation, wind generation, and residual load. This requires separate models per component, then a combiner.

.. code-block:: python

    from datetime import timedelta
    from openstef.workflow.create_forecast import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    transport_config = ForecastingWorkflowConfig(
        model_id="transport_hv_substation_leiden",
        model="xgboost",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        # Day-ahead horizon matches market and operational planning cycles
        horizons=[LeadTime.from_string("PT36H")],
        sample_interval=timedelta(minutes=15),
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_80m",
        radiation_column="shortwave_radiation",
        pressure_column="surface_pressure",
    )

**Key metric:** rMAE across the full forecast horizon.

---

District Heating Demand
-----------------------

District heating is a non-electrical use case: forecasting thermal demand on a heat network. The physics differ from electricity (thermal inertia, pipe losses, storage buffers), but the forecasting problem is structurally similar — predict demand at a network node given weather and calendar features.

OpenSTEF's generalised feature engineering handles this well. Temperature is the dominant driver (heating demand rises sharply below ~15 °C), and the same cyclic calendar features that capture electricity demand patterns apply equally to heat demand.

.. code-block:: python

    from datetime import timedelta
    from openstef.workflow.create_forecast import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    district_heating_config = ForecastingWorkflowConfig(
        model_id="heat_network_amsterdam_noord",
        model="lgbm",
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        horizons=[LeadTime.from_string("PT24H")],
        sample_interval=timedelta(hours=1),
        # Temperature is the primary driver for heating demand
        temperature_column="temperature_2m",
        # Humidity affects perceived temperature and heating behaviour
        relative_humidity_column="relative_humidity_2m",
        # Country code controls holiday calendar — set appropriately
        country_code="NL",
    )

.. note::

   District heating support in OpenSTEF 4.0 is actively being developed. The configuration above reflects the current generalised interface; domain-specific enhancements (thermal storage features, pipe loss modelling) are planned for future releases.

---

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most complex use case. A single MV cable route may serve multiple substations, and the load on any segment of the route depends on the *topology* of the network — which switches are open or closed, which customers are connected where. A forecast that ignores topology will be wrong whenever the network is reconfigured.

OpenSTEF addresses this by integrating with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, a library for power flow calculations on distribution networks. The workflow is:

1. Forecast load at each individual node (substation or customer) using standard OpenSTEF pipelines.
2. Pass the per-node forecasts and the network topology to ``power-grid-model`` for a power flow calculation.
3. The power flow result gives cable loading on each route segment, accounting for the actual topology.

.. code-block:: python

    import power_grid_model as pgm
    from openstef.workflow.create_forecast import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q
    from datetime import timedelta

    # Step 1: One config per node on the MV route
    node_config = ForecastingWorkflowConfig(
        model_id="mv_node_<node_id>",   # instantiate per node
        model="xgboost",
        quantiles=[Q(0.5), Q(0.9), Q(0.95)],
        horizons=[LeadTime.from_string("PT48H")],
        sample_interval=timedelta(minutes=15),
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
    )

    # Step 2: After collecting per-node forecasts into `node_forecasts_df`,
    # run a power flow calculation to get route loading:
    #
    #   pgm_input = build_pgm_input(network_topology, node_forecasts_df)
    #   output = pgm.PowerGridModel(pgm_input).calculate_power_flow()
    #   route_loading = extract_cable_loading(output, rated_capacities)

.. note::

   The ``build_pgm_input`` and ``extract_cable_loading`` helpers are application-level code that you write for your specific network model. OpenSTEF provides the per-node forecasts; ``power-grid-model`` handles the physics. See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for network model construction.

This approach is more expensive computationally — you run one forecasting pipeline per node rather than one per route — but it is the only way to get physically correct route loading under variable topology.

---

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration differences across use cases:

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 20 15

   * - Use Case
     - Model
     - Quantiles
     - Horizon
     - Key Feature
   * - Congestion management
     - ``xgboost``
     - Wide (0.05–0.95)
     - 24–48 h
     - High quantiles
   * - Free space estimation
     - ``lgbm``
     - Upper tail (0.90–0.99)
     - 7 days
     - Rated capacity
   * - Grid losses
     - ``gblinear``
     - Symmetric (0.1–0.9)
     - 36 h
     - Market price
   * - Transport
     - ``xgboost``
     - Narrow (0.1–0.9)
     - 36 h
     - Full horizon accuracy
   * - District heating
     - ``lgbm``
     - Standard (0.1–0.9)
     - 24 h
     - Temperature
   * - MV route congestion
     - ``xgboost`` per node
     - Upper tail
     - 48 h
     - Topology (pgm)

---

Related Pages
-------------

- :doc:`data_integration` — how to feed measurement data from S3, Databricks, or InfluxDB into these pipelines
- :doc:`deployment` — production patterns for running multiple forecasting pipelines at scale
- :doc:`migration_v3_v4` — if you are migrating existing congestion or transport pipelines from V3