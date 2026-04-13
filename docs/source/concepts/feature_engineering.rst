Feature Engineering for Energy Forecasting
===========================================

Good forecasting models are only as good as the features they learn from. In energy
forecasting, raw load measurements alone are rarely sufficient — the model needs
context: what time of day is it, how warm is it outside, is it a holiday, what was
the load doing an hour ago? This page explains the feature categories that matter
most for short-term energy forecasting and shows how OpenSTEF's built-in transforms
let you construct them systematically.

For background on what short-term forecasting is and why it matters, see
:doc:`forecasting_basics`. For information on how models are selected and trained
on these features, see :doc:`model_selection`.

.. mermaid:: diagrams/concepts/feature_engineering_diagram_1.mmd

What Makes a Good Energy Feature
---------------------------------

A useful feature for energy forecasting has two properties: it is **causally related**
to electricity demand, and it is **available at forecast time** (i.e., you can obtain
it for future timestamps, not just the past). Weather forecasts, calendar information,
and lagged load values all satisfy both criteria, which is why they form the backbone
of most energy forecasting feature sets.

Features that are highly correlated with load but unavailable in the future — such as
the current load value itself — can only be used as lagged inputs. Features that are
available but uncorrelated with load add noise and can hurt model performance. The
transforms described below are designed with these constraints in mind.

Weather Features
----------------

Weather is the dominant external driver of electricity demand. Temperature governs
heating and cooling loads; solar radiation determines both PV generation and cooling
demand; wind speed drives wind power output; atmospheric pressure and humidity affect
industrial and HVAC loads.

OpenSTEF provides dedicated transform classes for each of these domains, all living
under ``openstef_models.transforms``.

**Radiation-derived features**

The ``RadiationDerivedFeaturesAdder`` takes a raw global horizontal irradiance column
and derives additional solar-relevant quantities. Because the relationship between
radiation and PV output is non-linear and location-dependent, this transform also
requires the geographic coordinate of the substation or measurement point:

.. code-block:: python

    from datetime import timedelta
    import pandas as pd
    from pydantic_extra_types.coordinate import Coordinate
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.weather_domain import RadiationDerivedFeaturesAdder

    data = pd.DataFrame(
        {"load": [...], "radiation": [...]},
        index=pd.date_range("2024-01-01", periods=96, freq="15min"),
    )
    dataset = TimeSeriesDataset(data, timedelta(minutes=15))

    adder = RadiationDerivedFeaturesAdder(
        coordinate=Coordinate(latitude=52.37, longitude=4.90),
        radiation_column="radiation",
    )
    enriched = adder.fit_transform(dataset)

**Daylight features**

``DaylightFeatureAdder`` adds features that encode whether it is currently daylight
and how far through the daylight window the current timestamp falls. These features
are computed purely from the timestamp and location — no measured input column is
needed — making them reliable even when sensor data is missing:

.. code-block:: python

    from openstef_models.transforms.weather_domain import DaylightFeatureAdder

    daylight = DaylightFeatureAdder(
        coordinate=Coordinate(latitude=52.37, longitude=4.90)
    )
    enriched = daylight.fit_transform(dataset)

**Wind power features**

``WindPowerFeatureAdder`` converts a wind speed measurement into an estimated wind
power output using the characteristic cubic relationship between wind speed and power.
This is particularly useful when forecasting net load on grids with significant wind
generation:

.. code-block:: python

    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    wind = WindPowerFeatureAdder(windspeed_reference_column="wind_speed")
    enriched = wind.fit_transform(dataset)

**Atmosphere-derived features**

``AtmosphereDerivedFeaturesAdder`` combines temperature, relative humidity, and
atmospheric pressure into composite indices such as apparent temperature (heat index
or wind chill equivalent). These composite measures often correlate more strongly with
demand than raw temperature alone because human thermal comfort — and therefore HVAC
load — responds to perceived rather than measured temperature:

.. code-block:: python

    from openstef_models.transforms.weather_domain import AtmosphereDerivedFeaturesAdder

    atmos = AtmosphereDerivedFeaturesAdder(
        pressure_column="pressure",
        relative_humidity_column="humidity",
        temperature_column="temperature",
    )
    enriched = atmos.fit_transform(dataset)

Time and Calendar Features
---------------------------

Electricity demand follows strong periodic patterns: a morning ramp-up, an evening
peak, a weekend dip, a summer cooling season. Encoding these patterns explicitly
gives tree-based models like XGBoost the information they need to learn these
rhythms without having to infer them from noisy load history alone.

