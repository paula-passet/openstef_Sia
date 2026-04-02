Use Cases
=========

OpenSTEF is a flexible forecasting library that supports multiple energy grid use cases. This page helps you identify which use case matches your needs and understand what makes each approach different.

All use cases share the same core workflow—loading data, training models, and generating forecasts—but differ in their input data, prediction targets, and how forecasts inform operational decisions.

Overview
--------

OpenSTEF supports these primary use cases:

- **Congestion forecasts**: Predict peak load on substations to prevent overloading
- **Free space estimation**: Calculate available capacity for new connections
- **Grid loss forecasts**: Predict energy losses in the distribution network
- **Transport forecasts**: Forecast energy flow through transmission infrastructure
- **District heating forecasts**: Predict thermal energy demand in heating networks
- **MV route congestion management**: Manage medium-voltage routes using network topology

Each use case can be implemented with the same OpenSTEF library functions, customized through configuration and data preparation.


Congestion Forecasts
--------------------

Congestion forecasting predicts when and how severely a substation or feeder will approach its capacity limit. This is the most common OpenSTEF use case.

When to use
^^^^^^^^^^^

Use congestion forecasts when you need to:

- Identify substations at risk of overloading in the next 1-48 hours
- Plan preventive switching operations before peak demand
- Prioritize maintenance and grid reinforcement investments
- Provide early warnings to grid operators

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Congestion forecasts focus on **peak load prediction** rather than average consumption. The key characteristics:

- Target variable: Maximum power demand (kW or MW) at a specific location
- Time horizon: Short-term (hours to days ahead)
- Critical metric: Accuracy at high quantiles (P95, P99) to capture extreme events
- Input data: Historical load measurements, weather forecasts, calendar features

Example
^^^^^^^

.. code-block:: python

   from openstef.model.trainer import ModelTrainer
   from openstef.pipeline.train_model import train_model_pipeline
   
   # Configuration for congestion forecasting
   pj = {
       "id": 307,
       "name": "Substation_North",
       "type": "demand",
       "quantiles": [0.5, 0.9, 0.95, 0.99],  # Focus on high quantiles
       "model": "xgb_quantile",
       "resolution_minutes": 15
   }
   
   # Train model with historical load and weather data
   model = train_model_pipeline(pj, input_data)
   
   # Generate forecast for next 48 hours
   forecast = create_forecast_pipeline(pj, model, forecast_input_data)

The forecast provides quantile predictions that tell you: "There's a 95% chance the load will stay below X MW."


Free Space Estimation
---------------------

Free space estimation calculates how much additional capacity is available for new customer connections without causing congestion.

When to use
^^^^^^^^^^^

Use free space estimation when you need to:

- Evaluate connection requests from new customers
- Determine if grid reinforcement is needed before approving connections
- Plan capacity allocation across multiple connection requests
- Provide transparency to customers about connection availability

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Free space estimation combines **load forecasting with capacity analysis**:

- Derived metric: Available capacity = Rated capacity - Forecasted peak load
- Considers safety margins and regulatory requirements
- May aggregate forecasts across multiple feeders
- Often uses high quantiles (P95) to ensure conservative estimates

The calculation typically looks like:

.. code-block:: python

   # After generating congestion forecast
   rated_capacity = 10.0  # MW
   safety_margin = 0.9  # Use 90% of rated capacity
   
   # Use P95 forecast to be conservative
   forecasted_peak = forecast["forecast_p95"].max()
   
   free_space = (rated_capacity * safety_margin) - forecasted_peak
   
   if free_space > requested_connection_size:
       print(f"Connection approved: {free_space:.2f} MW available")
   else:
       print("Grid reinforcement required")

.. note::

   Free space estimation uses the same forecasting models as congestion forecasts but applies different post-processing logic.


Grid Loss Forecasts
-------------------

Grid loss forecasting predicts energy losses in the distribution network due to resistance in cables and transformers.

When to use
^^^^^^^^^^^

Use grid loss forecasts when you need to:

- Calculate energy procurement needs (customer demand + losses)
- Optimize grid operations to minimize losses
- Allocate loss costs across the network
- Monitor grid efficiency over time

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Grid losses are a **derived quantity** that depends on load patterns and network topology:

- Losses increase quadratically with current (I²R losses)
- Require both load forecasts and network impedance data
- May need topology information for accurate calculation
- Typically expressed as percentage of total energy or absolute MWh

Example workflow
^^^^^^^^^^^^^^^^

.. code-block:: python

   # Step 1: Forecast total load
   load_forecast = create_forecast_pipeline(pj, model, input_data)
   
   # Step 2: Calculate losses based on load
   # Simplified loss model (real implementations may use power-grid-model)
   def estimate_losses(load_mw, network_resistance):
       # Losses proportional to load squared
       current = load_mw / voltage
       losses_mw = (current ** 2) * network_resistance
       return losses_mw
   
   forecast["grid_losses"] = estimate_losses(
       forecast["forecast"],
       network_resistance=0.05
   )
   
   # Step 3: Calculate total procurement need
   forecast["total_procurement"] = forecast["forecast"] + forecast["grid_losses"]

For more accurate loss calculations, integrate with power-grid-model to account for voltage drops and network topology.


Transport Forecasts
-------------------

Transport forecasting predicts energy flow through transmission infrastructure connecting different grid areas.

When to use
^^^^^^^^^^^

Use transport forecasts when you need to:

- Predict cross-border or inter-regional energy flows
- Plan transmission capacity allocation
- Coordinate between transmission and distribution operators
- Balance supply and demand across grid regions

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Transport forecasts focus on **net energy flow** rather than absolute consumption:

- Target variable: Net power transfer (can be positive or negative)
- Requires understanding of supply and demand on both sides
- May involve multiple interconnected prediction jobs
- Weather patterns may affect both source and destination regions differently

Example
^^^^^^^

.. code-block:: python

   # Transport forecast configuration
   pj = {
       "id": 450,
       "name": "Interconnector_AB",
       "type": "transport",
       "quantiles": [0.1, 0.5, 0.9],  # Symmetric quantiles for bidirectional flow
       "model": "xgb_quantile",
   }
   
   # Input data includes load from both regions
   input_data["region_a_load"] = region_a_data
   input_data["region_b_load"] = region_b_data
   
   # Forecast net flow (positive = A to B, negative = B to A)
   transport_forecast = create_forecast_pipeline(pj, model, input_data)

Transport forecasts often require coordination with neighboring grid operators to share data and align predictions.


District Heating Forecasts
---------------------------

District heating forecasting predicts thermal energy demand in heating networks that distribute hot water or steam to buildings.

When to use
^^^^^^^^^^^

Use district heating forecasts when you need to:

- Optimize heat generation from multiple sources (CHP, boilers, heat pumps)
- Plan fuel procurement for heating plants
- Prevent supply shortages during cold periods
- Minimize costs by scheduling efficient generation units

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

District heating has unique characteristics compared to electricity:

- **Strong temperature dependency**: Heating demand closely follows outdoor temperature
- **Thermal inertia**: Buildings retain heat, creating lag effects
- **Seasonal patterns**: Demand near zero in summer, peaks in winter
- **Different units**: Typically measured in MW thermal or GJ/hour

Example
^^^^^^^

.. code-block:: python

   # District heating forecast configuration
   pj = {
       "id": 601,
       "name": "District_Heating_Central",
       "type": "demand",
       "quantiles": [0.5, 0.9],
       "model": "xgb_quantile",
       "resolution_minutes": 60
   }
   
   # Temperature is the dominant feature
   input_data["temperature"] = weather_data["temp"]
   input_data["temperature_lag_24h"] = weather_data["temp"].shift(24)
   
   # Train model emphasizing temperature features
   model = train_model_pipeline(pj, input_data)
   
   # Generate forecast
   heating_forecast = create_forecast_pipeline(pj, model, forecast_input_data)

District heating forecasts typically show stronger weather dependency than electricity demand, with temperature explaining 70-90% of variance.


