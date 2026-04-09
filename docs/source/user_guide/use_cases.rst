Common Use Cases
================

OpenSTEF supports a diverse range of energy forecasting applications, each with distinct requirements for accuracy, optimization targets, and aggregation levels. This page describes the most common use cases, explains what makes them different, and provides guidance on when to use each approach.

Understanding Use Case Characteristics
---------------------------------------

Different forecasting use cases optimize for different objectives:

- **Congestion forecasts** prioritize accuracy at peak load periods
- **Transport forecasts** require balanced accuracy across all time periods
- **Grid loss forecasts** optimize for cost-weighted error minimization
- **Free space estimation** focuses on remaining capacity calculations
- **District heating** applies forecasting to thermal demand (non-electrical)

The aggregation level significantly impacts model behavior. Highly aggregated forecasts (e.g., grid losses) exhibit strong temporal patterns where weather predictors have diminished impact. Low-aggregation forecasts (e.g., individual customers) show high behavioral variability and require robust handling of unpredictability.

Congestion Management Forecasts
--------------------------------

Grid operators need precise predictions at congestion points to prevent transformer and cable overload. These forecasts enable proactive mitigation strategies such as demand response, customer compensation programs, and capacity planning.

**When to use:** Forecasting load at substations, transformers, cables, or individual customer connections where overload risk exists.

**Key characteristics:**

- **Primary focus:** Accuracy near peak load periods
- **Aggregation levels:** Highly variable, from aggregated substations to individual customers
- **Typical applications:** Substation forecasting, MSRs (medium-voltage substations), individual customer predictions
- **Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS
- **Model optimization:** Emphasis on peak detection and high-quantile accuracy

Individual customer forecasts present particular challenges due to behavioral variability. The model must handle high uncertainty while maintaining useful peak predictions.

.. code-block:: python

   from openstef.pipeline import train_model
   from openstef.model.model_creator import ModelCreator
   
   # Configure for congestion forecasting
   # Emphasize peak performance with quantile models
   model_specs = {
       "model": "xgb_quantile",
       "quantiles": [0.1, 0.5, 0.9],  # Include high quantiles for peak detection
       "hyper_params": {
           "subsample": 0.8,
           "max_depth": 7,
           "min_child_weight": 3
       }
   }
   
   # Train with focus on peak periods
   trained_model = train_model(
       pj=prediction_job,
       model_type="xgb_quantile",
       quantiles=[0.1, 0.5, 0.9]
   )

Transport Forecasts
-------------------

Grid operators communicate planned energy usage to upstream network operators and receive forecasts from downstream customers. This enables coordinated grid management and capacity planning across the transmission and distribution network.

**When to use:** Reporting energy transport to transmission system operators (e.g., Alliander to TenneT) or receiving forecasts from large customers.

**Key characteristics:**

- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregated points balancing predictability and granularity
- **Business context:** Coordinated grid management between network operators
- **Key metrics:** rMAE
- **Model optimization:** Balanced performance across entire forecast horizon

Some operators require transport forecasts split into components (solar, wind, other generation), necessitating split-component models that forecast each source separately.

.. code-block:: python

   from openstef.pipeline import train_model
   
   # Standard transport forecast configuration
   model_specs = {
       "model": "xgb",
       "hyper_params": {
           "subsample": 0.9,
           "max_depth": 5,
           "learning_rate": 0.1
       }
   }
   
   # For component-split forecasts, train separate models
   solar_model = train_model(
       pj=solar_prediction_job,
       model_type="xgb"
   )
   
   wind_model = train_model(
       pj=wind_prediction_job,
       model_type="xgb"
   )
   
   other_model = train_model(
       pj=other_prediction_job,
       model_type="xgb"
   )

Grid Loss Forecasts
-------------------

Grid losses represent energy dissipated in transmission and distribution infrastructure. Accurate forecasts enable financial optimization considering market price fluctuations and operational costs.

**When to use:** Optimizing energy procurement to account for grid losses, financial planning for loss compensation.

**Key characteristics:**

- **Primary focus:** Overall accuracy with cost-weighted error minimization
- **Aggregation levels:** Highly aggregated where system-level patterns dominate
- **Predictive characteristics:** Weather predictors have diminished impact; temporal and cyclic patterns dominate
- **Business context:** Financial optimization considering market prices
- **Key metrics:** rMAE plus total error cost minimization based on market prices
- **Model optimization:** Error weighting based on real-time market prices

At high aggregation levels, individual weather variations matter less than system-wide behavioral trends and temporal patterns (time of day, day of week, seasonal cycles).

