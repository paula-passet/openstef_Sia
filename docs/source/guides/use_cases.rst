Common OpenSTEF Use Cases
=========================

OpenSTEF is a Python machine learning library designed for short-term energy forecasting across diverse applications. Each use case has specific accuracy requirements, optimization targets, and business contexts that determine the best forecasting approach. This guide helps you identify which use case matches your needs and understand the key differences between approaches.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case. Grid operators need precise predictions at congestion points to prevent overloads and implement effective mitigation strategies.

**When to use:** You need to predict peak load periods at specific grid locations to prevent equipment overload or implement demand response measures.

**Key characteristics:**

- **Primary focus:** Accuracy near peak load periods, not overall forecast accuracy
- **Aggregation levels:** Highly variable, from individual customers to substations
- **Optimization target:** Peak detection with high quantile accuracy
- **Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS

**What makes it different:** Models are optimized specifically for peak detection rather than general accuracy. Individual customer forecasts can be particularly challenging due to behavioral variability, while aggregated substation forecasts benefit from smoothing effects.

.. code-block:: python

   from openstef.model import OpenstfRegressor
   from openstef.feature_engineering import apply_features
   
   # Configure model for congestion management
   model = OpenstfRegressor(
       model_type='xgb',
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles for peak detection
       optimize_for_peaks=True
   )
   
   # Train with emphasis on peak periods
   model.fit(train_data, sample_weight=peak_weights)

**Business context:** Grid operators use these forecasts to call customers in advance for demand response, prevent overload through proactive measures, and optimize existing grid capacity utilization.

Transport Forecasts
-------------------

Transport forecasts enable coordinated grid management between different network operators by predicting energy flows at interconnection points.

**When to use:** You need to communicate planned energy usage to upstream operators or receive forecasts from downstream customers for grid coordination.

**Key characteristics:**

- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregated points balancing predictability and granularity
- **Optimization target:** Balanced performance across entire forecast horizon
- **Key metrics:** rMAE (relative Mean Absolute Error)

**What makes it different:** Unlike congestion management, transport forecasts prioritize consistent accuracy rather than peak detection. Some operators require component splits (solar, wind, other) necessitating specialized split-component models.

.. code-block:: python

   # Standard transport forecast configuration
   model = OpenstfRegressor(
       model_type='lgb',
       quantiles=[0.1, 0.5, 0.9],
       optimize_for_peaks=False  # Focus on overall accuracy
   )
   
   # For component-split requirements
   from openstef.tasks.split_forecast import create_component_forecasts
   
   components = create_component_forecasts(
       forecast_data=data,
       components=['solar', 'wind', 'other']
   )

**Business context:** Alliander provides transport forecasts to TenneT (transmission system operator) while receiving forecasts from customers, enabling coordinated capacity planning and grid management.

Grid Loss Forecasts
--------------------

Grid loss forecasting focuses on financial optimization by predicting system-wide energy losses with cost-weighted error minimization.

**When to use:** You need to optimize grid operations financially, considering market price fluctuations and operational costs.

**Key characteristics:**

- **Primary focus:** Cost-weighted error minimization based on market prices
- **Aggregation levels:** Highly aggregated points where system-level patterns dominate
- **Predictive characteristics:** Weather predictors have diminished impact; temporal patterns dominate
- **Key metrics:** rMAE plus total error cost minimization

**What makes it different:** Models incorporate real-time market prices for error weighting, making financial impact more important than pure forecast accuracy. System-wide behavioral trends become dominant factors over weather dependency.

.. code-block:: python

   # Grid loss forecast with cost weighting
   from openstef.model.regressors import create_custom_objective
   
   # Custom objective function considering market prices
   cost_objective = create_custom_objective(
       base_objective='mae',
       cost_weights=market_prices
   )
   
   model = OpenstfRegressor(
       model_type='xgb',
       objective=cost_objective,
       quantiles=[0.5]  # Focus on point forecasts for cost optimization
   )

**Business context:** Financial optimization of grid operations where the cost of forecast errors varies with market conditions and operational constraints.

Free Space Estimation
----------------------

Free space estimation predicts available grid capacity for new connections, particularly important for EV charging infrastructure and distributed energy resources.

