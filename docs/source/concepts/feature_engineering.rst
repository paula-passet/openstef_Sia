Feature Engineering
===================

Energy load is shaped by a rich interplay of physical, behavioural, and calendar effects. A model that sees only raw historical load will miss the systematic patterns that make short-term forecasting tractable. This page explains the feature categories that matter most for energy forecasting and shows how OpenSTEF's built-in transform library lets you compose them into a preprocessing pipeline.

For background on what short-term forecasting is and why it matters, see :doc:`forecasting_basics`. For how uncertainty is expressed in the resulting forecasts, see :doc:`quantiles_and_confidence`.

.. note::

   All feature engineering in OpenSTEF is implemented as composable ``TimeSeriesTransform`` objects. You assemble them into a pipeline; the library handles fitting, transforming, and propagating feature metadata automatically.

[DIAGRAM: Feature engineering pipeline showing raw inputs (load, weather, datetime index) flowing through transform stages (weather domain, time domain, energy domain, general) into a feature matrix consumed by a forecaster]

Why Features Matter
-------------------

Classical ML models — XGBoost, LightGBM, linear regression — do not learn temporal structure on their own. They treat each row as an independent observation. Good feature engineering bridges that gap by encoding the patterns the model cannot discover unaided:

- **Periodicity.** Load follows daily, weekly, and annual cycles. Encoding these explicitly prevents the model from having to rediscover them from sparse data.
- **Physical causation.** Solar irradiance drives PV generation; temperature drives heating and cooling demand. Providing derived physical quantities gives the model a causal handle on the target.
- **Recent history.** The load five minutes ago is a strong predictor of the load now. Lag features make this information available at inference time.
- **Exceptional days.** Public holidays break the normal weekly pattern. Without a holiday indicator, the model will confidently predict a working-day profile on Christmas Day.

The sections below cover each feature category in turn.

Weather Features
----------------

Weather is the dominant exogenous driver of short-term load. OpenSTEF groups weather transforms under ``openstef_models.transforms.weather_domain``.

**Radiation and solar generation**

``RadiationDerivedFeaturesAdder`` takes a raw irradiance column and the geographic coordinate of the forecast location and derives features that capture the solar generation potential — accounting for sun angle, day length, and seasonal variation. This is particularly important for grids with significant behind-the-meter PV, where generation offsets measured load in ways that are invisible without solar context.

**Atmospheric conditions**

``AtmosphereDerivedFeaturesAdder`` combines pressure, relative humidity, and temperature into derived meteorological quantities. Temperature alone is a strong predictor of heating and cooling demand, but the derived features capture non-linear interactions — for example, apparent temperature (the "feels like" value) correlates better with residential heating load than dry-bulb temperature.

**Wind power**

``WindPowerFeatureAdder`` estimates wind power output from a wind speed column. It applies the wind profile power law to extrapolate from measurement height to hub height, then maps the result through a parameterised power curve. For substations serving wind farms, this feature can dramatically reduce forecast error.

**Daylight**

``DaylightFeatureAdder`` uses the forecast location's coordinate to compute sunrise, sunset, and solar elevation angle. This is a clean, physics-based signal for the daily load envelope that does not require a weather forecast input.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

   weather_transforms = [
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=(52.3, 4.9),   # (lat, lon) of the substation
           radiation_column="radiation",
       ),
       DaylightFeatureAdder(coordinate=(52.3, 4.9)),
   ]

Time and Calendar Features
--------------------------

Even without any weather data, time itself is highly informative. OpenSTEF provides several transforms under ``openstef_models.transforms.time_domain``.

**Cyclic encoding**

``CyclicFeaturesAdder`` encodes periodic time components — hour of day, day of week, month of year — as sine/cosine pairs. This is important because naive integer encoding (hour = 23, hour = 0) creates a false discontinuity at midnight. Cyclic encoding preserves the circular topology of time so that the model sees 23:45 and 00:15 as close together.

**Datetime features**

``DatetimeFeaturesAdder`` adds raw calendar columns (hour, weekday, month, quarter, and similar) for models that benefit from direct integer representations alongside the cyclic ones. The ``onehot_encode`` parameter controls whether these are one-hot expanded or kept as ordinal integers.

**Holiday indicators**

``HolidayFeatureAdder`` uses the ``holidays`` library to generate a binary ``is_holiday`` column and per-holiday binary columns (``is_christmas_day``, ``is_new_years_day``, etc.) for a given country. Holidays cause load profiles that look nothing like the surrounding weekdays; without this signal, models trained on weekday data will produce badly wrong forecasts on public holidays.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from pydantic_extra_types.country import CountryAlpha2

   time_transforms = [
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
   ]

Load Pattern Features
---------------------

Historical load values, when correctly aligned to the forecast horizon, are among the most powerful predictors available.

**Lag features**

