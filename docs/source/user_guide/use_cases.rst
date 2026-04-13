Use Cases
=========

OpenSTEF is a general-purpose short-term energy forecasting library, but the problems it is applied to vary considerably in their data characteristics, optimisation targets, and downstream applications. This page describes the main use cases the library has been designed to support, explains what makes each one distinct, and shows how to configure OpenSTEF appropriately for each scenario.

.. note:: [DIAGRAM: Use case overview — six forecasting scenarios (congestion management, free space estimation, grid loss, transport, district heating, MV route congestion) arranged around a central OpenSTEF library core, each annotated with its primary input data types (load measurements, weather, topology) and output applications (peak alerts, capacity headroom, cost optimisation, TSO reporting, thermal demand, network power flow)]

---

Overview
--------

The table below summarises the six use cases covered on this page and the key dimension along which they differ:

.. list-table::
   :header-rows: 1
   :widths: 28 22 20 30

   * - Use Case
     - Aggregation Level
     - Primary Metric
     - Distinguishing Feature
   * - Congestion management
     - Low–high (variable)
     - rMAE@peak, rCRPS
     - Peak-period accuracy, high-quantile focus
   * - Free space estimation
     - Low–medium
     - rMAE@peak
     - Derived from congestion forecast + rated capacity
   * - Grid loss forecasting
     - Very high
     - rMAE + cost-weighted error
     - Market-price error weighting, weak weather signal
   * - Transport forecasting
     - Medium
     - rMAE
     - Component splitting (solar/wind/other)
   * - District heating demand
     - Medium
     - rMAE
     - Non-electrical domain, temperature-driven
   * - MV route congestion
     - Low (per cable/transformer)
     - rMAE@peak
     - Topology-aware via power-grid-model integration

---

Congestion Management Forecasts
--------------------------------

Congestion management is the original and most mature use case for OpenSTEF. A distribution system operator (DSO) needs to know *when* a transformer or cable will be loaded beyond its rated capacity so that it can intervene — calling customers, activating flexibility contracts, or rerouting power — before an overload occurs.

What makes this use case hard is the variability in aggregation level. A high-voltage substation aggregates thousands of customers and is relatively predictable. A single medium-voltage connection point or an individual industrial customer can be highly erratic. OpenSTEF handles both, but the model configuration and evaluation strategy differ.

**Key characteristics:**

- The forecast horizon is typically 24–48 hours ahead, with 15-minute resolution.
- Accuracy near peak periods matters far more than accuracy at low-load times.
- Probabilistic forecasts (quantiles) are essential: operators need to know not just the expected load but also the upper-bound risk.
- Weather features (temperature, solar irradiance, wind) are important predictors.

