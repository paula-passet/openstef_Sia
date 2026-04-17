Feature Engineering
===================

Good forecasts depend on good features. OpenSTEF's classical ML models — XGBoost, LightGBM, and linear variants — achieve strong accuracy not through architectural complexity but through domain-aware feature engineering. This page explains the feature categories OpenSTEF provides, why each matters for energy forecasting, and how to compose or extend them in your own pipelines.

For background on what short-term forecasting is and why it is needed, see :doc:`forecasting_basics`. For information on how uncertainty is expressed in forecasts, see :doc:`quantiles_and_confidence`.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

Why Features Matter
-------------------

Energy load is driven by a small number of well-understood physical and social phenomena: temperature determines heating and cooling demand, sunlight drives solar generation, time-of-day and day-of-week shape human activity patterns, and public holidays disrupt those patterns. A model that receives raw timestamps and a handful of weather scalars must discover all of this structure from data alone. Encoding it explicitly as features dramatically reduces the amount of training data required and makes models more robust when conditions shift.

OpenSTEF organises its feature transforms into four domains, each exposed as a composable ``TimeSeriesTransform`` object:

- **Time domain** — cyclic encodings, datetime components, holidays, lags, rolling aggregates
- **Weather domain** — atmosphere-derived features, radiation-derived features, daylight
- **Energy domain** — wind power estimates
- **General** — scaling, outlier handling, dimensionality reduction

All transforms share the same ``fit`` / ``transform`` interface and can be inspected with ``features_added()`` to see exactly which columns they produce.

Time Features
-------------

Human behaviour is the dominant driver of electricity demand, and human behaviour is strongly periodic. OpenSTEF provides several transforms that capture this periodicity.

**Cyclic encodings** are the most important time features to get right. Representing hour-of-day as an integer (0–23) tells the model that hour 23 and hour 0 are far apart, when in reality they are adjacent. ``CyclicFeaturesAdder`` encodes temporal cycles as sine/cosine pairs so that the distance between any two points on the cycle is geometrically correct:

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   cyclic = CyclicFeaturesAdder()
   dataset_with_cyclic = cyclic.transform(dataset)
   print(cyclic.features_added())
   # e.g. ['hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos', ...]

**Raw datetime components** such as month, week number, and day of week are added by ``DatetimeFeaturesAdder``. These complement cyclic features when tree-based models benefit from explicit split points:

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

   dt_features = DatetimeFeaturesAdder(onehot_encode=False)
   dataset_with_dt = dt_features.transform(dataset)

**Holiday features** capture the sharp demand drops that occur on public holidays. Because holidays vary by country, ``HolidayFeatureAdder`` requires a country code and generates one binary indicator per named holiday in that country's calendar:

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   from pydantic_extra_types.country import CountryAlpha2

   holidays = HolidayFeatureAdder(country_code=CountryAlpha2("NL"))
   dataset_with_holidays = holidays.transform(dataset)

.. note::

   Holiday effects are often asymmetric — Christmas Eve may suppress demand more than Christmas Day. Including individual named holidays rather than a single binary flag lets the model learn these differences.

Load Patterns: Lags and Rolling Aggregates
------------------------------------------

The single most informative predictor of load at time *t* is usually load at time *t − 24h* (the same hour yesterday) or *t − 168h* (the same hour last week). These **lag features** give the model direct access to the autocorrelation structure of the series.

``LagsAdder`` generates lag features that are causally valid for each forecast horizon. This is a critical correctness concern: a lag that looks back only 15 minutes cannot be used when forecasting 4 hours ahead, because that data will not be available at inference time. OpenSTEF enforces this automatically through the ``horizons`` parameter:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   lags = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[timedelta(minutes=15), timedelta(hours=1), timedelta(hours=4)],
       add_trivial_lags=True,
       target_column="load",
   )
   lags.fit(dataset)
   dataset_with_lags = lags.transform(dataset)

**Rolling aggregates** smooth over short-term noise and capture recent trends. ``RollingAggregatesAdder`` computes statistics such as mean, median, min, and max over a rolling window of the target series. Like ``LagsAdder``, it respects forecast horizons and falls back gracefully when recent target data is unavailable at inference time:

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   rolling = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "max"],
       horizons=[timedelta(hours=1), timedelta(hours=4)],
   )
   rolling.fit(dataset)
   dataset_with_rolling = rolling.transform(dataset)

Together, lags and rolling aggregates give the model a compact representation of recent load history without requiring a recurrent architecture.

Weather Features
----------------

Weather is the primary exogenous driver of energy load. OpenSTEF provides three weather-domain transforms that go beyond passing raw sensor readings directly to the model.

**Atmosphere-derived features** compute physically meaningful combinations of pressure, relative humidity, and temperature. Apparent temperature (the "feels like" temperature that drives heating and cooling behaviour) is a non-linear function of these three variables; providing it as an explicit feature is more informative than leaving the model to discover the relationship:

