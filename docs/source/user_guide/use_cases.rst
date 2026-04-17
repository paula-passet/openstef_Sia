Common OpenSTEF Use Cases
=========================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was shaped by a specific set
of real-world problems faced by distribution system operators (DSOs). This page describes the main use
cases the library supports, what makes each one distinct in terms of data, configuration, and model
choice, and how to set up a ``ForecastingWorkflowConfig`` for each scenario.

.. note::

   [DIAGRAM: Use case overview flowchart showing six forecasting scenarios (Congestion Management, Free Space Estimation, Grid Loss, Transport, District Heating, MV Route Congestion) arranged as branches from a central "OpenSTEF Library" node. Each branch shows the primary input data types (load history, weather, topology, market prices) flowing in and the output application (peak alerts, capacity headroom, cost optimisation, TSO reporting, thermal demand, route loading) flowing out.]

For information on how to load data into these workflows, see :doc:`data_integration`. For running
these patterns in production, see :doc:`deployment`.

----

Congestion Management
---------------------

Congestion management is OpenSTEF's founding use case and the one most thoroughly validated in
production. The core problem is straightforward: a substation or cable segment has a rated capacity,
and when forecast load exceeds that capacity the operator must intervene — typically by calling
customers in advance to curtail consumption or generation.

This use case is characterised by **high variability at low aggregation levels**. A single industrial
customer or medium-voltage substation (MSR) can swing dramatically from one day to the next, making
accurate peak detection harder than forecasting a highly aggregated feeder. The model must therefore
be tuned for tail accuracy, not just average error.

**What matters most:** precision and recall around peak events, high-quantile accuracy (P90/P95),
and reliable uncertainty bands so operators can set alert thresholds with confidence.

**Recommended metrics:** rMAE at the 50th quantile during peak periods, rCRPS.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_models.presets.forecasting_workflow import GBLinearForecaster

   # Congestion management: prioritise high-quantile accuracy over a 48-hour horizon.
   # Wide quantile range gives operators a conservative upper bound for alert thresholds.
   config = ForecastingWorkflowConfig(
       model_id="substation_msrA_congestion",
       model="xgboost",                         # XGBoost handles non-linear peak behaviour well
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9), Q(0.95)],  # High quantiles for conservative alerts
       sample_interval=timedelta(minutes=15),
       target_column="load",
       radiation_column="shortwave_radiation",
       temperature_column="temperature_2m",
       wind_speed_column="wind_speed_80m",
   )

   workflow = create_forecasting_workflow(config=config)

.. note::

   Individual customer and MSR-level forecasts are inherently noisier than substation aggregates.
   If precision/recall on peak events is poor, consider ensemble configurations or increasing the
   training window to capture more seasonal peak examples.

----

Free Space Estimation
---------------------

Free space estimation answers a different question: not *when will we exceed capacity*, but *how much
headroom remains on a given asset right now and over the next 48 hours*. This is used to decide
whether a new customer connection request can be accepted without reinforcement.

The forecast target is typically the **remaining capacity** — the rated limit of the transformer or
cable minus the predicted load. Because the output is a derived quantity, you can either train a model
directly on the residual or compute it as a post-processing step from a standard load forecast.

The probabilistic output is especially valuable here: the P10 lower bound of the free-space estimate
gives a conservative figure that a grid planner can use with confidence.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Free space: same load forecast, but we care about the lower bound of remaining capacity.
   # The P05 quantile of load gives the P95 lower bound of free space.
   config = ForecastingWorkflowConfig(
       model_id="transformer_T42_free_space",
       model="lgbm",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.05), Q(0.5), Q(0.95)],   # P05 load → conservative free-space estimate
       sample_interval=timedelta(minutes=15),
       target_column="load",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
   )

   workflow = create_forecasting_workflow(config=config)

   # After prediction, derive free space:
   # free_space_P95 = rated_capacity_mw - forecast.quantile_P05

.. note::

   The rated capacity of the asset is metadata you supply at the application layer — OpenSTEF
   forecasts load, and your code computes the residual. This keeps the library generic and lets you
   apply the same trained model to assets with different ratings.

