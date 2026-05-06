Common Use Cases
================

OpenSTEF was built around a concrete operational problem — predicting load at grid locations to prevent
congestion — but the same forecasting machinery applies to a wider set of energy domain problems. This
page describes the main use cases the library supports, what distinguishes each one, and how to configure
OpenSTEF appropriately for each scenario.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_1.mmd

----

Congestion Management
---------------------

Congestion management is the original and most mature use case. A grid operator needs to know *when and
where* a transformer or cable will approach or exceed its rated capacity so that demand-response actions
can be triggered in advance.

The defining characteristic of this use case is that **accuracy near peak load matters far more than
average accuracy**. A model that is precise at median load but consistently underestimates the top 5 %
of hours is operationally useless for congestion management. OpenSTEF addresses this by supporting
quantile regression: you request high-quantile forecasts (e.g. the 90th or 95th percentile) and use
those as the conservative estimate for capacity planning.

Aggregation levels vary widely. A high-voltage substation serving tens of thousands of customers is
highly predictable; a single medium-voltage substation (MSR) serving a few hundred customers is
dominated by behavioural noise. OpenSTEF handles both, but model selection and hyperparameter tuning
differ between them.

**Typical metrics:** rMAE at the 50th quantile during peak hours, precision/recall of peak-hour
detection, rCRPS.

.. code-block:: python

    from datetime import timedelta
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_core.types import LeadTime, Quantile

    # High-quantile forecaster for congestion management
    # Request the median plus upper confidence bounds
    forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.5), Quantile(0.9), Quantile(0.95)],
        horizons=[LeadTime(timedelta(hours=24))],
    )

The 0.90 and 0.95 quantiles give operators a conservative upper bound on expected load. When the 95th
percentile forecast exceeds the cable rating, a congestion alert is raised with enough lead time to
contact customers.

----

Free Space Estimation
---------------------

Free space estimation is closely related to congestion management but asks the inverse question: *how
much remaining capacity is available* on a cable or transformer at a given moment? Rather than
forecasting raw load, the output is the headroom between the forecast load and the asset's rated
capacity.

In practice this is often derived directly from a congestion forecast: subtract the upper-quantile load
forecast from the rated capacity. The lower the resulting headroom, the less room there is to connect
new customers or accept additional generation without risking overload.

.. code-block:: python

    import pandas as pd

    # Assume `forecast_df` is a DataFrame returned by the forecaster
    # with columns named by quantile, e.g. "q0.95"
    rated_capacity_mw = 10.0  # transformer rating

    forecast_df["free_space_mw"] = rated_capacity_mw - forecast_df["q0.95"]
    forecast_df["congestion_risk"] = forecast_df["free_space_mw"] < 0.5

The key difference from pure congestion management is that free space estimation is often used for
*connection decisions* (can a new solar park be connected?) rather than real-time operational alerts.
This shifts the relevant horizon from hours ahead to days or weeks ahead, and the relevant quantile
from the 95th to something more conservative still.

----

Grid Losses Forecasting
-----------------------

Every transmission and distribution network loses a fraction of the energy it carries as heat in
conductors and transformers. Forecasting these losses accurately has direct financial consequences:
grid operators must purchase energy on the day-ahead market to cover losses, and buying too much or
too little at the wrong time is costly.

Grid losses are highly aggregated — they represent the sum of losses across an entire network — which
makes them more predictable than individual substation loads. Temporal and cyclic patterns (time of
day, day of week, season) dominate. Weather predictors have less influence than in substation-level
forecasting.

The distinctive modelling requirement is **cost-weighted error minimisation**. An overestimate at a
high market-price hour is more expensive than the same overestimate at a low-price hour. OpenSTEF
supports this through custom loss functions and sample weighting.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    # Grid losses: median forecast is usually sufficient;
    # cost weighting is applied during training, not via quantiles
    forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.5)],
        horizons=[LeadTime(timedelta(hours=48))],
    )

.. note::

   Market-price weighting during training is configured through the training pipeline, not the
   forecaster itself. See the pipeline configuration reference for details on passing sample weights.

----

Transport Forecasts
-------------------

Transport forecasts serve a coordination function between network operators. A distribution system
operator (DSO) like Alliander must report expected energy flows to the transmission system operator
(TSO) it connects to, and in turn receives similar forecasts from large industrial customers. These
forecasts feed into capacity planning and balancing markets.

Unlike congestion management, transport forecasts need to be **accurate across the entire forecast
horizon**, not just at peaks. The relevant metric is overall rMAE rather than peak-specific accuracy.
Aggregation is at medium levels — regional substations or entire grid areas — which gives a good
balance between predictability and granularity.

Some operators require transport forecasts decomposed into components: solar generation, wind
generation, and residual load. This requires training separate models per component and summing them,
or using a split-component model architecture.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_models.models.forecasting.gblinear_forecaster import GBLinearForecaster
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    horizons = [LeadTime(timedelta(hours=h)) for h in [1, 6, 24, 48]]

    # For a split-component transport forecast, train one forecaster per component
    solar_forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.5)],
        horizons=horizons,
    )
    wind_forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.5)],
        horizons=horizons,
    )
    residual_forecaster = GBLinearForecaster(
        quantiles=[Quantile(0.5)],
        horizons=horizons,
    )

