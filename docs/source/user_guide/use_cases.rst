Common Use Cases
================

OpenSTEF supports diverse energy forecasting applications, each with distinct characteristics and requirements. This page describes the most common use cases, their typical configurations, and when to apply each approach.

Congestion Management Forecasts
--------------------------------

Congestion forecasts predict peak load periods at grid assets like transformers, cables, and substations. Grid operators use these forecasts to prevent overloads through proactive interventions such as calling customers to reduce consumption or implementing demand response programs.

When to Use
^^^^^^^^^^^

Use congestion forecasts when:

- You need to predict peak moments at specific grid assets
- Accuracy near capacity limits is more important than overall accuracy
- You're forecasting at low aggregation levels (individual substations, MSRs, or even individual customers)
- The business goal is preventing grid overloads rather than financial optimization

Key Characteristics
^^^^^^^^^^^^^^^^^^^

**Aggregation levels:** Highly variable, from very aggregated points down to individual customers. Individual customer forecasts are particularly challenging due to behavioral unpredictability.

**Optimization focus:** Peak detection and high-quantile accuracy. The model should excel at predicting when loads approach or exceed capacity thresholds.

**Evaluation metrics:** Effective precision and recall at peak thresholds, rMAE at the 50th quantile during peaks, and rCRPS (relative Continuous Ranked Probability Score).

**Typical applications:** Substation forecasting, medium-voltage substations (MSRs), individual customer predictions, transformer and cable loading predictions.

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   
   # Configure pipeline for congestion forecasting
   pipeline = create_forecast_pipeline(
       model=XGBQuantileOpenstfRegressor(
           quantiles=[0.1, 0.5, 0.9],  # Include high quantiles for peak detection
           objective="reg:quantileerror"
       ),
       horizon_hours=47,
       resolution_minutes=15
   )
   
   # Train with emphasis on peak periods
   pipeline.train(
       data=historical_data,
       target_column="load",
       feature_columns=["temperature", "wind_speed", "hour", "day_of_week"]
   )
   
   # Generate forecast with quantile predictions
   forecast = pipeline.predict(input_data)

.. note::

   For congestion forecasts, consider using quantile regression to capture uncertainty around peak predictions. The 90th percentile forecast is often more valuable than the median for capacity planning.

Transport Forecasts
-------------------

Transport forecasts predict overall energy flow through the grid, enabling coordination between grid operators at different voltage levels. These forecasts support capacity planning and grid management across the network hierarchy.

When to Use
^^^^^^^^^^^

Use transport forecasts when:

- You need to communicate planned energy usage to upstream network operators
- You receive forecasts from downstream customers and need to aggregate them
- Overall accuracy across all time periods matters more than peak-specific accuracy
- You need component-split forecasts (solar, wind, other)

Key Characteristics
^^^^^^^^^^^^^^^^^^^

**Aggregation levels:** Medium aggregation, balancing predictability with granularity.

**Optimization focus:** Balanced performance across the entire forecast horizon with emphasis on reliability.

**Evaluation metrics:** rMAE (relative Mean Absolute Error) across all forecast periods.

**Business context:** Grid operators like Alliander provide transport forecasts to transmission system operators (e.g., TenneT) while receiving forecasts from customers, enabling coordinated grid management.

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from openstef.model.regressors import XGBOpenstfRegressor
   
   # Configure pipeline for transport forecasting
   pipeline = create_forecast_pipeline(
       model=XGBOpenstfRegressor(),
       horizon_hours=168,  # Week-ahead forecast
       resolution_minutes=60
   )
   
   # Train with balanced objective
   pipeline.train(
       data=historical_data,
       target_column="transport_load",
       feature_columns=["temperature", "radiation", "wind_speed", 
                       "hour", "day_of_week", "is_holiday"]
   )
   
   forecast = pipeline.predict(input_data)

For component-split forecasts (separating solar, wind, and other sources), train separate models for each component:

.. code-block:: python

   # Train component-specific models
   solar_pipeline = create_forecast_pipeline(model=XGBOpenstfRegressor())
   solar_pipeline.train(data=historical_data, target_column="solar_generation")
   
   wind_pipeline = create_forecast_pipeline(model=XGBOpenstfRegressor())
   wind_pipeline.train(data=historical_data, target_column="wind_generation")
   
   other_pipeline = create_forecast_pipeline(model=XGBOpenstfRegressor())
   other_pipeline.train(data=historical_data, target_column="other_load")
   
   # Generate component forecasts
   solar_forecast = solar_pipeline.predict(input_data)
   wind_forecast = wind_pipeline.predict(input_data)
   other_forecast = other_pipeline.predict(input_data)
   
   # Aggregate for total transport forecast
   total_forecast = solar_forecast + wind_forecast + other_forecast

