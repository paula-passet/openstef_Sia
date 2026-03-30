Common OpenSTEF Use Cases
=========================

OpenSTEF is a Python machine learning library designed for short-term energy forecasting across diverse applications. Each use case has unique characteristics that determine the optimal forecasting approach, model configuration, and evaluation metrics. This guide helps you identify which use case matches your needs and understand the key differences between approaches.

Congestion Management Forecasts
-------------------------------

Congestion management represents OpenSTEF's original and most mature use case, focusing on preventing grid overloads through accurate peak detection.

**When to use:** You need to predict when grid components will approach their capacity limits to implement proactive mitigation strategies like demand response or load curtailment.

**Key characteristics:**
- **Primary focus:** Accuracy during peak load periods rather than overall forecast performance
- **Aggregation levels:** Highly variable, from individual customers to large substations
- **Critical challenge:** Individual customer forecasts can be unpredictable due to behavioral variability

**Typical applications:**
- Substation capacity planning
- Individual customer peak prediction
- Medium-voltage substation (MSR) monitoring
- Proactive congestion prevention

**Optimization approach:**
- Emphasis on high-quantile accuracy (95th, 99th percentiles)
- Peak detection capabilities with effective precision and recall
- Robust handling of high variability in low-aggregation scenarios

**Key metrics:** Effective precision and recall, rMAE@50th quantile at peaks, rCRPS

.. code-block:: python

   from openstef_beam.forecasting import Forecaster
   from openstef_beam.models import XGBQuantileRegressor
   
   # Configure for congestion management
   forecaster = Forecaster(
       model=XGBQuantileRegressor(quantiles=[0.5, 0.95, 0.99]),
       optimize_for_peaks=True,
       peak_threshold_percentile=90
   )

Transport Forecasts
-------------------

Transport forecasts enable coordination between grid operators at different voltage levels, providing reliable predictions for capacity planning and energy trading.

**When to use:** You need to communicate planned energy usage to upstream network operators (like transmission system operators) or receive forecasts from downstream customers.

**Key characteristics:**
- **Primary focus:** Overall forecast accuracy across all time periods
- **Aggregation levels:** Medium aggregated points balancing predictability with granularity
- **Business context:** Enables coordinated grid management between DSOs and TSOs

**Typical applications:**
- DSO reporting to transmission operators (e.g., Alliander to TenneT)
- Capacity planning and energy trading
- Split-component forecasting (solar, wind, other) when required by regulations

**Optimization approach:**
- Balanced performance across entire forecast horizon
- Emphasis on reliability and consistency
- May require component decomposition for regulatory compliance

**Key metrics:** rMAE across all periods

.. code-block:: python

   from openstef_beam.forecasting import Forecaster
   from openstef_beam.models import LightGBMRegressor
   
   # Configure for transport forecasting
   forecaster = Forecaster(
       model=LightGBMRegressor(),
       optimize_for_reliability=True,
       enable_component_split=True  # If regulatory requirements
   )

Grid Loss Forecasts
-------------------

Grid loss forecasting optimizes the financial aspects of grid operations by predicting system losses and minimizing costs based on real-time market prices.

**When to use:** You need to optimize grid operations financially, accounting for energy losses and market price fluctuations.

**Key characteristics:**
- **Primary focus:** Cost-weighted error minimization rather than pure accuracy
- **Aggregation levels:** Highly aggregated points where system-level patterns dominate
- **Predictive patterns:** Weather has diminished impact; temporal and cyclic patterns become dominant

**Typical applications:**
- Financial optimization of grid operations
- Energy trading and balancing market participation
- System-wide efficiency monitoring

**Optimization approach:**
- Error weighting based on real-time market prices
- Focus on system-level temporal patterns
- Reduced emphasis on weather predictors at high aggregation

**Key metrics:** rMAE plus total error cost minimization based on market prices

.. code-block:: python

   from openstef_beam.forecasting import Forecaster
   from openstef_beam.models import LinearRegressor
   
   # Configure for grid loss forecasting
   forecaster = Forecaster(
       model=LinearRegressor(),
       cost_weighting=True,
       market_price_integration=True,
       reduce_weather_features=True
   )

Free Space Estimation
---------------------

Free space estimation determines available grid capacity for new connections, particularly important for EV charging infrastructure and distributed energy resources.

**When to use:** You need to assess how much additional load can be connected to grid points without causing congestion.

