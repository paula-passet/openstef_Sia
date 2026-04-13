Feature Engineering
===================

Good forecasting models are only as good as the features they learn from. In energy forecasting, raw measurements — a timestamp and a load reading — are rarely enough on their own. The models need context: what time of day is it, how sunny will it be, what was the load doing an hour ago? This page explains the feature categories that matter most for short-term energy forecasting and shows how OpenSTEF's built-in transforms handle them.

For background on the forecasting task itself, see :doc:`forecasting_basics`. For how features interact with model choice, see :doc:`model_selection`.

.. note:: [DIAGRAM: Feature engineering pipeline — raw inputs (timestamp, load, weather) flowing through transform stages (time domain, weather domain, energy domain) into a feature matrix fed to the model]

What Makes a Good Feature for Energy Forecasting
-------------------------------------------------

A useful feature has two properties: it correlates with the load you are trying to predict, and it is *available at forecast time*. That second constraint is easy to overlook. A feature derived from the actual future load is useless in production — you don't have it yet. Features derived from weather *forecasts*, calendar data, or lagged historical observations all satisfy the availability requirement and form the backbone of OpenSTEF's feature set.

The other practical consideration is that energy load is driven by human behaviour and physical processes that repeat on well-understood cycles — daily routines, weekly work patterns, seasonal heating and cooling demand, and the solar cycle. Features that encode these cycles explicitly give tree-based models like XGBoost and LightGBM a significant advantage, because those models cannot extrapolate beyond their training range and benefit greatly from having periodic structure made explicit.

Time Features
-------------

The most universally important features in any energy forecasting problem are derived from the timestamp. OpenSTEF provides two complementary transforms for this.

**Cyclic encoding** is the right way to represent periodic quantities to a machine learning model. A raw hour-of-day column that jumps from 23 back to 0 looks like a discontinuity to a tree-based model. Encoding it as sine and cosine components wraps the cycle smoothly so that 23:00 and 00:00 are correctly understood as adjacent. ``CyclicFeaturesAdder`` handles this for four standard cycles:

.. code-block:: python

   import pandas as pd
   from datetime import timedelta
   from openstef_core.datasets import TimeSeriesDataset
   from openstef_models.transforms.time_domain import CyclicFeaturesAdder

   data = pd.DataFrame(
       {"load": [100, 120, 110, 130]},
       index=pd.date_range("2025-06-01 00:00", periods=4, freq="1h"),
   )
   dataset = TimeSeriesDataset(data, timedelta(hours=1))

   # Encode time-of-day, day-of-week, month, and season as sine/cosine pairs
   transform = CyclicFeaturesAdder(
       included_features=["time_of_day", "day_of_week", "month", "season"]
   )
   transformed = transform.transform(dataset)
   print(transformed.data.filter(like="_sine").head(2))

This produces columns such as ``time_of_day_sine``, ``time_of_day_cosine``, ``season_sine``, and so on. Each cyclic feature contributes two columns, giving the model both the phase and the symmetry of the cycle.

**One-hot and ordinal datetime features** are added by ``DatetimeFeaturesAdder``, which extracts components such as hour, day of week, and month as plain integer or one-hot columns. These are useful for linear models that can directly use ordinal structure.

**Holiday indicators** are added by ``HolidayFeatureAdder``, which marks public holidays for a given country. Load profiles on holidays often resemble Sundays rather than the weekday they fall on, and flagging them explicitly prevents the model from treating them as anomalies.

.. code-block:: python

   from openstef_models.transforms.time_domain import HolidayFeatureAdder

   holiday_adder = HolidayFeatureAdder(country_code="NL")
   transformed = holiday_adder.transform(dataset)

Weather Features
----------------

Weather is the dominant driver of short-term load variation in most grids. Temperature drives heating and cooling demand; solar radiation determines both PV generation and passive solar heating; wind speed affects both wind power output and building heat loss. OpenSTEF provides dedicated transforms for each of these domains.

