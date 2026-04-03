Common Use Cases
================

OpenSTEF is designed to forecast energy-related time series across diverse applications. This page describes common use cases, explains what makes each unique, and provides practical configuration examples to help you choose the right approach for your forecasting needs.

Overview
--------

While OpenSTEF's core forecasting engine remains the same across applications, different use cases require different data inputs, feature engineering strategies, and evaluation metrics. The key differences lie in:

- **What you're forecasting**: Load, capacity utilization, losses, or demand
- **Physical constraints**: Capacity limits, bidirectional flow, topology dependencies
- **Feature requirements**: Weather sensitivity, network topology, building characteristics
- **Evaluation priorities**: Peak accuracy, overall RMSE, or capacity violation detection

Congestion Forecasts
--------------------

Congestion forecasting predicts the loading on grid assets like transformers, cables, and substations to identify potential capacity violations before they occur. This is critical for grid operators managing asset utilization and planning maintenance windows.

What makes congestion forecasts unique
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Capacity limits are central**: Each asset has physical limits (upper and/or lower) that define congestion thresholds
- **Peak accuracy matters most**: Missing a peak can mean equipment damage or service interruptions
- **Bidirectional flow**: Some assets (especially with distributed generation) can have both positive and negative loading
- **Asset-specific behavior**: Different transformer types, cable ratings, and cooling systems affect capacity

When to use congestion forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use congestion forecasting when you need to:

- Predict when transformers or cables will approach their rated capacity
- Plan maintenance windows that avoid high-load periods
- Identify assets requiring upgrades or reinforcement
- Optimize switching operations to balance load across the network

