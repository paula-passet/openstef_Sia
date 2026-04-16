Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but its design has been shaped by a set of recurring real-world problems faced by distribution system operators (DSOs) and other energy sector organisations. This page describes the most common use cases, explains what makes each one distinct from a modelling perspective, and shows how to configure OpenSTEF's library components for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

Each use case differs along three axes that drive modelling choices:

- **Aggregation level** — how many customers or assets are rolled up into the target signal
- **Accuracy focus** — whether you care about overall accuracy, peak accuracy, or cost-weighted accuracy
- **Output type** — a single probabilistic load forecast, a component-split forecast, or a topology-aware congestion probability

---

Congestion Management Forecasts
---------------------------------

Congestion management is the original motivation for OpenSTEF. A grid operator needs to know, hours to days in advance, whether a transformer or cable segment will be loaded beyond its rated capacity. When a congestion event is predicted, the operator can call customers in advance and ask them to reduce consumption or generation — often with financial compensation — before the physical limit is breached.

What makes this use case technically demanding is the **aggregation level**. Forecasting a high-voltage substation serving tens of thousands of customers is relatively smooth; forecasting a medium-voltage substation serving a single industrial customer or a small residential street is highly variable and behavioural. Both scenarios fall under congestion management, but they require different modelling strategies.

**Key characteristics:**

- Accuracy matters most near peak load, not during quiet overnight periods
- High-quantile forecasts (Q0.9, Q0.95) are as important as the median
- Metrics: rMAE at the 50th quantile during peak hours, rCRPS, effective precision and recall of peak detection

**Example configuration:**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflowConfig

   congestion_config = ForecastingWorkflowConfig(
       model_id="substation_hv_001",
       model="xgboost",
       # 48-hour horizon covers the next operational day plus buffer
       horizons=[LeadTime(timedelta(hours=48))],
       # Wide quantile range captures tail risk for peak detection
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       model_reuse_enable=True,
   )

The upper quantiles (Q0.9, Q0.95) are what the congestion management process actually acts on — the operator triggers a demand-response call when the Q0.9 forecast exceeds the asset rating, giving a 90 % confidence that an overload would otherwise occur.

---

Free Space Estimation
----------------------

Free space estimation is closely related to congestion management but asks the inverse question: rather than *will this asset overload?*, it asks *how much additional load can this asset safely absorb?* This is critical for connecting new customers, EV charging infrastructure, or distributed generation to the grid.

The remaining capacity at any moment is simply the asset rating minus the forecast load. Because the answer must be conservative — connecting a new customer based on an optimistic forecast and then causing an overload is unacceptable — free space estimation relies heavily on **upper-quantile forecasts**. The free space is computed from the high quantile of the load forecast, not the median.

.. code-block:: python

   import pandas as pd

   # Assume `forecast` is a ForecastDataset returned by a fitted workflow
   # Asset rating in MW
   asset_rating_mw = 10.0

   forecast_df = forecast.data

   # Conservative free space uses the 95th percentile of load
   forecast_df["free_space_mw"] = asset_rating_mw - forecast_df["forecast_0.95"]

   # Flag time windows where free space is sufficient for a new 1 MW connection
   forecast_df["connection_feasible"] = forecast_df["free_space_mw"] >= 1.0

The model configuration for free space estimation is identical to congestion management — the difference is entirely in how the output quantiles are consumed downstream.

---

Grid Loss Forecasts
--------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses accurately matters for two reasons: grid operators must purchase this energy on the wholesale market in advance, and the cost of being wrong is directly tied to real-time market prices.

This use case is distinctive because the target signal is **highly aggregated** — losses are measured at the system level, not per asset. At this aggregation level, individual behavioural variability averages out, and the dominant patterns become temporal (time of day, day of week, season) and system-wide. Weather predictors have less influence than in substation-level forecasts.

**Key characteristics:**

- Highly aggregated target signal; temporal patterns dominate
- Error weighting by real-time market prices — a 1 MW error at peak price costs far more than the same error overnight
- Metrics: rMAE plus total cost of forecast error weighted by EPEX spot prices

