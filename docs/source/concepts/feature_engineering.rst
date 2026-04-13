Feature Engineering
===================

Good forecasts depend on good features. A raw load time series alone carries limited predictive signal — the model also needs to know whether it is a Monday morning or a Sunday night, whether a heat wave is approaching, and what the load looked like at the same hour last week. This page explains how OpenSTEF's feature engineering pipeline works, which feature families it provides out of the box, and how to extend it with your own domain knowledge.

For background on why short-term forecasting matters and what the overall workflow looks like, see :doc:`forecasting_basics`. For details on how uncertainty is represented in the output, see :doc:`quantiles_and_confidence`.

.. note:: [DIAGRAM: Feature engineering pipeline — raw inputs (load, weather, timestamp) flow through a series of transform steps (feature adders → standardizers → EmptyFeatureRemover) to produce the feature matrix fed to the model.]

What Makes a Good Feature for Energy Forecasting
-------------------------------------------------

Energy consumption is driven by a small number of well-understood physical and social factors: temperature, daylight, human schedules, and recent consumption history. A feature is useful when it captures one of these drivers in a form the model can exploit.

Three properties matter most:

- **Availability at forecast time.** A feature that is only known after the fact cannot be used in production. Weather *forecasts* are available; weather *actuals* are not (for future horizons). OpenSTEF's built-in transforms are designed with this constraint in mind.
- **Stable relationship with the target.** Features that correlate with load today but not tomorrow add noise rather than signal. Physically motivated features — solar irradiance, temperature — tend to be stable across seasons and years.
- **Low redundancy.** Highly correlated features increase model complexity without adding information. OpenSTEF includes an ``EmptyFeatureRemover`` standardizer that drops constant or near-empty columns automatically.

OpenSTEF embeds domain knowledge directly into its transform library. Rather than leaving feature construction to the user, the library ships a rich set of ready-made transforms that cover the most important predictor families.

Weather Features
----------------

Weather is the single strongest external driver of electricity demand and renewable generation. OpenSTEF provides dedicated transforms for both raw weather variables and derived physical quantities.

**Radiation and solar power**

``RadiationDerivedFeaturesAdder`` takes a measured or forecast global horizontal irradiance (GHI) column and the geographic coordinate of the grid point, then derives features such as clear-sky irradiance and the ratio of actual to clear-sky radiation. This ratio (the *clearness index*) is a much more stable predictor than raw GHI because it removes the predictable diurnal and seasonal envelope, leaving only cloud-related variability.

``SolarPowerFeatureAdder`` goes one step further: it estimates the expected PV generation for a given installed capacity, orientation, and tilt angle. This is particularly valuable when the load series contains embedded PV generation that must be partially "explained away" before the net load can be forecast.

**Wind**

``WindPowerFeatureAdder`` converts a wind speed forecast into an estimated wind power output using a configurable power curve. Like the solar adder, it translates a meteorological variable into the energy domain that the model is actually trying to predict.

**Atmospheric conditions**

``AtmosphereDerivedFeaturesAdder`` combines temperature, relative humidity, and pressure into derived quantities such as apparent temperature (heat index / wind chill). Apparent temperature correlates more strongly with heating and cooling demand than dry-bulb temperature alone.

**Daylight**

``DaylightFeatureAdder`` computes sunrise and sunset times for the configured coordinate and derives features such as hours of daylight and whether the current timestamp falls within daylight hours. This is especially useful for capturing the sharp morning and evening load ramps that are difficult to learn from time-of-day features alone.

.. code-block:: python

   from pydantic_extra_types.coordinate import Coordinate
   from openstef_models.transforms.weather_domain import (
       RadiationDerivedFeaturesAdder,
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       WindPowerFeatureAdder,
   )

   coordinate = Coordinate(latitude=52.37, longitude=4.90)  # Amsterdam

   weather_transforms = [
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="radiation",
       ),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       DaylightFeatureAdder(coordinate=coordinate),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
   ]

Time and Calendar Features
--------------------------

Human behaviour follows strong cyclic patterns — the morning commute, the weekend, the summer holiday. Capturing these patterns requires features that encode calendar position in a way tree-based models can use.

**Datetime features**

``DatetimeFeaturesAdder`` extracts scalar calendar components from the timestamp index: hour of day, day of week, day of month, month, and year. When ``onehot_encode=False`` (the default for XGBoost), these are passed as integer columns, allowing the model to learn non-linear calendar effects directly.

**Cyclic features**

Integer hour-of-day has an artificial discontinuity: hour 23 and hour 0 are numerically far apart but temporally adjacent. ``CyclicFeaturesAdder`` resolves this by encoding periodic calendar variables as sine/cosine pairs, so that the distance in feature space reflects the true cyclic distance in time.

**Holiday features**

``HolidayFeatureAdder`` adds a binary indicator for public holidays using a country-specific calendar. Load on public holidays often resembles a Sunday profile regardless of the actual day of week, so this feature can substantially improve accuracy around national holidays.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )

   time_transforms = [
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code="NL"),
   ]

Load History: Lag and Rolling Features
---------------------------------------

Past load is often the strongest predictor of future load. A substation that consumed 50 MW at this hour last week will likely consume a similar amount this week, all else being equal. OpenSTEF captures this through two complementary mechanisms.

