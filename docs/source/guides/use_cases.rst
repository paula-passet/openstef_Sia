OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed to address diverse short-term energy forecasting challenges. Each use case has unique characteristics that influence model selection, optimization targets, and evaluation metrics. Understanding these differences helps you choose the right approach for your specific forecasting needs.

This guide covers the major use cases where OpenSTEF excels, from traditional grid congestion management to emerging applications like district heating and topology-aware forecasting. Whether you're managing peak loads at individual substations or optimizing system-wide energy flows, OpenSTEF provides the tools to build accurate, reliable forecasts.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case. Grid operators use these forecasts to prevent overloads and implement demand response strategies at critical network points.

**Primary Focus:** Peak load prediction accuracy
**Aggregation Levels:** Highly variable - from aggregated substations to individual customer connections
**Key Challenge:** Individual customer forecasts can be unpredictable due to behavioral variability

The business context centers on proactive grid management. Operators need precise predictions at congestion points to:

- Schedule maintenance during low-load periods
- Implement demand response programs
- Call customers in advance to reduce consumption
- Prevent equipment overload through early intervention

**Recommended Models:** XGBoost or LightGBM with quantile regression for uncertainty estimation
**Key Metrics:** rMAE@50th quantile at peaks, effective precision and recall for peak detection, rCRPS for probabilistic accuracy
**Model Optimization:** Emphasize high-quantile accuracy and robust peak detection

.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   from openstef.pipeline import train_model_pipeline
   
   # Configure for congestion management
   model = XGBQuantileOpenstfRegressor(
       quantiles=[0.1, 0.5, 0.9],  # Focus on peak uncertainty
       max_depth=6,
       n_estimators=200
   )
   
   # Train with emphasis on peak periods
   trained_model = train_model_pipeline(
       model=model,
       train_data=train_data,
       validation_data=validation_data,
       optimize_for_peaks=True
   )

Transport Forecasts
-------------------

Transport forecasts enable coordination between grid operators at different voltage levels. Distribution system operators (DSOs) provide these forecasts to transmission system operators (TSOs) while receiving similar forecasts from their customers.

**Primary Focus:** Overall forecast accuracy across all time periods
**Aggregation Levels:** Medium aggregated points balancing predictability with granularity
**Business Context:** Grid coordination and capacity planning

For example, Alliander provides transport forecasts to TenneT (the Dutch TSO) while receiving forecasts from its customers. This enables coordinated grid management and optimal capacity allocation across the entire network.

Some operators require component-split transport forecasts (solar, wind, conventional load), necessitating specialized modeling approaches that can decompose total demand into constituent parts.

**Recommended Models:** Linear models or LightGBM for balanced performance
**Key Metrics:** rMAE across entire forecast horizon
**Model Optimization:** Consistent accuracy with emphasis on reliability over peak detection

.. code-block:: python

   from openstef.model.regressors import LGBMOpenstfRegressor
   
   # Configure for transport forecasting
   model = LGBMOpenstfRegressor(
       n_estimators=100,
       max_depth=5,
       learning_rate=0.1,
       objective='regression'  # Focus on overall accuracy
   )
   
   # For component-split forecasts
   from openstef.feature_engineering import create_component_features
   
   # Add renewable generation features
   features = create_component_features(
       data,
       include_solar=True,
       include_wind=True,
       weather_data=weather_data
   )

Grid Loss Forecasts
-------------------

Grid losses represent the energy lost during transmission and distribution. These forecasts support financial optimization of grid operations, particularly when considering dynamic market pricing.

**Primary Focus:** Cost-weighted error minimization
**Aggregation Levels:** Highly aggregated system-level points
**Predictive Characteristics:** Weather predictors have diminished impact; temporal and cyclic patterns dominate

At high aggregation levels, individual weather variations average out, making system-wide behavioral trends and temporal patterns the primary predictive factors. Market price fluctuations add another dimension, as errors during high-price periods are more costly than during low-price periods.

**Recommended Models:** Linear models for interpretability and stability at high aggregation
**Key Metrics:** rMAE plus total error cost minimization based on market prices
**Model Optimization:** Error weighting based on real-time market prices and operational costs

.. code-block:: python

   from openstef.model.regressors import LinearOpenstfRegressor
   from openstef.evaluation import create_cost_weighted_metrics
   
   # Configure for grid loss forecasting
   model = LinearOpenstfRegressor(
       fit_intercept=True,
       normalize=True
   )
   
   # Create cost-weighted evaluation
   cost_metrics = create_cost_weighted_metrics(
       price_data=market_prices,
       error_weights='quadratic'
   )

