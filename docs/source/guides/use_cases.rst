Use Cases
=========

OpenSTEF is a Python machine learning library designed to handle diverse short-term energy forecasting scenarios. Each use case has distinct characteristics, optimization targets, and accuracy requirements. This guide helps you identify which approach best matches your specific forecasting needs.

Overview of Use Cases
---------------------

The library supports six primary use cases, each optimized for different business contexts and technical requirements:

- **Congestion Management**: Peak-focused forecasting for grid capacity planning
- **Transport Forecasts**: Balanced accuracy for grid operator coordination
- **Grid Loss Forecasts**: Cost-optimized system-level predictions
- **Free Space Estimation**: Available capacity forecasting for new connections
- **EV Charging Capacity**: Infrastructure planning for electric vehicle adoption
- **MV Route Congestion with Topology**: Advanced topology-aware forecasting using power-grid-model integration

Congestion Management Forecasts
--------------------------------

Congestion management represents OpenSTEF's original and most mature use case, designed to prevent grid overloads through accurate peak prediction.

**Primary Focus**: Accuracy during peak load periods when grid congestion is most likely to occur.

**Aggregation Levels**: Highly variable, ranging from very aggregated substation-level forecasts to individual customer predictions. Individual customer forecasts present particular challenges due to behavioral variability and unpredictable consumption patterns.

**Typical Applications**:
- Substation load forecasting
- Medium-voltage substation (MSR) predictions
- Individual customer demand forecasting
- Critical grid point monitoring

**Business Context**: Grid operators need precise predictions at congestion-prone locations to implement proactive mitigation strategies, such as calling customers in advance to reduce consumption or preventing overloads through demand response programs.

**Key Metrics**: Effective precision and recall for peak detection, rMAE at 50th quantile during peak periods, and rCRPS (relative Continuous Ranked Probability Score) for probabilistic accuracy.

**Model Optimization**: Emphasis on high-quantile accuracy and robust peak detection, with specialized handling for high variability in low-aggregation scenarios.

.. code-block:: python

   from openstef import OpenSTEF
   
   # Configure for congestion management
   model = OpenSTEF(
       use_case="congestion_management",
       optimization_target="peak_accuracy",
       metrics=["precision_recall", "rmae_peaks", "rcrps"]
   )

Transport Forecasts
-------------------

Transport forecasts provide balanced accuracy across all time periods, supporting coordination between grid operators at different voltage levels.

**Primary Focus**: Overall forecast accuracy throughout the entire prediction horizon, not just during peaks.

**Aggregation Levels**: Medium aggregated points that balance predictability with operational granularity.

**Business Context**: Grid operators require reliable forecasts to communicate planned energy usage to upstream network operators (like transmission system operators) while receiving similar forecasts from downstream customers. For example, Alliander provides transport forecasts to TenneT while receiving forecasts from its customers, enabling coordinated grid management and capacity planning.

**Component Splitting**: Some operators require transport forecasts split into components (solar, wind, other generation), necessitating specialized split-component models.

**Key Metrics**: rMAE (relative Mean Absolute Error) across the full forecast horizon.

**Model Optimization**: Balanced performance with emphasis on reliability and consistency rather than peak-specific accuracy.

.. code-block:: python

   # Transport forecast with component splitting
   model = OpenSTEF(
       use_case="transport",
       split_components=["solar", "wind", "other"],
       optimization_target="overall_accuracy"
   )

Grid Loss Forecasts
-------------------

Grid loss forecasting focuses on system-level predictions where financial optimization drives model performance requirements.

**Primary Focus**: Overall accuracy combined with cost-weighted error minimization based on real-time market conditions.

**Aggregation Levels**: Highly aggregated system-level points where temporal and cyclic patterns dominate individual behavioral variations.

**Predictive Characteristics**: Weather predictors have diminished impact at this aggregation level. System-wide behavioral trends and temporal patterns become the dominant predictive factors.

**Business Context**: Financial optimization of grid operations considering fluctuating market prices and operational costs. Errors during high-price periods carry greater business impact than errors during low-price periods.

**Key Metrics**: Similar to transport forecasts (rMAE) plus total error cost minimization weighted by market prices.

**Model Optimization**: Error weighting based on real-time market prices and operational cost structures.

.. code-block:: python

   # Grid loss forecast with cost weighting
   model = OpenSTEF(
       use_case="grid_losses",
       cost_weighting=True,
       market_price_integration=True,
       optimization_target="cost_minimization"
   )

Free Space Estimation
---------------------

