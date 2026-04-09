Common OpenSTEF Use Cases
==========================

OpenSTEF is a flexible forecasting library that supports diverse energy forecasting applications. This page describes the most common use cases, their unique characteristics, and practical guidance on when to use each approach. Each use case has different accuracy requirements, optimization targets, and data aggregation levels that influence model configuration and evaluation.

.. note:: [DIAGRAM: Use case overview showing different forecasting scenarios (congestion management, transport, grid losses, district heating) with their input data types (load measurements, weather, topology) and output applications (capacity planning, grid operations, financial optimization)]

Understanding Use Case Differences
-----------------------------------

Different forecasting use cases require fundamentally different approaches. The key differentiators are:

- **Optimization target**: Peak accuracy vs. overall accuracy vs. cost-weighted accuracy
- **Aggregation level**: Individual customers (high variability) vs. substations (medium) vs. system-wide (highly aggregated)
- **Temporal focus**: Peak periods only vs. all time periods equally
- **Business context**: Operational safety vs. financial optimization vs. regulatory compliance

OpenSTEF's modular design allows you to configure models, metrics, and evaluation strategies to match your specific use case requirements.

Congestion Management Forecasts
--------------------------------

Congestion management is OpenSTEF's original use case and remains the most common application. Grid operators need accurate predictions at congestion points to prevent transformer and cable overload.

**When to use**: Forecasting load at substations, transformers, cables, or individual customers where peak load accuracy is critical for preventing grid congestion.

**Key characteristics**:

- **Primary focus**: Accuracy near peak load periods
- **Aggregation levels**: Highly variable — from individual customers (very unpredictable) to substations (more stable)
- **Typical applications**: Substation forecasting, MSRs (medium-voltage substations), individual customer predictions
- **Key metrics**: Effective precision and recall, rMAE@50th quantile at peaks, rCRPS

**What makes it different**: Unlike other use cases, congestion forecasts prioritize peak detection over overall accuracy. A model that performs well on average but misses peaks is not suitable for congestion management.

**Model optimization considerations**:

- Emphasis on high quantiles (P90, P95) for conservative capacity planning
- Robust handling of high variability in low-aggregation scenarios
- Feature engineering focused on peak behavior patterns
- Quantile regression to capture uncertainty at peak periods

**Example configuration**:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.models.forecasting import XGBoostForecaster
   from openstef_core.pipeline import CustomForecastingWorkflow
   
   # Configure forecaster for congestion management
   # Focus on high quantiles for conservative peak estimates
   forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.5),   # Median forecast
           Quantile(0.9),   # Conservative estimate
           Quantile(0.95),  # Very conservative for critical assets
       ],
       model_params={
           "max_depth": 6,
           "learning_rate": 0.1,
           "n_estimators": 100,
       }
   )
   
   # Create pipeline for congestion forecasting
   pipeline = CustomForecastingWorkflow(
       model_id="congestion_transformer_123",
       model=forecaster
   )
   
   # Fit and predict
   pipeline.fit(training_dataset)
   forecast = pipeline.predict(input_dataset)

**Free space estimation**: A related use case is estimating remaining capacity on grid assets. This uses the same forecasting approach but focuses on the gap between forecast peak load and asset capacity limits.

Transport Forecasts
-------------------

Transport forecasts predict energy flow between grid operators and are used for coordination and capacity planning. Grid operators provide forecasts to upstream transmission operators and receive forecasts from downstream customers.

**When to use**: Communicating planned energy usage to upstream network operators (e.g., DSO to TSO) or receiving forecasts from downstream customers for coordinated grid management.

**Key characteristics**:

- **Primary focus**: Overall forecast accuracy across all time periods
- **Aggregation levels**: Medium aggregated points (balance between predictability and granularity)
- **Business context**: Regulatory compliance, capacity planning, coordinated grid operations
- **Key metrics**: rMAE (relative Mean Absolute Error)

**What makes it different**: Transport forecasts require consistent accuracy across the entire forecast horizon, not just at peaks. Some operators require component-level forecasts (solar, wind, other), necessitating split-component models.

**Model optimization considerations**:

- Balanced performance across all time periods
- Emphasis on reliability and consistency
- May require separate models for different energy components
- Lower quantile requirements (often just P50) compared to congestion management

**Example configuration**:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.models.forecasting import LGBMForecaster
   
   # Transport forecasts typically focus on median prediction
   forecaster = LGBMForecaster(
       quantiles=[Quantile(0.5)],  # Median forecast sufficient
       model_params={
           "num_leaves": 31,
           "learning_rate": 0.05,
           "n_estimators": 150,
       }
   )
   
   pipeline = CustomForecastingWorkflow(
       model_id="transport_to_tennet",
       model=forecaster
   )

**Real-world example**: Alliander (Dutch DSO) provides transport forecasts to TenneT (transmission system operator) while receiving forecasts from its customers, enabling coordinated grid management.

Grid Loss Forecasts
--------------------

Grid losses represent energy dissipated in transmission and distribution. Accurate loss forecasts enable financial optimization by accounting for market price fluctuations when purchasing replacement energy.

**When to use**: Financial optimization of grid operations where energy losses must be compensated through market purchases.

**Key characteristics**:

- **Primary focus**: Overall accuracy with cost-weighted error minimization
- **Aggregation levels**: Highly aggregated (system-wide patterns dominate)
- **Predictive characteristics**: Weather predictors have diminished impact; temporal and cyclic patterns dominate
- **Key metrics**: rMAE plus total error cost minimization based on market prices