``AtmosphereDerivedFeaturesAdder`` computes derived meteorological features from basic weather inputs — temperature, relative humidity, and atmospheric pressure. These derived quantities (such as dew point or apparent temperature) often correlate more directly with human thermal comfort, and therefore with load, than the raw measurements alone.

``RadiationDerivedFeaturesAdder`` takes solar radiation measurements and the site's geographic coordinates and produces features that capture the relationship between irradiance and the solar position. Because the same radiation value means different things at solar noon versus near sunset, position-aware features carry more information than raw irradiance.

``DaylightFeatureAdder`` adds features based on sunrise and sunset times for the site's location. These are particularly valuable for capturing the sharp morning and evening ramps in both load and PV generation.

``WindPowerFeatureAdder`` converts wind speed into an estimate of wind power output, applying the characteristic cubic relationship between wind speed and power that governs wind turbine behaviour.

.. code-block:: python

   from openstef_models.transforms.weather_domain import (
       AtmosphereDerivedFeaturesAdder,
       RadiationDerivedFeaturesAdder,
       DaylightFeatureAdder,
       WindPowerFeatureAdder,
   )
   from openstef_core.datasets import TimeSeriesDataset

   # Assuming `dataset` contains columns: temperature, relative_humidity,
   # pressure, radiation, windspeed
   atm = AtmosphereDerivedFeaturesAdder(
       pressure_column="pressure",
       relative_humidity_column="relative_humidity",
       temperature_column="temperature",
   )
   rad = RadiationDerivedFeaturesAdder(
       coordinate=(52.37, 4.90),   # Amsterdam
       radiation_column="radiation",
   )
   daylight = DaylightFeatureAdder(coordinate=(52.37, 4.90))
   wind = WindPowerFeatureAdder(windspeed_reference_column="windspeed")

   dataset = atm.transform(dataset)
   dataset = rad.transform(dataset)
   dataset = daylight.transform(dataset)
   dataset = wind.transform(dataset)

.. note::

   Weather features are only as good as the weather forecast driving them. During training, observed weather measurements are used. At inference time, the model receives numerical weather prediction (NWP) data. Any systematic bias between observed and forecast weather will degrade forecast quality, so it is worth monitoring weather forecast error separately from model error.

Load Pattern Features (Rolling Aggregates and Lags)
----------------------------------------------------

Recent load history is one of the strongest predictors of near-future load. A grid connection that was drawing 500 kW ten minutes ago is likely still drawing close to 500 kW. ``RollingAggregatesAdder`` captures this by computing rolling statistics — mean, median, minimum, maximum — over a configurable window and set of forecast horizons.

.. code-block:: python

   from datetime import timedelta
   from openstef_models.transforms.time_domain import RollingAggregatesAdder
   from openstef_core.lead_time import LeadTime

   rolling = RollingAggregatesAdder(
       feature="load",
       rolling_window_size=timedelta(hours=2),
       aggregation_functions=["mean", "max"],
       horizons=[LeadTime.from_string("PT36H")],
   )
   rolling.fit(dataset)        # learns fallback values from training data
   transformed = rolling.transform(dataset)

   # New columns: rolling_mean_load_PT2H, rolling_max_load_PT2H
   print(transformed.data[["rolling_mean_load_PT2H", "rolling_max_load_PT2H"]].head())

A key design detail: ``RollingAggregatesAdder`` requires a ``fit`` step. During training, it records the last valid aggregate values. At inference time, when future load is unavailable, it falls back to forward-filling from the most recent computed aggregate, then to the training-time fallback. This makes the transform safe to use in production without special-casing the inference path.

Lag features — the load value at a fixed offset in the past — complement rolling aggregates by giving the model direct access to specific historical points. The library provides utilities to generate lag sets automatically:

.. code-block:: python

   from openstef_models.transforms.time_domain.versioned_lags_adder import (
       generate_minute_lags,
       generate_day_lags,
       generate_autocorr_lags,
   )

   # Generate lags at 15-minute intervals up to the forecast horizon
   minute_lags = generate_minute_lags(max_horizon=timedelta(hours=36))

   # Generate daily lags (same time yesterday, same time last week, etc.)
   day_lags = generate_day_lags(max_horizon=timedelta(hours=36), max_day_lags=7)

   # Automatically identify lags at autocorrelation peaks
   autocorr_lags = generate_autocorr_lags(
       signal=dataset.data["load"],
       max_horizon=timedelta(hours=36),
   )

The autocorrelation-based approach is particularly useful when you are not sure which lags matter: it inspects the signal itself and selects lags at peaks in the autocorrelation function, which correspond to the dominant periodicities in the data.

Custom Features
---------------

OpenSTEF is a library, and its transform architecture is designed to be extended. Any custom feature logic can be packaged as a ``TimeSeriesTransform`` subclass and dropped into the same pipeline as the built-in transforms.

The interface is minimal: implement ``transform``, optionally implement ``fit`` if the transform needs to learn from training data, and implement ``features_added`` to declare which columns your transform produces.

.. code-block:: python

   from openstef_models.transforms.base import TimeSeriesTransform
   from openstef_core.datasets import TimeSeriesDataset
   import pandas as pd

   class TemperatureSquaredAdder(TimeSeriesTransform):
       """Adds a squared temperature feature to capture non-linear heating demand."""

       def features_added(self) -> list[str]:
           return ["temperature_squared"]

       def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
           new_data = data.data.copy()
           new_data["temperature_squared"] = new_data["temperature"] ** 2
           return TimeSeriesDataset(new_data, data.sample_interval)

   custom_transform = TemperatureSquaredAdder()
   transformed = custom_transform.transform(dataset)

Because ``TimeSeriesTransform`` is stateless by default (``is_fitted`` returns ``True`` without a ``fit`` call), simple transforms like this require no additional boilerplate. Stateful transforms — those that learn parameters from training data — should override ``is_fitted`` to return ``False`` until ``fit`` has been called, following the same pattern as ``RollingAggregatesAdder``.

Once written, a custom transform slots into the standard pipeline alongside built-in transforms:

.. code-block:: python

   pipeline_transforms = [
       AtmosphereDerivedFeaturesAdder(
           pressure_column="pressure",
           relative_humidity_column="relative_humidity",
           temperature_column="temperature",
       ),
       TemperatureSquaredAdder(),          # custom transform, same interface
       CyclicFeaturesAdder(),
       HolidayFeatureAdder(country_code="NL"),
   ]

   for t in pipeline_transforms:
       dataset = t.transform(dataset)

Feature Selection Considerations
---------------------------------

Adding more features is not always better. Irrelevant or redundant features increase training time, can degrade model generalisation, and make it harder to diagnose problems. A few practical guidelines:

- **Start with the built-in transforms.** They encode domain knowledge accumulated from operational deployments and cover the most important signal categories for most grid connections.
- **Add weather features only when you have reliable forecast data.** A weather feature derived from a poor NWP source can hurt more than it helps.
- **Lag features should respect the forecast horizon.** A lag of 15 minutes is only valid for a 15-minute-ahead forecast; using it for a 24-hour-ahead forecast means the feature will be unavailable at inference time. The ``horizons`` parameter on ``RollingAggregatesAdder`` enforces this automatically.
- **Monitor feature importance over time.** The relative importance of features can shift seasonally or as the grid connection changes (e.g., new PV installation). OpenSTEF's models expose feature importance through the underlying XGBoost and LightGBM APIs.

The ``EmptyFeatureRemover`` transform, used in the standard pipeline, automatically drops columns that are entirely null after the feature engineering stage, providing a safety net against features that fail to compute due to missing input data.

Related Topics
--------------

- :doc:`forecasting_basics` — how the forecasting task is framed and what the model is actually predicting
- :doc:`model_selection` — how feature choices interact with model selection and which models benefit most from engineered features
- :doc:`quantiles_and_confidence` — how uncertainty estimates are produced from the same feature set
- :doc:`reliability_and_fallback` — what happens when feature inputs (such as weather data) are missing at inference time