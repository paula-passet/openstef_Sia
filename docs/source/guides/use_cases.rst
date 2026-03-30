OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed to handle diverse short-term energy forecasting applications. Each use case has distinct characteristics, optimization targets, and business requirements that influence model selection and configuration. Understanding these differences helps you choose the right approach for your specific forecasting needs.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case. Grid operators use these forecasts to prevent equipment overload and maintain grid stability through proactive interventions.

**Primary Focus:** Accuracy during peak load periods when congestion is most likely to occur.

**Aggregation Levels:** Highly variable, ranging from individual customer connections to large substations. Individual customer forecasts present the greatest challenge due to behavioral unpredictability, while aggregated points offer more stable patterns.

**Typical Applications:**
- Substation load forecasting
- Individual customer demand prediction
- Medium-voltage substation (MSR) monitoring
- Critical grid point surveillance

**Business Context:** Grid operators need precise peak predictions to implement effective mitigation strategies such as demand response activation, generation curtailment, or customer communication for voluntary load reduction.

**Key Metrics:** Effective precision and recall for peak detection, rMAE at 50th quantile during peaks, and rCRPS (Continuous Ranked Probability Score) for probabilistic accuracy.

**Model Optimization:** Emphasis on high-quantile accuracy and peak detection capabilities. XGBoost quantile models typically perform well due to their ability to capture complex non-linear relationships and handle the high variability in low-aggregation scenarios.

.. code-block:: python

   from openstef.model.regressors.xgb_quantile import XGBQuantileOpenstfRegressor
   from openstef.pipeline.create_forecast import create_forecast_pipeline
   
   # Configure for congestion management
   model = XGBQuantileOpenstfRegressor()
   pipeline = create_forecast_pipeline(
       model=model,
       quantiles=[0.1, 0.5, 0.9],  # Focus on extreme quantiles
       horizon_hours=48
   )

Transport Forecasts
-------------------

Transport forecasts enable coordination between different levels of the electricity grid. Distribution system operators (DSOs) provide these forecasts to transmission system operators (TSOs) while receiving similar forecasts from their customers.

**Primary Focus:** Overall forecast accuracy across all time periods rather than peak-specific performance.

**Aggregation Levels:** Medium aggregation providing a balance between predictability and operational granularity.

**Business Context:** Grid operators require reliable forecasts for capacity planning and coordinated grid management. For example, Alliander provides transport forecasts to TenneT (the Dutch TSO) while receiving forecasts from large industrial customers. Some operators also require component-split forecasts (solar, wind, other), necessitating specialized models.

**Key Metrics:** rMAE (relative Mean Absolute Error) across the entire forecast horizon.

**Model Optimization:** Balanced performance emphasizing reliability and consistency rather than peak detection. Linear models often perform well due to their stability and interpretability.

.. code-block:: python

   from openstef.model.regressors.linear_quantile import LinearQuantileOpenstfRegressor
   
   # Configure for transport forecasting
   model = LinearQuantileOpenstfRegressor()
   pipeline = create_forecast_pipeline(
       model=model,
       quantiles=[0.5],  # Focus on median forecast
       horizon_hours=24,
       split_components=True  # Enable solar/wind/other splitting
   )

Grid Loss Forecasts
-------------------

Grid losses represent the energy dissipated during transmission and distribution. Accurate loss forecasting enables financial optimization of grid operations by accounting for market price fluctuations.

**Primary Focus:** Overall accuracy with cost-weighted error minimization based on real-time energy market prices.

**Aggregation Levels:** Highly aggregated system-level points where temporal and cyclic patterns dominate over local variations.

**Predictive Characteristics:** Weather predictors have diminished impact at this aggregation level. System-wide behavioral trends and temporal patterns become the dominant factors.

**Business Context:** Financial optimization of grid operations considering market price fluctuations. Operators can optimize energy procurement and loss compensation strategies.

**Key Metrics:** Similar to transport forecasts plus total error cost minimization based on market prices.

**Model Optimization:** Error weighting based on real-time market prices and operational costs. Models should emphasize accuracy during high-price periods.

Free Space Estimation
---------------------

Free space estimation determines available capacity at grid connection points, enabling informed decisions about new connections and capacity allocation.

**Primary Focus:** Conservative estimation to prevent overcommitment of grid capacity.

**Business Context:** Grid operators need to assess available capacity for new customer connections, EV charging infrastructure, or renewable energy installations while maintaining grid stability.

**Model Approach:** Typically uses the difference between maximum capacity and forecasted peak demand, with safety margins applied based on forecast uncertainty.

.. code-block:: python

   # Example of free space calculation
   def calculate_free_space(forecast, capacity, safety_margin=0.1):
       peak_forecast = forecast.quantile(0.9)  # Conservative estimate
       safety_buffer = capacity * safety_margin
       free_space = capacity - peak_forecast - safety_buffer
       return max(0, free_space)  # Cannot be negative

EV Charging Capacity Estimation
-------------------------------

Electric vehicle charging presents unique forecasting challenges due to the combination of transportation patterns and energy demand. This use case helps grid operators plan charging infrastructure and manage local grid impacts.

**Characteristics:** Highly variable demand patterns influenced by commuting schedules, seasonal variations, and charging behavior. Requires consideration of both individual charging events and aggregated load patterns.

**Applications:** Planning charging infrastructure capacity, managing local grid impacts, optimizing charging schedules to avoid peak periods.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines traditional forecasting with power system topology analysis using power-grid-model (PGM) integration.

**Unique Approach:** Unlike point-based forecasting, this use case considers the electrical network topology to understand how loads and generation affect different parts of the grid.

**Integration with PGM:** OpenSTEF forecasts are combined with power-grid-model's network analysis capabilities to identify potential congestion points throughout the network topology.

**Applications:** Proactive identification of congestion points, optimal placement of flexibility resources, network planning and reinforcement decisions.

.. note::
   [DIAGRAM: Network topology showing how forecasts at different nodes combine with power flow analysis to identify congestion points]

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electricity into thermal energy forecasting. This community-driven use case demonstrates the library's flexibility for non-electrical energy applications.

**Domain Differences:** Thermal demand patterns differ significantly from electrical load, with stronger temperature dependencies and different temporal characteristics.

**Applications:** Heat demand forecasting for district heating systems, thermal storage optimization, combined heat and power plant scheduling.

**Status:** Currently in development as part of the community's efforts to broaden OpenSTEF's applicability beyond electrical grid applications.

Choosing the Right Use Case
----------------------------

When selecting an approach for your forecasting needs, consider these key factors:

**Data Aggregation Level:**
- Individual connections: Use congestion management approaches with robust handling of high variability
- Medium aggregation: Transport forecasts or MV route analysis depending on topology requirements  
- High aggregation: Grid loss forecasting with emphasis on temporal patterns

**Business Objectives:**
- Peak management: Congestion management with quantile-focused models
- Capacity planning: Transport forecasts with reliable median predictions
- Cost optimization: Grid loss forecasting with market price weighting
- Infrastructure planning: Free space estimation or EV capacity analysis

**Available Data:**
- Network topology available: Consider MV route congestion approach with PGM integration
- Component-level data: Use split-component transport models
- Market price data: Enable cost-weighted optimization for grid loss forecasting

**Accuracy Requirements:**
- Critical infrastructure protection: Congestion management with conservative quantiles
- Regulatory reporting: Transport forecasts with balanced accuracy
- Financial optimization: Grid loss forecasting with cost-sensitive metrics

For detailed implementation guidance, see the :doc:`../getting_started/tutorials` page. For specific deployment scenarios, refer to the :doc:`how_to_guides` section.