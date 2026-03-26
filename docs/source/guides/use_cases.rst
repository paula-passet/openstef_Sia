OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library designed for short-term energy forecasting across diverse applications. Each use case has distinct requirements for accuracy, optimization targets, and operational constraints. This guide helps you identify which approach matches your specific forecasting needs.

Congestion Management
---------------------

Congestion management represents OpenSTEF's original and most mature use case. Grid operators need precise predictions at congestion points to implement effective mitigation strategies before overloads occur.

**Primary focus:** Accuracy during peak load periods when grid congestion is most likely.

**Aggregation characteristics:** Highly variable, ranging from very aggregated points (substations) to low-aggregation scenarios (individual customers). Individual customer forecasts present particular challenges due to behavioral unpredictability.

**Typical applications:**
- Substation load forecasting
- Individual customer predictions  
- Medium-voltage substation (MSR) monitoring
- Peak demand response planning

**Key metrics:** Effective precision and recall for peak detection, rMAE@50th quantile at peaks, rCRPS for uncertainty quantification.

**Model optimization:** Emphasis on peak detection accuracy and high-quantile performance, with robust handling of high variability in low-aggregation scenarios.

.. code-block:: python

   from openstef_beam.forecasting import create_forecast
   from openstef_beam.metrics import confusion_matrix, precision_recall
   
   # Configure for congestion management
   forecast_config = {
       "model_type": "xgb",
       "quantiles": [0.1, 0.5, 0.9],  # Focus on high quantiles
       "feature_modules": ["weather", "calendar", "lag"],
       "optimize_for_peaks": True
   }
   
   # Generate forecast with peak detection focus
   forecast = create_forecast(data, config=forecast_config)
   
   # Evaluate peak detection performance
   cm = confusion_matrix(y_true, forecast["forecast"], 
                        threshold_percentile=90)
   pr = precision_recall(cm, effective=True)

**When to use:** Grid operators managing local congestion, utilities implementing demand response programs, or any application where peak load prediction is critical for operational decisions.

Transport Forecasts
-------------------

Transport forecasts provide grid operators with reliable predictions to communicate planned energy usage to upstream network operators and receive forecasts from downstream customers.

**Primary focus:** Overall forecast accuracy across all time periods, not just peaks.

**Aggregation characteristics:** Medium aggregated points, providing a balance between predictability and granularity.

**Business context:** Essential for coordinated grid management between transmission system operators (like TenneT) and distribution system operators (like Alliander). Some operators require transport forecasts split into components (solar, wind, other), necessitating split-component models.

**Key metrics:** rMAE across the entire forecast horizon.

**Model optimization:** Balanced performance with emphasis on reliability and consistency.

.. code-block:: python

   # Configure for transport forecasting
   transport_config = {
       "model_type": "linear",
       "quantiles": [0.25, 0.5, 0.75],
       "feature_modules": ["weather", "calendar", "lag", "solar_split"],
       "split_components": ["solar", "wind", "other"],
       "optimize_for_balance": True
   }
   
   # Generate component-split transport forecast
   forecast = create_forecast(data, config=transport_config)
   
   # Evaluate overall accuracy
   rmae_score = rmae(y_true, forecast["forecast"])

**When to use:** Distribution system operators coordinating with transmission operators, utilities requiring component-split forecasts, or applications where consistent accuracy across all periods is more important than peak detection.

Grid Loss Forecasting
---------------------

Grid loss forecasting focuses on financial optimization of grid operations, considering market price fluctuations and operational costs.

**Primary focus:** Overall accuracy with cost-weighted error minimization based on real-time market prices.

**Aggregation characteristics:** Highly aggregated points where system-level temporal and cyclic patterns dominate over local variations.

**Predictive characteristics:** Weather predictors have diminished impact at this aggregation level. Stronger temporal patterns and system-wide behavioral trends become the dominant factors.

**Key metrics:** Similar to transport forecasts plus total error cost minimization based on market prices.

**Model optimization:** Error weighting based on real-time market prices and operational costs.

.. code-block:: python

   # Configure for grid loss forecasting
   loss_config = {
       "model_type": "linear",
       "feature_modules": ["calendar", "lag", "price"],
       "cost_weighting": True,
       "market_price_column": "electricity_price",
       "aggregation_level": "system"
   }
   
   # Generate cost-optimized forecast
   forecast = create_forecast(data, config=loss_config)
   
   # Evaluate with cost weighting
   weighted_mae = mae(y_true, forecast["forecast"], 
                     sample_weights=market_prices)