----

Grid Loss Forecasting
---------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Accurate
loss forecasts matter financially: losses must be purchased on the day-ahead market, and buying too
much or too little has a direct cost.

This use case operates at a **high aggregation level** — typically the entire distribution network
or a large region. At this scale, individual customer behaviour averages out and system-level temporal
patterns (time of day, day of week, seasonal cycles) dominate. Weather variables have less predictive
power than in substation-level forecasts.

The key differentiator is **cost-weighted error minimisation**. An overestimate on a high-price day
is more expensive than the same overestimate on a low-price day, so the model should be aware of
market prices when computing sample weights during training.

**What matters most:** overall rMAE across the full horizon, plus minimising total procurement cost
weighted by real-time market prices.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Grid loss: highly aggregated, cost-weighted, market-price-aware.
   config = ForecastingWorkflowConfig(
       model_id="network_losses_region_north",
       model="gblinear",                         # GBLinear extrapolates well; good for smooth aggregates
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.5)],
       sample_interval=timedelta(minutes=15),
       target_column="load",
       energy_price_column="EPEX_NL",            # Market prices used for cost-weighted training
       temperature_column="temperature_2m",
   )

   workflow = create_forecasting_workflow(config=config)

.. note::

   If your market uses a different price index, pass the column name via ``energy_price_column``.
   The column must be present in your training dataset with the same timestamp index as the load
   measurements.

----

Transport Forecasts
-------------------

Transport forecasts are used to communicate planned energy flows between network operators. A DSO
such as Alliander provides these forecasts to the transmission system operator (TSO, e.g. TenneT)
while simultaneously receiving similar forecasts from large customers. The goal is coordinated
capacity planning across the entire supply chain.

Unlike congestion management, transport forecasts must be **accurate across the entire forecast
horizon**, not just at peaks. The aggregation level is medium — a high-voltage/medium-voltage
substation serving a district — which gives a reasonable balance between predictability and
granularity.

Some operators require transport forecasts **split by component**: solar generation, wind generation,
and residual demand are reported separately. This requires training separate models for each
component and combining them.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # Transport forecast — net load at an HV/MV substation.
   config_net = ForecastingWorkflowConfig(
       model_id="substation_HV42_transport_net",
       model="lgbm",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.5)],
       sample_interval=timedelta(minutes=15),
       target_column="load",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
   )

   # Component forecast — solar generation only (negative load convention).
   config_solar = ForecastingWorkflowConfig(
       model_id="substation_HV42_transport_solar",
       model="lgbm",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.5)],
       sample_interval=timedelta(minutes=15),
       target_column="solar_load",              # Separate target column for solar component
       radiation_column="shortwave_radiation",
   )

   workflow_net = create_forecasting_workflow(config=config_net)
   workflow_solar = create_forecasting_workflow(config=config_solar)

----

District Heating Demand
-----------------------

District heating is a community use case that extends OpenSTEF beyond electricity. The forecast
target is **thermal demand** — the heat load on a district heating network — rather than electrical
load. The physics are different (thermal inertia is much higher than electrical), but the forecasting
problem is structurally identical: predict a time series of demand values given weather and calendar
features.

Because district heating demand is strongly driven by outdoor temperature and building heat loss,
temperature features are the dominant predictors. Solar radiation matters too (passive solar gain
reduces heating demand). Wind speed can be relevant for exposed buildings.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # District heating: temperature-dominated, longer thermal time constants.
   config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_west",
       model="xgboost",
       horizons=[LeadTime.from_string("PT48H")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       sample_interval=timedelta(minutes=15),
       target_column="heat_load_mw",            # Thermal demand target
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
   )

   workflow = create_forecasting_workflow(config=config)

.. note::

   District heating support in OpenSTEF is a community-driven extension. The library's feature
   engineering pipeline is electricity-centric (it includes PV generation estimates from radiation,
   for example), so you may want to disable or replace those feature adders for a purely thermal
   use case. Custom feature adders can be injected via the workflow's transform pipeline.

