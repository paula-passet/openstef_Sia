Common OpenSTEF Use Cases
=========================

OpenSTEF is a Python library designed to be composed into forecasting pipelines, and the same core
machinery — probabilistic models, quantile outputs, lead-time-aware datasets — underpins a wide range
of real-world applications. This page describes the most common use cases, what distinguishes each
one, and how to configure OpenSTEF appropriately for each.

.. note:: [DIAGRAM: Use case overview showing the six forecasting scenarios (congestion management, free space estimation, grid loss, transport, district heating, MV route congestion) arranged around a central OpenSTEF library core, with arrows indicating the input data types (load measurements, weather, topology, market prices) flowing in and the output applications (congestion alerts, capacity planning, cost optimisation, TSO reporting, heating dispatch, route-level risk) flowing out.]

All six use cases share the same fundamental workflow: provide a :class:`ForecastInputDataset` with
historical measurements and optional exogenous features, configure a forecaster with the quantiles and
lead times appropriate to your problem, and consume the resulting :class:`ForecastDataset`. What
differs is which quantiles matter, how far ahead you need to look, and how you interpret the output.

----

Congestion Management Forecasts
--------------------------------

Congestion management is the original use case for which OpenSTEF was built, and it remains the most
demanding in terms of accuracy requirements. A distribution system operator (DSO) needs to know *when*
a transformer or cable will be loaded beyond its rated capacity so that demand-response actions —
curtailment requests, customer call-outs, or automated switching — can be triggered in advance.

The key characteristic of this use case is that **errors near peak load are far more costly than errors
at low load**. A forecast that is 5 % wrong at midnight is inconsequential; the same relative error
during a summer-afternoon peak can mean an undetected overload. This drives two configuration choices:

- **High quantiles matter most.** You need a well-calibrated 90th or 95th percentile to answer "what
  is the worst plausible load in the next four hours?" The median is useful for situational awareness
  but not for triggering interventions.
- **Short to medium horizons dominate.** Congestion actions are typically taken 1–48 hours ahead.
  Longer horizons are used for capacity planning, but operational decisions live in this window.

Aggregation levels vary enormously: a high-voltage substation serving tens of thousands of customers
is highly predictable, while a single medium-voltage substation (MSR) serving a handful of industrial
customers can be volatile. OpenSTEF handles both, but you should expect wider confidence intervals and
higher rMAE at low-aggregation points.

**Primary metrics:** rMAE at the 50th quantile during peak periods, precision/recall for overload
events, rCRPS for overall probabilistic calibration.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Congestion management: emphasise high quantiles, short horizons
    forecaster = XGBoostForecaster(
        quantiles=[
            Quantile(0.5),   # median — operational overview
            Quantile(0.9),   # high load scenario — triggers demand response
            Quantile(0.95),  # worst-case — hard capacity checks
        ],
        horizons=[
            LeadTime(timedelta(hours=1)),
            LeadTime(timedelta(hours=4)),
            LeadTime(timedelta(hours=24)),
        ],
        hyperparams=XGBoostHyperParams(
            n_estimators=200,
            max_depth=6,
        ),
    )

    forecaster.fit(training_data)
    predictions = forecaster.predict(test_data)

The forecast output can then be compared against the transformer's rated capacity to derive a
**loading percentage** and flag periods where the upper quantile exceeds a safety threshold.

----

Free Space Estimation
---------------------

Free space estimation is the complement of congestion forecasting: rather than asking "will we
overload?", you ask "how much spare capacity is available to connect new loads or generators?" This
matters for grid connection decisions, where a DSO must commit to a contracted capacity months or
years in advance.

Because the question is about *remaining* capacity rather than *peak* load, the **lower quantiles
become safety-critical**. A connection decision based on the 50th percentile of free space could
result in congestion if actual load turns out higher than expected. Operators therefore use a
conservative lower quantile (e.g., 10th percentile of free space, equivalently the 90th percentile
of load) as the binding constraint.

In practice, free space is derived from the load forecast:

.. code-block:: python

    import pandas as pd

    # Assume `predictions` is a ForecastDataset with quantile columns
    # and `rated_capacity_mw` is the asset's thermal rating
    rated_capacity_mw = 40.0

    forecast_df = predictions.to_dataframe()

    # Free space at each quantile: capacity minus forecast load
    forecast_df["free_space_p10"] = rated_capacity_mw - forecast_df["q0.9"]
    forecast_df["free_space_p50"] = rated_capacity_mw - forecast_df["q0.5"]

    # Conservative available capacity: minimum free space over the horizon
    available_capacity = forecast_df["free_space_p10"].min()
    print(f"Conservative available capacity: {available_capacity:.1f} MW")

