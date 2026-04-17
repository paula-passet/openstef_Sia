Common Use Cases
================

OpenSTEF has grown from a single congestion management tool into a library that supports a range of energy grid forecasting scenarios. This page describes the main use cases, what distinguishes each one, and how to configure OpenSTEF appropriately for each.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

---

Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case in OpenSTEF. The goal is to predict peak load at specific grid locations — substations, medium-voltage substations (MSRs), or even individual customers — so that grid operators can act before a cable or transformer is overloaded.

What makes this use case distinctive is that accuracy *near peaks* matters far more than average accuracy. A model that is excellent on quiet nights but misses a summer afternoon peak is not useful here. OpenSTEF therefore emphasises high-quantile accuracy and probabilistic forecasts: the 90th or 95th percentile of the forecast distribution is often the actionable number, not the median.

Aggregation levels vary widely. A substation serving thousands of customers is relatively predictable; a single industrial customer is not. At low aggregation, behavioural variability dominates and models must be robust to noisy targets.

**Key metrics:** precision and recall at peaks, rMAE at the 50th quantile during peak periods, rCRPS.

.. code-block:: python

    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    # High-quantile focus for congestion: include upper tail quantiles
    congestion_config = ForecastingWorkflowConfig(
        model_id="substation_A_congestion",
        model="xgboost",
        horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("P1D")],
        # Upper quantiles (P90, P95) drive the congestion alert threshold
        quantiles=[Q(0.05), Q(0.25), Q(0.50), Q(0.75), Q(0.90), Q(0.95)],
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        temperature_column="temperature_2m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "max"],
    )

The short horizon (``PT1H``) feeds real-time congestion alerts; the day-ahead horizon (``P1D``) supports scheduling of demand-response calls to customers.

.. note::

   XGBoost handles the nonlinear, spiky load profiles typical at low-aggregation points better than linear models. For highly aggregated substations, ``gblinear`` is a reasonable alternative and trains faster.

---

Free Space Estimation
---------------------

Free space estimation answers a related but different question: *how much remaining capacity is available on a cable or transformer right now, and in the near future?* Rather than predicting raw load, the output is the headroom between the current (or forecast) load and the physical limit of the asset.

In practice, free space is derived from a congestion forecast: you subtract the forecast load from the rated capacity of the asset. The probabilistic nature of OpenSTEF forecasts is especially valuable here — the lower bound of the free space (i.e., the upper bound of the load forecast) gives a conservative estimate of available capacity that can be offered to customers or used for flexibility dispatch.

.. code-block:: python

    import pandas as pd

    ASSET_CAPACITY_MW = 12.5  # Rated capacity of the transformer

    # `forecast` is a ForecastDataset returned by workflow.predict()
    forecast_df = forecast.data.copy()

    # Conservative free space: capacity minus the P90 load forecast
    forecast_df["free_space_mw"] = ASSET_CAPACITY_MW - forecast_df["quantile_P90"]

    # Optimistic free space: capacity minus the P50 load forecast
    forecast_df["free_space_p50_mw"] = ASSET_CAPACITY_MW - forecast_df["quantile_P50"]

    congestion_risk = forecast_df[forecast_df["free_space_mw"] < 0]
    print(f"Congestion risk periods: {len(congestion_risk)} timestamps")

The underlying ``ForecastingWorkflowConfig`` is identical to the congestion management setup above — the difference is entirely in how you interpret and post-process the output.

---

Grid Loss Forecasts
-------------------

Grid losses are the energy dissipated as heat in cables and transformers during transmission. Forecasting losses accurately has direct financial value: grid operators buy energy on the day-ahead market to cover expected losses, and errors translate directly into imbalance costs.

This use case operates at a much higher aggregation level than congestion management — typically the entire distribution network or a large region. At this scale, system-level temporal patterns (time of day, day of week, seasonal cycles) dominate, and weather predictors have less influence than they do for individual substations. Market prices become an important input because the cost of a forecast error depends on when it occurs.

**Key metrics:** rMAE, total error cost weighted by real-time market prices.

.. code-block:: python

    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    grid_loss_config = ForecastingWorkflowConfig(
        model_id="network_losses_region_north",
        model="gblinear",  # Linear model suits the smooth, aggregated signal
        horizons=[LeadTime.from_string("P1D"), LeadTime.from_string("P3D")],
        quantiles=[Q(0.10), Q(0.50), Q(0.90)],
        # Weather features still included but carry less weight at this scale
        radiation_column="shortwave_radiation",
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        # Market price as a feature: errors during high-price hours cost more
        energy_price_column="EPEX_NL",
        rolling_aggregate_features=["mean", "median", "max", "min"],
    )

Because the target signal is smoother and more predictable than individual substations, ``gblinear`` often matches or exceeds tree-based models here while being faster to train and more interpretable.

---

Transport Forecasts
-------------------

Transport forecasts serve a coordination function between network operators. A distribution system operator (DSO) like Alliander must report expected energy flows to the transmission system operator (TenneT) and, in turn, receives forecasts from large industrial customers. These forecasts cover medium-aggregation points — regional substations or high-voltage/medium-voltage interfaces — where load is predictable enough for reliable day-ahead and multi-day planning.

