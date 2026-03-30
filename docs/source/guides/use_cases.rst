OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed to support diverse short-term energy forecasting applications. Each use case has specific requirements for accuracy, optimization targets, and aggregation levels. This guide helps you identify which approach matches your forecasting needs and understand the key differences between them.

Congestion Management Forecasts
-------------------------------

Congestion management forecasts focus on predicting peak load periods to prevent grid overloads and implement effective mitigation strategies.

**Primary focus:** Accuracy near peak load periods
**Aggregation levels:** Highly variable, from aggregated substations to individual customers
**Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS

**When to use:**

- Managing grid congestion at substations
- Predicting individual customer load patterns
- Forecasting medium-voltage substation (MSR) demand
- Implementing demand response programs

**What makes it different:**

- Emphasizes peak detection over overall accuracy
- Optimized for high-quantile accuracy
- Handles high variability in low-aggregation scenarios
- Individual customer forecasts can be particularly unpredictable due to behavioral variability

**Business context:** Grid operators use these forecasts to call customers in advance for demand response, prevent overloads, and coordinate congestion mitigation strategies.

.. code-block:: python

   from openstef.model import OpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   
   # Configure for congestion management
   model = OpenstfRegressor(
       model_type='xgb',
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles
       optimize_for_peaks=True
   )
   
   pipeline = create_forecast_pipeline(
       model=model,
       use_case='congestion_management'
   )

Transport Forecasts
-------------------

Transport forecasts provide reliable predictions for communicating planned energy usage between grid operators at different voltage levels.

**Primary focus:** Overall forecast accuracy across all time periods
**Aggregation levels:** Medium aggregated points balancing predictability and granularity
**Key metrics:** rMAE

**When to use:**

- Communicating forecasts to upstream transmission operators
- Receiving forecasts from downstream customers
- Coordinated grid management and capacity planning
- Split-component forecasting (solar, wind, other)

**What makes it different:**

- Balanced performance across the entire forecast horizon
- Emphasis on reliability over peak accuracy
- Often requires component decomposition
- Medium aggregation provides stable patterns

**Business context:** For example, Alliander provides transport forecasts to TenneT (transmission system operator) while receiving forecasts from customers, enabling coordinated grid management.

.. code-block:: python

   # Transport forecast with component splitting
   model = OpenstfRegressor(
       model_type='lgb',
       split_components=['solar', 'wind', 'other']
   )
   
   pipeline = create_forecast_pipeline(
       model=model,
       use_case='transport',
       aggregation_level='medium'
   )

Grid Loss Forecasts
-------------------

Grid loss forecasts optimize financial operations by minimizing cost-weighted errors based on market price fluctuations.

**Primary focus:** Overall accuracy with cost-weighted error minimization
**Aggregation levels:** Highly aggregated points where system-level patterns dominate
**Key metrics:** rMAE plus total error cost minimization based on market prices

**When to use:**

- Financial optimization of grid operations
- Market-based energy trading
- System-level loss prediction
- Cost-sensitive forecasting scenarios

**What makes it different:**

- Error weighting based on real-time market prices
- Weather predictors have diminished impact at high aggregation
- Temporal patterns and system-wide trends dominate
- Cost optimization over pure accuracy

**Predictive characteristics:** At high aggregation levels, weather dependency decreases while temporal and cyclic patterns become more important.

.. code-block:: python

   # Grid loss forecast with cost weighting
   model = OpenstfRegressor(
       model_type='linear',
       cost_weighted_errors=True,
       market_price_integration=True
   )
   
   pipeline = create_forecast_pipeline(
       model=model,
       use_case='grid_losses',
       aggregation_level='high'
   )

Free Space Estimation
---------------------

Free space estimation forecasts available grid capacity for new connections and demand growth planning.

**Primary focus:** Capacity planning and connection feasibility
**Aggregation levels:** Variable, depending on grid topology and planning requirements

**When to use:**

- Planning new customer connections
- Estimating available grid capacity
- Long-term infrastructure planning
- EV charging infrastructure deployment

**What makes it different:**

- Focuses on maximum capacity utilization
- Considers future demand scenarios
- Integrates with grid topology models
- Supports capacity planning workflows

District Heating Forecasts
---------------------------

District heating represents OpenSTEF's expansion beyond electrical grid applications into thermal demand forecasting.

**Primary focus:** Thermal demand prediction for heating networks
**Application domain:** Non-electrical energy systems

**When to use:**

- Community heating system management
- Thermal energy demand forecasting
- Heat pump coordination
- Combined heat and power optimization

**What makes it different:**

- Thermal rather than electrical demand patterns
- Different weather dependencies (heating degree days)
- Community-driven use case development
- Demonstrates OpenSTEF's domain flexibility

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model for topology-aware predictions.

**Primary focus:** Topology-aware congestion management
**Integration:** Combined with power-grid-model (PGM) library
**Aggregation levels:** Route-specific, considering grid topology

**When to use:**

- Route-specific congestion management
- Topology-aware load flow analysis
- Advanced grid optimization
- Research applications requiring grid modeling

**What makes it different:**

- Integrates grid topology information
- Uses power-grid-model for electrical calculations
- Route-specific rather than point-based forecasting
- Advanced modeling capabilities

.. note::
   This approach requires additional setup with power-grid-model. See the integration guides for detailed implementation examples.

.. code-block:: python

   from power_grid_model import PowerGridModel
   from openstef.integrations import PGMIntegration
   
   # Topology-aware forecasting
   grid_model = PowerGridModel(grid_data)
   
   integration = PGMIntegration(
       grid_model=grid_model,
       forecast_model=model
   )
   
   topology_forecast = integration.create_topology_aware_forecast()

Choosing the Right Use Case
---------------------------

Consider these factors when selecting your forecasting approach:

**Data aggregation level:**

- High aggregation: Grid losses, transport forecasts
- Medium aggregation: Transport forecasts, some congestion management
- Low aggregation: Individual customer forecasting, detailed congestion management

**Optimization target:**

- Peak accuracy: Congestion management
- Overall accuracy: Transport forecasts
- Cost optimization: Grid loss forecasts
- Capacity planning: Free space estimation

**Business context:**

- Operational grid management: Congestion forecasts
- Inter-operator communication: Transport forecasts
- Financial optimization: Grid loss forecasts
- Infrastructure planning: Free space estimation

**Technical requirements:**

- Standard forecasting: Most use cases
- Topology integration: MV route congestion
- Component splitting: Some transport forecasts
- Cost weighting: Grid loss forecasts

Next Steps
----------

- Start with the :doc:`../getting_started/quickstart` for basic forecasting setup
- Follow :doc:`../getting_started/tutorials` for comprehensive examples
- Check :doc:`how_to_guides` for specific implementation tasks
- Review :doc:`../reference/concepts` for deeper understanding of forecasting principles