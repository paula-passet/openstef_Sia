Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was shaped by concrete operational problems faced by grid operators. This page describes the main use cases the library supports, what distinguishes each one technically, and how to configure OpenSTEF appropriately for each scenario.

.. note:: [DIAGRAM: Use case overview showing the six main forecasting scenarios (congestion management, free space estimation, grid loss, transport, district heating, MV route congestion) arranged by aggregation level (individual asset → system-wide) and primary optimisation target (peak accuracy → cost-weighted accuracy → overall accuracy), with representative input data types (load measurements, weather, energy prices, topology) and downstream applications (demand response, capacity planning, financial optimisation, TSO reporting)]

All use cases share the same underlying library primitives — ``ForecastingWorkflowConfig``, probabilistic quantile outputs, and the feature engineering pipeline — but differ in which model type to choose, which quantiles matter most, and how to weight errors during training.

---

Congestion Management Forecasts
---------------------------------

This is the original and most operationally mature use case. A grid operator needs to know, up to 48 hours in advance, whether load at a specific transformer or cable will exceed its rated capacity. If a peak is predicted, customers can be called in advance to reduce consumption or generation voluntarily (with compensation), avoiding an overload without requiring immediate grid reinforcement.

**What makes it different:** The forecast only needs to be accurate *near peak load periods*. Nighttime accuracy is largely irrelevant. This asymmetry means you should optimise for high-quantile precision and peak detection rate rather than overall RMSE.

**Aggregation level:** Highly variable. Substation-level forecasts are relatively smooth and predictable; individual customer or MSR (medium-voltage substation room) forecasts can be highly volatile due to behavioural variability.

**Key metrics:** rMAE at the 50th quantile during peak hours, effective precision and recall for peak events, rCRPS.

**Configuration guidance:** Use ``xgboost`` or ``lgbm`` as the base model. Include high quantiles (0.9, 0.95) in your output so downstream systems can apply conservative thresholds. Emphasise peak-period sample weighting if your training data is imbalanced toward low-load periods.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Quantile as Q, LeadTime

   # High-quantile config for congestion management
   # Include upper quantiles to support conservative peak thresholds
   congestion_config = ForecastingWorkflowConfig(
       model_id="substation_hv_mv_transformer_01",
       run_name="congestion-v1",
       model="xgboost",
       horizons=[LeadTime.from_string("P2D")],
       quantiles=[Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "max"],
   )

   workflow = create_forecasting_workflow(congestion_config)

The ``Q(0.95)`` quantile is particularly important here: it gives the operator a conservative upper bound on expected load, reducing the risk of missed peaks at the cost of some false alarms.

---

Free Space Estimation
----------------------

Free space estimation answers a different question: *how much remaining capacity is available on a grid asset right now and in the near future?* Rather than predicting raw load, the output is the headroom between forecast load and the asset's rated limit. This is used for connection decisions — can a new customer be connected without triggering congestion?

**What makes it different:** The target variable is derived, not directly measured. You typically compute ``free_space = rated_capacity - forecast_load``, which means the forecast itself is a standard load forecast, but the post-processing and downstream interpretation differ. Uncertainty is critical: a narrow confidence interval around a load close to the rated limit is a very different situation from a wide interval.

**Aggregation level:** Asset-level (individual transformers or cable segments).

**Key metrics:** rCRPS (captures the full predictive distribution), coverage of the rated-capacity threshold.

