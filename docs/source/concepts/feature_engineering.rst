Feature Engineering
===================

Good forecasts depend on good features. Raw load measurements and weather readings rarely tell the full story on their own — it is the *derived* features that give a model the context it needs to distinguish a cold Tuesday morning in January from a warm bank-holiday Monday in August. This page explains the feature categories that matter most for short-term energy forecasting and shows how to work with OpenSTEF's built-in feature transforms.

.. note::

   This page focuses on feature construction. For an introduction to the forecasting problem itself, see :doc:`forecasting_basics`. For how uncertainty is represented in the output, see :doc:`quantiles_and_confidence`.

---

Why Features Matter for Energy Forecasting
-------------------------------------------

Energy load is driven by human behaviour and physical processes that repeat on predictable cycles: the morning kettle, the evening commute, the solar noon, the winter heating peak. A model that can see these patterns explicitly — rather than having to infer them from raw timestamps — learns faster, generalises better, and degrades more gracefully when data is sparse.

OpenSTEF encodes decades of domain knowledge into a library of composable *transform* classes. Each transform takes a :class:`TimeSeriesDataset`, adds one or more feature columns, and returns the enriched dataset. You can use these transforms individually or chain them into a preprocessing pipeline.

.. note:: [DIAGRAM: Feature engineering pipeline — raw inputs (load, weather, datetime index) flow through a series of transform blocks (LagsAdder, WeatherFeatures, CyclicFeaturesAdder, HolidayFeatureAdder) to produce a feature matrix fed into the forecaster.]

---

Time-Based Features
--------------------

The most universally useful features are derived directly from the datetime index. OpenSTEF provides two transforms for this.

**DatetimeFeaturesAdder** extracts calendar fields such as hour of day, day of week, day of month, month, and year. These give the model a direct handle on the daily and weekly load cycles that dominate most grid points.

**CyclicFeaturesAdder** goes one step further. Calendar integers like "hour = 23" and "hour = 0" are numerically far apart even though they represent adjacent moments in time. Cyclic encoding wraps these values onto a unit circle using sine and cosine projections, so the model sees continuity across midnight, across the end of the week, and across the year boundary.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
   )
   from openstef_core.datasets import TimeSeriesDataset

   # dataset is a TimeSeriesDataset with a DatetimeIndex
   dataset = DatetimeFeaturesAdder().transform(dataset)
   dataset = CyclicFeaturesAdder().transform(dataset)

Both transforms are stateless — they derive everything from the index — so they require no fitting step and add no risk of data leakage.

Holiday Features
^^^^^^^^^^^^^^^^

Public holidays break the normal weekly pattern. A model trained only on weekday/weekend signals will systematically mis-forecast Christmas Day or a national bank holiday. :class:`HolidayFeatureAdder` uses the ``holidays`` library to add a binary ``is_holiday`` column plus one binary column per named holiday for the specified country.

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder
   from pydantic_extra_types.country import CountryAlpha2

   adder = HolidayFeatureAdder(country_code=CountryAlpha2("NL"))
   dataset = adder.transform(dataset)
   # New columns: is_holiday, is_christmas_day, is_kings_day, ...

The country code follows the ISO 3166-1 alpha-2 standard. Choosing the right country is important: a grid point in Belgium should use ``"BE"``, not ``"NL"``, even if the operating company is headquartered across the border.

---

Weather Features
-----------------

Weather is the dominant external driver of energy load. OpenSTEF provides a dedicated set of weather-domain transforms under ``openstef_models.transforms.weather_domain``.

**AtmosphereDerivedFeaturesAdder** computes derived meteorological features from basic weather inputs — temperature, relative humidity, and atmospheric pressure. Derived quantities such as apparent temperature (which combines heat and humidity into a perceived-temperature index) are often more predictive of cooling and heating load than raw temperature alone.

**RadiationDerivedFeaturesAdder** combines measured solar radiation with the geographic coordinates of the grid point to produce features that capture the solar generation potential at that location. This is particularly important for distribution grids with significant rooftop PV penetration, where net load can go negative on sunny afternoons.

**WindPowerFeatureAdder** derives wind-power-relevant features from wind speed measurements. Wind speed has a cubic relationship with power output, so the raw measurement is a poor linear predictor; the transform handles this non-linearity explicitly.

**DaylightFeatureAdder** adds features based on sunrise and sunset times computed from the grid point's coordinates. These features capture the sharp load transitions at dawn and dusk that are difficult for a model to learn from radiation data alone when cloud cover is variable.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
       DaylightFeatureAdder,
   )
   from openstef_core.types import Coordinate

   location = Coordinate(lat=52.37, lon=4.90)  # Amsterdam

   dataset = AtmosphereDerivedFeaturesAdder(
       temperature_column="temperature",
       relative_humidity_column="humidity",
       pressure_column="pressure",
   ).transform(dataset)

   dataset = RadiationDerivedFeaturesAdder(
       coordinate=location,
       radiation_column="radiation",
   ).transform(dataset)

   dataset = WindPowerFeatureAdder(
       windspeed_reference_column="wind_speed",
   ).transform(dataset)

   dataset = DaylightFeatureAdder(coordinate=location).transform(dataset)