Configuration example
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_core.target import Target
   from datetime import datetime

   # Transformer congestion forecast
   transformer_target = Target(
       name="transformer_hvmv_001",
       description="110/10kV transformer at substation Alpha",
       group_name="region_north",
       latitude=52.3702,
       longitude=4.8952,
       limit=25.0,  # MVA rating
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

   # Cable with bidirectional flow
   cable_target = Target(
       name="cable_mv_route_12",
       description="MV cable route with solar generation",
       group_name="region_south",
       latitude=51.9225,
       longitude=4.4792,
       upper_limit=5.0,   # Maximum forward flow (MW)
       lower_limit=-2.0,  # Maximum reverse flow (MW)
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

For congestion forecasts, focus your model evaluation on peak prediction accuracy. Consider using quantile forecasts to estimate the probability of exceeding capacity limits.

Free Space Estimation
---------------------

Free space estimation forecasts the remaining available capacity on grid assets, answering the question: "How much additional load can this asset handle?" This is essential for connection requests, EV charging planning, and distributed generation integration.

What makes free space unique
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Derived metric**: Free space = capacity limit - forecasted load
- **Planning horizon**: Often requires longer forecast horizons (weeks to months) than operational forecasts
- **Worst-case scenarios**: Conservative estimates are preferred to avoid overcommitting capacity
- **Aggregation patterns**: May need to consider simultaneous peaks across multiple assets

When to use free space estimation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use free space forecasting when you need to:

- Evaluate new connection requests for homes, businesses, or EV chargers
- Plan distributed generation (solar, wind) integration capacity
- Assess headroom for demand response programs
- Support long-term capacity planning and investment decisions

Configuration approach
^^^^^^^^^^^^^^^^^^^^^^

Free space estimation uses the same forecasting infrastructure as congestion forecasts but focuses on different quantiles and evaluation metrics:

.. code-block:: python

   from openstef_core.target import Target
   from openstef_models.models.forecasting.gblinear_forecaster import GBLinearForecaster
   from openstef_core.models.forecasting import Q
   
   # Target configuration is identical to congestion forecasting
   substation_target = Target(
       name="substation_042",
       description="Distribution substation for residential area",
       group_name="region_west",
       limit=15.0,  # MVA capacity
       # ... other parameters
   )
   
   # Model configuration emphasizes upper quantiles
   forecaster = GBLinearForecaster(
       horizons=[LeadTime.from_string("PT168H")],  # 7-day horizon
       quantiles=[Q(0.5), Q(0.9), Q(0.95), Q(0.99)],  # Focus on high quantiles
       hyperparams=GBLinearHyperParams(
           n_steps=1000,
           learning_rate=0.3,
       )
   )

For free space estimation, evaluate your forecasts using the 90th or 95th percentile predictions. The remaining capacity is then ``limit - forecast_q95``, providing a conservative estimate that accounts for forecast uncertainty.

Grid Loss Forecasts
-------------------

Grid loss forecasting predicts energy losses in transmission and distribution networks due to resistance heating, transformer core losses, and other inefficiencies. Accurate loss forecasts are essential for energy procurement and system efficiency monitoring.

What makes grid loss forecasts unique
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Quadratic relationship**: Losses scale with the square of current (I²R losses)
- **Temperature dependency**: Conductor and transformer losses vary with ambient temperature
- **Network topology**: Losses depend on power flow patterns across the entire network
- **Small signal in noise**: Losses are often 2-10% of total load, making accurate measurement challenging

When to use grid loss forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use grid loss forecasting when you need to:

- Optimize energy procurement to account for distribution losses
- Monitor network efficiency and identify anomalous loss patterns
- Evaluate the impact of network reconfiguration on losses
- Support regulatory reporting on system efficiency

Configuration considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Grid loss forecasts require careful feature engineering to capture the quadratic relationship with load:

.. code-block:: python

   from openstef_core.target import Target
   from openstef_core.transforms import TransformPipeline, LagTransform
   from openstef_models.preprocessing.transforms import FeatureAdder
   
   # Grid loss target
   loss_target = Target(
       name="grid_losses_region_a",
       description="Total distribution losses for Region A",
       group_name="region_a",
       # No capacity limit for loss forecasts
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )
   
   # Feature engineering for losses
   preprocessing = TransformPipeline(
       transforms=[
           # Add squared load features to capture I²R relationship
           FeatureAdder(
               features={
                   "load_squared": lambda df: df["total_load"] ** 2,
                   "temp_load_interaction": lambda df: df["temperature"] * df["total_load"]
               }
           ),
           LagTransform(lags=[24, 48, 168]),  # Daily and weekly patterns
       ]
   )

Grid loss forecasts benefit from including total network load as a predictor, along with ambient temperature and network topology information.

Transport Forecasts
-------------------

Transport forecasting predicts energy demand for electric vehicle charging infrastructure, public transport systems, and other mobility-related loads. These forecasts exhibit unique temporal patterns driven by commuting behavior and travel patterns.

What makes transport forecasts unique
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Commuting patterns**: Strong weekday/weekend differences and morning/evening peaks
- **Event sensitivity**: Public holidays, school vacations, and major events significantly impact demand
- **Weather impact**: Rain, snow, and extreme temperatures affect travel behavior
- **Rapid growth**: EV adoption means historical patterns may not reflect future demand

When to use transport forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use transport forecasting when you need to:

- Predict EV charging station demand for capacity planning
- Forecast public transport energy requirements for procurement
- Optimize charging schedules for electric bus or truck fleets
- Plan grid reinforcement for transportation electrification

Configuration example
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from openstef_core.target import Target
   from openstef_models.preprocessing.transforms import HolidayFeatureAdder
   from openstef_core.enums import CountryAlpha2
   
   # EV charging station forecast
   ev_target = Target(
       name="ev_charging_hub_central",
       description="Fast charging hub at central station",
       group_name="transport_charging",
       latitude=52.0907,
       longitude=5.1214,
       limit=2.0,  # MW capacity
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2023, 1, 1)  # Shorter history due to rapid growth
   )
   
   # Holiday features are critical for transport
   preprocessing = TransformPipeline(
       transforms=[
           HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
           # Add weekday/weekend indicators
           # Add hour-of-day features
       ]
   )

Transport forecasts require careful handling of holiday effects and may benefit from shorter training windows to emphasize recent demand patterns as EV adoption accelerates.

District Heating Demand
-----------------------

District heating forecasting predicts thermal energy demand for centralized heating systems serving multiple buildings. These forecasts are highly weather-sensitive and exhibit strong seasonal patterns.

What makes district heating unique
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Temperature dominance**: Heating demand is primarily driven by outdoor temperature and wind chill
- **Thermal inertia**: Building thermal mass creates lag between weather changes and demand response
- **Seasonal variation**: Extreme differences between summer (minimal) and winter (peak) demand
- **Base load**: Domestic hot water creates year-round base load independent of heating needs

When to use district heating forecasts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use district heating forecasting when you need to:

- Optimize combined heat and power (CHP) plant operations
- Plan fuel procurement for heating plants
- Forecast heat storage requirements
- Balance supply across multiple heat sources

Configuration considerations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

District heating forecasts require rich weather features and careful handling of temperature lags:

.. code-block:: python

   from openstef_core.target import Target
   from openstef_core.transforms import TransformPipeline
   from openstef_models.preprocessing.transforms import LagTransform, WeatherFeatureAdder
   
   # District heating target
   heating_target = Target(
       name="district_heating_west",
       description="District heating network West sector",
       group_name="heating_networks",
       limit=50.0,  # MW thermal capacity
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2020, 1, 1)  # Longer history for seasonal patterns
   )
   
   # Weather features with lags for thermal inertia
   preprocessing = TransformPipeline(
       transforms=[
           WeatherFeatureAdder(
               features=["temperature", "windspeed", "radiation", "humidity"]
           ),
           # Add temperature lags to capture thermal inertia
           LagTransform(
               columns=["temperature"],
               lags=[1, 2, 3, 6, 12, 24]  # Hours of thermal lag
           ),
       ]
   )

