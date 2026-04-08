Common OpenSTEF Use Cases
=========================

OpenSTEF is a flexible forecasting library designed to support diverse energy forecasting applications. This page describes common use cases, their unique characteristics, and how to configure OpenSTEF for each scenario. Understanding these patterns helps you choose the right approach and optimize your forecasting pipeline for your specific needs.

Congestion Management Forecasts
--------------------------------

Congestion management is OpenSTEF's original use case and remains one of its most critical applications. Grid operators need accurate predictions at potential congestion points—transformers, cables, and substations—to prevent overloads and implement mitigation strategies.

**When to use:** Forecasting load at individual substations, transformers, medium-voltage routes (MSRs), or even individual customer connections where grid capacity constraints exist.

**Key characteristics:**

- **Focus on peak accuracy:** The most important moments are near maximum load, not average conditions
- **Highly variable aggregation:** From very aggregated points (entire substations) to low-aggregation scenarios (individual customers with unpredictable behavior)
- **Peak detection emphasis:** Models must reliably identify when congestion will occur, not just predict average load

**Optimization approach:**

Congestion forecasts prioritize accuracy at high quantiles and peak periods. Key metrics include:

- Effective precision and recall for peak detection
- rMAE@50th quantile specifically at peaks
- rCRPS (ranked Continuous Ranked Probability Score) for probabilistic forecasts

The challenge increases dramatically at lower aggregation levels. Individual customer forecasts are particularly unpredictable due to behavioral variability—a single household's load pattern is far less stable than an aggregated substation serving hundreds of customers.

**Configuration considerations:**

- Use quantile-based models or probabilistic forecasting to capture uncertainty at peaks
- Consider separate models for peak vs. off-peak periods if accuracy requirements differ significantly
- For low-aggregation points, evaluate whether forecasting is viable or if alternative strategies (e.g., direct measurement with fast response) are more appropriate

Transport Forecasts
-------------------

Transport forecasts predict energy flow between grid operators and their upstream/downstream partners. These forecasts enable coordinated grid management and capacity planning across organizational boundaries.

**When to use:** Communicating planned energy usage to upstream network operators (e.g., distribution system operators reporting to transmission system operators) or receiving forecasts from downstream customers.

**Key characteristics:**

- **Balanced accuracy:** All time periods matter equally, not just peaks
- **Medium aggregation:** Typically forecasting at connection points between grid operators, providing natural aggregation that improves predictability
- **Component splitting:** Some operators require forecasts split by energy source (solar, wind, other)

**Business context:**

Grid operators like Alliander provide transport forecasts to TenneT (the Dutch transmission system operator) while receiving similar forecasts from their customers. This bidirectional forecasting enables coordinated capacity planning and operational decisions across the entire grid hierarchy.

**Optimization approach:**

Transport forecasts optimize for overall accuracy across the entire forecast horizon. The primary metric is rMAE (relative Mean Absolute Error), emphasizing consistent performance rather than peak-specific accuracy.

**Component splitting example:**

When transport forecasts must be split by energy source, use OpenSTEF's component splitting models:

.. code-block:: python

   from openstef_models.models.component_splitting import (
       ComponentSplittingModel,
       ConstantComponentSplitter,
       ConstantComponentSplitterConfig,
   )
   from openstef_core.types import EnergyComponentType
   from openstef_core.mixins import TransformPipeline

   # Configure component splitter with known ratios
   splitter = ConstantComponentSplitter(
       ConstantComponentSplitterConfig(
           source_column="total_load",
           components=[
               EnergyComponentType.SOLAR,
               EnergyComponentType.WIND,
               EnergyComponentType.OTHER,
           ],
           component_ratios={
               EnergyComponentType.SOLAR: 0.35,
               EnergyComponentType.WIND: 0.25,
               EnergyComponentType.OTHER: 0.40,
           }
       )
   )

   # Create model with preprocessing pipeline
   model = ComponentSplittingModel(
       component_splitter=splitter,
       preprocessing=TransformPipeline(),
       source_column="total_load"
   )

   # Train and predict
   model.fit(training_data)
   components = model.predict(forecast_data)

Grid Loss Forecasts
-------------------

Grid losses represent energy dissipated during transmission and distribution. Accurate loss forecasting enables financial optimization of grid operations, particularly when considering market price fluctuations.

**When to use:** Forecasting system-wide energy losses for financial planning and operational cost minimization.

**Key characteristics:**

- **Highly aggregated:** System-level forecasting where temporal and cyclic patterns dominate
- **Reduced weather impact:** At this aggregation level, weather predictors have diminished influence compared to congestion or transport forecasts
- **Cost-weighted optimization:** Errors during high-price periods are more costly than errors during low-price periods

