Feature Engineering
===================

Good forecasts depend on good features. Raw load measurements and weather readings alone rarely give a model enough context to distinguish a cold Monday morning from a warm Sunday afternoon — yet that distinction can mean hundreds of megawatts of difference on a distribution grid. This page explains the feature categories OpenSTEF uses, why each matters for energy forecasting, and how to work with the library's built-in transforms as well as your own custom features.

For background on what short-term forecasting is and why it is needed, see :doc:`forecasting_basics`. For an explanation of how OpenSTEF expresses forecast uncertainty through quantiles, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Feature engineering pipeline — raw inputs (load history, weather, calendar) flow through transform stages (lag generation, cyclic encoding, weather derivation) into a feature matrix consumed by the model]

Why Features Matter
-------------------

OpenSTEF's models are predominantly classical machine learning algorithms — XGBoost, LightGBM, and linear models. Unlike deep learning architectures that can learn temporal structure directly from sequences, these models require that temporal and physical relationships be made explicit in the input matrix. Feature engineering is therefore not an optional refinement; it is where the domain knowledge lives.

A well-engineered feature set lets a gradient-boosted tree answer questions like:

- Is this a peak-demand hour on a weekday, or off-peak on a public holiday?
- How much solar generation should we expect given today's radiation forecast and the panel orientation at this grid point?
- What was the load doing at this same time last week, when conditions were similar?

The transforms described below are available in ``openstef_models.transforms`` and are composed into a pipeline during model training and inference.

Weather Features
----------------

Weather is the dominant driver of short-term load variability for most grid points. OpenSTEF ships several weather-domain transforms that convert raw meteorological inputs into physically meaningful predictors.

**Radiation and solar generation**

``RadiationDerivedFeaturesAdder`` takes a raw global horizontal irradiance column and the geographic coordinate of the grid point and derives features such as clear-sky index, solar elevation angle, and estimated PV output. These derived quantities are far more informative than raw radiation alone because they account for the time of day and season — the same radiation value means something very different at solar noon in June versus late afternoon in December.

**Wind power**

``WindPowerFeatureAdder`` converts wind speed to an estimated wind power output using a power-curve approximation. This is particularly useful for grid points with significant wind generation, where the cubic relationship between wind speed and power output makes the raw speed a poor linear predictor.

**Atmospheric conditions**

``AtmosphereDerivedFeaturesAdder`` derives additional predictors from pressure, relative humidity, and temperature — for example, apparent temperature (which correlates more closely with heating and cooling demand than dry-bulb temperature alone) and humidity-adjusted comfort indices.

**Daylight**

``DaylightFeatureAdder`` adds binary and continuous daylight indicators based on sunrise and sunset times calculated from the grid point's coordinates. This gives models a clean signal for the lighting-load component that is independent of cloud cover.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
   )
   from openstef_models.transforms.general import Coordinate

   coordinate = Coordinate(lat=52.1, lon=5.1)

   weather_transforms = [
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="radiation",
       ),
       DaylightFeatureAdder(coordinate=coordinate),
   ]

Each transform implements ``features_added()`` so you can inspect exactly which columns it will produce before fitting.

Time Features
-------------

Energy consumption follows strong periodic patterns — hourly, daily, and weekly cycles are present in almost every load series. OpenSTEF encodes these patterns in two complementary ways.

**Datetime features**

``DatetimeFeaturesAdder`` extracts calendar components such as hour of day, day of week, month, and quarter. When ``onehot_encode=False`` (the default for tree-based models), these are passed as integer-valued columns that the model can split on directly. One-hot encoding is available for linear models that cannot exploit ordinal structure.

**Cyclic encoding**

Integer hour-of-day has an artificial discontinuity: hour 23 and hour 0 are numerically far apart but temporally adjacent. ``CyclicFeaturesAdder`` resolves this by encoding periodic features as sine/cosine pairs, so that the distance in feature space reflects the true circular distance in time.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
   )

   time_transforms = [
       CyclicFeaturesAdder(),          # sin/cos encoding of hour, day-of-week, etc.
       DatetimeFeaturesAdder(onehot_encode=False),
   ]

**Holidays**