Grid Loss Forecasts
-------------------

Grid loss forecasts predict energy losses in the distribution network, enabling financial optimization of grid operations. These forecasts help operators minimize costs by accounting for market price fluctuations when planning grid operations.

When to Use
^^^^^^^^^^^

Use grid loss forecasts when:

- You need to optimize operational costs based on energy market prices
- You're forecasting at highly aggregated system levels
- Temporal and cyclic patterns dominate over weather effects
- Financial accuracy matters more than physical precision

Key Characteristics
^^^^^^^^^^^^^^^^^^^

**Aggregation levels:** Highly aggregated points where system-level patterns dominate.

**Optimization focus:** Error weighting based on real-time market prices and operational costs. Minimizing cost-weighted forecast errors is more important than minimizing absolute errors.

**Evaluation metrics:** rMAE plus total error cost minimization based on market prices.

**Predictive characteristics:** Weather predictors have diminished impact at this aggregation level. Temporal patterns and system-wide behavioral trends become the dominant factors.

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from openstef.model.regressors import XGBOpenstfRegressor
   
   # Configure pipeline for grid loss forecasting
   pipeline = create_forecast_pipeline(
       model=XGBOpenstfRegressor(),
       horizon_hours=24,
       resolution_minutes=15
   )
   
   # Train with emphasis on temporal features
   pipeline.train(
       data=historical_data,
       target_column="grid_losses",
       feature_columns=["hour", "day_of_week", "month", 
                       "is_holiday", "is_weekend",
                       "total_load"]  # Weather features less important
   )
   
   forecast = pipeline.predict(input_data)

To incorporate cost-weighted optimization, apply custom sample weights during training:

.. code-block:: python

   import pandas as pd
   
   # Calculate sample weights based on historical market prices
   market_prices = pd.read_csv("market_prices.csv", index_col="datetime")
   sample_weights = market_prices["price"] / market_prices["price"].mean()
   
   # Train with cost-weighted samples
   pipeline.train(
       data=historical_data,
       target_column="grid_losses",
       feature_columns=feature_columns,
       sample_weight=sample_weights
   )

Free Space Estimation
---------------------

Free space estimation calculates remaining capacity at grid connection points, helping operators manage new connections and prevent overloading. This use case combines load forecasting with capacity constraints to determine available headroom.

When to Use
^^^^^^^^^^^

Use free space estimation when:

- You need to assess available capacity for new connections
- You're managing EV charging infrastructure deployment
- You need to communicate capacity constraints to customers
- You're planning grid reinforcements based on remaining capacity

Key Characteristics
^^^^^^^^^^^^^^^^^^^

Free space estimation builds on congestion forecasting but adds capacity constraint logic. The forecast predicts peak loads, then subtracts them from rated capacity to determine remaining space.

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from openstef.model.regressors import XGBQuantileOpenstfRegressor
   
   # First, create congestion forecast with high quantiles
   pipeline = create_forecast_pipeline(
       model=XGBQuantileOpenstfRegressor(quantiles=[0.5, 0.9, 0.95]),
       horizon_hours=47,
       resolution_minutes=15
   )
   
   pipeline.train(data=historical_data, target_column="load")
   load_forecast = pipeline.predict(input_data)
   
   # Calculate free space using conservative (high quantile) estimates
   rated_capacity = 630  # kW, for example
   free_space = rated_capacity - load_forecast["quantile_0.95"]
   
   # Identify periods with available capacity
   available_periods = free_space[free_space > 0]
   print(f"Available capacity: {available_periods.min():.1f} kW")

.. warning::

   Always use conservative (high quantile) forecasts for free space estimation to avoid overcommitting capacity. The 95th percentile is commonly used to maintain safety margins.

MV Route Congestion with Topology
----------------------------------

MV (medium-voltage) route congestion forecasting combines OpenSTEF with power-grid-model to account for network topology. This approach distributes forecasted loads across the network structure, identifying congestion points that depend on power flow patterns.

When to Use
^^^^^^^^^^^

Use topology-aware forecasting when:

- Congestion depends on power flow distribution, not just total load
- You need to identify bottlenecks in meshed or complex network topologies
- You're forecasting for medium-voltage networks with multiple routes
- Load distribution across the network varies significantly

Key Characteristics
^^^^^^^^^^^^^^^^^^^