**When to use:** Grid operators optimizing financial performance, utilities with significant grid losses, or applications where operational costs vary significantly with market conditions.

Free Space Estimation
---------------------

Free space estimation determines available grid capacity for new connections, particularly important for EV charging infrastructure and renewable energy integration.

**Primary focus:** Conservative capacity estimates that prevent grid overload while maximizing utilization.

**Aggregation characteristics:** Varies from individual connection points to substation level, depending on the capacity planning scope.

**Business context:** Essential for grid expansion planning, EV charging network deployment, and renewable energy integration. Requires balancing conservative estimates (to prevent overload) with optimal utilization of existing infrastructure.

**Model optimization:** Emphasis on high-quantile accuracy to ensure capacity estimates account for peak scenarios.

.. code-block:: python

   # Configure for free space estimation
   capacity_config = {
       "model_type": "xgb",
       "quantiles": [0.8, 0.9, 0.95],  # Conservative estimates
       "feature_modules": ["weather", "calendar", "lag", "capacity"],
       "safety_margin": 0.1,  # 10% safety buffer
       "optimize_for_capacity": True
   }
   
   # Generate capacity forecast
   forecast = create_forecast(data, config=capacity_config)
   
   # Calculate available capacity
   peak_forecast = forecast["quantile_0.95"]
   available_capacity = grid_capacity - peak_forecast - safety_margin

**When to use:** Grid planners assessing connection capacity, EV charging network operators, renewable energy developers, or any application requiring conservative capacity estimates.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model for topology-aware predictions, enabling more precise congestion management.

**Primary focus:** Topology-aware congestion prediction that accounts for network configuration and power flow constraints.

**Integration approach:** Uses power-grid-model (PGM) to incorporate electrical network topology into forecasting decisions, enabling more accurate congestion predictions.

**Business context:** Advanced congestion management that considers not just load magnitude but also network constraints and power flow patterns.

.. code-block:: python

   from power_grid_model import PowerGridModel
   
   # Configure topology-aware forecasting
   topology_config = {
       "model_type": "xgb", 
       "feature_modules": ["weather", "calendar", "lag", "topology"],
       "topology_integration": True,
       "pgm_model": grid_model,  # Power-grid-model instance
       "constraint_awareness": True
   }
   
   # Generate topology-aware forecast
   forecast = create_forecast(data, config=topology_config)
   
   # Validate against network constraints
   pgm_results = grid_model.calculate_power_flow(forecast["forecast"])
   congestion_points = identify_violations(pgm_results)

**When to use:** Advanced grid operators with detailed network models, utilities implementing sophisticated congestion management, or applications where network topology significantly impacts congestion patterns.

District Heating and Thermal Systems
-------------------------------------

District heating represents OpenSTEF's expansion beyond electricity into thermal demand forecasting, demonstrating the library's broader applicability to energy systems.

**Primary focus:** Thermal demand prediction for district heating networks, considering temperature dependencies and seasonal patterns.

**Aggregation characteristics:** Typically aggregated at district or neighborhood level, with strong weather dependency and seasonal variations.

**Business context:** Community energy systems, municipal heating networks, and integrated energy planning where thermal and electrical systems interact.

.. note::
   District heating support is under active development. The core forecasting framework applies directly, but domain-specific features for thermal systems are being refined based on community feedback.

**When to use:** District heating operators, municipal energy planners, integrated energy system operators, or any thermal energy application requiring short-term demand forecasting.

Choosing the Right Approach
----------------------------

The choice between use cases depends on your specific operational requirements:

**For peak-critical applications** (congestion management, capacity planning): Choose approaches optimized for high-quantile accuracy and peak detection.

**For operational coordination** (transport forecasts): Prioritize overall accuracy and reliability across all time periods.

**For financial optimization** (grid losses): Focus on cost-weighted accuracy that accounts for market conditions.

**For capacity planning** (free space estimation): Emphasize conservative estimates with appropriate safety margins.

**For advanced applications** (topology-aware forecasting): Integrate with network models for constraint-aware predictions.

Each approach can be customized through OpenSTEF's modular architecture. See the tutorials in the getting started section for detailed implementation examples and the how-to guides for specific deployment patterns.