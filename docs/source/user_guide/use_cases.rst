Common Use Cases
================

This page demonstrates practical applications of OpenSTEF for different energy forecasting scenarios. Each use case addresses specific operational challenges in energy grid management, from preventing transformer overloads to optimizing district heating systems.

Understanding which use case matches your needs helps you configure OpenSTEF appropriately—different scenarios require different data, metrics, and model configurations.


Congestion Forecasting
----------------------

Congestion forecasting predicts when grid assets like transformers, cables, or substations will approach or exceed their capacity limits. This is critical for preventing equipment damage and planning grid reinforcements.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Unlike general load forecasting, congestion forecasting prioritizes accurate peak detection over overall accuracy. A model that slightly overestimates peaks is often preferable to one with better average accuracy but poor peak detection.

Key characteristics:

- Focus on upper quantiles (e.g., 95th, 99th percentile)
- Asymmetric cost: missing a peak is worse than a false alarm
- Asset-specific capacity limits drive thresholds
- Metrics emphasize precision/recall at capacity thresholds

Example configuration
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from datetime import timedelta
   from openstef_beam.workflows import ForecastingWorkflowConfig
   from openstef_beam.metrics import confusion_matrix, precision_recall
   
   # Configure for transformer congestion monitoring
   config = ForecastingWorkflowConfig(
       model_id="transformer_001",
       horizons=[0.25, 1, 6, 24, 47],  # 15min to 47 hours ahead
       quantiles=[0.1, 0.5, 0.9, 0.95, 0.99],  # Include high quantiles
       sample_interval=timedelta(minutes=15),
   )
   
   # Define transformer capacity limit
   transformer_limit = 630.0  # kVA
   
   # Evaluate peak detection performance
   cm = confusion_matrix(
       y_true=actual_load,
       y_pred=forecast_load,
       threshold=transformer_limit,
       threshold_margin=0.05  # 5% margin
   )
   
   pr = precision_recall(cm)
   print(f"Peak detection precision: {pr.precision:.2%}")
   print(f"Peak detection recall: {pr.recall:.2%}")

When to use this
^^^^^^^^^^^^^^^^

- Monitoring individual transformers or cables
- Planning maintenance windows
- Identifying grid reinforcement needs
- Real-time congestion management

See the :doc:`deployment` guide for patterns on running congestion forecasts in production.


Free Space Estimation
---------------------

Free space (or remaining capacity) forecasting predicts how much additional load a grid asset can handle before reaching its limit. This is essential for connecting new customers or distributed energy resources.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Free space is derived by subtracting forecasted load from asset capacity. The focus shifts to understanding both the expected load and its uncertainty—you need probabilistic forecasts to assess connection risks.

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow
   
   # Run probabilistic forecast
   workflow = ForecastingWorkflow(config)
   forecast = workflow.predict(input_data)
   
   # Calculate free space for different confidence levels
   cable_capacity = 400.0  # kVA
   
   # Conservative estimate (95th percentile load)
   conservative_free_space = cable_capacity - forecast.quantile(0.95)
   
   # Expected free space (median load)
   expected_free_space = cable_capacity - forecast.quantile(0.5)
   
   # Optimistic estimate (5th percentile load)
   optimistic_free_space = cable_capacity - forecast.quantile(0.05)
   
   print(f"Available capacity range: "
         f"{optimistic_free_space.min():.1f} - {conservative_free_space.min():.1f} kVA")

When to use this
^^^^^^^^^^^^^^^^

- Evaluating new connection requests
- Planning distributed generation installations
- Assessing grid headroom for electric vehicle charging
- Long-term capacity planning

The quality of free space estimates depends heavily on your capacity limits being accurate. Ensure these are updated as grid topology changes.


Grid Loss Forecasting
---------------------

Grid losses represent energy dissipated as heat in transmission and distribution equipment. Forecasting losses helps optimize grid operations and accurately allocate costs.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Grid losses are typically 2-8% of total load and follow a quadratic relationship with current (losses ∝ I²R). This non-linear behavior requires careful feature engineering.

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflowConfig
   
   # Configure for loss forecasting
   config = ForecastingWorkflowConfig(
       model_id="grid_losses_region_a",
       horizons=[1, 6, 24],
       quantiles=[0.1, 0.5, 0.9],
       # Include squared load features for quadratic relationship
       rolling_aggregate_features=["mean", "max", "std"],
   )
   
   # Prepare input with squared load features
   import pandas as pd
   
   input_data = pd.DataFrame({
       'load': measured_load,
       'load_squared': measured_load ** 2,
       'temperature_2m': temperature,
       # ... other weather features
   })

When to use this
^^^^^^^^^^^^^^^^

- Optimizing grid operations to minimize losses
- Accurate energy accounting and cost allocation
- Identifying inefficient grid segments
- Regulatory reporting

Grid losses are sensitive to network topology. If your grid configuration changes significantly, retrain models with updated data.


Transport Forecasting
---------------------

