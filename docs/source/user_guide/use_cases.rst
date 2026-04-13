Common Use Cases
================

OpenSTEF is a general-purpose forecasting library, but its design was shaped by a specific family of
problems: grid operators need to know *what will happen on their network* before it happens. This page
walks through the most common forecasting scenarios the library supports, explaining what makes each one
distinct, which model settings work well, and how to configure them in code.

.. note:: [DIAGRAM: Use case overview — six forecasting scenarios arranged around a central OpenSTEF
   library core. Each scenario shows its primary input data types (smart meter readings, weather,
   market prices, topology) on the left and its downstream application (congestion alerts, capacity
   planning, financial settlement, heating dispatch) on the right. Arrows indicate data flow direction.]

The six scenarios covered here are:

- :ref:`congestion-forecasts` — transformer and cable loading at substations
- :ref:`free-space-estimation` — remaining headroom before a thermal limit is reached
- :ref:`grid-loss-forecasts` — system losses for financial optimisation
- :ref:`transport-forecasts` — aggregate flows reported to upstream operators
- :ref:`district-heating` — thermal demand for non-electricity networks
- :ref:`mv-route-congestion` — topology-aware congestion using power-grid-model

Each scenario uses the same core library API. What differs is the optimisation target, the quantiles
that matter, and — for MV route congestion — how individual point forecasts are composed.

.. _congestion-forecasts:

Congestion Forecasts (Transformer and Cable Loading)
-----------------------------------------------------

Congestion management is the original motivation for OpenSTEF and remains the most widely deployed use
case. At Alliander, the library currently produces forecasts for more than 10,000 grid locations daily
to support congestion management operations.

The goal is to predict whether a transformer or cable will exceed its thermal rating during the upcoming
hours or days. Because the cost of a missed peak far outweighs the cost of a false alarm, the model
must be accurate *near the top of the load distribution*, not just on average.

**What makes this use case distinct:**

- Aggregation level varies enormously — from a high-voltage substation serving thousands of customers
  to a single medium-voltage connection point (MSR). Low-aggregation points are inherently noisier.
- The relevant error metric is peak-weighted: rMAE at the 50th quantile during peak periods, plus the
  ranked Continuous Ranked Probability Score (rCRPS) to evaluate the full predictive distribution.
- High quantiles (0.9, 0.95) are operationally critical because they drive congestion alerts.

**Recommended configuration:**

Emphasise high-quantile accuracy and use a wide quantile set so that downstream systems can choose
their own risk threshold.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Wide quantile set — high quantiles drive congestion alerts
    congestion_quantiles = [
        Quantile(0.05),
        Quantile(0.1),
        Quantile(0.3),
        Quantile(0.5),
        Quantile(0.7),
        Quantile(0.9),
        Quantile(0.95),
    ]

    forecaster = XGBoostForecaster(
        quantiles=congestion_quantiles,
        horizons=[
            LeadTime(timedelta(hours=24)),
            LeadTime(timedelta(hours=48)),
        ],
        hyperparams=XGBoostHyperParams(
            n_estimators=200,
            max_depth=6,
        ),
    )

The 0.9 and 0.95 quantile outputs are what a congestion management system will typically threshold
against the rated capacity of the asset.

.. _free-space-estimation:

Free Space Estimation (Remaining Capacity)
------------------------------------------

Free space estimation answers a slightly different question than congestion forecasting: not "will this
asset overload?" but "how much headroom remains?". This is used for capacity planning — for example,
deciding whether a new large customer connection can be accepted without reinforcement works.

Operationally, free space is derived directly from a congestion forecast:

.. code-block:: python

    import pandas as pd

    # rated_capacity_mw: the thermal limit of the asset in MW
    # forecast_df: DataFrame with quantile columns from the forecaster
    rated_capacity_mw = 12.5

    forecast_df["free_space_p50"] = rated_capacity_mw - forecast_df["quantile_0.50"]
    forecast_df["free_space_p90"] = rated_capacity_mw - forecast_df["quantile_0.90"]

    # Negative free space at p90 indicates a congestion risk
    congestion_risk = forecast_df["free_space_p90"] < 0

Because free space is a linear transformation of the load forecast, the model configuration is
identical to the congestion case. The distinction is entirely in how the output is interpreted and
presented to downstream consumers.

.. note::

   Free space estimates at high quantiles are conservative by design. A negative free space at the
   0.9 quantile means the asset has a roughly 10 % chance of exceeding its rating during that interval,
   not that it will definitely overload.

.. _grid-loss-forecasts:

