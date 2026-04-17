Feature Engineering
===================

Good features are the foundation of accurate energy forecasts. OpenSTEF's classical ML approach — XGBoost, LightGBM, and linear models — relies on carefully crafted input features rather than raw sequences. This page explains the feature categories that matter most for short-term load forecasting and shows how to use OpenSTEF's built-in transform library to construct them.

.. note::

   Feature engineering in OpenSTEF is implemented as a composable pipeline of
   ``TimeSeriesTransform`` objects. Each transform is independently configurable,
   testable, and reusable. All transforms live under ``openstef_models.transforms``,
   organised into four sub-packages: ``time_domain``, ``weather_domain``,
   ``energy_domain``, and ``general``.

**[DIAGRAM: Feature engineering pipeline — raw inputs flow through time_domain, weather_domain, energy_domain, and general transforms to produce a feature matrix fed into the forecasting model]**

---

Why Feature Engineering Matters
--------------------------------

Short-term electricity load is driven by a small set of well-understood physical and social phenomena: people wake up and go to work, the sun rises and heats buildings, wind turbines spin faster in storms. A model that cannot *see* these signals must infer them from raw timestamps and meter readings alone — a much harder problem.

OpenSTEF embeds domain knowledge directly into its feature transforms. Solar radiation combined with temperature gives a proxy for PV generation. Cyclic encodings of hour-of-day prevent the model from treating midnight and 23:00 as maximally different. Lag features let the model ask "what was the load exactly one week ago?" — one of the strongest predictors available. The result is that even relatively simple tree-based models achieve high accuracy because the features do the heavy lifting.

---

Time Features
-------------

Time-of-day, day-of-week, and seasonal patterns account for the bulk of predictable load variation. OpenSTEF provides three transforms that cover this space.

**Cyclic encodings** — ``CyclicFeaturesAdder`` converts periodic time components (hour, day-of-week, month, etc.) into sine/cosine pairs. This is important because raw integer encodings imply a false discontinuity: hour 23 and hour 0 are adjacent, but ``23 > 0`` suggests otherwise. Sine/cosine pairs preserve the circular topology.

**Calendar features** — ``DatetimeFeaturesAdder`` extracts a richer set of calendar attributes (year, quarter, week number, and so on) as plain integers or one-hot encoded columns, depending on the model type. XGBoost typically works well with raw integers; linear models benefit from one-hot encoding.

**Holiday indicators** — ``HolidayFeatureAdder`` adds a binary ``is_holiday`` flag plus one binary column per named public holiday for a given country. Load on public holidays often resembles a Sunday regardless of the calendar day, so this single feature can dramatically improve weekend-adjacent forecasts.

.. code-block:: python

   import pandas as pd
   from pydantic_extra_types.country import CountryAlpha2
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )

   # Assume `dataset` is a TimeSeriesDataset with a DatetimeIndex
   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {"load_mw": [100.0, 98.5, 102.3]},
           index=pd.date_range("2024-12-24 00:00", periods=3, freq="15min"),
       ),
       sample_interval=pd.Timedelta(minutes=15),
   )

   # Add cyclic time-of-day and day-of-week features
   dataset = CyclicFeaturesAdder().transform(dataset)

   # Add raw calendar attributes (no one-hot encoding for tree models)
   dataset = DatetimeFeaturesAdder(onehot_encode=False).transform(dataset)

   # Add Dutch public holiday flags
   dataset = HolidayFeatureAdder(country_code=CountryAlpha2("NL")).transform(dataset)

   print(dataset.data.columns.tolist())

---

Weather Features
----------------

Weather is the dominant external driver of both demand and renewable generation. OpenSTEF groups weather transforms under ``openstef_models.transforms.weather_domain``.

**Atmospheric derived features** — ``AtmosphereDerivedFeaturesAdder`` computes secondary meteorological quantities from temperature, pressure, and relative humidity. Humidity, for instance, reduces PV output by scattering and absorbing sunlight, so the raw humidity reading is less informative than a derived quantity that captures this non-linear relationship.

