Use Cases Overview
==================


Understanding OpenSTEF Use Cases
--------------------------------


OpenSTEF is a flexible forecasting library designed to adapt to diverse energy system forecasting needs. As a model-agnostic Python framework, it provides complete pipelines for data preprocessing, feature engineering, model training, and probabilistic forecasting across various energy domains.

Use cases differ along several key dimensions: forecast horizon (hours to days ahead), data types (load, generation, transport), grid levels (distribution to transmission), and application context (congestion management, capacity planning, demand response). The library's modular architecture enables customization for specific forecasting scenarios while maintaining consistent methodology.


- Grid congestion management - Forecast peak loads to enable proactive demand response and prevent equipment overload

- Energy system optimization - Optimize energy distribution and reduce grid losses through accurate load predictions

- Research and experimentation - Support data scientists with metrics, plotting, and backtesting frameworks for energy forecasting research

- Small-scale deployments - Enable single teams to implement end-to-end forecasting solutions from data retrieval to prediction

- Specialized applications - Support transport forecasts, district heating, EV charging capacity, and MV route congestion analysis


Grid Infrastructure Use Cases
-----------------------------


OpenSTEF supports three core grid infrastructure forecasting applications. Congestion forecasting predicts when grid equipment will exceed capacity limits, enabling proactive demand response by calling customers to reduce consumption before overloads occur. Free space estimation calculates available grid capacity for connecting new customers without reinforcement. Grid loss forecasting predicts energy losses in transmission and distribution networks for operational optimization. All three approaches require historical load data, weather information, and grid topology details. Use congestion forecasting for preventing equipment overloads, free space estimation for connection planning, and grid loss forecasting for efficiency optimization.


.. [DIAGRAM: Comparison diagram showing the relationship between grid load, capacity, congestion, and free space forecasting]


Transport and Distribution Use Cases
------------------------------------


Transport forecasting for energy distribution networks focuses on predicting load flows across transmission lines, substations, and interconnection points. These forecasts require detailed network topology data, power flow constraints, and transmission capacity limits to optimize grid operations and prevent congestion.

District heating applications involve forecasting thermal energy demand across interconnected building networks. Unlike electrical grids, these systems must account for thermal inertia, heat storage capacity, and temperature-dependent losses through distribution pipes, requiring specialized preprocessing of ambient temperature and building occupancy data.

Both use cases typically operate at medium aggregation levels, balancing individual connection point accuracy with network-wide optimization needs. Transport forecasts emphasize peak period accuracy for congestion management, while district heating prioritizes temperature correlation and seasonal demand patterns for efficient heat production scheduling.


- Transport forecasts show pronounced daily commuting patterns with sharp morning and evening peaks, unlike grid forecasts which have more distributed load patterns

- District heating demand exhibits strong seasonal variations with minimal summer consumption, contrasting with electricity's year-round base load requirements

- Weather dependencies differ significantly - heating systems respond primarily to temperature changes while grid forecasts must consider multiple weather variables including solar irradiance

- Transport energy consumption follows predictable weekly cycles with reduced weekend activity, while electrical grid patterns vary more by customer type and industrial schedules

- Heating networks show thermal inertia effects where demand lags behind temperature changes, unlike immediate electrical load responses to weather conditions

- Peak demand timing varies - transport peaks during rush hours, heating peaks during cold mornings and evenings, while electrical grids peak during hot afternoons or cold evenings


Advanced Topology-Aware Forecasting
-----------------------------------


MV route congestion management addresses capacity constraints across medium-voltage distribution networks by forecasting load at multiple interconnected grid points. Unlike traditional single-point forecasting, this approach requires detailed topology information to understand how power flows through alternative routes when congestion occurs. OpenSTEF integrates with power-grid-model to enable topology-aware forecasting, combining load predictions with grid topology analysis to identify potential bottlenecks and optimize power flow across the entire MV network infrastructure.


.. [DIAGRAM: Architecture diagram showing how OpenSTEF integrates with power-grid-model for topology-aware forecasting workflows]


Choosing the Right Use Case
---------------------------


- Data availability: High-frequency historical data (15-minute intervals) enables short-term forecasting, while sparse data limits accuracy but may suffice for long-term planning

- Forecast horizon: Short-term forecasts (1-48 hours) require real-time data pipelines, medium-term (1-7 days) balance accuracy with computational cost, long-term (weeks-months) focus on seasonal patterns

- Accuracy requirements: Congestion management and grid operations demand high precision with sub-1% error tolerance, while capacity planning allows 5-10% margins

- Computational resources: Real-time forecasting needs continuous processing power and memory, batch forecasting can utilize scheduled compute resources more efficiently

- Integration complexity: Jupyter notebook experimentation requires minimal setup, production deployments need robust data pipelines and monitoring infrastructure


.. note::

   This page helps you select the right use case for your needs. For detailed implementation steps, code examples, and configuration guidance, refer to the tutorials and how-to guides sections.