.. note::

   Weather features require that the corresponding columns are present in the input dataset. If a weather feed is unavailable, the column can be omitted and the relevant transform skipped — OpenSTEF's fallback mechanisms handle missing inputs gracefully. See :doc:`reliability_and_fallback` for details.

---

Load History: Lags and Rolling Aggregates
-------------------------------------------

Past load is one of the strongest predictors of future load. OpenSTEF provides two transforms that encode load history.

Lag Features
^^^^^^^^^^^^

:class:`LagsAdder` creates lagged copies of the target column — for example, the load value 24 hours ago, 48 hours ago, and one week ago. These lags capture the strong daily and weekly autocorrelation present in most load series.

The transform is horizon-aware: it only adds lags that are genuinely available at the time a forecast would be made. A 15-minute-ahead forecast can use a lag of 15 minutes; a 36-hour-ahead forecast cannot. This prevents the silent data leakage that is easy to introduce when constructing lags manually.

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from datetime import timedelta

   adder = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[timedelta(minutes=15), timedelta(hours=24)],
       target_column="load",
       add_trivial_lags=True,
   )
   dataset = adder.transform(dataset)

Rolling Aggregates
^^^^^^^^^^^^^^^^^^

:class:`RollingAggregatesAdder` computes rolling statistics (mean, standard deviation, and similar) over configurable windows. Where a lag captures a single historical point, a rolling aggregate captures the *trend* over a recent period — useful for detecting whether load has been unusually high or low in the past few hours.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from datetime import timedelta

   adder = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std"],
       horizons=[timedelta(hours=24), timedelta(hours=48)],
   )
   adder.fit(dataset)   # stores fallback values from training data
   dataset = adder.transform(dataset)

Note that :class:`RollingAggregatesAdder` has a ``fit`` step: it stores the last valid aggregate values from the training set so that, at inference time, it can fall back to those values if recent history is incomplete.

---

Assembling a Feature Pipeline
-------------------------------

In practice you will combine several transforms into a single preprocessing pipeline. The example below shows a representative configuration for a grid point with weather inputs and a moderate history window.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_core.transforms import TransformPipeline
   from openstef_core.types import Coordinate, LeadTime
   from pydantic_extra_types.country import CountryAlpha2
   from datetime import timedelta

   location = Coordinate(lat=52.37, lon=4.90)
   horizons = [timedelta(hours=h) for h in [1, 6, 24, 48]]

   pipeline = TransformPipeline(transforms=[
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           target_column="load",
           add_trivial_lags=True,
       ),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       AtmosphereDerivedFeaturesAdder(
           temperature_column="temperature",
           relative_humidity_column="humidity",
           pressure_column="pressure",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=location,
           radiation_column="radiation",
       ),
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=location),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
       DatetimeFeaturesAdder(),
       RollingAggregatesAdder(
           feature="load",
           aggregation_functions=["mean", "std"],
           horizons=horizons,
       ),
   ])

   pipeline.fit(train_dataset)
   train_features = pipeline.transform(train_dataset)

The pipeline's ``fit`` call propagates through to any stateful transforms (such as :class:`RollingAggregatesAdder`); stateless transforms simply pass through. At inference time, call ``pipeline.transform(inference_dataset)`` without re-fitting.

---

What Makes a Good Energy Feature
----------------------------------

A few principles guide feature selection in energy forecasting:

- **Physical interpretability.** Features grounded in physical or behavioural mechanisms (solar angle, apparent temperature, day-of-week) tend to generalise better than purely statistical constructs.
- **Availability at forecast time.** A feature is only useful if it can be computed when the forecast is needed. Weather *forecasts* are available; weather *observations* from the future are not. OpenSTEF's lag transforms enforce this constraint automatically.
- **Appropriate resolution.** Features should match the temporal resolution of the target. A 15-minute load series benefits from 15-minute lag features; daily aggregates lose the intra-day structure the model needs.
- **Avoid redundancy.** Highly correlated features add noise without adding information and can slow tree-based models. OpenSTEF's :class:`EmptyFeatureRemover` and scaler transforms help clean up the feature matrix before it reaches the model.

---

Further Reading
----------------

- :doc:`forecasting_basics` — the forecasting problem and how OpenSTEF approaches it
- :doc:`quantiles_and_confidence` — how feature uncertainty propagates into probabilistic output
- :doc:`reliability_and_fallback` — what happens when weather inputs or load history are missing at inference time