Feature Engineering
===================

Good forecasting models are only as good as the features they learn from. For energy load forecasting, raw measurements alone — a single column of power readings — rarely capture the full picture. This page explains the categories of features that matter most in short-term energy forecasting, how OpenSTEF's built-in transforms generate them, and how you can extend the pipeline with your own domain knowledge.

For background on what short-term forecasting is and why it matters, see :doc:`forecasting_basics`. For details on how models consume these features, see :doc:`model_selection`.

.. mermaid:: /diagrams/concepts/feature_engineering_diagram_1.mmd

Why Features Matter
-------------------

Short-term energy forecasting sits at the intersection of human behaviour, physical environment, and electrical infrastructure. A model that sees only recent load values will struggle with a hot Monday morning after a cool weekend. A model that also sees temperature forecasts, the hour of day, and the previous Monday's load profile has the context it needs to reason correctly.

The key insight is that domain knowledge embedded in feature engineering often outperforms raw model complexity. Classical ML models — gradient-boosted trees, linear models — combined with well-crafted features routinely beat deep learning approaches on energy forecasting benchmarks. OpenSTEF is designed around this principle: its transform library encodes energy-domain expertise so you don't have to rediscover it from scratch.

OpenSTEF's Transform Architecture
----------------------------------

Every feature-generating step in OpenSTEF is a ``TimeSeriesTransform`` (or its versioned counterpart, ``VersionedTimeSeriesTransform``). Each transform follows a consistent interface:

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder

   transform = DaylightFeatureAdder()
   transform.fit(dataset)
   enriched = transform.transform(dataset)

   # Inspect what was added
   print(transform.features_added())

The ``features_added()`` method is particularly useful when building pipelines: it lets you audit exactly which columns each step contributes, making it straightforward to trace a feature back to its origin.

Transforms are composable. You chain them together to build a full feature engineering pipeline, and each one operates on a ``TimeSeriesDataset`` (or ``VersionedTimeSeriesDataset``) rather than a raw DataFrame. This keeps availability constraints and versioning metadata intact throughout the process.

Weather Features
----------------

Weather is the dominant external driver of electricity demand and renewable generation. OpenSTEF provides a dedicated ``weather_domain`` transform package covering three broad categories.

**Radiation and solar features**

Solar irradiance directly drives photovoltaic generation and influences cooling loads. The ``RadiationDerivedFeaturesAdder`` derives secondary features from raw radiation measurements — quantities like diffuse fraction and clearness index that are more directly informative to a model than raw global horizontal irradiance alone.

.. code-block:: python

   from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder

   radiation_transform = RadiationDerivedFeaturesAdder()
   radiation_transform.fit(dataset)
   dataset = radiation_transform.transform(dataset)

**Daylight features**

Sunrise and sunset times, day length, and solar elevation angle are powerful predictors because they capture the *phase* of solar forcing independently of cloud cover. The ``DaylightFeatureAdder`` computes these from the dataset's timestamps and location metadata, so no external astronomy library is needed.

.. code-block:: python

   from openstef_models.transforms.weather_domain import DaylightFeatureAdder

   daylight_transform = DaylightFeatureAdder()
   daylight_transform.fit(dataset)
   dataset = daylight_transform.transform(dataset)

**Atmosphere-derived features**

Temperature, humidity, and wind speed interact in non-linear ways that affect both demand (heating/cooling) and generation (wind power). The ``AtmosphereDerivedFeaturesAdder`` computes derived meteorological quantities — such as apparent temperature and dew point — that encode these interactions more directly than the raw measurements.

**Wind power features**

For grid points with significant wind generation, the ``WindPowerFeatureAdder`` converts wind speed data into estimated wind power output using a power curve transformation. This is a good example of physics-based feature engineering: rather than letting the model learn the cubic wind-speed-to-power relationship from scratch, you encode it explicitly.

.. code-block:: python

   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

   wind_transform = WindPowerFeatureAdder()
   wind_transform.fit(dataset)
   dataset = wind_transform.transform(dataset)

