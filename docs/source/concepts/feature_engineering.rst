Feature Engineering for Energy Forecasting
===========================================

Good features are the foundation of accurate short-term energy forecasts. While modern gradient-boosted models like XGBoost and LightGBM are powerful learners, they still depend on the quality and relevance of the inputs you provide. This page explains the feature categories that matter most for energy forecasting and shows how OpenSTEF's built-in transform library makes them easy to apply.

.. note::

   This page focuses on *what* features to use and *why* they work. For background on the forecasting problem itself, see :doc:`forecasting_basics`. For information on how uncertainty is expressed in forecasts, see :doc:`quantiles_and_confidence`.

Why Feature Engineering Matters
--------------------------------

Energy consumption and generation are driven by a small set of well-understood physical and behavioural processes: people follow daily and weekly routines, solar panels respond to irradiance, and heating loads rise with temperature. A model that receives raw timestamps and raw weather readings must discover these relationships from scratch. A model that receives carefully engineered representations of those same inputs — hour-of-day encoded as a sine/cosine pair, direct normal irradiance derived from global radiation, wind power estimated from a power curve — can learn the same patterns with far less data and generalise far better to unseen conditions.

OpenSTEF encodes this domain knowledge directly in its transform library under ``openstef_models.transforms``. The library is organised into four sub-packages:

- ``time_domain`` — cyclic, datetime, holiday, daylight, and rolling-aggregate features
- ``weather_domain`` — radiation, wind power, and atmosphere-derived features
- ``energy_domain`` — energy-specific transformations
- ``general`` — validation, scaling, and outlier handling

Each transform implements the ``TimeSeriesTransform`` interface, so they compose cleanly into preprocessing pipelines.

Time Features
-------------

Human behaviour is the dominant driver of load on most distribution grids. People wake up, go to work, cook dinner, and go to sleep on predictable schedules that repeat daily, weekly, and seasonally. Capturing these cycles precisely is therefore one of the highest-value things you can do.

**Cyclic encoding**

A naive integer encoding of hour-of-day (0–23) implies that hour 23 and hour 0 are far apart, when in reality they are adjacent. ``CyclicFeaturesAdder`` solves this by projecting periodic quantities onto the unit circle using sine and cosine pairs, producing smooth, continuous representations that tree-based models can split on effectively.

.. code-block:: python

   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   adder = CyclicFeaturesAdder()
   dataset = adder.transform(dataset)
   # Adds sin/cos pairs for hour-of-day, day-of-week, day-of-year, etc.

**Datetime features**

``DatetimeFeaturesAdder`` extracts a richer set of calendar attributes — hour, day of week, month, quarter, and similar — as plain integers or one-hot encoded columns depending on the downstream model.

.. code-block:: python

   from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

   adder = DatetimeFeaturesAdder(onehot_encode=False)
   dataset = adder.transform(dataset)

**Holiday features**

Public holidays break the normal weekly pattern: a Tuesday that falls on a national holiday looks nothing like a regular Tuesday. ``HolidayFeatureAdder`` uses a country-code-aware calendar to flag these days automatically.

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   adder = HolidayFeatureAdder(country_code="NL")
   dataset = adder.transform(dataset)

**Daylight features**

Sunrise and sunset times shift throughout the year and vary with latitude. ``DaylightFeatureAdder`` computes astronomically accurate daylight windows from geographic coordinates, giving the model a precise signal for when solar-driven loads (lighting, HVAC) are likely to change.

.. code-block:: python

   from openstef_models.transforms.time_domain import DaylightFeatureAdder
   from pydantic_extra_types.coordinate import Coordinate

   adder = DaylightFeatureAdder(coordinate=Coordinate(52.37, 4.90))
   dataset = adder.transform(dataset)

Weather Features
----------------

Weather is the second major driver of energy demand and the primary driver of renewable generation. OpenSTEF's weather transforms go beyond passing raw measurements to the model — they compute physically meaningful derived quantities that have a more direct relationship with load and generation.

**Radiation-derived features**

Global horizontal irradiance (GHI) is the most commonly available radiation measurement, but what actually matters for a rooftop solar installation is the irradiance on the tilted panel surface. ``RadiationDerivedFeaturesAdder`` uses solar position geometry (computed from coordinates and timestamp) to decompose GHI into Direct Normal Irradiance (DNI) and Global Tilted Irradiance (GTI). These derived quantities are far more predictive of PV output than raw GHI.

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder
   from pydantic_extra_types.coordinate import Coordinate

   adder = RadiationDerivedFeaturesAdder(
       coordinate=Coordinate(52.37, 4.90),
       radiation_column="radiation_ghi",
   )
   dataset = adder.transform(dataset)

**Wind power features**

Wind speed at measurement height (typically 10 m) is a poor proxy for the power output of a wind turbine, whose hub may sit at 80–120 m. ``WindPowerFeatureAdder`` applies the wind profile power law to extrapolate wind speed to hub height, then estimates power output via a parameterised power curve. The resulting feature captures the non-linear, cubic relationship between wind speed and power that a model would otherwise have to learn implicitly.

.. code-block:: python

   from openstef_models.transforms.weather_domain import WindPowerFeatureAdder

   adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_10m")
   dataset = adder.transform(dataset)

**Atmosphere-derived features**

