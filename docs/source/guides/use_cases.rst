Use Cases Overview
==================

OpenSTEF is a Python library designed to support diverse short-term energy forecasting applications. Each use case has specific accuracy requirements, optimization targets, and operational constraints. This guide helps you identify which approach matches your needs and understand what makes each use case unique.

Congestion Management Forecasting
----------------------------------

Congestion management represents OpenSTEF's primary use case, developed to address grid capacity limitations without requiring expensive infrastructure upgrades.

**When to use:** Grid operators need to predict peak load moments to implement demand response strategies and prevent equipment overload.

**Key characteristics:**

- **Primary focus:** Accuracy during peak load periods
- **Aggregation levels:** Highly variable, from individual customers to large substations
- **Typical applications:** Substation forecasting, individual customer predictions, medium-voltage substations (MSRs)

**Business context:** Grid congestion prevents new customer connections, creating significant societal impact. OpenSTEF enables operators to connect customers despite capacity limits by accurately forecasting when load will exceed equipment limits, allowing proactive demand response coordination.

.. code-block:: python

   from openstef import create_forecast
   
   # Configure for congestion management
   config = {
       'model_type': 'xgb',
       'optimization_target': 'peak_accuracy',
       'quantiles': [0.1, 0.5, 0.9, 0.95, 0.99],  # Focus on high quantiles
       'evaluation_metrics': ['rmae_at_peaks', 'precision_recall', 'rcrps']
   }
   
   forecast = create_forecast(
       data=load_data,
       config=config,
       target_column='net_load'
   )

**Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS for uncertainty quantification.

**Model optimization:** Emphasis on peak detection and high-quantile accuracy, with robust handling of high variability in low-aggregation scenarios.

Transport Forecasting
----------------------

Transport forecasts enable coordinated grid management between network operators at different voltage levels.

**When to use:** Grid operators need reliable forecasts to communicate planned energy usage to upstream operators (e.g., distribution to transmission) or receive forecasts from downstream customers.

**Key characteristics:**

- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregated points, balancing predictability with granularity
- **Business context:** Alliander provides transport forecasts to TenneT (transmission system operator) while receiving forecasts from customers

**Split-component requirements:** Some operators require transport forecasts separated into components (solar, wind, other), necessitating specialized model configurations.

.. code-block:: python

   # Standard transport forecast
   transport_config = {
       'model_type': 'linear',
       'optimization_target': 'overall_accuracy',
       'split_components': False,
       'evaluation_metrics': ['rmae']
   }
   
   # Split-component transport forecast
   split_config = {
       'model_type': 'ensemble',
       'optimization_target': 'overall_accuracy', 
       'split_components': True,
       'component_types': ['solar', 'wind', 'other'],
       'evaluation_metrics': ['rmae', 'component_rmae']
   }

**Key metrics:** rMAE across the entire forecast horizon.

**Model optimization:** Balanced performance with emphasis on reliability and consistency.

Grid Loss Forecasting
----------------------

Grid loss forecasting optimizes financial operations by predicting system-wide energy losses with consideration for market price fluctuations.

**When to use:** Grid operators need to minimize operational costs through accurate loss predictions that account for real-time energy market prices.

**Key characteristics:**

- **Primary focus:** Cost-weighted error minimization
- **Aggregation levels:** Highly aggregated points where system-level patterns dominate
- **Predictive characteristics:** Weather predictors have diminished impact; temporal and cyclic patterns become dominant

.. code-block:: python

   grid_loss_config = {
       'model_type': 'linear',
       'optimization_target': 'cost_weighted_accuracy',
       'cost_weighting': True,
       'market_price_integration': True,
       'feature_emphasis': 'temporal_patterns',
       'evaluation_metrics': ['rmae', 'cost_weighted_error']
   }

**Business context:** Financial optimization of grid operations considering market price fluctuations and operational costs.

**Key metrics:** Similar to transport forecasts plus total error cost minimization based on market prices.

**Model optimization:** Error weighting based on real-time market prices and operational costs.

Free Space Estimation and EV Charging Capacity
-----------------------------------------------

These emerging use cases address grid capacity planning for electric vehicle infrastructure and new customer connections.

**When to use:** Grid operators need to estimate available capacity for new connections or EV charging infrastructure deployment.

