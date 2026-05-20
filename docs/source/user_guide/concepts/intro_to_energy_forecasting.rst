Intro to Energy Forecasting
===========================

This page explains the fundamental concepts behind short-term energy forecasting — the problem domain that OpenSTEF is designed to address. Understanding these concepts will help you make better decisions when configuring forecasting pipelines and interpreting their results.

.. contents:: On this page
   :local:
   :depth: 2

What Is Short-Term Energy Forecasting?
--------------------------------------

Short-term energy forecasting (STEF) is the practice of predicting electrical load or generation at specific points in the grid over horizons ranging from minutes to approximately seven days ahead. Grid operators rely on these forecasts to:

- **Manage congestion** — anticipate when substations or cables approach capacity limits
- **Plan transport** — communicate expected energy flows to upstream and downstream operators
- **Optimize operations** — schedule maintenance, manage grid losses, and reduce costs

Unlike long-term planning (months to years), short-term forecasting operates at high temporal resolution — typically 15-minute intervals — and must be refreshed frequently as new measurements and weather forecasts arrive.

.. mermaid:: /diagrams/user_guide/concepts/intro_to_energy_forecasting_diagram_1.mmd

Why Accuracy Degrades with Lead Time
-------------------------------------

The **forecast horizon** (or lead time) is the gap between the moment you make a prediction and the moment you are predicting. A "36-hour-ahead" forecast made at noon Monday predicts conditions at midnight Tuesday into Wednesday.

Accuracy degrades with increasing lead time for two reasons:

1. **Weather forecast uncertainty compounds** — numerical weather models lose 15-minute resolution beyond ~7 days, and cloud cover predictions (critical for solar) become unreliable after 2–3 days.
2. **Lag features become unavailable** — the most recent measurements cannot be used as inputs when the horizon exceeds their age. If you are forecasting 36 hours ahead, you cannot use data from 24 hours ago.

OpenSTEF's :class:`~openstef_models.transforms.time_domain.lags_adder.LagsAdder` automatically selects only lag features that respect the forecast horizon, preventing data leakage while maximizing the information available at each lead time.

Input Signals and Why They Matter
---------------------------------

Energy forecasting draws on several categories of input data. Each captures a different driver of load or generation behaviour:

.. list-table:: Key Input Signal Categories
   :header-rows: 1
   :widths: 20 40 40

   * - Signal Category
     - Why It Matters
     - OpenSTEF Support
   * - **Load history**
     - Energy demand is highly auto-correlated — last Monday's load is the best predictor of this Monday's load.
     - :class:`~openstef_models.transforms.time_domain.lags_adder.LagsAdder` with configurable custom lags
   * - **Weather forecasts**
     - Temperature drives heating/cooling demand; wind speed and solar radiation drive renewable generation.
     - :class:`~openstef_models.transforms.weather_domain.AtmosphereDerivedFeaturesAdder`, :class:`~openstef_models.transforms.weather_domain.RadiationDerivedFeaturesAdder`
   * - **Calendar features**
     - Weekdays vs weekends, public holidays, and time-of-day create strong periodic patterns.
     - :class:`~openstef_models.transforms.time_domain.HolidayFeatureAdder`, :class:`~openstef_models.transforms.time_domain.CyclicFeaturesAdder`
   * - **Market prices**
     - Energy prices influence behaviour — wind parks may curtail at negative prices; industrial loads may shift.
     - Configurable via ``energy_price_column`` in workflow configuration
   * - **Daylight / astronomical**
     - Sunrise and sunset times bound solar generation windows.
     - :class:`~openstef_models.transforms.weather_domain.DaylightFeatureAdder`

.. note::

   OpenSTEF provides transforms to extract valuable features from raw inputs, but **good input data is essential**. No model can compensate for missing weather forecasts or corrupted load measurements. The principle of "garbage in, garbage out" applies strongly here.

What Makes Energy Forecasting Difficult
---------------------------------------

Even with good models and data, several characteristics of the energy domain make forecasting inherently challenging:

Unpredictable behaviour at low aggregation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Individual customers and small generation assets behave erratically. A single industrial customer may shut down for unannounced maintenance. A wind park may curtail output when market prices turn negative. These events are nearly impossible to predict from historical patterns alone.

Aggregation helps — but not always
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As a general rule, **higher aggregation levels are easier to forecast** because individual anomalies average out. A substation serving thousands of households is more predictable than any single household. However, congestion management often requires forecasts at low-aggregation points (individual substations, medium-voltage rings) where variability remains high.

Capacity and topology changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The grid is not static. New solar installations connect, industrial customers relocate, and network topology changes during maintenance. These shifts mean that historical patterns may not represent future behaviour. Models must adapt, and operators must monitor for concept drift.

Weather forecast quality varies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Solar and wind forecasts depend heavily on numerical weather prediction quality. A 5% error in cloud cover prediction can translate to a 30% error in solar generation. Beyond 2–3 days, weather models struggle to predict the precise timing of cloud passages at 15-minute resolution.

Feature quality drives accuracy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

OpenSTEF's transform modules (``transforms.time_domain``, ``transforms.weather_domain``, ``transforms.energy_domain``) exist because raw inputs are rarely sufficient. Derived features — wind power curves, cyclic encodings of hour-of-day, rate-of-change indicators — help models capture the physics and periodicity of energy systems. But these transforms can only work with what they are given.

OpenSTEF's Approach
-------------------

OpenSTEF addresses these challenges through:

- **Modular transform pipelines** — compose validation, feature engineering, and cleaning steps appropriate to your use case
- **Horizon-aware feature selection** — automatically prevents data leakage across forecast horizons
- **Probabilistic forecasting** — quantile predictions communicate uncertainty, which is critical when accuracy degrades at longer horizons
- **Extensible model architecture** — swap models without changing the pipeline (see :doc:`models`)

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_core.mixins import TransformPipeline

   # Lags are automatically constrained to respect the 36-hour horizon
   lags = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[LeadTime.from_string("PT36H")],
       target_column="load",
   )

Where to Go Next
----------------

This page covered the *what* and *why* of short-term energy forecasting. For the *how*:

- :ref:`guide_forecasting` — step-by-step guide to building and running a forecast pipeline
- :doc:`models` — understanding which model types suit which use cases
- The forecasting tutorial demonstrates a complete end-to-end workflow with real data