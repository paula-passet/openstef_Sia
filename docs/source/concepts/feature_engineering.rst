Feature Engineering
===================

Good forecasting models are only as good as the features they are trained on. In energy
forecasting, raw inputs like a timestamp and a weather reading rarely tell the full story
on their own. This page explains how OpenSTEF approaches feature engineering: which
predictors matter, why they work, and how to extend the built-in transforms with your
own domain knowledge.

For background on what short-term forecasting is and why it is useful, see
:doc:`forecasting_basics`. For information on how features interact with model selection,
see :doc:`model_selection`.

.. mermaid:: diagrams/concepts/feature_engineering_diagram_1.mmd

What Makes a Good Energy Feature
---------------------------------

Energy demand and generation are shaped by a small number of well-understood physical
and social drivers. A good feature captures one of those drivers in a form that a
machine learning model can exploit:

- **It is available at forecast time.** A feature derived from tomorrow's measured load
  cannot be used to forecast tomorrow's load. Lag features must respect the forecast
  horizon.
- **It is predictable.** Weather forecasts are imperfect, but they are available days
  ahead. Astronomical quantities like solar elevation are perfectly predictable. Both
  are useful; unmeasurable quantities are not.
- **It encodes domain knowledge.** Transforming raw wind speed into an estimated wind
  power output (which follows a cubic relationship at low speeds) gives the model a
  head start that would otherwise require many training samples to learn implicitly.
- **It varies with the target.** A feature that is constant, or that correlates with
  the target only by coincidence in the training set, adds noise rather than signal.

OpenSTEF ships a library of transforms that encode decades of energy-domain knowledge.
Each transform is a ``TimeSeriesTransform`` subclass that implements ``fit``,
``transform``, and ``features_added()``, so you always know exactly which columns a
transform contributes.

Weather Features
----------------

Weather is the dominant driver of both demand (heating, cooling) and renewable
generation (solar, wind). OpenSTEF provides three dedicated weather-domain transforms.

**Radiation-derived features** (``RadiationDerivedFeaturesAdder``) turn a raw
global-horizontal irradiance reading into quantities that more directly predict
photovoltaic output, such as clear-sky fraction and diffuse/direct decomposition.
Because PV output is non-linear in irradiance, these derived quantities give
gradient-boosted models a much cleaner signal than the raw value alone.

**Atmosphere-derived features** (``AtmosphereDerivedFeaturesAdder``) combine pressure,
relative humidity, and temperature into secondary meteorological quantities — for
example, dew point and absolute humidity — that correlate with heating and cooling load
better than temperature alone in humid climates.

**Wind power features** (``WindPowerFeatureAdder``) apply a physics-based power curve
to convert wind speed into an estimated wind power output. The cubic relationship
between wind speed and power in the partial-load regime is hard for a tree-based model
to learn from raw speed values; encoding it explicitly reduces the amount of training
data needed to achieve good accuracy.

.. code-block:: python

    from openstef_models.transforms.weather_domain import (
        AtmosphereDerivedFeaturesAdder,
        RadiationDerivedFeaturesAdder,
    )
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder

    # Each transform declares which columns it needs and which it adds
    radiation_adder = RadiationDerivedFeaturesAdder(
        coordinate=(52.1, 5.1),          # lat/lon for solar geometry
        radiation_column="ghi",
    )
    wind_adder = WindPowerFeatureAdder(windspeed_reference_column="wind_speed_10m")
    atmos_adder = AtmosphereDerivedFeaturesAdder(
        pressure_column="pressure_hpa",
        relative_humidity_column="rh_pct",
        temperature_column="temp_c",
    )

    dataset = radiation_adder.fit_transform(dataset)
    dataset = wind_adder.fit_transform(dataset)
    dataset = atmos_adder.fit_transform(dataset)

    print(radiation_adder.features_added())   # inspect added column names

Time and Calendar Features
---------------------------

Electricity consumption follows strong periodic patterns: the morning ramp-up, the
lunch dip, the evening peak, the weekend valley, and the holiday anomaly. Encoding
these patterns explicitly is one of the highest-leverage things you can do in energy
feature engineering.

**Datetime features** (``DatetimeFeaturesAdder``) extract the calendar components of
the timestamp — hour of day, day of week, month, and so on. These can be emitted as
raw integers or as one-hot encoded columns depending on the model type. XGBoost
typically works well with raw integers; linear models benefit from one-hot encoding.