The forecaster configuration is identical to congestion management — the difference is entirely in
how you post-process the quantile outputs.

----

Grid Loss Forecasts
-------------------

Grid losses (the energy dissipated as heat in cables and transformers) represent a significant
operational cost for network operators. Forecasting losses accurately enables better procurement of
balancing energy and, crucially, allows errors to be weighted by real-time market prices: a 1 MWh
forecast error at €200/MWh costs ten times more than the same error at €20/MWh.

This use case has a distinctive statistical character. Because losses are measured at a highly
aggregated level — summed across an entire network — **temporal and cyclic patterns dominate**, and
weather predictors have less influence than in substation-level forecasts. The model sees strong
weekly seasonality, holiday effects, and load-level dependence, but the spatial averaging smooths
out local weather impacts.

**Primary metrics:** rMAE (overall accuracy), total error cost weighted by market prices.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Grid loss: balanced quantiles, longer horizons for procurement
    forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[
            LeadTime(timedelta(hours=1)),
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        hyperparams=XGBoostHyperParams(
            n_estimators=150,
            max_depth=5,
        ),
    )

Because losses are a derived quantity (not directly metered at every point), your
:class:`ForecastInputDataset` will typically contain aggregated loss measurements computed from
energy balance calculations. Ensure your training data covers multiple seasons to capture the
full range of load levels and temperature-dependent resistance effects.

.. note::

   Market-price weighting of forecast errors is not built into the standard loss functions.
   You can implement this by constructing a custom sample-weight array during training, where
   each sample's weight is proportional to the market price at that timestamp.

----

Transport Forecasts
-------------------

Transport forecasts serve a different audience from congestion management: they are produced for
**exchange with neighbouring network operators** rather than for internal operational decisions.
A DSO such as Alliander provides day-ahead transport forecasts to the transmission system operator
(TSO, e.g. TenneT) and receives equivalent forecasts from large industrial customers. These
forecasts must be accurate across the *entire* horizon, not just at peaks.

Some operators require transport forecasts **split by energy component** — separating solar
generation, wind generation, and residual demand. This requires either separate models per
component or a multi-output forecaster, with the component forecasts summed to produce the total.

