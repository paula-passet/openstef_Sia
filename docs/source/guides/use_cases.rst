OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed to support diverse short-term energy forecasting applications. Each use case has distinct characteristics in terms of aggregation levels, optimization targets, and business requirements. This guide helps you identify which approach matches your specific forecasting needs.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case. Grid operators use these forecasts to prevent overloads and implement proactive demand response strategies.

**Primary Focus**
   Accuracy during peak load periods is critical. The model must excel at detecting when congestion is likely to occur.

**Aggregation Levels**
   Highly variable, ranging from very aggregated points down to individual customer forecasts. Individual customer predictions can be particularly challenging due to behavioral variability.

**Typical Applications**
   - Substation load forecasting
   - Individual customer demand prediction  
   - Medium-voltage substation (MSR) forecasting
   - Peak moment identification for demand response

**Key Metrics**
   - Effective precision and recall for peak detection
   - rMAE@50th quantile at peaks
   - rCRPS (ranked Continuous Ranked Probability Score)

**Model Optimization**
   Emphasis on peak detection and high-quantile accuracy, with robust handling of high variability in low-aggregation scenarios.

.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import create_forecast_pipeline
   
   # Configure for congestion management
   model = XGBQuantileOpenstfRegressor(
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles for peak detection
       max_depth=8,
       n_estimators=200
   )
   
   pipeline = create_forecast_pipeline(
       model=model,
       optimize_for="peak_detection"
   )

**When to Use**
   Choose congestion management forecasting when you need to prevent grid overloads, implement demand response programs, or manage capacity constraints at specific grid locations.

Transport Forecasts
-------------------

Transport forecasts provide overall energy flow predictions that grid operators use to coordinate with upstream transmission operators and downstream customers.

**Primary Focus**
   Overall forecast accuracy across all time periods, not just peaks. Reliability and consistency are more important than extreme event detection.

**Aggregation Levels**
   Medium aggregated points that balance predictability with operational granularity.

**Business Context**
   Grid operators like Alliander provide transport forecasts to transmission operators like TenneT while receiving similar forecasts from their customers. This enables coordinated grid management and capacity planning. Some operators require component-split forecasts (solar, wind, other), necessitating specialized models.

**Key Metrics**
   - rMAE (relative Mean Absolute Error)
   - Overall forecast reliability

**Model Optimization**
   Balanced performance across the entire forecast horizon with emphasis on consistency and reliability.

.. code-block:: python

   from openstef.model.regressors import LGBMOpenstfRegressor
   
   # Configure for transport forecasting
   model = LGBMOpenstfRegressor(
       objective='regression',
       num_leaves=50,
       learning_rate=0.1
   )
   
   pipeline = create_forecast_pipeline(
       model=model,
       optimize_for="overall_accuracy",
       split_components=True  # For solar/wind/other breakdown
   )

**When to Use**
   Select transport forecasting when you need to communicate planned energy usage to upstream operators, coordinate with neighboring grid areas, or provide reliable baseline forecasts for operational planning.

Grid Loss Forecasts
-------------------

Grid loss forecasting focuses on predicting energy losses within the distribution system, often for financial optimization and market operations.

**Primary Focus**
   Overall accuracy combined with cost-weighted error minimization based on real-time market prices.

**Aggregation Levels**
   Highly aggregated points where system-level temporal and cyclic patterns dominate individual customer behavior.

**Predictive Characteristics**
   Weather predictors have diminished impact at this aggregation level. Temporal patterns, system-wide behavioral trends, and market dynamics become the dominant factors.

**Business Context**
   Financial optimization of grid operations considering market price fluctuations. Errors during high-price periods are more costly than errors during low-price periods.

**Key Metrics**
   - rMAE for overall accuracy
   - Total error cost minimization based on market prices
   - Price-weighted forecast performance

**Model Optimization**
   Error weighting based on real-time market prices and operational costs, with reduced emphasis on weather features.

.. code-block:: python

   from openstef.model.regressors import LinearQuantileOpenstfRegressor
   
   # Configure for grid loss forecasting
   model = LinearQuantileOpenstfRegressor(
       quantiles=[0.25, 0.5, 0.75],
       fit_intercept=True
   )
   
   pipeline = create_forecast_pipeline(
       model=model,
       optimize_for="cost_weighted_accuracy",
       price_weighting=True,
       weather_features_reduced=True
   )

