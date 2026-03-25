Use Cases Guide
===============

OpenSTEF is a Python machine learning library designed to handle diverse short-term energy forecasting scenarios. Each use case has unique characteristics, optimization targets, and business requirements that influence model selection and configuration. This guide helps you identify which approach matches your specific forecasting needs.

Understanding Use Case Categories
---------------------------------

OpenSTEF supports six main categories of forecasting applications, each optimized for different operational requirements and data characteristics. The key differentiators are aggregation level, optimization focus, and the relative importance of peak versus overall accuracy.

**Aggregation Level Impact**: Higher aggregation typically means more predictable patterns and better forecast accuracy, while lower aggregation introduces more variability but provides granular insights needed for specific operational decisions.

**Optimization Focus**: Some use cases prioritize accuracy during peak periods (congestion management), others focus on overall accuracy across all time periods (transport forecasts), and some optimize for cost-weighted errors (grid losses).

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case, currently used in production at Alliander for over 10,000 grid locations daily.

**Primary Focus**: Accuracy during peak load periods when grid congestion is most likely to occur.

**Aggregation Levels**: Highly variable, ranging from very aggregated substation-level forecasts to individual customer predictions. Individual customer forecasts present the highest challenge due to behavioral unpredictability.

**Business Context**: Grid operators need precise predictions at congestion points to implement proactive mitigation strategies such as demand response, customer communication, and load shifting.

**Key Applications**:

- Substation forecasting for capacity planning
- Individual customer predictions for targeted demand response
- Medium-voltage substation (MSR) monitoring
- Peak load management and prevention

**Model Optimization**: Emphasis on peak detection and high-quantile accuracy. The library uses specialized metrics like effective precision and recall, rMAE@50th quantile at peaks, and rCRPS (Continuous Ranked Probability Score) to evaluate performance during critical periods.

.. code-block:: python

   from openstef.model import ModelCreator
   from openstef.data_classes import PredictionJob
   
   # Configure for congestion management
   pj = PredictionJob(
       name="substation_congestion",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9, 0.95, 0.99],  # Focus on high quantiles
       resolution_minutes=15
   )
   
   # Optimize for peak detection
   model = ModelCreator.create_model(pj, optimize_for_peaks=True)

Transport Forecasts
-------------------

Transport forecasts serve grid coordination between different network operators, enabling effective capacity planning and energy balance management.

**Primary Focus**: Overall forecast accuracy across all time periods, not just peaks.

**Aggregation Levels**: Medium aggregated points that balance predictability with operational granularity.

**Business Context**: Grid operators provide transport forecasts to upstream transmission system operators (like Alliander to TenneT) while receiving similar forecasts from downstream customers. This enables coordinated grid management and capacity planning across the entire energy system.

**Component Splitting**: Some operators require transport forecasts split into renewable components (solar, wind, other), necessitating specialized split-component models.

**Key Metrics**: Relative Mean Absolute Error (rMAE) across the entire forecast horizon.

**Model Optimization**: Balanced performance with emphasis on reliability and consistency rather than peak detection.

.. code-block:: python

   # Transport forecast configuration
   transport_pj = PredictionJob(
       name="transport_forecast",
       model="lgb",
       quantiles=[0.1, 0.5, 0.9],  # Standard quantiles
       resolution_minutes=15,
       split_components=True  # Enable component splitting
   )

Grid Loss Forecasts
-------------------

Grid loss forecasting focuses on financial optimization of grid operations by minimizing cost-weighted forecast errors.

**Primary Focus**: Overall accuracy with cost-weighted error minimization based on real-time market prices.

**Aggregation Levels**: Highly aggregated points where system-level temporal and cyclic patterns dominate individual customer behavior.

**Predictive Characteristics**: Weather predictors have diminished impact at this aggregation level. Instead, temporal patterns and system-wide behavioral trends become the dominant factors.

**Business Context**: Financial optimization of grid operations considering market price fluctuations and operational costs.

**Key Metrics**: Similar to transport forecasts (rMAE) plus total error cost minimization based on market prices.

**Model Optimization**: Error weighting based on real-time market prices and operational costs, with less emphasis on weather features.

Free Space Estimation
----------------------

Free space estimation helps grid operators understand available capacity for new connections or increased consumption at specific grid points.

**Primary Focus**: Accurate estimation of unused grid capacity during different time periods and scenarios.

**Business Context**: Supporting connection requests, capacity planning, and grid expansion decisions by quantifying available headroom.

**Model Approach**: Typically combines load forecasting with capacity constraints and safety margins to estimate available space for additional consumption or generation.

.. note::
   Free space estimation often requires combining OpenSTEF forecasts with grid capacity data and operational constraints that are external to the forecasting library itself.

EV Charging Capacity Estimation
-------------------------------

Electric vehicle charging capacity estimation addresses the growing need to integrate EV infrastructure with grid capacity planning.

**Primary Focus**: Predicting available capacity for EV charging infrastructure while maintaining grid stability.

**Business Context**: Supporting EV charging network expansion and dynamic load management as electric vehicle adoption accelerates.

**Model Considerations**: Must account for the highly variable and growing nature of EV charging patterns, often requiring specialized feature engineering for charging behavior.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management represents an advanced use case that combines OpenSTEF forecasting with power-grid-model for topology-aware predictions.

**Primary Focus**: Congestion management that considers the actual electrical topology and power flow constraints of the grid.

**Technical Integration**: Combines OpenSTEF point-based forecasts with power-grid-model's topology calculations to understand how forecasted loads will impact specific grid routes and components.

**Business Context**: More sophisticated congestion management that accounts for the physical constraints and power flow patterns of the actual grid infrastructure.

.. code-block:: python

   # Example integration with power-grid-model
   from power_grid_model import PowerGridModel
   from openstef.model import create_forecast
   
   # Create point forecasts with OpenSTEF
   forecasts = create_forecast(prediction_jobs)
   
   # Apply topology-aware analysis
   pgm = PowerGridModel(grid_data)
   topology_results = pgm.calculate_power_flow(forecasts)

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electrical energy into thermal demand forecasting.

**Primary Focus**: Thermal demand prediction for district heating systems.

**Business Context**: Community-driven use case that demonstrates OpenSTEF's applicability beyond electrical grid management to other energy domains.

**Model Adaptations**: Requires different feature engineering approaches focused on thermal dynamics, building characteristics, and heating degree days rather than electrical consumption patterns.

.. note::
   District heating support is still evolving as part of OpenSTEF's broader domain applicability goals in version 4.0.

Choosing the Right Use Case
---------------------------

When selecting your use case approach, consider these key decision factors:

**Data Aggregation Level**: Higher aggregation generally provides better accuracy but less operational granularity. Choose based on your specific operational needs.

**Peak vs. Overall Accuracy**: Congestion management prioritizes peak accuracy, while transport and grid loss forecasts optimize for overall performance.

**Business Requirements**: Consider whether you need component splitting, topology awareness, cost optimization, or capacity estimation features.

**Integration Needs**: Some use cases require integration with external systems like power-grid-model for topology or market pricing systems for cost optimization.

For detailed implementation guidance, see the tutorials in the getting started section. For specific deployment scenarios, consult the how-to guides.