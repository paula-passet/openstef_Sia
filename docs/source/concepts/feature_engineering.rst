Feature Engineering
===================

Good features are the foundation of accurate energy forecasts. OpenSTEF embeds substantial domain knowledge directly into its feature engineering pipeline, transforming raw inputs — timestamps, weather observations, and historical load — into the rich representations that tree-based models like XGBoost and LightGBM need to learn energy consumption patterns. This page explains what those features are, why they matter, and how to use or extend them in your own pipelines.

.. note::

   This page focuses on feature construction. For an overview of the forecasting
   process itself, see :doc:`forecasting_basics`. For how uncertainty is represented
   in the output, see :doc:`quantiles_and_confidence`.


Why Feature Engineering Matters for Energy
-------------------------------------------

Short-term load is driven by a handful of well-understood physical and social forces: people wake up and go to work, the sun rises and sets, temperature changes drive heating and cooling demand, and public holidays disrupt normal routines. Classical ML models cannot discover these patterns from raw timestamps alone — they need features that make the structure explicit.

OpenSTEF's philosophy is that **domain knowledge should live in the feature pipeline, not in model complexity**. A gradient-boosted tree with well-crafted features consistently outperforms a deep model trained on raw inputs, and it does so with far less data and training time. The library ships a complete set of energy-specific transforms so you do not have to rediscover this domain knowledge from scratch.

All feature transforms in OpenSTEF implement the ``TimeSeriesTransform`` interface from ``openstef_core``, meaning they expose ``fit``, ``transform``, and ``features_added`` methods and compose naturally into a preprocessing pipeline.


Weather Features
----------------

Weather is the single strongest external driver of electricity demand and renewable generation. OpenSTEF provides three dedicated weather-domain transform classes.

**Atmosphere-derived features**

``AtmosphereDerivedFeaturesAdder`` computes secondary meteorological quantities from the three most commonly available weather variables — temperature, pressure, and relative humidity. These derived quantities often correlate with load more directly than the raw inputs. For example, high humidity reduces photovoltaic (PV) output by scattering and absorbing sunlight, an effect that is invisible to a model that sees only irradiance.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

   data = pd.DataFrame(
       {
           "temperature": [20.0, 25.0, 15.0],
           "pressure": [1013.25, 1015.0, 1010.0],
           "relative_humidity": [60.0, 70.0, 80.0],
       },
       index=pd.date_range("2025-06-01 12:00", periods=3, freq="h", tz="UTC"),
   )
   dataset = TimeSeriesDataset(data=data, sample_interval=pd.Timedelta(hours=1))

   transform = AtmosphereDerivedFeaturesAdder(
       temperature_column="temperature",
       pressure_column="pressure",
       relative_humidity_column="relative_humidity",
   )
   enriched = transform.transform(dataset)
   print(transform.features_added())

**Radiation-derived features**

``RadiationDerivedFeaturesAdder`` converts a measured global horizontal irradiance (GHI) signal into physically meaningful solar components using the asset's geographic coordinates. It computes Direct Normal Irradiance (DNI) and Global Tilted Irradiance (GTI) via ``pvlib``, accounting for solar position, clear-sky models, and panel tilt. These features are essential for any grid that has significant PV penetration.

.. code-block:: python

   from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude
   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder

   transform = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(
           latitude=Latitude(52.0),
           longitude=Longitude(5.0),
       ),
       radiation_column="radiation",
       included_features=["dni", "gti"],
       surface_tilt=34.0,
       surface_azimuth=180.0,
   )
   enriched = transform.transform(dataset)

**Daylight features**

``DaylightFeatureAdder`` adds features that capture whether a given timestamp falls within daylight hours and how far into the day it is, again using geographic coordinates to compute sunrise and sunset times accurately. This is particularly useful for distinguishing morning ramp-up from evening ramp-down in load profiles.

**Wind power features**

``WindPowerFeatureAdder`` applies a wind-power curve transformation to a wind speed column, converting the raw meteorological measurement into an estimate of turbine output. This non-linear mapping — flat below cut-in speed, cubic in the operating range, flat at rated power — is far more informative to a model than the raw wind speed.


Time and Calendar Features
---------------------------

Human behaviour is strongly periodic. OpenSTEF captures this with two complementary transforms.

**Datetime features**

``DatetimeFeaturesAdder`` extracts calendar components from the index — hour of day, day of week, month, and similar quantities. These can be added as raw integers or, when ``onehot_encode=False``, as compact ordinal encodings that tree-based models handle efficiently.

**Cyclic encoding**

Raw integer hour-of-day features have an artificial discontinuity: hour 23 and hour 0 appear far apart numerically even though they are adjacent in time. ``CyclicFeaturesAdder`` resolves this by encoding periodic features as sine/cosine pairs, so the model sees a smooth, continuous representation of the daily and weekly cycles.

**Holiday features**

