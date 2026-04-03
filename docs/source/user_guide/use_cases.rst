Common Use Cases
================

OpenSTEF supports a variety of energy forecasting use cases, each with distinct requirements and configurations. This page explores the most common applications, explaining when to use each approach and how to configure your forecasting models appropriately.

Overview
--------

While OpenSTEF is a general-purpose forecasting library, certain use cases appear frequently in energy system operations:

- **Congestion forecasting**: Predicting when transformers, cables, or other grid assets approach capacity limits
- **Free space estimation**: Calculating remaining capacity for new connections or load growth
- **Grid loss forecasting**: Estimating energy losses in transmission and distribution networks
- **Transport forecasting**: Predicting energy flows through specific grid routes
- **District heating demand**: Forecasting thermal energy requirements for heating networks
- **MV route congestion**: Analyzing medium-voltage network congestion using detailed topology

Each use case requires different data, features, metrics, and model configurations.

Congestion Forecasting
----------------------

Congestion forecasting predicts when grid assets (transformers, cables, substations) will approach or exceed their capacity limits. This is critical for preventing equipment damage and planning maintenance windows.

Key characteristics
^^^^^^^^^^^^^^^^^^^

- **Focus on peak detection**: Accurately identifying when load exceeds thresholds matters more than overall forecast accuracy
- **Asymmetric costs**: Missing a congestion event (false negative) is typically more costly than a false alarm
- **Capacity limits**: Each asset has a defined ``limit`` that represents its maximum safe operating capacity
- **Time-critical**: Forecasts need sufficient lead time for operators to take preventive action

Configuration approach
^^^^^^^^^^^^^^^^^^^^^^