----

MV Route Congestion with Topology
----------------------------------

MV (medium-voltage) route congestion is the most complex use case. A single MV feeder serves many
customers connected in a radial or meshed topology, and the loading on any cable segment depends on
the *sum* of all downstream demand. Identifying which segment will congest first requires knowing
the network topology — which customers are connected where, and what the impedance of each cable
section is.

OpenSTEF handles the **forecasting** side of this problem: it predicts load at individual connection
points or aggregated nodes. The topology-aware power flow calculation — determining which cable
segment carries which current — is handled by `power-grid-model
<https://github.com/PowerGridModel/power-grid-model>`_, a separate LF Energy library. The two
libraries are used together: OpenSTEF produces nodal load forecasts, and power-grid-model runs a
load flow to translate those forecasts into cable and transformer loading percentages.

**Typical workflow:**

1. Train one OpenSTEF model per connection point (or per aggregated node) on the MV feeder.
2. At forecast time, collect the probabilistic load forecasts for all nodes.
3. Feed the P50 (and optionally P90) nodal forecasts into power-grid-model as input loads.
4. Run a load flow to obtain current and loading percentage for every cable segment.
5. Flag segments where the P90 loading exceeds a threshold (e.g., 80 % of rated current).

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   # One config per node on the MV feeder.
   # Use consistent horizons and quantiles so outputs can be combined in the load flow.
   def make_node_config(node_id: str) -> ForecastingWorkflowConfig:
       return ForecastingWorkflowConfig(
           model_id=f"mv_feeder_F12_node_{node_id}",
           model="lgbm",
           horizons=[LeadTime.from_string("PT48H")],
           quantiles=[Q(0.5), Q(0.9)],          # P90 for conservative cable loading estimate
           sample_interval=timedelta(minutes=15),
           target_column="load",
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
       )

   node_ids = ["N01", "N02", "N03", "N04"]
   workflows = {nid: create_forecasting_workflow(config=make_node_config(nid)) for nid in node_ids}

   # After training and prediction, collect nodal forecasts:
   # nodal_p50 = {nid: workflows[nid].predict(dataset).quantile_P50 for nid in node_ids}
   # nodal_p90 = {nid: workflows[nid].predict(dataset).quantile_P90 for nid in node_ids}
   # Then pass nodal_p50 / nodal_p90 to power-grid-model for load flow calculation.

.. note::

   power-grid-model is a separate library maintained by the LF Energy community. OpenSTEF does not
   depend on it directly — the integration is at the application layer. See the
   `power-grid-model documentation <https://power-grid-model.readthedocs.io>`_ for load flow setup.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case.

.. list-table::
   :header-rows: 1
   :widths: 22 16 20 22 20

   * - Use case
     - Aggregation
     - Recommended model
     - Key quantiles
     - Special config
   * - Congestion management
     - Low–medium
     - ``xgboost``
     - P50, P90, P95
     - Wide quantile range for alert thresholds
   * - Free space estimation
     - Low–medium
     - ``lgbm``
     - P05, P50, P95
     - Derive residual at application layer
   * - Grid loss
     - High
     - ``gblinear``
     - P50
     - ``energy_price_column`` for cost weighting
   * - Transport
     - Medium
     - ``lgbm``
     - P50
     - Separate models per component if required
   * - District heating
     - Medium
     - ``xgboost``
     - P10, P50, P90
     - Consider replacing PV feature adders
   * - MV route congestion
     - Low (per node)
     - ``lgbm``
     - P50, P90
     - Combine with power-grid-model load flow

----

Next Steps
----------

- **Data integration** — learn how to feed measurement data from InfluxDB, S3, or Databricks into
  these workflows: :doc:`data_integration`
- **Production deployment** — patterns for scheduling and scaling these workflows in production:
  :doc:`deployment`
- **Migrating from V3** — if you have existing prediction jobs from OpenSTEF V3, see
  :doc:`migration_v3_v4` for the configuration changes required