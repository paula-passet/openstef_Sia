Use Cases
==========

OpenSTEF is a flexible forecasting library that supports diverse energy forecasting applications. Each use case has distinct characteristics in terms of what matters most for accuracy, the level of data aggregation, and the business context driving forecast requirements. This guide helps you identify which use case matches your needs and understand how to configure OpenSTEF accordingly.

.. note:: OpenSTEF is a Python library, not a pre-configured application. You'll need to adapt the library's components—model selection, feature engineering, and evaluation metrics—to match your specific use case.


Congestion Management Forecasts
--------------------------------

Congestion management is OpenSTEF's original use case and remains the most common application. Grid operators use these forecasts to predict when and where grid capacity constraints will occur, enabling proactive interventions to prevent overloads.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

**Primary focus:** Accuracy near peak load periods. Missing a peak can result in grid overload, while false alarms waste operational resources.

**Aggregation levels:** Highly variable—from very aggregated points (entire substations) to low-aggregation scenarios (individual customers or small clusters). Individual customer forecasts are particularly challenging due to behavioral unpredictability.

**Typical applications:**

- Substation load forecasting
- Individual customer predictions for demand response programs
- Medium-voltage substation (MSR) forecasting

**Business context:** Grid operators need precise predictions at congestion points to implement mitigation strategies such as:

- Calling customers in advance to reduce consumption or generation (with compensation)
- Scheduling maintenance during low-load periods
- Planning grid reinforcements
- Activating demand response programs

Key metrics and optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Effective precision and recall** at peak detection
- **rMAE@50th quantile at peaks** (relative mean absolute error focused on peak periods)
- **rCRPS** (relative continuous ranked probability score) for quantile forecast quality

Model optimization emphasizes peak detection and high-quantile accuracy. You'll typically configure models to prioritize the 90th-99th percentiles rather than median performance.

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose congestion management forecasting when:

- You need to predict capacity constraint violations
- Peak accuracy matters more than overall accuracy
- You're working with grid points that experience periodic congestion
- Your business case involves operational interventions during high-load periods


Transport Forecasts
-------------------

Transport forecasts predict energy flows between different grid levels, enabling coordinated capacity planning across the electricity system hierarchy.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

**Primary focus:** Overall forecast accuracy across all time periods, not just peaks.

**Aggregation levels:** Medium aggregation—typically at the connection point between grid operators.

**Business context:** Grid operators require reliable forecasts to communicate planned energy usage to upstream network operators and receive similar forecasts from downstream customers. For example, a distribution system operator like Alliander provides transport forecasts to the transmission system operator (TenneT) while receiving forecasts from its customers. This enables coordinated grid management and capacity planning.

Some operators require transport forecasts split into components (solar, wind, other generation, consumption), which necessitates training separate models for each component and aggregating their predictions.

Key metrics and optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **rMAE** (relative mean absolute error) across the entire forecast horizon
- Balanced performance without special emphasis on peaks

Model optimization focuses on reliability and consistency rather than peak detection. The 50th percentile (median) forecast is typically most important.

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose transport forecasting when:

- You need to communicate planned energy flows to other grid operators
- Overall accuracy matters more than peak-specific accuracy
- You're forecasting at grid interconnection points
- Your business case involves capacity reservations or energy market participation


Grid Loss Forecasts
--------------------

Grid loss forecasting predicts energy losses in transmission and distribution networks, enabling financial optimization of grid operations.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

**Primary focus:** Overall accuracy with cost-weighted error minimization based on market prices.

**Aggregation levels:** Highly aggregated—typically at the system level where temporal and cyclic patterns dominate.

**Predictive characteristics:** Weather predictors have diminished impact at this aggregation level. System-wide behavioral trends, time-of-day patterns, and seasonal cycles become the dominant factors. This makes grid loss forecasting more predictable than low-aggregation use cases.

**Business context:** Grid operators must purchase energy to compensate for losses in their networks. Since energy prices fluctuate throughout the day, forecast errors during high-price periods are more costly than errors during low-price periods.

Key metrics and optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **rMAE** for overall accuracy
- **Total error cost minimization** weighted by real-time market prices

Model optimization incorporates error weighting based on electricity market prices. You can implement custom loss functions that penalize errors during expensive periods more heavily than errors during cheap periods.

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose grid loss forecasting when:

- You need to predict system-level energy losses
- Financial optimization is the primary driver
- You have access to electricity market price data
- Your data is highly aggregated with strong temporal patterns


Free Space Estimation
---------------------

Free space estimation forecasts available capacity for new connections or increased consumption at grid connection points. This use case helps grid operators manage connection requests and plan grid expansions.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

**Primary focus:** Predicting maximum available capacity (the gap between current load and grid limits) rather than absolute load values.

**Aggregation levels:** Varies depending on the connection point—from individual transformers to entire substations.

**Business context:** When customers request new connections or capacity increases, grid operators need to assess whether existing infrastructure can accommodate the additional load. Free space forecasts combine load predictions with grid capacity constraints to estimate available headroom.

