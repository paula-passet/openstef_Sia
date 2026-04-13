Common OpenSTEF Use Cases
=========================

OpenSTEF is a Python library designed for short-term energy forecasting, and while its core machinery
is general-purpose, it has been shaped by a concrete set of real-world problems that grid operators
face daily. This page describes the most common use cases, what distinguishes each one, and how to
configure the library appropriately for each scenario.

.. note:: [DIAGRAM: Use case overview showing the six forecasting scenarios (congestion management,
   free space estimation, grid loss, transport, district heating, MV route congestion) arranged around
   a central OpenSTEF library core. Each scenario shows its primary input data types (load measurements,
   weather, topology) on the left and its output applications (congestion alerts, capacity planning,
   market optimisation, TSO reporting) on the right.]

----

Overview
--------

The table below summarises the key characteristics of each use case at a glance.

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Use Case
     - Aggregation Level
     - Primary Metric
     - Key Distinguishing Factor
   * - Congestion management
     - Low to high (variable)
     - rMAE@peak, rCRPS
     - Peak accuracy, high-quantile precision
   * - Free space estimation
     - Asset level
     - Exceedance probability
     - Derived from congestion forecast + rated capacity
   * - Grid loss forecasting
     - Highly aggregated
     - rMAE + cost-weighted error
     - Market-price error weighting
   * - Transport forecasts
     - Medium aggregated
     - rMAE
     - Reliability across full horizon
   * - District heating
     - Building/district level
     - rMAE
     - Thermal demand, non-electrical domain
   * - MV route congestion
     - Route / feeder level
     - rMAE@peak
     - Topology-aware via power-grid-model

----

Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case in OpenSTEF. The goal is to predict
peak load moments on transformers and cables so that a grid operator can intervene before an asset
is overloaded — for example by calling customers to reduce consumption or by pre-emptively rerouting
power flows.

What makes this use case technically demanding is the variability in aggregation level. A high-voltage
substation aggregates thousands of customers and is relatively predictable; an individual medium-voltage
connection or a single industrial customer can be highly erratic. OpenSTEF handles both, but the model
configuration and the metrics that matter differ significantly between them.

**What to optimise for:** Accuracy near peak load periods. A forecast that is accurate on average but
consistently underestimates peaks is worse than useless for congestion management — it gives a false
sense of security. The relevant metrics are the rMAE evaluated at the 50th quantile during peak hours
and the rCRPS (Continuous Ranked Probability Score) across the full predictive distribution.

