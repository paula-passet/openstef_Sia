Common Use Cases
================

OpenSTEF supports a wide range of energy forecasting applications, each with distinct characteristics and requirements. This page describes the most common use cases, what makes them different, and how to configure OpenSTEF for each scenario.

Understanding these use cases helps you choose the right metrics, model configurations, and evaluation strategies for your specific forecasting problem.

Congestion Management Forecasts
--------------------------------

Congestion management is OpenSTEF's original use case and remains one of the most critical applications for grid operators. The goal is to predict peak load moments at specific grid locations to prevent overloading of transformers, cables, and other infrastructure.

**What makes it different:**

- **Peak-focused accuracy**: Performance during peak periods matters far more than average accuracy
- **Highly variable aggregation**: Ranges from highly aggregated substations to individual customers with unpredictable behavior
- **Asymmetric costs**: Missing a peak (false negative) is typically more costly than a false alarm

**Typical applications:**

- Substation load forecasting
- Transformer and cable loading predictions
- Medium-voltage substations (MSRs)
- Individual customer forecasts for large consumers

**Key metrics:**

- Effective precision and recall at peak thresholds
- rMAE@50th quantile specifically at peak moments
- rCRPS (ranked Continuous Ranked Probability Score) for uncertainty quantification

**Example configuration:**

.. code-block:: python

   from openstef_core.types import Quantile as Q, LeadTime
   from openstef_models.models.forecasting import GBLinearForecaster
   from openstef_models.models.forecasting.hyperparams import GBLinearHyperParams
   from openstef_models.models.forecasting_model import ForecastingModel
   from openstef_models.preprocessing import TransformPipeline, Scaler, FeatureSelection
   
   # Congestion forecasts need high quantiles for peak detection
   model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(
                   method="standard",
                   selection=FeatureSelection(include={"temperature", "radiation", "wind"})
               ),
           ]
       ),
       forecaster=GBLinearForecaster(
           horizons=[LeadTime.from_string("PT36H")],
           # Focus on high quantiles for peak detection
           quantiles=[Q(0.5), Q(0.75), Q(0.9), Q(0.95)],
           hyperparams=GBLinearHyperParams(
               n_steps=1000,
               learning_rate=0.3,
           ),
       ),
       target_column="load",
       tags={"use_case": "congestion", "location": "substation_123"},
   )

When evaluating congestion forecasts, focus your metrics on peak periods rather than overall performance. Consider using custom evaluation windows that isolate high-load scenarios.

Free Space Estimation
---------------------

Free space estimation calculates the remaining capacity available at a grid location—the difference between the maximum safe load and the forecasted load. This is essential for connecting new customers or approving capacity increases.

**What makes it different:**

- **Capacity-oriented**: Focuses on the gap between forecast and maximum threshold
- **Conservative bias**: Underestimating available capacity is safer than overestimating
- **Combines forecasting with planning**: Requires both prediction and threshold management

**Business context:**

Grid operators use free space estimates to make connection decisions. When a customer requests a new connection or capacity increase, the operator needs to know if the grid can handle the additional load without risking congestion.

**Key considerations:**

- Use high quantile predictions (e.g., 90th or 95th percentile) rather than median forecasts
- Account for seasonal variations in available capacity
- Consider both short-term and long-term capacity planning horizons

**Example calculation:**

.. code-block:: python

   import pandas as pd
   
   # After generating forecasts with your model
   forecasts = model.predict(input_data)
   
   # Calculate free space using 90th percentile forecast
   max_capacity = 1000.0  # kW, from grid specifications
   safety_margin = 0.9  # Use 90% of max capacity
   
   free_space = (max_capacity * safety_margin) - forecasts["quantile_0.9"]
   
   # Flag periods with insufficient capacity
   capacity_available = free_space > 0
   
   print(f"Minimum free space: {free_space.min():.1f} kW")
   print(f"Periods with available capacity: {capacity_available.sum()} / {len(capacity_available)}")

Transport Forecasts
-------------------

Transport forecasts predict energy flows between different grid levels, enabling coordination between network operators. These forecasts require balanced accuracy across all time periods, not just peaks.

**What makes it different:**

- **Bidirectional communication**: Grid operators both provide and receive transport forecasts
- **Medium aggregation**: More predictable than individual customers, less aggregated than system-wide
- **Contractual obligations**: Often part of formal agreements between operators
- **Component splitting**: May require separate forecasts for solar, wind, and other sources

**Business context:**

For example, a distribution system operator (DSO) like Alliander provides transport forecasts to the transmission system operator (TSO) TenneT, while receiving forecasts from downstream customers. This enables coordinated grid management and capacity planning across the entire network.

**Key metrics:**

- rMAE (relative Mean Absolute Error) across all periods
- Balanced performance without peak-specific weighting

**Example configuration:**

.. code-block:: python

   from openstef_models.models.forecasting import LGBMForecaster
   from openstef_models.models.forecasting.hyperparams import LGBMHyperParams
   
   # Transport forecasts emphasize overall accuracy
   transport_model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               Scaler(method="standard"),
           ]
       ),
       forecaster=LGBMForecaster(
           horizons=[LeadTime.from_string("PT24H")],
           # Symmetric quantiles for balanced uncertainty
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=LGBMHyperParams(
               num_leaves=31,
               learning_rate=0.1,
               n_estimators=100,
           ),
       ),
       target_column="transport_load",
       tags={"use_case": "transport", "operator": "upstream"},
   )

For component-split forecasts (solar, wind, other), train separate models for each component and aggregate the results.