**Primary metrics:** rMAE across all time steps. Reliability and consistency matter as much as
peak accuracy, because downstream operators build their own plans on top of these numbers.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Transport: symmetric quantiles, emphasis on overall accuracy
    forecaster = XGBoostForecaster(
        quantiles=[
            Quantile(0.1),
            Quantile(0.25),
            Quantile(0.5),
            Quantile(0.75),
            Quantile(0.9),
        ],
        horizons=[
            LeadTime(timedelta(hours=1)),
            LeadTime(timedelta(hours=6)),
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        hyperparams=XGBoostHyperParams(n_estimators=200, max_depth=6),
    )

For component-split transport forecasts, train a separate forecaster instance for each component
(solar, wind, other) using the corresponding measured component as the target column in each
:class:`ForecastInputDataset`.

----

District Heating Demand
-----------------------

District heating is an example of OpenSTEF being applied **outside the electricity domain**. The
target variable is thermal demand (heat load in MW or GJ/h) rather than electrical power, but the
forecasting problem is structurally identical: a time series with strong temperature dependence,
weekly seasonality, and holiday effects.

The main practical difference is that **weather features are more dominant** than in electricity
forecasting. Outdoor temperature, wind chill, and solar irradiance drive heating demand much more
directly than they drive aggregate electricity demand. You should ensure your feature set includes
high-quality temperature forecasts at multiple lead times.

.. code-block:: python

    import pandas as pd
    from openstef_core.datasets.validated_datasets import ForecastInputDataset

    # District heating input: thermal load + weather features
    # The target column is heat load (MW thermal), not electrical power
    heating_data = ForecastInputDataset(
        data=pd.DataFrame({
            "heat_load_mw": [...],          # target variable
            "temperature_c": [...],          # outdoor temperature forecast
            "wind_speed_ms": [...],          # wind chill effect
            "solar_irradiance_wm2": [...],   # solar gain on buildings
            "hour_of_day": [...],            # cyclic time features
            "day_of_week": [...],
        }),
        target_column="heat_load_mw",
    )

OpenSTEF makes no assumptions about the physical meaning of the target column, so no special
configuration is needed beyond choosing appropriate features. The same :class:`XGBoostForecaster`
used for electricity works directly for thermal demand.

----

MV Route Congestion with Topology Awareness
--------------------------------------------

Medium-voltage (MV) route congestion is the most technically complex use case. A single MV cable
route may serve multiple substations, and whether the route is congested depends not only on the
total load but on **how that load is distributed across the network topology**. This requires
combining OpenSTEF's probabilistic forecasts with a power flow solver.

The typical workflow is:

1. **Forecast load at each node** on the MV route using individual :class:`XGBoostForecaster`
   instances, one per substation or load point.
2. **Pass the forecast quantiles into a power flow model** (e.g., ``power-grid-model``, the
   open-source power flow library from LF Energy) to compute cable loading and voltage profiles
   for each scenario.
3. **Aggregate congestion risk** across the route by identifying time steps where any cable
   segment exceeds its rated current at the chosen quantile.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster

    # Step 1: one forecaster per MV node
    node_forecasters = {}
    for node_id, node_training_data in node_datasets.items():
        forecaster = XGBoostForecaster(
            quantiles=[Quantile(0.5), Quantile(0.9), Quantile(0.95)],
            horizons=[LeadTime(timedelta(hours=1)), LeadTime(timedelta(hours=4))],
        )
        forecaster.fit(node_training_data)
        node_forecasters[node_id] = forecaster

    # Step 2: collect forecasts for all nodes
    node_predictions = {
        node_id: forecaster.predict(node_test_data[node_id])
        for node_id, forecaster in node_forecasters.items()
    }

    # Step 3: pass P90 scenario into power-grid-model (illustrative)
    # power_flow_result = run_power_flow(
    #     topology=mv_network_topology,
    #     node_loads={nid: pred.to_dataframe()["q0.9"] for nid, pred in node_predictions.items()},
    # )

.. note::

   ``power-grid-model`` is a separate LF Energy project. OpenSTEF produces the probabilistic
   load forecasts; the power flow calculation is handled externally. The two libraries are
   designed to be composed, not bundled together.

The key insight for MV route congestion is that **you need correlated scenarios across nodes**,
not independent quantiles. If you use the 90th percentile independently at each node, you are
implicitly assuming all nodes peak simultaneously, which overstates congestion risk. A more
rigorous approach uses joint scenario sampling, which is an active area of development in the
OpenSTEF community.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the configuration differences across use cases:

+----------------------------+---------------------------+-----------------------------+---------------------+
| Use Case                   | Critical Quantiles        | Typical Horizons            | Primary Metric      |
+============================+===========================+=============================+=====================+
| Congestion management      | 0.9, 0.95                 | 1 h – 48 h                  | rMAE@peak, rCRPS    |
+----------------------------+---------------------------+-----------------------------+---------------------+
| Free space estimation      | 0.9, 0.95 (of load)       | 1 h – 48 h                  | rMAE@peak           |
+----------------------------+---------------------------+-----------------------------+---------------------+
| Grid loss                  | 0.1, 0.5, 0.9             | 1 h – 48 h                  | rMAE, cost-weighted |
+----------------------------+---------------------------+-----------------------------+---------------------+
| Transport                  | 0.1 – 0.9 (full range)    | 1 h – 48 h                  | rMAE (all periods)  |
+----------------------------+---------------------------+-----------------------------+---------------------+
| District heating           | 0.5, 0.9                  | 1 h – 24 h                  | rMAE                |
+----------------------------+---------------------------+-----------------------------+---------------------+
| MV route congestion        | 0.9, 0.95 per node        | 1 h – 4 h                   | rMAE@peak, rCRPS    |
+----------------------------+---------------------------+-----------------------------+---------------------+

A few rules of thumb:

- If your downstream decision is **triggered by a threshold** (overload, capacity limit), use a
  high quantile (0.9 or 0.95) as the decision input, not the median.
- If your downstream decision requires **overall accuracy** (reporting, billing, procurement),
  optimise for rMAE across all quantiles and all time steps.
- If your target variable has **strong price sensitivity**, consider weighting training samples
  by the cost of errors at each timestamp.
- If you are **new to a measurement point**, start with the :class:`BaseCaseForecaster` (a
  pattern-based baseline) to establish a benchmark before training a full XGBoost model.

----

Related Pages
-------------

- :doc:`data_integration` — how to load historical measurements and weather features from S3,
  Databricks, InfluxDB, and other sources into :class:`ForecastInputDataset`.
- :doc:`deployment` — production patterns for running multiple forecasters at scale (10,000+
  grid locations).
- :doc:`logging` — configuring structured logging for forecasting pipelines, including
  per-location log contexts useful when running many forecasters in parallel.