Short-Term Forecasting
======================

This page introduces the concept of short-term energy forecasting — what it is, why it matters for grid operations, and how OpenSTEF approaches the problem. If you're new to energy forecasting or to OpenSTEF, start here.

What Is Short-Term Energy Forecasting?
--------------------------------------

Short-term energy forecasting is the practice of predicting electrical load (consumption or generation) at specific grid points over a horizon of hours to several days. Unlike long-term planning forecasts that project demand years into the future, short-term forecasts operate at high temporal resolution — typically 15-minute intervals — and inform operational decisions that must be made within hours or days.

The "load" being predicted can represent:

- Total power flowing through a substation transformer
- Aggregated consumption of a neighbourhood or industrial park
- Generation output from solar panels or wind turbines
- Net load (consumption minus local generation) at a grid connection point

.. mermaid:: /diagrams/user_guide/concepts/short_term_forecasting_diagram_1.mmd

Forecast Horizons
-----------------

Short-term forecasting covers a range of lead times, each serving different operational needs:

**Very short-term (15 minutes to 1 hour)**
   Used for real-time grid balancing and immediate operational adjustments. At this horizon, recent measurements are the strongest predictor — the load 15 minutes from now is likely close to what it is right now.

**Intra-day (1 to 6 hours)**
   Supports dispatching decisions and short-notice demand response. Weather forecasts begin to matter more than persistence at this range.

**Day-ahead (12 to 36 hours)**
   The most common operational horizon. Grid operators need to know tomorrow's peak loads to schedule maintenance, activate flexibility contracts, or prepare congestion management actions. This is the primary horizon OpenSTEF targets.

**Multi-day (2 to 7 days)**
   Used for planning flexibility activation and communicating expected transport volumes to upstream operators. Beyond 7 days, weather forecast quality degrades significantly — 15-minute resolution weather data is typically unavailable, making accurate peak prediction unreliable.

In OpenSTEF, you configure the forecast horizon explicitly when setting up a workflow:

.. code-block:: python

   from openstef_core.types import LeadTime, Q
   from openstef_models.presets import ForecastingWorkflowConfig, create_forecasting_workflow

   workflow = create_forecasting_workflow(
       config=ForecastingWorkflowConfig(
           model_id="substation_forecast_v1",
           model="gblinear",
           # Predict up to 36 hours ahead (day-ahead + buffer)
           horizons=[LeadTime.from_string("PT36H")],
           # Probabilistic forecast: median + 80% prediction interval
           quantiles=[Q(0.5), Q(0.1), Q(0.9)],
           target_column="load",
       )
   )

Forecast Quality and Lead Time
------------------------------

A fundamental principle of forecasting: **accuracy degrades as lead time increases**. A 1-hour-ahead forecast will almost always outperform a 36-hour-ahead forecast for the same target.

This degradation is not linear. Several factors influence how quickly quality drops:

- **Aggregation level** — Forecasting a large substation (many customers) is easier than forecasting a single household. Individual behaviour is erratic; aggregated behaviour follows patterns.
- **Weather dependence** — Points with high solar or wind penetration are more sensitive to weather forecast errors, which grow with lead time.
- **Temporal patterns** — Highly regular loads (e.g., industrial processes) maintain accuracy further into the future than variable loads (e.g., EV charging).

.. note:: [VISUALIZATION: Line chart showing forecast error (y-axis, e.g., rMAE) vs. lead time (x-axis, 0-48 hours) for three scenarios: highly aggregated substation (low, slowly rising error), medium aggregation with solar (moderate, faster rise), and individual customer (high, steep rise)]

This is why OpenSTEF produces **probabilistic forecasts** — rather than a single point prediction, it generates quantiles that express uncertainty. The prediction interval naturally widens at longer lead times, giving operators a realistic picture of what might happen:

.. code-block:: python

   from openstef_core.datasets import ForecastDataset

   # Generate probabilistic forecasts
   forecast: ForecastDataset = workflow.predict(forecast_dataset)

   # Access different quantiles
   median_forecast = forecast.median_series        # P50 — best estimate
   lower_bound = forecast.quantiles_data           # P10 — unlikely to be below this
   # The gap between P10 and P90 widens at longer lead times

What Drives Short-Term Load?
----------------------------

Effective forecasting requires understanding what influences electrical load at short time scales:

**Temporal patterns**
   Load follows daily cycles (morning ramp-up, evening peak), weekly patterns (weekday vs. weekend), and seasonal trends. These are captured through time-based features.

**Weather**
   Temperature drives heating and cooling demand. Solar irradiance directly determines PV generation. Wind speed governs wind turbine output. Cloud cover creates rapid fluctuations in solar generation.

**Calendar effects**
   Public holidays, school vacations, and special events disrupt normal patterns. A Tuesday that's a national holiday looks more like a Sunday than a typical Tuesday.

**Lagged observations**
   Recent measurements carry strong predictive power, especially at short horizons. What the load was 15 minutes ago is highly informative about what it will be 15 minutes from now.

OpenSTEF incorporates domain-specific feature engineering that transforms raw weather data and timestamps into features tuned for energy forecasting — for example, converting solar irradiance into estimated PV generation based on panel orientation.

Where OpenSTEF Fits
-------------------

OpenSTEF is a **model-agnostic Python framework** for the complete short-term forecasting workflow. It is not a single model but a set of composable components covering:

- **Data preprocessing** — validation, cleaning, and alignment of input time series
- **Feature engineering** — domain-specific transformations for energy data
- **Model training** — flexible model fitting with configurable algorithms
- **Forecasting** — generating probabilistic predictions at specified horizons
- **Evaluation** — backtesting and metrics computation to assess forecast quality

.. mermaid:: /diagrams/user_guide/concepts/short_term_forecasting_diagram_2.mmd

OpenSTEF was originally developed at Alliander, a Dutch distribution system operator, for **congestion management** — predicting when grid equipment will be overloaded so that customers can be asked to reduce consumption in advance. Over time, it has expanded to support transport forecasts, grid loss estimation, EV charging prediction, and non-electricity domains like district heating.

Use Cases at a Glance
^^^^^^^^^^^^^^^^^^^^^

- **Congestion management** — Predict peak loads 2 days ahead to activate demand response before equipment limits are exceeded
- **Transport forecasts** — Communicate expected load profiles to upstream transmission operators
- **Grid loss forecasting** — Estimate system losses for financial optimization
- **Renewable generation** — Forecast solar and wind output for grid balancing

Each use case emphasizes different aspects of forecast quality. Congestion management cares primarily about accuracy near peaks; transport forecasts need balanced accuracy across all hours.

Next Steps
----------

Now that you understand the forecasting domain, explore these related topics:

- Learn about :doc:`probabilistic_forecasting` and why prediction intervals matter for operational decisions
- Understand the :doc:`machine_learning_pipeline` that OpenSTEF uses to train and deploy models
- See how :doc:`feature_engineering` encodes domain knowledge into model inputs