**Lag features**

Lag features present the model with the actual load value at a fixed time offset in the past. OpenSTEF provides three helper functions for generating lag configurations:

- ``generate_minute_lags`` — short-horizon lags at sub-hourly resolution, useful for the first few hours of the forecast horizon.
- ``generate_day_lags`` — lags at 24 h, 48 h, and 168 h (one week), capturing daily and weekly periodicity.
- ``generate_autocorr_lags`` — data-driven lag selection based on autocorrelation peaks in the training series. This is the most principled approach when the dominant periodicity is not known in advance.

**Rolling aggregates**

``RollingAggregatesAdder`` computes rolling statistics (mean, median, min, max, or any combination) over a configurable window and appends them as features. Rolling features smooth out noise and give the model a sense of recent trend rather than just a single historical snapshot.

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   # Assume `df` is a DataFrame with a 'load' column and a DatetimeIndex
   dataset = TimeSeriesDataset(df, timedelta(hours=1))

   rolling_adder = RollingAggregatesAdder(
       feature="load",
       rolling_window_size=timedelta(hours=24),
       aggregation_functions=["mean", "max"],
       horizons=[timedelta(hours=36)],
   )
   rolling_adder.fit(dataset)
   dataset_with_rolling = rolling_adder.transform(dataset)
   # New columns: 'rolling_mean_load_PT24H', 'rolling_max_load_PT24H'

.. note::

   During inference the target column is not yet known for future timestamps.
   ``RollingAggregatesAdder`` handles this automatically: it forward-fills from
   the last computed aggregate and falls back to the aggregate computed during
   training if no recent data is available.

Assembling a Full Feature Pipeline
------------------------------------

In practice, feature adders are composed into a preprocessing pipeline alongside standardization steps. The pipeline is executed in order, so each transform sees the output of all previous transforms.

.. code-block:: python

   from openstef_models.transforms.standardization import (
       Clipper,
       EmptyFeatureRemover,
       Scaler,
   )
   from openstef_core.transforms import TransformPipeline
   from openstef_core.selection import Exclude

   preprocessing = TransformPipeline(
       transforms=[
           # Weather features
           RadiationDerivedFeaturesAdder(
               coordinate=coordinate,
               radiation_column="radiation",
           ),
           AtmosphereDerivedFeaturesAdder(
               pressure_column="pressure",
               relative_humidity_column="humidity",
               temperature_column="temperature",
           ),
           DaylightFeatureAdder(coordinate=coordinate),
           WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
           # Load history
           RollingAggregatesAdder(
               feature="load",
               rolling_window_size=timedelta(hours=24),
               aggregation_functions=["mean", "max"],
               horizons=[timedelta(hours=36)],
           ),
           # Calendar features
           CyclicFeaturesAdder(),
           DatetimeFeaturesAdder(onehot_encode=False),
           HolidayFeatureAdder(country_code="NL"),
           # Standardization
           Scaler(selection=Exclude("load"), method="standard"),
           EmptyFeatureRemover(),
       ]
   )

The ``EmptyFeatureRemover`` at the end ensures that any feature column that is entirely missing — for example because an optional weather feed was unavailable — is dropped before the data reaches the model. This makes the pipeline robust to partial data outages without requiring manual intervention.

Adding Custom Features
-----------------------

When the built-in transforms do not cover a domain-specific signal — energy prices, industrial production schedules, grid topology indicators — you can implement a custom transform by subclassing ``TimeSeriesTransform``.

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class EnergyPriceRatioAdder(BaseConfig, TimeSeriesTransform):
       """Add the ratio of day-ahead price to its 7-day rolling mean."""

       price_column: str = "day_ahead_price"

       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # No state to learn from training data

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           rolling_mean = df[self.price_column].rolling("7D").mean()
           df["price_ratio_7d"] = df[self.price_column] / rolling_mean.clip(lower=1e-6)
           return TimeSeriesDataset(df, data.resolution)

       @property
       def features_added(self) -> list[str]:
           return ["price_ratio_7d"]

Once implemented, the custom transform slots into the pipeline exactly like any built-in adder — simply include it in the ``transforms`` list passed to ``TransformPipeline``.

.. note::

   Keep custom transforms stateless where possible. If a transform must learn
   parameters from training data (e.g., a rolling baseline), implement ``fit``
   to store those parameters and use them in ``transform`` during inference.
   This ensures that training-time statistics are not inadvertently recomputed
   on inference data.

Feature Selection and Importance
----------------------------------

OpenSTEF does not currently include an automated feature selection step — the expectation is that domain knowledge guides which transforms are included. However, tree-based models such as XGBoost and LightGBM expose feature importance scores after training, which can be used to audit whether the engineered features are actually being used.

If a feature consistently receives near-zero importance across multiple training runs, it is a candidate for removal. Conversely, if a physically motivated feature (e.g., the clearness index) ranks low, it may indicate a data quality problem in the input feed rather than a problem with the feature itself.

For guidance on which model to pair with a given feature set, see :doc:`model_selection`. For information on how feature quality affects forecast reliability in production, see :doc:`reliability_and_fallback`.