``GBLinearForecaster`` is often a good choice for the residual component because linear relationships
tend to dominate at high aggregation levels and the model extrapolates more reliably beyond the
training range.

----

District Heating Demand
-----------------------

District heating is an example of OpenSTEF being applied outside the electricity domain. A district
heating network distributes hot water to residential and commercial buildings; the operator needs to
forecast thermal demand to schedule heat production efficiently.

The input features and seasonal patterns differ from electricity: heating demand is strongly driven by
outdoor temperature (heating degree days), building stock characteristics, and time of day, but solar
irradiance and wind speed matter less than in electricity forecasting. The target variable is thermal
power (MW) or heat flow rather than electrical load.

OpenSTEF's feature engineering pipeline is configurable enough to accommodate this. The core
forecasting models are domain-agnostic — they learn from whatever tabular features you provide.

.. code-block:: python

    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    # District heating: temperature is the dominant predictor.
    # Provide outdoor temperature and heating degree day features in your dataset.
    forecaster = XGBoostForecaster(
        quantiles=[Quantile(0.1), Quantile(0.5), Quantile(0.9)],
        horizons=[LeadTime(timedelta(hours=24))],
    )

The quantile outputs are useful here for production scheduling: the 10th percentile gives a lower
bound on demand (minimum heat production needed), while the 90th percentile guards against
under-production on unexpectedly cold days.

.. note::

   District heating support in OpenSTEF 4.0 is actively being developed. The core forecasting
   components work today; domain-specific feature transformers for thermal networks are planned for
   future releases.

----

MV Route Congestion with Topology
----------------------------------

Medium-voltage (MV) route congestion is the most complex use case. Rather than forecasting load at a
single point, the goal is to determine whether a *path* through the MV grid — a sequence of cables
connecting substations — will become congested. This requires combining OpenSTEF's load forecasts with
a power flow calculation that accounts for grid topology.

The integration point is `power-grid-model <https://github.com/PowerGridModel/power-grid-model>`_,
an open-source library for power flow and state estimation on distribution grids. The workflow is:

1. Forecast load at each node along the MV route using OpenSTEF.
2. Feed the forecasted nodal loads into a power-grid-model power flow calculation.
3. Inspect the resulting cable loading percentages to identify which segments will exceed their rating.

.. mermaid:: /diagrams/user_guide/use_cases_diagram_2.mmd

.. code-block:: python

    import pandas as pd
    from openstef_models.models.forecasting.xgboost_forecaster import XGBoostForecaster
    from openstef_core.types import LeadTime, Quantile
    from datetime import timedelta

    # Step 1: Forecast load at each MV node independently
    node_forecasters = {}
    for node_id in mv_route_nodes:  # mv_route_nodes: list of node identifiers
        node_forecasters[node_id] = XGBoostForecaster(
            quantiles=[Quantile(0.5), Quantile(0.9)],
            horizons=[LeadTime(timedelta(hours=4))],
        )
        # Train each forecaster on historical measurements for that node
        # node_forecasters[node_id].fit(training_data[node_id])  # fit with node data

    # Step 2: Collect forecasts into a nodal load DataFrame
    # nodal_forecasts: dict mapping node_id -> forecast Series (MW)
    # Pass to power-grid-model for power flow calculation (see power-grid-model docs)

This use case requires that you have a network model (asset data, cable ratings, topology) in addition
to load measurements. The OpenSTEF side is straightforward — one forecaster per node — but the
power-grid-model integration requires grid topology data that is typically sourced from a GIS or asset
management system.

----

Choosing the Right Configuration
---------------------------------

The table below summarises the key configuration choices for each use case.

.. list-table::
   :header-rows: 1
   :widths: 25 20 20 35

   * - Use case
     - Recommended model
     - Key quantiles
     - Notes
   * - Congestion management
     - ``XGBoostForecaster``
     - 0.5, 0.9, 0.95
     - Tune for peak accuracy; low-aggregation nodes need more regularisation
   * - Free space estimation
     - ``XGBoostForecaster``
     - 0.95, 0.99
     - Derive headroom post-hoc from upper quantile
   * - Grid losses
     - ``XGBoostForecaster`` or ``GBLinearForecaster``
     - 0.5
     - Apply market-price sample weights during training
   * - Transport forecasts
     - ``GBLinearForecaster``
     - 0.5
     - Consider split-component models for solar/wind decomposition
   * - District heating
     - ``XGBoostForecaster``
     - 0.1, 0.5, 0.9
     - Temperature features are critical; electricity features less relevant
   * - MV route congestion
     - ``XGBoostForecaster`` per node
     - 0.5, 0.9
     - Requires power-grid-model integration for topology-aware results

----

Related Pages
-------------

- :doc:`data_integration` — how to load historical measurements and weather data from S3, Databricks,
  or InfluxDB into the format OpenSTEF expects.
- :doc:`deployment` — production deployment patterns for running multiple forecasters at scale across
  thousands of grid locations.
- :doc:`migration_v3_v4` — if you have existing V3 pipelines for any of these use cases, see the
  migration guide for the changes required to move to V4.