Define targets with explicit capacity limits:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkTarget
   from datetime import datetime
   
   transformer_target = BenchmarkTarget(
       name="transformer_001",
       description="Primary transformer at substation A",
       group_name="substations",
       latitude=52.0,
       longitude=4.5,
       limit=150.0,  # Maximum capacity in MW
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

Use metrics optimized for peak detection:

.. code-block:: python

   from openstef_beam.metrics import confusion_matrix, precision_recall, fbeta
   
   # Calculate confusion matrix for peak events
   cm = confusion_matrix(
       y_true=actual_load,
       y_pred=forecast_load,
       threshold=transformer_target.limit,
       relative_threshold=0.9  # Flag events above 90% of limit
   )
   
   # Calculate precision and recall
   pr = precision_recall(cm)
   
   # F-beta score with beta > 1 emphasizes recall (catching peaks)
   score = fbeta(pr, beta=2.0)

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Monitoring individual transformers, cables, or substations
- Planning maintenance during low-load periods
- Identifying assets at risk of overload
- Validating capacity upgrade decisions

Free Space Estimation
---------------------

Free space (or remaining capacity) forecasting estimates how much additional load an asset can accommodate before reaching its limit. This is essential for connection planning and grid expansion decisions.

Key characteristics
^^^^^^^^^^^^^^^^^^^

- **Derived metric**: Free space = capacity limit - forecasted load
- **Bidirectional limits**: Some assets have both upper and lower operating limits
- **Probabilistic outputs**: Uncertainty quantification helps assess risk of capacity exceedance
- **Planning horizon**: Often requires longer forecast horizons (days to weeks)

Configuration approach
^^^^^^^^^^^^^^^^^^^^^^

For assets with bidirectional limits:

.. code-block:: python

   cable_target = BenchmarkTarget(
       name="cable_mv_042",
       description="Medium voltage cable segment",
       group_name="mv_cables",
       latitude=52.1,
       longitude=4.6,
       upper_limit=80.0,  # Maximum forward flow in MW
       lower_limit=-20.0,  # Maximum reverse flow in MW
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

Calculate free space from probabilistic forecasts:

.. code-block:: python

   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.hyperparams import GBLinearHyperParams
   from openstef_models.preprocessing.quantile import Q
   from openstef_models.preprocessing.lead_time import LeadTime
   
   # Train model with quantile predictions
   forecaster = GBLinearForecaster(
       horizons=[LeadTime.from_string("PT168H")],  # 7-day horizon
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
       hyperparams=GBLinearHyperParams(
           n_steps=1000,
           learning_rate=0.3
       )
   )
   
   # After prediction, calculate free space
   free_space_p90 = cable_target.upper_limit - forecast_p90
   free_space_p10 = cable_target.upper_limit - forecast_p10

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Evaluating new connection requests
- Planning distributed generation installations
- Assessing grid capacity for electric vehicle charging
- Long-term capacity planning and investment decisions

Grid Loss Forecasting
---------------------

Grid losses represent energy dissipated as heat in transmission and distribution networks. Accurate loss forecasts support energy procurement and help identify inefficient grid segments.

Key characteristics
^^^^^^^^^^^^^^^^^^^

- **Non-linear relationship**: Losses scale roughly with the square of current (I²R losses)
- **Temperature dependent**: Conductor resistance varies with ambient and operating temperature
- **Network-wide aggregation**: Total losses sum across all grid segments
- **Relatively small magnitude**: Losses typically represent 2-8% of total energy flow

Configuration approach
^^^^^^^^^^^^^^^^^^^^^^

Loss forecasting often uses the same infrastructure as load forecasting but with different target variables:

.. code-block:: python

   loss_target = BenchmarkTarget(
       name="grid_losses_region_north",
       description="Total distribution losses in northern region",
       group_name="losses",
       latitude=52.5,
       longitude=5.0,
       limit=None,  # No hard limit for losses
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

Include features that capture non-linear effects:

.. code-block:: python

   from openstef_models.preprocessing.transforms import TransformPipeline, FeatureAdder
   import pandas as pd
   
   # Add squared load features to capture I²R relationship
   def add_squared_features(data: pd.DataFrame) -> pd.DataFrame:
       squared_data = data.copy()
       if "total_load" in data.columns:
           squared_data["total_load_squared"] = data["total_load"] ** 2
       return squared_data

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Energy procurement and balancing
- Identifying high-loss grid segments for upgrade
- Validating network models against measured losses
- Regulatory reporting and loss allocation

Transport Forecasting
---------------------

Transport forecasts predict energy flows through specific grid connections or routes, rather than consumption at endpoints. This is crucial for managing inter-regional transfers and avoiding bottlenecks.

Key characteristics
^^^^^^^^^^^^^^^^^^^

- **Bidirectional flow**: Energy can flow in either direction depending on generation and load
- **Network topology aware**: Flows depend on the entire network state, not just local conditions
- **Multiple constraints**: Both thermal limits and voltage constraints may apply
- **Coordination required**: Transport forecasts often inform multiple operational decisions

Configuration approach
^^^^^^^^^^^^^^^^^^^^^^

Transport targets typically represent interconnections:

.. code-block:: python

   transport_target = BenchmarkTarget(
       name="interconnect_region_a_b",
       description="Energy transport from Region A to Region B",
       group_name="interconnects",
       latitude=52.3,
       longitude=4.8,
       upper_limit=200.0,  # Maximum A→B flow
       lower_limit=-150.0,  # Maximum B→A flow
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Managing inter-regional energy transfers
- Coordinating with neighboring distribution system operators
- Planning network reconfigurations
- Optimizing distributed generation dispatch

District Heating Demand
------------------------

District heating networks distribute thermal energy for space heating and hot water. Demand forecasting helps optimize heat production and storage.

Key characteristics
^^^^^^^^^^^^^^^^^^^

- **Strong temperature dependence**: Heating demand correlates strongly with outdoor temperature
- **Thermal inertia**: Building thermal mass creates lag between weather changes and demand response
- **Seasonal patterns**: Demand varies dramatically between winter and summer
- **Time-of-day effects**: Hot water demand shows different patterns than space heating

Configuration approach
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   heating_target = BenchmarkTarget(
       name="district_heating_downtown",
       description="Thermal demand for downtown district heating network",
       group_name="district_heating",
       latitude=52.0,
       longitude=4.3,
       limit=50.0,  # Maximum thermal capacity in MW
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

Include temperature-related features with appropriate lags:

.. code-block:: python

   from openstef_models.preprocessing.transforms import LagTransform
   
   # Add lagged temperature features to capture thermal inertia
   lag_transform = LagTransform(
       lags=[1, 2, 3, 6, 12, 24],  # Hours
       features=["temperature", "wind_speed"]
   )

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Optimizing combined heat and power (CHP) plant operation
- Managing thermal storage systems
- Planning maintenance during low-demand periods
- Coordinating with electricity system operations

MV Route Congestion with Power Grid Model
------------------------------------------

Medium-voltage (MV) route congestion analysis uses detailed network topology to identify congestion points in complex distribution networks. This requires integration with power flow models.

Key characteristics
^^^^^^^^^^^^^^^^^^^

- **Topology-aware**: Considers network structure, not just individual assets
- **Power flow calculations**: Uses electrical network models to calculate branch flows
- **Multiple contingencies**: Analyzes network behavior under various outage scenarios
- **Detailed asset modeling**: Includes transformer tap positions, voltage levels, and protection settings

Integration approach
^^^^^^^^^^^^^^^^^^^^

OpenSTEF can integrate with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_ for detailed network analysis:

.. code-block:: python

   # This is a conceptual example showing integration patterns
   # Actual implementation depends on your network model structure
   
   from power_grid_model import PowerGridModel
   
   def analyze_mv_route_congestion(forecast_data, network_model):
       """Analyze MV route congestion using power flow calculations.
       
       Args:
           forecast_data: Load forecasts for all nodes in the network
           network_model: PowerGridModel instance with network topology
           
       Returns:
           Dictionary mapping branch IDs to congestion probabilities
       """
       # Run power flow with forecasted loads
       flow_results = network_model.calculate_power_flow(
           symmetric=True,
           update_data=forecast_data
       )
       
       # Identify congested branches
       congestion = {}
       for branch_id, flow in flow_results["branch"].items():
           loading = abs(flow["loading"])
           if loading > 0.8:  # 80% threshold
               congestion[branch_id] = loading
       
       return congestion

When to use this approach
^^^^^^^^^^^^^^^^^^^^^^^^^^

- Detailed distribution network planning
- Analyzing impact of distributed generation
- Evaluating network reconfiguration options
- Identifying critical branches for reinforcement

.. note::

   Integration with power-grid-model requires additional setup and network data. See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for details on network modeling.

Choosing the Right Approach
----------------------------

The table below summarizes key differences between use cases:

=========================  ==================  =================  ===================  ====================
Use Case                   Primary Metric      Capacity Limits    Forecast Horizon     Key Features
=========================  ==================  =================  ===================  ====================
Congestion                 Precision/Recall    Single limit       Hours to days        Peak detection
Free Space                 Quantile coverage   Upper/lower        Days to weeks        Probabilistic
Grid Losses                MAE/RMAE            None               Hours to days        Non-linear features
Transport                  MAE/Directional     Bidirectional      Hours to days        Network flows
District Heating           MAE/Temperature     Single limit       Hours to days        Temperature lags
MV Route (topology)        Branch loading      Per-branch         Hours                Network model
=========================  ==================  =================  ===================  ====================

Next Steps
----------

- Learn about :doc:`deployment` patterns for production systems
- Explore :doc:`data_integration` for connecting to data sources
- Review the API documentation for detailed configuration options