Grid Loss Forecasts
--------------------

Grid losses represent energy dissipated as heat during transmission and distribution. Accurate loss forecasts enable financial optimization by helping operators purchase the right amount of energy at the right time.

**What makes it different:**

- **Highly aggregated**: System-level patterns dominate individual variations
- **Temporal patterns**: Weather has less impact; cyclic and seasonal patterns are stronger
- **Cost-weighted errors**: Mistakes during high-price periods are more expensive
- **Financial optimization**: Used for market operations and energy procurement

**Business context:**

Grid operators must purchase energy to compensate for losses. Since energy prices fluctuate significantly, forecasting errors during high-price periods have disproportionate financial impact.

**Key metrics:**

- rMAE for overall accuracy
- Total error cost weighted by real-time market prices
- Performance during high-price periods

**Example configuration:**

.. code-block:: python

   from openstef_models.preprocessing import HolidayFeatureAdder
   from openstef_core.types import CountryAlpha2
   
   # Grid loss forecasts rely heavily on temporal patterns
   loss_model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               # Holiday patterns affect system-wide behavior
               HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
               Scaler(method="standard"),
           ]
       ),
       forecaster=GBLinearForecaster(
           horizons=[LeadTime.from_string("PT48H")],
           quantiles=[Q(0.5)],  # Median forecast for cost optimization
           hyperparams=GBLinearHyperParams(
               n_steps=1500,
               learning_rate=0.2,
           ),
       ),
       target_column="grid_losses",
       tags={"use_case": "losses", "optimization": "cost"},
   )

When evaluating grid loss forecasts, consider weighting errors by historical or forecasted energy prices to measure financial impact rather than just statistical accuracy.

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion forecasting combines load prediction with grid topology information to identify bottlenecks in the distribution network. This advanced use case integrates OpenSTEF with power-grid-model for topology-aware forecasting.

**What makes it different:**

- **Topology-aware**: Considers network structure and power flow paths
- **Multiple constraints**: Must respect both thermal limits and voltage constraints
- **Dynamic routing**: Power flows change based on switching states
- **Integration complexity**: Requires combining forecasting with power flow calculations

**Business context:**

MV routes connect multiple substations and customers. A congestion point anywhere along the route affects all downstream customers. Topology-aware forecasting helps operators identify which specific network segments will experience congestion.

**Key considerations:**

- Forecast loads at multiple points along the route
- Use power-grid-model to calculate flows through each network segment
- Account for different switching configurations
- Consider both normal operation and contingency scenarios

.. note::
   
   Detailed integration examples with power-grid-model are beyond the scope of this page. This use case typically requires custom workflow development combining OpenSTEF forecasts with power flow analysis.

**Conceptual workflow:**

.. code-block:: python

   # Conceptual example - actual implementation requires power-grid-model integration
   
   # Step 1: Generate forecasts for all relevant grid points
   forecasts = {}
   for location in mv_route_locations:
       forecasts[location] = model.predict(input_data[location])
   
   # Step 2: Use power-grid-model to calculate flows (pseudo-code)
   # grid_model = create_power_grid_model(topology_data)
   # flows = grid_model.calculate_power_flow(forecasts)
   
   # Step 3: Identify congestion points
   # congested_segments = flows[flows > thermal_limits]

District Heating Demand
-----------------------

District heating is a community use case demonstrating OpenSTEF's applicability beyond electricity grids. The library's flexible design supports thermal energy forecasting with similar patterns and techniques.

**What makes it different:**

- **Non-electrical**: Thermal energy demand instead of electrical load
- **Temperature-sensitive**: Strong correlation with ambient temperature
- **Thermal inertia**: Buildings retain heat, creating lag effects
- **Different seasonality**: Heating demand peaks in winter, opposite to cooling-driven electrical peaks

**Key considerations:**

- Temperature is the dominant predictor
- Consider lag features to capture thermal inertia
- Seasonal patterns are inverted compared to cooling-dominated electrical loads
- Building characteristics affect demand patterns

**Example configuration:**

.. code-block:: python

   from openstef_models.preprocessing import LagFeatureAdder
   
   # District heating model emphasizes temperature and thermal lag
   heating_model = ForecastingModel(
       preprocessing=TransformPipeline(
           transforms=[
               # Add lagged temperature to capture thermal inertia
               LagFeatureAdder(
                   selection=FeatureSelection(include={"temperature"}),
                   lags=[1, 6, 12, 24],  # Hours
               ),
               Scaler(method="standard"),
           ]
       ),
       forecaster=LGBMForecaster(
           horizons=[LeadTime.from_string("PT24H")],
           quantiles=[Q(0.1), Q(0.5), Q(0.9)],
           hyperparams=LGBMHyperParams(
               num_leaves=31,
               learning_rate=0.1,
           ),
       ),
       target_column="heat_demand",
       tags={"use_case": "district_heating", "energy_type": "thermal"},
   )

Choosing the Right Use Case Configuration
------------------------------------------

When configuring OpenSTEF for your use case, consider:

1. **Aggregation level**: Individual customers are less predictable than aggregated loads
2. **What matters most**: Peak accuracy, overall accuracy, or cost-weighted performance
3. **Quantile selection**: High quantiles for conservative estimates, symmetric quantiles for balanced uncertainty
4. **Evaluation metrics**: Choose metrics that align with business objectives
5. **Feature engineering**: Weather features matter more at lower aggregation levels

For data integration patterns and deployment strategies, see :doc:`data_integration` and :doc:`deployment`.