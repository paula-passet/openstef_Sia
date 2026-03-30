Use Cases
==========

OpenSTEF is a Python machine learning library designed to support diverse short-term energy forecasting applications. Each use case has distinct characteristics in terms of aggregation levels, accuracy requirements, and optimization targets. This guide helps you identify which approach matches your specific forecasting needs.

Understanding Aggregation Levels
---------------------------------

The forecasting approach depends heavily on the aggregation level of your data:

- **Highly aggregated**: System-level data where temporal patterns dominate and weather has less impact
- **Medium aggregated**: Balanced predictability with moderate weather dependency  
- **Low aggregation**: Individual assets or small groups with high variability and strong weather dependency

Congestion Management Forecasts
-------------------------------

**When to use**: Grid operators need to predict peak load periods to prevent equipment overload and implement demand response strategies.

**Aggregation levels**: Highly variable - from individual customers to large substations. Individual customer forecasts are particularly challenging due to behavioral variability.

**Key characteristics**:

- Primary focus on accuracy during peak load periods (not overall accuracy)
- Requires probabilistic forecasts with confidence intervals
- Strong emphasis on peak detection capabilities
- Applications include substation forecasting, individual customer predictions, and MSRs (medium-voltage substations)

**Optimization targets**:

- Effective precision and recall for peak detection
- rMAE@50th quantile specifically at peaks
- rCRPS (Relative Continuous Ranked Probability Score) for probabilistic accuracy

**Business context**: Grid operators use these forecasts to call customers in advance and request load reduction with compensation, enabling new connections despite capacity constraints.

.. code-block:: python

   from openstef_core import create_forecast_pipeline
   
   # Configure for congestion management
   pipeline = create_forecast_pipeline(
       use_case="congestion_management",
       target_quantiles=[0.1, 0.5, 0.9],  # Probabilistic forecasts
       optimization_metric="rMAE_peaks",    # Focus on peak accuracy
       peak_detection=True
   )

Transport Forecasts
-------------------

**When to use**: Grid operators need reliable forecasts to communicate planned energy usage to upstream network operators (e.g., transmission system operators) and coordinate with downstream customers.

**Aggregation levels**: Medium aggregated points providing balanced predictability and granularity.

**Key characteristics**:

- Primary focus on overall forecast accuracy across all time periods
- Balanced performance requirements throughout the forecast horizon
- Some operators require component splitting (solar, wind, other)
- Used for grid coordination between different voltage levels

**Optimization targets**:

- rMAE (Relative Mean Absolute Error) across entire forecast period
- Reliability and consistency over peak detection

**Business context**: Enables coordinated grid management between transmission and distribution system operators. For example, Alliander provides transport forecasts to TenneT while receiving forecasts from customers.

.. code-block:: python

   # Standard transport forecast
   pipeline = create_forecast_pipeline(
       use_case="transport",
       optimization_metric="rMAE",
       component_splitting=False
   )
   
   # Transport forecast with component splitting
   pipeline_split = create_forecast_pipeline(
       use_case="transport",
       optimization_metric="rMAE", 
       component_splitting=True,
       components=["solar", "wind", "other"]
   )

Grid Loss Forecasts
-------------------

**When to use**: Financial optimization of grid operations considering market price fluctuations and operational costs.

**Aggregation levels**: Highly aggregated points where system-level temporal and cyclic patterns dominate.

**Key characteristics**:

- Primary focus on cost-weighted error minimization
- Weather predictors have diminished impact at this aggregation level
- Strong temporal patterns and system-wide behavioral trends
- Market price integration for cost optimization

**Optimization targets**:

- rMAE for baseline accuracy
- Total error cost minimization based on real-time market prices
- Error weighting based on operational costs

**Business context**: Optimizes financial performance by minimizing the cost impact of forecasting errors during different market conditions.

.. code-block:: python

   pipeline = create_forecast_pipeline(
       use_case="grid_losses",
       optimization_metric="cost_weighted_error",
       market_price_weighting=True,
       weather_dependency="low"  # Less weather impact at high aggregation
   )

Free Space Estimation
---------------------

**When to use**: Determining available grid capacity for new connections by forecasting unused capacity at grid connection points.

**Key characteristics**:

- Focuses on capacity utilization rather than absolute load
- Combines load forecasting with capacity constraints
- Critical for grid expansion planning and new connection approvals

**Business context**: Enables grid operators to approve new connections by accurately estimating available capacity without requiring immediate grid reinforcement.

EV Charging Capacity Estimation  
-------------------------------

**When to use**: Forecasting electric vehicle charging demand to optimize charging infrastructure and grid capacity planning.

**Key characteristics**:

- Highly dependent on behavioral patterns and charging schedules
- Strong correlation with time-of-day and day-of-week patterns
- Integration with smart charging strategies

**Business context**: Supports the transition to electric mobility by ensuring adequate charging infrastructure and grid capacity.

MV Route Congestion Management with Topology
--------------------------------------------

**When to use**: Advanced congestion management that considers the actual grid topology using power-grid-model integration.

**Key characteristics**:

- Combines OpenSTEF forecasting with power-grid-model topology analysis
- Enables topology-aware congestion prediction
- Supports advanced grid optimization strategies
- Requires detailed grid topology data

**Business context**: Provides more sophisticated congestion management by understanding how power flows through the actual grid topology, enabling more targeted interventions.

.. code-block:: python

   from openstef_core import create_forecast_pipeline
   from power_grid_model import PowerGridModel
   
   # Topology-aware congestion management
   pipeline = create_forecast_pipeline(
       use_case="mv_congestion_topology",
       topology_model=PowerGridModel(grid_data),
       optimization_metric="topology_aware_congestion"
   )

District Heating
----------------

**When to use**: Thermal demand forecasting for district heating systems (non-electricity related).

**Key characteristics**:

- Temperature-dependent demand patterns
- Different seasonal patterns compared to electricity
- Heat storage considerations
- Community-driven use case expanding OpenSTEF beyond electricity

**Business context**: Enables efficient operation of district heating systems by predicting thermal demand and optimizing heat production and distribution.

Choosing the Right Use Case
---------------------------

Consider these factors when selecting your approach:

**Data aggregation level**:

- Individual assets → Congestion management
- Medium aggregation → Transport forecasts  
- High aggregation → Grid losses

**Primary business goal**:

- Peak load management → Congestion management
- Grid coordination → Transport forecasts
- Cost optimization → Grid losses
- Capacity planning → Free space estimation

**Weather dependency**:

- High weather impact → Congestion management, EV charging
- Medium weather impact → Transport forecasts
- Low weather impact → Grid losses (high aggregation)

**Forecast horizon and accuracy requirements**:

- Peak-focused accuracy → Congestion management
- Overall accuracy → Transport forecasts
- Cost-weighted accuracy → Grid losses

Next Steps
----------

- For implementation details, see :doc:`../getting_started/tutorials`
- For deployment guidance, see :doc:`how_to_guides`  
- For technical concepts, see :doc:`../reference/concepts`
- For architecture overview, see :doc:`../reference/architecture`