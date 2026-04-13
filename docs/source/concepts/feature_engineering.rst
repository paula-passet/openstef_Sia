Feature Engineering
===================

Good features are the single most important factor in energy forecasting accuracy. OpenSTEF is built around this principle: its classical ML models — XGBoost, LightGBM, and linear variants — achieve strong real-world performance precisely because they are paired with a rich, domain-aware feature engineering pipeline. This page explains what that pipeline contains, why each feature category matters, and how to extend it with your own transforms.

.. note::

   This page focuses on feature construction. For an overview of the forecasting
   problem itself, see :doc:`forecasting_basics`. For details on the models that
   consume these features, see :doc:`model_selection`.


Why Features Matter More Than Models
-------------------------------------

Energy consumption and generation are driven by a small set of physical and social forces: the sun rises and sets, temperatures change, people follow weekly routines, and holidays disrupt those routines. A model that cannot "see" these drivers has to infer them from the raw load signal alone, which is both harder and less reliable.

OpenSTEF's approach is to make these drivers explicit. Rather than relying on a deep neural network to discover temporal patterns from scratch, the library encodes domain knowledge directly into features and then lets a fast, interpretable tree model do the rest. The result is a pipeline that trains quickly, generalises well to new substations, and is easy to debug when something goes wrong.

The feature transforms in OpenSTEF are implemented as ``TimeSeriesTransform`` objects from ``openstef_core``. Each transform exposes a ``fit_transform`` method and a ``features_added()`` method so you always know exactly what columns were added to your dataset.


Weather Features
-----------------

Weather is the dominant external driver of electricity demand and distributed generation. OpenSTEF ships three dedicated weather-domain transforms.

**RadiationDerivedFeaturesAdder** takes a raw solar radiation column and derives additional features that improve PV generation estimates — for example, clear-sky irradiance ratios and angle-corrected radiation values that account for the geographic location of the substation.

**AtmosphereDerivedFeaturesAdder** takes temperature, relative humidity, and pressure and computes derived meteorological quantities such as apparent temperature (heat index / wind chill) and dew point. These derived values correlate more directly with heating and cooling loads than the raw measurements do.

**WindPowerFeatureAdder** converts wind speed into an estimate of wind power output using a power-curve transformation. Wind speed has a cubic relationship with power, so feeding raw wind speed to a linear model is inefficient; this transform makes the relationship approximately linear.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_models.transforms.weather_domain.daylight_feature_adder import (
       DaylightFeatureAdder,
   )

   # Each transform is configured via constructor arguments
   radiation_adder = RadiationDerivedFeaturesAdder(
       coordinate=(52.3, 4.9),          # (lat, lon) for solar angle calculations
       radiation_column="radiation",
   )

   atmosphere_adder = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="humidity",
       temperature_column="temperature",
   )

   wind_adder = WindPowerFeatureAdder(
       windspeed_reference_column="wind_speed",
   )

   # Apply sequentially to a TimeSeriesDataset
   dataset = radiation_adder.fit_transform(dataset)
   dataset = atmosphere_adder.fit_transform(dataset)
   dataset = wind_adder.fit_transform(dataset)

   # Inspect what was added
   print(radiation_adder.features_added())

**DaylightFeatureAdder** is a companion to the radiation transform. It adds binary and continuous daylight indicators derived from astronomical sunrise/sunset calculations for the configured location. These features help the model distinguish between "no radiation because it is night" and "no radiation because it is overcast" — a distinction that matters for confidence interval estimation.


Time and Calendar Features
---------------------------

Load patterns repeat on multiple timescales simultaneously: within a day, across the week, and across the year. OpenSTEF provides three transforms to capture these rhythms.

**DatetimeFeaturesAdder** decomposes the timestamp index into scalar calendar components: hour of day, day of week, day of month, month, and so on. These are the raw building blocks of temporal patterns.

**CyclicFeaturesAdder** takes those scalar calendar components and re-encodes them as sine/cosine pairs. This is important because calendar variables are circular: hour 23 is adjacent to hour 0, but a raw integer encoding makes them appear maximally distant. Cyclic encoding preserves the true topology of time.

**HolidayFeatureAdder** adds binary indicator columns for public holidays in the configured country. Holiday behaviour is idiosyncratic — Christmas load looks nothing like a typical Sunday — so a generic day-of-week feature cannot capture it. The transform uses the ``holidays`` library internally and sanitises holiday names into valid Python identifiers for use as column names.

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
   # e.g. ['is_holiday', 'christmas_day', 'kings_day', ...]

.. note::

   ``HolidayFeatureAdder`` requires a two-letter ISO 3166-1 alpha-2 country code
   (e.g. ``"NL"``, ``"DE"``, ``"FR"``). Forecasting a substation in a country
   with regional holidays? Pass the most specific code available, or consider
   adding a custom holiday transform for regional calendars.


Load Pattern Features
----------------------

Past load values are among the strongest predictors of future load. OpenSTEF provides two transforms that extract historical patterns from the target variable itself.

**LagsAdder** creates lagged copies of the target column. A lag of 24 hours captures the "same time yesterday" pattern; a lag of 168 hours captures "same time last week". The transform supports three strategies:

- *Trivial lags* — fixed offsets based on the resolution of the time series (e.g. every 15-minute interval up to some horizon).
- *Custom lags* — an explicit list of ``timedelta`` values you specify.
- *Autocorrelation-based lags* — the transform fits on training data and selects lags where the autocorrelation function exceeds a threshold, adapting to the specific load profile of each substation.

**RollingAggregatesAdder** computes rolling statistics (mean, standard deviation, min, max) of the target over configurable windows and horizons. These aggregates smooth out noise and capture recent trend information that point-in-time lags miss.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from datetime import timedelta

   lags_adder = LagsAdder(
       target_column="load",
       strategy="custom",
       lags=[timedelta(hours=24), timedelta(hours=48), timedelta(days=7)],
   )

   rolling_adder = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )

   dataset = lags_adder.fit_transform(dataset)
   dataset = rolling_adder.fit_transform(dataset)

.. warning::

   Lag and rolling features create a look-ahead risk if not handled carefully.
   OpenSTEF's ``TimeSeriesDataset`` tracks forecast horizons and will raise an
   error if a transform tries to use future information at inference time. Always
   fit transforms on training data only and call ``transform`` (not
   ``fit_transform``) on validation and test sets.


Adding Custom Features
-----------------------

The ``TimeSeriesTransform`` interface is designed to be subclassed. If your use case requires features not covered by the built-in transforms — industrial calendar events, grid topology indicators, price signals — you can implement them as first-class OpenSTEF transforms that slot directly into any pipeline.

.. code-block:: python

   from typing import override
   import pandas as pd
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform


   class IndustrialShutdownAdder(BaseConfig, TimeSeriesTransform):
       """Add a binary feature for known industrial shutdown periods."""

       shutdown_periods: list[tuple[str, str]]  # list of (start, end) date strings
       feature_name: str = "industrial_shutdown"

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           index = data.df.index
           mask = pd.Series(False, index=index)
           for start, end in self.shutdown_periods:
               mask |= (index >= start) & (index <= end)
           data.df[self.feature_name] = mask.astype(float)
           return data

       @override
       def features_added(self) -> list[str]:
           return [self.feature_name]


   # Use it exactly like any built-in transform
   shutdown_adder = IndustrialShutdownAdder(
       shutdown_periods=[("2024-12-23", "2025-01-03"), ("2024-07-15", "2024-07-19")],
   )
   dataset = shutdown_adder.fit_transform(dataset)

The ``BaseConfig`` mixin provides Pydantic validation for constructor arguments, so your custom transform benefits from the same configuration safety as the built-in ones. Implementing ``features_added()`` is not strictly required but is strongly recommended — it makes pipelines self-documenting and enables automatic feature selection downstream.


What Makes a Good Feature
---------------------------

Not every signal that correlates with load in historical data is a useful feature. A few practical guidelines:

- **Prefer causal signals over correlated ones.** Temperature causes heating load; the day-of-year number merely correlates with it. Causal features generalise better across unusual years (heatwaves, cold snaps).

- **Encode domain knowledge explicitly.** The wind power cubic transform and the cyclic time encoding are both examples of this. Encoding the relationship you know about frees the model to learn the relationships you don't.

- **Be careful with lag depth.** Very long lags (e.g. same time last year) can be useful but require a full year of training data before they are populated. Missing lag values at the start of a training set can silently degrade model quality.

- **Avoid leaking future information.** Any feature derived from the target variable — lags, rolling aggregates — must respect the forecast horizon. OpenSTEF's built-in transforms handle this automatically; custom transforms must do so explicitly.

- **Check feature importance after training.** Tree models provide feature importance scores. If a feature you added consistently scores near zero, it is adding noise rather than signal and should be removed.


Putting It All Together
------------------------

In a typical OpenSTEF pipeline the feature transforms are assembled in a specific order: raw checks first, then weather features, then time features, then load history features, and finally standardisation. The order matters because some transforms depend on columns added by earlier ones.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_models.transforms.weather_domain.daylight_feature_adder import DaylightFeatureAdder
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from datetime import timedelta

   feature_pipeline = [
       # Weather
       RadiationDerivedFeaturesAdder(coordinate=(52.3, 4.9), radiation_column="radiation"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
       DaylightFeatureAdder(coordinate=(52.3, 4.9)),
       # Time and calendar
       DatetimeFeaturesAdder(onehot_encode=False),
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
       # Load history
       LagsAdder(target_column="load", strategy="trivial"),
       RollingAggregatesAdder(
           feature="load",
           aggregation_functions=["mean", "std"],
           horizons=[timedelta(hours=1), timedelta(hours=24)],
       ),
   ]

   for transform in feature_pipeline:
       dataset = transform.fit_transform(dataset)

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

For production use, the pipeline is typically configured declaratively through the OpenSTEF model configuration object rather than assembled manually. See :doc:`model_selection` for how feature pipeline configuration integrates with model choice, and :doc:`reliability_and_fallback` for how missing weather inputs are handled when upstream data sources fail.