Consider using degree-day features (temperature below heating threshold) as predictors, as these often correlate better with heating demand than raw temperature.

MV Route Congestion with Power Grid Model
------------------------------------------

Medium voltage (MV) route congestion forecasting combines load forecasting with detailed network topology modeling using power-grid-model. This approach enables accurate prediction of cable loading considering network configuration, power flow physics, and distributed generation.

What makes MV route forecasting unique
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Topology awareness**: Cable loading depends on network configuration and switching state
- **Power flow physics**: Requires solving AC or DC power flow equations
- **Multiple inputs**: Aggregates forecasts from multiple substations and generators
- **Dynamic routing**: Load distribution changes with network reconfiguration

When to use topology-aware forecasting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use power-grid-model integration when you need to:

- Forecast cable loading in meshed or ring networks where flow paths vary
- Account for distributed generation impact on power flows
- Evaluate the effect of switching operations on asset loading
- Support advanced distribution management systems (ADMS)

Integration approach
^^^^^^^^^^^^^^^^^^^^

Topology-aware forecasting requires integrating OpenSTEF with power-grid-model:

.. code-block:: python

   from openstef_core.target import Target
   from power_grid_model import PowerGridModel
   import pandas as pd
   
   # Define targets for each substation/generator
   substation_targets = [
       Target(name=f"substation_{i}", ...) 
       for i in range(1, 10)
   ]
   
   # Generate forecasts for each target
   forecasts = {}
   for target in substation_targets:
       # Use standard OpenSTEF forecasting workflow
       forecast = generate_forecast(target)
       forecasts[target.name] = forecast
   
   # Load network topology
   pgm = PowerGridModel(input_data=network_topology)
   
   # Convert forecasts to power flow inputs
   def create_power_flow_input(forecasts, timestamp):
       """Convert load forecasts to power-grid-model input format."""
       return {
           "sym_load": [
               {"id": i, "p_specified": forecasts[f"substation_{i}"].loc[timestamp]}
               for i in range(1, 10)
           ]
       }
   
   # Calculate cable loading for each forecast timestamp
   cable_loading = []
   for timestamp in forecast.index:
       pf_input = create_power_flow_input(forecasts, timestamp)
       pf_result = pgm.calculate_power_flow(update_data=pf_input)
       cable_loading.append(pf_result["line"])  # Extract cable loading
   
   cable_loading_df = pd.DataFrame(cable_loading)

This approach separates load forecasting (OpenSTEF's strength) from power flow calculation (power-grid-model's strength), enabling accurate cable loading predictions that account for network physics.

Choosing the Right Use Case
----------------------------

The table below summarizes key characteristics to help you select the appropriate use case:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Use Case
     - Primary Driver
     - Capacity Limits
     - Forecast Horizon
     - Key Features
   * - Congestion
     - Load patterns
     - Critical
     - Hours to days
     - Weather, lags
   * - Free Space
     - Peak load
     - Critical
     - Days to months
     - High quantiles
   * - Grid Losses
     - Load squared
     - Not applicable
     - Hours to days
     - Load, temperature
   * - Transport
     - Commuting
     - Important
     - Hours to days
     - Holidays, weekday
   * - District Heating
     - Temperature
     - Important
     - Hours to days
     - Weather lags
   * - MV Routes
     - Network topology
     - Critical
     - Hours to days
     - Topology, power flow

Next Steps
----------

- See :doc:`data_integration` for connecting your data sources to OpenSTEF
- See :doc:`deployment` for production deployment patterns
- Consult the API documentation for detailed configuration options