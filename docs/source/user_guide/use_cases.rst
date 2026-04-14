Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was built to solve real operational problems in electricity grid management. This page describes the main use cases the library supports, what makes each one distinct, and how to configure OpenSTEF appropriately for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

Understanding which use case you are solving matters because each one has different accuracy priorities, aggregation characteristics, and model tuning requirements. The sections below walk through each scenario in turn.

----

Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case in OpenSTEF. Grid operators face situations where demand or generation at a specific point in the network — a transformer, a cable, a medium-voltage substation (MSR) — risks exceeding its rated capacity. Rather than building new infrastructure immediately, operators can intervene proactively: calling customers to shift load, activating demand response contracts, or re-routing power flows.

All of these interventions require accurate forecasts of *when* a congestion point will be overloaded, and by how much. The key accuracy requirement is therefore precision near **peak load periods**, not average accuracy across all hours. A model that is excellent on quiet nights but misses Tuesday afternoon peaks is operationally useless.

**What makes this use case hard:** Congestion points vary enormously in aggregation level. A high-voltage substation aggregates thousands of customers and is relatively predictable. An individual MSR serving a small industrial estate may have highly erratic behaviour driven by a single large customer. OpenSTEF handles both, but you should expect wider prediction intervals and higher rMAE at low-aggregation points.

**Key metrics:** rMAE at the 50th quantile during peak periods, effective precision and recall of peak detection, rCRPS (continuous ranked probability score).

