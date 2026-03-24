Free Space Estimation
=====================

Free space estimation determines the available capacity remaining on a grid connection before congestion occurs. This use case is closely related to congestion forecasting but focuses on quantifying the headroom rather than predicting when limits will be exceeded.

What is Free Space Estimation?
------------------------------

Free space estimation calculates how much additional load can be accommodated on a grid connection without causing congestion. Grid operators use this information for:

- **Connection planning**: Determining if new customers can be connected
- **Capacity allocation**: Managing available grid capacity efficiently  
- **Investment decisions**: Identifying when grid reinforcement is needed
- **Real-time operations**: Understanding current capacity margins

The estimation considers both the physical capacity limits of grid infrastructure and the forecasted load patterns.

How OpenSTEF Addresses Free Space Estimation
--------------------------------------------

OpenSTEF supports free space estimation through its probabilistic forecasting capabilities:

**Load Forecasting Foundation**
   OpenSTEF generates probabilistic load forecasts that capture uncertainty in future demand patterns. These forecasts form the basis for capacity calculations.

**Quantile-Based Analysis**
   The library outputs multiple quantiles (P10, P50, P90) that represent different confidence levels for load predictions. Higher quantiles provide conservative estimates for capacity planning.

**Multi-Horizon Predictions**
   Free space calculations can be performed across different time horizons, from hours ahead for operational planning to days ahead for connection decisions.

**Component Integration**
   When combined with grid topology information, OpenSTEF forecasts can be used to estimate free space at different aggregation levels in the network.

Typical Implementation Approach
-------------------------------

1. **Generate Load Forecasts**: Use OpenSTEF to create probabilistic forecasts for the relevant grid connection or area
2. **Apply Capacity Constraints**: Compare forecast quantiles against known capacity limits
3. **Calculate Headroom**: Determine remaining capacity at different confidence levels
4. **Account for Uncertainty**: Use higher quantiles for conservative capacity estimates

Output Format and Interpretation
--------------------------------

Free space estimation typically produces:

- **Absolute capacity values** (MW or kW remaining)
- **Percentage utilization** of total capacity
- **Time-series projections** showing how free space evolves
- **Confidence intervals** reflecting forecast uncertainty

The probabilistic nature of OpenSTEF forecasts enables risk-based capacity management, where different quantiles inform different types of decisions.

.. note::
   Free space estimation requires accurate capacity limit data for your grid infrastructure. OpenSTEF provides the load forecasting component, but capacity constraints must be supplied based on your specific grid configuration.

Related Use Cases
-----------------

- :doc:`congestion_forecasts` - Predicting when capacity limits will be exceeded
- :doc:`transport_forecasts` - Overall load transport prediction for capacity planning

Getting Started
---------------

To implement free space estimation with OpenSTEF:

1. Review the :doc:`../user_guide/quick_start` guide for basic forecasting setup
2. Explore the :doc:`../examples` for load forecasting implementations
3. Consult the :doc:`../api/index` for detailed pipeline documentation

For operational deployment examples, see the :doc:`../user_guide/tutorials` section.