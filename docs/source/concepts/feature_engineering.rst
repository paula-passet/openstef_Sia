Feature Engineering
===================

Energy demand and generation follow patterns driven by weather, time of day, seasonality, and human behavior. Feature engineering transforms raw input data into signals that machine learning models can exploit to produce accurate forecasts. OpenSTEF provides a composable set of **feature transforms** that you assemble into preprocessing pipelines, each adding domain-specific features to a ``TimeSeriesDataset``.

This page covers the feature categories available in OpenSTEF, why each matters for energy forecasting, and how to use the library's built-in transforms.

.. note::

   For background on what short-term energy forecasting is and why it matters, see :doc:`forecasting_basics`. For guidance on choosing a model to consume these features, see :doc:`model_selection`.


Why Features Matter
-------------------

A forecasting model is only as good as the information it receives. Raw load measurements alone cannot capture the drivers behind energy patterns. Temperature explains heating and cooling demand. Solar radiation predicts photovoltaic output. Time-of-day encodes human activity cycles. By engineering these signals explicitly, you give the model structured information that would otherwise require far more data and complexity to learn implicitly.

OpenSTEF organizes features into three domains:

- **Weather domain** — meteorological variables and their derived quantities
- **Time domain** — temporal patterns, holidays, lags, and rolling statistics
- **Energy domain** — physics-based features like estimated wind power


Weather Features
----------------

Weather is the single most important external driver of energy demand and renewable generation. OpenSTEF provides several transforms in ``openstef_models.transforms.weather_domain`` for deriving useful signals from raw weather data.

AtmosphereDerivedFeaturesAdder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Calculates derived meteorological quantities from basic weather measurements—temperature, pressure, and relative humidity. These derived features (such as dew point or air density) can improve model accuracy because they capture physical relationships that raw variables alone do not express.

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

   atmosphere_transform = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="relative_humidity",
       temperature_column="temperature",
   )

   dataset = atmosphere_transform.transform(dataset)

RadiationDerivedFeaturesAdder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Solar radiation is critical for forecasting photovoltaic generation and cooling-driven demand. This transform uses the geographic coordinate of the forecast location together with raw radiation data to compute features that account for solar geometry (sun angle, clear-sky index, etc.).

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder

   radiation_transform = RadiationDerivedFeaturesAdder(
       coordinate=(52.0, 5.0),  # latitude, longitude
       radiation_column="radiation",
   )

   dataset = radiation_transform.transform(dataset)

DaylightFeatureAdder
^^^^^^^^^^^^^^^^^^^^

Adds features indicating whether the current timestamp falls within daylight hours for a given location. This is a simple but effective signal for solar-related forecasting and for capturing the behavioral difference between daytime and nighttime energy use.

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder

   daylight_transform = DaylightFeatureAdder(
       coordinate=(52.0, 5.0),
   )

   dataset = daylight_transform.transform(dataset)


Time Features
-------------

Energy consumption follows strong temporal patterns: daily cycles, weekly rhythms, seasonal shifts, and disruptions from holidays. OpenSTEF's time-domain transforms in ``openstef_models.transforms.time_domain`` encode these patterns as model features.

CyclicFeaturesAdder
^^^^^^^^^^^^^^^^^^^

Encodes periodic time signals (hour of day, day of week, month of year) as sine/cosine pairs. This cyclic encoding is essential because it preserves the continuity between, for example, hour 23 and hour 0—something that raw integer encoding cannot represent.

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   cyclic_transform = CyclicFeaturesAdder()
   dataset = cyclic_transform.transform(dataset)

DatetimeFeaturesAdder
^^^^^^^^^^^^^^^^^^^^^

Adds discrete datetime features such as hour, day of week, and month. Some models (particularly tree-based ones like XGBoost) can work effectively with integer-encoded time features rather than cyclic encoding.

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

   datetime_transform = DatetimeFeaturesAdder(onehot_encode=False)
   dataset = datetime_transform.transform(dataset)

HolidayFeatureAdder
^^^^^^^^^^^^^^^^^^^

Holidays cause significant deviations from normal load patterns—industrial demand drops while residential patterns shift. This transform adds binary indicators for public holidays based on a country code, using standard holiday calendars.

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   holiday_transform = HolidayFeatureAdder(country_code="NL")
   dataset = holiday_transform.transform(dataset)


Load Pattern Features
---------------------

Historical load values themselves contain powerful predictive information. Yesterday's load at the same hour, last week's pattern, and recent trends all inform the forecast.

Lag Features
^^^^^^^^^^^^

The ``LagsAdder`` generates lagged versions of the target variable. OpenSTEF provides utility functions to determine appropriate lags automatically:

- ``generate_minute_lags`` — short-term lags for intraday forecasting
- ``generate_day_lags`` — daily and weekly lags (e.g., same hour yesterday, same hour last week)
- ``generate_autocorr_lags`` — data-driven lags based on autocorrelation peaks in the time series

.. code-block:: python

   from openstef_models.transforms.time_domain.lags_adder import (
       generate_day_lags,
       generate_autocorr_lags,
   )
   from datetime import timedelta

   # Generate lags capturing daily and weekly patterns
   day_lags = generate_day_lags(
       max_horizon=timedelta(hours=36),
       max_day_lags=7,
   )

   # Or let the data decide which lags are informative
   autocorr_lags = generate_autocorr_lags(
       signal=load_series,
       max_horizon=timedelta(hours=36),
       height_threshold=0.1,
       max_lag_hours=4,
   )

Rolling Aggregates
^^^^^^^^^^^^^^^^^^

The ``RollingAggregatesAdder`` computes rolling statistics (mean, max, min, median) over a configurable window. These features capture recent trends and smooth out noise. The transform includes a built-in fallback strategy for missing data during inference: it forward-fills from the last computed aggregate or falls back to the last valid value from training.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   rolling_transform = RollingAggregatesAdder(
       feature="load",
       rolling_window_size=timedelta(hours=2),
       aggregation_functions=["mean", "max"],
       horizons=[LeadTime.from_string("PT36H")],
   )

   rolling_transform.fit(training_dataset)
   dataset = rolling_transform.transform(dataset)

   # New columns: rolling_mean_load_PT2H, rolling_max_load_PT2H

.. note::

   Rolling aggregate transforms are stateful—they must be ``fit()`` on training data before calling ``transform()``. This allows the fallback mechanism to work during inference when recent target values may not be available.


Energy Domain Features
----------------------

WindPowerFeatureAdder
^^^^^^^^^^^^^^^^^^^^^

Converts raw wind speed measurements into estimated wind power output using a power curve relationship. This physics-informed feature is far more useful than raw wind speed for forecasting wind-heavy grid regions, because the relationship between wind speed and power is nonlinear (roughly cubic in the mid-range).

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

   wind_transform = WindPowerFeatureAdder(
       windspeed_reference_column="windspeed",
   )

   dataset = wind_transform.transform(dataset)


Composing a Feature Pipeline
-----------------------------

In practice, you combine multiple feature transforms into a preprocessing pipeline. OpenSTEF's workflow configurations assemble these automatically, but you can also compose them manually for custom use cases:

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       DaylightFeatureAdder,
   )
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

   feature_adders = [
       WindPowerFeatureAdder(windspeed_reference_column="windspeed"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="relative_humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=(52.0, 5.0),
           radiation_column="radiation",
       ),
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=(52.0, 5.0)),
       HolidayFeatureAdder(country_code="NL"),
   ]

   # Apply all transforms sequentially
   for transform in feature_adders:
       dataset = transform.transform(dataset)

Every transform follows the same interface: it accepts a ``TimeSeriesDataset`` and returns a ``TimeSeriesDataset`` with additional columns. You can inspect which columns a transform will add by calling its ``features_added()`` method.

.. note:: [DIAGRAM: Feature pipeline flow showing raw data entering a sequence of transforms (weather → time → energy → standardization) producing an enriched dataset ready for model training]


What Makes a Good Feature
--------------------------

When extending OpenSTEF with custom features or selecting which built-in transforms to use, keep these principles in mind:

- **Physical causality** — Features should represent actual drivers of energy behavior. Temperature drives heating/cooling demand; radiation drives solar output. Spurious correlations degrade forecast reliability.

- **Appropriate granularity** — Match feature resolution to your forecast horizon. Minute-level lags help 15-minute-ahead forecasts but add noise to day-ahead models.

- **Stationarity** — Prefer features that maintain a stable relationship with the target over time. Raw timestamps are poor features; cyclic encodings of hour-of-day are excellent ones.

- **Availability at inference time** — Every feature used during training must be available when generating forecasts. Weather forecasts are available; actual future load values are not (use lags instead).

- **Parsimony** — More features are not always better. Redundant or noisy features increase training time and can reduce accuracy. OpenSTEF includes an ``EmptyFeatureRemover`` and feature selection mechanisms to help manage this.

.. warning::

   If a feature column contains all missing or constant values, the ``EmptyFeatureRemover`` transform will drop it automatically. Ensure your input data pipelines provide meaningful variation in all supplied columns.


Further Reading
---------------

- :doc:`forecasting_basics` — Understand the forecasting problem these features serve
- :doc:`model_selection` — Choose models that best exploit your feature set
- :doc:`quantiles_and_confidence` — Learn how features feed into probabilistic forecasts
- :doc:`reliability_and_fallback` — Strategies when feature data is missing or degraded