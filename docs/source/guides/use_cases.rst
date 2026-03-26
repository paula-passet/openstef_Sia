OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed to handle diverse short-term energy forecasting scenarios. Each use case has distinct characteristics, optimization targets, and business requirements that influence model selection and evaluation metrics. This guide helps you identify which approach best matches your forecasting needs.

Understanding Use Case Categories
---------------------------------

OpenSTEF supports six primary use cases, each optimized for different operational requirements and data characteristics. The key differentiators are aggregation levels, forecast horizons, accuracy requirements, and business contexts.

.. note:: [DIAGRAM: Use case comparison matrix showing aggregation levels, key metrics, and business contexts]

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case, focusing on preventing grid overloads through accurate peak detection.

**When to use:** Grid operators need to identify potential congestion points and implement mitigation strategies like demand response or customer notifications.

**Key characteristics:**
- **Primary focus:** Accuracy during peak load periods
- **Aggregation levels:** Highly variable, from individual customers to large substations
- **Forecast horizon:** 24-48 hours ahead
- **Key metrics:** rMAE@50th quantile at peaks, effective precision and recall, rCRPS

**Typical applications:**
- Substation forecasting for load management
- Individual customer predictions for targeted interventions
- Medium-voltage substation (MSR) monitoring

.. code-block:: python

   from openstef_beam import create_forecast_pipeline
   from openstef_beam.metrics import rmae, precision_recall
   
   # Configure for congestion management
   pipeline = create_forecast_pipeline(
       use_case="congestion_management",
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles for peaks
       horizon_hours=48,
       peak_detection_threshold=0.8  # 80th percentile threshold
   )
   
   # Train with emphasis on peak periods
   model = pipeline.train(
       data=historical_load_data,
       target_column="load_mw",
       optimize_for_peaks=True
   )

**Business context:** Grid operators use these forecasts to call customers in advance for load reduction, prevent transformer overloads, and coordinate demand response programs. Individual customer forecasts can be particularly challenging due to behavioral variability.

Transport Forecasts
-------------------

Transport forecasts enable coordination between grid operators at different voltage levels, ensuring reliable energy flow planning across the network hierarchy.

**When to use:** Grid operators need to communicate planned energy usage to upstream operators (like TSOs) or receive forecasts from downstream customers.

**Key characteristics:**
- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregation providing predictability with useful granularity
- **Forecast horizon:** 24-48 hours ahead
- **Key metrics:** rMAE across entire forecast period

**Typical applications:**
- DSO-to-TSO communication (e.g., Alliander to TenneT)
- Downstream customer forecast integration
- Component-split forecasts (solar, wind, other)

.. code-block:: python

   # Configure for transport forecasting
   pipeline = create_forecast_pipeline(
       use_case="transport",
       quantiles=[0.5],  # Focus on median forecast
       horizon_hours=48,
       split_components=True  # Enable solar/wind/other splits
   )
   
   # Train for balanced performance
   model = pipeline.train(
       data=transport_data,
       target_column="transport_mw",
       weather_features=True,
       split_renewable_sources=True
   )

**Business context:** These forecasts enable coordinated grid management and capacity planning. Some operators require component splits to understand renewable generation patterns separately from base load.

Grid Loss Forecasts
--------------------

Grid loss forecasting optimizes the financial aspects of grid operations by predicting system losses and weighting errors based on market prices.

**When to use:** Financial optimization of grid operations where market price fluctuations significantly impact operational costs.

**Key characteristics:**
- **Primary focus:** Cost-weighted error minimization
- **Aggregation levels:** Highly aggregated where system-level patterns dominate
- **Forecast horizon:** 24-48 hours ahead
- **Key metrics:** rMAE plus total error cost based on market prices

**Predictive characteristics:**
- Weather predictors have diminished impact at high aggregation
- Temporal patterns and system-wide behaviors become dominant
- Market price integration for error weighting

.. code-block:: python

   # Configure for grid loss forecasting
   pipeline = create_forecast_pipeline(
       use_case="grid_losses",
       quantiles=[0.5],
       horizon_hours=48,
       cost_weighting=True
   )
   
   # Train with market price weighting
   model = pipeline.train(
       data=system_data,
       target_column="losses_mw",
       market_prices=price_data,
       temporal_features_emphasis=True,
       weather_features_reduced=True
   )

**Business context:** Grid operators minimize operational costs by accurately predicting system losses and timing energy purchases to coincide with favorable market conditions.

Free Space Estimation and EV Charging Capacity
-----------------------------------------------

