Short-Term Forecasting
======================

This page introduces the core concepts of short-term energy forecasting (STEF) — what it is, why it matters for power grid operations, and how OpenSTEF helps you build forecasting solutions. If you're new to the energy forecasting domain, start here before diving into code.

What Is Short-Term Energy Forecasting?
--------------------------------------

Short-term energy forecasting is the practice of predicting electrical load (consumption or generation) over horizons ranging from 15 minutes to approximately 7 days into the future. These predictions enable grid operators to make timely operational decisions — from dispatching generation assets to managing congestion on distribution networks.

Unlike long-term forecasting (months to years), which supports infrastructure planning, short-term forecasting operates on the timescale of grid operations. The predictions must be frequent, granular (typically 15-minute resolution), and reliable enough to trigger real-world actions.

.. mermaid:: /diagrams/user_guide/concepts/short_term_forecasting_diagram_1.mmd

Forecast Horizons
-----------------

Short-term forecasts span several operational horizons, each serving different purposes:

- **Intra-hour (15 min – 1 hour)**: Real-time balancing, immediate congestion response
- **Intra-day (1 – 12 hours)**: Operational scheduling, demand response activation
- **Day-ahead (12 – 48 hours)**: Market participation, crew scheduling, planned interventions
- **Week-ahead (48 hours – 7 days)**: Maintenance planning, capacity reservation

In OpenSTEF, you specify forecast horizons using the ``LeadTime`` type:

.. code-block:: python

   from openstef_core.types import LeadTime

   # Define forecast horizons
   horizons = [
       LeadTime.from_string("PT1H"),    # 1 hour ahead
       LeadTime.from_string("PT12H"),   # 12 hours ahead
       LeadTime.from_string("PT36H"),   # 36 hours ahead
   ]

The 7-day practical limit exists because weather forecasts beyond this range lack the 15-minute temporal resolution needed for accurate energy predictions. Solar and wind generation peaks become unpredictable as weather uncertainty compounds.

How Forecast Quality Relates to Lead Time
------------------------------------------

Forecast accuracy degrades as the prediction horizon increases. This is a fundamental property of all time series forecasting, but it is especially pronounced in energy systems because:

- **Weather uncertainty grows** — cloud cover, wind speed, and temperature predictions become less precise over time, directly affecting solar and wind generation forecasts.
- **Human behaviour is less predictable** — individual consumption patterns are harder to anticipate days in advance compared to hours ahead.
- **Compounding errors** — small inaccuracies in weather inputs amplify through the forecasting model at longer horizons.

.. note:: [VISUALIZATION: Plot showing forecast error (e.g., rMAE) on the y-axis versus lead time on the x-axis, demonstrating the characteristic degradation curve from 1-hour to 48-hour predictions]

This degradation is not uniform across all forecast targets. Highly aggregated loads (e.g., an entire substation) are more predictable than individual customers, because individual behavioural variability averages out at higher aggregation levels.

OpenSTEF's backtesting framework (BEAM) supports **lead time analysis** — evaluating how forecast quality changes from 1-hour to 48-hour predictions — which is critical for understanding whether your model meets operational requirements at each horizon.

Probabilistic Forecasting
--------------------------

Point forecasts (a single predicted value) are rarely sufficient for grid operations. Operators need to understand the *range* of likely outcomes to make risk-informed decisions. OpenSTEF produces **probabilistic forecasts** using quantiles:

.. code-block:: python

   from openstef_core.types import Q

   # Define quantiles for prediction intervals
   quantiles = [
       Q(0.1),   # 10th percentile (lower bound of 80% interval)
       Q(0.5),   # Median forecast
       Q(0.9),   # 90th percentile (upper bound of 80% interval)
   ]

A congestion manager, for example, might trigger preventive action when the 90th percentile forecast exceeds a transformer's rated capacity — even if the median forecast remains below the limit. This approach balances the cost of unnecessary interventions against the risk of equipment damage.

Use Cases in the Energy Domain
------------------------------

OpenSTEF is designed for several forecasting applications, each with distinct accuracy requirements:

**Congestion management**
   The primary use case. Grid operators predict peak load moments at substations and medium-voltage feeders to activate mitigation strategies (e.g., calling customers to reduce consumption). Accuracy near peaks matters most; nighttime errors are less critical.

**Transport forecasts**
   Grid operators communicate planned energy flows to upstream transmission system operators. Overall accuracy across the entire forecast horizon is the priority.

**Grid losses forecasting**
   Predicting system-level losses for financial optimization. At this high aggregation level, temporal and cyclic patterns dominate over weather effects.

**District heating and emerging applications**
   Thermal demand forecasting and other energy domains beyond electricity.

.. mermaid:: /diagrams/user_guide/concepts/short_term_forecasting_diagram_2.mmd

Where OpenSTEF Fits
-------------------

OpenSTEF is a Python library — not a deployed application — that provides the building blocks for short-term energy forecasting systems. It handles:

- **Data preprocessing**: Feature engineering with lag transforms, holiday features, and weather variable integration
- **Model training**: Configurable machine learning pipelines with multiple model types
- **Prediction**: Probabilistic forecasts with configurable quantiles and horizons
- **Evaluation**: Backtesting with realistic operational constraints (no future data leakage)

A minimal forecasting setup combines these components:

.. code-block:: python

   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow
   from openstef_core.types import LeadTime, Q

   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="my_substation_forecast",
           model="gblinear",
           horizons=[LeadTime.from_string("PT36H")],
           quantiles=[Q(0.5), Q(0.1), Q(0.9)],
           target_column="load",
       )
   )

OpenSTEF is currently used in production at Alliander (a Dutch distribution system operator) to generate forecasts for over 10,000 grid locations daily.

Key Takeaways
-------------

- Short-term energy forecasting predicts load over 15 minutes to 7 days, enabling operational grid decisions.
- Forecast quality degrades with lead time — evaluate your model at each horizon that matters for your use case.
- Probabilistic forecasts (quantiles) are essential for risk-informed decision-making in grid operations.
- Higher aggregation levels yield more predictable forecasts; individual customers are inherently harder to forecast.
- OpenSTEF provides modular library components that you compose into a forecasting system tailored to your needs.

Next Steps
----------

- Learn about the machine learning models available for forecasting in :doc:`models`
- Follow a hands-on tutorial to build your first forecast pipeline
- Explore backtesting to evaluate forecast quality across different lead times