**Datetime features**

``DatetimeFeaturesAdder`` extracts scalar calendar fields — hour of day, day of week,
month, and similar quantities — directly from the timestamp index. When
``onehot_encode=False`` (the default for XGBoost), these are kept as integers so the
model can exploit their ordinal structure:

.. code-block:: python

    from openstef_models.transforms.time_domain import DatetimeFeaturesAdder

    dt = DatetimeFeaturesAdder(onehot_encode=False)
    enriched = dt.fit_transform(dataset)

**Cyclic features**

Raw integer hour-of-day features have an artificial discontinuity: hour 23 and hour 0
look far apart numerically but are adjacent in reality. ``CyclicFeaturesAdder``
resolves this by encoding periodic quantities as sine/cosine pairs, producing a smooth
circular representation that models can learn from without boundary artefacts:

.. code-block:: python

    from openstef_models.transforms.time_domain import CyclicFeaturesAdder

    cyclic = CyclicFeaturesAdder()
    enriched = cyclic.fit_transform(dataset)

**Holiday features**

Public holidays cause load profiles that look like weekends but fall on weekdays,
creating systematic errors if not accounted for. ``HolidayFeatureAdder`` adds a
binary holiday indicator using the country code of the forecast location:

.. code-block:: python

    from openstef_models.transforms.time_domain import HolidayFeatureAdder

    holidays = HolidayFeatureAdder(country_code="NL")
    enriched = holidays.fit_transform(dataset)

Load Pattern Features
----------------------

Historical load values are among the most informative features available, because
demand at a given time is strongly correlated with demand at the same time yesterday,
last week, and in the preceding hours. OpenSTEF provides two complementary approaches
for capturing these patterns.

**Lag features**

``LagsAdder`` adds columns containing the load value at specific offsets into the
past. The library provides helper functions to generate sensible lag sets
automatically:

.. code-block:: python

    from datetime import timedelta
    from openstef_models.transforms.time_domain.lags_adder import (
        LagsAdder,
        generate_day_lags,
        generate_minute_lags,
        generate_autocorr_lags,
    )

    max_horizon = timedelta(hours=48)

    # Minute-resolution lags for the immediate past
    minute_lags = generate_minute_lags(max_horizon)

    # Daily lags to capture same-time-yesterday and same-time-last-week patterns
    day_lags = generate_day_lags(max_horizon, max_day_lags=7)

    # Data-driven lags based on autocorrelation peaks in the training signal
    autocorr_lags = generate_autocorr_lags(
        signal=dataset.data["load"],
        max_horizon=max_horizon,
        height_threshold=0.1,
    )

    lags = LagsAdder(lags=minute_lags + day_lags + autocorr_lags, horizons=[max_horizon])
    enriched = lags.fit_transform(dataset)

The ``generate_autocorr_lags`` function is particularly useful because it identifies
the lag offsets where the signal is most self-similar, rather than relying on
hand-crafted rules.

**Rolling aggregates**

Where lag features capture a single point in the past, rolling aggregates summarise
recent behaviour over a window. ``RollingAggregatesAdder`` computes statistics such
as mean, max, and median over a rolling window and adds them as features. It also
handles the common inference-time problem where recent load values are unavailable
by falling back to the last valid aggregate computed during training:

.. code-block:: python

    from openstef_models.transforms.time_domain import RollingAggregatesAdder
    from openstef_models.lead_time import LeadTime

    rolling = RollingAggregatesAdder(
        feature="load",
        rolling_window_size=timedelta(hours=2),
        aggregation_functions=["mean", "max"],
        horizons=[LeadTime.from_string("PT36H")],
    )
    rolling.fit(dataset)
    enriched = rolling.transform(dataset)

This produces columns such as ``rolling_mean_load_PT2H`` and
``rolling_max_load_PT2H``, which capture whether load is currently trending up or
down and how volatile it has been recently.

Assembling a Feature Pipeline
-------------------------------

In practice, you will want to apply several transforms in sequence. OpenSTEF's
``TransformPipeline`` chains transforms so that each one receives the output of the
previous step. The pipeline's ``fit`` method fits each transform on the progressively
enriched dataset, and ``transform`` applies all fitted transforms in order:

.. code-block:: python

    from openstef_core.transforms import TransformPipeline
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_models.transforms.time_domain import (
        DatetimeFeaturesAdder,
        CyclicFeaturesAdder,
        HolidayFeatureAdder,
        RollingAggregatesAdder,
    )
    from openstef_models.transforms.weather_domain import (
        RadiationDerivedFeaturesAdder,
        DaylightFeatureAdder,
        AtmosphereDerivedFeaturesAdder,
    )
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    pipeline = TransformPipeline[TimeSeriesDataset](
        transforms=[
            AtmosphereDerivedFeaturesAdder(
                pressure_column="pressure",
                relative_humidity_column="humidity",
                temperature_column="temperature",
            ),
            RadiationDerivedFeaturesAdder(
                coordinate=Coordinate(latitude=52.37, longitude=4.90),
                radiation_column="radiation",
            ),
            DaylightFeatureAdder(
                coordinate=Coordinate(latitude=52.37, longitude=4.90)
            ),
            WindPowerFeatureAdder(windspeed_reference_column="wind_speed"),
            DatetimeFeaturesAdder(onehot_encode=False),
            CyclicFeaturesAdder(),
            HolidayFeatureAdder(country_code="NL"),
            RollingAggregatesAdder(
                feature="load",
                rolling_window_size=timedelta(hours=2),
                aggregation_functions=["mean", "max"],
                horizons=[LeadTime.from_string("PT36H")],
            ),
        ]
    )

    pipeline.fit(train_dataset)
    enriched_train = pipeline.transform(train_dataset)
    enriched_test = pipeline.transform(test_dataset)

.. note::

   The pipeline fits each transform on the **output** of all preceding transforms.
   Order matters: place feature adders before standardisers, and standardisers before
   model-specific transforms.

Writing Custom Feature Transforms
-----------------------------------

If your use case requires domain-specific features not covered by the built-in
transforms — for example, industrial process schedules, tidal data for coastal grids,
or EV charging session counts — you can implement a custom transform by subclassing
``TimeSeriesTransform``:

.. code-block:: python

    from typing import override
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform

    class IndustrialScheduleAdder(TimeSeriesTransform):
        """Adds a binary feature indicating scheduled industrial activity."""

        def __init__(self, schedule_column: str):
            self.schedule_column = schedule_column

        @property
        @override
        def is_fitted(self) -> bool:
            return True  # stateless transform, no fitting required

        @override
        def fit(self, data: TimeSeriesDataset) -> None:
            pass  # nothing to learn from data

        @override
        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            df = data.data.copy()
            df["industrial_active"] = (df[self.schedule_column] > 0).astype(int)
            return TimeSeriesDataset(df, data.sample_interval)

        @override
        def features_added(self) -> list[str]:
            return ["industrial_active"]

The ``features_added`` method is used by the pipeline for bookkeeping and by
downstream components that need to know which columns were introduced by each step.
Stateful transforms — those that learn parameters from training data, such as a
custom scaler — should set ``is_fitted`` to ``False`` until ``fit`` has been called
and store their learned state as instance attributes.

.. note::

   Custom transforms slot directly into ``TransformPipeline`` alongside the built-in
   ones. There is no registration step required — just instantiate your transform and
   include it in the ``transforms`` list.

Practical Guidance
-------------------

A few principles that hold across most energy forecasting applications:

- **Weather features are non-negotiable for generation-heavy grids.** On a network
  with significant solar or wind penetration, omitting radiation or wind speed features
  will produce large systematic errors during weather extremes.

- **Cyclic encoding matters more than it might seem.** The discontinuity at midnight
  in raw hour-of-day features is a genuine source of model error, particularly for
  models trained on limited data.

- **Lag selection should be data-driven where possible.** Use ``generate_autocorr_lags``
  on your specific load signal rather than assuming that 24-hour and 168-hour lags are
  always the most informative.

- **Rolling aggregates help at longer horizons.** At a 36-hour forecast horizon, the
  most recent individual lag value may be 36 hours stale. A rolling mean over the last
  few hours is a more stable summary of recent load level.

- **Holiday calendars need to match the country.** ``HolidayFeatureAdder`` accepts an
  ISO 3166-1 alpha-2 country code. Using the wrong country silently produces incorrect
  holiday flags, which can degrade weekday forecast accuracy.

The feature engineering pipeline described here feeds directly into the model training
process. For details on how OpenSTEF selects and evaluates models given a feature
matrix, see :doc:`model_selection`. For an explanation of how uncertainty is
represented in the resulting forecasts, see :doc:`quantiles_and_confidence`.