**Example configuration:**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflowConfig

   grid_loss_config = ForecastingWorkflowConfig(
       model_id="grid_loss_region_west",
       model="gblinear",
       # Day-ahead horizon aligns with energy market gate closure
       horizons=[LeadTime(timedelta(hours=36))],
       quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
       # Market price column enables cost-weighted model evaluation
       energy_price_column="EPEX_NL",
       temperature_column="temperature_2m",
       model_reuse_enable=True,
   )

.. note::

   The ``energy_price_column`` parameter connects the forecast to market price data. When present,
   OpenSTEF can weight training errors by the cost of being wrong at each time step, shifting the
   model's attention toward high-price periods.

---

Transport Forecasts
--------------------

Transport forecasts serve a coordination function between network operators at different voltage levels. A DSO like Alliander must report its expected energy offtake to the transmission system operator (TSO, e.g. TenneT) on a day-ahead basis. Conversely, large industrial customers report their expected consumption to the DSO. These forecasts underpin grid balancing at the national level.

Unlike congestion management, transport forecasts need to be **accurate across the entire forecast horizon**, not just at peaks. The target signal is at medium aggregation — a regional substation or a group of substations — which makes it more predictable than individual asset forecasts.

Some operators additionally require transport forecasts **split into components**: how much of the total load is attributable to solar generation, wind generation, and residual (other) demand. OpenSTEF supports this through its component splitting workflow.

**Example: component-split transport forecast**

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset, EnergyComponentDataset
   from openstef_models.workflows.custom_component_split_workflow import (
       CustomComponentSplitWorkflow,
   )
   from openstef_models.models.component_splitting.linear_component_splitter import (
       LinearComponentSplitter,
       LinearComponentSplitterConfig,
   )

   # Configure the component splitter
   splitter_config = LinearComponentSplitterConfig(
       source_column="load",
   )
   splitter = LinearComponentSplitter(config=splitter_config)

   workflow = CustomComponentSplitWorkflow(model=splitter)

   # `train_data` is a TimeSeriesDataset containing total load plus weather features
   workflow.fit(train_data)

   # Returns an EnergyComponentDataset with columns: wind, solar, other
   components: EnergyComponentDataset = workflow.predict(forecast_input)

   print(components.feature_names)  # ['wind', 'solar', 'other']

The ``EnergyComponentDataset`` returned by the splitter contains separate time series for each energy source. These can be reported individually to the TSO or used as inputs to downstream capacity planning tools.

---

District Heating Demand
------------------------

District heating is an example of OpenSTEF being applied **outside the electricity domain**. A district heating operator needs to forecast thermal demand — the amount of heat that will be drawn from the network — to optimise boiler scheduling and fuel procurement.

The forecasting problem is structurally identical to electricity load forecasting: a time series target with strong weather dependence (outdoor temperature drives heating demand), temporal patterns (morning warm-up, evening peak), and a need for probabilistic outputs to handle uncertainty. OpenSTEF's library components apply directly with minimal adaptation.

**What changes compared to electricity use cases:**

- The target column contains thermal power (MW_th) rather than electrical power (MW_e)
- Temperature is typically the dominant weather predictor; solar radiation and wind matter less
- There is no market price signal unless the operator participates in a heat market
- Congestion in a heat network is a hydraulic constraint, not an electrical one

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile as Q
   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflowConfig

   district_heating_config = ForecastingWorkflowConfig(
       model_id="district_heat_amsterdam_south",
       model="xgboost",
       horizons=[LeadTime(timedelta(hours=48))],
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       # Temperature is the primary driver for heating demand
       temperature_column="temperature_2m",
       # Wind chill effect can be captured via wind speed
       wind_speed_column="wind_speed_80m",
       model_reuse_enable=True,
   )

.. note::

   OpenSTEF does not include hydraulic network simulation. For MV heat route congestion (the thermal
   equivalent of MV route congestion), you would integrate OpenSTEF's demand forecasts with a
   separate hydraulic solver, following the same pattern described for MV route congestion below.

---

MV Route Congestion with Power-Grid-Model
------------------------------------------