Transport forecasting predicts energy flow through specific grid connections, such as between transmission and distribution networks or across regional boundaries.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Transport forecasts can be bidirectional—energy may flow in either direction depending on local generation and consumption. This requires models that handle both positive and negative values appropriately.

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow
   import pandas as pd
   
   # Prepare bidirectional transport data
   # Positive = import, Negative = export
   transport_data = pd.DataFrame({
       'transport': measured_transport,  # Can be positive or negative
       'temperature_2m': temperature,
       'wind_speed_80m': wind_speed,
       'solar_radiation': solar_radiation,
   }, index=pd.date_range('2024-01-01', periods=len(measured_transport), freq='15min'))
   
   # Configure workflow
   config = ForecastingWorkflowConfig(
       model_id="transport_region_boundary",
       horizons=[0.25, 1, 6, 24],
       quantiles=[0.1, 0.5, 0.9],
   )
   
   workflow = ForecastingWorkflow(config)
   forecast = workflow.predict(transport_data)

When to use this
^^^^^^^^^^^^^^^^

- Balancing supply and demand across regions
- Planning transmission capacity
- Managing interconnector flows
- Coordinating with neighboring grid operators

Transport forecasts benefit from including renewable generation forecasts as features, especially in regions with high solar or wind penetration.


District Heating Demand
-----------------------

District heating systems distribute thermal energy for space heating and hot water. Demand forecasting helps optimize production and storage.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Heat demand is strongly temperature-dependent with significant thermal inertia—buildings retain heat, creating lag between temperature changes and demand response. This requires careful feature engineering with lagged temperature features.

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflowConfig
   import pandas as pd
   
   # Configure for district heating
   config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_1",
       horizons=[1, 6, 24, 48],  # Longer horizons for production planning
       quantiles=[0.1, 0.5, 0.9],
       temperature_column="temperature_2m",
       # Thermal inertia requires historical context
       rolling_aggregate_features=["mean", "min"],
   )
   
   # Prepare input with temperature lags
   heating_data = pd.DataFrame({
       'heat_demand': measured_demand,
       'temperature_2m': temperature,
       'temperature_lag_24h': temperature.shift(24),
       'temperature_lag_48h': temperature.shift(48),
       'wind_speed_10m': wind_speed,  # Affects building heat loss
   }, index=pd.date_range('2024-01-01', periods=len(measured_demand), freq='1h'))

When to use this
^^^^^^^^^^^^^^^^

- Optimizing combined heat and power (CHP) production
- Managing thermal storage systems
- Planning maintenance during low-demand periods
- Fuel procurement and cost optimization

District heating demand often shows different patterns than electrical load—weekday/weekend differences may be less pronounced, but seasonal variation is typically stronger.


MV Route Congestion with Power Grid Model
------------------------------------------

Medium voltage (MV) route congestion requires understanding how load distributes across the network topology. OpenSTEF can integrate with power-grid-model to account for network physics.

What makes it different
^^^^^^^^^^^^^^^^^^^^^^^

Unlike simple asset-level forecasting, MV route analysis requires:

- Network topology information (how assets connect)
- Power flow calculations to determine cable loading
- Aggregation of multiple load points
- Consideration of distributed generation

This is the most complex use case, requiring external topology data and power flow simulation.

.. code-block:: python

   from openstef_beam.workflows import ForecastingWorkflow
   from power_grid_model import PowerGridModel
   import pandas as pd
   
   # Step 1: Forecast individual substations
   substation_forecasts = {}
   
   for substation_id in mv_route_substations:
       config = ForecastingWorkflowConfig(
           model_id=f"substation_{substation_id}",
           horizons=[0.25, 1, 6, 24],
           quantiles=[0.5, 0.9, 0.95],
       )
       
       workflow = ForecastingWorkflow(config)
       substation_forecasts[substation_id] = workflow.predict(input_data)
   
   # Step 2: Load network topology
   # (This requires power-grid-model setup - see their documentation)
   pgm = PowerGridModel(
       input_data=network_topology,  # Your grid topology data
       system_frequency=50.0
   )
   
   # Step 3: Run power flow for each forecast horizon
   for horizon in [0.25, 1, 6, 24]:
       # Prepare load profile for this horizon
       load_profile = {
           substation_id: forecast.quantile(0.95)[horizon]
           for substation_id, forecast in substation_forecasts.items()
       }
       
       # Calculate power flow
       output = pgm.calculate_power_flow(
           symmetric=True,
           update_data=load_profile
       )
       
       # Extract cable loading
       cable_loading = output['line']['loading']
       
       # Identify congested cables
       congested = cable_loading > 0.8  # 80% threshold
       print(f"Horizon {horizon}h: {congested.sum()} cables above 80% loading")

When to use this
^^^^^^^^^^^^^^^^

- Detailed MV network analysis
- Planning grid reconfigurations
- Assessing impact of large new connections
- Optimizing network switching strategies

This approach requires significant additional setup beyond OpenSTEF. You'll need accurate network topology data and familiarity with power-grid-model. Consider starting with simpler asset-level forecasting before attempting full network analysis.

.. note::

   The power-grid-model integration shown here is illustrative. Actual implementation requires careful coordination between OpenSTEF forecasts and power flow calculations. See the power-grid-model documentation for detailed setup instructions.


Choosing the Right Use Case
----------------------------

Start with these questions:

1. **What decisions will the forecast support?** Operational decisions (congestion management) need different accuracy than planning decisions (capacity expansion).

2. **What's the cost of forecast errors?** Asymmetric costs (missing peaks worse than false alarms) should influence your metric selection and model configuration.

3. **What data is available?** MV route analysis requires topology data; simpler use cases need only load and weather data.

4. **What's your forecasting experience?** Start with congestion or transport forecasting before attempting complex multi-asset network analysis.

For data integration patterns to support these use cases, see :doc:`data_integration`. For production deployment considerations, see :doc:`deployment`.