**Model tuning:** Emphasise high-quantile accuracy. Use quantiles such as ``[0.1, 0.5, 0.9, 0.95]`` so that operators can reason about worst-case scenarios. XGBoost with a magnitude-weighted pinball loss (the default) works well here.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Congestion management: emphasise high quantiles for peak detection
    forecaster = XGBoostForecaster(
        quantiles=[
            Quantile(0.1),
            Quantile(0.5),
            Quantile(0.9),
            Quantile(0.95),
        ],
        horizons=[
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        hyperparams=XGBoostHyperParams(
            n_estimators=200,
            max_depth=6,
        ),
    )

    forecaster.fit(training_data)
    predictions = forecaster.predict(forecast_data)

The ``0.95`` quantile gives operators a conservative upper bound for capacity planning. The ``0.1`` quantile is useful for identifying periods where load will definitely be low and no intervention is needed.

----

Free Space Estimation
---------------------

Free space estimation is a derived use case built on top of congestion forecasts. Rather than asking "how much load will flow through this cable?", the question becomes "how much *additional* capacity is available on this cable at a given time?".

This is critical for connecting new customers — solar installations, EV charging parks, heat pumps — to the grid. A grid operator needs to know whether a proposed connection point has sufficient headroom before committing to a connection agreement.

**Relationship to congestion forecasting:** Free space is typically computed as:

.. code-block:: text

    free_space = rated_capacity - forecast_load (at a chosen quantile)

Using a high quantile (e.g., ``0.9`` or ``0.95``) for the forecast load gives a conservative estimate of free space, which is appropriate for capacity commitments. The OpenSTEF library produces the quantile forecasts; the free space calculation is then a straightforward post-processing step in your application.

**What makes this use case different:** The accuracy requirement shifts from peak detection to *reliable upper-bound estimation*. You want the ``0.9`` quantile to be well-calibrated — meaning that load actually exceeds it only 10% of the time — rather than simply minimising median error. Evaluate calibration explicitly using coverage metrics.

----

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses accurately matters for two reasons: operational efficiency (losses must be purchased on the energy market) and financial optimisation (buying loss-covering energy at the right time minimises cost).

**What makes this use case different:** Grid losses are measured at a highly aggregated level — typically the entire distribution network or large segments of it. At this aggregation level, individual customer behaviour averages out and **system-level temporal patterns dominate**: time of day, day of week, seasonal load curves. Weather predictors (temperature, irradiance) have diminished impact compared to congestion forecasting.

**Key metrics:** rMAE (similar to transport forecasts) plus total error cost, weighted by real-time market prices. A forecast error at peak price hours costs far more than the same error at off-peak hours.

**Model tuning:** Because the signal is smoother and more predictable, simpler models often perform competitively. Consider starting with ``GBLinearForecaster`` before reaching for XGBoost. If you have access to market price data, you can implement a custom loss function that weights errors by price.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.gblinear_forecaster import (
        GBLinearForecaster,
    )

    # Grid loss: aggregated signal, balanced quantiles, cost-aware evaluation
    forecaster = GBLinearForecaster(
        quantiles=[
            Quantile(0.1),
            Quantile(0.5),
            Quantile(0.9),
        ],
        horizons=[
            LeadTime(timedelta(hours=24)),
        ],
    )

    forecaster.fit(training_data)
    predictions = forecaster.predict(forecast_data)

.. note::

   Market price weighting is not built into the standard loss functions. Implement it by subclassing the forecaster or by applying sample weights during training. See the :doc:`deployment` page for patterns on integrating custom components into a production pipeline.

----

Transport Forecasts
-------------------

Transport forecasts serve a coordination function between network operators at different voltage levels. A distribution system operator (DSO) like Alliander must report expected energy flows to the transmission system operator (TSO, e.g. TenneT) so that the TSO can balance the national grid. Conversely, the DSO receives forecasts from large industrial customers connected to its network.

**What makes this use case different:** Unlike congestion forecasting, transport forecasts must be accurate *across the entire forecast horizon*, not just at peaks. A systematic bias in quiet periods is just as problematic as missing a peak, because it leads to incorrect capacity commitments upstream.

**Aggregation level:** Medium — typically at the level of a high-voltage/medium-voltage substation serving a region. This gives a good balance between predictability and granularity.

**Split-component forecasts:** Some TSOs require transport forecasts broken down by generation type: solar, wind, and residual load. This requires running separate forecasting pipelines per component and then aggregating. OpenSTEF's modular design supports this pattern naturally — instantiate one forecaster per component with appropriate input features.

**Key metrics:** rMAE across all time periods.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Transport: balanced accuracy across all horizons
    # Run once per component (solar, wind, residual) if split forecasts are required
    solar_forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    wind_forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    # Fit and predict independently, then sum for total transport forecast
    solar_forecaster.fit(solar_training_data)
    wind_forecaster.fit(wind_training_data)

----

District Heating Demand
-----------------------

District heating is a community use case that extends OpenSTEF beyond electricity into thermal energy. A district heating network distributes hot water from a central plant to residential and commercial buildings. Forecasting thermal demand allows the plant operator to schedule production efficiently and avoid both under-supply (cold buildings) and over-supply (wasted energy).

**What makes this use case different:** The target variable is thermal load (MW or MWh of heat), not electrical load. The dominant predictors shift accordingly: outdoor temperature and wind chill become far more important than irradiance. Temporal patterns (morning warm-up peaks, weekend vs. weekday profiles) remain relevant.

OpenSTEF does not require the target variable to be electrical — the library operates on time series data and is agnostic to the physical quantity being forecast. You can use the same forecaster classes with a thermal load time series as the target.

.. note::

   District heating support in OpenSTEF V4 is actively being developed. The core forecasting machinery works today, but domain-specific feature engineering (e.g., heating degree days, building thermal mass features) must currently be implemented in your own data preparation pipeline. Contributions to add built-in thermal features are welcome.

----

MV Route Congestion with Power-Grid-Model
------------------------------------------

Medium-voltage (MV) route congestion is the most topologically complex use case. In a meshed or ring MV network, the load on a specific cable segment depends not just on the customers directly connected to it, but on the entire network topology — which switches are open, which feeders are active, and how power flows are distributed across parallel paths.

**The challenge:** A point forecast at a single measurement location does not capture this topology dependency. If a switch configuration changes, the same customer load can produce completely different cable loading patterns.

**The solution:** Combine OpenSTEF's time-series forecasting with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, a Python library for power flow calculations on distribution networks. The workflow is:

1. Use OpenSTEF to forecast load at each measurement point in the MV network (individual substations, large customers).
2. Feed those load forecasts as inputs to a power-grid-model power flow calculation.
3. The power flow calculation returns cable and transformer loading for every segment in the network, accounting for the current topology.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_2.mmd

This architecture means OpenSTEF handles the forecasting problem (what will the load be at each node?) while power-grid-model handles the physics problem (given those loads, what flows through each cable?). Neither library needs to know about the other's internals.

**Practical considerations:**

- You need one OpenSTEF forecaster per measurement point in the MV network. For a network with 50 substations, that means 50 separate training and prediction pipelines. OpenSTEF is designed for this scale — Alliander runs forecasts for 10,000+ locations in production.
- Topology changes (switch operations, network reconfigurations) must be reflected in the power-grid-model input, not in the OpenSTEF forecasts. The forecasters remain topology-agnostic.
- Uncertainty propagation: if you use quantile forecasts from OpenSTEF as inputs to power-grid-model, you can run the power flow calculation at multiple quantile levels to obtain probabilistic cable loading estimates.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key differences between use cases to help you select appropriate settings:

+---------------------------+---------------------+---------------------------+----------------------------+
| Use case                  | Aggregation level   | Primary accuracy target   | Recommended quantiles      |
+===========================+=====================+===========================+============================+
| Congestion management     | Low to medium       | Peak detection            | 0.1, 0.5, 0.9, 0.95        |
+---------------------------+---------------------+---------------------------+----------------------------+
| Free space estimation     | Low to medium       | Upper-bound calibration   | 0.5, 0.9, 0.95             |
+---------------------------+---------------------+---------------------------+----------------------------+
| Grid loss                 | High                | Cost-weighted total error | 0.1, 0.5, 0.9              |
+---------------------------+---------------------+---------------------------+----------------------------+
| Transport                 | Medium              | Balanced across horizon   | 0.1, 0.5, 0.9              |
+---------------------------+---------------------+---------------------------+----------------------------+
| District heating          | Medium              | Balanced across horizon   | 0.1, 0.5, 0.9              |
+---------------------------+---------------------+---------------------------+----------------------------+
| MV route congestion       | Low (per node)      | Per-node accuracy         | 0.5, 0.9 (per node)        |
+---------------------------+---------------------+---------------------------+----------------------------+

.. note::

   These are starting points, not rules. Always evaluate your model against the metric that matters for your operational decision. For congestion management, that means evaluating rMAE specifically during peak periods, not across all hours equally.

----

Related Pages
-------------

- :doc:`data_integration` — How to load measurement data from S3, Databricks, InfluxDB, and other sources into the formats OpenSTEF expects.
- :doc:`deployment` — Production deployment patterns for running multiple forecasting pipelines at scale.
- :doc:`logging` — Configuring logging for long-running forecast pipelines across many grid locations.