Grid Loss Forecasts
-------------------

Grid losses are the difference between energy injected into a network and energy consumed by end users.
Losses arise from resistive heating in cables and transformers and are a real operating cost. Forecasting
them accurately enables grid operators to purchase the right amount of balancing energy on the market
ahead of time, minimising settlement costs.

**What makes this use case distinct:**

- Losses are measured at a highly aggregated level, so individual behavioural noise averages out.
  Temporal and cyclic patterns (time of day, day of week, season) dominate the signal.
- Weather predictors have diminished importance compared to congestion forecasting.
- The error metric includes a cost dimension: errors during high-price intervals are more expensive
  than errors during low-price intervals, so the model should be weighted accordingly.
- The optimisation target is total error cost, not just rMAE.

**Recommended configuration:**

A linear gradient boosting model (``GBLinearForecaster``) often performs well here because the
relationship between load patterns and losses is approximately linear at high aggregation. The
``GBLinearForecaster`` also extrapolates more predictably beyond the training range, which matters
when market conditions shift.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.gblinear_forecaster import (
        GBLinearForecaster,
        GBLinearHyperParams,
    )

    loss_forecaster = GBLinearForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
        hyperparams=GBLinearHyperParams(
            learning_rate=0.05,
            reg_alpha=0.1,
            reg_lambda=1.0,
        ),
    )

When integrating market price data, pass it as an additional feature column in your training
DataFrame. The library treats it as any other exogenous predictor.

.. _transport-forecasts:

Transport Forecasts
-------------------

Transport forecasts describe the aggregate energy flow across a network boundary over a future period.
They are exchanged between operators at different levels of the grid hierarchy: a distribution system
operator (DSO) like Alliander provides transport forecasts to the transmission system operator (TSO,
e.g. TenneT), and in turn receives similar forecasts from large industrial customers connected to its
network.

**What makes this use case distinct:**

- The aggregation level is medium — higher than a single MSR, lower than national totals. This gives
  a good balance between predictability and granularity.
- Accuracy is required across the *entire* forecast horizon, not just at peaks. The primary metric
  is rMAE across all time steps.
- Some operators need the forecast decomposed into generation components (solar, wind, residual load).
  This requires training separate component models and summing their outputs.

**Recommended configuration:**

