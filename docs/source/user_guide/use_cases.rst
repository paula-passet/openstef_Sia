Use Cases
=========

OpenSTEF is used across a range of grid-management scenarios, each with different accuracy requirements, data characteristics, and model configurations. This page walks through the most common use cases — what distinguishes them, when to reach for each, and how to configure OpenSTEF accordingly.

.. note:: [DIAGRAM: Use case overview showing the five forecasting scenarios (Congestion, Free Space, Grid Loss, Transport, District Heating / MV Route) as nodes, each annotated with its primary input data types (load history, weather, topology, market prices) and output applications (peak alerts, capacity headroom, cost optimisation, TSO reporting, thermal demand)]

---

Congestion Forecasts
--------------------

Congestion forecasting predicts load at individual grid assets — transformers, cables, medium-voltage substations — so that operators can act before an overload occurs. Because the forecast must be accurate *near peak moments*, the model is optimised for high-quantile precision rather than average error.

**What makes it different**

- Low aggregation: individual assets can be highly unpredictable due to behavioural variability.
- The business question is binary: *will this asset exceed its rated capacity in the next 48 hours?*
- Key metrics are rMAE at the 50th quantile during peaks and rCRPS; overall MAE is less important.

**Typical configuration**

Use XGBoost with a wide quantile set so that the upper tail (Q90, Q95) is well-calibrated. A 48-hour horizon covers the operational response window.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile as Q
    from openstef.workflow.config import ForecastingWorkflowConfig

    congestion_config = ForecastingWorkflowConfig(
        model_id="transformer_hv_mv_001",
        model="xgboost",
        # 48-hour horizon — enough lead time for demand-response activation
        horizons=[LeadTime.from_string("P2D")],
        # Wide quantile set: upper tail drives congestion alerts
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
        model_reuse_enable=True,
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        temperature_column="temperature_2m",
        rolling_aggregate_features=["mean", "median", "max", "min"],
    )

.. note::

   At very low aggregation levels (single customers, small MSRs) training data is often sparse and noisy.
   Set ``training_context_min_coverage`` conservatively and consider ``GBLinearForecaster`` as a fallback
   when XGBoost overfits.

---

Free Space Estimation
---------------------

Free space (remaining capacity) is the complement of congestion: instead of asking *will the asset overload?*, the question is *how much headroom is left?* This is used for connection-capacity decisions and for communicating available capacity to market parties.

Free space is derived from a congestion forecast — you subtract the upper-quantile load forecast from the asset's rated capacity. The configuration is therefore almost identical to a congestion forecast, but the *consumer* of the output is different (capacity planning rather than real-time operations).

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile as Q
    from openstef.workflow.config import ForecastingWorkflowConfig

    free_space_config = ForecastingWorkflowConfig(
        model_id="cable_lv_mv_042",
        model="xgboost",
        horizons=[LeadTime.from_string("P7D")],   # Longer horizon for planning
        quantiles=[Q(0.05), Q(0.1), Q(0.5), Q(0.9), Q(0.95)],
        model_reuse_enable=True,
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        rolling_aggregate_features=["mean", "median", "max", "min"],
    )

    # Downstream: free_space = rated_capacity_mw - forecast_q95

After generating forecasts, compute headroom in your application layer:

.. code-block:: python

    rated_capacity_mw = 10.0  # asset nameplate rating

    # predictions is a DataFrame with columns like "forecast_q0.95"
    predictions["free_space_mw"] = rated_capacity_mw - predictions["forecast_q0.95"]

---

Grid Loss Forecasts
-------------------

Grid losses are the difference between energy injected into the grid and energy delivered to customers. Forecasting losses matters financially: grid operators buy energy on the day-ahead market to cover losses, so forecast errors translate directly into cost.

**What makes it different**

- Highly aggregated: system-level temporal patterns (time-of-day, day-of-week, seasonal cycles) dominate over weather.
- Market prices introduce an asymmetric cost function — over-procurement and under-procurement have different financial consequences.
- Key metric: total error cost weighted by real-time market prices, in addition to rMAE.

Because the signal is smooth and aggregated, ``GBLinearForecaster`` often performs comparably to XGBoost while being less prone to overfitting on temporal artefacts.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile as Q
    from openstef.workflow.config import ForecastingWorkflowConfig

    grid_loss_config = ForecastingWorkflowConfig(
        model_id="grid_loss_region_north",
        model="gblinear",          # Linear model suits aggregated, smooth signal
        horizons=[LeadTime.from_string("P1D")],
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
        model_reuse_enable=True,
        # Weather features matter less here; energy price is the key external driver
        energy_price_column="EPEX_NL",
        temperature_column="temperature_2m",
        rolling_aggregate_features=["mean", "median", "max", "min"],
    )

.. note::

   If your market area uses a different price signal, replace ``energy_price_column`` with the
   appropriate column name in your input DataFrame. OpenSTEF treats it as a standard feature.

---

Transport Forecasts
-------------------

Transport forecasts report expected energy flows to upstream transmission system operators (TSOs) and receive similar forecasts from downstream customers. Alliander, for example, provides transport forecasts to TenneT while receiving them from large industrial customers.

**What makes it different**