**Recommended model:** ``XGBoostForecaster`` with a wide quantile set. The high quantiles (0.9, 0.95)
are used to trigger congestion alerts conservatively; the median (0.5) drives operational planning.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster, XGBoostHyperParams

    # Congestion management: wide quantile range to capture tail risk
    forecaster = XGBoostForecaster(
        quantiles=[
            Quantile(0.05),
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

    forecaster.fit(training_data)  # training_data: pd.DataFrame with load + weather features
    predictions = forecaster.predict(test_data)

The ``predictions`` DataFrame will contain one column per quantile. Downstream logic can then compare
the 95th-percentile forecast against the rated capacity of the asset to determine whether a congestion
alert should be raised.

.. note::

   At very low aggregation levels (individual customers or small MSRs), behavioural variability can
   dominate the signal. Consider using ``FlatlinerForecaster`` as a fallback for assets that show
   near-constant load profiles, and evaluate whether the forecast adds value over a simple persistence
   baseline before deploying.

----

Free Space Estimation
---------------------

Free space estimation answers the question: *how much remaining capacity does this asset have right
now, and how much will it have tomorrow?* It is a direct downstream application of a congestion
management forecast — you take the probabilistic load forecast and subtract it from the asset's rated
capacity.

.. code-block:: python

    import pandas as pd

    RATED_CAPACITY_MW = 10.0  # transformer or cable rating

    # predictions is the output of forecaster.predict(), indexed by timestamp
    # Use the 90th-percentile forecast for a conservative free-space estimate
    free_space = RATED_CAPACITY_MW - predictions["quantile_0.90"]

    # Flag hours where free space drops below a safety margin
    congestion_risk = free_space[free_space < 0.5]  # less than 0.5 MW headroom

Because free space is derived rather than directly modelled, the accuracy of the underlying load
forecast is paramount. The same ``XGBoostForecaster`` configuration used for congestion management
applies here. The choice of which quantile to use for the subtraction is a business decision: a
conservative operator might use the 95th percentile, while a capacity-trading application might use
the median.

**Typical horizon:** 24–48 hours ahead, updated every 15 minutes as new measurements arrive.

----

Grid Loss Forecasting
---------------------

Grid losses — the energy dissipated as heat in cables and transformers — are a financial cost that
grid operators must procure on the energy market. Forecasting losses accurately allows operators to
buy the right amount of energy in advance and minimise imbalance costs.

This use case is technically different from congestion management in two important ways:

1. **High aggregation.** Losses are measured at the system level, where temporal and cyclic patterns
   (time of day, day of week, seasonal load cycles) dominate. Weather predictors have much less
   influence than at individual asset level.

2. **Cost-weighted errors.** A forecast error at a high electricity price hour costs more than the
   same error at a low-price hour. The model should be optimised with market-price-weighted loss
   functions rather than uniform MAE.

.. code-block:: python

    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.gblinear_forecaster import (
        GBLinearForecaster,
        GBLinearHyperParams,
    )

    # Grid loss: linear model often performs well at high aggregation levels
    # where the load-loss relationship is approximately quadratic but smooth
    forecaster = GBLinearForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime.from_string("P1D"), LeadTime.from_string("P3D")],
        hyperparams=GBLinearHyperParams(
            learning_rate=0.05,
            reg_alpha=0.1,
            reg_lambda=1.0,
        ),
    )

    forecaster.fit(training_data)
    predictions = forecaster.predict(test_data)

**Input features to include:** Total system load (aggregated), day-ahead electricity market prices,
time-of-day and day-of-week cyclical encodings, ambient temperature (affects cable resistance).
Market prices should be included as a feature rather than used only in post-hoc evaluation so the
model can learn price-correlated loss patterns.

----

Transport Forecasts
-------------------

Transport forecasts serve a different master than congestion forecasts: they are communicated to
upstream and downstream network operators for coordinated capacity planning. A distribution system
operator (DSO) like Alliander provides transport forecasts to the transmission system operator
(TenneT), while simultaneously receiving forecasts from its large industrial customers.

The accuracy requirement here is uniform across the full forecast horizon — there is no special
emphasis on peaks. The relevant metric is rMAE averaged over all time steps. Some operators also
require forecasts decomposed into components (solar generation, wind generation, residual load),
which means running separate models for each component and combining the outputs.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster, XGBoostHyperParams

    # Transport forecast: medium quantile set, emphasis on median accuracy
    forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
            LeadTime(timedelta(days=3)),
        ],
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    forecaster.fit(training_data)
    transport_forecast = forecaster.predict(test_data)

**Split-component transport forecasts:** If your operator requires solar, wind, and residual
components separately, train one forecaster per component using the appropriate weather features
(irradiance for solar, wind speed at hub height for wind) and sum the predictions to produce the
total transport forecast. Verify that the sum of components matches a direct total-load forecast
before reporting — discrepancies indicate data quality issues.

----

District Heating Demand
-----------------------

District heating is a community use case that extends OpenSTEF beyond its electrical roots. The
target variable is thermal demand (heat delivered to buildings) rather than electrical load, but the
forecasting problem is structurally identical: a time-series target driven by weather, time patterns,
and calendar effects.

The key differences from electrical forecasting are:

- **Temperature sensitivity is stronger and non-linear.** Heating demand drops sharply above a
  comfort threshold (typically around 15–18 °C) and is near-zero in summer. Including a
  heating-degree-day feature or a piecewise temperature feature improves accuracy significantly.
- **No solar or wind features are needed** unless the district heating network includes solar thermal
  collectors.
- **Demand is always non-negative** and often has a hard lower bound (minimum circulation flow).