**Configuration guidance:** The model configuration is nearly identical to congestion management, but you should ensure the full quantile spread is available so that downstream systems can compute probabilistic free-space estimates.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Quantile as Q, LeadTime

   # Full quantile spread for free space estimation
   free_space_config = ForecastingWorkflowConfig(
       model_id="cable_segment_lv_042",
       run_name="free-space-v1",
       model="lgbm",
       horizons=[LeadTime.from_string("P2D")],
       # Full spread: downstream code computes rated_capacity - Q(x) for each quantile
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   workflow = create_forecasting_workflow(free_space_config)

.. note::

   Free space is not a model output — it is computed in post-processing. OpenSTEF produces the load
   forecast with uncertainty bands; your application layer subtracts those from the rated capacity to
   derive available headroom.

---

Grid Loss Forecasts
--------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses is important for financial optimisation: grid operators must purchase energy on the day-ahead market to cover losses, and errors in that purchase are settled at real-time market prices, which can be significantly higher or lower.

**What makes it different:** Grid losses are a highly aggregated, system-level quantity. At this aggregation level, weather predictors have diminished importance — the dominant signals are temporal patterns (time of day, day of week, seasonal cycles) and system-wide load trends. The loss function during training should be weighted by market prices, so that errors during expensive hours cost more than errors during cheap hours.

**Aggregation level:** High — typically a whole network region or voltage level.

**Key metrics:** rMAE (similar to transport forecasts) plus total error cost, computed as the sum of ``|forecast_error| × market_price`` over the forecast horizon.

**Configuration guidance:** A linear model (``gblinear`` or ``lgbmlinear``) often performs competitively at this aggregation level because the dominant patterns are smooth and cyclic. Include the energy price column so the model can learn price-correlated load patterns.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Quantile as Q, LeadTime

   # Grid loss forecast — linear model, price-aware features
   grid_loss_config = ForecastingWorkflowConfig(
       model_id="region_north_grid_losses",
       run_name="grid-loss-v1",
       model="gblinear",
       horizons=[LeadTime.from_string("P1D")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       # Energy price is a key predictor for cost-weighted optimisation
       energy_price_column="EPEX_NL",
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       rolling_aggregate_features=["mean", "median"],
   )

   workflow = create_forecasting_workflow(grid_loss_config)

---

Transport Forecasts
--------------------

Transport forecasts describe the planned energy flow across a grid connection point over the coming days. Grid operators use these to communicate expected usage to upstream transmission system operators (TSOs) and to receive equivalent forecasts from downstream customers. For example, a distribution system operator (DSO) provides transport forecasts to the national TSO for balancing purposes.

**What makes it different:** Unlike congestion management, accuracy must be good *across the entire forecast horizon*, not just at peaks. The forecast is used for scheduling and coordination, so systematic bias or poor off-peak accuracy is just as problematic as missing a peak. Some operators also require component-split forecasts (solar contribution, wind contribution, residual load) rather than a single aggregate.

**Aggregation level:** Medium — typically a substation or grid connection point that aggregates many customers.

**Key metrics:** rMAE across the full horizon.

**Configuration guidance:** Balanced model with no special peak weighting. If component splits are required, train separate models per component and combine them.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Quantile as Q, LeadTime

   # Transport forecast — balanced accuracy across full horizon
   transport_config = ForecastingWorkflowConfig(
       model_id="hv_connection_point_tso_border",
       run_name="transport-v1",
       model="lgbm",
       horizons=[LeadTime.from_string("P3D")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       temperature_column="temperature_2m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       energy_price_column="EPEX_NL",
       rolling_aggregate_features=["mean", "median", "max", "min"],
   )

   workflow = create_forecasting_workflow(transport_config)

---

District Heating Demand
------------------------

District heating is a non-electricity use case: a network of insulated pipes distributes hot water from a central source to residential and commercial buildings. Forecasting thermal demand allows operators to schedule heat production efficiently and avoid both under-supply (customer discomfort) and over-supply (wasted energy).

**What makes it different:** The target variable is thermal power (MW of heat) rather than electrical load. Temperature is by far the dominant predictor — demand rises sharply in cold weather and drops to near zero in summer. Solar radiation matters indirectly (solar gains reduce heating demand), but electrical grid features like energy prices are irrelevant. The seasonal pattern is much stronger and more predictable than in electricity forecasting.

**Aggregation level:** Variable — from a single building connection to a whole district network.

**Key metrics:** rMAE, with particular attention to cold-snap events where demand can spike rapidly.

**Configuration guidance:** Drop electricity-specific features (energy price) and emphasise temperature-based features. A gradient boosting model works well; the strong temperature signal means even simpler models can achieve good accuracy.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Quantile as Q, LeadTime

   # District heating — temperature-driven, no electricity price features
   heating_config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_west",
       run_name="heating-v1",
       model="xgboost",
       horizons=[LeadTime.from_string("P2D")],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       # wind_speed affects heat loss from buildings
       wind_speed_column="wind_speed_80m",
       pressure_column="surface_pressure",
       relative_humidity_column="relative_humidity_2m",
       # No energy_price_column — not relevant for thermal demand
       rolling_aggregate_features=["mean", "median", "max"],
   )

   workflow = create_forecasting_workflow(heating_config)

.. note::

   District heating is a community-contributed use case. OpenSTEF's feature engineering pipeline is
   electricity-oriented by default, but the library's modular design allows you to add custom
   domain-specific transforms. See the API reference for ``openstef_models.transforms`` for extension
   points.

---

MV Route Congestion with Topology
-----------------------------------

Medium-voltage (MV) route congestion is the most technically complex use case. Rather than forecasting load at a single point, the goal is to determine whether a *path* through the MV grid — a sequence of cables and transformers connecting a source to a load — will become congested. This requires combining OpenSTEF's probabilistic load forecasts with a power flow model that understands grid topology.

**What makes it different:** A single load forecast is not enough. You need forecasts at *multiple nodes* along the route, then run a power flow calculation to determine the resulting current through each cable segment. This is where ``power-grid-model`` (a separate LF Energy library) comes in: it takes the node-level load forecasts as inputs and computes the resulting power flows, voltages, and cable loadings across the full topology.

**Aggregation level:** Individual assets (cables, transformers) within an MV feeder.

**Key metrics:** Probability that cable loading exceeds rated current, computed from the joint distribution of node-level forecasts propagated through the power flow model.

**Workflow pattern:**

1. Configure one ``ForecastingWorkflowConfig`` per node on the MV route.
2. Run OpenSTEF to produce probabilistic load forecasts (with quantiles) for each node.
3. Feed the quantile forecasts into ``power-grid-model`` as scenario inputs.
4. Evaluate cable loading across scenarios to estimate congestion probability.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       create_forecasting_workflow,
   )
   from openstef_core.types import Quantile as Q, LeadTime

   # Step 1: Create one workflow per node on the MV route
   node_ids = ["mv_node_A", "mv_node_B", "mv_node_C"]

   node_configs = [
       ForecastingWorkflowConfig(
           model_id=node_id,
           run_name="mv-route-v1",
           model="xgboost",
           horizons=[LeadTime.from_string("P2D")],
           # Full quantile spread — needed for power flow scenario analysis
           quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
           wind_speed_column="wind_speed_80m",
           pressure_column="surface_pressure",
           relative_humidity_column="relative_humidity_2m",
           rolling_aggregate_features=["mean", "max"],
       )
       for node_id in node_ids
   ]

   node_workflows = [create_forecasting_workflow(cfg) for cfg in node_configs]

   # Step 2: Run each workflow to get probabilistic forecasts per node
   # node_forecasts = {node_id: workflow.predict(...) for node_id, workflow in ...}

   # Step 3: Pass node_forecasts into power-grid-model for topology-aware
   # power flow calculations — see power-grid-model documentation for details.

.. note::

   ``power-grid-model`` is a separate LF Energy library and is not bundled with OpenSTEF. The
   integration is at the application layer: OpenSTEF produces the probabilistic inputs; your code
   orchestrates the power flow calculations. A published paper describes this combined approach in
   detail — see the OpenSTEF community resources for the reference.

---

Choosing the Right Configuration
----------------------------------

The table below summarises the key configuration choices for each use case:

.. list-table::
   :header-rows: 1
   :widths: 22 18 20 20 20

   * - Use Case
     - Recommended Model
     - Critical Quantiles
     - Key Features
     - Primary Metric
   * - Congestion management
     - ``xgboost``, ``lgbm``
     - 0.9, 0.95
     - Weather, rolling max
     - rMAE@peaks, rCRPS
   * - Free space estimation
     - ``lgbm``
     - Full spread (0.05–0.95)
     - Weather, rolling max
     - rCRPS
   * - Grid loss
     - ``gblinear``, ``lgbmlinear``
     - 0.1, 0.5, 0.9
     - Energy price, temporal
     - rMAE + cost
   * - Transport
     - ``lgbm``
     - 0.1, 0.5, 0.9
     - Weather, price, rolling
     - rMAE
   * - District heating
     - ``xgboost``
     - 0.1, 0.5, 0.9
     - Temperature, radiation
     - rMAE
   * - MV route congestion
     - ``xgboost`` (per node)
     - Full spread (0.05–0.95)
     - Weather, rolling max
     - Cable loading probability

---

.. note::

   The configurations shown on this page are starting points. Real deployments benefit from
   backtesting against historical data to tune quantile selection, horizon length, and feature sets
   for your specific grid assets. See the deployment page for production patterns and the data
   integration page for connecting OpenSTEF to live data sources.