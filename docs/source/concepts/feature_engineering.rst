Feature Engineering for Energy Forecasting
==========================================

Energy load is shaped by a predictable mix of physical, temporal, and behavioural forces. A substation draws more power on cold Monday mornings than on warm Sunday afternoons; a solar-heavy feeder drops its net load whenever the sun is high and skies are clear. Good feature engineering translates these domain insights into columns that a gradient-boosted tree or linear model can exploit directly. This page explains the main feature families OpenSTEF uses, why each one matters, and how to compose them in your own pipeline.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

Feature Families
----------------

OpenSTEF organises features into four broad families: **temporal**, **weather-derived**, **load-history**, and **calendar/event** features. Each family captures a different source of variation in energy demand.

Temporal Features
-----------------

Raw timestamps carry no numerical signal for a model. OpenSTEF converts them into two complementary representations.

**Cyclic encoding** maps periodic quantities — time of day, day of week, month, season — onto a unit circle using sine and cosine pairs. This preserves the continuity that a plain integer would break: 23:45 and 00:15 are close in time but far apart as integers.

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain.cyclic_features_adder import CyclicFeaturesAdder

   data = pd.DataFrame(
       {"load": [100, 120, 110, 95]},
       index=pd.date_range("2025-06-02 06:00", periods=4, freq="1h"),
   )
   dataset = TimeSeriesDataset(data, sample_interval=timedelta(hours=1))

   adder = CyclicFeaturesAdder(
       included_features=["time_of_day", "day_of_week", "season", "month"]
   )
   result = adder.transform(dataset)
   # Adds: time_of_day_sine, time_of_day_cosine, day_of_week_sine, ...
   print(result.data.filter(like="_sine").head())

The default set covers all four cyclic features. You can restrict it to a subset by passing a shorter ``included_features`` list.

**Discrete datetime features** (hour, weekday number, ISO week, etc.) are added by ``DatetimeFeaturesAdder`` and are useful for tree-based models that can split on exact values rather than needing smooth representations.

.. code-block:: python

   from openstef_models.transforms.time_domain.datetime_features_adder import DatetimeFeaturesAdder

   adder = DatetimeFeaturesAdder(onehot_encode=False)
   result = adder.transform(dataset)

Weather Features
----------------

Weather is the dominant driver of both demand and renewable generation. OpenSTEF provides dedicated transforms for the most important meteorological signals.

**Radiation-derived features** go beyond raw global horizontal irradiance (GHI). Given the site's geographic coordinates, ``RadiationDerivedFeaturesAdder`` computes Direct Normal Irradiance (DNI) and Global Tilted Irradiance (GTI), which are far better proxies for actual PV panel output than GHI alone.

.. code-block:: python

   from pydantic_extra_types.coordinate import Coordinate
   from openstef_models.transforms.weather_domain.radiation_derived_features_adder import (
       RadiationDerivedFeaturesAdder,
   )

   adder = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(latitude=52.37, longitude=4.90),  # Amsterdam
       radiation_column="ghi",
   )
   result = adder.transform(dataset)
   # Adds: dni, gti — corrected for solar angle at this location

**Atmosphere-derived features** combine temperature, pressure, and relative humidity into secondary signals such as apparent temperature (wind chill / heat index) and dew point. These capture human thermal comfort, which drives heating and cooling loads more accurately than raw temperature alone.

.. code-block:: python

   from openstef_models.transforms.weather_domain.atmosphere_derived_features_adder import (
       AtmosphereDerivedFeaturesAdder,
   )

   adder = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure_hpa",
       relative_humidity_column="humidity_pct",
       temperature_column="temp_celsius",
   )
   result = adder.transform(dataset)

**Wind power features** convert a wind speed measurement at a reference height into an estimated power output using a turbine power curve approximation. This is especially valuable for feeders with significant wind generation.

.. code-block:: python

   from openstef_models.transforms.weather_domain.wind_power_feature_adder import (
       WindPowerFeatureAdder,
   )

   adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_ms")
   result = adder.transform(dataset)

**Daylight features** add a binary or continuous daylight indicator derived from sunrise/sunset times at the site's coordinates. This is a lightweight complement to radiation data and handles cases where radiation measurements are missing or noisy.

.. code-block:: python

   from openstef_models.transforms.time_domain.daylight_feature_adder import DaylightFeatureAdder

   adder = DaylightFeatureAdder(coordinate=Coordinate(latitude=52.37, longitude=4.90))
   result = adder.transform(dataset)

.. note:: [VISUALIZATION: Scatter plot of load vs. GTI and load vs. GHI for a solar-heavy feeder, showing tighter correlation with GTI]

Load History Features
---------------------

Historical load values are among the strongest predictors of future load. OpenSTEF provides two complementary approaches.

**Lag features** copy the target variable at fixed time offsets into the past. For a 15-minute resolution series, a lag of 96 steps is exactly one day ago — a powerful predictor because most consumption patterns repeat daily and weekly.

``LagsAdder`` generates two families of lags automatically:

- *Minute-based lags* — short offsets (15 min, 30 min, 1 h, …) that capture inertia and short-term trends.
- *Day-based lags* — offsets at multiples of 24 h (1 day, 2 days, 7 days, 14 days) that capture daily and weekly seasonality.

It also supports *autocorrelation-based lags*, which inspect the training data's autocorrelation function and select only the offsets where peaks occur, avoiding redundant features.

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import (
       LagsAdder,
       generate_minute_lags,
       generate_day_lags,
   )

   horizons = [timedelta(hours=1), timedelta(hours=24)]

   adder = LagsAdder(
       history_available=timedelta(days=14),
       horizons=horizons,
       add_trivial_lags=True,   # include minute- and day-based lags automatically
       target_column="load",
   )
   result = adder.fit(dataset).transform(dataset)
   print(adder.horizon_lags)   # shows which lags are valid per horizon

