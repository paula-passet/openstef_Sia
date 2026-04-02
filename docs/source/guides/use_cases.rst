Common Use Cases
================

OpenSTEF is a Python machine learning library designed for short-term energy forecasting across diverse operational scenarios. This page helps you identify which use case matches your needs and understand the key differences between approaches.

All use cases share the same core workflow—train a model, create forecasts, evaluate results—but differ in what you're forecasting, which features matter most, and how you interpret the results.

Overview of Use Cases
---------------------

OpenSTEF supports six primary use cases in energy system operations:

- **Congestion Management**: Forecast peak loads on substations to prevent grid overload
- **Free Space Estimation**: Predict available capacity for new connections
- **Grid Loss Forecasting**: Estimate energy losses in transmission and distribution
- **Transport Forecasting**: Predict energy flow through specific grid segments
- **District Heating**: Forecast heat demand in district heating networks
- **MV Route Congestion with Topology**: Advanced congestion management using network topology models

Each use case uses the same OpenSTEF library but with different data inputs, feature engineering, and evaluation priorities.

Congestion Management
---------------------

Forecast peak loads on substations, transformers, or cables to identify when equipment approaches its rated capacity. This is the most common OpenSTEF use case.

**What you're forecasting**: Total electrical load (MW or kW) at specific grid assets

**Key characteristics**:

- Focus on peak detection accuracy—missing a congestion event is costly
- Requires probabilistic forecasts to quantify risk (e.g., 90th percentile predictions)
- Weather dependency is high, especially temperature for heating/cooling loads
- Typical forecast horizons: 24-48 hours ahead

**When to use this approach**:

Use congestion management when you need to prevent equipment overload, plan maintenance windows, or defer grid investments by optimizing existing capacity.

**Example configuration**:

.. code-block:: python

   from openstef_beam import StandardForecastingSolution
   from openstef_core.types import Quantile as Q, LeadTime
   
   # Optimized for peak detection
   solution = StandardForecastingSolution.for_congestion_management()
   
   # Or configure manually with emphasis on high quantiles
   solution = StandardForecastingSolution(
       model_type="xgb",
       quantiles=[Q(0.5), Q(0.9), Q(0.95)],  # Focus on upper quantiles
       horizons=[LeadTime.from_string("PT47H")],
       feature_engineering_config={
           "add_weather_features": True,
           "add_temporal_features": True,
       }
   )

**Evaluation priorities**: Precision and recall for peak detection, F-beta score with emphasis on recall to avoid missing congestion events.

Free Space Estimation
---------------------

Predict available capacity for connecting new customers or distributed energy resources. This is the inverse of congestion forecasting—you're estimating how much headroom remains.

**What you're forecasting**: Available capacity (difference between rated limit and predicted load)

**Key characteristics**:

- Uses the same models as congestion management but interprets results differently
- Requires accurate upper quantile predictions (e.g., 95th percentile)
- Often combined with growth scenarios for long-term planning
- Must account for N-1 security constraints in critical infrastructure

**When to use this approach**:

Use free space estimation when evaluating connection requests, planning distributed generation integration, or optimizing asset utilization.

**Example workflow**:

.. code-block:: python

   from openstef_beam import StandardForecastingSolution
   from openstef_core.types import Quantile as Q
   
   # Train model for load forecasting
   solution = StandardForecastingSolution(
       model_type="lgbm",
       quantiles=[Q(0.5), Q(0.9), Q(0.95)],
   )
   
   trained_model = solution.train(measurements, predictors)
   forecast = solution.predict(trained_model, future_predictors)
   
   # Calculate free space from forecasted load
   asset_limit = 10.0  # MW
   predicted_peak = forecast.data["q_0.95"].max()
   free_space = asset_limit - predicted_peak
   
   print(f"Available capacity: {free_space:.2f} MW")

**Evaluation priorities**: Conservative estimates are safer—overestimating load (underestimating free space) prevents overloading when new connections are added.

Grid Loss Forecasting
---------------------

Estimate energy losses in transmission and distribution networks. Losses depend on load levels, network topology, and operating conditions.

