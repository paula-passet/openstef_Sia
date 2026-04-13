Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but its design was shaped by a concrete set of operational problems faced by distribution system operators (DSOs). This page describes the most common use cases the library supports, explains what makes each one distinct in terms of modelling choices and configuration, and provides practical code examples you can adapt to your own situation.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

All six use cases share the same library primitives — ``Quantile``, ``LeadTime``, forecasters, and workflow objects — but differ in the quantiles you care about, the horizon you need, the aggregation level of the measurement point, and sometimes the post-processing step applied to the raw forecast.

.. note::

   For instructions on wiring any of these use cases to a live data source, see :doc:`data_integration`.
   For production scheduling and orchestration patterns, see :doc:`deployment`.


Congestion Forecasts — Transformer and Cable Loading
-----------------------------------------------------

Congestion management is the original motivation for OpenSTEF and remains its most mature use case. The goal is to predict **when a transformer or cable will approach or exceed its rated capacity**, so the grid operator can take pre-emptive action — calling flexible customers, rerouting load, or issuing curtailment instructions.

What makes this use case distinctive is the asymmetric importance of errors. A missed peak (false negative) can cause physical damage or a forced outage; an unnecessary intervention (false positive) costs money but is recoverable. This drives two specific modelling choices:

- **High quantiles matter most.** You need accurate estimates of the 90th and 95th percentile of load, not just the median. The primary evaluation metrics are rMAE at peak hours and rCRPS across the full distribution.
- **Aggregation level is highly variable.** A substation serving thousands of customers is relatively predictable. A single medium-voltage connection to an industrial customer is not. The model must handle both, and hyperparameter tuning should reflect the noise level of the specific measurement point.

A typical configuration for a congestion forecast looks like this:

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   # Congestion use case: short horizon, emphasis on upper quantiles
   forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.5),
           Quantile(0.75),
           Quantile(0.9),
           Quantile(0.95),
       ],
       horizons=[LeadTime.from_string("PT48H")],
   )

The 48-hour horizon is typical: it gives the operations team enough lead time to contact flexible customers or arrange manual switching, while staying within the window where numerical weather prediction is still reliable enough to be useful.

.. note::

   Congestion forecasts are currently in production at Alliander for more than 10,000 grid locations.
   The library was built and battle-tested against this workload.


Free Space Estimation — Remaining Capacity
------------------------------------------

Free space estimation is a close relative of congestion forecasting. Instead of asking "will this asset overload?", it asks "how much additional load can this asset safely absorb?". The answer is used for **capacity planning and connection decisions** — for example, deciding whether a new solar park or EV charging hub can be connected to a given substation without triggering congestion.

The raw forecast is the same probabilistic load forecast you would produce for congestion management. The difference is in post-processing: you subtract the forecast (at a chosen quantile, typically the 90th or 95th percentile) from the asset's rated capacity.

.. code-block:: python

   import pandas as pd
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   RATED_CAPACITY_MW = 40.0  # transformer nameplate rating

   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.5), Quantile(0.9), Quantile(0.95)],
       horizons=[LeadTime.from_string("PT48H")],
   )

   # After obtaining forecasts from the workflow:
   # forecast_df is a DataFrame with quantile columns, e.g. "q0.95"
   def compute_free_space(forecast_df: pd.DataFrame, rated_capacity: float) -> pd.Series:
       """Remaining capacity at the 95th-percentile load forecast."""
       return (rated_capacity - forecast_df["q0.95"]).clip(lower=0.0)

Because free space estimation is a post-processing step on top of a standard probabilistic forecast, no special model configuration is required beyond ensuring the relevant upper quantiles are included in the ``quantiles`` list.


Grid Loss Forecasts
-------------------

Grid losses — the energy dissipated as heat in cables, transformers, and other network components — must be forecast for **financial settlement and procurement**. The grid operator buys energy on the wholesale market to cover anticipated losses; forecast errors translate directly into over- or under-procurement costs.

This use case has a different character from congestion forecasting in two important ways:

1. **Highly aggregated signal.** Grid losses are measured at the system level, so individual customer behaviour averages out. Temporal and cyclical patterns (time of day, day of week, season) dominate; weather predictors have less influence than in substation-level forecasts.
2. **Cost-weighted errors.** Not all forecast errors are equally expensive. An error during a high-price hour costs more than the same error during an off-peak hour. The model should ideally weight residuals by the real-time market price.

A practical configuration for grid loss forecasting uses a longer horizon and a balanced quantile set, since the goal is accuracy across the whole distribution rather than peak detection:

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.lgbm_forecaster import LGBMForecaster

   # Grid loss use case: longer horizon, full quantile spread, aggregated signal
   forecaster = LGBMForecaster(
       quantiles=[
           Quantile(0.05),
           Quantile(0.1),
           Quantile(0.3),
           Quantile(0.5),
           Quantile(0.7),
           Quantile(0.9),
           Quantile(0.95),
       ],
       horizons=[LeadTime.from_string("P3D")],
   )

The 3-day horizon aligns with typical day-ahead and intraday market windows. LightGBM tends to perform well on highly aggregated, pattern-dominated signals, but XGBoost is a reasonable alternative — benchmark both on your specific dataset.


Transport Forecasts
-------------------

Transport forecasts serve a coordination function between network operators. A DSO like Alliander provides transport forecasts to the transmission system operator (TSO, e.g. TenneT) so that the TSO can balance the national grid. Conversely, the DSO receives forecasts from its large industrial and generation customers.

