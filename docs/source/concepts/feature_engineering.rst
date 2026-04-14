Feature Engineering
===================

Good features are the foundation of accurate energy forecasts. OpenSTEF's models — primarily gradient-boosted trees like XGBoost and LightGBM — do not learn temporal structure automatically the way recurrent neural networks do. Instead, they rely on well-crafted input features that encode the patterns a human expert would recognise: the morning ramp-up in demand, the suppressing effect of sunshine on grid load, the quietness of a public holiday. This page explains the feature categories that matter most for short-term energy forecasting and shows how to use OpenSTEF's built-in transforms to construct them.

.. note::

   This page focuses on *what* features to use and *why*. For the broader forecasting workflow, see :doc:`forecasting_basics`. For how model choice interacts with feature selection, see :doc:`model_selection`.

---

Why Features Matter
-------------------

Classical ML models treat every row of input data as an independent observation. For a time series problem that means the model has no inherent memory — it cannot look back at yesterday's load unless you explicitly hand it that information as a column. Feature engineering is therefore not an optional refinement; it is the mechanism by which temporal structure, physical relationships, and domain knowledge enter the model.

OpenSTEF encodes this domain knowledge as a library of reusable ``TimeSeriesTransform`` objects. Each transform follows the same interface: it accepts a ``TimeSeriesDataset``, adds one or more columns, and exposes a ``features_added()`` method so you always know exactly what was produced. Transforms are composable — you chain them into a preprocessing pipeline and the library handles the rest.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

---

Weather Features
----------------

Weather is the dominant external driver of electricity demand and renewable generation. OpenSTEF ships three weather-domain transforms that go beyond raw measurements and derive physically meaningful quantities.

**Radiation and solar geometry** — ``RadiationDerivedFeaturesAdder`` takes a raw irradiance column and the geographic coordinate of the grid point, then derives features such as the clear-sky index and sun elevation angle. These capture the difference between what the sun *could* deliver and what it actually delivers, which is a strong predictor of PV generation and of cooling load.

**Atmospheric conditions** — ``AtmosphereDerivedFeaturesAdder`` combines temperature, relative humidity, and pressure into derived quantities such as apparent temperature (heat index / wind chill). Apparent temperature correlates with demand more tightly than dry-bulb temperature alone because it reflects how people actually experience the weather.

**Wind power** — ``WindPowerFeatureAdder`` applies a wind-power curve transformation to a wind-speed column, converting m/s into an estimate of the power fraction a turbine would produce. This is far more useful to a tree model than raw wind speed because the relationship between speed and power is non-linear (cubic in the linear region, then clipped at rated power).

**Daylight** — ``DaylightFeatureAdder`` uses the location coordinate and the timestamp to compute sunrise, sunset, and the fraction of daylight elapsed. This is particularly valuable when radiation data is missing or unreliable, and it helps the model distinguish a dark winter morning from a bright summer one even at the same clock time.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )

   # Each transform is configured with the column names present in your dataset
   radiation_adder = RadiationDerivedFeaturesAdder(
       coordinate=(52.37, 4.90),          # (latitude, longitude) of the grid point
       radiation_column="ghi",
   )
   atmosphere_adder = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure_hpa",
       relative_humidity_column="humidity_pct",
       temperature_column="temp_celsius",
   )
   wind_adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_ms")
   daylight_adder = DaylightFeatureAdder(coordinate=(52.37, 4.90))

   # Apply sequentially to a TimeSeriesDataset
   dataset = radiation_adder.fit_transform(dataset)
   dataset = atmosphere_adder.fit_transform(dataset)
   dataset = wind_adder.fit_transform(dataset)
   dataset = daylight_adder.fit_transform(dataset)

   # Inspect what was added
   print(radiation_adder.features_added())
   print(atmosphere_adder.features_added())

.. note::

   Raw weather columns (temperature, wind speed, radiation) should still be included alongside the derived features. The derived quantities complement rather than replace the originals.

---

Time Features
-------------

