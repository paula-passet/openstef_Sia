Feature Engineering
===================

Energy load forecasting is fundamentally a feature engineering problem. Raw time series data — a sequence of power measurements — carries surprisingly little predictive signal on its own. What makes a forecast accurate is the set of derived features that capture *why* load behaves the way it does: the time of day, the weather outside, whether it is a public holiday, and what the load was doing at the same time last week. This page explains the feature categories OpenSTEF uses, how each one contributes to forecast accuracy, and how to compose them into a preprocessing pipeline.

.. note::

   This page focuses on feature construction. For an introduction to how forecasts are produced and evaluated, see :doc:`forecasting_basics`. For probabilistic output features such as quantile intervals, see :doc:`quantiles_and_confidence`.

---

Why Features Matter More Than Models
-------------------------------------

OpenSTEF uses classical machine learning models — primarily XGBoost and LightGBM — rather than deep sequence models. This is a deliberate choice: given well-engineered features, gradient-boosted trees match or outperform recurrent networks on short-term energy forecasting while remaining interpretable and fast to retrain. The practical implication is that investing effort in feature quality pays off directly in forecast accuracy.

A good feature for energy forecasting has three properties:

- **Causal relevance** — it reflects a physical or behavioural driver of load (e.g. temperature drives heating and cooling demand).
- **Availability at forecast time** — it must be obtainable for the future horizon, typically from a numerical weather prediction (NWP) feed or from the calendar.
- **Low noise** — a feature that is mostly noise hurts more than it helps by consuming model capacity and introducing variance.

OpenSTEF organises its built-in transforms into four domains: time, weather, energy, and general. Each is a composable ``TimeSeriesTransform`` that can be assembled into a ``FeaturePipeline``.

---

Time Features
-------------

Time-based features are the backbone of any energy forecast. Load follows strong diurnal, weekly, and annual cycles, and these patterns must be made explicit for a tree-based model that has no inherent notion of temporal order.

**Cyclic encoding**

Raw calendar integers (hour = 0–23, day-of-week = 0–6) are ordinal but not cyclic: a model sees hour 23 and hour 0 as maximally distant when they are actually adjacent. ``CyclicFeaturesAdder`` resolves this by encoding each period as a sine/cosine pair, so the representation wraps smoothly around midnight and across the week boundary.

**Datetime decomposition**

``DatetimeFeaturesAdder`` extracts discrete calendar fields — hour, day of week, month, and similar — either as raw integers or as one-hot columns. These complement cyclic features by giving the model explicit categorical handles for patterns that are not smoothly cyclic (e.g. the sharp Monday-morning ramp).

**Holiday indicators**

Public holidays break the normal weekly pattern in ways that cyclic features cannot capture. ``HolidayFeatureAdder`` adds a binary ``is_holiday`` column plus individual columns for each named holiday (``is_christmas_day``, ``is_new_years_day``, etc.), keyed to a country code so that national calendars are respected.

**Lag features**

Lag features are the single most powerful predictor class for short-term load. ``LagsAdder`` adds columns containing the load value at previous time steps. The lags selected are horizon-aware: for a 4-hour-ahead forecast, lags shorter than 4 hours are unavailable and are excluded automatically. The adder can also detect autocorrelation peaks in the training data and select lags algorithmically, avoiding the need to hand-tune lag lists.

**Rolling aggregates**

``RollingAggregatesAdder`` computes rolling statistics (mean, standard deviation, and similar) over configurable windows and horizons. These smooth out short-term noise and give the model a sense of recent trend and volatility. During inference, if recent history is incomplete, the adder falls back to stored training-time aggregates rather than propagating NaN values.

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
       RollingAggregatesAdder,
   )
   from datetime import timedelta

   # Cyclic sine/cosine encoding of hour-of-day and day-of-week
   cyclic = CyclicFeaturesAdder()

   # Raw calendar fields (hour, weekday, month, ...)
   datetime_feats = DatetimeFeaturesAdder(onehot_encode=False)

   # Country-specific public holidays
   holidays_feats = HolidayFeatureAdder(country_code="NL")

   # Lag features for a 1-hour forecast horizon
   lags = LagsAdder(
       history_available=timedelta(days=14),
       horizons=[timedelta(hours=1)],
       add_trivial_lags=True,
       target_column="load_mw",
   )

   # Rolling mean and std over recent windows
   rolling = RollingAggregatesAdder(
       feature="load_mw",
       aggregation_functions=["mean", "std"],
       horizons=[timedelta(hours=1)],
   )

---

Weather Features
----------------

Weather is the dominant external driver of electricity demand. Heating and cooling loads respond directly to temperature; solar generation depends on irradiance; wind generation depends on wind speed. OpenSTEF provides dedicated transforms for each of these relationships.

**Atmosphere-derived features**

``AtmosphereDerivedFeaturesAdder`` takes basic NWP inputs — temperature, relative humidity, and surface pressure — and derives composite meteorological features that have stronger correlations with load than the raw inputs alone. Examples include apparent temperature (which combines temperature and humidity into a perceived-heat index) and dew point.

**Radiation-derived features**

``RadiationDerivedFeaturesAdder`` combines solar irradiance measurements with the geographic coordinates of the forecast location to produce features that account for the sun's elevation angle and the resulting effective irradiance on a horizontal surface. This is particularly important for grids with significant behind-the-meter PV penetration, where solar generation directly offsets net load.

**Daylight features**

``DaylightFeatureAdder`` adds features derived from sunrise and sunset times at the forecast location. These capture the sharp load transitions at dawn and dusk that are not fully represented by irradiance alone (e.g. lighting demand switching on at sunset regardless of cloud cover).

**Wind power features**