.. code-block:: python

   from openstef_models.transforms.weather_domain.atmosphere_derived_features_adder import (
       AtmosphereDerivedFeaturesAdder,
   )

   atm = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="humidity",
       temperature_column="temperature",
   )
   dataset_with_atm = atm.transform(dataset)

**Radiation-derived features** are essential for grids with significant solar generation. ``RadiationDerivedFeaturesAdder`` uses the site's geographic coordinates to compute solar position (elevation and azimuth) and combines this with measured irradiance to produce features that correlate directly with PV output:

.. code-block:: python

   from openstef_models.transforms.weather_domain.radiation_derived_features_adder import (
       RadiationDerivedFeaturesAdder,
   )
   from openstef_core.types import Coordinate

   radiation = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(lat=52.37, lon=4.90),
       radiation_column="global_radiation",
   )
   dataset_with_radiation = radiation.transform(dataset)

**Daylight features** from ``DaylightFeatureAdder`` encode sunrise and sunset times for the location. These are particularly useful as gating features: solar generation is strictly zero outside daylight hours, and a model that knows this can avoid fitting spurious correlations in night-time data.

**Wind power features** from ``WindPowerFeatureAdder`` apply a wind power curve to convert wind speed into an estimated power output. This non-linear transformation (wind power scales roughly with the cube of wind speed up to rated capacity) is much more informative to a linear or tree-based model than raw wind speed alone:

.. code-block:: python

   from openstef_models.transforms.energy_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )

   wind = WindPowerFeatureAdder(windspeed_reference_column="wind_speed")
   dataset_with_wind = wind.transform(dataset)

Composing a Feature Pipeline
-----------------------------

In practice, transforms are composed into a ``FeaturePipeline`` that is applied consistently during both training and inference. The pipeline below reflects the standard OpenSTEF configuration for an XGBoost model:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.weather_domain.atmosphere_derived_features_adder import (
       AtmosphereDerivedFeaturesAdder,
   )
   from openstef_models.transforms.weather_domain.radiation_derived_features_adder import (
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.weather_domain.daylight_feature_adder import (
       DaylightFeatureAdder,
   )
   from openstef_models.transforms.energy_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.types import Coordinate

   coordinate = Coordinate(lat=52.37, lon=4.90)
   horizons = [timedelta(minutes=15), timedelta(hours=1), timedelta(hours=4)]

   feature_adders = [
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=True,
           target_column="load",
       ),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="global_radiation",
       ),
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=coordinate),
       RollingAggregatesAdder(
           feature="load",
           aggregation_functions=["mean", "max"],
           horizons=horizons,
       ),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
       DatetimeFeaturesAdder(onehot_encode=False),
   ]

Each transform in the list is applied in sequence. Transforms that require fitting (``LagsAdder``, ``RollingAggregatesAdder``) learn statistics from training data and apply the same transformation at inference time.

Adding Custom Features
----------------------

Because every transform implements the ``TimeSeriesTransform`` interface, you can inject domain-specific features by writing a class with ``fit`` and ``transform`` methods and inserting it into the pipeline list. A common use case is incorporating a price signal or a grid-topology indicator:

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform
   from openstef_core.base_model import BaseConfig

   class EnergyPriceFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add day-ahead energy price as a feature."""

       price_column: str = "day_ahead_price"

       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # stateless transform

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Example: add a lagged price feature (price known day-ahead)
           df = data.dataframe.copy()
           df["price_lag_24h"] = df[self.price_column].shift(96)  # 96 × 15 min = 24 h
           return TimeSeriesDataset(dataframe=df)

       def features_added(self) -> list[str]:
           return ["price_lag_24h"]

Insert the custom transform into the ``feature_adders`` list at the appropriate position and it will be treated identically to any built-in transform.

.. note::

   When adding custom features, ensure that any look-back window respects the forecast horizon. A feature derived from data that will not be available at inference time will cause data leakage and over-optimistic validation metrics.

What Makes a Good Feature
--------------------------

The transforms described above embody several principles that apply whenever you design new features for energy forecasting:

- **Physical interpretability.** Features grounded in physical relationships (apparent temperature, wind power curve, solar position) generalise better than purely statistical constructs because the underlying relationship is stable across seasons and years.

- **Causal validity.** Every feature used at inference time must be available at the moment the forecast is made. Weather forecasts are available; actual load at the forecast horizon is not. OpenSTEF's lag and rolling-aggregate transforms enforce this automatically.

- **Cyclic correctness.** Encode periodic quantities (hour, day of week, month) as sine/cosine pairs rather than raw integers to preserve the circular topology of time.

- **Explicit non-linearities.** Tree-based models can approximate non-linear relationships, but providing explicit transformations (wind power curve, apparent temperature) reduces the depth of tree required and improves generalisation on small datasets.

- **Sparse holiday indicators.** A single ``is_holiday`` binary flag loses information. Named holiday indicators let the model learn that New Year's Day and a mid-week bank holiday have different demand profiles.

For information on how the model handles situations where features are missing or stale at inference time, see :doc:`reliability_and_fallback`.