**Cyclic features** (``CyclicFeaturesAdder``) go one step further by encoding periodic
quantities as sine/cosine pairs. A raw "hour = 23" and "hour = 0" look far apart to a
model that treats hour as a continuous variable, yet they are only 15 minutes apart on
the clock. Sine/cosine encoding wraps the period correctly so the model sees the true
proximity.

**Holiday features** (``HolidayFeatureAdder``) add binary indicators for public
holidays using country-specific calendars. A holiday Monday has a load profile that
looks nothing like a regular Monday, and without an explicit indicator the model will
systematically mis-forecast it.

**Daylight features** (``DaylightFeatureAdder``) add astronomy-derived quantities such
as solar elevation angle and day length for the forecast location. These are perfectly
predictable at any horizon and are particularly valuable for solar generation and
lighting-driven demand.

.. code-block:: python

    from openstef_models.transforms.time_domain import (
        CyclicFeaturesAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
    )
    from openstef_models.transforms.weather_domain import DaylightFeatureAdder

    datetime_adder = DatetimeFeaturesAdder(onehot_encode=False)
    cyclic_adder = CyclicFeaturesAdder()
    holiday_adder = HolidayFeatureAdder(country_code="NL")
    daylight_adder = DaylightFeatureAdder(coordinate=(52.1, 5.1))

    for transform in [datetime_adder, cyclic_adder, holiday_adder, daylight_adder]:
        dataset = transform.fit_transform(dataset)

.. note::

   ``HolidayFeatureAdder`` uses the ``holidays`` library under the hood and supports
   any ISO 3166-1 alpha-2 country code. Each distinct public holiday in the country's
   calendar gets its own binary column, so the model can learn that Christmas and
   Easter have different load shapes.

Load History and Lag Features
------------------------------

Recent load measurements are among the strongest predictors of future load. A
substation that was heavily loaded an hour ago is likely to remain heavily loaded; a
building that was empty yesterday at this time is probably empty again today.

OpenSTEF provides ``LagsAdder`` for creating lagged copies of the target variable.
Three strategies are available:

- **Trivial lags** — fixed offsets in minutes (e.g., 15, 30, 45, 60 minutes back).
  Useful for capturing inertia in the very short term.
- **Day-based lags** — the same time slot one day ago, two days ago, and one week ago.
  These capture the daily and weekly periodicity of load.
- **Autocorrelation-based lags** — the library analyses the autocorrelation function of
  the training data and selects the lag offsets that carry the most information. This
  is the recommended default because it adapts to the specific periodicity of each
  asset.

.. code-block:: python

    from openstef_models.transforms.time_domain import LagsAdder
    from datetime import timedelta

    # Autocorrelation-based lag selection (recommended)
    lags_adder = LagsAdder(strategy="autocorrelation")

    # Or specify explicit lag offsets
    lags_adder = LagsAdder(
        strategy="custom",
        lags=[
            timedelta(minutes=15),
            timedelta(minutes=30),
            timedelta(days=1),
            timedelta(days=7),
        ],
    )

    dataset = lags_adder.fit_transform(dataset)

.. warning::

   Lag features must respect the forecast horizon. If you are forecasting 4 hours
   ahead, you cannot use a lag of 1 hour — that measurement will not be available at
   forecast time. ``LagsAdder`` enforces this automatically when horizon information
   is present in the dataset. For versioned datasets where data availability varies
   over time, use ``VersionedLagsAdder`` instead.

Rolling Aggregates
------------------

Where lag features capture a single historical point, rolling aggregates summarise a
window of recent history. A rolling mean over the past 24 hours smooths out noise and
captures the baseline level; a rolling maximum highlights recent peak events that may
recur.

``RollingAggregatesAdder`` computes configurable aggregation functions (mean, max, min,
standard deviation, and others) over configurable windows, aligned to the forecast
horizons so that no future data leaks into the feature.

.. code-block:: python

    from openstef_models.transforms.time_domain import RollingAggregatesAdder
    from datetime import timedelta

    rolling_adder = RollingAggregatesAdder(
        feature="load_mw",
        aggregation_functions=["mean", "max", "std"],
        horizons=[timedelta(hours=1), timedelta(hours=24)],
    )

    dataset = rolling_adder.fit_transform(dataset)

Writing Custom Transforms
--------------------------

When built-in transforms do not cover a specific driver — for example, a local
industrial customer whose load correlates with a production schedule, or a custom
price signal — you can write your own transform by subclassing
``TimeSeriesTransform``.