``WindPowerFeatureAdder`` converts wind speed into an estimated wind power output using a power-curve transformation. This is more informative than raw wind speed for grids with wind generation because the power curve is nonlinear — a doubling of wind speed does not double power output.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
   from openstef_core.types import Coordinate

   location = Coordinate(lat=52.37, lon=4.90)  # Amsterdam

   atmosphere = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure_hpa",
       relative_humidity_column="humidity_pct",
       temperature_column="temperature_c",
   )

   radiation = RadiationDerivedFeaturesAdder(
       coordinate=location,
       radiation_column="ghi_wm2",
   )

   daylight = DaylightFeatureAdder(coordinate=location)

   wind_power = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_ms")

.. note::

   Weather features require NWP forecast data to be available at inference time. The quality of your weather input directly bounds the quality of your load forecast — no amount of feature engineering compensates for poor or missing weather data.

---

Assembling a Feature Pipeline
------------------------------

Individual transforms are composed into a ``FeaturePipeline`` that is embedded inside a ``ForecastingModel``. The pipeline applies transforms sequentially during both training and inference, ensuring that the same feature construction logic is used in both phases.

The following example assembles a complete feature pipeline combining time and weather transforms, then wraps it in a forecasting model:

.. code-block:: python

   from openstef_models.transforms.time_domain import (
       CyclicFeaturesAdder,
       DatetimeFeaturesAdder,
       HolidayFeatureAdder,
       LagsAdder,
   )
   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       DaylightFeatureAdder,
       RadiationDerivedFeaturesAdder,
   )
   from openstef_models.transforms.general import (
       EmptyFeatureRemover,
       OutlierHandler,
       Scaler,
   )
   from openstef_core.types import Coordinate
   from datetime import timedelta

   location = Coordinate(lat=52.37, lon=4.90)
   horizons = [timedelta(hours=1), timedelta(hours=4), timedelta(hours=24)]

   feature_pipeline_steps = [
       # Lag features — must come before scaling
       LagsAdder(
           history_available=timedelta(days=14),
           horizons=horizons,
           add_trivial_lags=True,
           target_column="load_mw",
       ),
       # Weather-derived features
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure_hpa",
           relative_humidity_column="humidity_pct",
           temperature_column="temperature_c",
       ),
       RadiationDerivedFeaturesAdder(
           coordinate=location,
           radiation_column="ghi_wm2",
       ),
       DaylightFeatureAdder(coordinate=location),
       # Time features
       CyclicFeaturesAdder(),
       DatetimeFeaturesAdder(onehot_encode=False),
       HolidayFeatureAdder(country_code="NL"),
       # Cleanup and normalisation
       EmptyFeatureRemover(),
       OutlierHandler(mode="standard"),
       Scaler(method="standard"),
   ]

The order of steps matters. Lag features should be added before scaling so that the scaler sees the full feature matrix. ``EmptyFeatureRemover`` should run after all feature adders so that any columns that turned out to be entirely NaN (e.g. a weather variable not present in the input) are dropped cleanly rather than causing downstream errors.

---

Custom Features
---------------

OpenSTEF's transform interface is designed to be extended. Any class that implements ``TimeSeriesTransform`` — with ``transform(data: TimeSeriesDataset) -> TimeSeriesDataset`` and ``features_added() -> list[str]`` methods — can be inserted into a pipeline alongside the built-in transforms.

A common use case is adding domain-specific signals: industrial production schedules, school term calendars, or grid-specific event flags.

.. code-block:: python

   from openstef_core.datasets import TimeSeriesDataset
   from openstef_core.transforms import TimeSeriesTransform
   import pandas as pd

   class SchoolTermFeatureAdder(TimeSeriesTransform):
       """Adds a binary feature indicating school term periods."""

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           # Example: mark September–June weekdays as school term
           idx = data.index
           is_term = (
               idx.month.isin(range(9, 13)) | idx.month.isin(range(1, 7))
           ) & (idx.dayofweek < 5)
           data["is_school_term"] = is_term.astype(int)
           return data

       def features_added(self) -> list[str]:
           return ["is_school_term"]

   # Drop it into any pipeline
   feature_pipeline_steps.append(SchoolTermFeatureAdder())

.. note::

   When writing custom transforms, always implement ``features_added()`` accurately. OpenSTEF uses this method to track which columns were introduced by each transform, enabling diagnostics and the ``EmptyFeatureRemover`` to work correctly.

---

What to Avoid
-------------

A few common pitfalls are worth naming explicitly:

- **Leaking future information into lag features.** ``LagsAdder`` handles horizon-awareness automatically, but hand-crafted lag columns can accidentally include values that would not be available at forecast time. Always verify that custom lag features respect the forecast horizon.
- **High-cardinality one-hot features.** One-hot encoding a feature with many categories (e.g. a raw timestamp string) inflates the feature matrix and rarely adds signal. Prefer cyclic or ordinal encodings for time-based fields.
- **Correlated weather inputs without derivation.** Raw temperature and humidity are correlated. Feeding both directly without deriving composite features (apparent temperature, dew point) can cause the model to double-count the same physical signal. The ``AtmosphereDerivedFeaturesAdder`` handles this derivation for you.
- **Features unavailable at inference time.** Any feature used during training must also be computable during inference. Actual load values from the forecast period are never available — only lagged values from before the forecast horizon are valid.

---

Further Reading
---------------

- :doc:`forecasting_basics` — how OpenSTEF turns features into probabilistic forecasts and what the training loop looks like.
- :doc:`quantiles_and_confidence` — how feature uncertainty propagates into quantile outputs.
- :doc:`reliability_and_fallback` — what happens when weather inputs are missing or stale at inference time.