**Example configuration:**

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # For congestion management, include high quantiles to capture peak-load risk.
   # The 0.90 and 0.95 quantiles drive the congestion alert logic downstream.
   forecaster = XGBoostForecaster(
       quantiles=[
           Quantile(0.05),
           Quantile(0.10),
           Quantile(0.50),
           Quantile(0.70),
           Quantile(0.90),
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

.. note::

   At low aggregation levels (individual customers, MSRs), consider using a ``GBLinearForecaster``
   as a fallback when training data is sparse. Its linear inductive bias can generalise better
   than a deep tree model when fewer historical patterns are available.

---

Free Space Estimation
---------------------

Free space estimation is a derived use case built directly on top of a congestion management forecast. Rather than asking "how loaded will this asset be?", it asks "how much *remaining capacity* is available?". The answer is simply the rated capacity of the asset minus the forecast load — but the probabilistic framing is what makes it useful.

By using the upper quantiles of the load forecast, operators can compute a *conservative* free space estimate: the headroom that is available even in a high-load scenario. This is used for decisions such as whether to connect a new customer or approve a new EV charging cluster.

.. code-block:: python

   import pandas as pd

   # Assume `forecast` is a ForecastDataset returned by a fitted workflow,
   # and `rated_capacity_mw` is the asset's nameplate rating.
   rated_capacity_mw = 10.0

   # Conservative free space uses the 90th-percentile load forecast.
   free_space = rated_capacity_mw - forecast.predictions["q_0.90"]

   # Negative values indicate congestion risk at the 90th percentile.
   congestion_risk = free_space[free_space < 0]

The configuration for the underlying forecaster is identical to the congestion management case. The distinction is entirely in how the output is consumed, not in how the model is trained.

---

Grid Loss Forecasting
---------------------

Grid losses — the energy dissipated as heat in cables and transformers during transmission — are a significant operational cost for network operators. Forecasting losses accurately allows operators to purchase the right amount of energy on the day-ahead market to cover those losses, minimising imbalance costs.

This use case has a fundamentally different character from congestion management:

- **High aggregation:** Losses are measured at a system level, aggregating over many assets. This makes the time series much smoother and more predictable.
- **Weak weather signal:** At high aggregation, individual weather effects cancel out. Temporal patterns (time of day, day of week, seasonal cycles) dominate.
- **Cost-weighted errors:** An over-forecast on a high-price hour is more expensive than the same error on a low-price hour. The loss function should reflect market prices.

Because temporal patterns dominate, a ``GBLinearForecaster`` often performs competitively here and is faster to train than a tree-based model.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.gblinear_forecaster import (
       GBLinearForecaster,
       GBLinearHyperParams,
   )

   # Grid loss forecasting: median forecast is sufficient for procurement decisions.
   # Add quantiles if you need to hedge against forecast uncertainty.
   forecaster = GBLinearForecaster(
       quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
       horizons=[LeadTime(timedelta(hours=24))],
       hyperparams=GBLinearHyperParams(
           learning_rate=0.05,
           reg_alpha=0.1,
           reg_lambda=1.0,
       ),
   )

.. note::

   Cost-weighted evaluation is not yet built into the standard OpenSTEF workflow configuration.
   To weight errors by market price, apply a custom sample-weight array during ``forecaster.fit()``
   or implement a custom loss callback in your workflow.

---

Transport Forecasts
-------------------

Transport forecasting serves a different business purpose: communicating planned energy flows to upstream and downstream network operators. A DSO like Alliander, for example, must report expected transport volumes to the national transmission system operator (TSO) TenneT, and simultaneously receives similar forecasts from its own large customers.

Transport forecasts are typically made at medium aggregation levels — a regional substation or a cluster of substations — which makes them more predictable than individual connection points.

A distinctive requirement for transport forecasts is **component splitting**: the TSO often wants the total forecast broken down into constituent generation components (solar, wind, residual load). OpenSTEF provides a dedicated ``ComponentSplittingModel`` and ``CustomComponentSplitWorkflow`` for this purpose.

.. code-block:: python

   from openstef_models.workflows.custom_component_split_workflow import (
       CustomComponentSplitWorkflow,
   )
   from openstef_models.models.component_splitting import (
       ComponentSplitter,
       ComponentSplitterConfig,
   )
   from openstef_core.datasets import TimeSeriesDataset

   # Configure a component splitter that decomposes total load into
   # solar, wind, and residual ("other") components.
   splitter_config = ComponentSplitterConfig()
   splitter = ComponentSplitter(config=splitter_config)

   workflow = CustomComponentSplitWorkflow(model=splitter)

   # training_data must contain total load plus known component proxies
   # (e.g., irradiance for solar, wind speed for wind).
   workflow.fit(training_data)  # training_data: TimeSeriesDataset

   # Returns an EnergyComponentDataset with per-component predictions.
   components = workflow.predict(inference_data)

The transport forecaster itself is configured identically to the congestion management case — the component split is a post-processing step applied to the raw load forecast output.

---

District Heating Demand
-----------------------

District heating is a community use case that extends OpenSTEF beyond electricity into thermal energy. A district heating operator needs to forecast heat demand across a network of buildings to schedule production from heat plants and avoid both under-supply (customer discomfort) and over-supply (wasted fuel).

The core modelling approach is the same as for electricity: a time-series regression model trained on historical demand and weather features. What changes is the feature set and the seasonality pattern:

- **Temperature is the dominant driver.** Unlike electricity, where temperature is one of several predictors, heat demand is almost entirely temperature-driven.
- **Solar irradiance matters indirectly** — sunny days reduce heating demand through passive solar gain.
- **Demand is near-zero in summer**, creating a strongly asymmetric seasonal pattern that the model must handle.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )
   from openstef_models.workflows.forecasting_workflow import ForecastingWorkflowConfig

   # District heating: 48-hour horizon, temperature-heavy feature set.
   config = ForecastingWorkflowConfig(
       model_id="district_heating_zone_a",
       model="xgboost",
       horizons=[LeadTime(timedelta(hours=48))],
       quantiles=[Quantile(0.10), Quantile(0.50), Quantile(0.90)],
       temperature_column="temperature_2m",
       # Disable wind features — less relevant for thermal demand.
       wind_speed_column=None,
   )

.. note::

   OpenSTEF's holiday calendar and time-of-day features are electricity-centric by default.
   For district heating, consider whether public holiday effects apply in your region and
   whether to add heating-degree-day (HDD) features as custom columns in your input dataset.

---

MV Route Congestion with Power-Grid-Model
------------------------------------------

Medium-voltage (MV) route congestion is the most topologically complex use case. A single MV feeder cable serves multiple connection points arranged in a branching network. Whether any individual cable segment is overloaded depends not just on local demand but on the aggregate load of all downstream customers — a relationship that is encoded in the network topology.

OpenSTEF addresses this by integrating with `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_, an open-source library for power flow calculations. The workflow is:

1. Forecast load at each individual connection point using OpenSTEF.
2. Feed the per-node forecasts into power-grid-model as boundary conditions.
3. Run a power flow calculation to determine the resulting current through each cable segment.
4. Compare the calculated current against each cable's rated ampacity to identify congestion.

.. note:: [DIAGRAM: MV route congestion workflow — left side shows individual connection-point forecasters (one per node) feeding probabilistic load forecasts into a power-grid-model topology graph; right side shows power flow results per cable segment with congestion flags where current exceeds rated ampacity]

This approach has two important implications for how you configure OpenSTEF:

- **Each connection point needs its own forecaster**, trained on that point's historical load. The forecasters are independent and can be trained in parallel.
- **Quantile forecasts are essential.** To assess congestion *risk* rather than just expected congestion, you run the power flow calculation at multiple quantile levels (e.g., the 50th, 90th, and 95th percentiles of the load forecast) and report the probability that any cable segment is overloaded.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime, Quantile
   from openstef_models.models.forecasting.xgboost_forecaster import (
       XGBoostForecaster,
       XGBoostHyperParams,
   )

   # One forecaster per connection point on the MV route.
   # All forecasters share the same quantile and horizon configuration
   # so their outputs can be combined in a single power flow run.
   SHARED_QUANTILES = [Quantile(0.50), Quantile(0.90), Quantile(0.95)]
   SHARED_HORIZONS = [LeadTime(timedelta(hours=24))]

   def build_node_forecaster(node_id: str) -> XGBoostForecaster:
       return XGBoostForecaster(
           quantiles=SHARED_QUANTILES,
           horizons=SHARED_HORIZONS,
           hyperparams=XGBoostHyperParams(n_estimators=150, max_depth=5),
       )

   # Build one forecaster per node in the MV route topology.
   node_ids = ["node_a", "node_b", "node_c", "node_d"]
   forecasters = {node_id: build_node_forecaster(node_id) for node_id in node_ids}

   # After fitting and predicting, pass per-node forecasts to power-grid-model
   # for the power flow calculation. That integration is outside OpenSTEF's scope
   # but the library produces the inputs it needs.

.. note::

   The power flow calculation itself is performed by power-grid-model, not by OpenSTEF.
   OpenSTEF's role is to produce accurate, calibrated probabilistic load forecasts at each node.
   See the `power-grid-model documentation <https://power-grid-model.readthedocs.io/>`_ for
   how to construct the network model and run power flow calculations.

---

Choosing the Right Configuration
---------------------------------

The use cases above share the same underlying library API. The differences are in:

- **Which quantiles to request.** Peak-risk use cases (congestion, free space, MV route) need high quantiles (0.90, 0.95). Cost-optimisation use cases (grid loss) typically need only the median plus a narrow interval.
- **Which model class to use.** Tree-based models (``XGBoostForecaster``, ``LGBMForecaster``) handle non-linear relationships well and suit low-to-medium aggregation. Linear models (``GBLinearForecaster``) generalise better with sparse data and suit high-aggregation or data-poor scenarios.
- **Which features to include.** Weather features matter most for congestion and district heating. Temporal features dominate for grid losses. Topology-derived features (downstream aggregate load) are relevant for MV route congestion.
- **Whether component splitting is needed.** Only transport forecasts typically require decomposing the total load into solar, wind, and residual components.

For guidance on how to bring your data into OpenSTEF for any of these use cases, see :doc:`data_integration`. For running these workflows in production, see :doc:`deployment`.