Free space estimation helps grid operators understand available capacity for new connections, particularly important for EV charging infrastructure expansion.

**When to use:** Planning new grid connections, EV charging station deployment, or assessing available capacity for distributed energy resources.

**Key characteristics:**
- **Primary focus:** Capacity margin estimation during peak periods
- **Aggregation levels:** Variable, depending on connection point
- **Forecast horizon:** Multiple horizons for planning purposes
- **Key metrics:** Peak capacity utilization, safety margins

.. code-block:: python

   # Configure for capacity estimation
   pipeline = create_forecast_pipeline(
       use_case="capacity_estimation",
       quantiles=[0.5, 0.8, 0.9, 0.95],  # Multiple quantiles for risk assessment
       horizon_hours=48,
       capacity_analysis=True
   )
   
   # Analyze available capacity
   forecast = model.predict(future_data)
   available_capacity = pipeline.calculate_free_space(
       forecast=forecast,
       installed_capacity=transformer_capacity_mva,
       safety_margin=0.8  # 80% utilization limit
   )

**Business context:** Essential for grid expansion planning and enabling the energy transition by identifying optimal locations for new EV charging infrastructure or renewable connections.

MV Route Congestion with Topology Integration
---------------------------------------------

This advanced use case combines OpenSTEF forecasting with power-grid-model (PGM) for topology-aware congestion management on medium-voltage networks.

**When to use:** Detailed analysis of medium-voltage network congestion requiring consideration of network topology and power flows.

**Key characteristics:**
- **Primary focus:** Topology-aware congestion detection
- **Integration:** Combined with power-grid-model for network analysis
- **Aggregation levels:** Route-specific and node-specific forecasts
- **Key metrics:** Congestion probability, power flow violations

.. code-block:: python

   from openstef_beam import create_forecast_pipeline
   from power_grid_model import PowerGridModel
   
   # Configure for topology-aware forecasting
   pipeline = create_forecast_pipeline(
       use_case="mv_route_congestion",
       quantiles=[0.1, 0.5, 0.9],
       horizon_hours=24,
       topology_integration=True
   )
   
   # Initialize power grid model
   grid_model = PowerGridModel(input_data=network_topology)
   
   # Create forecasts for each network node
   node_forecasts = {}
   for node_id in network_nodes:
       node_forecasts[node_id] = pipeline.predict(
           data=node_data[node_id],
           node_id=node_id
       )
   
   # Analyze congestion with topology
   power_flow_results = grid_model.calculate_power_flow(
       update_data=node_forecasts
   )
   
   congestion_analysis = pipeline.analyze_congestion(
       forecasts=node_forecasts,
       power_flows=power_flow_results,
       network_limits=line_capacities
   )

**Business context:** Enables sophisticated congestion management strategies that consider network topology, allowing operators to identify not just where congestion will occur, but how it propagates through the network.

District Heating and Thermal Demand
------------------------------------

District heating represents OpenSTEF's expansion beyond electricity forecasting into thermal energy systems.

**When to use:** Thermal energy system operators need demand forecasting for district heating networks, combined heat and power systems, or thermal storage optimization.

**Key characteristics:**
- **Primary focus:** Thermal demand patterns and storage optimization
- **Aggregation levels:** District or building-level aggregation
- **Forecast horizon:** 24-72 hours for thermal inertia planning
- **Key metrics:** Thermal demand accuracy, storage optimization metrics

.. note:: District heating support is currently in development for OpenSTEF 4.0. This represents the library's expansion into non-electricity energy domains.

**Business context:** District heating operators optimize heat production, storage, and distribution to minimize costs while maintaining service quality. Thermal systems have different characteristics than electrical systems, including thermal inertia and storage capabilities.

Choosing the Right Use Case
---------------------------

Select your use case based on these decision criteria:

**For peak-focused applications:** Choose congestion management if you need to detect and prevent overloads, or free space estimation if you're planning capacity expansion.

**For coordination between operators:** Transport forecasts enable communication with upstream/downstream grid operators and support component-split analysis.

**For financial optimization:** Grid loss forecasts integrate market prices and focus on cost minimization rather than pure accuracy.

**For advanced network analysis:** MV route congestion combines forecasting with topology analysis using power-grid-model integration.

**For thermal systems:** District heating extends OpenSTEF beyond electricity into thermal energy domains.

.. note:: 
   Multiple use cases can be combined in a single deployment. Many operators use both congestion management and transport forecasts, applying different models and metrics to the same underlying data.

For implementation details and code examples, see the :doc:`../getting_started/tutorials` and :doc:`how_to_guides` sections.