A critical detail: lags must be *causally valid*. A 1-hour-ahead forecast cannot use a lag of 30 minutes — that value lies in the future at prediction time. ``LagsAdder`` enforces this automatically based on the configured horizons.

**Rolling aggregates** summarise recent history with statistics such as mean, standard deviation, or maximum over a sliding window. They smooth out noise and expose trend information that individual lag values miss.

.. code-block:: python

   from openstef_models.transforms.time_domain.rolling_aggregates_adder import RollingAggregatesAdder

   adder = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std", "max"],
       horizons=horizons,
   )
   result = adder.fit(dataset).transform(dataset)

.. note:: [VISUALIZATION: Time series plot showing load alongside its 24-hour rolling mean and standard deviation bands, illustrating how rolling features track trend and volatility]

Calendar and Event Features
----------------------------

Human behaviour follows social calendars as much as physical clocks. Public holidays, school holidays, and special events shift load profiles in ways that cyclic time features cannot capture.

``HolidayFeatureAdder`` uses the ``holidays`` library under the hood and accepts an ISO country code, so it works across different national grids without manual calendar maintenance.

.. code-block:: python

   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder

   adder = HolidayFeatureAdder(country_code="NL")
   result = adder.transform(dataset)
   # Adds a binary 'is_holiday' column (and optionally named holiday columns)

For grids that span multiple countries or regions, instantiate one ``HolidayFeatureAdder`` per country code and concatenate the resulting columns.

What Makes a Good Feature for Energy Forecasting
-------------------------------------------------

A few principles guide feature selection in this domain:

**Causal validity.** A feature used at inference time must be available at the moment the forecast is made. Weather forecasts are available; yesterday's measured load is available; tomorrow's actual load is not. ``LagsAdder`` enforces this automatically, but custom features must respect the same constraint.

**Physical interpretability.** Features grounded in physics — GTI rather than raw GHI, apparent temperature rather than dry-bulb temperature — tend to generalise better across seasons and sites. They encode domain knowledge that a model would otherwise need to learn from data.

**Smooth representation of periodicity.** Encoding hour-of-day as an integer (0–23) creates a discontinuity between 23 and 0. Sine/cosine encoding eliminates this artefact. Use ``CyclicFeaturesAdder`` for any periodic quantity.

**Avoiding data leakage.** Rolling statistics and lag features computed over a window that extends into the forecast horizon introduce leakage. Always fit aggregation transforms on training data only and apply them to test/production data using the stored training-time statistics as fallbacks — ``RollingAggregatesAdder`` stores these fallbacks automatically.

**Sparse features hurt tree models less than linear models.** One-hot encoded holidays or weekday dummies are fine for XGBoost or LightGBM. For linear models, prefer continuous or cyclic encodings.

Composing a Full Feature Pipeline
----------------------------------

In practice, all feature adders are composed into a sequential pipeline. The order matters: lag and rolling features depend on the target column being present, while weather-derived features only need the raw meteorological inputs.

.. code-block:: python

   from datetime import timedelta
   from pydantic_extra_types.coordinate import Coordinate
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.time_domain.rolling_aggregates_adder import RollingAggregatesAdder
   from openstef_models.transforms.time_domain.cyclic_features_adder import CyclicFeaturesAdder
   from openstef_models.transforms.time_domain.daylight_feature_adder import DaylightFeatureAdder
   from openstef_models.transforms.time_domain.holiday_features_adder import HolidayFeatureAdder
   from openstef_models.transforms.weather_domain.radiation_derived_features_adder import RadiationDerivedFeaturesAdder
   from openstef_models.transforms.weather_domain.atmosphere_derived_features_adder import AtmosphereDerivedFeaturesAdder
   from openstef_models.transforms.weather_domain.wind_power_feature_adder import WindPowerFeatureAdder

   coordinate = Coordinate(latitude=52.37, longitude=4.90)
   horizons = [timedelta(hours=1), timedelta(hours=24)]

   pipeline = [
       # Load history
       LagsAdder(history_available=timedelta(days=14), horizons=horizons,
                 add_trivial_lags=True, target_column="load"),
       RollingAggregatesAdder(feature="load",
                              aggregation_functions=["mean", "std"],
                              horizons=horizons),
       # Weather
       RadiationDerivedFeaturesAdder(coordinate=coordinate, radiation_column="ghi"),
       AtmosphereDerivedFeaturesAdder(pressure_column="pressure_hpa",
                                      relative_humidity_column="humidity_pct",
                                      temperature_column="temp_celsius"),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed_ms"),
       # Temporal
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=coordinate),
       HolidayFeatureAdder(country_code="NL"),
   ]

   dataset: TimeSeriesDataset = ...   # your data

   for transform in pipeline:
       transform.fit(dataset)
       dataset = transform.transform(dataset)

.. note::

   When using OpenSTEF's built-in workflow classes (``XGBoostForecaster``, ensemble workflows), this pipeline is assembled automatically from the workflow configuration. You only need to compose it manually when building a custom pipeline.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_2.mmd

Related Topics
--------------

Feature engineering produces the inputs that feed the forecasting model. To understand what the model does with those inputs — including how it produces probabilistic outputs — see :doc:`forecasting_basics` and :doc:`quantiles_and_confidence`. For situations where the load signal itself is a mixture of components (e.g., net load with embedded solar), feature engineering interacts closely with the decomposition described in :doc:`component_splitting`.