.. code-block:: python

    import pandas as pd
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster, XGBoostHyperParams

    # Add a heating degree day feature before training
    COMFORT_TEMP = 16.0  # degrees Celsius
    training_data["heating_degree_hours"] = (
        COMFORT_TEMP - training_data["temperature_2m"]
    ).clip(lower=0.0)

    forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime.from_string("PT6H"), LeadTime.from_string("PT24H")],
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    forecaster.fit(training_data)
    heat_demand_forecast = forecaster.predict(test_data)

.. note::

   District heating is an evolving use case in OpenSTEF. The library provides all the necessary
   building blocks, but there is no domain-specific preprocessing pipeline for thermal networks yet.
   Contributions are welcome.

----

MV Route Congestion with Topology Awareness
--------------------------------------------

Medium-voltage (MV) route congestion is the most technically complex use case. A single MV feeder
(route) connects multiple substations and customers in a chain or ring topology. The load on any
cable segment depends on the aggregate of all customers downstream of that segment — a fact that a
naive per-asset forecast ignores.

The ``power-grid-model`` library (a separate open-source project from the same LF Energy ecosystem)
provides topology-aware power flow calculations. The pattern is:

1. **Forecast load at each node** using OpenSTEF's standard forecasting pipeline.
2. **Feed the node forecasts into power-grid-model** to compute power flows on each cable segment.
3. **Compare segment flows against rated capacities** to identify which cable segments are at risk.

.. code-block:: python

    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster, XGBoostHyperParams

    # Step 1: Train one forecaster per MV node (substation or large customer)
    node_forecasters = {}
    for node_id, node_data in mv_node_datasets.items():
        forecaster = XGBoostForecaster(
            quantiles=[Quantile(0.5), Quantile(0.9), Quantile(0.95)],
            horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("PT24H")],
            hyperparams=XGBoostHyperParams(n_estimators=100, max_depth=5),
        )
        forecaster.fit(node_data["train"])
        node_forecasters[node_id] = forecaster

    # Step 2: Generate node-level predictions
    node_predictions = {
        node_id: fc.predict(mv_node_datasets[node_id]["test"])
        for node_id, fc in node_forecasters.items()
    }

    # Step 3: Pass node_predictions to power-grid-model for topology-aware
    # power flow calculation — see the power-grid-model documentation for
    # the batch power flow API.

.. note::

   ``power-grid-model`` is not a dependency of OpenSTEF. Install it separately
   (``pip install power-grid-model``) and refer to its own documentation for the
   power flow calculation API. OpenSTEF's role is to produce the per-node load
   forecasts; topology resolution is handled entirely by ``power-grid-model``.

The main practical challenge in this use case is data alignment: every node must produce forecasts
on the same timestamp grid, and missing data at any node propagates into the power flow calculation.
Robust imputation and a ``FlatlinerForecaster`` fallback for nodes with sparse data are strongly
recommended.

----

Choosing the Right Configuration
---------------------------------

The table below maps each use case to the recommended forecaster and the most important configuration
choices.

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Use Case
     - Recommended Forecaster
     - Key Configuration Notes
   * - Congestion management
     - ``XGBoostForecaster``
     - Wide quantile set (0.05–0.95); 24–48 h horizons; tune ``max_depth`` per aggregation level
   * - Free space estimation
     - Same as congestion
     - Post-process: subtract high-quantile forecast from rated capacity
   * - Grid loss
     - ``GBLinearForecaster``
     - Include market price as feature; consider cost-weighted evaluation
   * - Transport
     - ``XGBoostForecaster``
     - Narrow quantile set (0.1, 0.5, 0.9); up to 3-day horizon; split-component if required
   * - District heating
     - ``XGBoostForecaster``
     - Add heating-degree-hour feature; exclude solar/wind features
   * - MV route congestion
     - ``XGBoostForecaster`` per node
     - Align timestamp grids across nodes; use ``FlatlinerForecaster`` as fallback

----

Related Pages
-------------

- :doc:`data_integration` — How to read load measurements and weather data from S3, Databricks,
  and InfluxDB to feed the forecasting pipelines described on this page.
- :doc:`deployment` — Production deployment patterns for running these use cases at scale,
  including scheduling, model storage, and monitoring.
- :doc:`logging` — Configuring structured logging for forecasting pipelines, including how to
  surface per-use-case metrics in your observability stack.