**What you're forecasting**: Energy losses (MWh) over a forecast period, typically as a percentage of total throughput

**Key characteristics**:

- Losses are proportional to current squared (I²R losses), creating nonlinear relationships
- Lower absolute values than load forecasting—requires careful feature scaling
- Weather dependency is indirect (through load dependency)
- Often aggregated to daily or weekly totals for reporting

**When to use this approach**:

Use grid loss forecasting for energy balancing, settlement calculations, or identifying inefficient network segments.

**Example configuration**:

.. code-block:: python

   from openstef_beam import StandardForecastingSolution
   from openstef_core.types import Quantile as Q, LeadTime
   
   # Configure for loss forecasting
   solution = StandardForecastingSolution(
       model_type="lgbm",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],  # Symmetric quantiles
       horizons=[LeadTime.from_string("PT24H")],
   )
   
   # Train on historical loss data
   # Measurements should contain actual measured losses
   trained_model = solution.train(loss_measurements, predictors)

**Evaluation priorities**: Mean Absolute Error (MAE) and R² for overall accuracy. Losses are typically small percentages, so relative metrics (rMAE) are more interpretable than absolute errors.

Transport Forecasting
---------------------

Predict energy flow through specific grid segments like cables, lines, or interconnections between regions. Similar to congestion management but focuses on flow rather than load.

**What you're forecasting**: Power flow (MW) through a specific asset, which can be bidirectional

**Key characteristics**:

- May require handling negative values (reverse flow from distributed generation)
- Flow patterns depend on both supply and demand in connected regions
- Critical for interconnector management and cross-border trading
- Often requires multiple forecasts (one per direction or per connected region)

**When to use this approach**:

Use transport forecasting when managing interconnections, optimizing power flow, or coordinating between grid operators.

**Example workflow**:

.. code-block:: python

   from openstef_beam import StandardForecastingSolution
   from openstef_core.types import Quantile as Q
   
   # Standard configuration works for transport forecasting
   solution = StandardForecastingSolution(
       model_type="xgb",
       quantiles=[Q(0.1), Q(0.5), Q(0.9)],
   )
   
   # Measurements contain historical flow data (can be negative)
   trained_model = solution.train(flow_measurements, predictors)
   
   # Forecast includes uncertainty in both directions
   forecast = solution.predict(trained_model, future_predictors)

**Evaluation priorities**: Accuracy across the full range of flow values, not just peaks. Symmetric quantile coverage (both upper and lower bounds) is important for bidirectional flow.

District Heating
----------------

Forecast heat demand in district heating networks. Heat demand has different patterns than electrical load, with stronger temperature dependency and slower dynamics.

**What you're forecasting**: Heat demand (MW thermal) or energy consumption (MWh) for district heating systems

**Key characteristics**:

- Very strong correlation with outdoor temperature (heating degree days)
- Thermal inertia creates lag effects—buildings respond slowly to temperature changes
- Seasonal patterns are more pronounced than in electrical systems
- Lower variability than electrical load (no instantaneous switching)

**When to use this approach**:

Use district heating forecasts for heat production planning, fuel procurement, or combined heat and power (CHP) optimization.

**Example configuration**:

.. code-block:: python

   from openstef_beam import StandardForecastingSolution
   from openstef_core.types import Quantile as Q, LeadTime
   
   # Configure with emphasis on temperature features
   solution = StandardForecastingSolution(
       model_type="lgbm",
       quantiles=[Q(0.5), Q(0.9)],
       horizons=[LeadTime.from_string("PT48H")],
       feature_engineering_config={
           "add_weather_features": True,
           "temperature_lags": [1, 2, 3, 6, 12, 24],  # Longer lags for thermal inertia
       }
   )

**Evaluation priorities**: Accuracy during extreme cold periods when production capacity is constrained. Temperature forecasts are the dominant uncertainty source.

MV Route Congestion Management with Topology
---------------------------------------------

Advanced congestion management that incorporates network topology using power grid models. This approach uses detailed network models to simulate power flow and identify congestion points more accurately.

**What you're forecasting**: Load at multiple points in a medium-voltage network, combined with power flow calculations

**Key characteristics**:

- Integrates with power-grid-model (PGM) for topology-aware analysis
- Accounts for network configuration, impedances, and voltage constraints
- Can identify congestion caused by network topology, not just load magnitude
- Requires detailed network data (node locations, cable types, impedances)
- Computationally more intensive than simple load forecasting

**When to use this approach**:

Use topology-aware forecasting when network configuration significantly affects congestion, when you need voltage analysis alongside load forecasts, or when planning network reconfigurations.

**Example workflow**:

.. code-block:: python

   from openstef_beam import StandardForecastingSolution
   from openstef_core.types import Quantile as Q
   import power_grid_model as pgm
   
   # Step 1: Create load forecasts for each node
   solution = StandardForecastingSolution(
       model_type="xgb",
       quantiles=[Q(0.5), Q(0.9)],
   )
   
   # Train models for multiple network nodes
   node_forecasts = {}
   for node_id, node_data in network_nodes.items():
       model = solution.train(node_data.measurements, node_data.predictors)
       node_forecasts[node_id] = solution.predict(model, future_predictors)
   
   # Step 2: Use power-grid-model for power flow analysis
   # Define network topology
   grid_model = pgm.PowerGridModel(
       input_data={
           "node": node_data,
           "line": line_data,
           "sym_load": load_data,
       }
   )
   
   # Run power flow with forecasted loads
   for timestamp in forecast_horizon:
       # Update loads with forecasted values
       update_data = {
           "sym_load": [
               {"id": node_id, "p_specified": forecast.data.loc[timestamp, "q_0.9"]}
               for node_id, forecast in node_forecasts.items()
           ]
       }
       
       # Calculate power flow
       results = grid_model.calculate_power_flow(update_data=update_data)
       
       # Identify congested lines
       congested_lines = results["line"][results["line"]["loading"] > 1.0]

**Evaluation priorities**: Accuracy of both load forecasts and power flow calculations. Validation requires comparing predicted line loadings against measured values, not just node loads.

.. note::

   Topology-aware forecasting requires additional setup beyond OpenSTEF. You'll need network data in power-grid-model format and integration code to combine forecasts with power flow calculations. See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for details.

Choosing the Right Use Case
----------------------------

The decision tree for selecting a use case:

1. **Are you forecasting electrical load or heat demand?**
   
   - Heat demand → District Heating
   - Electrical load → Continue to step 2

2. **Do you need detailed network topology analysis?**
   
   - Yes, with voltage/power flow → MV Route Congestion with Topology
   - No, asset-level forecasts sufficient → Continue to step 3

3. **What is your primary operational question?**
   
   - Will equipment overload? → Congestion Management
   - How much capacity is available? → Free Space Estimation
   - What are network losses? → Grid Loss Forecasting
   - What is flow through a connection? → Transport Forecasting

All use cases use the same OpenSTEF library and workflow. The main differences are in the target variable, feature importance, and how you interpret results for operational decisions.

Common Patterns Across Use Cases
---------------------------------

Despite their differences, all use cases share common implementation patterns:

**Data requirements**: All use cases need historical measurements with timestamps, weather data (temperature, radiation, wind speed), and temporal features (hour, day of week, holidays).

**Model selection**: LightGBM (``lgbm``) and XGBoost (``xgb``) work well for most use cases. Linear models (``lgbmlinear``) are faster but less accurate for complex patterns.

**Quantile forecasting**: Probabilistic forecasts with multiple quantiles provide uncertainty estimates essential for operational decision-making.

**Feature engineering**: Weather features, lag features, and temporal patterns are important across all use cases. The relative importance varies by use case.

**Evaluation**: Use domain-specific metrics—peak detection for congestion, relative errors for losses, symmetric quantiles for bidirectional flow.

Next Steps
----------

- **Quick start**: See :doc:`/getting_started/quickstart` for a minimal working example
- **Detailed tutorial**: Follow :doc:`/getting_started/tutorials` for comprehensive guidance
- **Deployment**: Check :doc:`/guides/how_to_guides` for production deployment patterns
- **Concepts**: Read :doc:`/reference/concepts` to understand forecasting fundamentals