``HolidayFeatureAdder`` marks timestamps that fall on public holidays for a given country, using the ``country_code`` parameter. Holidays break the normal weekly load pattern dramatically — a Tuesday that is a national holiday looks nothing like a regular Tuesday — and without this flag the model will systematically mis-forecast those days.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       DatetimeFeaturesAdder,
       CyclicFeaturesAdder,
   )
   from openstef_models.transforms.general import HolidayFeatureAdder

   pipeline = [
       DatetimeFeaturesAdder(onehot_encode=False),
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
   ]

   for step in pipeline:
       dataset = step.transform(dataset)


Load Pattern Features
---------------------

Historical load is the most predictive signal available. OpenSTEF provides two transforms that extract structure from the target time series itself.

**Lag features**

``VersionedLagsAdder`` creates lag features — copies of the target column shifted back by a fixed number of time steps — while respecting data availability constraints. In a live forecasting context, you cannot use a lag that would require future data, so the transform tracks which lags are actually available at each forecast horizon and only includes those that are valid. Lag selection can be driven by autocorrelation analysis to focus on the most informative delays.

**Rolling aggregates**

``RollingAggregatesAdder`` computes rolling statistics (mean, median, min, max) over a configurable window and set of horizons. These features capture recent trends — a sustained high-load period is a strong predictor of continued high load — and they handle missing target data gracefully during inference by forward-filling from the last computed aggregate.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   rolling = RollingAggregatesAdder(
       feature="load_mw",
       aggregation_functions=["mean", "max"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )
   rolling.fit(train_dataset)
   enriched = rolling.transform(inference_dataset)

.. note::

   ``RollingAggregatesAdder`` must be ``fit`` on training data before it can be
   used for inference. The fitted state stores fallback values used when the
   target column is unavailable at prediction time.


What Makes a Good Energy Feature
---------------------------------

Not every variable that correlates with load belongs in the feature set. A few principles guide good feature selection for energy forecasting:

- **Physical interpretability.** Prefer features that have a causal or physically motivated relationship with load. Solar irradiance causes PV generation; temperature causes heating and cooling demand. Spurious correlations in training data will not generalise.

- **Availability at forecast time.** A feature is only useful if it will be available when you need to make a prediction. Weather forecasts are available; actual measured load at the forecast horizon is not. OpenSTEF's lag transforms enforce this constraint automatically.

- **Appropriate resolution.** Features should be available at the same temporal resolution as your forecast. A daily average temperature is a poor substitute for 15-minute temperature readings when forecasting at 15-minute intervals.

- **Stability across seasons.** Features derived from raw weather values can shift dramatically between summer and winter. Derived features — solar angle, clear-sky ratio, degree-days — are often more stable predictors than the raw measurements.

- **Avoid leakage.** Rolling aggregates and lag features computed over a window that includes the forecast period introduce data leakage and will produce optimistic training metrics that do not reflect real-world performance.


Adding Custom Features
-----------------------

OpenSTEF's transform interface is designed to be extended. Any class that implements ``fit``, ``transform``, and ``features_added`` can be inserted into a pipeline alongside the built-in transforms. A minimal custom transform looks like this:

.. code-block:: python

   import pandas as pd
   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform


   class PeakTariffFlagAdder(BaseConfig, TimeSeriesTransform):
       """Flag timestamps that fall within peak electricity tariff hours."""

       peak_start_hour: int = 7
       peak_end_hour: int = 23

       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # stateless transform, nothing to fit

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           hour = data.data.index.hour
           flag = ((hour >= self.peak_start_hour) & (hour < self.peak_end_hour)).astype(int)
           result = data.data.copy()
           result["is_peak_tariff"] = flag
           return data.copy_with(result)

       def features_added(self) -> list[str]:
           return ["is_peak_tariff"]

Once defined, the transform slots directly into any pipeline:

.. code-block:: python

   pipeline = [
       DatetimeFeaturesAdder(onehot_encode=False),
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
       PeakTariffFlagAdder(peak_start_hour=7, peak_end_hour=23),
   ]

   for step in pipeline:
       dataset = step.transform(dataset)

.. note::

   Custom transforms that are stateful — for example, those that compute statistics
   from training data — must implement ``fit`` properly and be fitted before
   ``transform`` is called. The ``is_fitted`` property should return ``False``
   until ``fit`` has been called at least once.


The Full Feature Pipeline
--------------------------

In a complete OpenSTEF configuration, the feature pipeline is assembled automatically from the model configuration. The order of transforms matters: feature adders run before standardisers, and outlier handling runs before scaling. The typical sequence is:

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

1. **Alignment and validation** — ensure the dataset has the required columns and a consistent time index.
2. **Weather feature adders** — ``WindPowerFeatureAdder``, ``AtmosphereDerivedFeaturesAdder``, ``RadiationDerivedFeaturesAdder``, ``DaylightFeatureAdder``.
3. **Time and calendar adders** — ``HolidayFeatureAdder``, ``DatetimeFeaturesAdder``, ``CyclicFeaturesAdder``.
4. **Load pattern features** — ``RollingAggregatesAdder`` (when configured).
5. **Standardisation** — outlier handling, scaling, sample weighting, and removal of empty feature columns.

Each step is independently configurable, and custom transforms can be inserted at any point in the sequence.

For details on how forecast reliability is maintained when input features are missing or degraded, see :doc:`reliability_and_fallback`.