``HolidayFeatureAdder`` adds a binary indicator for each public holiday in the target country, using the country code from the grid point's location configuration. Holiday load profiles differ substantially from ordinary weekdays — offices are empty, industrial processes are paused — so these indicators carry significant predictive weight.

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   holiday_transform = HolidayFeatureAdder(country_code="NL")

   # Inspect which holiday columns will be added
   print(holiday_transform.features_added())

Load Pattern Features
---------------------

Historical load values, when added as lagged features, give the model direct access to recent demand patterns. OpenSTEF's lag generation utilities are designed specifically for energy time series.

**Lag features**

The ``LagAdder`` (and its versioned variant ``VersionedLagsAdder``) adds columns for load values at specified time offsets. Rather than choosing lags arbitrarily, OpenSTEF provides helper functions that generate sensible lag sets:

- ``generate_minute_lags`` — short-term lags at sub-hourly resolution, useful for capturing inertia in the load signal within the first few hours of the forecast horizon.
- ``generate_day_lags`` — lags at 24-hour multiples, capturing the same-time-yesterday and same-time-last-week patterns that dominate medium-term load forecasting.
- ``generate_autocorr_lags`` — data-driven lag selection based on autocorrelation peaks in the training series, so that only statistically significant lags are retained.

**Rolling aggregates**

``RollingAggregatesAdder`` computes rolling statistics (mean, standard deviation, min, max) over configurable windows and forecast horizons. These features capture the recent level and volatility of load, which is especially useful when the series has slow-moving trends or regime changes. The transform stores fallback values from training so that it degrades gracefully when recent history is unavailable at inference time — an important property for production systems (see :doc:`reliability_and_fallback`).

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   rolling_transform = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std"],
       horizons=[1, 24, 168],   # 1h, 24h, 1 week ahead
   )

Custom Features
---------------

OpenSTEF's transform pipeline is composable, so you can insert domain-specific features alongside the built-in ones. Any object that implements the ``TimeSeriesTransform`` interface — providing ``fit``, ``transform``, and ``features_added`` methods — can be dropped into the pipeline.

A common use case is adding grid-specific contextual signals: industrial process schedules, electric vehicle charging patterns, or local event calendars that are not captured by generic weather or calendar features.

.. code-block:: python

   from openstef_models.transforms.base import TimeSeriesTransform, BaseConfig
   from openstef_models.data import TimeSeriesDataset
   import pandas as pd

   class IndustrialScheduleAdder(BaseConfig, TimeSeriesTransform):
       """Add a binary feature indicating scheduled industrial activity."""

       schedule_column: str = "industrial_schedule"

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Mark hours 06:00–22:00 on weekdays as active production periods
           index = data.df.index
           is_production = (
               (index.hour >= 6) & (index.hour < 22) & (index.dayofweek < 5)
           ).astype(float)
           data.df["industrial_active"] = is_production
           return data

       def features_added(self) -> list[str]:
           return ["industrial_active"]

   # Compose with built-in transforms
   pipeline_transforms = [
       *weather_transforms,
       *time_transforms,
       IndustrialScheduleAdder(),
   ]

.. note::

   Custom transforms should be stateless where possible, or store any fitted state (such as scaling parameters) explicitly so that the same state is applied consistently at training and inference time.

What Makes a Good Feature
--------------------------

Not every signal that correlates with load in historical data makes a good feature. A few principles that apply specifically to energy forecasting:

**Availability at forecast time.** A feature is only useful if it can be computed for the future timestamps being forecast. Historical load values are available as lags, but the *actual* future load is not. Weather forecasts are available but introduce their own uncertainty; see :doc:`quantiles_and_confidence` for how OpenSTEF propagates that uncertainty into prediction intervals.

**Physical interpretability.** Features grounded in physical relationships — solar elevation driving PV output, temperature driving heating demand — generalise better across seasons and years than purely statistical correlations that may be artefacts of the training period.

**Avoiding data leakage.** Rolling aggregates and lag features must be computed using only data that would have been available at the time the forecast was made. OpenSTEF's built-in transforms handle this correctly by respecting the forecast horizon when constructing lag offsets.

**Sparsity and redundancy.** Adding many highly correlated features rarely improves accuracy and can slow training. The ``EmptyFeatureRemover`` transform, applied at the end of the feature pipeline, drops columns that are entirely missing or zero-variance, preventing them from consuming model capacity.

The interplay between feature quality and model choice is discussed further in :doc:`model_selection`.