Free space estimation forecasts available grid capacity for new customer connections and infrastructure planning.

**Primary Focus**: Determining available capacity margins while maintaining grid stability and reliability.

**Business Context**: Distribution system operators need accurate estimates of remaining grid capacity to approve new connections, plan infrastructure upgrades, and manage grid utilization efficiently.

**Key Considerations**: Must account for both current load patterns and potential future growth while maintaining safety margins for grid operation.

.. code-block:: python

   # Free space estimation
   model = OpenSTEF(
       use_case="free_space_estimation",
       safety_margin=0.8,  # 80% utilization threshold
       planning_horizon="1_year"
   )

EV Charging Capacity Estimation
-------------------------------

EV charging capacity estimation supports infrastructure planning for electric vehicle adoption by forecasting charging demand and available grid capacity.

**Primary Focus**: Predicting EV charging patterns and their impact on local grid capacity to guide infrastructure investments.

**Business Context**: As electric vehicle adoption accelerates, grid operators need to understand charging patterns, peak demand impacts, and infrastructure requirements for supporting EV charging networks.

**Key Considerations**: Highly variable charging patterns, seasonal effects, and rapid growth in EV adoption requiring adaptive modeling approaches.

.. code-block:: python

   # EV charging capacity estimation
   model = OpenSTEF(
       use_case="ev_charging_capacity",
       growth_modeling=True,
       seasonal_patterns=True,
       charging_behavior_analysis=True
   )

MV Route Congestion with Topology
----------------------------------

MV (Medium Voltage) route congestion management represents an advanced use case that combines OpenSTEF forecasting with power-grid-model for topology-aware predictions.

**Primary Focus**: Topology-aware congestion management that considers the physical structure and constraints of the medium voltage network.

**Integration**: Combines OpenSTEF's forecasting capabilities with power-grid-model's network analysis to provide more accurate and actionable congestion predictions.

**Business Context**: Medium voltage networks have complex topologies where congestion at one point can affect multiple downstream locations. Traditional point-based forecasting may miss these interdependencies.

**Technical Approach**: Uses power-grid-model to simulate network conditions and identify potential congestion points based on OpenSTEF forecasts, enabling more precise congestion management strategies.

.. note::
   This approach requires both OpenSTEF and power-grid-model libraries. See the power-grid-model documentation for topology modeling details.

.. code-block:: python

   from openstef import OpenSTEF
   from power_grid_model import PowerGridModel
   
   # Topology-aware congestion management
   forecaster = OpenSTEF(use_case="congestion_management")
   grid_model = PowerGridModel(network_data)
   
   # Combine forecasting with topology analysis
   forecasts = forecaster.predict(data)
   congestion_analysis = grid_model.analyze_congestion(forecasts)

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electrical energy into thermal demand forecasting for community heating systems.

**Primary Focus**: Thermal demand prediction for district heating networks, considering weather dependency and community consumption patterns.

**Business Context**: District heating operators need accurate thermal demand forecasts for efficient heat generation planning, storage management, and fuel procurement.

**Key Differences**: Unlike electrical forecasting, thermal systems have significant thermal inertia, different weather dependencies, and distinct seasonal patterns.

.. note::
   District heating support is under active development in OpenSTEF 4.0. Contact the community for current implementation status.

Choosing the Right Use Case
---------------------------

Select your use case based on these key decision factors:

**Business Objective**:
- Peak management → Congestion Management
- Grid coordination → Transport Forecasts  
- Cost optimization → Grid Loss Forecasts
- Capacity planning → Free Space Estimation or EV Charging Capacity
- Network-aware analysis → MV Route Congestion with Topology
- Thermal systems → District Heating

**Aggregation Level**:
- Individual customers → Congestion Management
- Medium aggregation → Transport Forecasts
- System-level → Grid Loss Forecasts

**Optimization Target**:
- Peak accuracy → Congestion Management
- Overall accuracy → Transport Forecasts
- Cost minimization → Grid Loss Forecasts

**Technical Requirements**:
- Topology awareness → MV Route Congestion with Topology
- Component splitting → Transport Forecasts
- Market integration → Grid Loss Forecasts

Next Steps
----------

Once you've identified your use case:

1. Review the :doc:`../getting_started/quickstart` for basic implementation
2. Follow the :doc:`../getting_started/tutorials` for detailed examples
3. Check :doc:`../reference/concepts` for deeper understanding of forecasting principles
4. Consult :doc:`how_to_guides` for specific implementation guidance

For questions about use case selection, visit the OpenSTEF community Slack workspace or attend the bi-weekly community meetings.