``LagsAdder`` generates lag columns from the target series. Crucially, it is horizon-aware: for a 4-hour-ahead forecast it will only include lags that are actually available at prediction time (i.e., observations at least 4 hours in the past). This prevents data leakage — a common source of over-optimistic offline evaluation that disappears in production.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import LagsAdder

   lags_transform = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[timedelta(hours=1), timedelta(hours=4), timedelta(hours=24)],
       add_trivial_lags=True,
       target_column="load",
   )

The ``add_trivial_lags`` flag includes the most recent available observation for each horizon — the single strongest individual predictor in most energy forecasting tasks.

**Rolling aggregates**

``RollingAggregatesAdder`` computes rolling statistics (mean, standard deviation, and others) over configurable windows and horizons. These features capture slowly-evolving trends and volatility that individual lag values miss.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   rolling_transform = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )

.. note::

   Lag and rolling features are the primary mechanism through which the model learns autocorrelation structure. They are not a substitute for a proper time-series model — they are how you give a classical ML model the information it needs to behave like one.

Assembling a Feature Pipeline
------------------------------

All transforms share the ``TimeSeriesTransform`` interface and can be composed into a ``TransformPipeline`` that is passed to ``ForecastingModel`` as its preprocessing stage. The pipeline calls ``fit`` on each transform in order during training and ``transform`` during both training and inference.

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_models.transforms.general import (
       OutlierHandler,
       Scaler,
       EmptyFeatureRemover,
   )

   horizons = [timedelta(hours=1), timedelta(hours=4), timedelta(hours=24)]

   preprocessing = [
       # Lag and rolling history
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=True,
           target_column="load",
       ),
       RollingAggregatesAdder(
           feature="load",
           aggregation_functions=["mean", "std"],
           horizons=horizons,
       ),
       # Weather-derived features
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=(52.3, 4.9),
           radiation_column="radiation",
       ),
       DaylightFeatureAdder(coordinate=(52.3, 4.9)),
       # Calendar features
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
       # Standardisation
       OutlierHandler(mode="standard"),
       Scaler(method="standard"),
       EmptyFeatureRemover(),
   ]

Adding Custom Features
----------------------

If the built-in transforms do not cover a domain-specific signal you need — industrial process schedules, tide tables, local event calendars — you can implement your own transform by subclassing ``TimeSeriesTransform`` from ``openstef_core``.

The interface requires two things: a ``transform`` method that accepts and returns a ``TimeSeriesDataset``, and a ``features_added`` method that declares which column names the transform introduces. Stateless transforms (those that do not learn parameters from training data) need not override ``fit``.

.. code-block:: python

   from typing import override
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class IndustrialShiftFeatureAdder(TimeSeriesTransform):
       """Adds a binary feature indicating industrial shift hours (06:00-22:00 weekdays)."""

       @override
       def features_added(self) -> list[str]:
           return ["is_industrial_shift"]

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           index = data.data.index
           is_weekday = index.dayofweek < 5
           is_shift_hour = (index.hour >= 6) & (index.hour < 22)
           data.data["is_industrial_shift"] = (is_weekday & is_shift_hour).astype(float)
           return data

Drop your custom transform into the preprocessing list alongside the built-in ones — the pipeline treats it identically.

.. warning::

   Custom transforms that learn state during ``fit`` (e.g., computing a rolling baseline from training data) must set ``is_fitted`` to ``False`` before fitting and ``True`` afterwards, and must be serialisable alongside the model. Stateless transforms like the example above carry no such requirement.

What Makes a Good Feature
--------------------------

A few practical principles guide feature selection for energy forecasting:

- **Causal relevance over correlation.** Features grounded in physical or behavioural causation (temperature → heating demand) generalise better than spurious correlations that happen to appear in the training window.
- **Availability at inference time.** A feature is only useful if it can be computed when you need to make a forecast. Weather forecasts are available; actual measured load at the forecast horizon is not. ``LagsAdder`` enforces this automatically, but custom features require the same discipline.
- **Avoid leakage through aggregation.** Rolling statistics computed over a window that includes future observations will produce unrealistically good training metrics. Always verify that aggregation windows respect the forecast horizon.
- **Prefer derived physical quantities over raw inputs.** Raw wind speed is less informative than estimated wind power output; raw irradiance is less informative than solar angle-corrected irradiance. The built-in weather transforms embody this principle.
- **Remove empty features.** After all transforms have run, ``EmptyFeatureRemover`` drops columns that are entirely NaN — a common outcome when a weather input column is absent from a particular dataset. This keeps the feature matrix clean without requiring manual bookkeeping.

[VISUALIZATION: Bar chart of feature importances from a trained XGBoost model, showing relative contribution of lag features, weather features, and calendar features across a representative substation]

Related Topics
--------------

- :doc:`forecasting_basics` — what short-term forecasting is and how OpenSTEF approaches it
- :doc:`quantiles_and_confidence` — how uncertainty is represented in probabilistic forecasts
- :doc:`component_splitting` — decomposing aggregate load into physical components, which changes which features are most relevant
- :doc:`reliability_and_fallback` — what happens when feature inputs are missing or degraded at inference time