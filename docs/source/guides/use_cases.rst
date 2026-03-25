Now I have comprehensive information about OpenSTEF's use cases. Let me create the complete RST documentation page.

OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed to handle diverse short-term energy forecasting scenarios. Each use case has distinct characteristics in terms of aggregation levels, optimization targets, and business requirements. This guide helps you identify which approach best matches your forecasting needs.

Understanding Use Case Categories
---------------------------------

OpenSTEF supports forecasting applications across different domains, each with specific accuracy requirements and operational constraints. The choice of use case determines model optimization strategies, evaluation metrics, and feature engineering approaches.

The library's modular design allows you to adapt these patterns to your specific context while leveraging proven forecasting techniques developed through years of operational experience.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case, focusing on preventing grid overloads through accurate peak load predictions.

**When to use this approach:**

- You need to identify potential grid congestion points
- Peak load accuracy is more critical than overall forecast precision
- You're working with highly variable aggregation levels (individual customers to substations)
- Your business process involves proactive demand response or customer communication

**Key characteristics:**

- **Primary focus:** Accuracy during peak load periods
- **Aggregation levels:** Highly variable, from individual customers to medium-voltage substations (MSRs)
- **Optimization target:** Peak detection and high-quantile accuracy
- **Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS

**Typical applications:**

- Substation load forecasting
- Individual customer demand prediction
- Medium-voltage route monitoring
- Demand response program optimization

.. code-block:: python

   from openstef.pipeline import create_forecast
   from openstef.data_classes import PredictionJob
   
   # Configure for congestion management
   job = PredictionJob(
       id="congestion_substation_001",
       model="xgb_quantile",  # Optimized for peak detection
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles
       horizon_minutes=2880,  # 48-hour horizon
   )
   
   forecast = create_forecast(job, input_data)

.. note::
   Individual customer forecasts can be particularly challenging due to behavioral variability. Consider using ensemble methods or fallback strategies for low-aggregation scenarios.

Transport Forecasts
-------------------

Transport forecasts provide reliable predictions for grid operators to communicate planned energy usage between network levels, enabling coordinated capacity planning.

**When to use this approach:**

- You need to communicate forecasts to upstream transmission operators
- You require balanced accuracy across all forecast periods
- You're working with medium-aggregated grid points
- Component splitting (solar, wind, other) is required

**Key characteristics:**

- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregated points balancing predictability and granularity
- **Optimization target:** Reliable performance across entire forecast horizon
- **Key metrics:** rMAE (relative Mean Absolute Error)

**Business context:**

Grid operators like Alliander provide transport forecasts to transmission system operators (TenneT) while receiving forecasts from downstream customers. This creates a coordinated forecasting chain that enables effective grid management.

.. code-block:: python

   # Transport forecast with component splitting
   job = PredictionJob(
       id="transport_region_north",
       model="xgb",  # Balanced performance model
       horizon_minutes=1440,  # 24-hour horizon
       feature_modules=["weather", "lag", "cyclic"],
   )
   
   # For component forecasts
   component_jobs = [
       PredictionJob(id="transport_solar", model="linear"),
       PredictionJob(id="transport_wind", model="xgb"),
       PredictionJob(id="transport_other", model="lgbm"),
   ]

Grid Loss Forecasts
-------------------

Grid loss forecasting focuses on financial optimization by minimizing cost-weighted forecast errors based on real-time market conditions.

**When to use this approach:**

- Financial optimization is your primary concern
- You're forecasting at highly aggregated system levels
- Market price fluctuations significantly impact operational costs
- Weather predictors have limited impact due to aggregation

**Key characteristics:**

- **Primary focus:** Cost-weighted error minimization
- **Aggregation levels:** Highly aggregated where system-level patterns dominate
- **Optimization target:** Error weighting based on market prices and operational costs
- **Key metrics:** rMAE plus total error cost minimization

**Predictive characteristics:**

At high aggregation levels, weather predictors become less influential while temporal patterns and system-wide behavioral trends dominate the forecasting signal.