Energy consumption follows strong periodic patterns: daily, weekly, and annual. Tree models cannot infer periodicity from a raw timestamp, so you must encode it explicitly.

**Datetime components** — ``DatetimeFeaturesAdder`` extracts calendar fields such as hour of day, day of week, month, and quarter. When ``onehot_encode=False`` (the default for XGBoost), these are kept as integers and the model learns the non-linear mapping itself. When ``onehot_encode=True``, they become binary columns suitable for linear models.

**Cyclic encoding** — ``CyclicFeaturesAdder`` converts periodic integer features into sine/cosine pairs. This is important because a raw integer encoding treats hour 23 and hour 0 as maximally distant, when in reality they are adjacent. Cyclic encoding preserves the circular topology of time.

**Holidays** — ``HolidayFeatureAdder`` adds a binary ``is_holiday`` column and, optionally, individual columns for named holidays (e.g., ``christmas_day``, ``new_years_day``). Named holidays have distinct load profiles — Christmas is not the same as a random Sunday — so the granularity is worth having. The transform accepts an ISO 3166-1 alpha-2 country code and uses the ``holidays`` library internally.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )

   datetime_adder = DatetimeFeaturesAdder(onehot_encode=False)
   cyclic_adder = CyclicFeaturesAdder()
   holiday_adder = HolidayFeatureAdder(country_code="NL")

   dataset = datetime_adder.fit_transform(dataset)
   dataset = cyclic_adder.fit_transform(dataset)
   dataset = holiday_adder.fit_transform(dataset)

   print(holiday_adder.features_added())
   # e.g. ['is_holiday', 'christmas_day', 'new_years_day', 'kings_day', ...]

.. note::

   ``CyclicFeaturesAdder`` operates on the datetime features already present in the dataset, so it should be applied *after* ``DatetimeFeaturesAdder``.

---

Load Pattern Features: Lags and Rolling Aggregates
---------------------------------------------------

The single most informative predictor of load at time *t* is often the load at time *t − 24 h* or *t − 168 h* (one week ago). Lag features give the model direct access to historical observations, capturing autocorrelation that no weather or calendar feature can replicate.

**Lag features** — ``LagsAdder`` creates lagged copies of the target column. OpenSTEF supports three strategies:

- *Trivial lags*: fixed offsets at round multiples of minutes or days (e.g., 15 min, 30 min, 1 day, 7 days).
- *Custom lags*: an explicit list of ``timedelta`` offsets you specify.
- *Autocorrelation-based lags*: the transform analyses the training data and selects the lags with the highest autocorrelation automatically.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import LagsAdder

   # Autocorrelation-based lag selection (recommended for most use cases)
   lags_adder = LagsAdder(strategy="autocorrelation", max_lags=20)

   # Or specify lags explicitly
   lags_adder = LagsAdder(
       strategy="custom",
       lags=[timedelta(hours=1), timedelta(days=1), timedelta(weeks=1)],
   )

   dataset = lags_adder.fit_transform(dataset)

**Rolling aggregates** — ``RollingAggregatesAdder`` computes statistics (mean, standard deviation, min, max) over a rolling window of past observations. These smooth out noise and give the model a sense of the recent trend, which is especially useful for detecting unusual demand events.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   rolling_adder = RollingAggregatesAdder(
       feature="load_mw",
       aggregation_functions=["mean", "std"],
       horizons=["PT1H", "PT4H", "P1D"],   # ISO 8601 duration strings
   )
   dataset = rolling_adder.fit_transform(dataset)

.. warning::

   Lag and rolling features introduce a look-ahead risk if not handled carefully. OpenSTEF's ``LagsAdder`` is horizon-aware: it only uses lags that are available at the time the forecast is made, preventing data leakage during training.

---

What Makes a Good Feature
--------------------------

Not every column you can compute will improve the model. A few principles guide good feature selection for energy forecasting:

- **Physical interpretability.** If you cannot explain why a feature should correlate with load, it probably won't generalise. Apparent temperature is a good feature because human comfort drives heating and cooling demand. Day-of-month is usually a poor feature because there is no physical mechanism linking the 15th of the month to a specific load level.