Temperature, pressure, and relative humidity interact in ways that affect both demand (heating and cooling loads) and generation efficiency. ``AtmosphereDerivedFeaturesAdder`` computes composite indices from these three inputs.

.. code-block:: python

   from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

   adder = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure_hpa",
       relative_humidity_column="humidity_pct",
       temperature_column="temperature_c",
   )
   dataset = adder.transform(dataset)

Load Pattern Features
---------------------

Recent load history is one of the most informative signals available for short-horizon forecasting. If consumption was high in the last hour, it is likely to remain elevated in the next hour. Rolling aggregates formalise this intuition.

``RollingAggregatesAdder`` computes statistics (mean, median, min, max) over a rolling window of the target variable and adds them as lagged features. Because the target is not available at inference time for future horizons, the transform includes a fallback strategy that forward-fills from the last computed aggregate, ensuring the pipeline remains operational in production.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import RollingAggregatesAdder

   adder = RollingAggregatesAdder(
       feature="load_mw",
       aggregation_functions=["mean", "max"],
       horizons=[timedelta(hours=1), timedelta(hours=24)],
   )
   dataset = adder.fit_transform(dataset)

.. note::

   Rolling aggregates must be fitted before use (to learn the fallback values). Always call ``fit_transform`` during training and ``transform`` during inference on a fitted instance.

Composing a Full Feature Pipeline
----------------------------------

In practice, you will use several transforms together. OpenSTEF's pipeline configuration assembles them in a consistent order: feature alignment and validation first, then domain-specific feature adders, then standardisation. The following example mirrors the structure used internally by the library's XGBoost pipeline.

.. code-block:: python

   from pydantic_extra_types.coordinate import Coordinate
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       DaylightFeatureAdder,
       HolidayFeatureAdder,
       RollingAggregatesAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       WindPowerFeatureAdder,
   )
   from datetime import timedelta

   coordinate = Coordinate(52.37, 4.90)

   feature_adders = [
       WindPowerFeatureAdder(windspeed_reference_column="wind_speed_10m"),
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure_hpa",
           relative_humidity_column="humidity_pct",
           temperature_column="temperature_c",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=coordinate,
           radiation_column="radiation_ghi",
       ),
       CyclicFeaturesAdder(),
       DaylightFeatureAdder(coordinate=coordinate),
       HolidayFeatureAdder(country_code="NL"),
       DatetimeFeaturesAdder(onehot_encode=False),
       RollingAggregatesAdder(
           feature="load_mw",
           aggregation_functions=["mean", "max"],
           horizons=[timedelta(hours=1), timedelta(hours=24)],
       ),
   ]

   for transform in feature_adders:
       dataset = transform.fit_transform(dataset)

What Makes a Good Feature
--------------------------

Not every column you can compute belongs in the model. A few principles guide good feature selection for energy forecasting:

- **Physical relevance.** Prefer features that have a known causal or physical link to load or generation. DNI is a better solar feature than raw GHI because it more directly drives panel output.
- **Availability at forecast time.** A feature is only useful if it can be computed for the future horizon you are targeting. Historical load is available for short horizons but not for multi-day forecasts; weather forecasts are available but carry their own uncertainty.
- **Smooth representation of periodicity.** Tree-based models cannot extrapolate, so cyclic quantities (hour, day-of-week) must be encoded as sine/cosine pairs rather than raw integers to avoid artificial discontinuities at period boundaries.
- **Avoid leakage.** Never include information that would not be available at the time the forecast is made. Rolling aggregates that look into the future relative to the forecast horizon will produce optimistic training metrics that do not hold in production.
- **Sparsity hurts.** Features that are almost always zero or that have very high cardinality with little signal add noise and slow training. OpenSTEF's ``EmptyFeatureRemover`` automatically drops columns that carry no information.

.. note::

   .. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

Custom Features
---------------

OpenSTEF's transform interface is designed to be extended. If your grid has a specific characteristic — a large industrial customer whose shift patterns drive local load, or a battery storage asset whose state-of-charge affects net demand — you can implement a custom transform by subclassing ``TimeSeriesTransform`` and ``BaseConfig``.

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class IndustrialShiftFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Adds a binary feature indicating industrial shift hours."""

       shift_start_hour: int = 6
       shift_end_hour: int = 22

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.to_dataframe()
           df["is_shift_hour"] = (
               (df.index.hour >= self.shift_start_hour) &
               (df.index.hour < self.shift_end_hour)
           ).astype(int)
           return TimeSeriesDataset.from_dataframe(df)

       def features_added(self) -> list[str]:
           return ["is_shift_hour"]

Custom transforms slot directly into the same pipeline list as the built-in ones, so they benefit from the same composition and validation infrastructure.

.. warning::

   Custom features that depend on external data sources (e.g., production schedules fetched from an API) must have a reliable fallback for when that data is unavailable. A feature that is missing at inference time will cause the pipeline to fail or silently degrade. See :doc:`reliability_and_fallback` for strategies to handle this in production.

Summary
-------

OpenSTEF's feature engineering library covers the most important predictors for energy forecasting out of the box: cyclic time encodings, holiday calendars, daylight windows, physically derived weather features, and rolling load aggregates. These transforms are composable, production-tested, and encode domain knowledge that would otherwise take significant effort to replicate. For most use cases, combining the built-in transforms with one or two custom features tailored to your specific grid will give you a strong feature set without overfitting.