**Radiation derived features** — ``RadiationDerivedFeaturesAdder`` takes a solar radiation column and the geographic coordinate of the grid connection point to compute features such as clear-sky irradiance and the ratio of measured to theoretical maximum radiation. These features are particularly valuable for grids with significant rooftop PV penetration.

**Daylight features** — ``DaylightFeatureAdder`` adds sunrise/sunset times and a binary daylight indicator derived from the location coordinate. This is a lightweight complement to radiation features and is useful even when a radiation sensor is unavailable.

**Wind power features** — ``WindPowerFeatureAdder`` converts a wind speed column into an estimated wind power output using a standard power curve approximation. The cubic relationship between wind speed and power is difficult for linear models to learn from raw wind speed alone; this transform makes it explicit.

.. code-block:: python

   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Coordinate
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

   dataset = TimeSeriesDataset(
       data=pd.DataFrame(
           {
               "load_mw": [80.0, 85.0, 90.0],
               "temperature": [12.0, 13.5, 11.0],
               "pressure": [1013.0, 1012.0, 1014.0],
               "relative_humidity": [75.0, 70.0, 80.0],
               "radiation": [200.0, 350.0, 150.0],
               "wind_speed": [5.0, 7.5, 4.0],
           },
           index=pd.date_range("2024-06-01 08:00", periods=3, freq="15min"),
       ),
       sample_interval=pd.Timedelta(minutes=15),
   )

   amsterdam = Coordinate(lat=52.37, lon=4.90)

   dataset = AtmosphereDerivedFeaturesAdder(
       temperature_column="temperature",
       pressure_column="pressure",
       relative_humidity_column="relative_humidity",
   ).transform(dataset)

   dataset = RadiationDerivedFeaturesAdder(
       coordinate=amsterdam,
       radiation_column="radiation",
   ).transform(dataset)

   dataset = DaylightFeatureAdder(coordinate=amsterdam).transform(dataset)

   dataset = WindPowerFeatureAdder(windspeed_reference_column="wind_speed").transform(dataset)

.. note::

   Weather features are only as good as the weather forecast driving them. At
   short horizons (0–6 hours) numerical weather prediction (NWP) is highly
   accurate. Beyond 48 hours, uncertainty grows and the model's probabilistic
   output (see :doc:`quantiles_and_confidence`) becomes increasingly important.

---

Load Pattern Features
---------------------

Historical load is the single most informative predictor of future load. Two transform families capture this.

**Lag features** — ``LagsAdder`` creates time-shifted copies of the target variable. The most valuable lags for energy forecasting are typically:

- **15 minutes to 1 hour** — captures inertia in load (e.g., a building that was warm five minutes ago is likely still warm).
- **24 hours** — same time yesterday; captures daily routine.
- **7 days** — same time last week; captures weekly patterns and is often the single strongest predictor.

``LagsAdder`` is horizon-aware: it only adds lags that are causally valid for each forecast horizon, preventing data leakage.

**Rolling aggregates** — ``RollingAggregatesAdder`` computes rolling statistics (mean, standard deviation, min, max) of the target over configurable windows and horizons. These smooth out noise and give the model a sense of recent trend and volatility.

.. code-block:: python

   from datetime import timedelta
   from openstef_core.types import LeadTime
   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder

   horizons = [LeadTime(timedelta(minutes=15)), LeadTime(timedelta(hours=24))]

   dataset = LagsAdder(
       history_available=timedelta(days=14),
       horizons=horizons,
       add_trivial_lags=True,
       target_column="load_mw",
   ).transform(dataset)

   dataset = RollingAggregatesAdder(
       feature="load_mw",
       aggregation_functions=["mean", "std"],
       horizons=horizons,
   ).transform(dataset)

.. warning::

   Always construct ``LagsAdder`` with the same ``horizons`` list you pass to
   the forecaster. Mismatched horizons will either leak future data or discard
   valid history.

---

Composing a Full Feature Pipeline
----------------------------------

In practice, transforms are composed into a ``FeaturePipeline`` and embedded inside a ``ForecastingModel``. The pipeline is applied consistently during both training and inference, ensuring the feature space is identical at prediction time.

**[DIAGRAM: FeaturePipeline composition — ordered list of transforms applied sequentially to a TimeSeriesDataset, producing an enriched dataset passed to the forecaster]**