- Medium aggregation: more predictable than individual assets, less smooth than system-level losses.
- Balanced accuracy across the *entire* forecast horizon matters, not just peaks.
- Some operators require component-split forecasts (solar contribution, wind contribution, residual load) — this requires separate models per component that are later recombined.
- Key metric: rMAE across all time steps.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile as Q
    from openstef.workflow.config import ForecastingWorkflowConfig

    # Main transport forecast
    transport_config = ForecastingWorkflowConfig(
        model_id="transport_substation_A",
        model="xgboost",
        horizons=[LeadTime.from_string("P3D")],
        quantiles=[Q(0.05), Q(0.1), Q(0.3), Q(0.5), Q(0.7), Q(0.9), Q(0.95)],
        model_reuse_enable=True,
        radiation_column="shortwave_radiation",
        wind_speed_column="wind_speed_80m",
        temperature_column="temperature_2m",
        rolling_aggregate_features=["mean", "median", "max", "min"],
    )

    # Component split: solar model (same asset, solar-only target)
    solar_component_config = ForecastingWorkflowConfig(
        model_id="transport_substation_A_solar",
        model="xgboost",
        horizons=[LeadTime.from_string("P3D")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        model_reuse_enable=True,
        radiation_column="shortwave_radiation",
        rolling_aggregate_features=["mean", "max"],
    )

---

District Heating Demand
-----------------------

District heating is a non-electricity use case: the target variable is thermal demand (heat load in MW or GJ/h) rather than electrical load. The forecasting problem is structurally similar — time series regression with weather features — but the dominant driver shifts from solar irradiance and wind to outdoor temperature and heating degree days.

OpenSTEF's model-agnostic design means you can apply the same ``XGBoostForecaster`` or ``GBLinearForecaster`` to thermal demand data with minimal changes to the configuration.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile as Q
    from openstef.workflow.config import ForecastingWorkflowConfig

    district_heating_config = ForecastingWorkflowConfig(
        model_id="district_heating_zone_3",
        model="xgboost",
        horizons=[LeadTime.from_string("P2D")],
        quantiles=[Q(0.1), Q(0.5), Q(0.9)],
        model_reuse_enable=True,
        # Temperature is the primary driver for heat demand
        temperature_column="temperature_2m",
        # Wind chill effect
        wind_speed_column="wind_speed_80m",
        rolling_aggregate_features=["mean", "median", "min"],
        # Solar and radiation columns can be omitted or left as None
    )

.. note::

   District heating targets are typically strictly non-negative. If your training data contains
   negative values (measurement artefacts), clean them before fitting — OpenSTEF does not
   enforce non-negativity constraints on predictions by default.

---

MV Route Congestion with Power-Grid-Model Topology
---------------------------------------------------

Medium-voltage (MV) route congestion combines OpenSTEF load forecasts with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_ topology calculations. The idea is that a single MV feeder serves multiple nodes; congestion on the *route* depends on the *sum* of loads along that route, which is determined by the network topology.

**Workflow**

1. Produce individual node-level load forecasts using OpenSTEF (one ``ForecastingWorkflowConfig`` per node).
2. Pass the forecasts and the network topology to ``power-grid-model`` to compute line loadings.
3. Flag routes where the upper-quantile line loading exceeds the cable's rated current.

.. code-block:: python

    from datetime import timedelta
    from openstef_core.types import LeadTime, Quantile as Q
    from openstef.workflow.config import ForecastingWorkflowConfig

    # Step 1: one config per MV node (repeat for each node on the route)
    node_config = ForecastingWorkflowConfig(
        model_id="mv_node_feeder7_node12",
        model="xgboost",
        horizons=[LeadTime.from_string("P2D")],
        quantiles=[Q(0.5), Q(0.9), Q(0.95)],   # Upper tail for congestion check
        model_reuse_enable=True,
        temperature_column="temperature_2m",
        radiation_column="shortwave_radiation",
        rolling_aggregate_features=["mean", "max"],
    )

    # Step 2 & 3: aggregate forecasts per route using power-grid-model
    # (topology-aware load flow calculation — see power-grid-model documentation)

.. note::

   MV route congestion is the most infrastructure-intensive use case. Node-level forecasts can be
   produced in parallel across thousands of assets; the topology calculation is then a lightweight
   post-processing step. See the :doc:`deployment` page for parallelisation patterns.

---

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices across use cases.

+------------------------------+------------+-------------------+-------------------+------------------------------+
| Use case                     | Model      | Horizon           | Quantile focus    | Key feature columns          |
+==============================+============+===================+===================+==============================+
| Congestion (transformer)     | xgboost    | P2D               | Q90, Q95          | temperature, radiation, wind |
+------------------------------+------------+-------------------+-------------------+------------------------------+
| Free space estimation        | xgboost    | P7D               | Q90, Q95          | temperature, radiation       |
+------------------------------+------------+-------------------+-------------------+------------------------------+
| Grid loss                    | gblinear   | P1D               | Full range        | energy_price, temperature    |
+------------------------------+------------+-------------------+-------------------+------------------------------+
| Transport                    | xgboost    | P3D               | Full range        | temperature, radiation, wind |
+------------------------------+------------+-------------------+-------------------+------------------------------+
| District heating             | xgboost    | P2D               | Q10, Q50, Q90     | temperature, wind            |
+------------------------------+------------+-------------------+-------------------+------------------------------+
| MV route congestion          | xgboost    | P2D               | Q90, Q95          | temperature, radiation       |
+------------------------------+------------+-------------------+-------------------+------------------------------+

.. note::

   ``gblinear`` is preferred for smooth, highly aggregated signals (grid losses) because it avoids
   the extrapolation artefacts that tree-based models can produce outside the training range.
   For all other use cases, ``xgboost`` is the default starting point.

---

Related Pages
-------------

- :doc:`data_integration` — how to feed each use case with data from S3, Databricks, or InfluxDB.
- :doc:`deployment` — production patterns for running forecasts at scale across thousands of assets.
- :doc:`migration_v3_v4` — if you have existing V3 pipelines for any of these use cases, start here.