This use case requires integration between OpenSTEF (for load forecasting) and power-grid-model (for power flow calculations). The workflow involves forecasting loads at multiple points, then running power flow analysis to determine actual loading on network assets.

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from openstef.model.regressors import XGBOpenstfRegressor
   import power_grid_model as pgm
   
   # Step 1: Forecast loads at multiple network points
   forecasts = {}
   for location_id in network_locations:
       pipeline = create_forecast_pipeline(model=XGBOpenstfRegressor())
       pipeline.train(
           data=historical_data[location_id],
           target_column="load"
       )
       forecasts[location_id] = pipeline.predict(input_data)
   
   # Step 2: Set up power grid model with network topology
   grid = pgm.PowerGridModel(
       input_data={
           "node": nodes_data,
           "line": lines_data,
           "transformer": transformers_data,
           "sym_load": loads_data
       }
   )
   
   # Step 3: Run power flow calculation with forecasted loads
   for timestamp in forecasts[location_id].index:
       # Update load values from forecasts
       load_updates = {
           "sym_load": [
               {"id": loc_id, "p_specified": forecasts[loc_id].loc[timestamp]}
               for loc_id in network_locations
           ]
       }
       
       # Calculate power flow
       result = grid.calculate_power_flow(update_data=load_updates)
       
       # Identify congested assets
       line_loading = result["line"]["loading"]
       congested_lines = line_loading > 0.8  # 80% threshold

.. note::

   Integration with power-grid-model requires careful alignment of network topology data with forecast locations. See the power-grid-model documentation for details on network modeling.

District Heating Demand
-----------------------

District heating forecasts predict thermal demand in community heating systems. While OpenSTEF was originally designed for electrical grid forecasting, its architecture supports thermal demand forecasting with appropriate feature engineering.

When to Use
^^^^^^^^^^^

Use OpenSTEF for district heating when:

- You're forecasting thermal demand in district heating networks
- Temperature and weather patterns strongly influence demand
- You need short-term operational forecasts for heating plant scheduling
- You want to leverage OpenSTEF's proven forecasting algorithms for non-electrical applications

Key Characteristics
^^^^^^^^^^^^^^^^^^^

**Predictive features:** Temperature is the dominant predictor for heating demand. Wind speed and solar radiation also affect building heat loss.

**Seasonality:** Strong seasonal patterns with minimal demand in summer and peak demand in winter.

**Aggregation:** Typically forecasted at plant or network level rather than individual buildings.

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef.pipeline import create_forecast_pipeline
   from openstef.model.regressors import XGBOpenstfRegressor
   
   # Configure pipeline for district heating
   pipeline = create_forecast_pipeline(
       model=XGBOpenstfRegressor(),
       horizon_hours=48,
       resolution_minutes=60
   )
   
   # Train with temperature-focused features
   pipeline.train(
       data=historical_data,
       target_column="thermal_demand",  # MW or GJ
       feature_columns=[
           "temperature",
           "wind_speed",
           "radiation",
           "hour",
           "day_of_week",
           "is_weekend",
           "month"
       ]
   )
   
   forecast = pipeline.predict(input_data)

.. note::

   District heating demand typically shows stronger temperature correlation than electrical load. Consider adding degree-day features or temperature moving averages to improve accuracy.

Choosing the Right Use Case
----------------------------

The table below summarizes key differences between use cases:

+---------------------------+---------------------+-------------------------+------------------------+
| Use Case                  | Aggregation Level   | Primary Metric          | Optimization Focus     |
+===========================+=====================+=========================+========================+
| Congestion Management     | Low to Medium       | rMAE@peaks, rCRPS       | Peak detection         |
+---------------------------+---------------------+-------------------------+------------------------+
| Transport Forecasts       | Medium              | rMAE                    | Overall accuracy       |
+---------------------------+---------------------+-------------------------+------------------------+
| Grid Loss Forecasts       | High                | Cost-weighted error     | Financial optimization |
+---------------------------+---------------------+-------------------------+------------------------+
| Free Space Estimation     | Low to Medium       | rMAE@peaks              | Conservative peaks     |
+---------------------------+---------------------+-------------------------+------------------------+
| MV Route Congestion       | Medium              | rMAE + flow analysis    | Topology-aware peaks   |
+---------------------------+---------------------+-------------------------+------------------------+
| District Heating          | Medium to High      | rMAE                    | Temperature response   |
+---------------------------+---------------------+-------------------------+------------------------+

For data integration patterns and production deployment approaches, see :doc:`data_integration` and :doc:`deployment`.