OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library that supports diverse short-term energy forecasting applications. Each use case has distinct characteristics in terms of aggregation levels, optimization targets, and business requirements. This guide helps you identify which approach matches your specific forecasting needs.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case. Grid operators use these forecasts to prevent network overloads through proactive demand response and customer coordination.

**When to use:** You need to predict peak load periods at specific grid points to implement congestion mitigation strategies.

**Key characteristics:**

- **Primary focus:** Maximum accuracy during peak load periods
- **Aggregation levels:** Highly variable, from individual customers to large substations
- **Typical applications:** Substation forecasting, MSRs (medium-voltage substations), individual customer predictions
- **Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS

**What makes it different:** Individual customer forecasts can be particularly unpredictable due to behavioral variability. The model optimization emphasizes peak detection and high-quantile accuracy rather than overall performance.

**Business context:** Grid operators need precise predictions at congestion points to call customers in advance for load reduction, prevent overloads through demand response, and optimize grid capacity utilization.

::

   from openstef.model import ModelCreator
   from openstef.data_classes import PredictionJob
   
   # Configure for congestion management
   job = PredictionJob(
       name="substation_congestion",
       model="xgb",
       quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles for peaks
       resolution_minutes=15
   )
   
   # Optimize for peak accuracy
   model = ModelCreator.create_model(
       job,
       objective="quantile_loss",  # Better for peak detection
       eval_metric="rCRPS"
   )

Transport Forecasts
-------------------

Transport forecasts enable coordination between different grid operators by predicting energy flows across network boundaries.

**When to use:** You need to communicate planned energy usage to upstream operators or receive forecasts from downstream customers.

**Key characteristics:**

- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregated points balancing predictability and granularity
- **Key metrics:** rMAE (relative Mean Absolute Error)
- **Component splitting:** Some operators require forecasts split by generation type (solar, wind, other)

**What makes it different:** Unlike congestion management, transport forecasts prioritize consistent accuracy across the entire forecast horizon rather than peak-specific performance.

**Business context:** Alliander provides transport forecasts to TenneT (transmission system operator) while receiving forecasts from customers. This enables coordinated grid management and capacity planning across network levels.

::

   # Standard transport forecast
   transport_job = PredictionJob(
       name="transport_forecast",
       model="lgb",  # Often performs well for transport
       quantiles=[0.5],  # Focus on median forecast
       resolution_minutes=15
   )
   
   # For component-split requirements
   split_job = PredictionJob(
       name="transport_with_components",
       model="linear",
       split_components=["solar", "wind", "other"]
   )

Grid Loss Forecasts
-------------------

Grid loss forecasting focuses on predicting energy losses in the transmission and distribution network for financial optimization.

**When to use:** You need to optimize grid operations considering market price fluctuations and minimize operational costs.

**Key characteristics:**

- **Primary focus:** Overall accuracy with cost-weighted error minimization
- **Aggregation levels:** Highly aggregated points where system-level patterns dominate
- **Predictive characteristics:** Weather predictors have diminished impact; temporal and cyclic patterns become dominant
- **Key metrics:** rMAE plus total error cost minimization based on market prices

**What makes it different:** Model optimization includes error weighting based on real-time market prices. Weather features become less important at high aggregation levels.

**Business context:** Financial optimization of grid operations where forecast errors have direct cost implications based on energy market prices.

::

   from openstef.model.objective import create_custom_objective
   
   # Cost-weighted optimization
   loss_job = PredictionJob(
       name="grid_losses",
       model="linear",  # Often sufficient for highly aggregated data
       quantiles=[0.5]
   )
   
   # Custom objective with market price weighting
   def cost_weighted_loss(y_true, y_pred, market_prices):
       errors = abs(y_true - y_pred)
       return sum(errors * market_prices)
   
   model = ModelCreator.create_model(
       loss_job,
       objective=cost_weighted_loss
   )

Free Space Estimation
---------------------

Free space estimation predicts available capacity in the grid for new connections or increased consumption.

**When to use:** You need to assess available grid capacity for connection requests or capacity planning.

**Key characteristics:**

- **Primary focus:** Conservative estimates to ensure grid stability
- **Aggregation levels:** Substation or feeder level
- **Model approach:** Often uses quantile regression focusing on lower quantiles for safety margins

**What makes it different:** Emphasizes conservative forecasting to prevent overestimation of available capacity, which could lead to grid instability.

EV Charging Capacity Estimation
-------------------------------

Specialized forecasting for electric vehicle charging infrastructure planning and real-time capacity management.

**When to use:** You need to predict EV charging demand for infrastructure planning or dynamic load management.

**Key characteristics:**

- **Primary focus:** Peak demand periods and charging pattern recognition
- **Temporal patterns:** Strong daily and weekly cycles with growing long-term trends
- **Data requirements:** May include EV adoption rates, charging behavior patterns

**What makes it different:** Incorporates EV-specific behavioral patterns and adoption trends that differ significantly from traditional load patterns.

MV Route Congestion with Topology
----------------------------------

Advanced congestion management that incorporates grid topology information using power-grid-model integration.

**When to use:** You need topology-aware forecasting that considers how power flows through the actual grid structure.

**Key characteristics:**

- **Integration:** Combined with power-grid-model for topology-aware forecasting
- **Complexity:** Higher computational requirements due to power flow calculations
- **Accuracy:** Can provide more accurate results by considering grid physics

**What makes it different:** Unlike standard point-based forecasting, this approach considers how power flows through the grid topology, enabling more sophisticated congestion analysis.

.. note::
   MV route congestion with topology requires additional setup with power-grid-model. See the integration guides for detailed implementation examples.

District Heating
-----------------

Non-electrical energy forecasting for thermal demand in district heating systems.

**When to use:** You need to forecast thermal energy demand for district heating networks.

**Key characteristics:**

- **Domain:** Thermal energy rather than electrical
- **Weather dependency:** Strong correlation with outdoor temperature
- **Seasonal patterns:** Pronounced heating season effects

**What makes it different:** Represents OpenSTEF's expansion beyond electrical grid applications into broader energy forecasting domains.

Choosing the Right Use Case
---------------------------

Consider these factors when selecting your approach:

**Aggregation Level Impact:**

- High aggregation: Weather effects diminish, temporal patterns dominate
- Low aggregation: Higher variability, behavioral factors more important
- Individual level: Highest uncertainty, requires robust handling

**Business Requirements:**

- Peak accuracy: Choose congestion management approach
- Overall accuracy: Use transport forecast methods  
- Cost optimization: Apply grid loss techniques
- Safety margins: Implement free space estimation

**Data Availability:**

- Limited weather data: Consider grid loss approaches
- Rich behavioral data: Leverage congestion management techniques
- Topology information: Explore MV route congestion methods

**Computational Resources:**

- Standard forecasting: Use point-based approaches
- Advanced analysis: Consider topology-aware methods
- High-frequency updates: Optimize for computational efficiency

.. note::
   For detailed implementation examples of each use case, see the tutorials page. For specific deployment patterns, consult the how-to guides section.