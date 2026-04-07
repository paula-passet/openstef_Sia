Common Use Cases
================

OpenSTEF is a general-purpose short-term energy forecasting library, but it was designed with specific operational challenges of grid operators in mind. This page describes the most common use cases, explains what makes each one distinct, and shows how to configure OpenSTEF for each scenario.

All of these use cases share the same core workflow—train a model on historical data, then produce forecasts—but they differ in what you forecast, which features matter most, and how you interpret the output.

.. contents:: On this page
   :local:
   :depth: 2


Congestion Forecasting
----------------------

Congestion forecasting predicts the electrical load on specific grid assets—transformers, cables, or busbars—to determine whether they will exceed their rated capacity. This is the most common use case for OpenSTEF and the one it was originally built for.

**What makes it different:** The focus is on accurately predicting *peaks*, not average load. A forecast that is accurate on average but misses the afternoon peak is operationally useless. This means you should use probabilistic forecasts (multiple quantiles) and evaluate with peak-detection metrics.

**Key configuration choices:**

- Use upper quantiles (e.g., P90, P95) to flag potential congestion with appropriate safety margins
- Configure short forecast horizons (15-minute to 48-hour) for operational decisions
- Include weather features (temperature, solar radiation, wind) since they drive peak loads

.. code-block:: python

   from datetime import timedelta
   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
   )
   from openstef_core.types import LeadTime, Q

   config = ForecastingWorkflowConfig(
       model_id="transformer_north_007",
       model="xgboost",
       quantiles=[Q(0.10), Q(0.50), Q(0.90), Q(0.95)],
       sample_interval=timedelta(minutes=15),
       horizons=[
           LeadTime.from_string("PT1H"),
           LeadTime.from_string("PT6H"),
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
       location=LocationConfig(
           name="transformer_north_007",
           description="MV/LV transformer, industrial district",
           country_code="NL",
       ),
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
   )

To evaluate congestion forecasts, use the peak-detection metrics provided by ``openstef_beam.metrics``:

.. code-block:: python

   from openstef_beam.metrics import confusion_matrix, precision_recall, fbeta

   # Compare forecast against asset capacity limit
   capacity_limit = 630.0  # kVA rated capacity
   cm = confusion_matrix(y_true, y_pred, threshold=capacity_limit)
   pr = precision_recall(cm)
   f2 = fbeta(pr, beta=2)  # F2 favors recall over precision

.. note::

   For congestion forecasting, an F2 score (beta=2) is often more appropriate than F1 because missing a real congestion event (false negative) is more costly than a false alarm.


Free Space Estimation
---------------------

Free space estimation answers the question: *how much additional load can this asset handle before it becomes congested?* It is the complement of congestion forecasting—instead of predicting absolute load, you compute the remaining capacity.

**What makes it different:** The output is derived by subtracting the forecasted load from the asset's rated capacity. The forecast itself is identical to a congestion forecast, but the interpretation and downstream use differ. Free space estimates are used for connection request assessments and flexibility market activation.

.. code-block:: python

   import pandas as pd

   # After generating a standard load forecast:
   rated_capacity = 630.0  # kVA

   # Free space = capacity - forecasted load
   # Use upper quantile for conservative (safe) estimate
   forecast_data["free_space_conservative"] = (
       rated_capacity - forecast_data["quantile_P90"]
   )
   # Use median for best-estimate
   forecast_data["free_space_best_estimate"] = (
       rated_capacity - forecast_data["quantile_P50"]
   )

   # Negative free space means expected congestion
   congestion_periods = forecast_data[
       forecast_data["free_space_conservative"] < 0
   ]

The forecasting model configuration is the same as for congestion forecasting. The difference is entirely in post-processing.


Grid Loss Forecasting
---------------------

Grid losses—the energy dissipated as heat in cables and transformers—are a significant cost for network operators. Forecasting these losses helps with energy procurement and settlement.

**What makes it different:** Grid losses are proportional to the *square* of the current (I²R losses), which means they are highly nonlinear. The target variable is the loss itself (measured or calculated), not the load. Feature engineering should include squared load terms or let the tree-based models capture this nonlinearity.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
   )
   from openstef_core.types import LeadTime, Q
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="grid_loss_region_east",
       model="lgbm",  # LightGBM handles nonlinear relationships well
       quantiles=[Q(0.10), Q(0.50), Q(0.90)],
       sample_interval=timedelta(hours=1),
       horizons=[
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
       temperature_column="temperature_2m",
   )

.. note::

   Grid loss forecasting typically uses hourly resolution rather than 15-minute, since losses are used for energy balance and settlement calculations that operate on hourly intervals.


Transport Forecasting
---------------------

Transport forecasts predict the total energy flowing through a section of the grid, typically at the interface between transmission and distribution networks. These forecasts are used for day-ahead and intraday energy procurement.

**What makes it different:** Transport forecasts operate at a higher aggregation level than individual asset forecasts. The aggregation tends to smooth out individual variations, which generally improves forecast accuracy. Weather features remain important, but the dominant drivers are often energy prices and calendar effects (weekday vs. weekend, holidays).

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
   )
   from openstef_core.types import LeadTime, Q
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="transport_substation_main",
       model="xgboost",
       quantiles=[Q(0.10), Q(0.50), Q(0.90)],
       sample_interval=timedelta(minutes=15),
       horizons=[
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
       location=LocationConfig(
           name="substation_main",
           description="HV/MV substation, mixed urban/rural",
           country_code="NL",
       ),
       temperature_column="temperature_2m",
       radiation_column="shortwave_radiation",
       wind_speed_column="wind_speed_80m",
       energy_price_column="EPEX_NL",
   )