**When to use:** You need to determine available grid capacity for new connections or assess headroom for additional load at specific grid points.

**Key characteristics:**

- **Primary focus:** Conservative capacity estimation to prevent future congestion
- **Aggregation levels:** Variable, depending on connection point and grid level
- **Optimization target:** Risk-averse forecasting with safety margins
- **Key metrics:** Peak load prediction with confidence intervals

**What makes it different:** Emphasizes conservative estimates with wide confidence intervals to ensure grid safety. Often combined with scenario analysis for different connection types and usage patterns.

.. code-block:: python

   # Conservative capacity estimation
   model = OpenstfRegressor(
       model_type='xgb',
       quantiles=[0.05, 0.1, 0.5, 0.9, 0.95],  # Wide quantile range
       optimize_for_peaks=True
   )
   
   # Calculate free space with safety margins
   peak_forecast = model.predict_quantile(data, quantile=0.9)
   grid_capacity = 1000  # kW
   safety_margin = 0.1
   
   free_space = grid_capacity * (1 - safety_margin) - peak_forecast

**Business context:** Grid operators need conservative capacity estimates to safely approve new connections without risking future congestion or equipment overload.

District Heating Forecasts
---------------------------

District heating represents OpenSTEF's expansion beyond electricity to thermal energy demand forecasting for community heating systems.

**When to use:** You operate district heating networks and need to predict thermal demand for efficient heat generation and distribution planning.

**Key characteristics:**

- **Primary focus:** Thermal demand patterns rather than electrical load
- **Aggregation levels:** Community or district level aggregation
- **Predictive characteristics:** Strong temperature dependency, different seasonal patterns
- **Key metrics:** Similar to transport forecasts but optimized for thermal systems

**What makes it different:** Thermal demand has different weather dependencies and temporal patterns compared to electrical load. Heating systems have thermal inertia affecting demand patterns.

.. note::
   District heating support is a community-driven use case expanding OpenSTEF beyond traditional electrical grid applications.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model for topology-aware analysis, enabling more sophisticated grid management.

**When to use:** You need congestion management that considers actual grid topology and power flows rather than treating each point independently.

**Key characteristics:**

- **Primary focus:** Topology-aware congestion prediction
- **Integration:** Combined with power-grid-model library
- **Optimization target:** Network-wide congestion prevention
- **Key metrics:** Congestion management metrics plus power flow constraints

**What makes it different:** Unlike standard point-based forecasting, this approach considers grid topology and power flows to predict congestion propagation and identify optimal intervention points.

.. code-block:: python

   # Integration with power-grid-model for topology awareness
   from power_grid_model import PowerGridModel
   from openstef.model import OpenstfRegressor
   
   # Create topology-aware forecasting pipeline
   grid_model = PowerGridModel(grid_topology_data)
   forecast_model = OpenstfRegressor(model_type='xgb')
   
   # Combine forecasts with power flow analysis
   forecasts = forecast_model.predict(forecast_data)
   power_flows = grid_model.calculate_power_flow(forecasts)
   
   # Identify congestion points considering topology
   congestion_analysis = analyze_congestion_with_topology(
       forecasts, power_flows, grid_model
   )

**Business context:** Advanced grid management requiring understanding of how congestion at one point affects the entire network, enabling more effective and coordinated intervention strategies.

.. note::
   [DIAGRAM: Comparison matrix showing use cases vs. key characteristics (aggregation level, optimization target, key metrics, weather dependency)]

Choosing the Right Approach
----------------------------

The choice between use cases depends on your specific requirements:

**For peak management:** Choose congestion management forecasts with peak-optimized models and high quantile focus.

**For grid coordination:** Use transport forecasts with balanced accuracy across all time periods.

**For cost optimization:** Implement grid loss forecasts with market price weighting.

**For capacity planning:** Apply free space estimation with conservative, wide-interval predictions.

**For thermal systems:** Adapt district heating approaches with temperature-focused feature engineering.

**For network-aware analysis:** Combine MV route congestion with power-grid-model integration.

Each approach can be customized further based on your specific data availability, accuracy requirements, and operational constraints. See the tutorials section for detailed implementation examples and the how-to guides for specific deployment scenarios.