Time Features
-------------

Energy consumption is deeply rhythmic. Demand on a Tuesday at 08:00 looks very different from the same timestamp on a Sunday. Time features give the model the vocabulary to express these cycles.

Useful time features for energy forecasting include:

- **Hour of day** — captures the daily demand cycle (morning ramp-up, evening peak, overnight trough)
- **Day of week** — distinguishes weekday industrial load from weekend residential patterns
- **Month or week of year** — encodes seasonal heating and cooling trends
- **Public holiday indicator** — holidays often produce load profiles closer to Sundays than weekdays
- **Minutes since midnight** — a continuous alternative to hour-of-day for sub-hourly data

Rather than encoding these as raw integers (which imply a false linear ordering — hour 23 is not "greater than" hour 0 in any meaningful sense), it is common practice to encode cyclical features as sine/cosine pairs:

.. code-block:: python

   import numpy as np
   import pandas as pd

   def add_cyclical_time_features(df: pd.DataFrame) -> pd.DataFrame:
       """Add sine/cosine encodings for hour-of-day and day-of-week."""
       hour = df.index.hour
       dow = df.index.dayofweek

       df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
       df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
       df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
       df["dow_cos"] = np.cos(2 * np.pi * dow / 7)
       return df

This encoding preserves the circular structure: the model sees that 23:45 and 00:15 are close together, not 23.75 hours apart.

Lag Features and Load Patterns
-------------------------------

Historical load values are among the most predictive features available. Yesterday's consumption at the same hour is an excellent prior for today's. The previous week's profile captures weekly seasonality. Recent measurements capture short-term momentum.

OpenSTEF provides two lag transforms depending on whether you are working with versioned or non-versioned datasets.

**Non-versioned data: LagsAdder**

For straightforward datasets, ``LagsAdder`` creates shifted copies of a target column:

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import LagsAdder

   lag_transform = LagsAdder(
       feature="load",
       lags=[
           timedelta(hours=-1),   # one hour ago
           timedelta(hours=-24),  # same hour yesterday
           timedelta(days=-7),    # same hour last week
       ]
   )
   lag_transform.fit(dataset)
   dataset = lag_transform.transform(dataset)

**Versioned data: VersionedLagsAdder**

In production, measurement data arrives with varying latency — a meter reading from 15 minutes ago may not yet be available, but a reading from two hours ago almost certainly is. The ``VersionedLagsAdder`` preserves these availability constraints so that lag features only use data that would genuinely have been available at prediction time. This prevents a subtle but serious form of data leakage:

.. code-block:: python

   from datetime import timedelta
   import pandas as pd
   from openstef_core.datasets import VersionedTimeSeriesDataset
   from openstef_models.transforms.time_domain import VersionedLagsAdder

   # Assume 'dataset' is a VersionedTimeSeriesDataset with 1-hour availability delay
   lag_transform = VersionedLagsAdder(
       feature="load",
       lags=[timedelta(hours=-1), timedelta(hours=-2)]
   )
   result = lag_transform.transform(dataset)

   # Inspect the generated feature names
   snapshot = result.select_version()
   lag_cols = [c for c in snapshot.feature_names if "lag" in c]
   print(sorted(lag_cols))
   # ['load_lag_-PT1H', 'load_lag_-PT2H']

The naming convention uses ISO 8601 duration strings (``-PT1H``, ``-PT2H``) so feature names are unambiguous regardless of the lag magnitude.

.. note::

   Always prefer ``VersionedLagsAdder`` in production pipelines. Using ``LagsAdder`` with live data risks including measurements that were not yet available when the forecast would have been generated, leading to optimistic training metrics that do not reflect real-world performance.

What Makes a Good Lag?
^^^^^^^^^^^^^^^^^^^^^^^

Not all lags are equally useful. Choosing lags thoughtlessly inflates the feature space and can hurt model performance. Practical guidelines:

- **Align lags to natural cycles**: 1 h, 24 h, 48 h, 168 h (one week) are almost always worth including.
- **Match lags to your forecast horizon**: if you are forecasting 4 hours ahead, a 1-hour lag is unavailable — the shortest usable lag is equal to or greater than the horizon.
- **Use autocorrelation analysis** to identify statistically significant lags before adding them to the pipeline.
- **Avoid redundant lags**: 23 h and 24 h lags are highly correlated; including both adds noise without signal.

Custom Features
---------------

No built-in transform library can anticipate every grid point's idiosyncrasies. A substation serving a large factory will have load spikes tied to shift patterns. A coastal grid point may need tidal or wave-height features. OpenSTEF's transform interface makes it straightforward to encode this knowledge.

To create a custom transform, subclass ``TimeSeriesTransform`` and implement ``transform()`` and ``features_added()``:

.. code-block:: python

   from openstef_core.base_model import BaseConfig
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform

   class ShiftPatternFeatureAdder(BaseConfig, TimeSeriesTransform):
       """Add binary features for industrial shift patterns.

       Marks morning shift (06:00-14:00) and afternoon shift (14:00-22:00)
       on weekdays, which correlate with industrial load at this substation.
       """

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           df = data.data.copy()
           hour = df.index.hour
           is_weekday = df.index.dayofweek < 5

           df["shift_morning"] = ((hour >= 6) & (hour < 14) & is_weekday).astype(float)
           df["shift_afternoon"] = ((hour >= 14) & (hour < 22) & is_weekday).astype(float)

           return data.with_data(df)

       def features_added(self) -> list[str]:
           return ["shift_morning", "shift_afternoon"]

   # Use it exactly like any built-in transform
   shift_transform = ShiftPatternFeatureAdder()
   shift_transform.fit(dataset)
   dataset = shift_transform.transform(dataset)

The ``features_added()`` method is not just documentation — it is used by the pipeline infrastructure to track provenance and can be used to selectively drop or inspect features later.

Avoiding Common Pitfalls
------------------------

**Data leakage through lag selection**
  If you select which lags to include by looking at the full dataset (including the test period), you are leaking future information into your feature selection. Always perform lag selection on the training split only.

**Stale weather forecasts**
  Weather forecast data has its own latency and uncertainty. A temperature forecast issued 6 hours ago is less accurate than one issued 30 minutes ago. Where possible, track the *issue time* of weather forecasts alongside their values.

**Clipping outliers**
  Extreme values in features — a sensor fault producing a 10× spike — can destabilise tree-based models. The built-in ``Clipper`` transform clips feature values to the range observed during training, providing a simple safeguard:

  .. code-block:: python

     from openstef_models.transforms.general import Clipper

     clipper = Clipper(features=["temperature", "wind_speed"])
     clipper.fit(training_dataset)   # learns min/max from training data
     dataset = clipper.transform(dataset)

**Too many features**
  More features are not always better. Irrelevant features add noise and slow training. Use feature importance scores from your trained model (most tree-based models expose these) to prune features that contribute little.

Summary
-------

Effective feature engineering for energy forecasting draws on four pillars:

- **Weather features** — radiation, daylight, atmosphere, and wind transforms encode physical drivers of demand and generation.
- **Time features** — cyclical encodings of hour, day, and season give the model a sense of where it is in the demand cycle.
- **Lag features** — historical load values capture temporal momentum and weekly/daily periodicity; use ``VersionedLagsAdder`` in production to respect data availability.
- **Custom features** — domain-specific transforms for industrial patterns, local geography, or grid topology that no generic library can anticipate.

OpenSTEF's transform library handles the first three categories out of the box. For the fourth, the ``TimeSeriesTransform`` interface gives you a clean extension point that integrates naturally with the rest of the pipeline.

For guidance on how the model training pipeline consumes these features, see :doc:`model_selection`. For information on how forecast uncertainty relates to feature quality, see :doc:`quantiles_and_confidence`.