A standard XGBoost forecaster with a moderate quantile set works well. For component decomposition,
train one forecaster per component and combine predictions:

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    transport_quantiles = [Quantile(0.1), Quantile(0.5), Quantile(0.9)]
    horizons = [LeadTime(timedelta(days=1)), LeadTime(timedelta(days=3))]

    # One forecaster per component
    solar_forecaster = XGBoostForecaster(
        quantiles=transport_quantiles,
        horizons=horizons,
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    wind_forecaster = XGBoostForecaster(
        quantiles=transport_quantiles,
        horizons=horizons,
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    residual_forecaster = XGBoostForecaster(
        quantiles=transport_quantiles,
        horizons=horizons,
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    # After fitting and predicting each component, combine:
    # total_p50 = solar_p50 + wind_p50 + residual_p50

.. note::

   Quantile combination by simple addition is only valid when the components are independent. If
   solar and wind are correlated at your location, consider summing the raw predictions before
   computing quantiles, or use a copula-based approach.

.. _district-heating:

District Heating Demand
-----------------------

District heating is a community use case that extends OpenSTEF beyond electricity networks. A district
heating operator needs to forecast thermal demand — the heat load that will be drawn from a central
plant or network — to schedule generation and avoid under- or over-supply.

The forecasting problem is structurally similar to electrical load forecasting:

- The target variable is thermal power (MW) or energy (MWh) rather than electrical power.
- Weather is a dominant predictor, but the relevant variable is outdoor temperature (and sometimes
  solar irradiance for passive solar gains), not wind speed.
- Temporal patterns (morning warm-up, overnight setback, weekday/weekend) are strong.

Because OpenSTEF is a general-purpose library, using it for district heating requires no special
configuration — you simply supply a DataFrame with thermal load as the target and temperature as a
feature:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # training_data: DataFrame with columns including
    #   'load'              — measured thermal demand in MW
    #   'temperature_2m'    — outdoor air temperature in °C
    #   'hour', 'dayofweek' — temporal features (or use OpenSTEF feature engineering)

    heating_forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
        hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
    )

    heating_forecaster.fit(training_data)  # training_data is a pandas DataFrame

The library's built-in feature engineering pipeline handles lag features and rolling aggregates
automatically, which is particularly valuable for thermal demand where recent load history is a strong
predictor of near-term demand.

.. _mv-route-congestion:

MV Route Congestion with power-grid-model
------------------------------------------

Medium-voltage (MV) route congestion is the most topologically complex use case. A single MV cable
route may serve dozens of connection points, and the load on any segment of that route is the *sum*
of loads at all connection points downstream of that segment. Identifying which segment will congest
first requires knowing both the individual loads and the network topology.

OpenSTEF addresses this by combining point-level load forecasts with the
`power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_ library for topology-aware
power flow calculations.

**The workflow has three stages:**

1. **Forecast each connection point independently** using a standard OpenSTEF forecaster.
2. **Compose route loads** by feeding the individual forecasts into power-grid-model, which propagates
   them through the network topology to compute cable segment loadings.
3. **Identify congestion** by comparing segment loadings against their rated capacities.

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from openstef_core.types import LeadTime, Quantile
    from openstef_models.models.forecasting.xgboost_forecaster import (
        XGBoostForecaster,
        XGBoostHyperParams,
    )

    # Step 1: Train a forecaster for each connection point
    # connection_data: dict mapping connection_id -> training DataFrame
    connection_ids = ["cp_001", "cp_002", "cp_003"]
    forecasters = {}

    point_quantiles = [Quantile(0.5), Quantile(0.9), Quantile(0.95)]
    horizons = [LeadTime(timedelta(hours=4)), LeadTime(timedelta(hours=24))]

    for cid in connection_ids:
        f = XGBoostForecaster(
            quantiles=point_quantiles,
            horizons=horizons,
            hyperparams=XGBoostHyperParams(n_estimators=100, max_depth=5),
        )
        f.fit(connection_data[cid])
        forecasters[cid] = f

    # Step 2: Generate point forecasts
    point_forecasts = {
        cid: forecasters[cid].predict(future_features[cid])
        for cid in connection_ids
    }

    # Step 3: Pass point_forecasts into power-grid-model for topology-aware
    # load flow calculation — see power-grid-model documentation for details.
    # The result is per-segment loading as a fraction of rated capacity.

.. note::

   The power-grid-model integration is not bundled with OpenSTEF itself. You need to install
   ``power-grid-model`` separately and maintain a network model (nodes, branches, rated capacities)
   for your MV routes. OpenSTEF's role is to produce the per-connection-point probabilistic forecasts
   that feed into the power flow solver.

**Why use the 0.9 or 0.95 quantile for route congestion?**

When you sum independent probabilistic forecasts across many connection points, the aggregate
distribution narrows relative to the individual distributions (by the law of large numbers). However,
connection points on the same MV route are *not* independent — they share weather exposure and
customer behaviour patterns. Using the 0.9 quantile at the point level provides a conservative but
not extreme estimate of route loading.

Choosing the Right Configuration
---------------------------------

The table below summarises the key differences between use cases to help you select the right
settings quickly.

+------------------------------+------------------+-----------------------------+---------------------------+
| Use Case                     | Aggregation      | Key Metric                  | Recommended Model         |
+==============================+==================+=============================+===========================+
| Congestion (substation)      | Low–medium       | rMAE at peaks, rCRPS        | XGBoostForecaster         |
+------------------------------+------------------+-----------------------------+---------------------------+
| Free space estimation        | Low–medium       | Derived from congestion     | XGBoostForecaster         |
+------------------------------+------------------+-----------------------------+---------------------------+
| Grid loss                    | High             | rMAE + cost-weighted error  | GBLinearForecaster        |
+------------------------------+------------------+-----------------------------+---------------------------+
| Transport                    | Medium           | rMAE across horizon         | XGBoostForecaster         |
+------------------------------+------------------+-----------------------------+---------------------------+
| District heating             | Medium           | rMAE                        | XGBoostForecaster         |
+------------------------------+------------------+-----------------------------+---------------------------+
| MV route congestion          | Low (per point)  | Segment loading fraction    | XGBoostForecaster + PGM   |
+------------------------------+------------------+-----------------------------+---------------------------+

As a general rule: use ``GBLinearForecaster`` when the signal is highly aggregated and you expect
linear relationships to dominate, or when you need reliable extrapolation beyond the training range.
Use ``XGBoostForecaster`` for everything else — it handles non-linearities and interaction effects
that are common at lower aggregation levels.

For production deployment patterns that apply to all of these use cases, see :doc:`deployment`.
For guidance on feeding data from S3, Databricks, or InfluxDB into your forecasting pipeline, see
:doc:`data_integration`.