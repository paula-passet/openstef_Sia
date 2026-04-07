Common Use Cases
================

OpenSTEF supports a variety of energy forecasting use cases, each with specific characteristics and configuration requirements. This page describes the most common applications, what makes them different, and how to configure OpenSTEF for each scenario.

Overview
--------

While OpenSTEF is a general-purpose forecasting library, certain use cases appear frequently in energy system operations:

- **Congestion forecasts**: Predicting transformer or cable loading to prevent overloads
- **Free space estimation**: Calculating remaining capacity for new connections
- **Grid loss forecasts**: Estimating transmission and distribution losses
- **Transport forecasts**: Predicting energy flows through the network
- **District heating demand**: Forecasting thermal energy requirements
- **MV route congestion**: Medium voltage route analysis with topology awareness

Each use case requires different data, features, and evaluation metrics. Understanding these differences helps you configure OpenSTEF appropriately for your specific needs.

Congestion Forecasts
--------------------

Congestion forecasting predicts when transformers, cables, or other grid assets will approach or exceed their rated capacity. This is critical for grid operators who need to prevent equipment damage and service interruptions.

**What makes it different**: Congestion forecasts prioritize peak detection accuracy over overall error metrics. Missing a peak can lead to equipment failure, while slightly overestimating load is acceptable from a safety perspective.

**Key characteristics**:

- Focus on short-term horizons (1-48 hours ahead)
- Asymmetric error costs (underestimation is worse than overestimation)
- Need for quantile forecasts to capture uncertainty
- Asset capacity limits are critical metadata

**Example configuration**:

.. code-block:: python

   from openstef_beam.benchmarking import BenchmarkTarget
   from datetime import datetime

   transformer_target = BenchmarkTarget(
       name="transformer_001",
       description="Primary distribution transformer at substation A",
       group_name="distribution_transformers",
       latitude=52.0123,
       longitude=4.3456,
       limit=630.0,  # kVA capacity rating
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

For congestion management, configure your evaluation to emphasize peak performance:

.. code-block:: python

   from openstef_beam.analysis import AnalysisConfig
   
   congestion_analysis = AnalysisConfig(
       metrics=[
           "rmse",
           "mae", 
           "peak_mae",  # Mean absolute error during peak hours
           "quantile_score"  # For probabilistic forecasts
       ],
       focus_on_peaks=True,
       peak_threshold=0.8  # 80% of capacity
   )

**Recommended features**: Historical load patterns, weather (temperature, solar radiation), calendar features (weekday/weekend, holidays), and lag features at weekly intervals to capture periodic patterns.

Free Space Estimation
---------------------

Free space forecasting calculates remaining capacity available for new connections or increased consumption. Grid operators use this to approve new customer connections and plan grid expansions.

**What makes it different**: Free space is derived from congestion forecasts but requires both upper and lower bounds. You're forecasting the gap between predicted load and asset limits, often with different limits for import and export.

**Key characteristics**:

- Requires bidirectional capacity limits (upper and lower)
- Often aggregated across multiple assets
- Longer planning horizons (days to weeks)
- Conservative estimates preferred (safety margin)

**Example configuration**:

.. code-block:: python

   cable_target = BenchmarkTarget(
       name="cable_mv_route_12",
       description="MV cable connecting substations B and C",
       group_name="mv_cables",
       latitude=52.0234,
       longitude=4.3567,
       upper_limit=500.0,  # kW import capacity
       lower_limit=-400.0,  # kW export capacity (negative)
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

When forecasting for free space, you typically predict the load and then calculate available capacity:

.. code-block:: python

   # After generating forecasts
   free_space_import = cable_target.upper_limit - predicted_load
   free_space_export = predicted_load - cable_target.lower_limit

**Recommended features**: Similar to congestion forecasts, but consider adding longer-term weather forecasts and seasonal trends for planning horizons beyond 48 hours.

Grid Loss Forecasts
-------------------

Grid losses represent energy dissipated as heat in transmission and distribution equipment. Forecasting losses helps operators optimize dispatch and accurately account for energy balance.

**What makes it different**: Losses are typically a function of load squared (I²R losses), making them nonlinear. They're often calculated as the difference between measured input and output rather than directly measured.

**Key characteristics**:

- Nonlinear relationship with load
- Smaller magnitude than load forecasts
- May require physics-based features
- Accuracy requirements often lower than load forecasts

**Example approach**:

.. code-block:: python

   loss_target = BenchmarkTarget(
       name="grid_losses_region_north",
       description="Total distribution losses in northern region",
       group_name="losses",
       latitude=52.5,
       longitude=4.8,
       limit=None,  # No capacity limit for losses
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

For loss forecasting, consider engineering features that capture the quadratic relationship:

.. code-block:: python

   # In your data provider's get_predictors_for_target method
   def get_predictors_for_target(self, target):
       base_predictors = self.load_weather_data(target)
       
       # Add squared load features if historical load is available
       if "total_load" in base_predictors.columns:
           base_predictors["load_squared"] = base_predictors["total_load"] ** 2
       
       return base_predictors

**Recommended features**: Total system load, load squared, ambient temperature (affects conductor resistance), and time-of-day patterns.

Transport Forecasts
-------------------

Transport forecasting predicts energy flows between grid nodes, such as power flowing through interconnections or between voltage levels. This differs from load forecasting because transport can be bidirectional.

**Key characteristics**:

- Bidirectional flows (positive and negative values)
- Depends on load distribution across multiple nodes
- May require topology information
- Often more volatile than aggregate load

**Example configuration**:

.. code-block:: python

   transport_target = BenchmarkTarget(
       name="transport_hv_mv_station_5",
       description="Power flow from HV to MV at station 5",
       group_name="hv_mv_transport",
       latitude=52.1,
       longitude=4.4,
       upper_limit=2000.0,  # kW forward capacity
       lower_limit=-1500.0,  # kW reverse capacity
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

**Recommended features**: Upstream and downstream load measurements, distributed generation (solar/wind) in the area, and weather features that affect local generation.

District Heating Demand
-----------------------

District heating systems distribute thermal energy for space heating and hot water. Demand patterns differ significantly from electrical load.

**What makes it different**: Heating demand is heavily weather-dependent with significant thermal inertia. Temperature changes affect demand with a lag as buildings heat up or cool down.

**Key characteristics**:

- Strong correlation with outdoor temperature
- Thermal inertia creates lagged responses
- Seasonal patterns more pronounced than daily
- Wind speed affects heat loss from buildings

**Example configuration**:

.. code-block:: python

   heating_target = BenchmarkTarget(
       name="district_heating_zone_west",
       description="Thermal demand for western district heating zone",
       group_name="district_heating",
       latitude=52.2,
       longitude=4.5,
       limit=50.0,  # MW thermal capacity
       benchmark_start=datetime(2024, 1, 1),
       benchmark_end=datetime(2024, 3, 1),
       train_start=datetime(2022, 1, 1)
   )

**Recommended features**: Outdoor temperature, wind speed, solar radiation, temperature lags (6-24 hours), and building occupancy patterns. Consider degree-day features that accumulate temperature effects over time.

MV Route Congestion with Topology
----------------------------------

Medium voltage (MV) route forecasting incorporates network topology to understand how load flows through specific cables and transformers. This is the most sophisticated use case, requiring integration with power system models.

**What makes it different**: Instead of forecasting individual assets in isolation, topology-aware forecasting considers how loads aggregate and flow through the network structure.

**Key characteristics**:

- Requires power-grid-model or similar topology library
- Forecasts multiple interconnected assets simultaneously
- Accounts for switching states and network configuration
- Enables "what-if" analysis for grid planning

**Integration approach**:

While OpenSTEF focuses on time series forecasting, you can integrate topology information through custom data providers:

.. code-block:: python

   from openstef_beam.data import BaseDataProvider
   import power_grid_model as pgm
   
   class TopologyAwareDataProvider(BaseDataProvider):
       def __init__(self, grid_model_path, data_path):
           self.grid_model = self.load_grid_model(grid_model_path)
           self.data_path = data_path
       
       def load_grid_model(self, path):
           # Load power-grid-model topology
           return pgm.PowerGridModel.from_json(path)
       
       def get_targets(self):
           # Create targets for each cable/transformer in topology
           targets = []
           for asset in self.grid_model.get_assets():
               if asset.type in ["cable", "transformer"]:
                   targets.append(BenchmarkTarget(
                       name=asset.id,
                       description=f"{asset.type} {asset.name}",
                       group_name=f"mv_{asset.type}s",
                       latitude=asset.latitude,
                       longitude=asset.longitude,
                       limit=asset.rated_capacity,
                       benchmark_start=datetime(2024, 1, 1),
                       benchmark_end=datetime(2024, 3, 1),
                       train_start=datetime(2022, 1, 1)
                   ))
           return targets
       
       def get_predictors_for_target(self, target):
           # Include topology-derived features
           base_features = self.load_weather_data(target)
           
           # Add upstream/downstream load aggregations
           connected_loads = self.grid_model.get_connected_loads(target.name)
           for load_id in connected_loads:
               load_data = self.load_historical_load(load_id)
               base_features[f"upstream_load_{load_id}"] = load_data
           
           return base_features

This approach allows you to forecast individual assets while leveraging network structure to create better features.

Choosing the Right Configuration
---------------------------------

When implementing a use case, consider these factors:

**Forecast horizon**: Congestion and transport forecasts typically need 1-48 hours. Free space estimation may extend to weeks. District heating benefits from longer horizons due to thermal inertia.

**Error tolerance**: Congestion management requires high accuracy at peaks. Grid losses can tolerate more error. Free space estimates should be conservative.

**Data requirements**: All use cases need historical measurements and weather data. Topology-aware forecasting additionally requires network models. District heating needs detailed temperature and wind data.

**Evaluation metrics**: Choose metrics that align with operational needs. For congestion, emphasize peak performance and quantile scores. For losses, overall RMSE may suffice.

Next Steps
----------

- See :doc:`data_integration` for connecting your data sources
- Review :doc:`deployment` for production deployment patterns
- Check :doc:`logging` for monitoring forecast quality in production