- **Availability at forecast time.** A feature is only useful if it will be available when the model runs in production. Weather *forecasts* are available; weather *observations* are not (unless you are forecasting very short horizons). OpenSTEF's horizon-aware lag selection enforces this automatically, but you must apply the same discipline to any custom features you add.

- **Stable distributions.** Features whose statistical properties shift dramatically over time (e.g., a raw energy price during a market shock) can destabilise the model. The ``Clipper`` transform addresses this by clipping feature values to the range observed during training.

- **Low redundancy.** Highly correlated features do not add information and can slow training. If you add both ``temp_celsius`` and ``apparent_temperature``, consider whether both are genuinely needed or whether one subsumes the other for your use case.

---

Adding Custom Features
----------------------

OpenSTEF's transform interface is designed to be extended. To add a domain-specific feature, subclass ``TimeSeriesTransform`` and implement ``transform()`` and ``features_added()``.

.. code-block:: python

   from typing import override
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class HeatingDegreeDayAdder(BaseConfig, TimeSeriesTransform):
       """Adds a heating degree day (HDD) feature.

       HDD = max(0, base_temp - outdoor_temp), a standard proxy for heating demand.
       """

       base_temp: float = 18.0          # °C threshold below which heating is needed
       temperature_column: str = "temp_celsius"

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           hdd = (self.base_temp - data[self.temperature_column]).clip(lower=0)
           data["heating_degree_day"] = hdd
           return data

       @override
       def features_added(self) -> list[str]:
           return ["heating_degree_day"]

   # Use it exactly like any built-in transform
   hdd_adder = HeatingDegreeDayAdder(base_temp=15.5, temperature_column="temp_celsius")
   dataset = hdd_adder.fit_transform(dataset)

Because custom transforms follow the same ``TimeSeriesTransform`` protocol, they slot directly into any OpenSTEF pipeline alongside the built-in adders. The ``features_added()`` method ensures downstream components — including the ``EmptyFeatureRemover`` — know which columns your transform is responsible for.

---

Putting It Together: A Typical Feature Pipeline
------------------------------------------------

In practice, feature adders are composed into an ordered list. The order matters: cyclic encoding must follow datetime extraction; lag features should come after any smoothing you apply to the target.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )

   feature_pipeline = [
       # 1. Weather-derived features
       RadiationDerivedFeaturesAdder(coordinate=(52.37, 4.90), radiation_column="ghi"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure_hpa",
           relative_humidity_column="humidity_pct",
           temperature_column="temp_celsius",
       ),
       DaylightFeatureAdder(coordinate=(52.37, 4.90)),
       # 2. Time features (datetime first, then cyclic encoding on top)
       DatetimeFeaturesAdder(onehot_encode=False),
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
       # 3. Load history features
       LagsAdder(strategy="autocorrelation", max_lags=20),
       RollingAggregatesAdder(
           feature="load_mw",
           aggregation_functions=["mean", "std"],
           horizons=["PT1H", "PT4H", "P1D"],
       ),
       # 4. Custom domain feature
       HeatingDegreeDayAdder(base_temp=15.5, temperature_column="temp_celsius"),
   ]

   for transform in feature_pipeline:
       dataset = transform.fit_transform(dataset)

This pattern — a flat list of stateless, composable transforms — keeps feature engineering auditable and easy to modify. Adding or removing a feature is a one-line change, and ``features_added()`` on each transform gives you a complete inventory of what the model will see.

---

Further Reading
---------------

- :doc:`forecasting_basics` — how features feed into the end-to-end forecasting workflow
- :doc:`model_selection` — how different model families (XGBoost, LightGBM, linear) respond to feature engineering choices
- :doc:`quantiles_and_confidence` — how feature quality affects the width of probabilistic forecast intervals
- :doc:`reliability_and_fallback` — what happens when feature data (e.g., weather forecasts) is unavailable at inference time