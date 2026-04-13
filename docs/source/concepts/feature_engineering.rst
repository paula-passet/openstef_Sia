Feature Engineering
===================

Good features are the foundation of accurate energy forecasts. A model that receives raw load values and timestamps will underperform compared to one that understands solar irradiance, wind speed, and the difference between a Tuesday in July and a public holiday in December. This page explains the categories of features that matter most for short-term energy forecasting, how OpenSTEF constructs them, and how you can extend the pipeline with your own domain knowledge.

.. note::

   This page focuses on *what* features are used and *why* they work. For background on the forecasting task itself, see :doc:`forecasting_basics`. For information on how models are selected and trained, see :doc:`model_selection`.

Why Features Matter for Energy Forecasting
-------------------------------------------

Energy consumption and generation are driven by a small number of well-understood physical and social processes: people wake up and go to work, the sun rises and sets, wind turbines respond to wind speed, and factories follow production schedules. A model that can see these drivers directly — rather than inferring them from load history alone — is far more robust, especially at longer forecast horizons where recent history becomes less informative.

OpenSTEF's feature engineering philosophy is to encode as much domain knowledge as possible into the feature set, then let gradient-boosted tree models (XGBoost, LightGBM) discover the relevant interactions. This combination of energy-specific transformations with classical ML models is a key reason why OpenSTEF achieves competitive accuracy without requiring deep learning architectures.

All feature construction in OpenSTEF is implemented as ``TimeSeriesTransform`` objects. Each transform is composable, inspectable (via ``features_added()``), and can be assembled into a preprocessing pipeline. The sections below describe the main transform families.

Weather Features
----------------

Weather is the dominant driver of short-term load variation for most grid points. OpenSTEF provides several weather-domain transforms in ``openstef_models.transforms.weather_domain``.

**Radiation-derived features** (``RadiationDerivedFeaturesAdder``)
   Raw solar radiation measurements are transformed into features that better represent the physical relationship between irradiance and PV generation. This includes corrections for the geographic location of the measurement point, since the same radiation value means different things at different latitudes and times of year.

**Daylight features** (``DaylightFeatureAdder``)
   Sunrise and sunset times, day length, and solar elevation angle are computed from the grid point's coordinates. These features give the model an astronomically precise sense of when solar generation is possible, without relying on the model to infer this from historical patterns.

**Atmosphere-derived features** (``AtmosphereDerivedFeaturesAdder``)
   From basic meteorological inputs — temperature, pressure, and relative humidity — this transform derives composite variables such as apparent temperature (heat index / wind chill) and dew point. These composites often correlate more strongly with heating and cooling loads than the raw measurements alone.

**Wind power features** (``WindPowerFeatureAdder``)
   Wind speed is converted to an estimated wind power output using a power curve relationship. This non-linear transform (roughly cubic at low speeds, then saturating) captures the physical behaviour of wind turbines far better than raw wind speed.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       RadiationDerivedFeaturesAdder,
       DaylightFeatureAdder,
       AtmosphereDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from openstef_core.types import Coordinate

   location = Coordinate(lat=52.1, lon=5.1)

   weather_transforms = [
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="humidity",
           temperature_column="temperature",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=location,
           radiation_column="radiation",
       ),
       DaylightFeatureAdder(coordinate=location),
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
   ]

   # Inspect what each transform will add before applying it
   for t in weather_transforms:
       print(t.__class__.__name__, "->", t.features_added())

.. note::

   Weather features are only as good as the weather forecast that feeds them. At short horizons (0–6 hours), numerical weather prediction errors are small. Beyond 48 hours, weather uncertainty becomes a significant source of forecast error. See :doc:`quantiles_and_confidence` for how OpenSTEF represents this uncertainty in its probabilistic outputs.

Time and Calendar Features
--------------------------

Even without any weather data, time-of-day and day-of-week patterns explain a large fraction of load variance. Electricity demand follows human schedules: morning ramp-ups, lunchtime dips, evening peaks, weekend reductions. OpenSTEF captures these patterns through two complementary transform families.

**Datetime features** (``DatetimeFeaturesAdder``)
   Extracts calendar components from the timestamp index: hour of day, day of week, day of month, month of year, and week of year. These can be encoded as raw integers or as one-hot vectors depending on the model type. For tree-based models, raw integer encoding is typically preferred because the model can learn arbitrary threshold splits.

**Cyclic features** (``CyclicFeaturesAdder``)
   Calendar integers have a discontinuity problem: hour 23 and hour 0 are numerically far apart but temporally adjacent. Cyclic encoding resolves this by projecting each periodic variable onto a unit circle using sine and cosine transforms. The result is a pair of continuous features where the distance between any two time points reflects their true temporal proximity.

**Holiday features** (``HolidayFeatureAdder``)
   Public holidays disrupt normal weekly patterns significantly. This transform uses the ``holidays`` library to add binary indicator features for each public holiday in the configured country. Individual holidays (Christmas, Easter, etc.) get their own feature columns, allowing the model to learn that different holidays have different load profiles.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
       HolidayFeatureAdder,
   )

   time_transforms = [
       DatetimeFeaturesAdder(onehot_encode=False),
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
   ]

   for t in time_transforms:
       print(t.__class__.__name__, "->", t.features_added())

Load Pattern Features
---------------------

Historical load values are among the most predictive features available, because consumption patterns are strongly auto-correlated. A site that consumed 500 kW at this time last week is likely to consume a similar amount this week, all else being equal.