Free Space Estimation
---------------------

Free space estimation determines available capacity for new connections or increased load at specific grid points. This use case combines forecasting with capacity analysis to support grid planning decisions.

**Primary Focus:** Conservative capacity estimation with safety margins
**Business Context:** New connection requests and grid expansion planning
**Key Challenge:** Balancing conservative estimates with efficient capacity utilization

Grid operators use these forecasts to evaluate connection requests and plan infrastructure investments. The approach requires not just accurate load prediction but also uncertainty quantification to ensure safe capacity margins.

**Recommended Models:** Quantile regression models for conservative capacity estimation
**Key Metrics:** High-quantile accuracy (90th, 95th percentiles) for safety margins
**Model Optimization:** Conservative bias with robust uncertainty estimation

.. code-block:: python

   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   
   # Configure for capacity estimation
   model = XGBQuantileOpenstfRegressor(
       quantiles=[0.5, 0.9, 0.95, 0.99],  # Focus on high quantiles
       max_depth=4,
       conservative_bias=True
   )
   
   # Calculate available capacity
   def estimate_free_space(forecast, capacity_limit, safety_margin=0.1):
       peak_forecast = forecast.quantile(0.95)
       available = capacity_limit * (1 - safety_margin) - peak_forecast
       return max(0, available)

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electricity into thermal demand forecasting. This community-driven use case demonstrates the library's flexibility for non-electrical energy systems.

**Primary Focus:** Thermal demand patterns and temperature dependencies
**Aggregation Levels:** Community or district level aggregation
**Predictive Characteristics:** Strong weather dependency, different seasonal patterns than electricity

District heating systems have distinct characteristics: thermal inertia, storage capabilities, and different weather sensitivities compared to electrical systems. The forecasting approach must account for these thermal dynamics.

**Recommended Models:** Models with strong weather feature engineering
**Key Metrics:** Temperature-weighted accuracy metrics
**Model Optimization:** Enhanced weather feature engineering for thermal applications

.. note::
   District heating support is actively being developed by the OpenSTEF community. Check the latest documentation for current capabilities and examples.

MV Route Congestion Management with Topology
---------------------------------------------

Medium-voltage (MV) route congestion management represents the most advanced OpenSTEF use case, combining traditional forecasting with power system topology analysis using the power-grid-model library.

**Primary Focus:** Topology-aware congestion prediction
**Integration:** Combined with power-grid-model (PGM) for network analysis
**Business Context:** Sophisticated congestion management considering network topology

This approach moves beyond point-based forecasting to consider how power flows through the network topology. By combining OpenSTEF forecasts with power-grid-model's network analysis, operators can predict congestion points that emerge from network constraints rather than just local load increases.

**Recommended Models:** Standard OpenSTEF models combined with PGM topology analysis
**Key Metrics:** Network-aware congestion metrics
**Model Optimization:** Integration with power flow calculations

.. code-block:: python

   from openstef.pipeline import create_forecast
   from power_grid_model import PowerGridModel
   
   # Create standard OpenSTEF forecast
   load_forecast = create_forecast(
       model=trained_model,
       input_data=forecast_data
   )
   
   # Integrate with topology analysis
   pgm_model = PowerGridModel(network_data)
   
   # Run power flow with forecasted loads
   power_flow_result = pgm_model.calculate_power_flow(
       update_data=load_forecast.to_pgm_format()
   )
   
   # Identify topology-based congestion
   congestion_points = identify_congestion(
       power_flow_result,
       capacity_limits
   )

.. note::
   [DIAGRAM: Network topology showing MV routes with forecasted loads and identified congestion points]

Choosing the Right Use Case
---------------------------

Selecting the appropriate use case depends on your specific requirements:

**For peak load management:** Use congestion management forecasts with quantile regression models
**For grid coordination:** Implement transport forecasts with balanced accuracy optimization  
**For financial optimization:** Apply grid loss forecasts with cost-weighted metrics
**For capacity planning:** Deploy free space estimation with conservative uncertainty bounds
**For thermal systems:** Explore district heating approaches with enhanced weather features
**For network analysis:** Combine standard forecasts with topology-aware congestion management

Each use case builds on OpenSTEF's core forecasting capabilities while optimizing for specific business objectives. The modular design allows you to adapt these approaches or combine multiple use cases within a single deployment.

For detailed implementation guidance, see the :doc:`../getting_started/tutorials` page. For specific deployment scenarios, consult the :doc:`how_to_guides` section.