District Heating Demand
-----------------------

OpenSTEF can forecast thermal energy demand for district heating networks. While the library was designed for electrical energy, the underlying time series patterns—weather dependence, calendar effects, daily profiles—are similar enough that the same models work well.

**What makes it different:** Temperature is the dominant predictor, far more so than for electrical load. The relationship between outdoor temperature and heating demand is strongly nonlinear (heating degree days). Wind speed and solar radiation also matter because they affect the perceived temperature and building heat loss.

.. code-block:: python

   from openstef_models.presets.forecasting_workflow import (
       ForecastingWorkflowConfig,
       LocationConfig,
   )
   from openstef_core.types import LeadTime, Q
   from datetime import timedelta

   config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_a",
       model="xgboost",
       quantiles=[Q(0.10), Q(0.50), Q(0.90)],
       sample_interval=timedelta(hours=1),
       horizons=[
           LeadTime.from_string("PT24H"),
           LeadTime.from_string("PT48H"),
       ],
       location=LocationConfig(
           name="heating_zone_a",
           description="District heating network, residential area",
           country_code="NL",
       ),
       temperature_column="temperature_2m",
       wind_speed_column="wind_speed_80m",
       radiation_column="shortwave_radiation",
   )

.. warning::

   District heating demand is seasonal by nature. Ensure your training data covers at least two full heating seasons to capture year-over-year variation. Models trained only on winter data will not generalize to shoulder seasons.


MV Route Congestion with Power Grid Model
------------------------------------------

Medium-voltage (MV) route congestion forecasting combines OpenSTEF's load forecasts with a power flow model to assess congestion across an entire feeder or route, not just a single asset. This is the most advanced use case and requires integration with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, an open-source library for power system calculations.

**What makes it different:** Instead of forecasting a single measurement point, you forecast load at multiple nodes in the network and then run a power flow calculation to determine loading on every cable and transformer in the route. This captures the fact that congestion on one cable depends on loads at many points in the network.

The workflow has three stages:

1. **Forecast** load at each node using OpenSTEF
2. **Map** forecasts onto a network topology model
3. **Calculate** power flow to determine asset loading across the route

.. note:: [DIAGRAM: MV route congestion workflow showing multiple node forecasts feeding into a power-grid-model topology, producing per-asset loading results]

.. code-block:: python

   import pandas as pd

   # Stage 1: Generate forecasts for each node in the MV route
   node_forecasts = {}
   for node_id in ["node_001", "node_002", "node_003", "node_004"]:
       # Each node has its own trained model and forecast
       # (training and prediction code omitted for brevity)
       node_forecasts[node_id] = forecast_for_node(node_id)

   # Stage 2: Map forecasts to power-grid-model input
   # power-grid-model expects load per node as sym_load update data
   import numpy as np
   from power_grid_model import PowerGridModel

   # Assume `pgm_model` is a pre-built PowerGridModel instance
   # and `node_to_load_id` maps node IDs to PGM load component IDs
   for timestamp in forecast_timestamps:
       update_data = {
           "sym_load": np.array(
               [
                   (node_to_load_id[node_id], forecast.loc[timestamp, "quantile_P50"])
                   for node_id, forecast in node_forecasts.items()
               ],
               dtype=[("id", "i4"), ("p_specified", "f8")],
           )
       }

       # Stage 3: Run power flow calculation
       result = pgm_model.calculate_power_flow(update_data=update_data)

       # Extract loading percentages for all lines
       line_loading = result["line"]["loading"]

This approach gives you a complete picture of where congestion will occur across the network, not just at individually monitored points.


Choosing the Right Use Case
----------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Use Case
     - Target Variable
     - Typical Resolution
     - Key Features
     - Primary Metric
   * - Congestion
     - Asset load (kW/kVA)
     - 15 min
     - Weather, calendar
     - F2 score (peak detection)
   * - Free Space
     - Remaining capacity
     - 15 min
     - Weather, calendar
     - MAE at peaks
   * - Grid Loss
     - Energy loss (kWh)
     - 1 hour
     - Temperature, load
     - MAE, RMAE
   * - Transport
     - Substation flow (MW)
     - 15 min
     - Weather, price, calendar
     - MAE, R²
   * - District Heating
     - Thermal demand (MWth)
     - 1 hour
     - Temperature, wind
     - MAE, R²
   * - MV Route
     - Per-asset loading (%)
     - 15 min
     - Weather, topology
     - F2 score per asset

All use cases benefit from probabilistic forecasting via quantiles. Configure the ``quantiles`` parameter based on your operational needs—wider intervals (e.g., P5–P95) for risk-averse decisions, narrower intervals for cost-sensitive operations.


Next Steps
----------

- For connecting your data sources to these configurations, see :doc:`data_integration`
- For deploying forecasting pipelines in production, see :doc:`deployment`
- For configuring logging and monitoring, see :doc:`logging`