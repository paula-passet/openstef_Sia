Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but its design was shaped by a concrete set of operational problems faced by distribution system operators (DSOs). This page describes the most common use cases, what distinguishes each one technically, and how to configure OpenSTEF appropriately for each scenario.

.. mermaid:: diagrams/user_guide/use_cases_diagram_1.mmd

Understanding the use cases helps you make the right choices about model selection, quantile configuration, evaluation metrics, and how to structure your forecasting pipeline. The sections below move roughly from the most granular (individual asset) to the most aggregated (system-wide) forecasting problems.

----

Congestion Management Forecasts
--------------------------------

Congestion management is the original motivation for OpenSTEF and remains its most mature use case. The goal is to predict when a transformer or cable will approach or exceed its rated capacity, giving the grid operator enough lead time to intervene — typically by calling customers to curtail consumption or generation.

**What makes it distinctive:** Accuracy at peak moments matters far more than average accuracy. A forecast that is excellent on quiet nights but misses a summer afternoon peak is operationally useless. This drives the choice of evaluation metrics (rMAE at the 50th quantile during peaks, rCRPS) and model optimisation strategy.

**Aggregation level:** Highly variable. A high-voltage substation serving thousands of customers is relatively predictable; a single medium-voltage substation (MSR) serving a handful of industrial customers can be extremely volatile. OpenSTEF handles both, but you should expect wider prediction intervals and higher relative errors at low aggregation levels.

**Quantile configuration:** For congestion management, upper quantiles are critical. You want to know not just the expected load but the plausible worst case. A typical configuration uses quantiles spanning the full distribution, with emphasis on the upper tail:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # Congestion management: broad quantile range, focus on upper tail
   forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.05),
           Quantile(0.10),
           Quantile(0.50),
           Quantile(0.75),
           Quantile(0.90),
           Quantile(0.95),
       ],
       horizons=[
           LeadTime(timedelta(hours=24)),
           LeadTime(timedelta(hours=48)),
       ],
       hyperparams=XGBoostHyperParams(),
   )

The 0.90 and 0.95 quantiles give operators a conservative upper bound for capacity planning. The 0.50 quantile provides the best point estimate for scheduling.

----

Free Space Estimation
---------------------

Free space estimation is a derived use case built on top of congestion management forecasts. Rather than forecasting raw load, the objective is to estimate the *remaining capacity* on a cable or transformer — the headroom available before the asset reaches its limit.

**Relationship to congestion forecasts:** Free space is computed as ``rated_capacity - forecast_load``. However, because capacity limits are hard constraints, the relevant quantity for operational decisions is the *lower* quantile of free space (equivalently, the *upper* quantile of load). A grid operator offering flexibility services to customers needs to know: "How much additional load can I safely accommodate with 90% confidence?"

**What makes it distinctive:** The sign convention and the quantile of interest flip relative to congestion forecasting. You are now interested in the pessimistic estimate of available headroom, which corresponds to the optimistic (high) estimate of load. The same forecaster output serves both use cases — you simply consume different quantiles downstream.

.. code-block:: python

   import pandas as pd

   # Assume `forecast` is a ForecastDataset returned by forecaster.predict()
   # and `rated_capacity_mw` is the asset's thermal rating.
   rated_capacity_mw = 10.0

   # Extract the load forecast as a DataFrame
   forecast_df = forecast.to_dataframe()

   # Free space at the conservative (p90 load) estimate
   free_space_p10 = rated_capacity_mw - forecast_df["quantile_0.90"]

   # Free space at the median estimate
   free_space_p50 = rated_capacity_mw - forecast_df["quantile_0.50"]

   print(free_space_p10.describe())

.. note::

   Free space estimation does not require a separate model. Configure your congestion management
   forecaster with the quantiles you need, then derive free space in post-processing. This keeps
   your forecasting pipeline simple and ensures consistency between the two outputs.

----

Grid Loss Forecasts
-------------------