.. code-block:: python

   from datetime import timedelta
   from pathlib import Path

   import pandas as pd
   from pydantic_extra_types.country import CountryAlpha2

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.types import Coordinate, LeadTime
   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
   )
   from openstef_models.transforms.time_domain.lags_adder import LagsAdder
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )

   horizons = [LeadTime(timedelta(hours=h)) for h in [1, 6, 24]]
   location = Coordinate(lat=52.37, lon=4.90)

   feature_pipeline = [
       # Load history
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=True,
           target_column="load_mw",
       ),
       # Weather
       AtmosphereDerivedFeaturesAdder(
           temperature_column="temperature",
           pressure_column="pressure",
           relative_humidity_column="relative_humidity",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=location,
           radiation_column="radiation",
       ),
       DaylightFeatureAdder(coordinate=location),
       # Time
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code=CountryAlpha2("NL")),
   ]

The ordering matters: lag features should be added before any transforms that
might drop rows, and weather transforms should run before dimensionality
reduction if you use ``DimensionalityReducer`` from ``openstef_models.transforms.general``.

---

Writing Custom Transforms
--------------------------

When the built-in transforms do not cover a domain-specific signal — for example, a local industrial calendar, a grid topology feature, or a custom price index — you can implement your own by subclassing ``TimeSeriesTransform`` from ``openstef_core.transforms``.

A custom transform must implement three methods:

- ``fit(data)`` — learn any statistics needed (e.g., mean, scale). Stateless transforms can leave this as a no-op.
- ``transform(data)`` — apply the feature computation and return a new ``TimeSeriesDataset``.
- ``features_added()`` — return the list of column names your transform introduces.

.. code-block:: python

   from typing import override
   import pandas as pd
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class IndustrialShiftFeatureAdder(TimeSeriesTransform):
       """Adds a binary feature indicating industrial day-shift hours (06:00-22:00)."""

       def fit(self, data: TimeSeriesDataset) -> None:
           pass  # stateless

       @override
       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           hours = data.data.index.hour
           shift_active = ((hours >= 6) & (hours < 22)).astype(float)
           new_data = data.data.copy()
           new_data["is_industrial_shift"] = shift_active
           return TimeSeriesDataset(
               data=new_data,
               sample_interval=data.sample_interval,
           )

       @override
       def features_added(self) -> list[str]:
           return ["is_industrial_shift"]

Drop this transform into any ``feature_pipeline`` list alongside the built-in
transforms — the pipeline treats all transforms uniformly.

---

What Makes a Good Feature
--------------------------

A few practical principles guide feature selection for energy forecasting:

- **Causal validity.** A feature must be available at prediction time. Weather *forecasts* are valid inputs; actual measured weather at the forecast horizon is not. ``LagsAdder`` enforces this automatically for load history.
- **Physical interpretability.** Prefer features grounded in physical or social mechanisms (solar angle, holiday flag) over purely statistical constructs. Interpretable features generalise better across seasons and years.
- **Avoid redundancy.** Highly correlated features add noise without information. Use ``DimensionalityReducer`` from ``openstef_models.transforms.general`` to prune redundant columns after the feature adders have run.
- **Handle missing data explicitly.** Weather sensors fail; NWP models have gaps. Use ``openstef_models.transforms.general.Imputer`` to fill gaps rather than silently propagating NaN values into the model.
- **Scale appropriately.** Tree-based models (XGBoost, LightGBM) are scale-invariant, but linear models are not. The ``Scaler`` transform in ``openstef_models.transforms.general`` applies standard scaling and should be placed after all feature adders in pipelines that include linear models.

---

Related Topics
--------------

Feature engineering does not exist in isolation. The features described here feed directly into the forecasting models and influence the uncertainty estimates in the output:

- :doc:`forecasting_basics` — how OpenSTEF uses these features inside a training and prediction workflow.
- :doc:`quantiles_and_confidence` — how feature quality affects the width of confidence intervals.
- :doc:`component_splitting` — decomposing aggregate load into sub-components, each of which may benefit from different feature sets.
- :doc:`meta_ensembles` — how the meta-ensemble layer combines models that may use different feature subsets.