**Lag features** (``LagsAdder``)
   Creates copies of the target variable shifted back in time by specified intervals. Common lags for energy forecasting include 15 minutes, 30 minutes, 1 hour, 24 hours, 48 hours, and 7 days. The 24-hour and 7-day lags are particularly powerful because they capture the same time-of-day on the previous day and the same day of the previous week respectively.

   OpenSTEF supports three lag strategies:

   - **Trivial lags**: fixed offsets in minutes or days, specified directly
   - **Custom lags**: an explicit list of ``timedelta`` values
   - **Autocorrelation-based lags**: the library analyses the training data's autocorrelation structure and selects the most informative lags automatically

**Rolling aggregates** (``RollingAggregatesAdder``)
   Computes rolling statistics (mean, standard deviation, min, max) over recent windows of the target variable. These smooth out noise and give the model a sense of recent trend and variability, which is especially useful for detecting unusual conditions that may persist into the forecast horizon.

.. code-block:: python

   from openstef_models.transforms.time_domain import RollingAggregatesAdder, LagsAdder
   from datetime import timedelta

   lag_transform = LagsAdder(
       feature="load",
       strategy="trivial",   # use standard minute/day-based lags
   )

   rolling_transform = RollingAggregatesAdder(
       feature="load",
       aggregation_functions=["mean", "std"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )

   print("Lag features:", lag_transform.features_added())
   print("Rolling features:", rolling_transform.features_added())

.. mermaid:: diagrams/concepts/feature_engineering_diagram_1.mmd

What Makes a Good Feature
--------------------------

Not every variable that correlates with load makes a good feature. The following principles guide feature selection in energy forecasting:

**Physical interpretability**
   Features grounded in physical processes (solar geometry, thermodynamics, wind power curves) generalise better across seasons and years than purely statistical features derived from historical data alone. When a model has never seen a particular weather pattern, physically-motivated features give it a better basis for extrapolation.

**Availability at forecast time**
   A feature is only useful if it can be computed at the moment a forecast is needed. Weather forecasts are available; actual future load is not. Lag features must use values that are genuinely available at the forecast origin — using a 1-hour lag when forecasting 30 minutes ahead is valid; using it when forecasting 2 hours ahead requires that the 1-hour-old value is already observed and stored.

**Low noise, high signal**
   Raw sensor readings often contain outliers, missing values, and measurement errors. OpenSTEF's ``Clipper`` transform bounds features to their observed historical range, preventing extreme values from distorting tree splits. The ``Scaler`` transform standardises feature magnitudes so that regularisation and distance-based operations behave consistently.

**Avoiding leakage**
   Features derived from the target variable (lags, rolling aggregates) must be constructed with strict respect for the forecast horizon. OpenSTEF's ``RollingAggregatesAdder`` and ``LagsAdder`` both accept a ``horizons`` parameter that ensures no future information leaks into the training examples.

Adding Custom Features
-----------------------

OpenSTEF is designed to be extended. If your grid point has domain-specific predictors — industrial production schedules, gas prices, EV charging session counts — you can add them by implementing a custom ``TimeSeriesTransform``.

.. code-block:: python

   from typing import override
   import pandas as pd
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class IndustrialScheduleAdder(BaseConfig, TimeSeriesTransform):
       """Adds a binary feature indicating industrial production hours."""

       schedule_column: str = "production_schedule"

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.to_dataframe()
           # Mark hours 06:00-22:00 on weekdays as production hours
           is_weekday = df.index.dayofweek < 5
           is_production_hour = (df.index.hour >= 6) & (df.index.hour < 22)
           df["industrial_active"] = (is_weekday & is_production_hour).astype(float)
           return TimeSeriesDataset.from_dataframe(df)

       @override
       def features_added(self) -> list[str]:
           return ["industrial_active"]

Once implemented, the custom transform slots directly into the same pipeline as the built-in transforms:

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder, CyclicFeaturesAdder

   pipeline_transforms = [
       DatetimeFeaturesAdder(onehot_encode=False),
       CyclicFeaturesAdder(),
       IndustrialScheduleAdder(),
   ]

   # Apply the pipeline to a dataset
   dataset = ...  # your TimeSeriesDataset
   for transform in pipeline_transforms:
       dataset = transform.fit_transform(dataset)

.. note::

   The ``features_added()`` method is not just documentation — it is used by OpenSTEF internally to track which columns were introduced by each transform, enabling clean removal of features that turn out to be empty or constant (via ``EmptyFeatureRemover``).

Feature Pipeline in Context
-----------------------------

In a complete OpenSTEF forecasting configuration, feature transforms are declared as part of the model pipeline. The order matters: weather-domain transforms should run before standardisation, and lag features should be computed after any derived weather features are in place (so that derived columns can also be lagged if needed).

A typical ordering follows this structure:

1. **Data validation** — check for required columns, consistent timestamps
2. **Weather-domain transforms** — derive physical features from raw meteorological inputs
3. **Time-domain transforms** — add calendar, cyclic, and holiday features
4. **Load-pattern transforms** — add lags and rolling aggregates
5. **Standardisation** — clip outliers, scale features, remove empty columns

This is the same ordering used by the built-in ``XGBoostForecaster`` and ``LightGBMForecaster`` pipelines. When you add custom transforms, insert them at the appropriate stage rather than appending them at the end after standardisation has already run.

For details on how the full pipeline is assembled and how models are trained on the resulting feature matrix, see :doc:`model_selection`. For guidance on what happens when feature data is unavailable or degraded at inference time, see :doc:`reliability_and_fallback`.