Grid losses are the electrical energy dissipated in cables and transformers during transmission — the difference between energy injected into the grid and energy delivered to customers. Forecasting losses accurately has direct financial consequences because grid operators must purchase this energy on the wholesale market.

**What makes it distinctive:** Grid losses are a highly aggregated quantity. At the system level, temporal and cyclic patterns (time of day, day of week, seasonal load curves) dominate, and weather predictors have a relatively weaker influence compared to substation-level forecasts. The optimisation objective also differs: errors are not equally costly. An under-forecast on a high-price day is more expensive than the same error on a low-price day, so models can be weighted by real-time market prices.

**Key metrics:** rMAE (same as transport forecasts) plus total error cost minimisation based on market prices.

**Model choice:** Because temporal patterns dominate, a linear model such as ``GBLinearForecaster`` often performs competitively with tree-based models and offers better extrapolation behaviour outside the training distribution:

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   # Grid loss: aggregated signal, linear model often sufficient
   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
       horizons=[LeadTime(timedelta(hours=24))],
       hyperparams=GBLinearHyperParams(
           learning_rate=0.05,
           reg_alpha=0.1,
           reg_lambda=1.0,
       ),
   )

----

Transport Forecasts
-------------------

Transport forecasts describe the total energy flow across a network boundary over a given period. DSOs use them to communicate planned usage to upstream transmission system operators (TSOs) and to receive equivalent forecasts from large downstream customers. For example, a DSO might provide hourly transport forecasts to the national TSO for the next 48 hours to support balancing and congestion management at the transmission level.

**What makes it distinctive:** Unlike congestion management, transport forecasts must be accurate across the *entire* forecast horizon, not just at peak moments. The evaluation metric is rMAE computed uniformly over all time steps. Some operators also require transport forecasts decomposed into components (solar generation, wind generation, residual load), which requires running separate forecasters per component and aggregating.

**Aggregation level:** Medium. Transport points aggregate many substations, making them more predictable than individual MSRs but still sensitive to weather and behavioural patterns.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # Transport forecast: balanced quantiles, 48-hour horizon
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
       horizons=[
           LeadTime(timedelta(hours=24)),
           LeadTime(timedelta(hours=48)),
       ],
       hyperparams=XGBoostHyperParams(),
   )

For split-component transport forecasts, instantiate one forecaster per component (solar, wind, other) using the same configuration, train each on the corresponding measured component, and sum the median predictions for the total transport figure.

----

District Heating Demand
-----------------------

District heating is a community-contributed use case that extends OpenSTEF beyond electricity into thermal energy. A district heating network distributes hot water from a central plant to residential and commercial buildings; forecasting demand allows the plant operator to optimise fuel consumption and reduce heat waste.

**What makes it distinctive:** This is not an electricity use case. The target variable is thermal power (MW\ :sub:`th`) or heat flow rather than electrical load. Weather — particularly outdoor temperature and wind chill — is the dominant predictor, and the seasonal pattern is inverted relative to cooling-dominated electricity grids (peak demand in winter, not summer). Holiday calendars and building stock characteristics are important covariates.

**Key consideration:** Because OpenSTEF is a general-purpose library, adapting it to district heating is primarily a data preparation task. You supply a time series of measured thermal demand as the target, include outdoor temperature as a feature, and configure the forecaster as you would for any other use case. No changes to the library itself are required.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # District heating: temperature-driven, winter-peaked demand
   # Target variable: thermal load in MW_th
   # Key features: outdoor temperature, wind speed, solar irradiance, hour, day-of-week
   forecaster = XGBoostForecaster(
       quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
       horizons=[LeadTime(timedelta(hours=24))],
       hyperparams=XGBoostHyperParams(),
   )

.. note::

   Ensure your training dataset includes at least two full heating seasons (typically October–April)
   to capture the full range of temperature-driven demand variation. A single winter may not expose
   the model to extreme cold snaps that drive peak demand.