Key metrics and optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **High-quantile accuracy** (similar to congestion management) since you're predicting peak capacity usage
- **Capacity violation probability** for risk assessment

Model optimization focuses on the upper tail of the forecast distribution, typically the 95th-99th percentiles.

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose free space estimation when:

- You need to assess capacity for new connections
- You're managing connection request queues
- Your business case involves capacity planning for growth
- You want to identify grid points approaching capacity limits


District Heating
----------------

District heating forecasting predicts thermal demand in community heating systems. This represents OpenSTEF's expansion beyond electricity forecasting into other energy domains.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

**Primary focus:** Thermal demand prediction for heat generation planning.

**Aggregation levels:** Typically at the district or neighborhood level.

**Predictive characteristics:** Thermal demand has strong weather dependency (especially temperature) but different temporal patterns than electricity. Heat storage in buildings creates lag effects between weather changes and demand response.

**Business context:** District heating operators need forecasts to optimize heat generation from combined heat and power plants, heat pumps, or other sources. Accurate forecasts enable efficient fuel usage and reduce operational costs.

Key metrics and optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **rMAE** for overall accuracy
- **Peak accuracy** during cold weather events

Model optimization requires careful feature engineering to capture thermal lag effects and building heat storage characteristics.

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose district heating forecasting when:

- You're forecasting thermal demand rather than electricity
- You operate or plan district heating systems
- You need to optimize heat generation scheduling
- Your data includes temperature and thermal load measurements


MV Route Congestion Management with Topology
---------------------------------------------

Medium-voltage (MV) route congestion management combines OpenSTEF with power-grid-model (PGM) to create topology-aware forecasts. This advanced use case accounts for how power flows through the grid network rather than treating each point independently.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

**Primary focus:** Predicting congestion on specific grid routes considering network topology and power flow physics.

**Aggregation levels:** Individual MV routes or cable sections within the distribution network.

**Technical approach:** OpenSTEF forecasts load at multiple grid points, then power-grid-model calculates resulting power flows through the network topology. This reveals congestion on specific cables or routes that wouldn't be apparent from individual point forecasts alone.

**Business context:** Modern distribution grids with distributed generation (solar, wind) experience complex power flows that depend on network topology. A cable might be congested even when no single connection point exceeds its limit, because power from multiple sources flows through that cable.

Key metrics and optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Route-level congestion detection** (precision and recall)
- **Power flow accuracy** at critical network elements
- **Combined forecast-and-flow error metrics**

Model optimization requires coordinating multiple forecasts to ensure their combined effect accurately represents network-level behavior.

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^

Choose topology-aware forecasting when:

- You need to predict congestion on specific cables or routes
- Your grid has significant distributed generation
- Single-point forecasts miss important network-level effects
- You have access to detailed grid topology data
- You can integrate power-grid-model into your workflow

.. note:: This use case requires both OpenSTEF and power-grid-model libraries, plus detailed network topology data. See the power-grid-model documentation for integration details.


Comparing Use Cases
-------------------

The following table summarizes key differences to help you choose the right approach:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Use Case
     - What Matters Most
     - Aggregation Level
     - Key Metrics
     - Model Focus
   * - Congestion Management
     - Peak accuracy
     - Variable (high to low)
     - rMAE@peaks, rCRPS
     - High quantiles
   * - Transport Forecasts
     - Overall accuracy
     - Medium
     - rMAE
     - Median forecast
   * - Grid Losses
     - Cost-weighted accuracy
     - High (system-level)
     - rMAE, cost minimization
     - Price-weighted errors
   * - Free Space Estimation
     - Available capacity
     - Variable
     - High quantiles
     - Upper tail
   * - District Heating
     - Thermal demand
     - Medium (district-level)
     - rMAE, peak accuracy
     - Thermal lag effects
   * - MV Route + Topology
     - Route congestion
     - Low (route-level)
     - Flow accuracy
     - Network-aware


Getting Started with Your Use Case
-----------------------------------

Once you've identified your use case, follow these steps:

1. **Review the quickstart guide** at :doc:`../getting_started/quickstart` to understand basic OpenSTEF usage
2. **Work through the tutorials** at :doc:`../getting_started/tutorials` to learn model training and evaluation
3. **Customize for your use case:**

   - Select appropriate evaluation metrics (see :doc:`../reference/concepts` for metric explanations)
   - Configure model parameters to emphasize what matters (peaks vs. overall accuracy)
   - Engineer features relevant to your domain (weather, temporal patterns, etc.)

4. **Set up deployment** using the guides at :doc:`how_to_guides`

.. note:: Most use cases can start with OpenSTEF's default configuration and then customize based on evaluation results. The library's modular design makes it easy to swap components as you refine your approach.


Next Steps
----------

- :doc:`../getting_started/quickstart` - Train your first model
- :doc:`../reference/concepts` - Understand forecasting concepts and metrics
- :doc:`faq` - Common questions about OpenSTEF capabilities