**Optimization approach:**

Grid loss forecasts use similar metrics to transport forecasts (rMAE) but add cost-weighted error minimization based on real-time market prices. The model should minimize total financial impact rather than treating all errors equally.

**Predictive characteristics:**

At high aggregation levels, system-wide behavioral trends and temporal patterns (time of day, day of week, seasonal cycles) become the dominant factors. Weather variables that strongly influence individual customer behavior or localized congestion have less impact on total grid losses.

Free Space Estimation
---------------------

Free space estimation calculates remaining grid capacity—how much additional load a transformer, cable, or substation can handle before reaching its limit. This is a derived use case that combines load forecasting with capacity constraints.

**When to use:** Planning new connections, evaluating distributed generation integration, or assessing whether grid reinforcement is needed.

**Key characteristics:**

- **Derived from congestion forecasts:** Uses peak load predictions combined with known capacity limits
- **Focus on maximum values:** Interested in worst-case scenarios, not average conditions
- **Uncertainty quantification critical:** Decision-makers need to understand confidence intervals for capacity planning

**Implementation approach:**

Free space estimation typically involves:

1. Generate congestion forecasts with quantile predictions
2. Apply capacity constraints (transformer ratings, cable limits)
3. Calculate remaining capacity: ``free_space = capacity_limit - predicted_peak_load``
4. Provide uncertainty bounds using high quantiles (e.g., 90th, 95th percentile)

This use case emphasizes the importance of probabilistic forecasting—knowing that a transformer has 100 kW of free space with 95% confidence is far more valuable than a point estimate.

District Heating Demand
-----------------------

District heating forecasting predicts thermal energy demand for community heating systems. While not electricity-related, it shares many characteristics with electrical load forecasting and benefits from OpenSTEF's flexible architecture.

**When to use:** Forecasting heat demand for district heating networks, enabling efficient operation of combined heat and power (CHP) plants and thermal storage systems.

**Key characteristics:**

- **Strong weather dependence:** Temperature is the dominant predictor, with heating degree days providing strong signals
- **Thermal inertia:** Building thermal mass creates lag effects between weather changes and heat demand
- **Seasonal patterns:** Demand varies dramatically between heating and non-heating seasons

**Configuration considerations:**

District heating forecasts benefit from:

- Temperature-based features with lag terms to capture thermal inertia
- Seasonal models that adapt to heating vs. non-heating periods
- Wind speed features (affects building heat loss)

The same OpenSTEF pipeline components work for district heating—only the input features and domain-specific preprocessing differ from electrical load forecasting.

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion forecasting combines load predictions with grid topology information from power-grid-model. This advanced use case accounts for how electrical flow distributes across the network based on physical grid structure.

**When to use:** Forecasting congestion on specific cables or routes within a medium-voltage network where topology significantly affects load distribution.

**Key characteristics:**

- **Topology-aware:** Uses power-grid-model to understand how load flows through the network
- **Route-specific predictions:** Forecasts load on individual cables or routes, not just at nodes
- **Complex aggregation:** Multiple customer loads may contribute to a single route's congestion

**Integration approach:**

This use case requires integrating OpenSTEF with power-grid-model to:

1. Forecast loads at individual nodes (using standard OpenSTEF forecasting)
2. Use power-grid-model to simulate power flow based on network topology
3. Calculate resulting loads on specific cables and routes
4. Identify congestion points based on cable capacity limits

The integration typically happens outside OpenSTEF's core forecasting pipeline—OpenSTEF generates node-level forecasts, then power-grid-model performs the topology-aware load flow calculations.

.. note::

   Topology-aware forecasting requires detailed grid models and is typically used by distribution system operators with comprehensive network data. For simpler use cases, direct cable or route measurement with standard forecasting may be sufficient.

Choosing the Right Use Case
----------------------------

When implementing OpenSTEF for your application, consider:

**Aggregation level:** Higher aggregation generally means more predictable forecasts. Individual customers are harder to forecast than substations serving hundreds of customers.

**Accuracy requirements:** Peak-focused use cases (congestion management) need different optimization than balanced accuracy use cases (transport forecasts).

**Data availability:** Topology-aware forecasting requires detailed grid models. Component splitting requires knowledge of energy source ratios or historical component data.

**Business context:** Cost-weighted optimization (grid losses) requires market price data. Peak detection (congestion) requires defining what constitutes a "peak" in your specific context.

For guidance on integrating your data sources with OpenSTEF, see :doc:`data_integration`. For production deployment patterns, see :doc:`deployment`.