.. code-block:: python

   from openstef.pipeline import train_model
   
   # Grid loss forecasts emphasize temporal features
   model_specs = {
       "model": "xgb",
       "hyper_params": {
           "subsample": 0.9,
           "max_depth": 4,  # Shallower trees for aggregated patterns
           "learning_rate": 0.05
       }
   }
   
   # Consider cost-weighted evaluation during model selection
   # (Implementation depends on your market price data integration)
   trained_model = train_model(
       pj=prediction_job,
       model_type="xgb"
   )

Free Space Estimation
---------------------

Free space (remaining capacity) estimation calculates how much additional load a grid component can handle before reaching its rated capacity. This supports connection requests, capacity planning, and proactive grid reinforcement.

**When to use:** Evaluating new connection requests, planning grid expansions, estimating available capacity for EV charging or solar installations.

**Key characteristics:**

- Derived from congestion forecasts by subtracting predicted peak load from rated capacity
- Requires accurate peak load predictions
- Often combined with uncertainty quantification to provide confidence intervals

.. code-block:: python

   from openstef.pipeline import make_forecast
   
   # Generate peak load forecast
   forecast = make_forecast(
       pj=prediction_job,
       model=trained_model
   )
   
   # Calculate free space
   rated_capacity = 630  # kW, transformer rating
   predicted_peak = forecast["forecast"].quantile(0.9)  # 90th percentile
   free_space = rated_capacity - predicted_peak
   
   print(f"Estimated free space: {free_space:.1f} kW")
   print(f"Remaining capacity: {(free_space/rated_capacity)*100:.1f}%")

District Heating Demand
-----------------------

District heating systems distribute thermal energy for space heating and hot water. While not electricity-related, the forecasting principles and OpenSTEF library apply equally well to thermal demand prediction.

**When to use:** Forecasting heat demand for district heating networks, optimizing combined heat and power (CHP) operations.

**Key characteristics:**

- Strong correlation with outdoor temperature and weather conditions
- Seasonal patterns with winter peaks
- Similar modeling approaches to electrical load forecasting
- May require different feature engineering (e.g., heating degree days)

.. code-block:: python

   from openstef.pipeline import train_model
   from openstef.feature_engineering.feature_applicator import FeatureApplicator
   
   # District heating emphasizes temperature features
   # Standard OpenSTEF weather features work well
   model_specs = {
       "model": "xgb",
       "hyper_params": {
           "subsample": 0.85,
           "max_depth": 6,
           "learning_rate": 0.1
       }
   }
   
   trained_model = train_model(
       pj=heating_prediction_job,
       model_type="xgb"
   )

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion forecasting combines load predictions with grid topology information using power-grid-model. This enables topology-aware forecasting that accounts for network configuration and power flow constraints.

**When to use:** Forecasting congestion on MV routes where topology changes (switching operations, maintenance) affect load distribution.

**Key characteristics:**

- Integrates OpenSTEF forecasts with power-grid-model for power flow calculations
- Accounts for network topology and switching states
- Enables "what-if" analysis for different network configurations
- Requires grid topology data and switching state information

.. note::
   Integration with power-grid-model requires additional setup and topology data. Refer to the power-grid-model documentation for grid modeling details.

.. code-block:: python

   from openstef.pipeline import make_forecast
   # Note: power-grid-model integration example
   # Actual implementation depends on your grid model setup
   
   # Generate forecasts for multiple points on the MV route
   forecasts = {}
   for location in mv_route_locations:
       forecast = make_forecast(
           pj=location.prediction_job,
           model=location.trained_model
       )
       forecasts[location.id] = forecast
   
   # Combine with power-grid-model for topology-aware analysis
   # (Requires power-grid-model setup - see power-grid-model docs)
   # grid_model = load_grid_topology(...)
   # power_flow_result = grid_model.calculate_power_flow(forecasts)

Choosing the Right Approach
----------------------------

Consider these factors when selecting a use case approach:

1. **Business objective:** What decision does the forecast support? Peak management, capacity planning, financial optimization?

2. **Aggregation level:** Individual customers require different modeling than highly aggregated grid losses.

3. **Accuracy requirements:** Where does accuracy matter most? Peaks, overall performance, or cost-weighted errors?

4. **Available data:** Do you have topology information, market prices, component-level measurements?

5. **Evaluation metrics:** Choose metrics aligned with business objectives (see metrics documentation).

For deployment patterns and production considerations, see :doc:`deployment`. For integrating data sources, refer to :doc:`data_integration`.