MV Route Congestion Management with Topology
---------------------------------------------

Medium-voltage (MV) route congestion management uses network topology to forecast load on specific cable routes and optimize switching operations.

When to use
^^^^^^^^^^^

Use topology-aware MV forecasting when you need to:

- Manage congestion on specific cable routes, not just substations
- Optimize switching configurations to balance load across routes
- Account for network topology changes (switching, maintenance)
- Simulate "what-if" scenarios for different network configurations

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

This is the most sophisticated OpenSTEF use case, requiring **integration with network topology models**:

- Uses power-grid-model (PGM) for topology representation
- Forecasts propagate through network based on connectivity
- Can simulate different switching states
- Requires detailed network data (cable impedances, switch positions)
- Enables route-level rather than substation-level forecasts

Architecture
^^^^^^^^^^^^

.. note::

   [DIAGRAM: MV route congestion management architecture showing: (1) OpenSTEF forecasts for individual feeders, (2) power-grid-model topology representation, (3) load flow calculation distributing forecasts across routes, (4) congestion detection on specific cables]

Example workflow
^^^^^^^^^^^^^^^^

.. code-block:: python

   from power_grid_model import PowerGridModel
   
   # Step 1: Create forecasts for each feeder
   feeder_forecasts = {}
   for feeder_pj in feeder_prediction_jobs:
       model = train_model_pipeline(feeder_pj, historical_data)
       feeder_forecasts[feeder_pj["id"]] = create_forecast_pipeline(
           feeder_pj, model, forecast_input_data
       )
   
   # Step 2: Load network topology
   pgm = PowerGridModel(input_data=network_topology)
   
   # Step 3: Distribute forecasted loads across routes
   for timestamp in forecast_timestamps:
       # Assign forecasted loads to network nodes
       load_profile = {
           feeder_id: forecast.loc[timestamp, "forecast"]
           for feeder_id, forecast in feeder_forecasts.items()
       }
       
       # Run power flow calculation
       result = pgm.calculate_power_flow(update_data=load_profile)
       
       # Identify congested routes
       for line_id, line_result in result["line"].items():
           loading_pct = line_result["loading"] * 100
           if loading_pct > 80:
               print(f"Route {line_id} congestion: {loading_pct:.1f}%")

This approach enables precise congestion management at the cable level, allowing operators to take targeted switching actions.

Integration requirements
^^^^^^^^^^^^^^^^^^^^^^^^^

To implement topology-aware forecasting:

1. **Network model**: Detailed MV network topology in power-grid-model format
2. **Feeder mapping**: Map OpenSTEF prediction jobs to network nodes
3. **Switching state**: Current and historical switch positions
4. **Validation data**: Measurements at multiple points to validate load flow

.. note::

   Topology-aware forecasting requires significantly more data and infrastructure than basic congestion forecasts. Start with simpler use cases and add topology when route-level precision is needed.


Choosing Your Use Case
-----------------------

This decision tree helps you select the right approach:

1. **Do you need route-level precision with topology?**
   
   - Yes → MV route congestion management with PGM
   - No → Continue to question 2

2. **What are you forecasting?**
   
   - Substation load → Congestion forecasts
   - Available capacity → Free space estimation
   - Network losses → Grid loss forecasts
   - Inter-regional flow → Transport forecasts
   - Thermal demand → District heating forecasts

3. **What's your data availability?**
   
   - Basic: Historical load + weather → Start with congestion forecasts
   - Advanced: Network topology + detailed measurements → Consider topology-aware approach

Most users start with congestion forecasts and expand to other use cases as their needs evolve.


Next Steps
----------

- **Quick implementation**: See :doc:`../getting_started/quickstart` for basic forecasting workflow
- **Detailed tutorial**: Follow :doc:`../getting_started/tutorials` for comprehensive examples
- **Deployment**: Check :doc:`how_to_guides` for production deployment patterns
- **Concepts**: Read :doc:`../reference/concepts` to understand forecasting fundamentals

For questions about which use case fits your situation, visit the OpenSTEF community channels linked in :doc:`../index`.