Medium-voltage (MV) route congestion is the most topologically complex use case. A single MV cable route may serve dozens of transformers and connection points. Whether any segment of that route is overloaded depends not just on the total load but on **where** the load is located relative to the cable's rated sections — a question that requires network topology.

OpenSTEF addresses this by combining its probabilistic load forecasts with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, an open-source library for power flow calculations on distribution networks. The pattern is:

1. Use OpenSTEF to produce probabilistic load forecasts for each individual connection point or transformer along the route.
2. Feed those forecasts (at a chosen quantile) into power-grid-model as nodal injections.
3. Run a power flow calculation to determine line loading percentages across every cable segment.
4. Flag segments where the loading exceeds the rated capacity.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_2.mmd

**Sketch of the integration pattern:**

.. code-block:: python

   # Pseudocode illustrating the integration pattern.
   # Exact power-grid-model API details depend on your network model.

   from openstef_models.workflows.forecasting_workflow import (
       ForecastingWorkflowConfig,
       ForecastingWorkflow,
   )
   from openstef_core.types import LeadTime, Quantile as Q
   from datetime import timedelta

   # Step 1: Produce a conservative (high-quantile) load forecast for each node
   node_configs = {
       node_id: ForecastingWorkflowConfig(
           model_id=f"mv_node_{node_id}",
           model="xgboost",
           horizons=[LeadTime(timedelta(hours=24))],
           # Use Q0.9 for conservative congestion assessment
           quantiles=[Q(0.5), Q(0.9)],
           temperature_column="temperature_2m",
           radiation_column="shortwave_radiation",
       )
       for node_id in network_node_ids
   }

   node_forecasts = {}
   for node_id, config in node_configs.items():
       workflow = ForecastingWorkflow(config=config, storage=model_storage)
       node_forecasts[node_id] = workflow.predict(node_input_data[node_id])

   # Step 2: Extract Q0.9 nodal injections for each forecast timestep
   nodal_injections = {
       node_id: forecast.data["forecast_0.9"]
       for node_id, forecast in node_forecasts.items()
   }

   # Step 3: Pass to power-grid-model for power flow calculation
   # (power-grid-model API shown schematically)
   # pgm_result = run_power_flow(network_model, nodal_injections)
   # congested_segments = pgm_result[pgm_result["loading_pct"] > 100]

**What makes this use case different** from simple asset-level congestion forecasting is that the congestion point is not known in advance — it depends on the spatial distribution of load across the route. A transformer at the end of a long cable may be lightly loaded while the cable feeding it is already at capacity. Only a power flow calculation can reveal this.

---

Choosing the Right Configuration
----------------------------------

The table below summarises the key modelling choices for each use case:

.. list-table::
   :header-rows: 1
   :widths: 25 15 20 20 20

   * - Use Case
     - Aggregation
     - Critical Quantiles
     - Key Inputs
     - Primary Metric
   * - Congestion management
     - Low–medium
     - Q0.9, Q0.95
     - Load, weather
     - rMAE@peaks, rCRPS
   * - Free space estimation
     - Low–medium
     - Q0.95
     - Load, weather
     - Conservative capacity margin
   * - Grid loss
     - High
     - Q0.5
     - Load, weather, market price
     - Cost-weighted rMAE
   * - Transport
     - Medium
     - Q0.5
     - Load, weather
     - rMAE (all periods)
   * - Transport (component split)
     - Medium
     - Q0.5 per component
     - Load, weather, generation mix
     - rMAE per component
   * - District heating
     - Low–medium
     - Q0.1, Q0.5, Q0.9
     - Thermal load, temperature
     - rMAE
   * - MV route congestion
     - Low (per node)
     - Q0.9 (per node)
     - Load, weather, topology
     - Segment loading accuracy

---

Related Pages
--------------

- For connecting OpenSTEF to your data sources (InfluxDB, S3, Databricks), see :doc:`data_integration`.
- For running OpenSTEF forecasts in production pipelines, see :doc:`deployment`.
- If you are migrating an existing V3 pipeline to V4, see :doc:`migration_v3_v4`.