----

MV Route Congestion with Power-Grid-Model
------------------------------------------

Medium-voltage (MV) route congestion is the most topologically complex use case. A single MV cable route may serve multiple substations in a ring or radial configuration; whether a given cable segment is congested depends not just on the load at one point but on the power flows across the entire route, which are determined by network topology.

**What makes it distinctive:** This use case combines OpenSTEF's time-series forecasting with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, an open-source library for power flow calculations. The workflow is:

1. Forecast load at each substation on the MV route using OpenSTEF (one forecaster per node).
2. Pass the forecasted nodal loads into power-grid-model as boundary conditions.
3. Run a power flow calculation to determine cable loading on each segment.
4. Identify segments where the calculated loading exceeds the thermal rating.

This separation of concerns is intentional: OpenSTEF handles the statistical forecasting problem; power-grid-model handles the physics. Neither library needs to know about the internals of the other.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # One forecaster per MV substation node on the route
   node_ids = ["MSR_A", "MSR_B", "MSR_C"]

   forecasters = {
       node_id: XGBoostForecaster(
           quantiles=[Quantile(0.50), Quantile(0.90), Quantile(0.95)],
           horizons=[LeadTime(timedelta(hours=24))],
           hyperparams=XGBoostHyperParams(),
       )
       for node_id in node_ids
   }

   # After training and predicting, collect nodal forecasts
   # nodal_forecasts: dict[str, ForecastDataset] = {
   #     node_id: forecasters[node_id].predict(node_data[node_id])
   #     for node_id in node_ids
   # }

   # Pass nodal_forecasts into power-grid-model for power flow calculation
   # (see power-grid-model documentation for the load update API)

.. note::

   For MV route congestion, use the **p90 or p95 quantile** as the nodal load input to the power
   flow calculation. Using the median forecast underestimates the probability of congestion on the
   cable segments because load uncertainties at multiple nodes compound.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key differences between use cases to help you make configuration decisions quickly.

+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+
| Use case                  | Aggregation level   | Critical quantiles          | Primary metric     | Dominant features                |
+===========================+=====================+=============================+====================+==================================+
| Congestion management     | Low–medium          | Upper tail (p90, p95)       | rMAE@peaks, rCRPS  | Weather, lag, calendar           |
+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+
| Free space estimation     | Low–medium          | Upper tail (derived)        | rMAE@peaks         | Same as congestion               |
+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+
| Grid loss                 | High                | Median (p50)                | rMAE, cost-weighted| Temporal/cyclic, market price    |
+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+
| Transport                 | Medium              | Full range                  | rMAE               | Weather, lag, calendar           |
+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+
| District heating          | Medium–high         | Full range                  | rMAE               | Temperature, wind, calendar      |
+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+
| MV route congestion       | Low (per node)      | Upper tail (p90, p95)       | rMAE@peaks         | Weather, lag, topology           |
+---------------------------+---------------------+-----------------------------+--------------------+----------------------------------+

A few practical rules of thumb:

- **If you care about avoiding overload**, configure upper-tail quantiles (p90, p95) and evaluate on peak periods.
- **If you care about average accuracy**, a symmetric quantile set (p10, p50, p90) with rMAE evaluation is appropriate.
- **If your target is highly aggregated** (system-level losses, large transport points), try a linear model before a tree-based one — it may generalise better and trains faster.
- **If topology matters**, do not try to encode network structure into the forecaster features. Use power-grid-model for the physics and keep OpenSTEF focused on the statistical problem.

----

Related Pages
-------------

- :doc:`data_integration` — How to load measurement data from S3, Databricks, InfluxDB, and other sources into the formats OpenSTEF expects.
- :doc:`deployment` — Production deployment patterns for running multiple forecasters at scale across thousands of grid locations.
- :doc:`logging` — Configuring structured logging for forecasting pipelines, including per-use-case log contexts.