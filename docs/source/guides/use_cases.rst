Use Cases
=========

OpenSTEF is a Python machine learning library designed to handle diverse short-term energy forecasting scenarios. Each use case has distinct characteristics that influence model selection, optimization targets, and evaluation metrics. Understanding these differences helps you choose the right approach for your specific forecasting needs.

This guide covers the most common OpenSTEF applications, from traditional congestion management to emerging use cases like district heating and topology-aware forecasting.

Congestion Management Forecasts
-------------------------------

Congestion management is OpenSTEF's original use case and remains the most demanding in terms of accuracy requirements. These forecasts focus on predicting peak load periods to prevent grid overloads through proactive demand response.

**Key characteristics:**

- **Primary focus:** Accuracy during peak load periods
- **Aggregation levels:** Highly variable, from individual customers to large substations
- **Optimization target:** Peak detection and high-quantile accuracy
- **Key metrics:** rMAE@50th quantile at peaks, rCRPS, precision and recall for peak events

**When to use:** Grid operators need precise predictions at congestion points to implement effective mitigation strategies like calling customers in advance or preventing overloads through demand response.

.. code-block:: python

   from openstef.model import OpenstfRegressor
   from openstef.data_classes import PredictionJobDataClass
   
   # Configure for congestion management
   pj = PredictionJobDataClass(
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles for peak detection
       resolution_minutes=15,       # High temporal resolution
       forecast_type="demand"
   )
   
   # Train with emphasis on peak periods
   model = OpenstfRegressor()
   model.fit(train_data, pj)

Individual customer forecasts can be particularly challenging due to behavioral variability, while aggregated substation forecasts typically achieve higher accuracy.

Transport Forecasts
-------------------

Transport forecasts provide overall energy flow predictions for grid coordination between network operators. These forecasts emphasize consistent accuracy across all time periods rather than peak-specific performance.

**Key characteristics:**

- **Primary focus:** Overall forecast accuracy across entire horizon
- **Aggregation levels:** Medium aggregated points balancing predictability and granularity  
- **Optimization target:** Balanced performance with emphasis on reliability
- **Key metrics:** rMAE across all periods

**When to use:** Grid operators need reliable forecasts to communicate planned energy usage to upstream operators (e.g., Alliander to TenneT) or receive forecasts from downstream customers. Some applications require component splitting (solar, wind, other).

.. code-block:: python

   # Transport forecast configuration
   pj = PredictionJobDataClass(
       model="lgb",
       quantiles=[0.1, 0.5, 0.9],
       resolution_minutes=60,        # Hourly resolution typical
       forecast_type="demand",
       split_components=True         # Enable solar/wind splitting if needed
   )

Transport forecasts benefit from the balanced nature of medium aggregation levels, where individual behavioral variations smooth out while maintaining meaningful granularity.

Grid Loss Forecasts
-------------------

Grid loss forecasting focuses on system-level energy losses with cost optimization considerations. These highly aggregated forecasts emphasize temporal patterns over weather dependencies.

**Key characteristics:**

- **Primary focus:** Overall accuracy with cost-weighted error minimization
- **Aggregation levels:** Highly aggregated where system-level patterns dominate
- **Optimization target:** Error weighting based on market prices and operational costs
- **Key metrics:** rMAE plus total error cost minimization

**When to use:** Financial optimization of grid operations considering market price fluctuations. Weather predictors have diminished impact at this aggregation level.

.. code-block:: python

   # Grid loss forecast with cost weighting
   pj = PredictionJobDataClass(
       model="linear",              # Simple models often sufficient
       quantiles=[0.25, 0.5, 0.75],
       resolution_minutes=60,
       forecast_type="demand"
   )
   
   # Custom cost weighting during evaluation
   from openstef.evaluation import evaluate_forecast
   
   results = evaluate_forecast(
       forecast_data, 
       realized_data,
       cost_weights=market_prices    # Weight errors by market prices
   )

Free Space Estimation
---------------------

Free space estimation determines available grid capacity for new connections, particularly important for EV charging infrastructure and distributed energy resources.

**Key characteristics:**

- **Primary focus:** Conservative capacity estimates to prevent overloads
- **Aggregation levels:** Location-specific, often at transformer or feeder level
- **Optimization target:** High-quantile accuracy for capacity planning
- **Key metrics:** Quantile accuracy at 90th-95th percentiles

**When to use:** Planning new connections, EV charging station deployment, or distributed generation integration where conservative capacity estimates prevent future congestion.

.. code-block:: python

   # Free space estimation focusing on high quantiles
   pj = PredictionJobDataClass(
       model="xgb",
       quantiles=[0.5, 0.8, 0.9, 0.95],  # Focus on high quantiles
       resolution_minutes=15,
       forecast_type="demand"
   )
   
   # Calculate free space from peak forecasts
   peak_forecast = model.predict(future_data)
   available_capacity = transformer_rating - peak_forecast['quantile_0.95']

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electricity into thermal demand forecasting. This use case demonstrates the library's flexibility for non-electrical energy systems.

**Key characteristics:**

- **Primary focus:** Thermal demand patterns and temperature dependencies
- **Aggregation levels:** Community or district level
- **Optimization target:** Overall accuracy with strong temperature correlation
- **Key metrics:** rMAE with temperature-weighted evaluation

**When to use:** Community heating systems, thermal energy planning, or integrated energy system optimization where thermal and electrical demands interact.

.. note::
   District heating is a community-contributed use case demonstrating OpenSTEF's applicability beyond electrical grid forecasting.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model for topology-aware analysis. This advanced use case considers grid structure in forecasting decisions.

**Key characteristics:**

- **Primary focus:** Network-aware congestion prediction
- **Aggregation levels:** Route and node level within MV networks
- **Optimization target:** Topology-constrained peak management
- **Integration:** Combined with power-grid-model library

**When to use:** Advanced grid management where network topology significantly influences congestion patterns, or when coordinated control across multiple grid points is required.

.. code-block:: python

   # Topology-aware forecasting workflow
   from power_grid_model import PowerGridModel
   
   # Create grid model
   grid_model = PowerGridModel(grid_topology_data)
   
   # Generate forecasts for all nodes
   node_forecasts = {}
   for node_id in grid_nodes:
       pj = PredictionJobDataClass(
           model="xgb",
           quantiles=[0.1, 0.5, 0.9],
           resolution_minutes=15
       )
       node_forecasts[node_id] = model.predict(node_data[node_id])
   
   # Analyze network constraints
   power_flow_results = grid_model.calculate_power_flow(node_forecasts)

This approach enables sophisticated congestion management strategies that consider network-wide effects rather than treating each point independently.

Choosing the Right Use Case
---------------------------

The choice between use cases depends on your specific requirements:

**For peak management:** Use congestion management forecasts with high quantile focus
**For grid coordination:** Choose transport forecasts with balanced accuracy
**For cost optimization:** Apply grid loss forecasts with market price weighting  
**For capacity planning:** Implement free space estimation with conservative quantiles
**For thermal systems:** Adapt district heating approaches with temperature emphasis
**For network-aware control:** Combine MV route congestion with topology modeling

Each use case can be implemented using OpenSTEF's flexible model configuration system. The key differences lie in quantile selection, aggregation levels, evaluation metrics, and integration with external systems like power-grid-model.

For detailed implementation examples, see the :doc:`../getting_started/tutorials` page. For specific deployment patterns, consult the :doc:`how_to_guides` section.