.. code-block:: python

   from openstef.model.objective import create_custom_objective
   
   # Grid loss forecast with cost weighting
   def market_price_objective(y_true, y_pred, market_prices):
       """Custom objective weighted by market prices"""
       errors = abs(y_true - y_pred)
       return (errors * market_prices).mean()
   
   job = PredictionJob(
       id="grid_losses_system",
       model="lgbm",
       custom_objective=market_price_objective,
       feature_modules=["lag", "cyclic"],  # Weather less important
   )

Free Space Estimation
---------------------

Free space estimation determines available grid capacity for new connections, particularly relevant for EV charging infrastructure and distributed energy resources.

**When to use this approach:**

- You need to assess grid capacity for new connections
- Planning EV charging station deployments
- Evaluating distributed generation integration potential
- Supporting grid investment decisions

**Key characteristics:**

- **Primary focus:** Capacity utilization and headroom calculation
- **Aggregation levels:** Variable, depending on connection point
- **Optimization target:** Conservative estimates to ensure grid stability
- **Applications:** EV charging capacity estimation, connection studies

.. code-block:: python

   # Free space estimation combining forecasts with capacity limits
   job = PredictionJob(
       id="free_space_feeder_12",
       model="xgb_quantile",
       quantiles=[0.8, 0.9, 0.95],  # Conservative estimates
       horizon_minutes=8760 * 60,  # Annual horizon
   )
   
   # Calculate available capacity
   def calculate_free_space(forecast, grid_capacity):
       peak_forecast = forecast.quantile(0.95)
       return grid_capacity - peak_forecast

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electrical grid applications into thermal demand forecasting for community heating systems.

**When to use this approach:**

- You're forecasting thermal demand rather than electrical load
- Working with district heating or cooling systems
- Community-scale energy management
- Thermal storage optimization

**Key characteristics:**

- **Domain:** Thermal energy (not electricity)
- **Applications:** Community heating systems, thermal storage management
- **Optimization target:** Thermal demand patterns and storage efficiency

.. note::
   District heating support is an emerging use case. The OpenSTEF community is actively developing specialized features for thermal forecasting applications.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model for topology-aware predictions, enabling more sophisticated grid analysis.

**When to use this approach:**

- Grid topology significantly affects your forecasting accuracy
- You need to model power flows and network constraints
- Working with complex medium-voltage networks
- Topology changes affect load distribution

**Key characteristics:**

- **Integration:** Combined with power-grid-model library
- **Topology awareness:** Considers network structure in forecasting
- **Applications:** Complex MV network management, topology-sensitive forecasting
- **Advanced feature:** Requires additional modeling expertise

.. code-block:: python

   # Topology-aware forecasting (conceptual)
   from power_grid_model import PowerGridModel
   
   # This requires integration between OpenSTEF and power-grid-model
   # Specific implementation depends on your network topology
   
   job = PredictionJob(
       id="mv_route_topology_aware",
       model="xgb",
       topology_model=PowerGridModel(network_data),
       feature_modules=["weather", "lag", "topology"],
   )

Choosing the Right Use Case
---------------------------

Use this decision framework to select the most appropriate approach:

**Start with your primary objective:**

- **Peak accuracy needed?** → Congestion Management
- **Overall reliability important?** → Transport Forecasts  
- **Cost optimization focus?** → Grid Loss Forecasts
- **Capacity planning required?** → Free Space Estimation
- **Thermal systems?** → District Heating
- **Complex topology matters?** → MV Route with Topology

**Consider your data characteristics:**

- **Individual customers:** Congestion Management (with fallback strategies)
- **Medium aggregation:** Transport Forecasts or Free Space Estimation
- **High aggregation:** Grid Loss Forecasts
- **Thermal data:** District Heating

**Evaluate your operational context:**

- **Real-time congestion management:** Congestion Management
- **Regulatory reporting:** Transport Forecasts
- **Financial optimization:** Grid Loss Forecasts
- **Infrastructure planning:** Free Space Estimation

For detailed implementation guidance, see the :doc:`../getting_started/tutorials` page. For specific deployment scenarios, refer to :doc:`how_to_guides`.