**Key characteristics:**
- **Primary focus:** Conservative capacity estimation with safety margins
- **Aggregation levels:** Variable, depending on connection voltage level
- **Critical requirement:** Must account for simultaneous peak scenarios

**Typical applications:**
- EV charging station capacity planning
- New customer connection assessments
- Distributed energy resource integration
- Grid expansion planning

**Optimization approach:**
- Conservative forecasting with built-in safety margins
- Simultaneous peak scenario modeling
- Integration with capacity planning tools

.. code-block:: python

   from openstef_beam.forecasting import Forecaster
   from openstef_beam.analysis import CapacityAnalyzer
   
   # Configure for free space estimation
   forecaster = Forecaster(
       model=XGBQuantileRegressor(quantiles=[0.5, 0.95, 0.99]),
       conservative_estimation=True
   )
   
   analyzer = CapacityAnalyzer(
       safety_margin=0.2,  # 20% safety margin
       simultaneous_peak_probability=0.95
   )

MV Route Congestion with Topology
----------------------------------

Medium-voltage route congestion management combines OpenSTEF forecasting with power-grid-model topology analysis for comprehensive grid state prediction.

**When to use:** You need topology-aware forecasting that considers the electrical network structure and power flows, not just individual point forecasts.

**Key characteristics:**
- **Integration requirement:** Combines OpenSTEF with power-grid-model library
- **Topology awareness:** Considers network structure and power flow constraints
- **Advanced modeling:** Accounts for voltage levels, line impedances, and network topology

**Typical applications:**
- Advanced congestion management with network constraints
- Voltage stability analysis
- Network reconfiguration planning
- Coordinated control strategies

**Optimization approach:**
- Point forecasts combined with power flow calculations
- Network constraint consideration
- Coordinated optimization across multiple grid points

.. note::
   This use case requires integration with the power-grid-model library for topology calculations. See the power-grid-model documentation for network modeling details.

.. code-block:: python

   from openstef_beam.forecasting import Forecaster
   from power_grid_model import PowerGridModel
   
   # Combine OpenSTEF with topology analysis
   forecaster = Forecaster(model=XGBQuantileRegressor())
   
   # Power flow analysis with forecasted loads
   grid_model = PowerGridModel(input_data)
   
   # Topology-aware congestion analysis
   for forecast_time in forecast_horizon:
       load_forecast = forecaster.predict(forecast_time)
       power_flow_result = grid_model.calculate_power_flow(load_forecast)
       congestion_analysis = analyze_network_constraints(power_flow_result)

District Heating
----------------

District heating represents OpenSTEF's expansion beyond electricity forecasting into thermal demand prediction for community heating systems.

**When to use:** You operate district heating systems and need to predict thermal demand for efficient heat generation and distribution.

**Key characteristics:**
- **Domain:** Thermal energy rather than electrical
- **Seasonal patterns:** Strong correlation with outdoor temperature and weather
- **Community application:** Non-DSO/TSO use case expanding OpenSTEF's applicability

**Typical applications:**
- Heat generation planning
- Thermal storage optimization
- Community heating system management
- Combined heat and power (CHP) coordination

.. note::
   District heating support is under active development in OpenSTEF 4.0. Check the latest documentation for current capabilities and examples.

Choosing the Right Use Case
---------------------------

Consider these factors when selecting your forecasting approach:

**Data aggregation level:**
- High aggregation (system-wide): Grid losses, transport forecasts
- Medium aggregation (substation-level): Transport, some congestion management
- Low aggregation (customer-level): Individual congestion management, free space estimation

**Primary optimization target:**
- Peak accuracy: Congestion management, free space estimation
- Overall accuracy: Transport forecasts
- Cost optimization: Grid loss forecasts
- Safety/reliability: Free space estimation, MV route congestion

**Business context:**
- Operational (real-time): Congestion management, MV route congestion
- Planning (medium-term): Transport forecasts, free space estimation
- Financial (market-driven): Grid loss forecasts
- Regulatory (compliance): Transport forecasts with component splits

**Technical complexity:**
- Standard forecasting: Most use cases
- Topology integration: MV route congestion
- Multi-domain: District heating
- Component decomposition: Some transport forecasts

For detailed implementation guidance, see the :doc:`../getting_started/tutorials` and :doc:`how_to_guides` sections. For deeper understanding of the underlying concepts, refer to :doc:`../reference/concepts`.