**What makes it different**: Grid loss forecasts operate at high aggregation levels where individual customer behavior averages out. The optimization target includes financial cost, not just prediction accuracy.

**Model optimization considerations**:

- Error weighting based on real-time market prices
- Strong emphasis on temporal features (time of day, day of week, seasonality)
- Reduced importance of weather features compared to other use cases
- May benefit from simpler models due to smoother aggregate patterns

**Example configuration**:

.. code-block:: python

   from openstef_core.types import Quantile
   from openstef_models.models.forecasting import GBLinearForecaster
   
   # Linear models often perform well for highly aggregated forecasts
   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.5)],
       model_params={
           "learning_rate": 0.1,
           "n_estimators": 100,
       }
   )
   
   pipeline = CustomForecastingWorkflow(
       model_id="grid_losses_system",
       model=forecaster
   )

For cost-weighted optimization, you can implement custom evaluation metrics that incorporate market price data during model training and evaluation.

District Heating Demand
-----------------------

District heating is a community use case that demonstrates OpenSTEF's applicability beyond electricity forecasting. It predicts thermal demand for district heating systems.

**When to use**: Forecasting heat demand in district heating networks for operational planning and capacity management.

**Key characteristics**:

- **Domain**: Thermal energy (not electricity)
- **Predictive factors**: Strong weather dependence (temperature, wind), building thermal inertia
- **Aggregation levels**: Varies by network size
- **Temporal patterns**: Different from electricity (slower response times, thermal storage effects)

**What makes it different**: Thermal systems have different physics than electrical grids. Heat demand responds more slowly to weather changes due to building thermal mass, and thermal storage can buffer supply-demand mismatches.

**Model considerations**:

- Temperature is the dominant predictor
- Lagged weather features capture thermal inertia effects
- Different seasonal patterns compared to electricity
- May require domain-specific feature engineering

This use case demonstrates OpenSTEF's flexibility as a general-purpose forecasting library beyond its original DSO/TSO focus.

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion forecasting combines OpenSTEF with power-grid-model for topology-aware forecasting. This advanced use case accounts for grid structure and power flow physics.

**When to use**: Forecasting congestion on MV routes where grid topology and power flow constraints significantly impact load distribution.

**Key characteristics**:

- **Integration**: Combines OpenSTEF forecasts with power-grid-model topology analysis
- **Complexity**: Requires grid topology data and power flow calculations
- **Applications**: MV cable loading, route-level congestion management
- **Research basis**: Published methodology available in academic literature

**What makes it different**: Standard OpenSTEF forecasts are point-based (each location forecasted independently). Topology-aware forecasting uses grid structure to improve accuracy and ensure physical consistency.

**Implementation approach**:

1. Generate point forecasts using OpenSTEF for grid nodes
2. Load grid topology into power-grid-model
3. Run power flow calculations to distribute forecasts across routes
4. Identify congestion points based on cable/transformer ratings

.. code-block:: python

   from openstef_core.pipeline import CustomForecastingWorkflow
   from openstef_models.models.forecasting import XGBoostForecaster
   # power-grid-model integration (external library)
   from power_grid_model import PowerGridModel
   
   # Step 1: Generate node forecasts with OpenSTEF
   forecaster = XGBoostForecaster(quantiles=[Quantile(0.9)])
   pipeline = CustomForecastingWorkflow(model_id="node_forecast", model=forecaster)
   node_forecasts = pipeline.predict(input_dataset)
   
   # Step 2: Load grid topology (example structure)
   grid_model = PowerGridModel(
       input_data={
           "node": node_data,
           "line": line_data,
           "transformer": transformer_data,
       }
   )
   
   # Step 3: Run power flow with forecasted loads
   # (Implementation details depend on power-grid-model API)
   power_flow_results = grid_model.calculate_power_flow(
       update_data={"sym_load": node_forecasts}
   )
   
   # Step 4: Identify congestion on MV routes
   congested_lines = power_flow_results["line"][
       power_flow_results["line"]["loading"] > 0.8
   ]

.. note::
   Topology-aware forecasting requires additional expertise in power systems analysis and grid modeling. Refer to published research papers on OpenSTEF + power-grid-model integration for detailed methodology.

Choosing the Right Use Case Configuration
------------------------------------------

When implementing your forecasting solution, consider these questions:

**What matters most?**

- Peak accuracy → Congestion management
- Overall accuracy → Transport forecasts
- Cost optimization → Grid losses
- Thermal dynamics → District heating

**What is your aggregation level?**

- Individual customers → High variability, need robust models
- Substations/routes → Medium aggregation, balanced approach
- System-wide → High aggregation, simpler patterns

**What metrics should you optimize?**

- Congestion: rMAE@peaks, effective precision/recall, rCRPS
- Transport: rMAE across all periods
- Grid losses: rMAE + cost-weighted error
- District heating: Domain-specific metrics

**Do you need topology awareness?**

- Point-based forecasting (standard OpenSTEF) works for most use cases
- Topology-aware forecasting (OpenSTEF + power-grid-model) needed for route-level analysis

See Also
--------

- :doc:`data_integration`: Connecting OpenSTEF to your data sources
- :doc:`deployment`: Production deployment patterns for different scales
- :doc:`../core_concepts/metrics`: Understanding evaluation metrics for different use cases
- :doc:`../tutorials/quickstart`: Getting started with basic forecasting