The interface is minimal: implement ``transform`` to add columns to the dataset and
``features_added`` to declare which columns you add. The ``fit`` method is optional;
override it only if your transform needs to learn parameters from training data (for
example, to compute a rolling baseline).

.. code-block:: python

    from typing import override
    import pandas as pd
    from openstef_core.base_model import BaseConfig
    from openstef_core.datasets import TimeSeriesDataset
    from openstef_core.transforms import TimeSeriesTransform

    class ProductionScheduleAdder(BaseConfig, TimeSeriesTransform):
        """Add a binary feature indicating planned production hours."""

        schedule_column: str = "production_schedule"

        @override
        def transform(self, data: TimeSeriesDataset) -> TimeSeriesDataset:
            # Mark hours 06:00–22:00 on weekdays as production hours
            index = data.df.index
            is_production = (
                (index.hour >= 6) & (index.hour < 22) & (index.dayofweek < 5)
            ).astype(float)
            data.df[self.schedule_column] = is_production
            return data

        @override
        def features_added(self) -> list[str]:
            return [self.schedule_column]

Once written, a custom transform slots into a pipeline exactly like any built-in one:

.. code-block:: python

    custom_adder = ProductionScheduleAdder(schedule_column="production_hours")
    dataset = custom_adder.fit_transform(dataset)

Because ``features_added()`` is explicit, downstream components — including the model
and any feature-importance reporting — automatically know about the new column.

Putting It Together: A Feature Pipeline
-----------------------------------------

In practice, transforms are composed in sequence. The order matters: some transforms
depend on columns that earlier transforms add (for example, ``RollingAggregatesAdder``
needs the target column to already be present). A typical pipeline for a grid
connection with solar and wind looks like this:

.. code-block:: python

    from openstef_models.transforms.weather_domain import (
        AtmosphereDerivedFeaturesAdder,
        DaylightFeatureAdder,
        RadiationDerivedFeaturesAdder,
    )
    from openstef_models.transforms.energy_domain import WindPowerFeatureAdder
    from openstef_models.transforms.time_domain import (
        CyclicFeaturesAdder,
        DatetimeFeaturesAdder,
        HolidayFeatureAdder,
        LagsAdder,
        RollingAggregatesAdder,
    )
    from datetime import timedelta

    transforms = [
        # Physics-based weather features
        RadiationDerivedFeaturesAdder(coordinate=(52.1, 5.1), radiation_column="ghi"),
        WindPowerFeatureAdder(windspeed_reference_column="wind_speed_10m"),
        AtmosphereDerivedFeaturesAdder(
            pressure_column="pressure_hpa",
            relative_humidity_column="rh_pct",
            temperature_column="temp_c",
        ),
        # Astronomical and calendar features
        DaylightFeatureAdder(coordinate=(52.1, 5.1)),
        DatetimeFeaturesAdder(onehot_encode=False),
        CyclicFeaturesAdder(),
        HolidayFeatureAdder(country_code="NL"),
        # Load history
        LagsAdder(strategy="autocorrelation"),
        RollingAggregatesAdder(
            feature="load_mw",
            aggregation_functions=["mean", "max"],
            horizons=[timedelta(hours=1), timedelta(hours=24)],
        ),
    ]

    for transform in transforms:
        dataset = transform.fit_transform(dataset)

.. note::

   When using OpenSTEF's built-in forecaster classes (such as ``XGBoostForecaster``),
   this pipeline is constructed automatically from the forecast configuration. You only
   need to build it manually when integrating individual transforms into a custom
   workflow.

Feature Importance and Selection
----------------------------------

After training, tree-based models expose feature importance scores that reveal which
engineered features are actually driving predictions. Cyclic time features and
same-time-last-week lags typically rank highest for demand forecasting; radiation
derivatives dominate for solar generation. Low-importance features can be removed to
reduce training time without sacrificing accuracy, using ``EmptyFeatureRemover`` to
automatically drop constant or all-NaN columns.

If you find that a built-in transform contributes nothing for your specific asset, it
is safe to remove it from the pipeline. Conversely, if a domain-specific signal (such
as a price index or a production schedule) consistently ranks highly, it is worth
investing in a well-tested custom transform for it.

For information on how the model consumes these features and produces probabilistic
outputs, see :doc:`quantiles_and_confidence`. For guidance on what to do when feature
data is missing or delayed in production, see :doc:`reliability_and_fallback`.