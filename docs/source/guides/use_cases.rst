OpenSTEF Use Cases
==================

OpenSTEF is a Python machine learning library that supports diverse short-term energy forecasting applications. Each use case has distinct characteristics, optimization targets, and business contexts that influence model selection and performance metrics. This guide helps you identify which approach matches your forecasting needs.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's primary use case, developed to address grid capacity limitations during the energy transition. When grid infrastructure reaches physical limits, accurate peak predictions enable proactive demand response instead of costly grid reinforcement.

**Primary focus:** Accuracy during peak load periods when congestion occurs.

**Aggregation levels:** Highly variable, from individual customers to large substations. Individual customer forecasts face significant behavioral variability, while aggregated points show more predictable patterns.

**Typical applications:**
- Substation load forecasting
- Individual customer predictions for large consumers
- Medium-voltage substations (MSRs)
- Distribution transformer monitoring

**Business context:** Grid operators need precise predictions at congestion points to implement effective mitigation strategies. This enables connecting new customers despite capacity constraints by calling customers in advance to reduce consumption during predicted peak periods.

**Key metrics:** Effective precision and recall for peak detection, rMAE@50th quantile at peaks, rCRPS for uncertainty quantification.

**Model optimization:** Emphasis on peak detection accuracy and high-quantile precision, with robust handling of high variability in low-aggregation scenarios.

.. code-block:: python

   from openstef_beam.forecasting import ForecastingPipeline
   from openstef_beam.models import XGBQuantileRegressor

   # Configure for congestion management
   pipeline = ForecastingPipeline(
       model=XGBQuantileRegressor(
           quantiles=[0.1, 0.5, 0.9],  # Focus on high quantiles
           peak_emphasis=True
       ),
       target_column="load_mw",
       horizon_hours=48
   )

Transport Forecasts
-------------------

Transport forecasts enable coordination between grid operators at different voltage levels. Distribution system operators provide forecasts to transmission operators while receiving forecasts from their customers, creating a hierarchical forecasting system.

**Primary focus:** Overall forecast accuracy across all time periods, not just peaks.

**Aggregation levels:** Medium aggregated points that balance predictability with operational granularity.

**Business context:** Grid operators require reliable forecasts to communicate planned energy usage to upstream network operators. For example, Alliander provides transport forecasts to TenneT (transmission system operator) while receiving forecasts from customers. Some operators require component-split forecasts (solar, wind, other) for detailed planning.

**Key metrics:** rMAE across the entire forecast horizon.

**Model optimization:** Balanced performance with emphasis on reliability and consistency rather than peak detection.

.. code-block:: python

   # Transport forecast configuration
   pipeline = ForecastingPipeline(
       model=XGBQuantileRegressor(
           quantiles=[0.25, 0.5, 0.75],  # Balanced quantiles
           objective="reg:squarederror"  # Focus on overall accuracy
       ),
       target_column="transport_mw",
       split_components=["solar", "wind", "other"]  # Component splitting
   )

Grid Loss Forecasts
-------------------

Grid losses represent the difference between energy input and output in the distribution system. These forecasts optimize financial operations by predicting losses that must be compensated through energy purchases.

**Primary focus:** Overall accuracy with cost-weighted error minimization based on market prices.

**Aggregation levels:** Highly aggregated points where system-level patterns dominate individual customer behavior.

**Predictive characteristics:** Weather predictors have diminished impact at this aggregation level. Temporal patterns and system-wide behavioral trends become the dominant factors.

**Business context:** Financial optimization of grid operations considering real-time market price fluctuations. Accurate loss prediction enables better energy procurement strategies.

**Key metrics:** rMAE plus total error cost minimization based on market prices.

**Model optimization:** Error weighting based on real-time market prices and operational costs.

.. code-block:: python

   # Grid loss forecast with cost weighting
   pipeline = ForecastingPipeline(
       model=LinearRegressor(),  # Simple model for aggregated data
       target_column="grid_losses_mwh",
       cost_weighting=True,
       market_price_column="price_eur_mwh"
   )

Free Space Estimation
---------------------

Free space estimation calculates available grid capacity by forecasting current load and subtracting it from equipment limits. This enables grid operators to assess connection capacity for new customers.

**Primary focus:** Conservative estimation to avoid overcommitment of grid capacity.

**Business context:** Grid operators need reliable estimates of available capacity to make connection decisions. Underestimating available space is safer than overestimating, as overcommitment can lead to equipment overload.

**Model characteristics:** Typically uses high quantile forecasts (e.g., 90th percentile) to ensure conservative capacity estimates.

.. code-block:: python

   # Free space estimation using high quantile
   pipeline = ForecastingPipeline(
       model=XGBQuantileRegressor(quantiles=[0.9]),
       target_column="load_mw"
   )

   # Calculate free space
   forecast = pipeline.predict(data)
   equipment_limit = 50.0  # MW
   free_space = equipment_limit - forecast["quantile_0.9"]

EV Charging Capacity Estimation
-------------------------------

Electric vehicle charging capacity estimation forecasts available power for EV charging infrastructure, considering existing grid load and capacity constraints.

**Primary focus:** Real-time capacity assessment for dynamic load management.

**Business context:** EV charging operators need to understand available grid capacity to optimize charging schedules and avoid grid congestion. This becomes critical as EV adoption increases.

**Model characteristics:** Requires high-frequency forecasting (15-minute to hourly intervals) with emphasis on near-term accuracy.

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model topology analysis to predict congestion along specific grid routes rather than at individual points.

**Primary focus:** Route-level congestion prediction considering power flow topology.

**Business context:** Traditional point-based forecasting may miss congestion that occurs along transmission routes between substations. Topology-aware forecasting provides more accurate congestion predictions.

**Integration approach:** OpenSTEF provides load forecasts that feed into power-grid-model for topology-aware power flow calculations.

.. note::
   MV route congestion requires integration with the power-grid-model library for topology analysis. See the power-grid-model documentation for topology modeling details.

.. code-block:: python

   from power_grid_model import PowerGridModel
   
   # Generate forecasts for all grid points
   forecasts = {}
   for node in grid_nodes:
       pipeline = ForecastingPipeline(model=XGBQuantileRegressor())
       forecasts[node.id] = pipeline.predict(node.data)
   
   # Use topology model to assess route congestion
   grid_model = PowerGridModel(topology_data)
   congestion_analysis = grid_model.calculate_power_flow(forecasts)

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electricity forecasting into thermal energy systems. This use case forecasts heat demand for district heating networks.

**Primary focus:** Thermal demand prediction for heating system optimization.

**Business context:** District heating operators need accurate demand forecasts to optimize heat generation and distribution. Unlike electricity, heat can be stored more easily, changing the optimization dynamics.

**Model characteristics:** Strong temperature dependency with different seasonal patterns compared to electricity demand.

.. note::
   District heating support is under development in OpenSTEF 4.0. This represents expansion beyond traditional electricity grid applications.

Choosing Your Use Case
-----------------------

To select the appropriate use case for your application:

1. **Identify your optimization target:** Peak detection (congestion), overall accuracy (transport), or cost minimization (losses)

2. **Consider aggregation level:** Individual customers require different approaches than aggregated substations

3. **Determine forecast horizon:** Real-time capacity (EV charging) versus day-ahead planning (transport)

4. **Assess data availability:** Topology-aware forecasting requires additional grid model data

5. **Understand business constraints:** Conservative estimates (free space) versus balanced accuracy (transport)

For detailed implementation guidance, see the tutorials and how-to guides sections. The concepts reference page provides deeper insight into the forecasting principles behind each use case.