The distinguishing requirement for some operators is *component splitting*: the total load forecast must be decomposed into solar, wind, and residual (other) components. This requires separate models or a multi-output configuration for each component.

**Key metrics:** rMAE across the full forecast horizon.

.. code-block:: python

    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    # One config per component when split forecasts are required
    transport_solar_config = ForecastingWorkflowConfig(
        model_id="hv_substation_B_solar",
        model="xgboost",
        horizons=[LeadTime.from_string("P1D"), LeadTime.from_string("P3D")],
        quantiles=[Q(0.10), Q(0.50), Q(0.90)],
        radiation_column="shortwave_radiation",
        temperature_column="temperature_2m",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "median"],
    )

    transport_wind_config = ForecastingWorkflowConfig(
        model_id="hv_substation_B_wind",
        model="xgboost",
        horizons=[LeadTime.from_string("P1D"), LeadTime.from_string("P3D")],
        quantiles=[Q(0.10), Q(0.50), Q(0.90)],
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        temperature_column="temperature_2m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "median"],
    )

The total transport forecast is then the sum of the component forecasts. Keeping them separate allows each model to specialise on the feature interactions most relevant to its target.

---

District Heating Demand
-----------------------

District heating is an example of OpenSTEF being applied outside the electricity domain. The target variable is thermal demand (heat load in MW or GJ/h) rather than electrical load, but the forecasting problem is structurally identical: a time series of demand measurements, weather as the dominant external driver, and a need for short-term probabilistic forecasts to support dispatch decisions.

Temperature is by far the most important predictor for heat demand. Solar radiation matters for passive solar gains in buildings. Wind speed affects heat loss through building envelopes.

.. code-block:: python

    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    district_heating_config = ForecastingWorkflowConfig(
        model_id="district_heating_zone_3",
        model="xgboost",
        horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("P1D")],
        quantiles=[Q(0.10), Q(0.50), Q(0.90)],
        # Temperature is the dominant driver for heat demand
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        pressure_column="surface_pressure",
        relative_humidity_column="relative_humidity_2m",
        rolling_aggregate_features=["mean", "min"],
        # No energy price column — not relevant for heat dispatch in most setups
    )

.. note::

   Holiday calendars affect heat demand patterns differently from electricity demand. OpenSTEF 4.0 supports customisable holiday calendars to handle non-Dutch contexts and non-electricity domains correctly.

---

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most complex use case. Rather than forecasting load at a single measurement point, the goal is to determine whether a *path* through the grid — a sequence of cables connecting substations — will be overloaded. This requires combining OpenSTEF's load forecasts with a power flow model of the network topology.

The typical workflow is:

1. Produce load forecasts for each node on the MV route using OpenSTEF.
2. Feed those forecasts into `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, which solves the power flow equations for the network topology.
3. Extract the resulting cable loading percentages and flag routes where loading exceeds a threshold.

.. code-block:: python

    from openstef_models.presets import ForecastingWorkflowConfig
    from openstef_core.types import LeadTime, Quantile as Q

    # Step 1: one config per node on the MV route
    node_configs = [
        ForecastingWorkflowConfig(
            model_id=f"mv_node_{node_id}",
            model="xgboost",
            horizons=[LeadTime.from_string("PT1H"), LeadTime.from_string("P1D")],
            quantiles=[Q(0.50), Q(0.90), Q(0.95)],
            temperature_column="temperature_2m",
            radiation_column="shortwave_radiation",
            wind_speed_column="wind_speed_80m",
            pressure_column="surface_pressure",
            relative_humidity_column="relative_humidity_2m",
            rolling_aggregate_features=["mean", "max"],
        )
        for node_id in ["node_101", "node_102", "node_103"]
    ]

    # Step 2: collect P90 forecasts per node, then pass to power-grid-model
    # (power flow calculation is outside OpenSTEF's scope)

.. note::

   Power flow calculations with ``power-grid-model`` are outside OpenSTEF's scope. OpenSTEF provides the per-node load forecasts; ``power-grid-model`` handles the network physics. See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for how to set up the topology and run load flow calculations.

---

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case.

.. list-table::
   :header-rows: 1
   :widths: 22 18 20 20 20

   * - Use Case
     - Aggregation
     - Recommended Model
     - Critical Quantiles
     - Key Extra Feature
   * - Congestion management
     - Low–medium
     - ``xgboost``
     - P90, P95
     - —
   * - Free space estimation
     - Low–medium
     - ``xgboost``
     - P90, P95
     - Post-process from congestion forecast
   * - Grid losses
     - High
     - ``gblinear``
     - P50
     - ``energy_price_column``
   * - Transport
     - Medium
     - ``xgboost``
     - P50
     - Component splitting
   * - District heating
     - Medium
     - ``xgboost``
     - P50, P90
     - Custom holiday calendar
   * - MV route congestion
     - Low (per node)
     - ``xgboost``
     - P90, P95
     - ``power-grid-model`` topology

---

Related Pages
-------------

- :doc:`data_integration` — how to feed measurement and weather data into OpenSTEF from S3, Databricks, or InfluxDB.
- :doc:`deployment` — production deployment patterns for running forecasts at scale across thousands of grid locations.
- :doc:`migration_v3_v4` — if you are migrating existing congestion or transport forecast jobs from V3, see the breaking changes and updated API.