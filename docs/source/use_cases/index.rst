Use Cases
=========

OpenSTEF supports diverse forecasting applications across the energy sector. Each use case has specific accuracy requirements, optimization targets, and aggregation characteristics. This page outlines the primary applications where OpenSTEF provides value.

.. note::
   OpenSTEF is a Python library that provides the building blocks for these use cases. You'll need to integrate it into your own application or workflow to implement these forecasting scenarios.

Congestion Management Forecasts
-------------------------------

Congestion management forecasts focus on predicting when and where grid capacity constraints will occur, enabling proactive mitigation strategies.

**Primary Focus:** Accuracy near peak load periods where congestion is most likely to occur.

**Aggregation Levels:** Highly variable, ranging from very aggregated points down to individual customer forecasts. Individual customer predictions can be particularly challenging due to behavioral variability and unpredictable consumption patterns.

**Typical Applications:**
- Substation forecasting
- Individual customer load predictions  
- Medium-voltage substation (MSR) forecasting
- Distribution grid capacity planning

**Business Context:** Grid operators need precise predictions at potential congestion points to implement effective mitigation strategies, such as load shifting, demand response, or infrastructure upgrades.

**Key Metrics:** 
- Effective precision and recall for peak detection
- rMAE@50th quantile at peaks
- rCRPS (ranked Continuous Ranked Probability Score)

**Model Optimization:** Emphasis on peak detection accuracy and high-quantile performance, with robust handling of high variability in low-aggregation scenarios.

**Configuration Considerations:**
- Use quantile models to capture uncertainty in peak predictions
- Configure feature engineering to emphasize weather dependencies
- Consider ensemble approaches for critical congestion points

Transport Forecasts
-------------------

Transport forecasts predict the total energy flow through grid connections, supporting coordination between different levels of the electricity system.

**Primary Focus:** Overall forecast accuracy across all time periods, providing reliable baseline predictions.

**Aggregation Levels:** Medium aggregated points, balancing predictability with operational granularity.

**Business Context:** Grid operators require reliable forecasts to communicate planned energy usage to upstream network operators (e.g., transmission system operators) and receive forecasts from downstream customers. This enables coordinated grid management and capacity planning across the entire electricity system.

**Typical Applications:**
- Distribution system operator (DSO) forecasts to transmission system operators (TSO)
- Regional energy flow predictions
- Component-split forecasts (solar, wind, conventional generation)

**Key Metrics:** rMAE (relative Mean Absolute Error) across the entire forecast horizon.

**Model Optimization:** Balanced performance across all time periods with emphasis on reliability and consistency.

**Configuration Considerations:**
- Focus on temporal patterns and system-wide behavioral trends
- Weather predictors remain important but may have less impact than in congestion forecasting
- Consider split-component models when detailed generation mix is required

Grid Loss Forecasting
---------------------

Grid loss forecasting predicts technical losses in the electricity distribution system, supporting financial optimization of grid operations.

**Primary Focus:** Overall accuracy with cost-weighted error minimization based on market price fluctuations.

**Aggregation Levels:** Highly aggregated points where system-level temporal and cyclic patterns dominate individual consumer behavior.

**Predictive Characteristics:** Weather predictors have diminished impact at this aggregation level. Stronger temporal patterns, system-wide behavioral trends, and operational characteristics become the dominant factors.

**Business Context:** Financial optimization of grid operations considering real-time market price fluctuations and operational costs. Accurate loss predictions enable better energy procurement and cost allocation.

**Key Metrics:** 
- Similar to transport forecasts (rMAE)
- Total error cost minimization based on market prices
- Cost-weighted performance metrics

**Model Optimization:** Error weighting based on real-time market prices and operational costs, with emphasis on system-level pattern recognition.

**Configuration Considerations:**
- Emphasize temporal and cyclic features over weather dependencies
- Consider market price integration for cost-weighted training
- Focus on system-level aggregation patterns

District Heating and Thermal Demand
-----------------------------------

District heating forecasts predict thermal energy demand for heating systems, supporting efficient operation of combined heat and power systems.

**Primary Focus:** Thermal demand prediction with strong weather dependency, particularly temperature sensitivity.

**Aggregation Levels:** Varies from building-level to district-wide thermal networks.

**Business Context:** District heating operators need accurate thermal demand forecasts to optimize heat generation, storage, and distribution. This is particularly important for combined heat and power (CHP) systems that must balance electrical and thermal output.

**Typical Applications:**
- District heating network demand forecasting
- Building-level thermal load prediction
- CHP system optimization
- Thermal storage management

**Key Characteristics:**
- Strong temperature dependency
- Seasonal patterns more pronounced than electrical loads
- Different time constants compared to electrical demand

**Configuration Considerations:**
- Emphasize temperature and weather-related features
- Consider seasonal decomposition techniques
- Account for thermal inertia in building systems

Free Space Estimation
--------------------

Free space estimation determines available capacity or headroom on grid connections, supporting connection planning and capacity management.

**Primary Focus:** Predicting available capacity margins to support new connections and prevent overloading.

**Relationship to Congestion Forecasts:** Closely related to congestion management but focuses on available capacity rather than constraint violations.

**Business Context:** Grid operators need to understand available capacity to approve new connections, plan infrastructure investments, and manage grid utilization efficiently.

**Typical Applications:**
- New connection capacity assessment
- Infrastructure planning support
- Grid utilization optimization
- Capacity allocation decisions

**Configuration Considerations:**
- Similar to congestion forecasting but with focus on capacity margins
- Consider probabilistic outputs to quantify capacity uncertainty
- Integrate with grid topology information where available

MV Route Congestion Management (with Power Grid Model)
------------------------------------------------------

Advanced congestion management that combines OpenSTEF forecasting with power-grid-model for topology-aware route-level analysis.

**Primary Focus:** Route-specific congestion prediction considering actual grid topology and power flows.

**Integration Approach:** OpenSTEF provides load forecasts that feed into power-grid-model for detailed power flow analysis and congestion identification.

**Business Context:** More sophisticated congestion management that accounts for actual grid topology, enabling precise identification of congestion locations and optimal mitigation strategies.

**Typical Applications:**
- Route-level congestion analysis
- Topology-aware capacity planning
- Optimal switching strategies
- Detailed grid constraint analysis

**Configuration Considerations:**
- Requires integration with power-grid-model
- Need detailed grid topology data
- Consider computational complexity for real-time applications

Getting Started with Use Cases
------------------------------

To implement any of these use cases:

1. **Install OpenSTEF**: ``pip install openstef``
2. **Prepare your data**: Ensure you have historical load data and relevant predictors
3. **Configure your PredictionJob**: Set up the appropriate model and features for your use case
4. **Train and validate**: Use backtesting to validate performance for your specific scenario
5. **Deploy**: Integrate into your operational workflow

For detailed implementation guidance, see the :doc:`../user_guide/tutorials` and :doc:`../how_to_guides/index` sections.

.. note::
   Each use case may require different data sources, model configurations, and evaluation metrics. The OpenSTEF library provides the flexibility to adapt to your specific requirements while maintaining robust forecasting performance.