**Free space estimation characteristics:**

- **Focus:** Predicting unused grid capacity during different time periods
- **Applications:** New customer connection planning, infrastructure investment decisions
- **Methodology:** Combines load forecasting with equipment capacity limits

**EV charging capacity characteristics:**

- **Focus:** Estimating additional load capacity for electric vehicle charging
- **Applications:** Public charging infrastructure planning, residential EV adoption support
- **Methodology:** Integrates behavioral patterns with grid capacity constraints

.. code-block:: python

   # Free space estimation
   free_space_config = {
       'model_type': 'quantile',
       'optimization_target': 'capacity_estimation',
       'capacity_limits': equipment_ratings,
       'safety_margins': 0.8,  # 80% utilization threshold
       'evaluation_metrics': ['capacity_accuracy', 'safety_violations']
   }
   
   # EV charging capacity
   ev_capacity_config = {
       'model_type': 'ensemble',
       'optimization_target': 'charging_capacity',
       'behavioral_patterns': True,
       'charging_profiles': ev_charging_data,
       'evaluation_metrics': ['charging_accuracy', 'peak_capacity']
   }

District Heating Forecasting
-----------------------------

District heating represents OpenSTEF's expansion beyond electricity into thermal energy systems.

**When to use:** District heating operators need to forecast thermal demand for efficient heat generation and distribution planning.

**Key characteristics:**

- **Domain:** Thermal energy (not electricity)
- **Applications:** Heat generation planning, distribution optimization, storage management
- **Predictive factors:** Weather dependency (heating degree days), building thermal mass, occupancy patterns

.. note::
   District heating support is being developed for OpenSTEF 4.0. This represents the library's expansion into non-electricity energy domains.

.. code-block:: python

   # District heating configuration (OpenSTEF 4.0)
   heating_config = {
       'model_type': 'thermal',
       'optimization_target': 'heat_demand_accuracy',
       'weather_features': ['temperature', 'wind_speed', 'solar_radiation'],
       'thermal_features': ['building_mass', 'insulation_factor'],
       'evaluation_metrics': ['thermal_rmae', 'peak_heat_accuracy']
   }

MV Route Congestion with Topology Integration
----------------------------------------------

This advanced use case combines OpenSTEF with Power Grid Model (PGM) for topology-aware forecasting in medium-voltage networks.

**When to use:** Grid operators need congestion forecasts that account for network topology and power flow constraints in medium-voltage distribution networks.

**Integration approach:**

- **OpenSTEF:** Provides load forecasting at network nodes
- **Power Grid Model:** Calculates power flows and identifies congestion points
- **Combined output:** Topology-aware congestion predictions

.. code-block:: python

   # MV route congestion with PGM integration
   from power_grid_model import PowerGridModel
   
   mv_config = {
       'model_type': 'topology_aware',
       'optimization_target': 'route_congestion',
       'topology_integration': True,
       'pgm_model': grid_topology,
       'congestion_thresholds': line_ratings,
       'evaluation_metrics': ['route_accuracy', 'congestion_detection']
   }
   
   # Integrate with Power Grid Model
   pgm_model = PowerGridModel(grid_topology)
   
   # Combined forecasting workflow
   node_forecasts = create_forecast(data=node_data, config=mv_config)
   power_flows = pgm_model.calculate_power_flow(node_forecasts)
   congestion_points = identify_congestion(power_flows, line_ratings)

**Business context:** Medium-voltage network congestion management requires understanding both load patterns and network constraints.

**Key benefits:** Topology-aware predictions enable more precise congestion management and optimal network utilization.

Choosing the Right Use Case
----------------------------

**For peak-focused applications:** Use congestion management forecasting with high-quantile optimization.

**For overall accuracy:** Choose transport forecasting with balanced performance across all periods.

**For cost optimization:** Select grid loss forecasting with market price integration.

**For capacity planning:** Apply free space estimation or EV charging capacity forecasting.

**For thermal systems:** Use district heating forecasting (OpenSTEF 4.0).

**For network-aware predictions:** Combine MV route congestion with Power Grid Model integration.

Each use case can be customized through OpenSTEF's modular architecture. See the tutorials section for detailed implementation examples and the how-to guides for specific deployment scenarios.