The key characteristic of transport forecasts is that **overall accuracy across all time periods matters equally** — there is no special emphasis on peaks. The primary metric is rMAE across the full forecast horizon. Aggregation levels are medium: a regional substation or high-voltage/medium-voltage interface point, where individual customer noise has largely averaged out.

Some operators also require transport forecasts **split by component** — separating solar generation, wind generation, and residual demand into distinct time series. This requires training separate models for each component and summing them, or using a multi-output model architecture.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   # Transport use case: balanced quantiles, multiple horizons
   forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.1),
           Quantile(0.3),
           Quantile(0.5),
           Quantile(0.7),
           Quantile(0.9),
       ],
       horizons=[
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
   )

Using multiple horizons in a single forecaster is efficient when the TSO requires both day-ahead and two-day-ahead submissions.


District Heating Demand
-----------------------

District heating is the most domain-diverse use case currently supported by OpenSTEF. The library is not limited to electricity — any time series where demand correlates with weather, time patterns, and calendar effects is a candidate.

For a district heating network, the target variable is **thermal demand** (typically in MW or GJ/h) rather than electrical load. The modelling approach is identical to electricity forecasting, but the feature set shifts: outdoor temperature becomes the dominant weather predictor (replacing solar radiation, which matters less for heat demand), and the seasonal pattern is inverted relative to cooling-dominated electricity grids.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   # District heating: temperature-driven, medium horizon
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
       horizons=[LeadTime.from_string("PT24H")],
   )

The main practical difference when integrating district heating data is ensuring that your input ``ForecastInputDataset`` uses a temperature column as the primary weather feature. Check the ``temperature_column`` parameter of your workflow configuration and confirm it maps to the correct field in your data source.

.. note::

   District heating support is an active area of development in OpenSTEF V4. The core modelling
   primitives are fully applicable today, but domain-specific utilities (e.g., heating degree day
   features) may need to be added as custom feature transformers.


MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most complex use case because it combines probabilistic load forecasting with **power flow calculation over the actual network topology**. A single measurement point at the head of a feeder does not tell you which cable segment is congested; you need to propagate the load forecast through the network graph to find the bottleneck.

OpenSTEF handles the forecasting side of this problem. The topology-aware power flow step is handled by `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, an open-source library from the same Alliander ecosystem. The two libraries are designed to be used together:

1. **OpenSTEF** produces probabilistic load forecasts for each measurement point on the MV feeder (individual customers, distributed generation assets, etc.).
2. **power-grid-model** takes those forecasts as nodal injections and solves the power flow equations to compute voltage profiles and branch currents across the route.
3. The branch current forecasts are compared against cable ratings to identify which segment, and at which quantile, is at risk of congestion.

.. code-block:: python

   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

   # One forecaster per measurement node on the MV route.
   # Upper quantiles are critical for cable rating comparison.
   node_forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.5),
           Quantile(0.9),
           Quantile(0.95),
       ],
       horizons=[LeadTime.from_string("PT48H")],
   )

   # After collecting forecasts for all nodes, pass the quantile outputs
   # as nodal power injections to power-grid-model's batch power flow solver.
   # The resulting branch current time series can then be compared to
   # the thermal limits of each cable segment.

.. note::

   Integrating power-grid-model is outside the scope of the OpenSTEF library itself. Refer to the
   `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for the power flow
   API. OpenSTEF's role is to supply the probabilistic nodal forecasts that feed into it.


Choosing the Right Configuration
---------------------------------

The list below summarises the key configuration differences across use cases. Use it as a starting point; always validate against your own data.

**Congestion / transformer loading**

- Typical horizon: PT24H – PT48H
- Key quantiles: 0.5, 0.75, 0.9, 0.95
- Primary metrics: rMAE at peak hours, rCRPS

**Free space estimation**

- Typical horizon: PT24H – PT48H
- Key quantiles: 0.9, 0.95 (subtracted from rated capacity in post-processing)
- Primary metrics: rMAE at peak hours

**Grid losses**

- Typical horizon: P1D – P3D
- Key quantiles: full spread 0.05 – 0.95
- Primary metrics: rMAE, cost-weighted total error

**Transport**

- Typical horizon: PT24H – PT48H
- Key quantiles: 0.1 – 0.9 balanced
- Primary metrics: rMAE across all hours

**District heating**

- Typical horizon: PT24H
- Key quantiles: 0.1, 0.5, 0.9
- Primary metrics: rMAE

**MV route congestion**

- Typical horizon: PT48H (per node)
- Key quantiles: 0.5, 0.9, 0.95 (per node, fed into power flow solver)
- Primary metrics: branch-level rMAE at peak hours

A few rules of thumb:

- If you care about **not missing peaks**, include quantiles of 0.9 and above and evaluate with rCRPS or rMAE restricted to peak hours.
- If you need **overall reliability** across all hours, use a balanced quantile spread and evaluate with unconditional rMAE.
- If your measurement point is **highly aggregated** (many customers), temporal features dominate and tree-based models generalise well with default hyperparameters. If it is **low aggregation** (single customer), expect higher noise and consider regularising more aggressively or using an ensemble.
- For **cost-sensitive** applications (grid losses, market settlement), consider adding market price data as a feature or weighting the training loss by price.


Related Pages
-------------

- :doc:`data_integration` — how to connect any of these use cases to S3, InfluxDB, Databricks, or other data sources
- :doc:`deployment` — production scheduling patterns for running forecasting pipelines at scale
- :doc:`logging` — configuring structured logging and monitoring for production forecast jobs