**When to Use**
   Use grid loss forecasting when you need to optimize operational costs, participate in energy markets, or minimize financial impact of forecast errors in highly aggregated system-level predictions.

Free Space Estimation
---------------------

Free space estimation determines available capacity for new connections or increased load at specific grid locations.

**Primary Focus**
   Conservative estimation of available capacity while maintaining grid stability and safety margins.

**Aggregation Levels**
   Varies by application, from individual connection points to substation-level capacity assessment.

**Business Context**
   Grid operators need to assess how much additional load can be safely connected without triggering congestion or violating operational limits.

**Key Considerations**
   - Safety margins and conservative estimates
   - Peak load scenarios and worst-case conditions
   - Integration with capacity planning processes

**When to Use**
   Apply free space estimation when evaluating new connection requests, planning grid expansions, or assessing available capacity for electric vehicle charging infrastructure.

EV Charging Capacity Estimation
-------------------------------

Specialized forecasting for electric vehicle charging infrastructure planning and real-time capacity management.

**Primary Focus**
   Predicting charging demand patterns and available capacity for EV infrastructure.

**Aggregation Levels**
   Ranges from individual charging points to neighborhood-level charging hubs.

**Business Context**
   Supporting the rapid expansion of electric vehicle infrastructure while maintaining grid stability and optimizing charging schedules.

**Key Considerations**
   - Charging behavior patterns
   - Time-of-use optimization
   - Grid impact assessment
   - Dynamic pricing integration

**When to Use**
   Choose EV charging capacity estimation when planning charging infrastructure, optimizing charging schedules, or managing real-time charging demand.

MV Route Congestion with Topology
---------------------------------

Advanced congestion management that incorporates grid topology using power-grid-model for topology-aware forecasting.

**Primary Focus**
   Topology-aware congestion prediction that considers power flows and grid constraints across the network.

**Integration with Power-Grid-Model**
   OpenSTEF can be combined with power-grid-model to enable topology-aware forecasting, moving beyond point-based predictions to network-aware analysis.

**Business Context**
   More sophisticated congestion management that considers how power flows through the actual grid topology, enabling better-informed operational decisions.

**Technical Requirements**
   - Grid topology data
   - Integration with power-grid-model library
   - Network analysis capabilities

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from power_grid_model import PowerGridModel
   
   # Topology-aware forecasting setup
   pipeline = create_forecast_pipeline(
       model=model,
       topology_aware=True,
       grid_model=PowerGridModel(grid_data)
   )

**When to Use**
   Select topology-aware forecasting when you have detailed grid topology data and need to consider power flow constraints across the network, not just at individual points.

District Heating
----------------

Non-electricity forecasting application for thermal demand prediction in district heating systems.

**Primary Focus**
   Thermal demand forecasting with different seasonal patterns and weather dependencies compared to electrical load.

**Key Differences from Electrical Forecasting**
   - Temperature dependency is more direct and linear
   - Seasonal patterns differ significantly
   - Storage and thermal inertia considerations
   - Different peak patterns (heating vs. cooling seasons)

**Business Context**
   Community-driven use case extending OpenSTEF beyond traditional electrical grid applications to thermal energy systems.

**When to Use**
   Apply district heating forecasting when managing thermal energy systems, optimizing heating plant operations, or planning district heating capacity.

Choosing the Right Use Case
---------------------------

The choice of use case depends on several key factors:

**Aggregation Level**
   - High aggregation: Grid losses, transport forecasts
   - Medium aggregation: Transport forecasts, some congestion management
   - Low aggregation: Individual customer forecasts, specific congestion points

**Business Objective**
   - Peak detection: Congestion management
   - Overall accuracy: Transport forecasts
   - Cost optimization: Grid loss forecasts
   - Capacity planning: Free space estimation

**Weather Dependency**
   - High weather dependency: Low-aggregation forecasts, renewable-heavy areas
   - Medium weather dependency: Most congestion management applications
   - Low weather dependency: Highly aggregated grid loss forecasts

**Operational Requirements**
   - Real-time decision making: Congestion management
   - Planning and coordination: Transport forecasts
   - Financial optimization: Grid loss forecasts

For detailed implementation guidance, see the :doc:`../getting_started/tutorials` and :doc:`how_to_guides` sections. To understand the underlying concepts better, refer to :doc:`../reference/concepts`.